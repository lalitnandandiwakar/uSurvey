import string
import re
import redis
from django.core.cache import cache
from cacheops import cached_as
from dateutil import relativedelta
from datetime import date
import json
import inspect
from django import template
from django.core.urlresolvers import reverse
from survey.interviewer_configs import MONTHS
from survey.models.helper_constants import CONDITIONS
from survey.utils.views_helper import get_ancestors
from survey.models import (Survey, Question, Batch, Interviewer, MultiChoiceAnswer, Answer, AnswerAccessDefinition,
                           ODKAccess, SurveyAllocation)
from survey.models import AudioAnswer
from survey.models import ImageAnswer
from survey.models import QuestionSet
from survey.models import VideoAnswer
from django.utils.safestring import mark_safe
from django.utils import html
from survey.forms.logic import LogicForm

register = template.Library()


@register.filter
def current(value, arg):
    try:
        return value[int(arg)]
    except:
        return None


@register.filter
def next(value, arg):
    try:
        return value[int(arg) + 1]
    except:
        return None


@register.filter
def space_replace(value, search_string):
    return value.replace(search_string, ' ')


@register.filter
def replace_space(value, replace_string):
    """Basically the inverse of space replace
    :param value:
    :param replace_string:
    :return:
    """
    return value.replace(' ', replace_string)


@register.filter
def is_location_selected(locations_data, location):
    if locations_data.has_location_selected(location):
        return "selected='selected'"


@register.filter
def is_ea_selected(locations_data, ea):
    if locations_data.selected_ea == ea:
        return "selected='selected'"


@register.filter
def is_selected(batch, selected_batch):
    if batch == selected_batch:
        return "selected='selected'"


@register.filter
def is_batch_open_for_location(open_locations, location):
    if location in open_locations:
        return "checked='checked'"


@register.filter
def is_mobile_number(field):
    return 'mobile number' in field.lower()


@register.filter
def is_radio(field):
    if "radio" in str(field) and not "select" in str(field):
        return "radio_field"
    return ""


@register.filter
def display_list(list):
    new_list = [str(item) for item in list]
    return mark_safe(', '.join(new_list))


@register.filter
def join_list(list, delimiter):
    new_list = ['<span class="muted">%s</span>' % string.capwords(str(item)) for item in list]
    return mark_safe(delimiter.join(new_list))


@register.filter
def get_value(obj, key):
    if isinstance(obj, dict):
        return obj.get(key, "")
    elif isinstance(key, basestring) and hasattr(obj, key):
        return getattr(obj, key)
    elif callable(obj):
        return obj(key)


@register.filter
def get_cached_result(key, default):
    return cache.get(key, default)


@register.filter
def batches_enabled(survey, ea):
    return 'Enabled' if survey.batches_enabled(ea) else 'Not Enabled'


@register.filter
def get_month(index):
    if not str(index).isdigit() and not index:
        return "N/A"
    return MONTHS[int(index)][1]


@register.filter
def format_date(date):
    if date:
        return date.strftime("%b %d, %Y")


@register.filter
def get_age(d):
    return relativedelta.relativedelta(date.today(), d).years


@register.filter
def get_url_with_ids(args, url_name):
    if isinstance(args, basestring) and (str(args).isdigit() is False):
        arg_list = [int(arg) for arg in args.split(',')]
        return reverse(url_name, args=arg_list)
    if str(args).isdigit():
        return reverse(url_name, args=(args, ))
    return reverse(url_name, args=args, )


@register.filter
def get_url_without_ids(url_name):
    return reverse(url_name)


@register.filter
def add_string(int_1, int_2):
    return "%s, %s" % (str(int_1), str(int_2))


@register.assignment_tag
def concat_strings(*args):
    return ''.join([str(arg) for arg in args])


@register.filter
def condition_text(key):
    value = CONDITIONS.get(key, "")
    return value


@register.filter
def modulo(num, val):
    return num % val == 0


@register.filter
def repeat_string(s, times):
    return s * (times - 1)


@register.filter
def is_survey_selected_given(survey, selected_batch):
    if not selected_batch or not selected_batch.survey:
        return None

    if survey == selected_batch.survey:
        return "selected='selected'"


@register.filter
def non_response_is_activefor(open_locations, location):
    if location in open_locations:
        return "checked='checked'"


@register.filter
def ancestors_reversed(location):
    ancestors = get_ancestors(location)
    ancestors.reverse()
    return ancestors


@register.filter
def show_condition(flow):
    if flow.validation_test:
        return '%s ( %s )' % (flow.validation_test, ' and '.join([str(param) for param in flow.test_params]))
    return ""


@register.filter
def access_channels(answer_type):
    channels = AnswerAccessDefinition.objects.filter(answer_type=answer_type
                                                     ).values_list('channel', flat=True).order_by('channel')
    return ",".join(channels)


@register.filter
def quest_validation_opts(batch):
    opts_dict = {}
    for cls in Answer.__subclasses__():
        opts = []
        for validator in cls.validators():
            opts.append({'display': validator.__name__,
                         'value': validator.__name__.upper()})
        opts_dict[cls.choice_name()] = opts
    return mark_safe(json.dumps(opts_dict))


@register.filter
def validation_args(batch):
    args_map = {}
    for validator in Answer.validators():
        # validator is a class method, plus answer extra pram
        args_map.update({validator.__name__.upper(): len(inspect.getargspec(validator).args) - 2})
    return mark_safe(json.dumps(args_map))


@register.filter
def trim(value):
    return value.strip()


@register.assignment_tag
def get_question_value(question, answers_dict):
    return answers_dict.get(question.pk)


@register.assignment_tag
def get_answer(question, interview):
    @cached_as(question, interview)
    def _get_answer():
        answer_class = Answer.get_class(question.answer_type)
        if answer_class in [VideoAnswer, AudioAnswer, ImageAnswer]:
            url_component = '%s %s' % (question.pk, interview.pk)
            return mark_safe('<a href="{% url download_qset_attachment ' + url_component + ' %}">Download</a>')
        else:
            answer = answer_class.objects.filter(interview=interview, question=question).last()
            if answer:
                return answer.value
    return _get_answer()


@register.assignment_tag
def can_start_survey(interviewer):
    return SurveyAllocation.can_start_batch(interviewer)


@register.assignment_tag
def build_question_text(text, context):
    context = template.Context(context)
    return template.Template(text).render(context)


@register.assignment_tag
def has_super_powers(request):
    from survey.utils.views_helper import has_super_powers
    return has_super_powers(request)


@register.assignment_tag
def is_relevant_sample(ea_id, assignments):
    ea_assignmts = assignments.filter(allocation_ea__id=ea_id)
    return ' or '.join(["selected(/qset/surveyAllocation, '%s')" % a.allocation_ea.name for a in ea_assignmts ])


@register.assignment_tag
def get_download_url(request, url_name, instance=None):
    if instance is None:
        return request.build_absolute_uri(reverse(url_name))
    else:
        return request.build_absolute_uri(reverse(url_name, args=(instance.pk, )))


@register.assignment_tag
def get_absolute_url(request, url_name, *args):
    return request.build_absolute_uri(reverse(url_name, args=args))


@register.assignment_tag
def get_home_url(request):
    return request.build_absolute_uri('/')


@register.assignment_tag
def get_sample_data_display(sample):
    return sample.get_display_label()


@register.assignment_tag
def get_loop_aware_path(question):
    loops = question.qset.get_loop_story().get(question.pk, [])
    tokens = ['q%sq%s' % (loop.loop_starter.pk, loop.loop_ender.pk) for loop in loops]
    if tokens:
        return '/%s' % '/'.join(tokens)
    else:
        return ''


def get_xform_relative_path(question):
    return '/qset/qset%s/questions/surveyQuestions%s' % (question.qset.pk, get_loop_aware_path(question))


def get_node_path(question):
    return '%s/q%s' % (get_xform_relative_path(question), question.pk)


@register.assignment_tag(takes_context=True)
def is_relevant_odk(context, question, interviewer):
    batch = question.qset
    if question.pk == batch.start_question.pk:
        default_relevance = 'true()'
    else:
        default_relevance = 'false()'
    relevance_context = ' (%s)' % (
        ' or '.join(context.get(question.pk, [default_relevance, ])),
    )
    if hasattr(question, 'group') and question.group:
        relevance_context = '%s %s' % (relevance_context, is_relevant_by_group(context, question))

    # do not include back to flows to this
    flows = question.flows.exclude(desc=LogicForm.BACK_TO_ACTION)
    node_path = get_node_path(question)
    flow_conditions = []
    if flows:
        for flow in flows:
            if flow.validation_test:
                text_params = [t.param for t in flow.text_arguments]
                answer_class = Answer.get_class(question.answer_type)
                flow_condition = answer_class.print_odk_validation(     # get appropriate flow condition
                    node_path, flow.validation_test, *text_params)
                flow_conditions.append(flow_condition)
                if flow.next_question:
                    next_question = flow.next_question
                    next_q_context = context.get(
                        next_question.pk, ['false()', ])
                    next_q_context.append(flow_condition)
                    context[next_question.pk] = next_q_context
        null_flows = flows.filter(validation__isnull=True, next_question__isnull=False)
        if null_flows:
            null_flow = null_flows[0]
            # check if next question if we are moving to a less looped question
            # essentially same as checking if next question is outside current questions loop
            loop_story = question.qset.get_loop_story()
            # fix for side by side loops. check
            # basically check if next question is not on same loop
            if len(loop_story.get(question.pk, [])) > len(loop_story.get(null_flow.next_question.pk, [])):
                null_condition = ["count(%s) &gt; 0" % node_path, ]
            else:
                null_condition = ["string-length(%s) &gt; 0" % node_path, ]
            # ['true()', "string-length(%s) &gt; 0" % node_path]
            # null_condition = ['true()', ]
            if len(flow_conditions) > 0 and hasattr(question, 'loop_ended') is False:
                null_condition.append('not(%s)' %
                                      ' or '.join(flow_conditions))
            next_question = null_flow.next_question
            next_q_context = context.get(next_question.pk, ['false()', ])
            next_q_context.append('(%s)' % ' and '.join(null_condition))
            if hasattr(question, 'group') and (hasattr(next_question, 'group') is False or
                                                       question.group != next_question.group):
                next_q_context.append('true()')
            # if get_loop_aware_path(question) != get_loop_aware_path(next_question):
            #     next_q_context.append('true()')
            # if hasattr(next_question, 'loop_ended'):
            #     next_q_context.append('true()')
            context[next_question.pk] = next_q_context
    return mark_safe(relevance_context)


def get_group_question_path(qset, group_question):
    return '/qset/qset%s/questions/groupQuestions/q%s' % (qset.id, group_question.id)


def get_name_references(qset):
    @cached_as(QuestionSet.objects.filter(pk=qset.pk))
    def _get_name_references(qset):
        name_references = {}
        for question in qset.questions.all():
            name_references[question.identifier] = mark_safe('<output value="%s"/>' % get_node_path(question))
        try:
            qset = Batch.get(pk=qset.pk)
            if hasattr(qset, 'parameter_list'):
                for question in qset.parameter_list.questions.all():
                    name_references[question.identifier] = \
                        mark_safe('<output value="%s"/>' % get_group_question_path(qset, question))
        except Batch.DoesNotExist:
            pass
        return name_references
    return template.Context(_get_name_references(qset))


@register.assignment_tag
def get_question_text(question):
    question_context = get_name_references(question.qset)
    return template.Template(html.escape(question.text)).render(question_context)


def is_relevant_by_group(context, question):
    question_group = question.group
    qset = question.qset

    @cached_as(question_group, qset)
    def _is_relevant_by_group(qset):
        qset = QuestionSet.get(pk=qset.pk)
        relevant_new = []
        for condition in question_group.group_conditions.all():
            test_question = qset.parameter_list.questions.get(identifier=condition.test_question.identifier)
            answer_class = Answer.get_class(condition.test_question.answer_type)
            relevant_new.append(answer_class.print_odk_validation(get_group_question_path(qset, test_question),
                                                                  condition.validation_test,  *condition.test_params))
        relevance_builder = ['false()', ]
        if relevant_new:
            relevance_builder.append('(%s)' % ' and '.join(relevant_new))
        return ' and (%s)' % ' or '.join(relevance_builder)
    return _is_relevant_by_group(qset)
