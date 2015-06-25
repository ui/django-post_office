from django.core.mail import backends
from django.test import TestCase
from django.test.utils import override_settings

from .test_backends import ErrorRaisingBackend
from ..connections import connections
from ..settings import get_available_backends


class ConnectionTest(TestCase):

    def test_get_connection(self):
        # Ensure ConnectionHandler returns the right connection
        self.assertTrue(isinstance(connections['error'], ErrorRaisingBackend))
        self.assertTrue(isinstance(connections['smtp'], backends.smtp.EmailBackend))
        self.assertTrue(isinstance(connections['locmem'], backends.locmem.EmailBackend))
