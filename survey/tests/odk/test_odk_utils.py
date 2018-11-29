__author__ = 'antsmc2'
import time
from zipfile import ZipFile
from StringIO import StringIO
from django.core.files.uploadedfile import SimpleUploadedFile
from lxml import etree
import python_digest
from model_mommy import mommy
import random
from hashlib import md5
from django.test import TestCase
from django.utils.safestring import mark_safe
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.test.client import Client
from django.contrib.auth.models import User
from survey.models import *
from survey.odk.utils.odk_helper import OpenRosaResponseNotAllowed, OpenRosaServerError, OpenRosaResponseNotFound
from survey.forms.question import get_question_form
from survey.forms.logic import LogicForm
from survey.templatetags.template_tags import get_answer
from survey.tests.models.survey_base_test import SurveyBaseTest


class ODKTest(SurveyBaseTest):

    def setUp(self):
        super(ODKTest, self).setUp()
        self.odk_user = ODKAccess.objects.create(interviewer=self.interviewer, user_identifier='ants',
                                                 odk_token='antsman')

    def _save_ussd_compatible_questions(self):
        self._create_ussd_non_group_questions()

    def _make_odk_request(self, url=reverse('odk_survey_forms_list'), data=None, content_type=None, raw=False,
                          odk_user=None):
        if odk_user is None:
            odk_user = self.odk_user
        username = odk_user.user_identifier
        password = odk_user.odk_token
        auth_headers = {}
        if content_type:
            auth_headers['content_type'] = content_type
        if data is None:
            # first do digest challeng
            response = self.client.get(url)
            self.assertEquals(response.status_code, 401)
            digest_challenge = response.get('www-authenticate')
            auth_headers['HTTP_AUTHORIZATION'] = self._get_digest_header(username, password, 'get',
                                                                         url, digest_challenge)
            return self.client.get(url, **auth_headers)
        else:
            response = self.client.post(url)
            self.assertEquals(response.status_code, 401)
            digest_challenge = response.get('www-authenticate')
            auth_headers['HTTP_AUTHORIZATION'] = self._get_digest_header(username, password, 'post',
                                                                         url, digest_challenge)
            if raw:
                return self.client.post(url, data, **auth_headers)
            else:
                return self.client.post(url, data=data, **auth_headers)

    def _get_digest_header(self, username, password, method, uri, digest_challenge):
        return python_digest.build_authorization_request(
            username,
            method.upper(),
            uri,
            1,  # nonce_count
            digest_challenge=digest_challenge,
            password=password
        )

    def test_form_list_throws_no_error(self):
        response = self._make_odk_request()
        self.assertEquals(response.status_code, 200)

    def test_no_xform_without_opening_batch(self):
        response = self._make_odk_request()
        self.assertEquals(response.status_code, 200)
        qset = QuestionSet.objects.first()
        path = '<formID>%s</formID>' % qset.pk
        self.assertNotIn(path, response.content)

    def test_xform_with_opening_batch(self):
        batch = QuestionSet.get(id=self.qset.id)
        batch.open_for_location(self.ea.locations.first())
        response = self._make_odk_request()
        self.assertEquals(response.status_code, 200)
        path = '<formID>%s</formID>' % batch.pk
        self.assertIn(path, response.content)

    def test_batch_without_questions_has_empty_questions_section_in_xform(self):
        url = reverse('download_odk_batch_form', args=(self.qset.id, ))
        response = self._make_odk_request(url=url)
        self.assertEquals(response.status_code, 200)
        # at least some reference representation would be there is it's been referenec some how
        self.assertNotIn('ref="/qset/qset%s/questions/surveyQuestions' % self.qset.id, response.content)

    def test_select_batch_odk_question(self):
        self._save_ussd_compatible_questions()
        url = reverse('download_odk_batch_form', args=(self.qset.id, ))
        response = self._make_odk_request(url=url)
        self.assertEquals(response.status_code, 200)
        survey_tree = etree.fromstring(response.content)
        path = '/qset/qset%s/questions/surveyQuestions/q%s' % (self.qset.id, self.qset.questions.first().id)
        self.assertIn(path, response.content)

    def test_select_batch_with_group_odk_question(self):
        self._create_ussd_group_questions()
        url = reverse('download_odk_batch_form', args=(self.qset.id, ))
        response = self._make_odk_request(url=url)
        self.assertEquals(response.status_code, 200)
        survey_tree = etree.fromstring(response.content)
        path = '/qset/qset%s/questions/surveyQuestions/q%s' % (self.qset.id, self.qset.questions.first().id)
        self.assertIn(path, response.content)
        param_question = self.qset.parameter_list.questions.last()
        group_path = '/qset/qset%s/questions/groupQuestions/q%s' % (self.qset.id, param_question.id)
        self.assertIn(group_path, response.content)
        # a check to confirm the group condition is printed. Might need to improve this more.
        self.assertIn('%s &gt; 7' % group_path, response.content)

    def _get_completed_xform(self, answer1, answer2, answer3, answer4, qset=None):
        if qset is None:
            qset = self.qset
        completed = b'''<qset id="%(qset)s" >
                         <meta>
                            <instanceID>%(instance_id)s</instanceID>
                            <instanceName>%(instance_id)s-Name</instanceName>
                        <creationDate />
                        <locked />
                         </meta>
                         <submissions>
                             <id />
                             <dates>
                                 <lastModified />
                             </dates>
                         </submissions>
                           <surveyAllocation>%(survey_allocation)s</surveyAllocation>
                           <qset%(qset)s>
                            <questions>
                                <groupQuestions></groupQuestions>
                                <surveyQuestions>
                                    <q1>%(answer1)s</q1><q2>%(answer2)s</q2><q3>%(answer3)s</q3><q4>%(answer4)s</q4>
                                </surveyQuestions>
                            </questions>
                           </qset%(qset)s>
                       </qset>
                       '''
        context = {'qset': qset.id, 'instance_id': random.randint(0, 1000),
                   'survey_allocation': self.survey_allocation.allocation_ea.name.encode('utf8'),
                   'answer1': answer1, 'answer2': answer2, 'answer3': answer3, 'answer4': answer4}
        return completed % context

    def _get_completed_sample_xform(self, ref_interview, answer1, answer2, answer3, answer4):
        completed = b'''<qset id="%(qset)s" >
                         <meta>
                            <instanceID>%(instance_id)s</instanceID>
                            <instanceName>%(instance_id)s-Name</instanceName>
                        <creationDate />
                        <locked />
                         </meta>
                         <submissions>
                             <id />
                             <dates>
                                 <lastModified />
                             </dates>
                         </submissions>
                           <surveyAllocation>%(survey_allocation)s</surveyAllocation>
                           <qset1>
                            <sampleData>
                                <selectedSample>%(ref_interview)s</selectedSample>
                            </sampleData>
                            <questions>
                                <groupQuestions></groupQuestions>
                                <surveyQuestions>
                                    <q1>%(answer1)s</q1><q2>%(answer2)s</q2><q3>%(answer3)s</q3><q4>%(answer4)s</q4>
                                </surveyQuestions>
                            </questions>
                           </qset1>
                       </qset>
                       '''
        context = {'qset': self.qset.id, 'instance_id': random.randint(0, 1000),
                   'survey_allocation': self.survey_allocation.allocation_ea.name.encode('utf8'),
                   'answer1': answer1, 'answer2': answer2, 'answer3': answer3, 'answer4': answer4,
                   'ref_interview': ref_interview.id}
        return completed % context

    def _get_completed_xform2(self, answer1, answer2, answer3, answer4, answer5, answer6, answer7,
                              answer8, answer9, answer10):
        completed = b'''<qset id="%(qset)s" >
                         <meta>
                            <instanceID>%(instance_id)s</instanceID>
                            <instanceName>%(instance_id)s-Name</instanceName>
                        <creationDate />
                        <locked />
                         </meta>
                         <submissions>
                             <id />
                             <dates>
                                 <lastModified />
                             </dates>
                         </submissions>
                           <surveyAllocation>%(survey_allocation)s</surveyAllocation>
                           <qset1>
                            <questions>
                                <groupQuestions></groupQuestions>
                                <surveyQuestions>
                                    <q1>%(answer1)s</q1><q2>%(answer2)s</q2><q3>%(answer3)s</q3><q4>%(answer4)s</q4>
                                    <q5>%(answer5)s</q5><q6>%(answer6)s</q6><q7>%(answer7)s</q7><q8>%(answer8)s</q8>
                                    <q9>%(answer9)s</q9><q10>%(answer10)s</q10>
                                </surveyQuestions>
                            </questions>
                           </qset1>
                       </qset>
                       '''
        context = {'qset': self.qset.id, 'instance_id': random.randint(0, 1000),
                   'survey_allocation': self.survey_allocation.allocation_ea.name.encode('utf8'),
                   'answer1': answer1, 'answer2': answer2, 'answer3': answer3, 'answer4': answer4,
                   'answer5': answer5, 'answer6': answer6, 'answer7': answer7, 'answer8': answer8,
                   'answer9': answer9, 'answer10': answer10, }
        return completed % context

    def _get_groups_completed_xform(self, param_answer, answer1, answer2, answer3, answer4):
        param_question = self.qset.parameter_list.questions.last()
        completed = b'''<qset id="%(qset)s" >
                         <meta>
                            <instanceID>%(instance_id)s</instanceID>
                            <instanceName>%(instance_id)s-Name</instanceName>
                        <creationDate />
                        <locked />
                         </meta>
                         <submissions>
                             <id />
                             <dates>
                                 <lastModified />
                             </dates>
                         </submissions>
                           <surveyAllocation>%(survey_allocation)s</surveyAllocation>
                           <qset%(qset)s>
                            <questions>
                                <groupQuestions><q%(param_id)s>%(param_answer)s</q%(param_id)s></groupQuestions>
                                <surveyQuestions>
                                    <q1>%(answer1)s</q1><q2>%(answer2)s</q2><q4>%(answer3)s</q4><q5>%(answer4)s</q5>
                                </surveyQuestions>
                            </questions>
                           </qset%(qset)s>
                       </qset>
                       '''
        context = {'qset': self.qset.id, 'instance_id': random.randint(0, 1000),
                   'param_answer': param_answer, 'param_id': param_question.id,
                   'survey_allocation': self.survey_allocation.allocation_ea.name.encode('utf8'),
                   'answer1': answer1, 'answer2': answer2, 'answer3': answer3, 'answer4': answer4}
        return completed % context

    def _get_non_response_xml(self, answer1, answer2, answer3, answer4):
        completed = b'''<qset id="%(qset)s" >
                         <meta>
                            <instanceID>%(instance_id)s</instanceID>
                            <instanceName>%(instance_id)s-Name</instanceName>
                        <creationDate>02-10-2017</creationDate>
                        <locked />
                         </meta>
                         <submissions>
                             <id />
                             <dates>
                                 <lastModified />
                             </dates>
                         </submissions>
                         <nqrc>1</nqrc>
                         <nqr>OTHER</nqr>
                         <nqr_other>Just tired</nqr_other>
                           <surveyAllocation>%(survey_allocation)s</surveyAllocation>
                           <qset%(qset)s>
                            <questions>
                                <groupQuestions></groupQuestions>
                                <surveyQuestions>
                                    <q1>%(answer1)s</q1><q2>%(answer2)s</q2><q4>%(answer3)s</q4><q5>%(answer4)s</q5>
                                </surveyQuestions>
                            </questions>
                           </qset%(qset)s>
                       </qset>
                       '''
        context = {'qset': self.qset.id, 'instance_id': random.randint(0, 1000),
                   'survey_allocation': self.survey_allocation.allocation_ea.name.encode('utf8'),
                   'answer1': answer1, 'answer2': answer2, 'answer3': answer3, 'answer4': answer4}
        return completed % context

    def _get_xml_with_issue(self, answer1, answer2, answer3, answer4):
        completed = b'''<qset id="%(qset)s" >
                         <meta>
                            <instanceID>%(instance_id)s</instanceID>
                            <instanceName>%(instance_id)s-Name</instanceName>
                        <creationDate>02-10js-2017</creationDate>
                        <locked />
                         </meta>
                         <submissions>
                             <id>93939</id>
                             <dates>
                                 <lastModified />
                             </dates>
                         </submissions>
                           <surveyAllocation>%(survey_allocation)s</surveyAllocation>
                           <qset%(qset)s>
                            <questions>
                                <groupQuestions></groupQuestions>
                                <surveyQuestions>
                                    <q1>%(answer1)s</q1><q2>%(answer2)s</q2><q4>%(answer3)s</q4><q5>%(answer4)s</q5>
                                </surveyQuestions>
                            </questions>
                           </qset%(qset)s>
                       </qset>
                       '''
        context = {'qset': 829, 'instance_id': random.randint(0, 1000),
                   'survey_allocation': self.survey_allocation.allocation_ea.name.encode('utf8'),
                   'answer1': answer1, 'answer2': answer2, 'answer3': answer3, 'answer4': answer4}
        return completed % context

    def test_submit_xform_with_issue_returns_openrosaerror(self):
        self._create_ussd_non_group_questions(self.qset)
        all_questions = self.qset.all_questions
        mommy.make(QuestionLoop, loop_starter=all_questions[1], loop_ender=all_questions[-1])
        country = Location.country()
        for location in country.get_children():
            self.qset.activate_non_response_for(location)
        xml = self._get_xml_with_issue('2', 'James', 'Y', '1')
        f = SimpleUploadedFile("surveyfile.xml", xml)
        url = reverse('odk_submit_forms')
        response = self._make_odk_request(url=url, data={'xml_submission_file': f}, raw=True)
        self.assertEquals( response.status_code, 500)
        self.assertEquals(ODKSubmission.objects.count(), 0)
        self.assertTrue(isinstance(response, OpenRosaServerError))
        # not confirm that 5 responses were given (including param question)
        self.assertEquals(Answer.objects.count(), 0)

    def _get_loop_xml(self, answer1, answer2, answer3, answer4):
        completed = b'''<qset id="%(qset)s" >
                         <meta>
                            <instanceID>%(instance_id)s</instanceID>
                            <instanceName>%(instance_id)s-Name</instanceName>
                            <creationDate>12-10-2017</creationDate>
                        <locked />
                         </meta>
                         <submissions>
                             <id />
                             <dates>
                                 <lastModified />
                             </dates>
                         </submissions>
                           <surveyAllocation>%(survey_allocation)s</surveyAllocation>
                           <qset%(qset)s>
                            <questions>
                                <groupQuestions></groupQuestions>
                                <surveyQuestions>
                                    <q1>%(answer1)s</q1>
                                    <q2q4>
                                        <id1 />
                                        <creationDate>12-10-2017</creationDate>
                                        <q2>%(answer2)s</q2><q3>%(answer3)s</q3><q4>%(answer4)s</q4>
                                    </q2q4>
                                </surveyQuestions>
                            </questions>
                           </qset%(qset)s>
                       </qset>
                       '''
        context = {'qset': self.qset.id, 'instance_id': random.randint(0, 1000),
                   'survey_allocation': self.survey_allocation.allocation_ea.name.encode('utf8'),
                   'answer1': answer1, 'answer2': answer2, 'answer3': answer3, 'answer4': answer4}
        return completed % context

    def test_submit_loop_xform(self):
        self._create_ussd_non_group_questions(self.qset)
        all_questions = self.qset.all_questions
        mommy.make(QuestionLoop, loop_starter=all_questions[1], loop_ender=all_questions[-1])
        country = Location.country()
        for location in country.get_children():
            self.qset.activate_non_response_for(location)
        # confirm all eas are all non response enabled
        for ea in EnumerationArea.objects.all():
            self.assertTrue(self.qset.non_response_enabled(ea))
        xml = self._get_loop_xml('2', 'James', 'Y', '1')
        f = SimpleUploadedFile("surveyfile.xml", xml)
        url = reverse('odk_submit_forms')
        response = self._make_odk_request(url=url, data={'xml_submission_file': f}, raw=True)
        self.assertTrue( 300 > response.status_code and response.status_code >= 200)
        self.assertEquals(ODKSubmission.objects.count(), 1)
        # not confirm that 5 responses were given (including param question)
        self.assertEquals(Answer.objects.count(), 4)

    def test_submit_non_response_xform(self):
        self._create_ussd_non_group_questions(self.qset)
        country = Location.country()
        for location in country.get_children():
            self.qset.activate_non_response_for(location)
        xml = self._get_non_response_xml('2', 'James', 'Y', '1')
        f = SimpleUploadedFile("surveyfile.xml", xml)
        url = reverse('odk_submit_forms')
        response = self._make_odk_request(url=url, data={'xml_submission_file': f}, raw=True)
        self.assertTrue( 300 > response.status_code and response.status_code >= 200)
        self.assertEquals(ODKSubmission.objects.count(), 1)
        # not confirm that 5 responses were given (including param question)
        self.assertEquals(NonResponseAnswer.objects.count(), 1)

    def test_submit_group_xform(self):
        self._create_ussd_group_questions(self.qset)
        xml = self._get_groups_completed_xform('10', '2', 'James', 'Y', '1')
        f = SimpleUploadedFile("surveyfile.xml", xml)
        url = reverse('odk_submit_forms')
        response = self._make_odk_request(url=url, data={'xml_submission_file': f}, raw=True)
        self.assertTrue( 300 > response.status_code and response.status_code >= 200)
        self.assertEquals(ODKSubmission.objects.count(), 1)
        # not confirm that 5 responses were given (including param question)
        self.assertEquals(Answer.objects.count(), len(self.qset.all_questions))
        # now test the instances listpage

    def test_submit_xform(self):
        self._create_ussd_non_group_questions(self.qset)
        xml = self._get_completed_xform('2', 'James', 'Y', '1')
        f = SimpleUploadedFile("surveyfile.xml", xml)
        url = reverse('odk_submit_forms')
        response = self._make_odk_request(url=url, data={'xml_submission_file': f}, raw=True)
        self.assertTrue( 300 > response.status_code and response.status_code >= 200)
        self.assertEquals(ODKSubmission.objects.count(), 1)
        # not confirm that 4 responses were given
        self.assertEquals(Answer.objects.count(), 4)
        # now test the instances listpage
        url = reverse('odk_submission_list')
        # check all the if the
        raj = self.assign_permission_to(User.objects.create_user('Rajni', 'rajni@kant.com', 'I_Rock'),
                                        'can_view_aggregates')
        client = Client()
        client.login(username='Rajni', password='I_Rock')
        response = client.get(url)
        templates = [template.name for template in response.templates]
        self.assertIn('odk/submission_list.html', templates)
        self.assertEquals(response.context['submissions'].count(), 1)
        # check instances list on ODK
        url = reverse('instances_form_list')
        response = self._make_odk_request(url=url)
        templates = [template.name for template in response.templates]
        self.assertIn("odk/instances_xformsList.xml", templates)
        self.assertEquals(response.context['submissions'].count(), 1)
        self.assertEquals(response.context['submissions'].filter(status=ODKSubmission.COMPLETED).count(), 1)
        submission = response.context['submissions'].first()
        # try to download the previously submitted form
        url = reverse('download_odk_submission', args=(submission.pk, ))
        response = self._make_odk_request(url=url)
        self.assertTrue( 300 > response.status_code and response.status_code >= 200)
        self.assertEquals(submission.xml.strip(), response.content.strip())
        tree = etree.fromstring(submission.xml)
        dates_nodes = tree.xpath('//qset/submissions/dates/lastModified')
        # this field is only included when updating instances
        self.assertEquals(len([d.text for d in dates_nodes if d.text]), 1)
        self.assertEquals(tree.xpath('//qset/submissions/id')[0].text, str(submission.id))
        # now submit modified form
        f = SimpleUploadedFile("surveyfile.xml", submission.xml.encode('utf8'))
        url = reverse('odk_submit_forms')
        response = self._make_odk_request(url=url, data={'xml_submission_file': f}, raw=True)
        self.assertTrue(300 > response.status_code and response.status_code >= 200)
        self.assertEquals(ODKSubmission.objects.count(), 1)
        self.assertEquals(Answer.objects.count(), 4)        # note: update only doesn't increase answer or subs count
        submission = ODKSubmission.objects.order_by('created').last()
        tree = etree.fromstring(submission.xml)
        # this field is only included when updating instances
        self.assertEquals(tree.xpath('//qset/submissions/id')[0].text, str(submission.id))

    def test_submit_xform_with_file_form(self):
        import os
        self._create_test_non_group_questions(self.qset)
        BASE_DIR = os.path.dirname(__file__)
        image_path = os.path.join(BASE_DIR, 'testimage.png')
        video_path = os.path.join(BASE_DIR, 'testvideo.mov')
        audio_path = os.path.join(BASE_DIR, 'testaudio.m4a')
        with open(image_path) as fi, open(video_path) as fv, open(audio_path) as fa:
            fi_name = os.path.basename(fi.name)
            fa_name = os.path.basename(fa.name)
            fv_name = os.path.basename(fv.name)
            fi_content = fi.read()
            fa_content = fa.read()
            fv_content = fv.read()
            answers = ('2', 'James', 'Y', '1', ['Y', 'MB'], '31-08-2017', '12.8 8.0 8 7', fi_name, fa_name, fv_name)
            xml = self._get_completed_xform2(*answers)
            f = SimpleUploadedFile("surveyfile.xml", xml)
            sfi = SimpleUploadedFile(fi_name, fi_content)
            sfa = SimpleUploadedFile(fa_name, fa_content)
            sfv = SimpleUploadedFile(fv_name, fv_content)
            url = reverse('odk_submit_forms')
            response = self._make_odk_request(url=url, data={'xml_submission_file': f,
                                                             fi_name: sfi, fa_name: sfa,
                                                             fv_name: sfv}, raw=True)
            self.assertTrue(300 > response.status_code and response.status_code >= 200)
            self.assertEquals(ODKSubmission.objects.count(), 1)
            self.assertEquals(Attachment.objects.count(), 3)
            # not confirm that 4 responses were given
            self.assertEquals(Answer.objects.count(), len(answers))
            # now test the instances listpage
            submission = ODKSubmission.objects.last()
            url = reverse('download_submission_attachment', args=(submission.pk,))
            # check all the if the
            raj = self.assign_permission_to(User.objects.create_user('Rajni', 'rajni@kant.com', 'I_Rock'),
                                            'can_view_aggregates')
            client = Client()
            client.login(username='Rajni', password='I_Rock')
            response = client.get(url)
            self.assertEquals(response._headers['content-type'][1], 'application/zip')
            extracted = self._extract_zip(response.content)
            # check instances list on ODK
            for key, extracted_content in extracted.items():
                # doing checks this way because we're compressing entire directory
                # filename may have a random pre/appender to it
                if fi_name in key:
                    self.assertEquals(extracted_content, fi_content)   # fake image
                if fa_name in key:
                    self.assertEquals(extracted_content, fa_content)   # fake audio
                if fv_name in key:
                    self.assertEquals(extracted_content, fv_content)   # fake video
            # now test get answer of template_tag
            video_answer = VideoAnswer.objects.last()
            text_answer = TextAnswer.objects.last()
            interview = video_answer.interview
            question = video_answer.question
            url_component = '%s %s' % (question.pk, interview.pk)
            # really not the best in the world
            url_desc = mark_safe('<a href="{% url download_qset_attachment ' + url_component + ' %}">Download</a>')
            self.assertEquals(url_desc, get_answer(question, interview))
            self.assertEquals(get_answer(text_answer.question, text_answer.interview), text_answer.value)
            # test case where answer does not exist
            self.assertIn(get_answer(mommy.make(Question, qset=self.qset, answer_type=TextAnswer.choice_name()),
                                     interview), ['', None])

    def test_submit_with_ref_interview_xform(self):
        self._create_ussd_non_group_questions(self.qset)
        interview = mommy.make(Interview, interviewer=self.interviewer, survey=self.survey, ea=self.ea,
                               interview_channel=self.access_channel, question_set=self.qset)
        xml = self._get_completed_sample_xform(interview, '2', 'James', 'Y', '1')
        f = SimpleUploadedFile("surveyfile.xml", xml)
        url = reverse('odk_submit_forms')
        response = self._make_odk_request(url=url, data={'xml_submission_file': f}, raw=True)
        self.assertTrue( 300 > response.status_code and response.status_code >= 200)
        self.assertEquals(ODKSubmission.objects.count(), 1)
        # not confirm that 4 responses were given
        self.assertEquals(Answer.objects.count(), 4)
        # check if the saved interview has current one as reference interview
        self.assertEquals(Interview.objects.last().interview_reference, interview)
        # now test the instances listpage
        url = reverse('odk_submission_list')
        # check all the if the
        raj = self.assign_permission_to(User.objects.create_user('Rajni', 'rajni@kant.com', 'I_Rock'),
                                        'can_view_aggregates')
        client = Client()
        client.login(username='Rajni', password='I_Rock')
        response = client.get(url)
        templates = [template.name for template in response.templates]
        self.assertIn('odk/submission_list.html', templates)
        self.assertEquals(response.context['submissions'].count(), 1)
        # check instances list on ODK

    def _extract_zip(self, input_content):
        input_zip = StringIO(input_content)
        input_zip = ZipFile(input_zip)
        return {name: input_zip.read(name) for name in input_zip.namelist()}

    def _prep_listing(self):
        listing_form = mommy.make(ListingTemplate, name='test_listing')
        mommy.make(QuestionSetChannel, qset=listing_form, channel=self.access_channel.choice_name())
        self._create_ussd_non_group_questions(listing_form)
        self.survey.has_sampling = True
        self.survey.listing_form = listing_form
        self.survey.sample_size = 3
        self.survey.save()
        return listing_form

    def test_submit_insufficient_form_for_listing(self):
        listing_form = self._prep_listing()
        response = self._make_odk_request()
        url = reverse('download_odk_listing_form')
        self.assertIn(listing_form.name, response.content)
        self.assertIn(url, response.content)
        # download listing form
        response = self._make_odk_request(url=url)
        xml = self._get_completed_xform('2', 'James', 'Y', '1', qset=listing_form)
        f = SimpleUploadedFile("surveyfile.xml", xml)
        url = reverse('odk_submit_forms')
        response = self._make_odk_request(url=url, data={'xml_submission_file': f}, raw=True)
        self.assertTrue( 300 > response.status_code and response.status_code >= 200)
        self.assertEquals(ODKSubmission.objects.count(), 1)
        # not confirm that 5 responses were given (including param question)
        self.assertEquals(Answer.objects.count(), len(listing_form.all_questions))
        # now try to download batch form
        url = reverse('download_odk_batch_form', args=(self.qset.id, ))
        response = self._make_odk_request(url=url)
        self.assertTrue(isinstance(response, OpenRosaResponseNotAllowed))

    def test_submit_sufficient_form_for_listing(self):
        listing_form = self._prep_listing()
        response = self._make_odk_request()
        url = reverse('download_odk_listing_form')
        self.assertIn(listing_form.name, response.content)
        self.assertIn(url, response.content)
        # download listing form
        response = self._make_odk_request(url=url)
        xml = self._get_completed_xform('2', 'James', 'Y', '1', qset=listing_form)
        f = SimpleUploadedFile("surveyfile.xml", xml)
        url = reverse('odk_submit_forms')
        response = self._make_odk_request(url=url, data={'xml_submission_file': f}, raw=True)
        self.assertTrue( 300 > response.status_code and response.status_code >= 200)
        self.assertEquals(ODKSubmission.objects.count(), 1)
        # not confirm that 5 responses were given (including param question)
        self.assertEquals(Answer.objects.count(), len(listing_form.all_questions))
        xml = self._get_completed_xform('7', 'Rita', 'Y', '12', qset=listing_form)
        f = SimpleUploadedFile("surveyfile.xml", xml)
        url = reverse('odk_submit_forms')
        response = self._make_odk_request(url=url, data={'xml_submission_file': f}, raw=True)
        self.assertTrue(300 > response.status_code and response.status_code >= 200)
        self.assertEquals(ODKSubmission.objects.count(), 2)
        # not confirm that 5 responses were given (including param question)
        self.assertEquals(Answer.objects.count(), len(listing_form.all_questions)*2)
        xml = self._get_completed_xform('8', 'Sam', 'N', '11', qset=listing_form)
        f = SimpleUploadedFile("surveyfile.xml", xml)
        url = reverse('odk_submit_forms')
        response = self._make_odk_request(url=url, data={'xml_submission_file': f}, raw=True)
        self.assertTrue(300 > response.status_code and response.status_code >= 200)
        self.assertEquals(ODKSubmission.objects.count(), 3)
        # not confirm that 5 responses were given (including param question)
        self.assertEquals(Answer.objects.count(), len(listing_form.all_questions)*3)
        xml = self._get_completed_xform('12', 'Ray', 'N', '8', qset=listing_form)
        f = SimpleUploadedFile("surveyfile.xml", xml)
        url = reverse('odk_submit_forms')
        response = self._make_odk_request(url=url, data={'xml_submission_file': f}, raw=True)
        self.assertTrue(300 > response.status_code and response.status_code >= 200)
        self.assertEquals(ODKSubmission.objects.count(), 4)
        # not confirm that 5 responses were given (including param question)
        self.assertEquals(Answer.objects.count(), len(listing_form.all_questions) * 4)
        # now try to download batch form
        url = reverse('download_odk_batch_form', args=(self.qset.id, ))
        response = self._make_odk_request(url=url)
        self.assertIn('Select Sample', response.content)
        self.assertIn(self.qset.name, response.content)

    def test_submit_invalid_answer_only_exempts_wrong_answer_xform(self):
        self._create_ussd_non_group_questions(self.qset)
        interview = mommy.make(Interview, interviewer=self.interviewer, survey=self.survey, ea=self.ea,
                               interview_channel=self.access_channel, question_set=self.qset)
        xml = self._get_completed_sample_xform(interview, '2', 'James', 'Yol', '1')     # yol is invalid answer
        f = SimpleUploadedFile("surveyfile.xml", xml)
        url = reverse('odk_submit_forms')
        response = self._make_odk_request(url=url, data={'xml_submission_file': f}, raw=True)
        self.assertTrue( 300 > response.status_code and response.status_code >= 200)
        self.assertEquals(ODKSubmission.objects.count(), 1)
        # not confirm that 3 responses were given
        self.assertEquals(Answer.objects.count(), 3)

    def test_download_question_with_flow(self):
        self._create_ussd_non_group_questions()
        numeric_question = Question.objects.filter(answer_type=NumericalAnswer.choice_name()).first()
        last_question = Question.objects.last()
        test_condition = 'equals'
        test_param = '15'
        form_data = {
            'action': LogicForm.SKIP_TO,
            'next_question': last_question.id,
            'condition': test_condition,
            'value': test_param
        }
        logic_form = LogicForm(numeric_question, data=form_data)
        self.assertTrue(logic_form.is_valid())
        logic_form.save()
        self.assertEquals(QuestionFlow.objects.filter(question=numeric_question,
                                                      next_question=last_question).count(), 1)
        url = reverse('download_odk_batch_form', args=(self.qset.id,))
        response = self._make_odk_request(url=url)
        self.assertIn("/qset/qset1/questions/surveyQuestions/q1 = '15'", response.content)

    def test_odk_user_who_does_not_exist_gives_openrosa_404(self):
        self._create_ussd_non_group_questions(self.qset)
        odk_access= ODKAccess(interviewer=self.interviewer, user_identifier='someguy', odk_token='12iw')
        # use unsaved access
        xml = self._get_completed_xform('2', 'James', 'Yol', '1')     # yol is invalid answer
        f = SimpleUploadedFile("surveyfile.xml", xml)
        url = reverse('odk_submit_forms')
        response = self._make_odk_request(url=url, data={'xml_submission_file': f}, raw=True, odk_user=odk_access)
        self.assertEquals(response.status_code, 404)
        self.assertEquals(ODKSubmission.objects.count(), 0)
        # not confirm that 3 responses were given
        self.assertEquals(Answer.objects.count(), 0)
        self.assertTrue(isinstance(response, OpenRosaResponseNotFound))