from django.conf import settings
from django.test import TestCase

from ..cache import *
from ..settings import get_cache_backend


class CacheTest(TestCase):

    def test_get_backend_settings(self):
        """
            Test basic get backend function and its settings
        """
        # Sanity check
        self.assertTrue('post_office' in settings.CACHES)
        self.assertEqual('post_office', get_cache_backend())

        # If no post office key is defined, it should return default
        del(settings.CACHES['post_office'])
        self.assertEqual('default', get_cache_backend())

        # If no caches key in settings, it should return None
        delattr(settings, 'CACHES')
        self.assertEqual(None, get_cache_backend())

    def test_get_cache_key(self):
        """
            Test for converting names to cache key
        """
        self.assertEqual('post_office::template::test', get_cache_key('test'))
        self.assertEqual('post_office::template::test-slugify', get_cache_key('test slugify'))

    def test_basic_cache_operations(self):
        """
            Test basic cache operations
        """
        # clean test
        cache.clear()
        self.assertEqual(None, get_cache('test'))
        set_cache('test', 'qwe')
        self.assertTrue('qwe', get_cache('test'))
        delete_cache('test')
        self.assertEqual(None, get_cache('test'))
