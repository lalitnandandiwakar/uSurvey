Feature: Users feature

    Scenario: new user page
      Given I am logged in as a superuser
      And I visit new user page
      Then I see all  new user fields
      And I click submit
      Then I should see the error messages

    Scenario: create user
       Given I am logged in as a superuser
       And I have a group
       And I visit new user page
       Then I fill all necessary new user fields
       And I click submit
       Then I should see user successfully registered
       And I can login that user successfully

    Scenario: create user with already existing mobile
      Given I am logged in as a superuser
      And I have a group
      And I visit new user page
      Then I fill an existing mobile number
      And I click submit
      Then I should see existing mobile number error message

    Scenario: create user with already existing username
      Given I am logged in as a superuser
      And I have a group
      And I visit new user page
      Then I fill an existing username
      And I click submit
      Then I should see existing username error message

    Scenario: create user with already existing email
      Given I am logged in as a superuser
      And I have a group
      And I visit new user page
      Then I fill an existing email
      And I click submit
      Then I should see existing email error message

    Scenario: create user with prohibited username
      Given I am logged in as a superuser
      And I have a group
      And I visit new user page
      Then I fill a not allowed username
      And I click submit
      Then I should see not allowed username error message

    Scenario: List users
      Given I am logged in as a superuser
      And I have 100 users
      And I visit the users list page
      Then I should see a list of users
      When I click add user button
      Then I should see add user page

    Scenario: Edit a user
      Given I am logged in as a superuser
      And I visit the users list page
      And I click on the edit button
      Then I should see the users information in a form
      And I see that username is readonly
      When I modify the users information
      And I click the update button
      Then I should see user information updated successfully

    Scenario: Edit a user when logged in with no permissions
      Given I have a user
      And I visit the login page
      And I login a user
      And I am in the home page
      And I click user settings link
      And I select edit action
      Then I should not see the groups field
      When I modify the users information
      And I click the update button
      Then I should see user information updated successfully

    Scenario: Edit a user when logged as superuser
      Given I am logged in as a superuser
      And I visit the login page
      And I login a user
      And I am in the home page
      And I click user settings link
      And I select edit action
      Then I should see the groups field
      When I modify the users information
      And I click the update button
      Then I should see user information updated successfully

    Scenario: View user details
      Given I am logged in as admin
      And I have one user
      And I visit the users list page
      And I click the user details link
      Then I should see the user details displayed
      Then back button should take back to users page

  Scenario: Deactivate/Activate a user
    Given I am logged in as admin
    And I have one user
    And I visit the users list page
    And I click the user deactivate link
    Then I should see a deactivate user confirmation modal
    When I confirm deactivate
    Then I should see the user is deactivated
    When I click the activate link for that user
    Then I should see a reactivate user confirmation modal
    When I confirm reactivate
    Then I should see the user is reactivated
