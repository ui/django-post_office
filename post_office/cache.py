from django.core.cache import get_cache

from django.contrib.sites.models import Site
from django.template.defaultfilters import slugify

from dbtemplates.conf import settings


def get_cache_backend():
    return get_cache(settings.DBTEMPLATES_CACHE_BACKEND)

cache = get_cache_backend()


def get_cache_key(name):
    current_site = Site.objects.get_current()
    return 'dbtemplates::%s::%s' % (slugify(name), current_site.pk)


def get_cache_notfound_key(name):
    return get_cache_key(name) + '::notfound'


def remove_notfound_key(instance):
    # Remove notfound key as soon as we save the template.
    cache.delete(get_cache_notfound_key(instance.name))


def set_and_return(cache_key, content, display_name):
    # Save in cache backend explicitly if manually deleted or invalidated
    if cache:
        cache.set(cache_key, content)
    return (content, display_name)


def add_template_to_cache(instance, **kwargs):
    """
    Called via Django's signals to cache the templates, if the template
    in the database was added or changed.
    """
    remove_cached_template(instance)
    remove_notfound_key(instance)
    cache.set(get_cache_key(instance.name), instance.content)


def remove_cached_template(instance, **kwargs):
    """
    Called via Django's signals to remove cached templates, if the template
    in the database was changed or deleted.
    """
    cache.delete(get_cache_key(instance.name))
