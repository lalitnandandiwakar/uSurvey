from ordered_set import OrderedSet
from cacheops import invalidate_obj
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Max
from survey.models.locations import Location
from survey.models.surveys import Survey
from survey.models.base import BaseModel
from survey.models.questions import QuestionSet
from survey.models.batch_questions import BatchQuestion
from survey.models.access_channels import InterviewerAccess
# from survey.models.enumeration_area import EnumerationArea


class Batch(QuestionSet):
    order = models.PositiveIntegerField(null=True)
    survey = models.ForeignKey(Survey, null=True, related_name="batches")
    BATCH_IS_OPEN_MESSAGE = "Batch cannot be deleted because it is open in %s."
    BATCH_HAS_ANSWERS_MESSAGE = "Batch cannot be deleted because it has responses."

    @classmethod
    def question_model(cls):
        return BatchQuestion

    class Meta:
        app_label = 'survey'
        ordering = ('modified', 'created')

    def __unicode__(self):
        return "%s" % self.name

    @classmethod
    def index_breadcrumbs(cls, **kwargs):
        breadcrumbs = [
            ('Surveys', reverse('survey_list_page'))
        ]
        if kwargs.get('survey'):
             breadcrumbs.append((kwargs.get('survey'), reverse('batch_index_page', args=(kwargs.get('survey').pk, ))))
        return breadcrumbs

    @classmethod
    def edit_breadcrumbs(cls, **kwargs):
        breadcrumbs = cls.index_breadcrumbs(**kwargs)
        if 'survey' in kwargs or 'qset' in kwargs:
            survey = kwargs.get('survey') or kwargs['qset'].survey
            breadcrumbs.append(
                (survey.name, reverse(
                    'batch_index_page', args=(
                        survey.pk, ))))
        if 'qset' in kwargs:
            breadcrumbs.append((kwargs.get('qset').name, reverse('qset_questions_page',kwargs={'qset_id':kwargs['qset'].id})))
        return breadcrumbs

    def non_response_enabled(self, ea):
        locations = set()
        ea_locations = ea.locations.all()
        if ea_locations:
            map(lambda loc: locations.update(
                loc.get_ancestors(include_self=True)), ea_locations)
        return self.open_locations.filter(
            non_response=True, location__pk__in=[
                location.pk for location in locations]).exists()

    def get_non_response_active_locations(self):
        locations = set()
        locations_register = self.open_locations.filter(non_response=True)
        if locations_register:
            map(lambda reg: locations.update(reg.location.get_descendants(
                include_self=True)), locations_register)
        return locations

    @property
    def non_response_eas(self):
        eas = set()
        locations = self.get_non_response_active_locations()
        map(lambda loc: eas.update(loc.enumeration_areas.all()), locations)
        return eas

    def open_for_location(self, location):
        invalidate_obj(location)
        return self.open_locations.get_or_create(batch=self, location=location)

    def close_for_location(self, location):
        invalidate_obj(location)
        self.open_locations.filter(batch=self, location=location).delete()

    def is_closed_for(self, location):
        # its closed if its closed in any parent loc or self
        locations = location.get_ancestors(include_self=True)
        return self.open_locations.filter(
            location__pk__in=locations).count() == 0

    def is_open_for(self, location):
        return not self.is_closed_for(location)

    def is_applicable(self, house_member):
        return True  # probably might be used later

    def is_open(self):
        return self.open_locations.all().exists()

    @property
    def survey_questions(self):
        return self.flow_questions

    def activate_non_response_for(self, location):
        invalidate_obj(location)
        obj, _ = self.open_locations.get_or_create(batch=self, location=location)
        obj.non_response=True
        obj.save()

    def deactivate_non_response_for(self, location):
        invalidate_obj(location)
        self.open_locations.filter(
            location=location).update(non_response=False)

    def save(self, *args, **kwargs):
        last_order = Batch.objects.aggregate(Max('order'))['order__max']
        self.order = last_order + 1 if last_order else 1
        super(Batch, self).save(*args, **kwargs)
        if self.pk:
            from survey.models import SurveyParameterList
            SurveyParameterList.update_parameter_list(self)

    @property
    def all_questions(self):
        """This is might be different from the flow questions because it might have group paramater questions if present
        :return:
        """
        if self.parameter_list:
            questions = OrderedSet(self.parameter_list.parameters)
        else:
            questions = OrderedSet()
        map(lambda q: questions.add(q), self.flow_questions)
        return questions

    @property
    def g_first_question(self):
        questions = self.all_questions
        if questions:
            return questions[0]


class BatchLocationStatus(BaseModel):
    batch = models.ForeignKey(Batch, null=True, related_name="open_locations")
    location = models.ForeignKey(
        Location, null=True, related_name="open_batches")
    non_response = models.BooleanField(null=False, default=False)


class BatchChannel(BaseModel):
    ACCESS_CHANNELS = [(name, name)
                       for name in InterviewerAccess.access_channels()]
    batch = models.ForeignKey(Batch, related_name='baccess_channels')
    channel = models.CharField(max_length=100, choices=ACCESS_CHANNELS)

    class Meta:
        app_label = 'survey'
        unique_together = ('batch', 'channel')
