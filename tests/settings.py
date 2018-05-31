"""
This file contains django settings to run tests with runtests.py
"""
SECRET_KEY = 'fake-key'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'test',
        'USER': 'test',
        'PASSWORD': 'test',
        'HOST': '127.0.0.1',
        'PORT': '5432'
    },
    'secondary': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'test2',
        'USER': 'test',
        'PASSWORD': 'test',
        'HOST': '127.0.0.1',
        'PORT': '5432'
    }
}

INSTALLED_APPS = [
    "src",
    "tests"
]
