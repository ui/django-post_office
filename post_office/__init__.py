from os.path import dirname, join

with open(join(dirname(__file__), 'version.txt'), 'r') as fh:
    VERSION = eval(fh.read())

from .backends import EmailBackend

default_app_config = 'post_office.apps.PostOfficeConfig'
