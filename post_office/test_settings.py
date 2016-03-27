# -*- coding: utf-8 -*-
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    },
}


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'TIMEOUT': 36000,
        'KEY_PREFIX': 'post-office',
    },
    'post_office': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'TIMEOUT': 36000,
        'KEY_PREFIX': 'post-office',
    }
}

POST_OFFICE = {
    'BACKENDS': {
        'default': 'django.core.mail.backends.dummy.EmailBackend',
        'locmem': 'django.core.mail.backends.locmem.EmailBackend',
        'error': 'post_office.tests.test_backends.ErrorRaisingBackend',
        'smtp': 'django.core.mail.backends.smtp.EmailBackend',
        'connection_tester': 'post_office.tests.test_mail.ConnectionTestingBackend',
    },
    'TEMPLATE_DIR': os.path.join(BASE_DIR, 'post_office', 'tests', 'templates'),
}


INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'post_office',
)

SECRET_KEY = 'a'

ROOT_URLCONF = 'post_office.test_urls'

DEFAULT_FROM_EMAIL = 'webmaster@example.com'

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)
