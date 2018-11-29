from django.utils import timezone
from django.conf import settings
from django.core.validators import MinLengthValidator, MaxLengthValidator, MinValueValidator, MaxValueValidator
from django.db import models
from survey.interviewer_configs import LEVEL_OF_EDUCATION, LANGUAGES, INTERVIEWER_MIN_AGE, INTERVIEWER_MAX_AGE
from survey.models.base import BaseModel
from survey.models.access_channels import USSDAccess, ODKAccess, InterviewerAccess
from survey.models.locations import Location
from survey.models.interviews import Interview
import random
from django.core.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from survey.utils.sms import send_sms


def validate_min_date_of_birth(value):
    if relativedelta(timezone.now().date(), value).years < INTERVIEWER_MIN_AGE:
        raise ValidationError(
            'interviewers must be at most %s years' % INTERVIEWER_MIN_AGE)


def validate_max_date_of_birth(value):
    if relativedelta(timezone.now().date(), value).years > INTERVIEWER_MAX_AGE:
        raise ValidationError(
            'interviewers must not be at more than %s years' %
            INTERVIEWER_MAX_AGE)


class Interviewer(BaseModel):
    MALE = '1'
    FEMALE = '0'
    LEVEL_OF_EDUCATION_CHOICES = LEVEL_OF_EDUCATION
    LANGUAGES_CHOICES = LANGUAGES
    name = models.CharField(max_length=100)
    gender = models.CharField(default=MALE, verbose_name="Gender", choices=[(MALE, "M"), (FEMALE, "F")],
                              max_length=10)
#     age = models.PositiveIntegerField(validators=[MinValueValidator(18), MaxValueValidator(50)], null=True)
    date_of_birth = models.DateField(
        null=True,
        validators=[
            validate_min_date_of_birth,
            validate_max_date_of_birth])
    level_of_education = models.CharField(
        max_length=100,
        null=True,
        choices=LEVEL_OF_EDUCATION,
        blank=False,
        default='Primary',
        verbose_name="Education")
    is_blocked = models.BooleanField(default=False)
    ea = models.ForeignKey('EnumerationArea', null=True,        # shall use this to track the interviewer present ea
                           related_name="interviewers", verbose_name='Enumeration Area', blank=True,
                           on_delete=models.SET_NULL)  # reporting mostly
    language = models.CharField(
        max_length=100,
        null=True,
        choices=LANGUAGES,
        blank=False,
        default='English',
        verbose_name="Preferred language")
    weights = models.FloatField(default=0, blank=False)

    class Meta:
        app_label = 'survey'
        ordering = ('modified', 'created')

    def __unicode__(self):
        return self.name

    @property
    def assigned_eas(self):
        return ','.join(self.assignments.filter(status=SurveyAllocation.PENDING
                                                ).values_list('allocation_ea__name', flat=True))

    @property
    def unfinished_assignments(self):
        return self.assignments.filter(status=SurveyAllocation.PENDING)

    @property
    def non_response_eas(self):
        eas = set()
        for assignment in self.unfinished_assignments:
            survey = assignment.survey
            ea = assignment.allocation_ea
            for batch in survey.batches.all():
                if ea in batch.non_response_eas:
                    eas.add(ea)
        return eas

    @property
    def present_interviews(self):
        return self.interviews.filter(
            ea__in=[a.allocation_ea for a in self.unfinished_assignments]).count()

    @property
    def age(self):
        return relativedelta(timezone.now().date(), self.date_of_birth).years

    def completed_batch_or_survey(self, survey, batch):
        """This method is old, might not be supported in future versions"""
        if survey and not batch:
            return self.interviews.filter(survey=survey).exists()
        return self.interviews.filter(survey=survey, question_set=batch).exists()

    def locations_in_hierarchy(self):
        assignments = self.assignments
        if assignments.exists():
            ea = assignments.last().allocation_ea
            return ea.locations.last().get_ancestors(
                include_self=True).exclude(
                parent__isnull=True)
        else:
            Location.objects.none()

    @property
    def ussd_access(self):
        return USSDAccess.objects.filter(interviewer=self)

    @property
    def access_ids(self):
        accesses = self.intervieweraccess.all()
        ids = []
        if accesses.exists():
            ids = [acc.user_identifier for acc in accesses]
        return ids

    @property
    def odk_access(self):
        return ODKAccess.objects.filter(interviewer=self)

    def get_ussd_access(self, mobile_number):
        return USSDAccess.objects.get(
            interviewer=self, user_identifier=mobile_number)

    def get_odk_access(self, identifier):
        return ODKAccess.objects.get(
            interviewer=self, user_identifier=identifier)

    def has_survey(self):
        return self.assignments.filter(
            status=SurveyAllocation.PENDING).count() > 0

    @property
    def has_access(self):
        return self.intervieweraccess.filter(is_active=True).exists()

    @classmethod
    def sms_interviewers_in_locations(cls, locations, text):
        interviewers = []
        for location in locations:
            interviewers.extend(Interviewer.objects.filter(
                ea__locations__in=location.get_leafnodes(True)))
        # send(text, interviewers)

    def allocated_surveys(self):
        return self.assignments.filter(
            status=SurveyAllocation.PENDING,
            allocation_ea=self.ea)

    def survey_name(self):
        assignment = self.unfinished_assignments.first()
        survey_name = ''
        if assignment:
            survey_name = assignment.survey.name
        return survey_name


class SurveyAllocation(BaseModel):
    LISTING = 1
    SURVEY = 2
    PENDING = 0
    COMPLETED = 1
    DEALLOCATED = 2
    interviewer = models.ForeignKey(Interviewer, related_name='assignments')
    survey = models.ForeignKey('Survey', related_name='work_allocation')
    allocation_ea = models.ForeignKey(
        'EnumerationArea', related_name='survey_allocations')
    stage = models.CharField(max_length=20, choices=[(LISTING, 'LISTING'),
                                                     (SURVEY, 'SURVEY'), ],
                             null=True, blank=True)
    status = models.IntegerField(
        default=PENDING, choices=[
            (PENDING, 'PENDING'), (DEALLOCATED, 'DEALLOCATED'), (COMPLETED, 'COMPLETED')])

    class Meta:
        app_label = 'survey'

    def __unicode__(self):
        return self.allocation_ea.name      # because typically same survey multiple eas

    @classmethod
    def get_allocation(cls, interviewer, count=0):
        """
        This function is just retained for compatibility sake. Shall be removed in time. Be wary about using it
        :param interviewer:
        :param count:
        :return:
        """
        allocation = cls.get_allocation_details(interviewer)
        if allocation:
            return allocation[count].survey

    @classmethod
    def get_allocation_details(cls, interviewer):
        return cls.objects.filter(interviewer=interviewer, status=cls.PENDING).order_by('created')

    def min_eas_is_covered(self, loc):
        pass

    def open_batches(self):
        return [batch for batch in self.survey.batches.order_by('name') if
                batch.is_open_for(self.allocation_ea.locations.all()[0])]

    @classmethod
    def can_start_batch(cls, interviewer, survey=None):
        survey_allocations = interviewer.unfinished_assignments
        if survey:
            survey_allocations = interviewer.unfinished_assignments.filter(survey=survey)
        else:
            survey = survey_allocations.first().survey
        if survey.has_sampling:
            # essentially allocation usually happens with same survey at a time
            completed = filter(
                lambda allocation: allocation.sample_size_reached(),
                survey_allocations)
            return (1.0 * len(completed)) / survey_allocations.count() >= getattr(settings,
                                                                                  'EAS_PERCENT_TO_START_SURVEY', 1.0)
        return True

    def is_valid(self):
        '''
        It's up to users of this class to ensure that interviewer as not been assigned to new ea from allocated one
        :return:
        '''
        return self.status == self.PENDING and self.interviewer.ea == self.allocation_ea

    def sample_size_reached(self):
        from survey.models import ListingSample
        survey = self.survey.preferred_listing or self.survey
        if self.survey.preferred_listing:
            survey = self.survey.preferred_listing
        # more than one interviewer can result in the sample size for that EA
        return len(ListingSample.get_possible_samples(survey, self.survey,
                                                      self.allocation_ea)) >= self.survey.sample_size

