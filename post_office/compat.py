try:
    import importlib
except ImportError:
    from django.utils import importlib

import sys


PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3


if PY3:
    string_types = str
    text_type = str
else:
    string_types = basestring
    text_type = unicode


# Django 1.4 doesn't have ``import_string`` or ``import_by_path``
def import_attribute(name):
    """Return an attribute from a dotted path name (e.g. "path.to.func")."""
    module_name, attribute = name.rsplit('.', 1)
    module = importlib.import_module(module_name)
    return getattr(module, attribute)
