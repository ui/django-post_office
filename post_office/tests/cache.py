from django.conf import settings
from django.test import TestCase

from post_office import cache
from ..settings import get_cache_backend


class CacheTest(TestCase):

    def test_get_backend_settings(self):
        """Test basic get backend function and its settings"""
        # Sanity check
        self.assertTrue('post_office' in settings.CACHES)
        self.assertTrue(get_cache_backend())

        # If no post office key is defined, it should return default
        del(settings.CACHES['post_office'])
        self.assertTrue(get_cache_backend())

        # If no caches key in settings, it should return None
        delattr(settings, 'CACHES')
        self.assertEqual(None, get_cache_backend())

    def test_get_cache_key(self):
        """
            Test for converting names to cache key
        """
        self.assertEqual('post_office:template:test:None', cache.get_cache_key('test'))
        self.assertEqual('post_office:template:test:en', cache.get_cache_key('test', 'en'))
        self.assertEqual('post_office:template:test-slugify:None', cache.get_cache_key('test slugify'))

    def test_basic_cache_operations(self):
        """
            Test basic cache operations
        """
        # clean test cache
        cache.cache_backend.clear()
        self.assertEqual(None, cache.get('test-cache'))
        cache.set('test-cache', 'awesome content', 'en')
        self.assertEqual(None, cache.get('test-cache'))
        self.assertEqual(None, cache.get('test-cache', 'fr'))
        self.assertEqual('awesome content', cache.get('test-cache', 'en'))
        cache.delete('test-cache', 'en')
        self.assertEqual(None, cache.get('test-cache', 'en'))
