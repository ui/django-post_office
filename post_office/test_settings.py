# -*- coding: utf-8 -*-


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    },
}

# Default values: True
# POST_OFFICE_CACHE = True
# POST_OFFICE_TEMPLATE_CACHE = True


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

DEFAULT_FROM_EMAIL = 'webmaster@example.com'

MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)
MIDDLEWARE_CLASSES = MIDDLEWARE

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
