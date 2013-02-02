from django.core.cache import get_cache
from django.template.defaultfilters import slugify

from .settings import get_cache_backend

# Stripped down version of caching functions from django-dbtemplates
# https://github.com/jezdez/django-dbtemplates/blob/develop/dbtemplates/utils/cache.py
backend_cache = get_cache(get_cache_backend())


def get_cache_key(name):
    """
    Prefixes and slugify the key name
    """
    return 'post_office:template:%s' % (slugify(name))


def set(name, content):
    return backend_cache.set(get_cache_key(name), content)


def get(name):
    return backend_cache.get(get_cache_key(name))


def delete(name):
    return backend_cache.delete(get_cache_key(name))
