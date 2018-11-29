#!/usr/bin/env python
__author__ = 'anthony <antsmc2@gmail.com>'
from django.core.cache import cache
from django.conf import settings


PATH_FORMAT = settings.FLOWS_REDIS_PATH_FORMAT


def get_entry(access, key, default=None):
    return cache.get(
        PATH_FORMAT % {
            'np': settings.INTERVIEWER_SESSION_NAMESPACE,
            'access_id': access.id,
            'key': key},
        default)


def set_entry(access, key, value):
    return cache.set(
        PATH_FORMAT % {
            'np': settings.INTERVIEWER_SESSION_NAMESPACE,
            'access_id': access.id,
            'key': key},
        value,
        timeout=settings.ONLINE_SURVEY_TIME_OUT)


def delete_entry(access):
    cancel_path = '%(np)s/%(access_id)s/' % {
        'np': settings.INTERVIEWER_SESSION_NAMESPACE,
        'access_id': access.id}
    cache.delete_pattern('%s*' % cancel_path)
