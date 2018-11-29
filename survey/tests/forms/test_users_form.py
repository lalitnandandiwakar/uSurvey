from django.test import TestCase
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test.client import RequestFactory, Client
from django.core.urlresolvers import reverse
from survey.forms.users import *
from survey.forms.password_mgt import uSurveyPasswordResetForm
from survey.models.users import UserProfile


class UserFormTest(TestCase):

    def setUp(self):
        self.form_data = {
            'username': 'rajnii',
            'password1': 'kant',
            'password2': 'kant',
            'last_name': 'Rajni',
            'email': 'raj@ni.kant',
            'mobile_number': '791234567',
        }
        self.form_data1 = {
            'username': 'rajniis',
            'password1': 'kants',
            'password2': 'kants',
            'last_name': 'Rajnis',
            'email': 'raj@ni.kants',
            'mobile_number': '791204567',
        }

    def test_valid(self):
        data1 = {
            'username': 'rajniiss',
            'password1': 'kantss',
            'password2': 'kantss',
            'last_name': 'Rajniss',
            'email': 'raj@ni.kantss',
            'mobile_number': '791204563',
        }

        user_form = UserForm(data1)
        self.assertTrue(user_form.is_valid())
        user = user_form.save()
        self.failUnless(user.id)
        user_retrieved = User.objects.get(last_name='Rajniss')
        self.assertEqual(user_retrieved, user)
        user_profile = UserProfile.objects.filter(user=user)
        self.failUnless(user_profile)
        self.assertEquals(
            user_profile[0].mobile_number, data1['mobile_number'])

    def test_number_of_digits_in_mobile_number(self):
        form_data = self.form_data
        number_of_length_greater_than_9 = 1234567555890
        form_data['mobile_number'] = number_of_length_greater_than_9
        user_form = UserForm(form_data)
        # self.assertFalse(user_form.is_valid())
        message = "Ensure this value has at most 12 characters (it has 13)."
        self.assertEquals(user_form.errors['mobile_number'], [message])

    def test_email_already_used(self):
        form_data = self.form_data
        user = User.objects.create(email=form_data['email'])
        user_form = UserForm(form_data)
        self.assertFalse(user_form.is_valid())
        message = "This email already exist with: "
        self.assertEquals(user_form.errors['email'], [message])

    def test_clean_email_when_editing_a_user(self):
        form_data = self.form_data
        user = User.objects.create(
            username=form_data['username'], email=form_data['email'])
        user_form = UserForm(form_data, instance=user)
        self.assertTrue(user_form.is_valid())

    def test_mobile_number_already_used(self):
        form_data = self.form_data
        user = User.objects.create(username='some_other_name')
        userprofile = UserProfile.objects.create(
            user=user, mobile_number=form_data['mobile_number'])
        user_form = UserForm(form_data)
        self.assertFalse(user_form.is_valid())
        message = "This mobile_number already exist with: some_other_name"
        self.assertEquals(user_form.errors['mobile_number'], [message])

    def test_clean_mobile_number_when_editing_a_user(self):
        form_data = self.form_data
        user = User.objects.create(username=form_data['username'])
        userprofile = UserProfile.objects.create(
            user=user, mobile_number=form_data['mobile_number'])
        user_form = UserForm(form_data, instance=user, initial={
                             'mobile_number': form_data['mobile_number']})
        self.assertTrue(user_form.is_valid())

    def test_clean_username_no_duplicates_on_create(self):
        form_data = self.form_data
        user = User.objects.create(username=form_data['username'])
        user_form = UserForm(form_data)
        self.assertFalse(user_form.is_valid())
        message = "A user with that username already exists."
        self.assertEquals(user_form.errors['username'], [message])

    def test_clean_user_name_when_editing_a_user(self):
        form_data = self.form_data
        user = User.objects.create(username=form_data['username'])
        user_form = UserForm(form_data, instance=user)
        self.assertTrue(user_form.is_valid())

    def test_clean_confirm_password(self):
        form_data = self.form_data
        form_data['password2'] = 'tank'
        user_form = UserForm(form_data)
        self.assertFalse(user_form.is_valid())
        message = "The two password fields didn't match."
        self.assertEquals(user_form.errors['password2'], [message])
        form_data['password2'] = form_data['password1']
        user_form = UserForm(form_data)
        self.assertTrue(user_form.is_valid())


class EditUserFormTest(TestCase):

    def setUp(self):
        self.user_data = {
            'username': 'rajnii',
            'last_name': 'Rajni',
            'email': 'raj@ni.kant',
        }
        self.initial = {'mobile_number': '791234567'}
        self.user_to_be_edited = User.objects.create(**self.user_data)
        self.profile = UserProfile.objects.create(
            user=self.user_to_be_edited, mobile_number=self.initial['mobile_number'])

    def test_valid(self):
        user_data = self.user_data
        user_data['last_name'] = 'Rajniii'
        form_data = dict(user_data, **self.initial)
        user_form = EditUserForm(data=form_data, user=self.user_to_be_edited,
                                 instance=self.user_to_be_edited, initial=self.initial)
        self.assertTrue(user_form.is_valid())
        user = user_form.save()
        self.failUnless(user.id)
        user_retrieved = User.objects.get(**user_data)
        self.assertEqual(user_retrieved, user)
        user_profile = UserProfile.objects.filter(user=user)
        self.failUnless(user_profile)
        self.assertEquals(
            user_profile[0].mobile_number, form_data['mobile_number'])

    def test_email_already_used(self):
        user_data = self.user_data
        form_data = dict(user_data, **self.initial)
        some_email = 'haha@ha.ha'
        form_data['email'] = some_email
        other_user = User.objects.create(email=some_email)
        user_form = EditUserForm(data=form_data, user=self.user_to_be_edited,
                                 instance=self.user_to_be_edited, initial=self.initial)
        self.assertFalse(user_form.is_valid())
        message = "This email already exist with: "
        self.assertEquals(user_form.errors['email'], [message])

    def test_mobile_number_already_used(self):
        user_data = self.user_data
        form_data = dict(user_data, **self.initial)
        some_number = '111111111'
        form_data['mobile_number'] = some_number
        other_user = User.objects.create(username='some_other_name')
        userprofile = UserProfile.objects.create(
            user=other_user, mobile_number=form_data['mobile_number'])
        user_form = EditUserForm(data=form_data, user=self.user_to_be_edited,
                                 instance=self.user_to_be_edited, initial=self.initial)
        self.assertFalse(user_form.is_valid())
        message = "This mobile_number already exist with: some_other_name"
        self.assertEquals(user_form.errors['mobile_number'], [message])

    def test_clean_username_should_not_work_if_user_uses_other_existing_usernames_ie_no_changing_other_people_accounts(self):
        user_data = self.user_data
        form_data = dict(user_data, **self.initial)
        existing_username = 'some_other_existing_username'
        other_user, b = User.objects.get_or_create(username=existing_username)
        form_data['username'] = existing_username
        user_form = EditUserForm(data=form_data, user=self.user_to_be_edited,
                                 instance=self.user_to_be_edited, initial=self.initial)
        self.assertFalse(user_form.is_valid())
        message = "A user with that username already exists."
        self.assertEquals(user_form.errors['username'], [message])

    def create_admin_user(self):
        raj = User.objects.create_user(
            username='Rajni', email='rajni@kant.com', password='I_Rock')
        some_group = Group.objects.create(name='some group')
        auth_content = ContentType.objects.get_for_model(Permission)
        permission, out = Permission.objects.get_or_create(
            codename='can_view_users', content_type=auth_content)
        some_group.permissions.add(permission)
        some_group.user_set.add(raj)
        return raj, some_group

    def test_user_can_view_users_permission_can_edit_groups(self):
        raj, some_group = self.create_admin_user()
        form_data = dict(self.user_data, **self.initial)
        form_data['groups'] = [str(some_group.id)]
        user_form = EditUserForm(
            data=form_data, user=raj, instance=self.user_to_be_edited, initial=self.initial)
        self.assertTrue(user_form.is_valid())
        self.assertIn('groups', user_form.fields.keys())

    def test_empty_password_is_valid(self):
        EMPTY = ''
        user_data = self.user_data
        user_data['last_name'] = 'Rajniii'
        user_data['password'] = EMPTY
        user_data['confirm_password'] = EMPTY
        form_data = dict(user_data, **self.initial)
        raj, some_group = self.create_admin_user()
        user_form = EditUserForm(
            data=form_data, user=raj, instance=self.user_to_be_edited, initial=self.initial)
        self.assertTrue(user_form.is_valid())

    def test_empty_password_does_not_change_password(self):
        EMPTY = ''
        user_data = self.user_data
        user_data['last_name'] = 'Rajniii'
        user_data['password'] = EMPTY
        user_data['confirm_password'] = EMPTY
        form_data = dict(user_data, **self.initial)
        raj, some_group = self.create_admin_user()
        user_form = EditUserForm(
            data=form_data, user=raj, instance=self.user_to_be_edited, initial=self.initial)
        user_form.is_valid()
        user = user_form.save()
        self.failUnless(user.id)
        del user_data['password']
        del user_data['confirm_password']
        user_retrieved = User.objects.get(**user_data)
        self.assertEqual(user_retrieved, user)
        self.assertEqual(self.user_to_be_edited.password,
                         user_retrieved.password)

    def test_mismatching_passwords_is_invalid(self):
        user_data = self.user_data
        user_data['last_name'] = 'Rajniii'
        user_data['password'] = 'something'
        user_data['confirm_password'] = 'something else'
        form_data = dict(user_data, **self.initial)
        raj, some_group = self.create_admin_user()
        user_form = EditUserForm(
            data=form_data, user=raj, instance=self.user_to_be_edited, initial=self.initial)
        self.assertFalse(user_form.is_valid())
        message = "passwords must match."
        self.assertEquals(user_form.errors['confirm_password'], [message])

    def test_valid_password_changes_user_password(self):
        SOME_PASSWORD = '@yo.yo'
        user_data = self.user_data
        user_data['last_name'] = 'Rajniii'
        user_data['password'] = SOME_PASSWORD
        user_data['confirm_password'] = SOME_PASSWORD
        form_data = dict(user_data, **self.initial)
        raj, some_group = self.create_admin_user()
        user_form = EditUserForm(
            data=form_data, user=raj, instance=self.user_to_be_edited, initial=self.initial)
        user_form.is_valid()
        user = user_form.save()
        self.failUnless(user.id)
        del user_data['password']
        del user_data['confirm_password']
        user_retrieved = User.objects.get(**user_data)
        self.assertEqual(user_retrieved, user)
        self.assertTrue(user_retrieved.check_password(SOME_PASSWORD))

    def test_non_admin_user_cannot_change_password(self):
        SOME_PASSWD = 'some passwd'
        user_data = self.user_data
        user_data['last_name'] = 'Rajniii'
        user_data['password'] = SOME_PASSWD
        user_data['confirm_password'] = SOME_PASSWD
        form_data = dict(user_data, **self.initial)
        user_form = EditUserForm(data=form_data, user=self.user_to_be_edited,
                                 instance=self.user_to_be_edited, initial=self.initial)
        user_form.is_valid()
        user = user_form.save()
        self.failUnless(user.id)
        del user_data['password']
        del user_data['confirm_password']
        user_retrieved = User.objects.get(**user_data)
        self.assertEqual(user_retrieved, user)
        self.assertEqual(self.user_to_be_edited.password,
                         user_retrieved.password)
        self.assertTrue(user_retrieved.check_password(SOME_PASSWD))


class UserProfileFormTest(TestCase):

    def setUp(self):
        self.form_data = {
            'mobile_number': '791234567',
        }
        self.client = Client()
        self.client.login(username='demo8', password='demo8')

    def test_valid(self):
        user_profile_form = UserProfileForm(self.form_data)
        self.assertTrue(user_profile_form.is_valid())
        user = User.objects.create(username='rajni', password='kant')
        user_profile_form.instance.user = user
        user_profile = user_profile_form.save()
        self.failUnless(user_profile.id)
        user_profile_retrieved = UserProfile.objects.get(user=user)
        self.assertEqual(user_profile_retrieved, user_profile)

    def test_password_reset_form(self):
        data = {
            'username': 'rajniiss',
            'password1': 'kantss',
            'password2': 'kantss',
            'last_name': 'Rajniss',
            'email': 'raj@ni.kantss',
            'mobile_number': '791204563',
        }

        user_form = UserForm(data)
        self.assertTrue(user_form.is_valid())
        user = user_form.save()
        password = 'pet12'
        pdata = {'email': data['email'], }
        url = reverse('password_reset')
        self.client.login(username=data['username'], password=data['password1'])
        response = self.client.post(url, data=pdata)
        self.assertEquals(response.status_code, 302)
        self.assertIn(reverse('email_sent_page'), response.url)
