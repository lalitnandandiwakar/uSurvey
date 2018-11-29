from survey.models import BaseModel
from django.db import models


class QuestionModule(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)

    def remove_related_questions(self):
        self.question_templates.all().delete()

    def __unicode__(self):
        return self.name
