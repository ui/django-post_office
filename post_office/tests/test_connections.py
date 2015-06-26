from django.core.mail import backends
from django.test import TestCase

from .test_backends import ErrorRaisingBackend
from ..connections import connections


class ConnectionTest(TestCase):

    def test_get_connection(self):
        # Ensure ConnectionHandler returns the right connection
        self.assertTrue(isinstance(connections['error'], ErrorRaisingBackend))
        self.assertTrue(isinstance(connections['locmem'], backends.locmem.EmailBackend))
