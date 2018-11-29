from datetime import date, datetime
import os
import pytz
from lxml import etree
from django.core.files.base import ContentFile
from dateutil.parser import parse as extract_date
from django.forms import ValidationError
from django.http import HttpResponse, HttpResponseNotFound, StreamingHttpResponse
from django.core.servers.basehttp import FileWrapper
from django.core.files.storage import get_storage_class
from django.conf import settings
from django import template
from django.utils import timezone
from djangohttpdigest.digest import Digestor
from djangohttpdigest.authentication import SimpleHardcodedAuthenticator
from django.utils.translation import ugettext as _
from survey.models import (Survey, Interviewer, Interview, SurveyAllocation, ODKAccess, QuestionSet,
                           Question, Batch, ODKSubmission, ODKGeoPoint, TextAnswer, Answer, NonResponseAnswer,
                           VideoAnswer, AudioAnswer, ImageAnswer, MultiSelectAnswer, MultiChoiceAnswer, DateAnswer,
                           GeopointAnswer, ListingSample)
from survey.utils.logger import glogger as logger
from functools import wraps
from survey.utils.zip import InMemoryZip
from django.contrib.sites.models import Site
from django_rq import job, get_connection


OPEN_ROSA_VERSION_HEADER = 'X-OpenRosa-Version'
HTTP_OPEN_ROSA_VERSION_HEADER = 'HTTP_X_OPENROSA_VERSION'
OPEN_ROSA_VERSION = '1.0'
DEFAULT_CONTENT_TYPE = 'text/xml; charset=utf-8'
INSTANCE_ID_PATH = '//qset/meta/instanceID'
INSTANCE_NAME_PATH = '//qset/meta/instanceName'
CREATION_DATE_PATH = '//qset/meta/creationDate'
DEFAULT_DATE_CREATED_PATH = '//qset/meta/creationDate'
FORM_ID_PATH = '//qset/@id'
SUBMISSIONS_ID_PATH = '//qset/submissions/id'
FORM_TYPE_PATH = '//qset/type'
NON_RESPONSE_CONFIRMATION_PATH = '//qset/nqrc'
NON_RESPONSE_PATH = '//qset/nqr'
NON_RESPONSE_OTHERS_PATH = '//qset/nqr_other'
FORM_ASSIGNMENT_PATH = '//qset/surveyAllocation'
ANSWER_NODE_PATH = '//qset/qset{{ qset_id }}'
# default content length for submission requests
DEFAULT_CONTENT_LENGTH = 10000000
MAX_DISPLAY_PER_COLLECTOR = 1000


class NotEnoughData(ValueError):
    pass


def _get_tree_from_blob(blob_contents):
    return etree.fromstring(blob_contents)
#
#
# def _get_tree(xml_file):
#     return etree.fromstring(xml_file.read())


# either tree or xml_string must be defined
def _get_nodes(search_path, tree):
    return tree.xpath(search_path)


@job('odk', connection=get_connection())
def process_answers(xml, qset, access_channel, question_map, survey_allocation, submission, media_files={}):
    """Process answers for this answers_node. It's supposed to handle for all question answers in this xform.
    :param answers_node:
    :param qset:
    :param interviewer:
    :param question_map:
    :param survey_allocation:
    :param submission (e.g. odk submission)
    :param media_files (optional dict to search for media files (otherwise it shall be searched in submission attachmt.
    :return:
    """
    try:
        if not media_files:
            # if media files is not supplied, take it from the ODK submission
            media_files = {os.path.basename(attachment.media_file.name): attachment.media_file
                           for attachment in submission.attachments.all()}
        survey_tree = _get_tree_from_blob(xml)
        answers_nodes = _get_answer_nodes(survey_tree, qset)
        created_interviews = []
        survey = survey_allocation.survey
        for answers_node in answers_nodes:
            # answers = []
            survey_parameters = []
            reference_interview = None          # typically used if
            if _get_nodes('./sampleData/selectedSample', answers_node):
                # the following looks ugly but ./sampleData/selectedSample is calculated in xform by a concat of
                # sampleData/iq{{ ea_id }} values with -. See question_set.xml binding for ./sampleData/selectedSample
                # if for some reason more than one interview value is reflected, choose the first one
                reference_interview = _get_nodes('./sampleData/selectedSample',
                                                 answers_node)[0].text.strip('-').split('-')[0]
                reference_interview = Interview.objects.get(id=reference_interview)
            # map(lambda node: answers.extend(get_answers(node, qset, question_map)), question_answers_node.getchildren())
            # map(lambda node: survey_parameters.extend(get_answers(node, qset, question_map)),
            #     survey_parameters_node.getchildren())
            # now check if non response exists and is selected
            if _get_nodes(NON_RESPONSE_CONFIRMATION_PATH, survey_tree) and \
                            int(_get_nodes(NON_RESPONSE_CONFIRMATION_PATH, survey_tree)[0].text) > 0:
                answer = _get_nodes(NON_RESPONSE_PATH, survey_tree)[0].text
                if answer.upper() == 'OTHER':        # user selected non respons
                    answer = _get_nodes(NON_RESPONSE_OTHERS_PATH, survey_tree)[0].text
                non_response = save_non_response(survey_tree, qset, survey, survey_allocation, access_channel, answer,
                                                 reference_interview)
                created_interviews.append(non_response.interview)
            else:
                question_answers_node = _get_nodes('./questions/surveyQuestions', answers_node)[0]
                answers = get_answers(question_answers_node, qset, question_map,
                                      _get_default_date_created(survey_tree))
                survey_parameters = None
                if hasattr(qset, 'parameter_list'):
                    survey_parameters_node = _get_nodes('./questions/groupQuestions', answers_node)[0]
                    # survey paramaters does not have any single repeat
                    survey_parameters = get_answers(survey_parameters_node, qset, question_map,
                                                    _get_default_date_created(survey_tree))[0]
                created_interviews.extend(Interview.save_answers(qset, survey, survey_allocation.allocation_ea,
                                                                 access_channel, question_map, answers,
                                                                 survey_parameters=survey_parameters,
                                                                 reference_interview=reference_interview,
                                                                 media_files=media_files))
            if survey.has_sampling:
                survey_allocation.stage = SurveyAllocation.SURVEY
                survey_allocation.save()
        submission.status = ODKSubmission.COMPLETED
        submission.interviews.all().delete()          # wipe off the old interviews for this submission
        map(lambda interview: submission.interviews.add(interview), created_interviews)    # update with present interviews
        submission.save()
    except Exception, ex:
        # Let me confirm here. Capture if there is a failure for some reason
        logger.error('Error saving answer: %s' % str(ex))


def save_non_response(survey_tree, qset, survey, survey_allocation, access_channel, answer, reference_interview):
    interviewer = survey_allocation.interviewer
    closure_date = timezone.now()
    if _get_nodes(CREATION_DATE_PATH, survey_tree) and _get_nodes(CREATION_DATE_PATH, survey_tree)[0].text:
        extracted_date = extract_date(_get_nodes(CREATION_DATE_PATH, survey_tree)[0].text, dayfirst=False)
        closure_date = extracted_date.replace(tzinfo=timezone.now().tzinfo)
    interview = Interview.objects.create(survey=survey, question_set=qset, ea=survey_allocation.allocation_ea,
                                         interviewer=interviewer, interview_channel=access_channel,
                                         closure_date=closure_date,
                                         interview_reference_id=reference_interview)
    return NonResponseAnswer.objects.create(interview=interview, value=answer, interviewer=interviewer)


def get_answers(node, qset, question_map, completion_date):
    """get answers for the node set. Would work for nested loops but for loops sitting in same inline question thread
    """
    answers = []
    inline_record = {}
    for e in node.getchildren():
        if e.getchildren():
            if _get_nodes('./creationDate', e):
                completion_date = extract_date(_get_nodes('./creationDate', e)[0].text, dayfirst=False)
            loop_answers = get_answers(e, qset, question_map, completion_date)
            _update_loop_answers(inline_record, loop_answers)
            answers.extend(loop_answers)
        else:
            inline_record['completion_date'] = completion_date
            inline_record[e.tag.strip('q')] = e.text
            question = question_map.get(e.tag.strip('q'), '')
            if question:
                _update_answer_dict(question, e.text, answers)
    if len(answers) == 0:       # if there is no child here, you have to record the inline
        answers.append(inline_record)
    return answers


def _update_answer_dict(question, answer, answers):
    for d in answers:
        d[question.pk] = answer
    return answers


def _update_loop_answers(inline_record, loop_answers):
    for record in loop_answers:
        record.update(inline_record)
    return loop_answers


def _get_answer_nodes(tree, qset):
    answer_path = template.Template(ANSWER_NODE_PATH).render(template.Context({'qset_id': qset.pk}))
    return _get_nodes(answer_path, tree)


def _get_instance_id(survey_tree):
    return _get_nodes(INSTANCE_ID_PATH, survey_tree)[0].text


def _get_instance_name(survey_tree):
    return _get_nodes(INSTANCE_NAME_PATH, survey_tree)[0].text


def _get_default_date_created(survey_tree):
    date_string = _get_nodes(DEFAULT_DATE_CREATED_PATH, survey_tree)[0].text
    if date_string:
        return extract_date(date_string, dayfirst=False)
    else:
        return datetime.now()


def _get_form_id(survey_tree):
    return _get_nodes(FORM_ID_PATH, survey_tree)[0]


def _get_submission_id(survey_tree):
    return _get_nodes(SUBMISSIONS_ID_PATH, survey_tree)[0].text


def _get_qset(survey_tree):
    pk = _get_nodes(FORM_ID_PATH, survey_tree)[0]
    return QuestionSet.get(pk=pk)


def _get_allocation(interviewer, survey_tree):
    ea_name = _get_nodes(FORM_ASSIGNMENT_PATH, survey_tree)[0].text
    return interviewer.unfinished_assignments.get(allocation_ea__name=ea_name)


def process_submission(interviewer, xml_file, media_files={}, request=None):
    """extracts and saves the collected data from associated xform.
    """
    # media_files = dict([(os.path.basename(f.name), f) for f in media_files])
    return process_xml(interviewer, xml_file.read(), media_files=media_files, request=request)


def process_xml(interviewer, xml_blob, media_files={}, request=None):
    survey_tree = _get_tree_from_blob(xml_blob)
    form_id = _get_form_id(survey_tree)
    submission_id = _get_submission_id(survey_tree) or None
    instance_id = _get_instance_id(survey_tree)
    instance_name = _get_instance_name(survey_tree)
    qset = _get_qset(survey_tree)
    survey_allocation = _get_allocation(interviewer, survey_tree)
    # since interviewers may have downloaded this submission file before, fetch old instance if exists
    if submission_id:
        submission = ODKSubmission.objects.get(id=submission_id)
        if ListingSample.objects.filter(interview__in=submission.interviews.all()).exists():
            raise ValueError('Cannot update Listing with existing batches')
        submission.xml = xml_blob       # update the xml
        submission.save()
    else:
        # first things first. save the submission incase all else background task fails... enables recover
        submission = ODKSubmission.objects.create(interviewer=interviewer, survey=survey_allocation.survey,
                                                  question_set=qset, ea=survey_allocation.allocation_ea,
                                                  form_id=form_id, xml=xml_blob, instance_id=instance_id,
                                                  instance_name=instance_name)
    question_map = dict([(str(q.pk), q) for q in qset.all_questions])
    access_channel = ODKAccess.objects.filter(interviewer=interviewer).first()
    # refresh attachments
    submission.attachments.all().delete()
    submission.save_attachments(media_files)
    process_answers.delay(xml_blob, qset, access_channel, question_map, survey_allocation, submission)
    #process_answers(xml_blob, qset, access_channel, question_map, survey_allocation, submission)
    return submission


def get_survey_allocation(interviewer):
    '''Just helper function to put additional layer of abstraction to allocation retrival
    @param: interviewer. Interviewer to which to get survey allocation
    '''
    return SurveyAllocation.get_allocation_details(interviewer)


def disposition_ext_and_date(name, extension, show_date=True):
    if name is None:
        return 'attachment;'
    if show_date:
        name = "%s_%s" % (name, date.today().strftime("%Y_%m_%d"))
    return 'attachment; filename=%s.%s' % (name, extension)


def response_with_mimetype_and_name(
        mimetype, name, extension=None, show_date=True,
        use_local_filesystem=False, full_mime=False):
    if extension is None:
        extension = mimetype
    if not full_mime:
        mimetype = "application/%s" % mimetype
    response = HttpResponse(content_type=mimetype)
    response['Content-Disposition'] = disposition_ext_and_date(name, extension, show_date)
    return response


class HttpResponseNotAuthorized(HttpResponse):
    status_code = 401

    def __init__(self):
        HttpResponse.__init__(self)
        self['WWW-Authenticate'] =\
            'Basic realm="%s"' % Site.objects.get_current().name


class BaseOpenRosaResponse(HttpResponse):
    status_code = 201

    def __init__(self, *args, **kwargs):
        super(BaseOpenRosaResponse, self).__init__(*args, **kwargs)
        if self.status_code > 201:
            self.reason_phrase = self.content
        self[OPEN_ROSA_VERSION_HEADER] = OPEN_ROSA_VERSION
        tz = pytz.timezone(settings.TIME_ZONE)
        dt = datetime.now(tz).strftime('%a, %d %b %Y %H:%M:%S %Z')
        self['Date'] = dt
        self['X-OpenRosa-Accept-Content-Length'] = DEFAULT_CONTENT_LENGTH
        self['Content-Type'] = DEFAULT_CONTENT_TYPE


class OpenRosaResponse(BaseOpenRosaResponse):
    status_code = 201

    def __init__(self, *args, **kwargs):
        super(OpenRosaResponse, self).__init__(*args, **kwargs)
        # wrap content around xml
        self.content = '''<?xml version='1.0' encoding='UTF-8' ?>
<OpenRosaResponse xmlns="http://openrosa.org/http/response">
        <message nature="">%s</message>
</OpenRosaResponse>''' % self.content
        self['X-OpenRosa-Accept-Content-Length'] = len(self.content)


class OpenRosaResponseNotFound(OpenRosaResponse):
    status_code = 404


class OpenRosaResponseBadRequest(OpenRosaResponse):
    status_code = 400


class OpenRosaResponseNotAllowed(OpenRosaResponse):
    status_code = 405


class OpenRosaRequestForbidden(OpenRosaResponse):
    status_code = 403


class OpenRosaRequestConflict(OpenRosaResponse):
    status_code = 409


class OpenRosaServerError(OpenRosaResponse):
    status_code = 500


def http_digest_interviewer_auth(func):
    @wraps(func)
    def _decorator(request, *args, **kwargs):
        if request.META.has_key('HTTP_HOST'):
            realm = request.META['HTTP_HOST']
        else:
            realm = Site.objects.get_current().name
        digestor = Digestor(method=request.method,
                            path=request.get_full_path(), realm=realm)
        if request.META.has_key('HTTP_AUTHORIZATION'):
            logger.debug('request meta: %s' %
                         request.META['HTTP_AUTHORIZATION'])
            try:
                parsed_header = digestor.parse_authorization_header(
                    request.META['HTTP_AUTHORIZATION'])
                if parsed_header['realm'] == realm:
                    odk_access = ODKAccess.objects.get(user_identifier=parsed_header[
                                                       'username'], is_active=True)
                    # interviewer = Interviewer.objects.get(mobile_number=parsed_header['username'], is_blocked=False)
                    authenticator = SimpleHardcodedAuthenticator(server_realm=realm,
                                                                 server_username=odk_access.user_identifier,
                                                                 server_password=odk_access.odk_token)
                    if authenticator.secret_passed(digestor):
                        request.user = odk_access.interviewer
                        return func(request, *args, **kwargs)
            except ODKAccess.DoesNotExist:
                return OpenRosaResponseNotFound()
        response = HttpResponseNotAuthorized()
        response['www-authenticate'] = digestor.get_digest_challenge()
        return response
    return _decorator


def get_zipped_dir(dirpath):
    zipf = InMemoryZip()
    for root, dirs, files in os.walk(dirpath):
        for filename in files:
            f = open(os.path.join(root, filename))
            zipf.append(filename, f.read())
            f.close()
    return zipf.read()
