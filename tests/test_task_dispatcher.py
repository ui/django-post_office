import os
import subprocess
import sys
from unittest import mock, skipUnless

import django
from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.test import SimpleTestCase, TransactionTestCase
from django.test.utils import override_settings


def enqueue_custom():
    pass


def enqueue_named_backend():
    from post_office.django_tasks import send_queued_mail

    send_queued_mail.using(backend='mail').enqueue()


class TaskDispatcherConfigurationTests(SimpleTestCase):
    def test_default_and_explicit_disable(self):
        from post_office.settings import get_task_dispatcher

        for config in ({}, {'CELERY_ENABLED': True, 'TASK_DISPATCHER': None}):
            with self.subTest(config=config), override_settings(POST_OFFICE=config):
                self.assertIsNone(get_task_dispatcher())

    def test_startup_selects_one_signal_handler(self):
        from post_office import tasks
        from post_office.task_dispatch import queued_mail_handler

        for config, receiver in (
            ({}, None),
            ({'CELERY_ENABLED': True}, tasks.queued_mail_handler),
            ({'CELERY_ENABLED': True, 'TASK_DISPATCHER': None}, None),
            ({'CELERY_ENABLED': True, 'TASK_DISPATCHER': enqueue_custom}, queued_mail_handler),
        ):
            with self.subTest(config=config), override_settings(POST_OFFICE=config):
                with mock.patch('post_office.signals.email_queued.connect') as connect:
                    apps.get_app_config('post_office').ready()
                    if receiver is None:
                        connect.assert_not_called()
                    else:
                        connect.assert_called_once_with(receiver)

    def test_custom_path_and_callable(self):
        from post_office.settings import get_task_dispatcher

        for dispatcher in ('tests.test_task_dispatcher.enqueue_custom', enqueue_custom):
            with self.subTest(dispatcher=dispatcher), override_settings(POST_OFFICE={'TASK_DISPATCHER': dispatcher}):
                self.assertIs(get_task_dispatcher(), enqueue_custom)

    def test_invalid_dispatchers_fail_clearly(self):
        from post_office.settings import get_task_dispatcher

        for dispatcher in ('missing.module.enqueue', 42):
            with self.subTest(dispatcher=dispatcher), override_settings(POST_OFFICE={'TASK_DISPATCHER': dispatcher}):
                with self.assertRaises(ImproperlyConfigured):
                    get_task_dispatcher()

    @skipUnless(django.VERSION < (6, 0), 'Older Django configuration')
    def test_django_tasks_requires_supported_django(self):
        from post_office.settings import get_task_dispatcher

        with override_settings(POST_OFFICE={'TASK_DISPATCHER': 'post_office.django_tasks.enqueue'}):
            with self.assertRaisesMessage(ImproperlyConfigured, 'requires Django 6.0'):
                get_task_dispatcher()


@override_settings(POST_OFFICE={'TASK_DISPATCHER': 'tests.test_task_dispatcher.enqueue_custom', 'CELERY_ENABLED': True})
class CustomTaskDispatcherTests(TransactionTestCase):
    def test_dispatch_after_commit_and_never_after_rollback(self):
        from post_office.task_dispatch import queued_mail_handler

        with mock.patch('tests.test_task_dispatcher.enqueue_custom') as enqueue:
            with transaction.atomic():
                queued_mail_handler(sender=None)
                enqueue.assert_not_called()
            enqueue.assert_called_once_with()
            enqueue.reset_mock()
            with self.assertRaises(ValueError):
                with transaction.atomic():
                    queued_mail_handler(sender=None)
                    raise ValueError('rollback')
            enqueue.assert_not_called()

    def test_explicit_dispatcher_replaces_celery_and_connects_once(self):
        from post_office import tasks
        from post_office.signals import email_queued

        with mock.patch('tests.test_task_dispatcher.enqueue_custom') as enqueue:
            with mock.patch.object(tasks, 'send_queued_mail', create=True) as celery_task:
                apps.get_app_config('post_office').ready()
                apps.get_app_config('post_office').ready()
                email_queued.send(sender=None, emails=[])
                enqueue.assert_called_once_with()
                celery_task.delay.assert_not_called()


@skipUnless(django.VERSION >= (6, 0), 'Django Tasks requires Django >= 6.0')
@override_settings(
    TASKS={'default': {'BACKEND': 'django.tasks.backends.dummy.DummyBackend'}},
    POST_OFFICE={'TASK_DISPATCHER': 'post_office.django_tasks.enqueue', 'CELERY_ENABLED': True},
)
class DjangoTaskDispatcherTests(TransactionTestCase):
    @override_settings(
        TASKS={
            'default': {'BACKEND': 'django.tasks.backends.dummy.DummyBackend'},
            'mail': {'BACKEND': 'django.tasks.backends.dummy.DummyBackend'},
        },
        POST_OFFICE={'TASK_DISPATCHER': 'tests.test_task_dispatcher.enqueue_named_backend'},
    )
    def test_custom_dispatcher_selects_named_backend(self):
        from django.tasks import task_backends

        from post_office.task_dispatch import queued_mail_handler

        task_backends['default'].clear()
        task_backends['mail'].clear()
        queued_mail_handler(sender=None)
        self.assertEqual(task_backends['default'].results, [])
        self.assertEqual(len(task_backends['mail'].results), 1)

    def test_django_dispatcher_without_celery_installed(self):
        code = """
import importlib.abc
import sys
class NoCelery(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'celery' or fullname.startswith('celery.'):
            raise ModuleNotFoundError(fullname)
sys.meta_path.insert(0, NoCelery())
from django.conf import settings
settings.POST_OFFICE = {'CELERY_ENABLED': True, 'TASK_DISPATCHER': 'post_office.django_tasks.enqueue'}
settings.TASKS = {'default': {'BACKEND': 'django.tasks.backends.dummy.DummyBackend'}}
import django
django.setup()
from django.tasks import default_task_backend
from post_office.signals import email_queued
email_queued.send(sender=None, emails=[])
assert len(default_task_backend.results) == 1
assert 'celery' not in sys.modules
"""
        result = subprocess.run(
            [sys.executable, '-c', code],
            env={**os.environ, 'DJANGO_SETTINGS_MODULE': 'tests.test_settings'},
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    @override_settings(TASKS={'default': {'BACKEND': 'django.tasks.backends.immediate.ImmediateBackend'}})
    def test_cleanup_task_reuses_existing_cleanup(self):
        from post_office.django_tasks import cleanup_mail

        with mock.patch('post_office.django_tasks.cleanup_expired_mails') as cleanup:
            cleanup_mail.enqueue(days=7, delete_attachments=False)
        self.assertEqual(cleanup.call_args.args[1], False)
