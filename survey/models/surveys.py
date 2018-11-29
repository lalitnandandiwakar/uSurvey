from django.db import models
from django_cloneable import CloneableMixin
from survey.models.base import BaseModel
from survey.models.users import UserProfile


class Survey(CloneableMixin, BaseModel):
    name = models.CharField(max_length=100, unique=True, default='')     # dummy default for smooth migrate
    description = models.CharField(max_length=300, blank=False, null=True)
    has_sampling = models.BooleanField(default=True, verbose_name='Survey Type')
    # next three are only relevant for listing data. I believe it saves
    # unnecessary extra tables to refer to them here
    sample_size = models.PositiveIntegerField(null=False, blank=False, default=10)
    listing_form = models.ForeignKey(
        'ListingTemplate',
        related_name='survey_settings',
        null=True,
        blank=True)
    preferred_listing = models.ForeignKey(
        'Survey',
        related_name='listing_users',
        help_text='Select which survey listing to reuse. '
        'Leave empty for fresh listing',
        null=True,
        blank=True)
    random_sample_label = models.TextField(
        null=True,
        blank=True,
        verbose_name='Randomly selected data label',
        help_text='Include double curly brackets to automatically insert '
        'identifiers from the listing form e.g {{structure_address}}')
    email_group = models.ManyToManyField(
        UserProfile, related_name='email_surveys')
    # random_sample_description = models.TextField()

    class Meta:
        app_label = 'survey'
        ordering = ['name', ]
        permissions = (
            ("view_completed_survey", "Can view Completed interviewers"),
        )

    def __unicode__(self):
        return self.name

    @classmethod
    def save_sample_size(cls, survey_form):
        survey = survey_form.save(commit=False)
        if not survey.has_sampling:
            survey.sample_size = 0
        survey.save()

    @property
    def qsets(self):
        ''' Returns all question sets associated with this survey. This includes all listing and batch questions.
        :return:
        '''
        from survey.models import QuestionSet
        qset_ids = []
        if self.has_sampling:
            if self.listing_form:
                qset_ids.append(self.listing_form.id)
            elif self.preferred_listing:
                qset_ids.append(self.preferred_listing.listing_form.id)
        qset_ids.extend(self.batches.values_list('id', flat=True))
        return QuestionSet.objects.filter(id__in=qset_ids)

    def is_open_for(self, location):
        all_batches = self.batches.all()
        for batch in all_batches:
            if batch.is_open_for(location):
                return True
        return False

    def eas_covered(self):
        return self.interviews.values_list('ea', flat=True).distinct().count()

    def is_open(self):
        """This is to be used in the context of survey batches. Not to be applied for listing"""
        return any([batch.is_open() for batch in self.batches.all()])

    def generate_completion_report(self, batch=None):
        from survey.models.interviewer import Interviewer
        data = []
        all_interviewers = Interviewer.objects.all()
        for interviewer in all_interviewers:
            if interviewer.completed_batch_or_survey(self, batch=batch):
                row = [interviewer.name, ','.join(interviewer.access_ids)]
                if interviewer.ea:
                    row.extend(interviewer.locations_in_hierarchy(
                    ).values_list('name', flat=True))
                data.append(row)
        return data

    def total_interviews(self, qset):
        from survey.models import Interview
        return Interview.objects.filter(
            survey=self, question_set__pk=qset.pk).count()

    def deep_clone(self):
        from survey.models import Batch
        import random
        # first clone this survey
        survey = self.clone(attrs={'name': '%s-copy-%s' % (self.name, random.randrange(1000))})
        # not create survey batches for this one
        for batch in Batch.objects.filter(survey__id=self.id):
            batch.deep_clone(survey=survey)
        return survey


class SurveySampleSizeReached(Exception):
    pass


class BatchCommencement(BaseModel):
    survey = models.ForeignKey(
        Survey, null=True, related_name='commencement_registry')
    ea = models.ForeignKey('EnumerationArea', null=True,
                           related_name='commencement_registry')
