from django.conf import settings
from django.core.cache import get_cache


def get_email_backend():
    if hasattr(settings, 'POST_OFFICE_BACKEND'):
        backend = getattr(settings, 'POST_OFFICE_BACKEND')
    else:
        backend = getattr(settings, 'EMAIL_BACKEND',
                          'django.core.mail.backends.smtp.EmailBackend')
        # If EMAIL_BACKEND is set to use PostOfficeBackend
        # and POST_OFFICE_BACKEND is not set, fall back to SMTP
        if 'post_office.EmailBackend' in backend:
            backend = 'django.core.mail.backends.smtp.EmailBackend'
    return backend


def get_cache_backend():
    if hasattr(settings, 'CACHES'):
        if "post_office" in settings.CACHES:
            return get_cache("post_office")
        else:
            return get_cache("default")
    return None
