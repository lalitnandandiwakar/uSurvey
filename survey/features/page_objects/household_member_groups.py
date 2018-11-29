from survey.features.page_objects.base import PageObject


class GroupConditionListPage(PageObject):
    url = '/conditions/'

    def validate_fields(self):
        self.validate_fields_present(
            ["Group Criteria List", "Condition", "Attribute", "Value"])


class GroupsListingPage(PageObject):
    url = '/groups/'

    def validate_fields(self):
        self.validate_fields_present(
            ["Groups List", "Order", "Group name", "Actions"])


class AddConditionPage(PageObject):
    url = "/conditions/new/"


class AddGroupPage(PageObject):
    url = '/groups/new/'

    def validate_latest_condition(self, condition):
        self.browser.find_by_value("%s > %s > %s" % (
            condition.attribute, condition.condition, condition.value))


class GroupConditionModalPage(PageObject):
    url = ''

    def validate_contents(self):
        self.validate_fields_present(
            ["Value", "Attribute", "Eligibility Criteria", "New Eligibility Criteria"])


class GroupDetailsPage(PageObject):

    def __init__(self, browser, group):
        super(GroupDetailsPage, self).__init__(browser)
        self.group = group
        self.url = '/groups/%s/' % group.id

    def validate_fields(self):
        self.validate_fields_present(
            ["Group %s Criteria List" % self.group.name, "Condition", "Attribute", "Value"])


class AddNewConditionToGroupPage(PageObject):

    def __init__(self, browser, group):
        super(AddNewConditionToGroupPage, self).__init__(browser)
        self.group = group
        self.url = '/groups/%d/conditions/new/' % group.id


class DeleteHouseholdMemberGroup(PageObject):

    def __init__(self, browser, group):
        super(DeleteHouseholdMemberGroup, self).__init__(browser)
        self.group = group
        self.url = '/groups/%d/delete/' % group.id
