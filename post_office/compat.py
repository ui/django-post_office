import sys


PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3


if PY3:
    string_types = str
    text_type = str
else:
    string_types = basestring
    text_type = unicode

