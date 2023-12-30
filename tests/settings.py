"""
This file contains django settings to run tests with runtests.py
"""
from os import environ

SECRET_KEY = 'fake-key'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'test',
        'USER': environ.get('PGUSER', 'test'),
        'PASSWORD': environ.get('PGPASS', 'test'),
        'HOST': environ.get('PGHOST', '127.0.0.1'),
        'PORT': environ.get('PGPORT', 5432)
    },
    'secondary': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'test2',
        'USER': environ.get('PGUSER', 'test'),
        'PASSWORD': environ.get('PGPASS', 'test'),
        'HOST': environ.get('PGHOST', '127.0.0.1'),
        'PORT': environ.get('PGPORT', 5432)
    }
}

INSTALLED_APPS = [
    "src",
    "tests"
]
