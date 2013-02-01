from django.core.cache import get_cache
from django.template.defaultfilters import slugify

from .settings import get_cache_backend


cache = get_cache(get_cache_backend())


def get_cache_key(name):
    """
    Prefixes and slugify the key name
    """
    return 'post_office:template:%s' % (slugify(name))


def set_cache(name, content):
    return cache.set(get_cache_key(name), content)


def get_cache(name):
    return cache.get(get_cache_key(name))


def delete_cache(name):
    return cache.delete(get_cache_key(name))
