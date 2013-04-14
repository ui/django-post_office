# -*- coding: utf-8 -*-


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


INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'post_office',
)

SECRET_KEY = 'a'

ROOT_URLCONF = 'post_office.test_urls'
