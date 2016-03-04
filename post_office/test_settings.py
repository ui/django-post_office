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

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'OPTIONS': {
        'loaders': [
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
            ('django.template.loaders.locmem.Loader', {
                'test_email_template/subject.txt': 'Subject',
                'test_email_template/content.html': '<html>Content</html>',
                'test_email_template/content.txt': 'Content',
            }),
        ],
        'context_processors': [
            'django.contrib.auth.context_processors.auth',
            'django.core.context_processors.request',
            'django.core.context_processors.static',
        ],
    },
}]
