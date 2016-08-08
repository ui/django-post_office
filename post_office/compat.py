try:
    import importlib
except ImportError:
    from django.utils import importlib

try:
    from logging.config import dictConfig  # Python >= 2.7
except ImportError:
    from django.utils.log import dictConfig  # Django <= 1.9

import sys


PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3


if PY3:
    string_types = str
    text_type = str
else:
    string_types = basestring
    text_type = unicode


try:
    from django.core.cache import caches  # Django >= 1.7

    def get_cache(name):
        return caches[name]
except ImportError:
    from django.core.cache import get_cache


try:
    from django.utils.encoding import smart_text  # For Django >= 1.5
except ImportError:
    from django.utils.encoding import smart_unicode as smart_text


# Django 1.4 doesn't have ``import_string`` or ``import_by_path``
def import_attribute(name):
    """Return an attribute from a dotted path name (e.g. "path.to.func")."""
    module_name, attribute = name.rsplit('.', 1)
    module = importlib.import_module(module_name)
    return getattr(module, attribute)
