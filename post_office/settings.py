import warnings

from django.conf import settings
from django.core.cache import get_cache
from django.core.cache.backends.base import InvalidCacheBackendError

from .compat import import_attribute


def _get_email_backend():
    warnings.warn("Please use the new dictionary styled settings for "
                  "POST_OFFICE_BACKEND", DeprecationWarning)
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
            # Sometimes this raises InvalidCacheBackendError, which is ok too
            try:
                return get_cache("default")
            except InvalidCacheBackendError:
                pass
    return None


def get_config():
    """
    Returns Post Office's configuration in dictionary format. e.g:
    POST_OFFICE = {
        'BATCH_SIZE': 1000
    }
    """
    return getattr(settings, 'POST_OFFICE', {})


def get_batch_size():
    return get_config().get('BATCH_SIZE', 5000)


def get_default_priority():
    return get_config().get('DEFAULT_PRIORITY', 'medium')


def get_default_log_level():
    return get_config().get('DEFAULT_LOG_LEVEL', 2)


def get_email_backend():
    email_backend = get_config().get('EMAIL_BACKEND')

    if not email_backend:
        email_backend = _get_email_backend()

    return email_backend


CONTEXT_FIELD_CLASS = get_config().get('CONTEXT_FIELD_CLASS',
                                       'jsonfield.JSONField')
context_field_class = import_attribute(CONTEXT_FIELD_CLASS)
