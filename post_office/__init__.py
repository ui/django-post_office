import django
from ast import literal_eval
from os.path import dirname, join

with open(join(dirname(__file__), 'version.txt'), 'r') as fh:
    VERSION = literal_eval(fh.read())

from .backends import EmailBackend

if django.VERSION < (3, 2): # pragma: no cover
    default_app_config = 'post_office.apps.PostOfficeConfig'
