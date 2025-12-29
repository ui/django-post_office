from django.test import TestCase, override_settings

from post_office.settings import get_file_storage


class TestFileStorageSettings(TestCase):
    @override_settings(
        STORAGES={
            'default': {
                'BACKEND': 'django.core.files.storage.FileSystemStorage',
            },
            'staticfiles': {
                'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
            },
        },
        POST_OFFICE={},
    )
    def test_default_file_storage(self):
        self.assertEqual(get_file_storage().__class__.__name__, 'FileSystemStorage')

    @override_settings(
        STORAGES={
            'default': {
                'BACKEND': 'django.core.files.storage.FileSystemStorage',
            },
            'staticfiles': {
                'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
            },
            'post_office': {
                'BACKEND': 'django.core.files.storage.InMemoryStorage',
            },
        },
        POST_OFFICE={
            'FILE_STORAGE': 'post_office',
        },
    )
    def test_configured_file_storage(self):
        self.assertEqual(get_file_storage().__class__.__name__, 'InMemoryStorage')
