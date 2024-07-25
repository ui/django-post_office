from ast import literal_eval
from os.path import dirname, join

with open(join(dirname(__file__), 'version.txt')) as fh:
    VERSION = literal_eval(fh.read())

from .backends import EmailBackend
