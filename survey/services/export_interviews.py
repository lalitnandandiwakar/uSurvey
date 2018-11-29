from survey.models import Interviewer, LocationType
import operator


class ExportInterviewersService:

    def __init__(self, export_fields):
        self.interviewers = Interviewer.objects.all()
        self.HEADERS = export_fields

    def formatted_responses(self):
        _formatted_responses = []
        headers = [loc_type.name.upper()
                   for loc_type in LocationType.in_between()]
        headers.extend([entry.upper() for entry in self.HEADERS])
        _formatted_responses.append(','.join(headers))
        interviewer_records = []
        for interviewer in self.interviewers:
            info = {}
            info['mobile_numbers'] = ','.join(
                [access.user_identifier for access in interviewer.ussd_access])
            info['odk_id'] = ','.join(
                [access.user_identifier for access in interviewer.odk_access])
            row = [str(loc.name) for loc in interviewer.ea.parent_locations()]
            row.extend(['"%s"' % str(getattr(interviewer, entry,
                                             info.get(entry, ''))) for entry in self.HEADERS])
            interviewer_records.append(row)
        interviewer_records = sorted(
            interviewer_records, key=operator.itemgetter(*range(len(headers))))
        _formatted_responses.extend(
            map(lambda row: ','.join(row), interviewer_records))
        return _formatted_responses
