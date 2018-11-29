import numpy as np
import pandas as pd
from django.core.mail import EmailMessage
from django.conf import settings
from django.db.models.sql.datastructures import EmptyResultSet
from survey.models import (
    Location,
    LocationType,
    Answer,
    MultiChoiceAnswer,
    MultiSelectAnswer,
    NumericalAnswer,
    QuestionOption,
    Interview,
    QuestionSet,
    Survey,
    EnumerationArea)
from survey.utils.query_helper import to_df
from cacheops import cached_as
from datetime import datetime
import StringIO


class ResultComposer:

    def __init__(self, user, results_download_service):
        self.results_download_service = results_download_service
        self.user = user

    def send_mail(self):
        attachment_name = '%s.csv' % (
            self.results_download_service.batch.name
            if self.results_download_service.batch else
            self.results_download_service.survey.name)
        subject = 'Completion report for %s' % attachment_name
        text = 'Completion report for %s. Date: %s' % (
            attachment_name, datetime.now())
        mail = EmailMessage(subject, text, settings.DEFAULT_EMAIL_SENDER, [
                            self.user.email, ])
        results_df = self.results_download_service.get_interview_answers()
        f = StringIO.StringIO()
        # exclude interview id
        data = results_df.to_csv(f, columns=results_df.columns[1:])
        f.seek(0)
        mail.attach(attachment_name, f.read(), 'text/csv')
        f.close()
        sent = mail.send()


class ResultsDownloadService(object):
    AS_TEXT = 1
    AS_LABEL = 0
    answers = None
    page_start = 0
    items_per_page = None

    def __init__(self, batch, survey=None, restrict_to=None, interviews=None, multi_display=AS_TEXT, page_index=0,
                 items_per_page=None, follow_ref=True):
        self.batch = batch
        self.survey = survey
        self.locations = []
        self.follow_ref = follow_ref
        if items_per_page:
            self.page_start = page_index * items_per_page
            self.items_per_page = items_per_page
        if interviews is None:
            interviews = Interview.objects.all()
        kwargs = {'question_set__pk': batch.pk}
        if survey:
            kwargs['survey'] = survey
        if restrict_to:
            map(lambda loc: self.locations.extend(
                loc.get_leafnodes(include_self=True)), restrict_to)
            kwargs['ea__locations__in'] = self.locations
        self.interviews = interviews.filter(**kwargs)
        self.multi_display = int(multi_display)

    def get_interview_answers(self):
        cache_filters = []
        if self.batch:
            cache_filters.append(QuestionSet.objects.get(id=self.batch.id))
        if self.survey:
            cache_filters.append(Survey.objects.get(id=self.survey.id))
        if self.locations:
            cache_filters.append(EnumerationArea.objects.filter(locations__in=self.locations))
        else:
            cache_filters.append(self.interviews)

        @cached_as(*cache_filters, extra=(self.page_start, self.items_per_page))
        def _get_interview_answers():
            interview_list_args = [
                'created',
                'closure_date',
                'ea__locations__name',
                'ea__name',
                'interviewer__name',
                'id',
            ]
            if self.follow_ref:
                interview_list_args.append('interview_reference__id')
            parent_loc = 'ea__locations'
            for i in range(LocationType.objects.count() - 2):
                parent_loc = '%s__parent' % parent_loc
                interview_list_args.insert(2, '%s__name' % parent_loc)      # insert after closure date
            header_names = ['Uploaded', 'Completion Date']
            location_names = list(LocationType.objects.get(parent__isnull=True
                                                           ).get_descendants(include_self=False
                                                                             ).values_list('name', flat=True))
            header_names.extend(location_names)
            header_names.extend(['EA', 'interviewer__name', 'id'])
            if self.follow_ref:
                header_names.append('interview_reference_id')
            interview_query_args = list(interview_list_args)
            interview_queryset = self.interviews.values_list(*interview_query_args)
            if self.items_per_page:
                interview_queryset = interview_queryset[self.page_start: self.page_start + self.items_per_page]
            try:
                interviews_df = to_df(interview_queryset, date_cols=['created', 'closure_date'])
            except EmptyResultSet:
                interviews_df = pd.DataFrame(columns=interview_query_args)
            interviews_df.columns = header_names
            reports_df = interviews_df
            if self.follow_ref:
                good_ref_interviews = interviews_df[interviews_df['interview_reference_id'].notnull()]
                if not good_ref_interviews.empty:   # only do the following when there is a value here
                    ref_answers_report_df = self._get_answer_df(good_ref_interviews['interview_reference_id'],
                                                                result_id_label='interview_reference_id')
                    reports_df = reports_df.join(ref_answers_report_df, on='interview_reference_id', how='outer')
            answers_report_df = self._get_answer_df(interviews_df['id'])
            reports_df = reports_df.join(answers_report_df, on='id', how='outer')
            # adding uploaded and completion date after other columns
            report_columns = list(reports_df.columns[2:]) + ['Uploaded', 'Completion Date']
            other_sort_fields = [identifier for identifier in
                                 self.batch.auto_fields.values_list('identifier',
                                                                    flat=True) if identifier in header_names]
            reports_df = reports_df.sort_values(['Uploaded', 'Completion Date'] + location_names + other_sort_fields)
            reports_df = reports_df[report_columns]
            # now clean up
            if 'id' in reports_df.columns:
                del reports_df['id']
            if 'interview_reference_id' in reports_df.columns:
                del reports_df['interview_reference_id']
            try:
                reports_df.Created = reports_df.Created.dt.tz_convert(settings.TIME_ZONE)
            except BaseException:
                pass        # just try to convert if possible. Else leave it
            reports_df.index += self.page_start
            return reports_df
        return _get_interview_answers()

    def _get_answer_df(self, interview_ids, result_id_label='id'):
        answer_query_args = ['interview__id', 'identifier', ]
        value = 'as_text'
        if self.multi_display == self.AS_LABEL:
            value = 'as_value'
        answer_query_args.append(value)
        answers_queryset = Answer.objects.filter(
            interview__id__in=interview_ids).values_list(
            *answer_query_args)
        try:
            answer_columns = [result_id_label, 'identifier', value]
            answers_df = to_df(answers_queryset)
            answers_df.columns = [result_id_label, 'identifier', value]
        except EmptyResultSet:
            answers_df = pd.DataFrame(columns=answer_columns)
        # not get pivot table of interview_id, identifier and question value
        return answers_df.pivot(index=result_id_label, columns='identifier', values=value)

    def generate_interview_reports(self):
        return self.get_interview_answers()
