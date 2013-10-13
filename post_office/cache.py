from django.core.cache import get_cache
from django.template.defaultfilters import slugify

from .settings import get_cache_backend

# Stripped down version of caching functions from django-dbtemplates
# https://github.com/jezdez/django-dbtemplates/blob/develop/dbtemplates/utils/cache.py
cache_backend = get_cache_backend()


def get_cache_key(name, language=None):
    """
    Prefixes and slugify the key name
    """
    return 'post_office:template:%s:%s' % (slugify(name), language)


def set(name, content, language=None):
    return cache_backend.set(get_cache_key(name, language), content)


def get(name, language=None):
    return cache_backend.get(get_cache_key(name, language))


def delete(name, language=None):
    return cache_backend.delete(get_cache_key(name, language))
