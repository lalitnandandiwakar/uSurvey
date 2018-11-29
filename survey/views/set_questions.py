import json
from django.core.urlresolvers import reverse
from django.shortcuts import render, get_object_or_404
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect, HttpResponse, Http404, JsonResponse
from django.contrib.auth.decorators import permission_required
from survey.forms.filters import QuestionFilterForm
from survey.models import Question, QuestionSet
from survey.models import QuestionFlow
from survey.models import QuestionSet
from survey.models import QuestionTemplate
from survey.models import TemplateOption
from survey.models import QuestionLoop
from survey.models import QuestionOption
from survey.models import Answer
from survey.models import ResponseValidation
from survey.forms.question import get_question_form, BatchQuestionForm, QuestionForm  # , QuestionFlowForm
from survey.services.export_questions import get_question_as_dump
from survey.utils.query_helper import get_filterset
from survey.views.custom_decorators import not_allowed_when_batch_is_open
from survey.forms.logic import LogicForm, LoopingForm
from survey.forms.response_validation import ResponseValidationForm


ADD_LOGIC_ON_OPEN_BATCH_ERROR_MESSAGE = "Logics cannot be added\
    while the batch is open."
ADD_SUBQUESTION_ON_OPEN_BATCH_ERROR_MESSAGE = "Subquestions cannot be\
    added while batch is open."
REMOVE_QUESTION_FROM_OPEN_BATCH_ERROR_MESSAGE = "Question cannot be \
    removed from a batch while the batch is open."


@permission_required('auth.can_view_batches')
def index(request, qset_id):
    # now I'm gonna call question set a batch of questions.\
        #If there's time, I'll rename them properly
    # So don't get confused :)
    try:
        batch = QuestionSet.get(pk=qset_id)
    except QuestionSet.DoesNotExist:
        raise Http404("No QuestionSet Model matches the given query.")
    questions = batch.questions_inline()
    request_data = request.GET if request.method == 'GET' else request.POST
    question_filter_form = QuestionFilterForm(data=request_data, qset=batch)
    search_fields = ['identifier', 'text', ]
    qset_questions = batch.questions.all()
    if 'q' in request_data:
        questions = get_filterset(qset_questions, request_data['q'], search_fields)
    if 'question_types' in request_data:
        relevant_ids = list(question_filter_form.filter(
            qset_questions).values_list('id', flat=True))
        questions = [q for q in questions if q.id in relevant_ids]
    # now maintain same inline other exclusing questions in
    breadcrumbs = Question.index_breadcrumbs(qset=batch)
    if breadcrumbs:
        request.breadcrumbs(breadcrumbs)
    context = {'questions': questions, 'request': request, 'batch': batch,
               'question_filter_form': question_filter_form,
               'placeholder': 'identifier, text',
               'template_file': 'interviews/answer.html',
               'is_preview': True
               # caution atleast on ODK access
               #  at least on access must exist
               }
    return render(request, 'set_questions/index.html', context)


@permission_required('auth.can_view_batches')
def new_subquestion(request, batch_id):
    return _save_subquestion(request, batch_id)


def _save_subquestion(request, batch_id, instance=None):
    # possible subquestions are questions not bound to any interviewer yet
    batch = QuestionSet.get(pk=batch_id)
    QuestionForm = get_question_form(batch.question_model())
    questionform = QuestionForm(batch, instance=instance)
    if request.method == 'POST':
        questionform = QuestionForm(batch, data=request.POST, instance=instance)
        if questionform.is_valid():
            if instance:
                zombify = False
            else:
                zombify = True
            question = questionform.save(zombie=zombify)
            if request.is_ajax():
                return HttpResponse(
                    json.dumps(
                        {
                            'id': question.pk,
                            'text': question.text,
                            'identifier': question.identifier}),
                    content_type='application/json')
            messages.info(request, 'Sub Question saved')
    if instance:
        heading = 'Edit Subquestion'
    else:
        heading = 'New Subquestion'
    context = {
        'questionform': questionform,
        'button_label': 'Create',
        'id': 'add-sub_question-form',
        'USSD_MAX_CHARS': settings.USSD_MAX_CHARS,
        'save_url': reverse(
            '%s_home' %
            batch.resolve_tag()),
        'cancel_url': reverse(
            'qset_questions_page',
            args=(
                batch.pk,
            )),
        'class': 'question-form',
        'heading': heading}
    breadcrumbs = Question.edit_breadcrumbs(qset=batch)
    if breadcrumbs:
        request.breadcrumbs(breadcrumbs)
    template_name = 'set_questions/new.html'
    if request.is_ajax():
        template_name = 'set_questions/_add_question.html'
        return render(request, template_name, context)
    else:
        return HttpResponseRedirect(
            reverse(
                'qset_questions_page',
                args=(
                    batch.pk,
                )))


def get_sub_questions_for_question(request, question_id):
    question = Question.objects.get(id=question_id)
    return _create_question_hash_response(Question.zombies(question.qset))


def get_prev_questions_for_question(request, question_id):
    question = Question.objects.get(id=question_id)
    return _create_question_hash_response(question.previous_inlines())


def get_questions_for_batch(request, batch_id, question_id):
    batch = QuestionSet.get(id=batch_id)
    questions = batch.questions_inline()
    questions = [q for q in questions if int(q.pk) is not int(question_id)]
    return _create_question_hash_response(questions)


def _create_question_hash_response(questions):
    questions_to_display = map(
        lambda question: {
            'id': str(
                question.id),
            'text': question.text,
            'identifier': question.identifier},
        questions)
    return HttpResponse(
        json.dumps(questions_to_display),
        content_type='application/json')


@permission_required('auth.can_view_batches')
def edit_subquestion(request, question_id, batch_id=None):
    question = Question.objects.get(pk=question_id)
    return _save_subquestion(request, batch_id, instance=question)


@permission_required('auth.can_view_batches')
def delete(request, question_id):
    return _remove(request, question_id)


@permission_required('auth.can_view_batches')
def add_logic(request, qset_id, question_id):
    question = Question.get(id=question_id)
    batch = QuestionSet.get(id=qset_id)
    QuestionForm = get_question_form(batch.question_model())
    response = None
    cancel_url = '../'
    logic_form = LogicForm(question)
    question_rules_for_batch = {}
#     question_rules_for_batch[question] = question.rules_for_batch(batch)
    if request.method == "POST":
        logic_form = LogicForm(question, data=request.POST)
        if logic_form.is_valid():
            logic_form.save()
            messages.success(request, 'Logic successfully added.')
            response = HttpResponseRedirect(
                reverse('qset_questions_page', args=(batch.pk, )))
    breadcrumbs = Question.edit_breadcrumbs(qset=batch)
    if breadcrumbs:
        request.breadcrumbs(breadcrumbs)
        cancel_url = breadcrumbs[-1][1]
    context = {
        'logic_form': logic_form,
        'button_label': 'Save',
        'question': question,
        'USSD_MAX_CHARS': settings.USSD_MAX_CHARS,
        'rules_for_batch': question_rules_for_batch,
        'questionform': QuestionForm(
            batch,
            parent_question=question),
        'modal_action': reverse(
            'add_qset_subquestion_page',
            args=(
                batch.pk,
            )),
        'class': 'question-form',
        'batch_id': qset_id,
        'batch': batch,
        'cancel_url': cancel_url}
    return response or render(request, "set_questions/logic.html", context)


def manage_loop(request, question_id):
    question = Question.get(id=question_id)
    batch = QuestionSet.get(pk=question.qset.pk)
    cancel_url = '../'
    existing_loop = getattr(question, 'loop_started', None)
    looping_form = LoopingForm(question, instance=existing_loop)
    if request.method == "POST":
        looping_form = LoopingForm(
            question,
            instance=existing_loop,
            data=request.POST)
        if looping_form.is_valid():
            looping_form.save()
            messages.success(request, 'Loop Logic successfully added.')
            return HttpResponseRedirect(
                reverse(
                    'qset_questions_page',
                    args=(
                        batch.pk,
                    )))
    breadcrumbs = Question.edit_breadcrumbs(qset=batch)

    if breadcrumbs:
        request.breadcrumbs(breadcrumbs)
        cancel_url = breadcrumbs[-1][1]
    context = {
        'loop_form': looping_form,
        'button_label': 'Save',
        'question': question,
        'cancel_url': cancel_url}
    return render(request, "set_questions/loop.html", context)


@permission_required('auth.can_view_batches')
def delete_logic(request, flow_id):
    flow = get_object_or_404(QuestionFlow, pk=flow_id)
    batch = flow.question.qset
    flow.delete()
    _kill_zombies(batch.zombie_questions())
    messages.success(request, "Logic successfully deleted.")
    return HttpResponseRedirect(
        reverse(
            'qset_questions_page',
            args=(
                batch.pk,
            )))


@permission_required('auth.can_view_batches')
def edit(request, question_id):
    question = Question.get(id=question_id)
    batch = QuestionSet.get(pk=question.qset.pk)
    response, context = _render_question_view(
        request, batch, instance=question)
    context['page_title '] = 'Edit Question'
    return response or render(request, 'set_questions/new.html', context)


@permission_required('auth.can_view_batches')
def new(request, qset_id):
    batch = QuestionSet.get(pk=qset_id)             # can be listng or actual batch
    response, context = _render_question_view(request, batch)
    context['page_title '] = 'Add Question'
    return response or render(request, 'set_questions/new.html', context)


@permission_required('auth.can_view_batches')
def insert(request, prev_quest_id):
    prev_question = Question.get(pk=prev_quest_id)
    batch = QuestionSet.get(pk=prev_question.qset.pk)
    response, context = _render_question_view(request, batch, prev_question=prev_question)
    context['prev_question'] = prev_question
    return response or render(request, 'set_questions/new.html', context)


@permission_required('auth.can_view_batches')
def json_create_response_validation(request):
    """This function is meant to create json posted response validation
    :param request:
    :return:
    """
    if request.method == 'POST':
        response_validation_form = ResponseValidationForm(data=request.POST)
        if response_validation_form.is_valid():
            response_validation = response_validation_form.save()
            return JsonResponse({'success': True, 'created': {'id': response_validation.id,
                                                              'text': str(response_validation)}})
        else:
            return JsonResponse({'success': False, 'error': response_validation_form.errors})
    return JsonResponse({})


@permission_required('auth.can_view_batches')
def get_response_validations(request):
    """This function is meant to create json posted response validation
    :param request:
    :return:
    """
    answer_type = request.GET.get('answer_type') if request.method == 'GET' else request.POST.get('answer_type')
    answer_class = Answer.get_class(answer_type)
    validator_names = [validator.__name__ for validator in answer_class.validators()]
    validations = ResponseValidation.objects.filter(validation_test__in=validator_names).values_list('id', flat=True)
    return JsonResponse(list(validations), safe=False)


def get_answer_validations(request):
    """This function is meant to create json posted response validation
    :param request:
    :return:
    """
    answer_type = request.GET.get('answer_type') if request.method == 'GET' else request.POST.get('answer_type')
    answer_class = Answer.get_class(answer_type)
    validator_names = [validator.__name__ for validator in answer_class.validators()]
    return JsonResponse(validator_names, safe=False)


def _process_question_form(request, batch, response, question_form):
    instance = question_form.instance
    action_str = 'edit' if instance else 'add'
    if question_form.is_valid():
        question = question_form.save(**request.POST)
        module = getattr(question, 'module', None)
        if 'add_to_lib_button' in request.POST:
            qt = QuestionTemplate.objects.create(
                identifier=question.identifier,
                text=question.text,
                answer_type=question.answer_type,
                module=module)
            options = question.options.all()
            if options:
                topts = []
                for option in options:
                    topts.append(TemplateOption(
                        question=qt, text=option.text, order=option.order))
                TemplateOption.objects.bulk_create(topts)
            messages.success(request, 'Question successfully %sed. to library' % action_str)
        messages.success(request, 'Question successfully Saved.')
        if 'add_more_button' in request.POST:
            redirect_age = ''
        else:
            redirect_age = reverse('qset_questions_page', args=(batch.pk, ))
        response = HttpResponseRedirect(redirect_age)
    else:
        messages.error(request, 'Question was not %sed: %s' % (action_str, question_form.errors.values()[0][0]))
#         options = dict(request.POST).get('options', None)
    return response, question_form


def _render_question_view(request, batch, instance=None, prev_question=None):
    if instance is None and prev_question is None:
        prev_question = batch.last_question_inline()
    elif prev_question is None:
        try:
            prev_inlines = instance.previous_inlines()
            if prev_inlines:
                prev_question = prev_inlines[-1]
        except ValidationError:
            pass
    button_label = 'Create'
    options = None
    response = None
    QuestionForm = get_question_form(batch.question_model())
    if instance:
        button_label = 'Save'
        options = instance.options.all().order_by('order')
        # options = [option.text.strip()\
            #for option in options] if options else None
    if request.method == 'POST':
        question_form = QuestionForm(
            batch,
            data=request.POST,
            instance=instance,
            prev_question=prev_question)
        response, question_form = _process_question_form(request, batch, response, question_form)
    else:
        question_form = QuestionForm(
            batch, instance=instance, prev_question=prev_question)
    context = {'button_label': button_label,
               'id': 'add-question-form',
               'instance':instance,
               'request': request,
               'class': 'question-form',
                'USSD_MAX_CHARS': settings.USSD_MAX_CHARS,
               'batch': batch,
               'prev_question': prev_question,
               # 'prev_question': prev_question,
               'cancel_url': reverse('qset_questions_page', args=(batch.pk, )),
               'questionform': question_form,
               'response_validation_form': ResponseValidationForm(),
               'model_name' : batch.__class__.__name__
               }

    if options:
        #options = filter(lambda text: text.strip(),
            #list(OrderedDict.fromkeys(options)))
        # options = map(lambda option: re.sub("[%s]" % \
            #settings.USSD_IGNORED_CHARACTERS, '', option), options)
        # map(lambda option: re.sub("  ", ' ', option), options)
        context['options'] = options
    breadcrumbs = Question.edit_breadcrumbs(qset=batch)
    if breadcrumbs:
        request.breadcrumbs(breadcrumbs)
    return response, context


@permission_required('auth.can_view_batches')
def assign(request, qset_id):
    batch = QuestionSet.get(id=qset_id)
    if batch.interviews.count():
        error_message = "Questions cannot be assigned \
            interviews has already been conducted: %s." % \
                        batch.name.capitalize()
        messages.error(request, error_message)
        return HttpResponseRedirect(
            reverse(
                'qset_questions_page',
                args=(
                    batch.pk,
                )))
    if request.method == 'POST':
        data = dict(request.POST)
        last_question = batch.last_question_inline()
        lib_questions = QuestionTemplate.objects.filter(
            identifier__in=data.get('identifier', ''))
        if lib_questions:
            for lib_question in lib_questions:
                question = Question.objects.create(
                    identifier=lib_question.identifier,
                    text=lib_question.text,
                    answer_type=lib_question.answer_type,
                    qset=batch,
                )
                # assign the options
                for option in lib_question.options.all():
                    QuestionOption.objects.create(
                        question=question,
                        text=option.text,
                        order=option.order)
                if last_question:
                    QuestionFlow.objects.create(
                        question=last_question, next_question=question)
                else:
                    batch.start_question = question
                    batch.save()
                last_question = question
            #batch_questions_form = BatchQuestionsForm(batch=batch,\
                #\data=request.POST, instance=batch)
        success_message = "Questions successfully assigned to %s: %s." % (
            batch.verbose_name(), batch.name.capitalize())
        messages.success(request, success_message)
        return HttpResponseRedirect(
            reverse(
                'qset_questions_page',
                args=(
                    batch.pk,
                )))
    used_identifiers = [
        question.identifier for question in batch.questions.all()]
    library_questions = QuestionTemplate.objects.exclude(
        identifier__in=used_identifiers).order_by('identifier')
    question_filter_form = QuestionFilterForm()
#     library_questions =  question_filter_form.filter(library_questions)
    breadcrumbs = Question.edit_breadcrumbs(qset=batch)
    page_name = ''
    if breadcrumbs:
        if breadcrumbs[0][0] == 'Listing Form':
            page_name = 'Listing'
        else:
            page_name = 'Batch'
        request.breadcrumbs(breadcrumbs)
    context = {
        'batch_questions_form': QuestionForm(batch),
        'batch': batch,
        'button_label': 'Save',
        'id': 'assign-question-to-batch-form',
        'library_questions': library_questions,
        'question_filter_form': question_filter_form,
        'page_name': page_name,
        'redirect_url': '/qsets/%s/questions/' % qset_id}
    return render(request, 'set_questions/assign.html',
                  context)


@permission_required('auth.can_view_batches')
def update_orders(request, qset_id):
    batch = QuestionSet.get(id=qset_id)
    # import pdb; pdb.set_trace()
    new_orders = request.POST.getlist('order_information', None)
    if len(new_orders) > 0:
        # wipe off present inline flows
        inlines = batch.questions_inline()
        if inlines:
            start_question = inlines[0]
            question = start_question
            while len(inlines) > 0:
                question = inlines.pop(0)
                QuestionFlow.objects.filter(question=question).delete()
            order_details = [(idx, order.split('-')[-1]) for idx, order in enumerate(new_orders)]
            # map(lambda order: order_details.append(order.split('-')), new_orders)
            # order_details = sorted(order_details, key=lambda detail: int(detail[0]))
            # recreate the flows
            questions = batch.questions.all()
            if questions:  # so all questions can be fetched once and cached
                question_id = order_details.pop(0)[1]
                start_question = questions.get(pk=question_id)
                for order, next_question_id in order_details:
                    QuestionFlow.objects.create(
                        question=questions.get(
                            pk=question_id), next_question=questions.get(
                            pk=next_question_id))
                    question_id = next_question_id
                batch.start_question = start_question
                batch.save()
            # better to clear all loops tied to this qset for now
            QuestionLoop.objects.filter(loop_starter__qset__pk=batch.pk).delete()
            success_message = "Question orders successfully updated for batch:\
                 %s." % batch.name.capitalize()
            messages.success(request, success_message)
    else:
        messages.error(request, 'No questions orders were updated.')
    return HttpResponseRedirect(
        reverse(
            'qset_questions_page',
            args=(
                batch.pk,
            )))


@permission_required('auth.can_view_batches')
@not_allowed_when_batch_is_open(
    message=REMOVE_QUESTION_FROM_OPEN_BATCH_ERROR_MESSAGE,
    redirect_url_name="batch_questions_page",
    url_kwargs_keys=['batch_id'])
def remove(request, question_id):
    return _remove(request, question_id)


@permission_required('auth.can_view_batches')
def remove_loop(request, loop_id):
    loop = get_object_or_404(QuestionLoop, id=loop_id)
    batch = loop.loop_starter.qset
    loop.delete()
    return HttpResponseRedirect(
        reverse(
            'qset_questions_page',
            args=(
                batch.pk,
            )))


def _kill_zombies(zombies):
    for z in zombies:
        z.delete()


def _remove(request, question_id):
    question = Question.get(pk=question_id)
    batch_id = question.qset.id
    batch = QuestionSet.get(pk=batch_id)
    redirect_url = reverse('qset_questions_page', args=(batch_id, ))
    if question.total_answers() > 0:
        messages.error(
            request,
            "Cannot delete question that has been answered at least once.")
    else:
        _kill_zombies(batch.zombie_questions())
        if question:
            success_message = "Question successfully deleted."
            # % ("Sub question" if question.subquestion else "Question"))
            messages.success(request, success_message)
        next_question = batch.next_inline(question)
        previous_inline = question.connecting_flows.filter(validation__isnull=True)
        if previous_inline.exists() and next_question:
            QuestionFlow.objects.create(
                question=previous_inline[0].question,
                next_question=next_question)
        elif next_question:
            # need to delete the previous flow for the next question
            batch.start_question = next_question
            batch.save()
        question.connecting_flows.all().delete()
        question.flows.all().delete()
        question.delete()
    return HttpResponseRedirect(redirect_url)


def export_batch_questions(request, qset_id):
    batch = QuestionSet.get(pk=qset_id)
    filename = '%s_questions' % batch.name
    formatted_responses = get_question_as_dump(batch.flow_questions)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment;\
        filename="%s.csv"' % filename
    response.write("\r\n".join(formatted_responses))
    return response
