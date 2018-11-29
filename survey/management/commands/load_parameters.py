__author__ = 'anthony'
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Permission, Group
from django.contrib.contenttypes.models import ContentType
from survey.models import AnswerAccessDefinition, AutoResponse, NumericalAnswer, TextAnswer, \
    MultiChoiceAnswer, MultiSelectAnswer, ImageAnswer, GeopointAnswer, DateAnswer, AudioAnswer, VideoAnswer, \
    USSDAccess, ODKAccess, WebAccess


class Command(BaseCommand):
    help = 'Creates default parameters'

    def handle(self, *args, **kwargs):
        #self.stdout.write('Creating permissions....')
        content_type = ContentType.objects.get_for_model(User)
        can_enter_data, _ = Permission.objects.get_or_create(
            codename='can_enter_data', name='Can enter data', content_type=content_type)
        can_view_batches, _ = Permission.objects.get_or_create(
            codename='can_view_batches', name='Can view Batches', content_type=content_type)
        can_view_interviewer, _ = Permission.objects.get_or_create(
            codename='can_view_interviewers', name='Can view Interviewers', content_type=content_type)
        can_view_aggregates, _ = Permission.objects.get_or_create(
            codename='can_view_aggregates', name='Can view Aggregates', content_type=content_type)
        can_view_com_surveys, _ = Permission.objects.get_or_create(
            codename='view_completed_survey', name='Can view Completed Surveys', content_type=content_type)
        can_view_households, _ = Permission.objects.get_or_create(
            codename='can_view_househs', name='Can view Households', content_type=content_type)
        can_view_locations, _ = Permission.objects.get_or_create(
            codename='can_view_locations', name='Can view Locations', content_type=content_type)
        can_view_users, _ = Permission.objects.get_or_create(
            codename='can_view_users', name='Can view Users', content_type=content_type)
        can_receive_email, _ = Permission.objects.get_or_create(
            codename='can_receive_email', name='Can Receive Email', content_type=content_type)
        can_have_super_powers, _ = Permission.objects.get_or_create(
            codename='can_have_super_powers', name='Can Have Super Powers', content_type=content_type)

        #self.stdout.write('Permissions created.')
        #self.stdout.write('Creating some groups...')
        group, _ = Group.objects.get_or_create(name='Administrator')
        group.permissions.add(can_enter_data)
        group.permissions.add(can_view_aggregates)
        group.permissions.add(can_view_batches)
        group.permissions.add(can_view_com_surveys)
        group.permissions.add(can_view_households)
        group.permissions.add(can_view_interviewer)
        group.permissions.add(can_view_locations)
        group.permissions.add(can_view_users)
        group.permissions.add(can_receive_email)
        group.permissions.add(can_have_super_powers)
        group, _ = Group.objects.get_or_create(name='Researcher')
        group.permissions.add(can_enter_data)
        group.permissions.add(can_view_aggregates)
        group.permissions.add(can_view_batches)
        group.permissions.add(can_view_com_surveys)
        group.permissions.add(can_view_households)
        group.permissions.add(can_view_interviewer)
        group.permissions.add(can_view_locations)
        group.permissions.add(can_receive_email)
        group, _ = Group.objects.get_or_create(name='Supervisor')
        group.permissions.add(can_enter_data)
        group.permissions.add(can_view_aggregates)
        group.permissions.add(can_view_batches)
        group.permissions.add(can_view_com_surveys)
        group.permissions.add(can_view_households)
        group.permissions.add(can_view_locations)
        group, _ = Group.objects.get_or_create(name='Data collector')
        group.permissions.add(can_enter_data)
        group.permissions.add(can_view_batches)
        group, _ = Group.objects.get_or_create(name='Viewer')
        group.permissions.add(can_view_aggregates)
        group.permissions.add(can_view_batches)
        group.permissions.add(can_view_com_surveys)
        group.permissions.add(can_receive_email)
        group, _ = Group.objects.get_or_create(name='Data Email Reports')
        group.permissions.add(can_receive_email)
        #self.stdout.write('Created groups.')
        #self.stdout.write('Creating answer definition... ')
        # ussd definition
        AnswerAccessDefinition.reload_answer_categories()
        #self.stdout.write('Successfully imported!')
