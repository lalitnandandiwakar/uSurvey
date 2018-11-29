# Django settings for mics project.
import os
import sys
from collections import OrderedDict
import ast
import phonenumbers
import pycountry


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
DEBUG = ast.literal_eval(os.getenv('DEBUG', 'False'))
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Anthony Anyanwu', 'antsmc2@gmail.com'),
)

PROJECT_TITLE = 'uSurvey'
COUNTRY = os.getenv('COUNTRY', 'Uganda').upper()

MANAGERS = ADMINS

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": os.getenv('USURVEY_DB', 'postgres'),
        "USER": os.getenv('USURVEY_DB_USER', 'postgres'),
        "PASSWORD": os.getenv('USURVEY_DB_PASS', ''),
        "HOST": os.getenv('USURVEY_DB_HOST', 'localhost'),

    }

}

CACHES = {
    'default': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': [
            '%s:%s' % (REDIS_HOST, REDIS_PORT),
        ],
        'OPTIONS': {
            'DB': 1,
            'PARSER_CLASS': 'redis.connection.HiredisParser',
            'CONNECTION_POOL_CLASS': 'redis.BlockingConnectionPool',
            'CONNECTION_POOL_CLASS_KWARGS': {
                'max_connections': 50,
                'timeout': 500,
            },
            'MAX_CONNECTIONS': 1000,
            'PICKLE_VERSION': -1,
        },
    },
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ['*', ]

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = os.getenv('TIME_ZONE', 'Africa/Kampala')

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = os.path.join(BASE_DIR, 'survey', 'static')

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.

)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

#STATICFILES_STORAGE = 'contrib.storage.my_whitenoise.WhitenoiseErrorSquashingStorage'

# Make this unique, and don't share it with anybody.
SECRET_KEY = os.getenv('USURVEY_SECRET_KEY', '@#D&@*')

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    #     'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.contrib.messages.context_processors.messages",
    "survey.context_processor.context_extras",
    "django.core.context_processors.request",
    'django.core.context_processors.request',
    'responsive.context_processors.device'
)

MIDDLEWARE_CLASSES = [
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
#    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'pagination_bootstrap.middleware.PaginationMiddleware',
    'breadcrumbs.middleware.BreadcrumbsMiddleware',
    'responsive.middleware.ResponsiveMiddleware'
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mics.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'mics.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates"or
    #"C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(BASE_DIR, 'survey', 'templates'),
)

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    #'django_nose',
    #'lettuce.django',
    'django_extensions',
    'pagination_bootstrap',
    'cacheops',
    'survey',
    'mptt',
    'django_rq',
    'django_rq_dashboard',
    'macros',
    'responsive'
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
]


# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

CACHEOPS_REDIS = {
    'host': REDIS_HOST,  # redis-server is on same machine
    'port': REDIS_PORT,        # default redis port
    'db': 1,             # SELECT non-default redis database
                         # using separate redis db or redis instance
                         # is highly recommended
}


CACHE_REFRESH_DURATION = 10800
CACHEOPS = {
    # refresh every 3 hrs
    'survey.point': {'ops': 'all', 'timeout': CACHE_REFRESH_DURATION},
    'survey.questionloop': {'ops': 'all', 'timeout': CACHE_REFRESH_DURATION},
    'survey.questionflow': {'ops': (), 'timeout': CACHE_REFRESH_DURATION},
    'survey.question': {'ops': ('fetch', ), 'timeout': CACHE_REFRESH_DURATION},
    'survey.respondentgroup': {'ops': (), 'timeout': CACHE_REFRESH_DURATION},
    'survey.answer': {'ops': 'all', 'timeout': CACHE_REFRESH_DURATION},
    'survey.numericalanswer': {
        'ops': 'all',
        'timeout': CACHE_REFRESH_DURATION},
    'survey.textanswer': {'ops': 'all', 'timeout': CACHE_REFRESH_DURATION},
    'survey.multichoiceanswer': {
        'ops': 'all',
        'timeout': CACHE_REFRESH_DURATION},
    'survey.odkgeopoint': {'ops': 'all', 'timeout': CACHE_REFRESH_DURATION},
    # refresh every 3 hrs
    'survey.locationtype': {'ops': 'all', 'timeout': CACHE_REFRESH_DURATION},
    # refresh every 3 hrs
    'survey.location': {
        'ops': ('get', ),
        'timeout': CACHE_REFRESH_DURATION},
    # refresh every 3 hrs
    'survey.enumerationarea': {'ops': 'all', 'timeout': CACHE_REFRESH_DURATION},
    # refresh every 3 hrs,
    # 'survey.batch': {'ops': (), 'timeout': CACHE_REFRESH_DURATION},
    # # refresh every 3 hrs,
    # 'survey.survey': {'ops': (), 'timeout': CACHE_REFRESH_DURATION},
    # 'survey.questionset': {'ops': (), 'timeout': CACHE_REFRESH_DURATION},
    'survey.*': {'ops': (), 'timeout': CACHE_REFRESH_DURATION},
    'auth.user': {'ops': (), 'timeout': CACHE_REFRESH_DURATION},
}

# DJANGO-WS CONFIG
WEBSOCKET_URL = '/ws/statusbar'
WS_HEARTBEAT = 3
UPDATE_INTERVAL = 3  # INTERVAL BETWEEN UPDATES IN SECS
# how long downloaded results would cached in secs before discarded
DOWNLOAD_CACHE_DURATION = 1800
DOWNLOAD_CACHE_KEY = '/DOWNLOADS/EXPORT/BATCH/%(user_id)s/%(batch_id)s'

SURVEY_REDIS_KEY = "/usurvey/completion_rates/%(survey_id)s"

#TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

NOSE_ARGS = [
    '--with-coverage',
    # '--keepdb',
    # '--failfast'
    '--cover-package=survey',
    '--verbosity=3',
    # '--quiet',
    # '--pdb',
    #'--processes=4'
]

TABLE_ENTRY_PER_PAGINATION = 10


INSTALLED_BACKENDS = {
    # "HTTP": {
    #     "ENGINE": "rapidsms.backends.database.DatabaseBackend",
    # },
}


PRODUCTION = False

# cookies settings
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 1800
SESSION_SAVE_EVERY_REQUEST = True

# email settings
EMAIL_USE_TLS = True
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_EMAIL_SENDER = os.getenv('DEFAULT_EMAIL_SENDER', EMAIL_HOST_USER)

# odk settings
TOKEN_DEFAULT_SIZE = 5
ODK_DEFAULT_TOKEN = '12345'
SUBMISSION_UPLOAD_BASE = os.path.join(BASE_DIR, 'files', 'submissions')
ANSWER_UPLOADS = os.path.join(BASE_DIR, 'files', 'answerFiles')
TEMP_DIR = os.path.join(BASE_DIR, 'tmp')
ODK_SUBMISSION_SUCCESS_MSG = "Successful submission.\
    Your submission is been Processed"
INTERVIEWER_EXPORT_HEADERS = [
    'assigned_eas',
    'name',
    'age',
    'level_of_education',
    'language',
    'mobile_numbers',
    'odk_id']
QUESTION_EXPORT_HEADERS = OrderedDict([
    ('identifier', 'Question Code'),
    ('text', 'Question Text'),
    ('answer_type', 'Answer Type'),
    ('options', 'Options'),
    ('group', 'Group'),
    ('module', 'Module')
])

USER_EXPORT_HEADERS = OrderedDict([
    ('first_name', 'First Name'),
    ('last_name', 'Last Name'),
    ('username', 'User Name'),
    ('email', 'Email'),
    ('groups__name', 'groups'),
])

ODK_UPLOADED_DATA_BELOW_SAMPLE_SIZE = 'Uploaded Data is below sample size.\
    Ensure to complete enough ' \
        'entries in a single form'
ODK_ERROR_OCCURED = 'An error occurred pls try again'


AGGREGATORS = [('testAggregator', 'testAggregator'), ]
DEFAULT_AGGREGATOR = 'testAggregator'
TWITTER_URL = os.getenv('USURVEY_TWITTER_URL', 'https://twitter.com/unicefuganda')
TWITTER_TOKEN = os.getenv('USURVEY_TWITTER_TOKEN', '')

###USSD config ##
USSD_NEXT = '*'
USSD_PREVIOUS = '#'
USSD_ITEMS_PER_PAGE = 10
USSD_RESTART = '##'
# USSD_STARTER = 'survey.ussd.flows.Start'
USSD_IGNORED_CHARACTERS = "*!#';&"
MAX_DISPLAY_PER_PAGE = 3
DEFAULT_TOTAL_HOUSEHOLDS_IN_EA = 1000
DATE_FORMAT = "%d-%m-%Y"
MOBILE_NUM_MIN_LENGTH = 7       # this is the min digits of phone numbers in national format (excluding leading 0)
MOBILE_NUM_MAX_LENGTH = 12      # this is the max digits of phone numbers in national format (excluding leading 0)
LOOP_QUESTION_REPORT_DEPT = 3  # reports up to 5 question loops
# following setting refers to the URL for loading the map data
SHAPE_FILE_URI = os.getenv('SHAPE_FILE_URI', '/static/map_resources/country_shape_file.json')
# field in the geojson referring to the field name holding the admin divisions polygon
SHAPE_FILE_LOC_FIELD = os.getenv('SHAPE_FILE_LOC_FIELD', 'name:en')
# field refers to the alternative name to look for the polygon in addition to SHAPE_FILE_LOC_FIELD
SHAPE_FILE_LOC_ALT_FIELD = os.getenv('SHAPE_FILE_LOC_ALT_FIELD', 'name')
# starting location of the map. Though map would auto adjust to map center. This field may not have much effect
# must be in format for log lat. see: http://geojson.org/geojson-spec.html
MAP_CENTER = os.getenv('MAP_CENTER', '1.34,32.683525')
# 0 for country level, 1 first level below country, 2 for second level etc.
MAP_ADMIN_LEVEL = int(os.getenv('MAP_ADMIN_LEVEL', 1))
MAP_ZOOM_LEVEL = int(os.getenv('MAP_ZOOM_LEVEL', 7))

USSD_MOBILE_NUMBER_FIELD = 'msisdn'             # for get or post request
USSD_MSG_FIELD = 'ussdRequestString'            # for get or post request
USSD_RESPONSE_FORMAT = 'responseString=%(response)s&action=1'
USSD_TIMEOUT = 180          # timeout in seconds
USSD_MAX_CHARS = 160


RESULT_REFRESH_FREQ = 6
MEMORIZE_TIMEOUT = 120

RQ_QUEUES = {
    'default': {
        'HOST': REDIS_HOST,
        'PORT': REDIS_PORT,
        'DB': 7,
        'DEFAULT_TIMEOUT': 360,
    },
    'results-queue': {
        'HOST': REDIS_HOST,
        'PORT': REDIS_PORT,
        'DB': 7,
        'DEFAULT_TIMEOUT': 360,
    },
    'email': {
        'HOST': REDIS_HOST,
        'PORT': REDIS_PORT,
        'DB': 7,
    },
    'ws-notice': {
        'HOST': REDIS_HOST,
        'PORT': REDIS_PORT,
        'DB': 7,
    },
    'upload_task': {
        'HOST': REDIS_HOST,
        'PORT': REDIS_PORT,
        'DB': 7,
    },
    'odk': {
        'HOST': REDIS_HOST,
        'PORT': REDIS_PORT,
        'DB': 7,
    }
}

# super powers duration in seconds
SUPER_POWERS_DURATION = 1800
SUPER_POWERS_KEY = 'auth:super_powers'

INTERVIEWER_SESSION_NAMESPACE = '//interviewer/'
ONLINE_SURVEY_TIME_OUT = 50000
# the redis key format used for online flows
FLOWS_REDIS_PATH_FORMAT = '/usurvey/online/%(np)s/%(access_id)s/%(key)s'


RESPONSIVE_MEDIA_QUERIES = {
    'small': {
        'verbose_name': ('Small screens'),
        'min_width': None,
        'max_width': 640,
    },
    'medium': {
        'verbose_name': ('Medium screens'),
        'min_width': 641,
        'max_width': 1024,
    },
    'large': {
        'verbose_name': ('Large screens'),
        'min_width': 1025,
        'max_width': 1440,
    },
    'xlarge': {
        'verbose_name': ('XLarge screens'),
        'min_width': 1441,
        'max_width': 1920,
    },
    'xxlarge': {
        'verbose_name': ('XXLarge screens'),
        'min_width': 1921,
        'max_width': None,
    }
}

NON_RESPONSE_REASONS = {
    'No competent respondent': 'No competent respondent',
    'No respondent available': 'No respondent available',
    'Refused': 'Refused',
    'Dwelling vacent / Address not a dwelling': 'Dwelling vacent / Address not a dwelling',
    'Dwelling destroyed': 'Dwelling destroyed',
    'Dwelling not found': 'Dwelling not found',
    'Other': 'Other'
}

LOG_DIR = os.path.join(BASE_DIR, 'logs')

EA_NAME = os.path.join('VERBOSE_EA_NAME', 'Enumeration Area')

##end USSD config ##
# Importing server specific settings

if 'test' in sys.argv:
    DEBUG = True
    COUNTRY = 'Uganda'
    DATABASES = {
       "default": {
           "ENGINE": "django.db.backends.sqlite3",
       }
    }
    FLOWS_REDIS_PATH_FORMAT = '/test/%s' % FLOWS_REDIS_PATH_FORMAT
    for queueConfig in RQ_QUEUES.itervalues():
        queueConfig['ASYNC'] = False
    for key in CACHEOPS:
        CACHE_REFRESH_DURATION = 0
        CACHEOPS[key] = {'ops': (), 'timeout': CACHE_REFRESH_DURATION}



