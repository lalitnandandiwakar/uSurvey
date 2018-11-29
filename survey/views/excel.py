import csv
from StringIO import StringIO
from rq import get_current_job
import json
from datetime import datetime
from django_rq import job, get_scheduler
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseNotFound
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.cache import cache
from survey.utils.zip import InMemoryZip
from survey.forms.filters import SurveyBatchFilterForm
from survey.forms.aggregates import InterviewerReportForm
from survey.models import Survey
from survey.models import Batch
from survey.models import LocationType
from survey.services.results_download_service import ResultsDownloadService, ResultComposer
from survey.utils.views_helper import contains_key
from survey.forms.enumeration_area import LocationsFilterForm


@job('email')
def send_mail(composer):
    composer.send_mail()

#
# @login_required
# @permission_required('auth.can_view_aggregates')
# def download_results(request, batch_id):
#     redis_key = settings.DOWNLOAD_CACHE_KEY % {'user_id': request.user.id, 'batch_id': batch_id}
#     download = cache.get(redis_key)
#     if download:
#         response = HttpResponse(content_type='text/csv')
#         response[
#             'Content-Disposition'] = 'attachment;\
#             filename="%s.csv"' % download['filename']
#         writer = csv.writer(response)
#         data = download['data']
#         #contents = data[0]
#         for row in data:
#             writer.writerow(row)
#         return response
#     else:
#         return HttpResponseNotFound()


@login_required
@permission_required('auth.can_view_aggregates')
def download(request):
    request_data = request.GET if request.method == 'GET' else request.POST
    survey_batch_filter_form = SurveyBatchFilterForm(data=request_data)
    locations_filter = LocationsFilterForm(data=request_data)
    last_selected_loc = locations_filter.last_location_selected
    if request_data and request_data.get('action'):
        survey_batch_filter_form = SurveyBatchFilterForm(data=request_data)
        if survey_batch_filter_form.is_valid():
            batch = survey_batch_filter_form.cleaned_data['batch']
            survey = survey_batch_filter_form.cleaned_data['survey']
            multi_option = \
                survey_batch_filter_form.cleaned_data['multi_option']
            restricted_to = None
            if last_selected_loc:
                restricted_to = [last_selected_loc, ]
            if request_data.get('action') == 'Email Spreadsheet':
                composer = ResultComposer(
                    request.user,
                    ResultsDownloadService(
                        batch,
                        survey=survey,
                        restrict_to=restricted_to,
                        multi_display=multi_option))
                send_mail.delay(composer)
                messages.warning(
                    request, "Email would be sent to\
                        you shortly. This could take a while.")
            else:
                download_service = ResultsDownloadService(
                    batch,
                    survey=survey,
                    restrict_to=restricted_to,
                    multi_display=multi_option)
                file_name = '%s%s' % ('%s-%s-' % (
                    last_selected_loc.type.name,
                    last_selected_loc.name) if last_selected_loc else '',
                    batch.name if batch else survey.name)
                reports_df = download_service.generate_interview_reports()
                response = HttpResponse(content_type='application/zip')
                string_buf = StringIO()
                reports_df.to_csv(string_buf, columns=reports_df.columns[1:])
                string_buf.seek(0)
                file_contents = string_buf.read()
                string_buf.close()
                zip_file = InMemoryZip()
                zip_file = zip_file.append("%s.csv" % file_name, file_contents)
                response['Content-Disposition'] = 'attachment;\
                    filename=%s.zip' % file_name
                response.write(zip_file.read())
                # exclude interview id
                if not request.is_ajax():
                    messages.info(request, "Download successfully downloaded")
                return response
    loc_types = LocationType.in_between()
    return render(request,
                  'aggregates/download_excel.html',
                  {'survey_batch_filter_form': survey_batch_filter_form,
                   'locations_filter': locations_filter,
                   'export_url': '%s?%s' % (reverse('excel_report'),
                                            request.META['QUERY_STRING']),
                   'location_filter_types': loc_types})


@login_required
@permission_required('auth.can_view_aggregates')
def _list(request):
    surveys = Survey.objects.order_by('name')
    batches = Batch.objects.order_by('order')
    return render(request, 'aggregates/download_excel.html',
                  {'batches': batches, 'surveys': surveys})


@login_required
@permission_required('auth.can_view_aggregates')
def completed_interviewer(request):
    batch = None
    survey = None
    params = request.POST or request.GET
    if contains_key(params, 'survey'):
        survey = Survey.objects.get(id=params['survey'])
    if contains_key(params, 'batch'):
        batch = Batch.objects.get(id=params['batch'])
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="interviewer.csv"'
    header = ['Interviewer', 'Access Channels']
    header.extend(LocationType.objects.exclude(
        name__iexact='country').values_list('name', flat=True))
    data = [header]
    data.extend(survey.generate_completion_report(batch=batch))
    writer = csv.writer(response)
    for row in data:
        writer.writerow(row)
    return response


@permission_required('auth.can_view_aggregates')
def interviewer_report(request):
    if request.GET and request.GET.get('action'):
        return completed_interviewer(request)
    report_form = InterviewerReportForm(request.GET)
    return render(request, 'aggregates/download_interviewer.html',
                  {'report_form': report_form, })
