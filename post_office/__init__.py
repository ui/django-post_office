VERSION = (1, 1, 1)

from .backends import EmailBackend, SSLEmailBackend
from .models import PRIORITY
from .utils import send_mail
