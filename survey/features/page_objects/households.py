# vim: ai ts=4 sts=4 et sw=4 encoding=utf-8
from rapidsms.contrib.locations.models import Location
from survey.features.page_objects.base import PageObject
from survey.investigator_configs import MONTHS
from survey.models.investigator import Investigator


class NewHouseholdPage(PageObject):
    url = "/households/new/"

    def valid_page(self):
        fields = ['investigator', 'surname', 'first_name', 'male', 'date_of_birth', 'occupation',
                  'level_of_education', 'resident_since_month', 'resident_since_year']
        fields += ['uid']
        for field in fields:
            assert self.browser.is_element_present_by_name(field)

    def get_household_values(self):
        return self.values

    def fill_valid_values(self, values, ea=None):
        kampala = Location.objects.get(name="Kampala")
        kampala_county = Location.objects.get(name="Kampala County")
        kampala_subcounty = Location.objects.get(name="Subcounty")
        kampala_parish = Location.objects.get(name="Parish")
        kampala_village = Location.objects.get(name="Village")
        self.fill_in_with_js('$("#location-district")', kampala.id)
        self.fill_in_with_js('$("#location-county")', kampala_county.id)
        self.fill_in_with_js('$("#location-subcounty")', kampala_subcounty.id)
        self.fill_in_with_js('$("#location-parish")', kampala_parish.id)
        self.fill_in_with_js('$("#location-village")', kampala_village.id)
        self.fill_in_with_js('$("#widget_ea")', ea.id)

        investigator = Investigator.objects.get(name="Investigator name")
        self.fill_in_with_js('$("#household-investigator")', investigator.id)
        self.fill_in_with_js('$("#household-extra_resident_since_year")', 1984)
        self.fill_in_with_js('$("#household-extra_resident_since_month")', 1)
        self.values = values
        self.browser.fill_form(self.values)

    def validate_household_created(self):
        assert self.browser.is_text_present(
            "Household successfully registered.")

    def has_children(self, value):
        self.choose_radio('has_children', value)

    def are_children_fields_disabled(self, is_disabled=True):
        for element_id in ['aged_between_5_12_years', 'aged_between_13_17_years']:
            element_id = 'household-children-' + element_id
            assert self.is_disabled(element_id) == is_disabled
        self.are_children_below_5_fields_disabled(is_disabled=is_disabled)

    def is_no_below_5_checked(self):
        assert self.browser.find_by_id(
            'household-children-has_children_below_5_1').selected == True

    def cannot_say_yes_to_below_5(self):
        assert self.is_disabled(
            "household-children-has_children_below_5_0") == True
        self.are_children_fields_disabled()

    def has_children_below_5(self, value):
        self.choose_radio('has_children_below_5', value)

    def are_children_below_5_fields_disabled(self, is_disabled=True):
        for element_id in ['aged_between_0_5_months', 'aged_between_6_11_months', 'aged_between_12_23_months',
                           'aged_between_24_59_months']:
            element_id = 'household-children-' + element_id
            assert self.is_disabled(element_id) == is_disabled

    def has_women(self, value):
        self.choose_radio('has_women', value)

    def are_women_fields_disabled(self, is_disabled=True):
        for element_id in ['aged_between_15_19_years', 'aged_between_20_49_years']:
            element_id = 'household-women-' + element_id
            assert self.is_disabled(element_id) == is_disabled

    def fill_in_number_of_females_lower_than_sum_of_15_19_and_20_49(self):
        self.browser.fill('number_of_females', '1')
        self.browser.fill('aged_between_15_19_years', '2')
        self.browser.fill('aged_between_20_49_years', '3')

    def see_an_error_on_number_of_females(self):
        self.is_text_present(
            'Please enter a value that is greater or equal to the total number of women above 15 years age.')

    def choose_occupation(self, occupation_value):
        self.browser.select('occupation', occupation_value)

    def is_specify_visible(self, status=True):
        extra = self.browser.find_by_css('#extra-occupation-field')
        if status:
            assert len(extra) == 1
        else:
            assert len(extra) == 0


class HouseholdDetailsPage(PageObject):

    def __init__(self, browser, household):
        super(HouseholdDetailsPage, self).__init__(browser)
        self.browser = browser
        self.household = household
        self.url = '/households/' + str(household.id) + '/'

    def validate_household_details(self):
        household_head = self.household.get_head()
        details = {
            'Family Name': household_head.surname,
            'Other Names': household_head.first_name,
            'Age': str(household_head.get_age()),
            'Gender': 'Male' if household_head.male else 'Female',
            'Occupation / Main Livelihood': household_head.occupation,
            'Highest level of education completed': household_head.level_of_education,
            'Since when have you lived here': str(household_head.resident_since_year),
        }
        for label, text in details.items():
            self.is_text_present(label)
            self.is_text_present(text)
        self.is_text_present(MONTHS[household_head.resident_since_month][1])

    def validate_household_member_details_table_headings(self):
        member_details_headings = ['Family Name', 'Date of birth', 'Sex']
        for heading in member_details_headings:
            self.is_text_present(heading)

    def validate_household_member_details_values(self):
        for member in self.household.household_member.all():
            for detail in [member.surname, member.date_of_birth.strftime('%b %d, %Y'), 'Male' if member.male else 'Female']:
                self.is_text_present(str(detail))

    def validate_household_member_details(self):
        self.validate_household_member_details_table_headings()
        self.validate_household_member_details_values()

    def validate_household_member_title_and_add_household_member_link(self):
        self.is_text_present('Household Members:')
        self.browser.find_link_by_text('Add Member')

    def validate_actions_edit_and_delete_member(self):
        self.browser.find_link_by_text('Edit')
        self.browser.find_link_by_text('Delete')

    def click_delete_link(self, member_id):
        self.browser.click_link_by_partial_href(
            "#delete_member_%d" % member_id)


class HouseholdsListPage(PageObject):
    url = '/households/'

    def validate_fields(self):
        self.validate_fields_present(["Households List", "Household ID", "Household Head",
                                      "District", "County", "Sub County", "Parish", "Village", "Investigator"])

    def validate_pagination(self):
        self.browser.click_link_by_text("2")

    def no_registered_huseholds(self):
        self.browser.is_text_present(
            'There are  no households currently registered  for this country.')


class EditHouseholdsPage(PageObject):

    def __init__(self, browser, household):
        self.browser = browser
        self.household = household
        self.url = '/households/%s/edit/' % str(household.id)
