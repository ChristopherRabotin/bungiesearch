import os
import sys


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
# Make sure the copy of seeker in the directory above this one is used.
sys.path.insert(0, BASE_DIR)
SECRET_KEY = 'cookies_are_delicious_delicacies'
INSTALLED_APPS = (
    'bungiesearch',
    'core',
)
ROOT_URLCONF = 'urls'
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True
DEBUG = True
MIDDLEWARE_CLASSES = ()
DEFAULT_INDEX_TABLESPACE = ''
BUNGIESEARCH = {
                'URLS': ['localhost'],
                'INDICES': {'bungiesearch_demo': 'core.search_indices',
                            'bungiesearch_demo_bis': 'core.search_indices_bis'},
                'ALIASES': {'bsearch': 'core.search_aliases'},
                'SIGNALS': {'BUFFER_SIZE': 1},
                #'ES_SETTINGS': {'http_auth': os.getenv('ELASTIC_SEARCH_AUTH')},
                }
