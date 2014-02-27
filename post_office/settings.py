from django.conf import settings
from django.core.cache import get_cache
from django.core.cache.backends.base import InvalidCacheBackendError


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
