from time import sleep
from lettuce import *
from rapidsms.contrib.locations.models import Location
from survey.features.page_objects.question import BatchQuestionsListPage, AddQuestionPage, ListAllQuestionsPage, CreateNewQuestionPage, CreateNewSubQuestionPage, EditQuestionPage
from survey.models import Batch, QuestionModule, BatchQuestionOrder
from survey.models.question import Question, QuestionOption
from survey.models.householdgroups import HouseholdMemberGroup
from survey.models.answer_rule import AnswerRule


@step(u'And I have 100 questions under the batch')
def and_i_have_100_questions_under_the_batch(step):
    for i in xrange(100):
        q = Question.objects.create(
            text="some questions %d" %
            i,
            answer_type=Question.NUMBER,
            identifier='ID %d' %
            i,
            order=i)
        q.batches.add(world.batch)
        BatchQuestionOrder.objects.create(
            batch=world.batch, question=q, order=i)


@step(u'And I visit questions listing page of the batch')
def and_i_visit_questions_listing_page_of_the_batch(step):
    world.page = BatchQuestionsListPage(world.browser, world.batch)
    world.page.visit()


@step(u'Then I should see the questions list paginated')
def then_i_should_see_the_questions_list_paginated(step):
    world.page.validate_fields()
    world.page.validate_pagination()
    world.page.validate_fields()


@step(u'When I change to 100 questions per page')
def when_i_change_to_100_questions_per_page(step):
    world.page.fill_valid_values({'number_of_questions_per_page': 100})
    world.page.click_by_css('#a-question-list')


@step(u'Then I should not see pagination')
def then_i_should_not_see_pagination(step):
    world.page.validate_pagination(False)


@step(u'And I have no questions under the batch')
def and_i_have_no_questions_under_the_batch(step):
    Question.objects.filter(batches=world.batch).delete()


@step(u'Then I should see error message on the page')
def then_i_should_see_error_message_on_the_page(step):
    world.page.is_text_present(
        "There are no questions associated with this batch yet.")


@step(u'And I click add question button')
def and_i_click_add_question_button(step):
    world.page.click_link_by_text("Select Question")


@step(u'Then I should see a add question page')
def then_i_should_see_a_add_question_page(step):
    world.page = AddQuestionPage(world.browser, world.batch)
    world.page.validate_url()


@step(u'When I fill the details for add question form')
def when_i_fill_the_details_for_add_question_form(step):
    data = {'module': world.module.id,
            'text': 'hritik  question',
            'answer_type': Question.NUMBER,
            'identifier': 'ID 1'}

    world.page.fill_valid_values(data)


@step(u'Then I should go back to questions listing page')
def then_i_should_go_back_to_questions_listing_page(step):
    world.page = BatchQuestionsListPage(world.browser, world.batch)
    world.page.validate_url()


@step(u'And I should see question successfully added message')
def and_i_should_see_question_successfully_added_message(step):
    world.page.is_text_present("Question successfully added.")


@step(u'And I have a member group')
def and_i_have_a_member_group(step):
    world.household_member_group = HouseholdMemberGroup.objects.create(
        name='Age 4-5', order=1)


@step(u'And I visit add new question page of the batch')
def and_i_visit_add_new_question_page_of_the_batch(step):
    world.page = AddQuestionPage(world.browser, world.batch)
    world.page.visit()


@step(u'And I fill the details for question')
def and_i_fill_the_details_for_question(step):
    world.page.fill_valid_values(
        {'identifier': 'ID 1', 'module': world.module.id, 'text': 'hritik  question'})
    world.page.select('group', [world.household_member_group.pk])


@step(u'When I select multichoice for answer type')
def when_i_select_multichoice_for_answer_type(step):
    world.page.select('answer_type', [Question.MULTICHOICE])


@step(u'Then I should see one option field')
def then_i_should_see_one_option_field(step):
    world.page.see_one_option_field("Option 1")
    world.page.see_option_add_and_remove_buttons(1)


@step(u'When I click add-option icon')
def when_i_click_add_option_icon(step):
    world.page.click_by_css(".icon-plus")


@step(u'Then I should see two options field')
def then_i_should_see_two_options_field(step):
    world.page.see_one_option_field("Option 1")
    world.page.see_one_option_field("Option 2")
    world.page.see_option_add_and_remove_buttons(2)


@step(u'When I click remove-option icon')
def when_i_click_remove_option_icon(step):
    world.page.click_by_css(".icon-remove")


@step(u'Then I should see only one option field')
def then_i_should_see_only_one_option_field(step):
    world.page.see_one_option_field("Option 1")
    world.page.see_option_add_and_remove_buttons(1)
    world.page.option_not_present("Option 2")


@step(u'And I fill an option question')
def and_i_fill_an_option_question(step):
    world.option = {'options': 'some option question text'}
    world.page.fill_valid_values(world.option)


@step(u'And I have more than 50 questions')
def and_i_have_100_questions(step):
    for i in xrange(100):
        Question.objects.create(
            text="some questions %d" %
            i,
            answer_type=Question.NUMBER,
            identifier='ID %d' %
            i,
            order=i)


@step(u'And I visit questions list page')
def and_i_visit_questions_list_page(step):
    world.page = ListAllQuestionsPage(world.browser)
    world.page.visit()


@step(u'And If I click create new question link')
def and_if_i_click_create_new_question_link(step):
    world.page.click_link_by_text("Create New Question")


@step(u'Then I should see create new question page')
def then_i_should_see_create_new_question_page(step):
    world.page = CreateNewQuestionPage(world.browser)
    world.page.validate_url()


@step(u'And I visit create new question page')
def and_i_visit_create_new_question_page(step):
    world.page = CreateNewQuestionPage(world.browser)
    world.page.visit()


@step(u'And I have a multichoice question')
def and_i_have_a_multichoice_question(step):
    world.multi_choice_question = Question.objects.create(
        module=world.module,
        text="Are these insecticide?",
        answer_type=Question.MULTICHOICE,
        order=6,
        group=world.household_member_group,
        identifier='ID 1')
    world.option1 = QuestionOption.objects.create(
        question=world.multi_choice_question, text="Yes", order=1)
    world.option2 = QuestionOption.objects.create(
        question=world.multi_choice_question, text="No", order=2)
    world.option3 = QuestionOption.objects.create(
        question=world.multi_choice_question, text="Dont Know", order=3)


@step(u'And I click on view options link')
def and_i_click_on_view_options_link(step):
    world.page.click_link_by_partial_href(
        "#view_options_%d" % world.multi_choice_question.id)


@step(u'Then I should see the question options in a modal')
def then_i_should_see_the_question_options_in_a_modal(step):
    world.page.validate_fields_present(
        [world.multi_choice_question.text, "Text", "Order"])


@step(u'And when I click the close button')
def and_when_i_click_the_close_button(step):
    world.page.click_link_by_text("Close")


@step(u'Then I should be back to questions list page')
def then_i_should_see_questions_list_page(step):
    sleep(2)
    world.page.validate_fields()


@step(u'And I click on view add subquestion link')
def and_i_click_on_view_add_subquestion_link(step):
    world.browser.click_link_by_text("Add Subquestion")


@step(u'Then I should go to add subquestion page')
def then_i_should_go_to_add_subquestion_page(step):
    world.page = CreateNewSubQuestionPage(
        world.browser, question=world.multi_choice_question)
    world.page.validate_url()


@step(u'When I fill in subquestion details')
def when_i_fill_in_subquestion_details(step):
    world.page.fill_valid_values(
        {'module': world.module.id, 'text': 'hritik  question', 'identifier': 'Q001'})
    world.page.select('group', [world.household_member_group.pk])
    world.page.select('answer_type', [Question.NUMBER])


@step(u'And I should see subquestion successfully added message')
def and_i_should_see_subquestion_successfully_added_message(step):
    world.page.see_success_message('Sub question', 'added')


@step(u'And I fill the invalid details details for question')
def and_i_fill_the_invalid_details_details_for_question(step):
    a_very_long_text = "Is there something here I'm missing? Is uni_form " \
                       "overriding the setting somehow? If not, any advice as " \
                       "to what I might look for in debug to see where/why this is happening?"
    world.page.fill_valid_values({'text': a_very_long_text})


@step(u'And I should see question was not added')
def and_i_should_see_question_was_not_added(step):
    world.page.see_message("Question was not added.")


@step(u'And I should see that option in the form')
def and_i_should_see_that_option_in_the_form(step):
    world.page.see_option_text(world.option['options'], 'options')


@step(u'And I visit question listing page')
def and_i_visit_question_listing_page(step):
    world.page = ListAllQuestionsPage(world.browser)
    world.page.visit()


@step(u'And I click the edit question link')
def and_i_click_the_edit_question_link(step):
    world.page.click_link_by_text(" Edit")


@step(u'Then I should see the edit question page')
def then_i_should_see_the_edit_question_page(step):
    world.page = EditQuestionPage(world.browser, world.multi_choice_question)
    world.page.validate_url()


@step(u'And I see the question form with values')
def and_i_see_the_question_form_with_values(step):
    world.form = {'module': 'Module',
                  'text': 'Text',
                  'group': 'Group',
                  'answer_type': 'Answer type'}

    form_values = {'module': world.module.id,
                   'text': world.multi_choice_question.text,
                   'group': world.multi_choice_question.group.id,
                   'answer_type': world.multi_choice_question.answer_type}
    world.page.validate_form_present(world.form)
    world.page.validate_form_values(form_values)


@step(u'When I fill in edited question details')
def when_i_fill_in_edited_question_details(step):
    world.edited_question_details = {
        'module': world.module.id,
        'text': 'edited question',
        'group': world.multi_choice_question.group.id}
    world.page.see_select_option(['Number'], 'answer_type')
    world.page.fill_valid_values(world.edited_question_details)


@step(u'Then I should see the question successfully edited')
def then_i_should_see_the_question_successfully_edited(step):
    world.page.see_success_message("Question", "edited")


@step(u'And I click on delete question link')
def and_i_click_on_delete_question_link(step):
    world.page.click_link_by_partial_href(
        "#delete_question_%d" % world.multi_choice_question.id)


@step(u'Then I should see a delete question confirmation modal')
def then_i_should_see_a_delete_question_confirmation_modal(step):
    world.page.see_confirm_modal_message(world.multi_choice_question.text)


@step(u'Then I should see that the question was deleted successfully')
def then_i_should_see_that_the_question_was_deleted_successfully(step):
    world.page.see_success_message("Question", "deleted")


@step(u'And I have a sub question for that question')
def and_i_have_a_sub_question_for_that_question(step):
    world.sub_question = Question.objects.create(
        module=world.module,
        parent=world.multi_choice_question,
        text="Sub Question 2?",
        answer_type=Question.NUMBER,
        subquestion=True,
        identifier='Q101')


@step(u'Then I should not see the sub question')
def then_i_should_not_see_the_sub_question(step):
    world.page.is_text_present(world.sub_question.text, False)


@step(u'And I have a non multichoice question')
def and_i_have_a_non_multi_choice_question(step):
    world.multi_choice_question = Question.objects.create(
        module=world.module,
        text="Are these insecticide?",
        answer_type=Question.NUMBER,
        order=7,
        group=world.household_member_group,
        identifier='Q921')
    world.multi_choice_question.batches.add(world.batch)
    BatchQuestionOrder.objects.create(
        batch=world.batch, question=world.multi_choice_question, order=1)


@step(u'When I click on the question')
def and_i_click_on_the_question(step):
    world.page.click_link_by_text(world.multi_choice_question.text)


@step(u'Then I should see the sub question below the question')
def then_i_should_see_the_sub_question_below_the_question(step):
    world.page.is_text_present("Subquestion")
    world.page.is_text_present(world.sub_question.text)


@step(u'And I have a rule linking one option with that subquestion')
def and_i_have_a_rule_linking_one_option_with_that_subquestion(step):
    world.answer_rule = AnswerRule.objects.create(
        question=world.multi_choice_question,
        action=AnswerRule.ACTIONS['ASK_SUBQUESTION'],
        condition=AnswerRule.CONDITIONS['EQUALS_OPTION'],
        validate_with_option=world.option3,
        next_question=world.sub_question)


@step(u'And I have a subquestion under that question')
def and_i_have_a_subquestion_under_that_question(step):
    world.sub_question = Question.objects.create(
        module=world.module,
        subquestion=True,
        parent=world.multi_choice_question,
        text="this is a subquestion",
        identifier='Q022')


@step(u'When I fill in duplicate subquestion details')
def when_i_fill_in_duplicate_subquestion_details(step):
    world.page.fill_valid_values(
        {'module': world.module.id, 'identifier': 'ID 1', 'text': world.sub_question.text})
    world.page.select('group', [world.household_member_group.pk])
    world.page.select('answer_type', [Question.NUMBER])


@step(u'And I should see subquestion not added message')
def and_i_should_see_subquestion_not_added_message(step):
    world.page.is_text_present("Sub question not saved.")


@step(u'And I have a rule on value with that subquestion')
def and_i_have_a_rule_on_value_with_that_subquestion(step):
    world.answer_rule = AnswerRule.objects.create(
        question=world.multi_choice_question,
        validate_with_value=1,
        condition=AnswerRule.CONDITIONS['EQUALS'],
        action=AnswerRule.ACTIONS['ASK_SUBQUESTION'],
        next_question=world.sub_question,
        batch=world.batch)


@step(u'And I click on view logic link')
def and_i_click_on_view_logic_link(step):
    world.page.click_link_by_partial_href(
        "#view_logic_%d" % world.multi_choice_question.id)


@step(u'Then I should see the logic in a modal')
def then_i_should_see_the_logic_in_a_modal(step):
    world.page.validate_fields_present(
        [world.multi_choice_question.text, "Eligibility Criteria", "Question/Value/Option", "Action"])


@step(u'Then I should see delete logic icon')
def then_i_should_delete_logic_icon(step):
    world.browser.find_by_css('.icon-trash')


@step(u'When I click delete logic icon')
def when_i_click_delete_logic_icon(step):
    world.page.click_by_css('#delete-icon-%s' % world.answer_rule.id)


@step(u'And I click confirm delete')
def and_i_click_confirm_delete(step):
    world.page.click_by_css('#delete-logic-%s' % world.answer_rule.id)


@step(u'Then I should redirected to batch question page')
def then_i_should_redirected_to_batch_question_page(step):
    world.page = BatchQuestionsListPage(world.browser, world.batch)
    world.page.validate_url()


@step(u'Then I should see special characters message')
def and_i_should_see_special_characters_message(step):
    special_characters = "Please note that the following special characters will be removed ["
    for character in Question.IGNORED_CHARACTERS:
        special_characters = special_characters + character + " "
    special_characters = special_characters.strip() + "]"
    world.page.is_text_present(special_characters)


@step(u'And I click delete sub question link')
def and_i_click_delete_sub_question_link(step):
    sleep(3)
    world.page.click_delete_subquestion()


@step(u'Then I should see a confirm delete subqestion modal')
def then_i_should_see_a_confirm_delete_subqestion_modal(step):
    world.page.see_confirm_modal_message(world.sub_question.text)


@step(u'Then I should see the sub question deleted successfully')
def then_i_should_see_the_sub_question_deleted_successfully(step):
    world.page.see_success_message("Sub question", "deleted")


@step(u'When I click confirm delete')
def when_i_click_confirm_delete(step):
    world.page.click_by_css("#delete-subquestion-%s" % world.sub_question.id)


@step(u'And I click edit sub question link')
def and_i_click_edit_sub_question_link(step):
    sleep(3)
    world.page.click_by_css("#edit_subquestion_%s" % world.sub_question.id)


@step(u'Then I see the sub question form with values')
def then_i_see_the_sub_question_form_with_values(step):
    form_values = {'module': world.module.id, 'text': world.sub_question.text,
                   'group': world.multi_choice_question.group.id,
                   'identifier': "Q101",
                   'answer_type': world.sub_question.answer_type}
    world.page.validate_form_values(form_values)


@step(u'When I fill in edited sub question details')
def when_i_fill_in_edited_sub_question_details(step):
    world.edited_sub_question_details = {
        'identifier': 'Q101',
        'module': world.module.id,
        'text': 'edited question',
        'group': world.multi_choice_question.group.id}
    world.page.see_select_option(['Number'], 'answer_type')
    world.page.fill_valid_values(world.edited_sub_question_details)


@step(u'Then I should see the sub question successfully edited')
def then_i_should_see_the_sub_question_successfully_edited(step):
    world.page.see_success_message("Sub question", "edited")


@step(u'And I click delete question rule')
def and_i_click_delete_question_rule(step):
    sleep(2)
    world.page.click_by_css('#delete-icon-%s' % world.answer_rule.id)


@step(u'And I should see that the logic was deleted successfully')
def and_i_should_see_that_the_logic_was_deleted_successfully(step):
    world.page.see_success_message("Logic", "deleted")


@step(u'And I select multichoice question in batch')
def and_i_select_multichoice_question_in_batch(step):
    world.batch = Batch.objects.create(
        order=1,
        name="Batch A",
        description='description',
        survey=world.survey)
    world.multi_choice_question.batches.add(world.batch)
    BatchQuestionOrder.objects.create(
        batch=world.batch, question=world.multi_choice_question, order=1)


@step(u'And I have a module')
def and_i_have_a_module(step):
    world.module = QuestionModule.objects.create(name="Education")


@step(u'And I have a location')
def and_i_have_a_location(step):
    world.kampala = Location.objects.create(name="Kampala")


@step(u'And I have an open batch in that location')
def and_i_have_an_open_batch_in_that_location(step):
    world.batch = Batch.objects.create(
        order=1,
        name="Batch A",
        description='description',
        survey=world.survey)
    world.batch.open_for_location(world.kampala)


@step(u'Then I should see question list with only view options action')
def then_i_should_see_question_list_with_only_view_options_action(step):
    world.page.validate_only_view_options_action_exists()


@step(u'And I have a multichoice and numeric questions with logics')
def and_i_have_a_multichoice_and_numeric_questions(step):
    world.numeric_question = Question.objects.create(
        text="some questions", answer_type=Question.NUMBER, identifier='ID', order=1)
    world.multi_choice_question = Question.objects.create(
        text="Are these insecticide?",
        answer_type=Question.MULTICHOICE,
        order=6,
        identifier='ID 1')
    world.option3 = QuestionOption.objects.create(
        text="haha", order=1, question=world.multi_choice_question)

    world.numeric_question.batches.add(world.batch)
    world.multi_choice_question.batches.add(world.batch)
    BatchQuestionOrder.objects.create(
        batch=world.batch, question=world.numeric_question, order=1)
    BatchQuestionOrder.objects.create(
        batch=world.batch, question=world.multi_choice_question, order=2)

    AnswerRule.objects.create(
        batch=world.batch,
        question=world.multi_choice_question,
        action=AnswerRule.ACTIONS['END_INTERVIEW'],
        condition=AnswerRule.CONDITIONS['EQUALS_OPTION'],
        validate_with_option=world.option3)

    AnswerRule.objects.create(
        batch=world.batch,
        question=world.numeric_question,
        action=AnswerRule.ACTIONS['END_INTERVIEW'],
        condition=AnswerRule.CONDITIONS['EQUALS_OPTION'],
        validate_with_value=2)


@step(u'Then I should see field required error message')
def then_i_should_see_field_required_error_message(step):
    world.page.is_text_present("This field is required.")


@step(u'And I should be able to export questions')
def and_i_should_be_able_to_export_questions(step):
    world.page.find_by_css("#export_question", "Export Questions")
