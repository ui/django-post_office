from django.conf import settings
from django.test import TestCase

from ..settings import get_cache_backend


class CacheTest(TestCase):

    def test_get_backend(self):
        pass
