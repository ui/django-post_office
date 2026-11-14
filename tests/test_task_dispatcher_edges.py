import datetime
import inspect
import os
import subprocess
import sys
from unittest import mock, skipUnless

import django
from django.apps import apps
from django.core import mail as django_mail
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.test import SimpleTestCase, TransactionTestCase, override_settings
from django.utils import timezone

from post_office import mail as post_mail
from post_office.models import STATUS, Email
from post_office.task_dispatch import queued_mail_handler


def enqueue_noop():
    pass


def enqueue_generator():
    yield None


async def enqueue_async_generator():
    yield None


class AsyncEnqueuer:
    async def __call__(self):
        pass


@override_settings(POST_OFFICE={'TASK_DISPATCHER': 'tests.test_task_dispatcher_edges.enqueue_noop'})
class DispatcherTransactionEdgeTests(TransactionTestCase):
    def setUp(self):
        apps.get_app_config('post_office').ready()

    def test_nested_savepoint_rollback_discards_only_its_dispatch(self):
        with mock.patch('tests.test_task_dispatcher_edges.enqueue_noop') as enqueue:
            with transaction.atomic():
                queued_mail_handler(sender=None)
                with self.assertRaises(ValueError):
                    with transaction.atomic():
                        queued_mail_handler(sender=None)
                        raise ValueError('savepoint rollback')
                enqueue.assert_not_called()
            enqueue.assert_called_once_with()

    def test_failed_enqueue_keeps_committed_email_for_manual_recovery(self):
        with mock.patch(
            'tests.test_task_dispatcher_edges.enqueue_noop', side_effect=ConnectionError('queue unavailable')
        ):
            with self.assertRaisesMessage(ConnectionError, 'queue unavailable'):
                with transaction.atomic():
                    post_mail.send(sender='from@example.com', recipients=['to@example.com'], message='persisted')
        email = Email.objects.get()
        self.assertEqual(email.status, STATUS.queued)
        with override_settings(POST_OFFICE={'BACKENDS': {'default': 'django.core.mail.backends.locmem.EmailBackend'}}):
            post_mail.send_queued_mail_until_done()
        email.refresh_from_db()
        self.assertEqual(email.status, STATUS.sent)

    def test_wrapped_lazy_dispatchers_fail_clearly_and_keep_committed_email(self):
        results = [AsyncEnqueuer()(), enqueue_generator(), enqueue_async_generator()]
        for result in results:
            try:
                with (
                    self.subTest(result=result),
                    override_settings(POST_OFFICE={'TASK_DISPATCHER': mock.Mock(return_value=result)}),
                ):
                    with self.assertRaisesMessage(ImproperlyConfigured, 'returned an awaitable or generator'):
                        post_mail.send(sender='from@example.com', recipients=['to@example.com'])
                    self.assertEqual(Email.objects.latest('id').status, STATUS.queued)
                    if inspect.iscoroutine(result):
                        self.assertIsNone(result.cr_frame)
            finally:
                if inspect.iscoroutine(result) or inspect.isgenerator(result):
                    result.close()

    def test_disabled_dispatcher_does_not_enqueue_with_registered_receiver(self):
        with override_settings(POST_OFFICE={'TASK_DISPATCHER': None, 'CELERY_ENABLED': True}):
            with mock.patch('tests.test_task_dispatcher_edges.enqueue_noop') as enqueue:
                post_mail.send(sender='from@example.com', recipients=['to@example.com'], message='disabled')
                enqueue.assert_not_called()
        self.assertEqual(Email.objects.get().status, STATUS.queued)

    def test_send_many_enqueues_once_after_all_rows_are_committed(self):
        row_counts = []
        with mock.patch(
            'tests.test_task_dispatcher_edges.enqueue_noop',
            side_effect=lambda: row_counts.append(Email.objects.count()),
        ):
            with transaction.atomic():
                post_mail.send_many(
                    [{'sender': 'from@example.com', 'recipients': ['to@example.com']} for _ in range(20)]
                )
                self.assertEqual(row_counts, [])
            self.assertEqual(row_counts, [20])

    def test_receiver_can_be_disconnected_by_function(self):
        from post_office import task_dispatch
        from post_office.signals import email_queued

        receiver = task_dispatch.queued_mail_handler
        try:
            self.assertTrue(email_queued.disconnect(receiver))
            with mock.patch('tests.test_task_dispatcher_edges.enqueue_noop') as enqueue:
                email_queued.send(sender=Email, emails=[])
                enqueue.assert_not_called()
        finally:
            apps.get_app_config('post_office').ready()

    def test_custom_awaitable_result_is_rejected(self):
        class Awaitable:
            def __await__(self):
                yield

        with override_settings(POST_OFFICE={'TASK_DISPATCHER': lambda: Awaitable()}):
            with self.assertRaises(ImproperlyConfigured):
                queued_mail_handler(sender=Email)


class RoutedBulkDispatcherTests(SimpleTestCase):
    def test_bulk_send_waits_for_write_database_commit_without_returned_rows(self):
        code = """
import tempfile
from pathlib import Path
from unittest import mock
from django.conf import settings
with tempfile.TemporaryDirectory() as directory:
    settings.DATABASES = {
        alias: {'ENGINE': 'django.db.backends.sqlite3', 'NAME': str(Path(directory) / (alias + '.sqlite3'))}
        for alias in ('default', 'mail')
    }
    class Router:
        def db_for_read(self, model, **hints):
            return 'default'
        def db_for_write(self, model, **hints):
            return 'mail'
    settings.DATABASE_ROUTERS = [Router()]
    calls = []
    settings.POST_OFFICE = {'TASK_DISPATCHER': lambda: calls.append('enqueue')}
    import django
    django.setup()
    from django.core.management import call_command
    from django.db import connections, transaction
    from post_office.mail import send_many
    from post_office.models import Email
    call_command('migrate', database='mail', verbosity=0)
    with mock.patch.object(type(connections['mail'].features), 'can_return_rows_from_bulk_insert', new=False):
        with transaction.atomic(using='mail'):
            emails = send_many([{'sender': 'from@example.com', 'recipients': ['to@example.com']}])
            assert emails[0]._state.db is None
            assert calls == [], calls
        assert calls == ['enqueue'], calls
        assert Email.objects.using('mail').count() == 1
        calls.clear()
        try:
            with transaction.atomic(using='mail'):
                send_many([{'sender': 'from@example.com', 'recipients': ['to@example.com']}])
                assert calls == [], calls
                raise ValueError('rollback')
        except ValueError:
            pass
        assert calls == [], calls
        assert Email.objects.using('mail').count() == 1
"""
        result = subprocess.run(
            [sys.executable, '-c', code],
            capture_output=True,
            text=True,
            env={**os.environ, 'DJANGO_SETTINGS_MODULE': 'tests.test_settings'},
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


class DispatcherStartupEdgeTests(SimpleTestCase):
    def test_invalid_dispatcher_fails_at_startup(self):
        code = """
from django.conf import settings
settings.POST_OFFICE = {'TASK_DISPATCHER': 42}
import django
django.setup()
"""
        result = subprocess.run(
            [sys.executable, '-c', code],
            capture_output=True,
            text=True,
            env={**os.environ, 'DJANGO_SETTINGS_MODULE': 'tests.test_settings'},
            timeout=30,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('ImproperlyConfigured', result.stderr)

    def test_legacy_celery_setting_with_celery_missing_starts_without_dispatch(self):
        code = """
import importlib.abc
import sys
class NoCelery(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'celery' or fullname.startswith('celery.'):
            raise ModuleNotFoundError(fullname)
sys.meta_path.insert(0, NoCelery())
from django.conf import settings
settings.POST_OFFICE = {'CELERY_ENABLED': True}
import django
django.setup()
from post_office.settings import get_task_dispatcher
from post_office.signals import email_queued
assert get_task_dispatcher() is None
email_queued.send(sender=None, emails=[])
assert 'celery' not in sys.modules
"""
        result = subprocess.run(
            [sys.executable, '-c', code],
            capture_output=True,
            text=True,
            env={**os.environ, 'DJANGO_SETTINGS_MODULE': 'tests.test_settings'},
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


@skipUnless(django.VERSION >= (6, 0), 'Django Tasks requires Django >= 6.0')
@override_settings(
    TASKS={'default': {'BACKEND': 'django.tasks.backends.immediate.ImmediateBackend'}},
    POST_OFFICE={
        'TASK_DISPATCHER': 'post_office.django_tasks.enqueue',
        'BACKENDS': {'default': 'django.core.mail.backends.locmem.EmailBackend'},
    },
)
class DjangoTaskDeliveryEdgeTests(TransactionTestCase):
    def setUp(self):
        apps.get_app_config('post_office').ready()

    def test_delivery_waits_for_outer_transaction_and_sees_attachments(self):
        from django.core.files.base import ContentFile

        with transaction.atomic():
            with transaction.atomic():
                email = post_mail.send(
                    sender='from@example.com',
                    recipients=['to@example.com'],
                    message='body',
                    attachments={'payload.bin': ContentFile(b'\x00\xff')},
                )
            self.assertEqual(email.status, STATUS.queued)
            self.assertEqual(len(django_mail.outbox), 0)
        email.refresh_from_db()
        self.assertEqual(email.status, STATUS.sent)
        self.assertEqual(len(django_mail.outbox), 1)
        self.assertEqual(django_mail.outbox[0].attachments[0].content, b'\x00\xff')

    def test_scheduled_email_needs_a_later_processor(self):
        from post_office.django_tasks import send_queued_mail

        future = timezone.now() + datetime.timedelta(hours=1)
        email = post_mail.send(sender='from@example.com', recipients=['to@example.com'], scheduled_time=future)
        email.refresh_from_db()
        self.assertEqual(email.status, STATUS.queued)
        self.assertEqual(len(django_mail.outbox), 0)
        with mock.patch('post_office.mail.timezone.now', return_value=future + datetime.timedelta(seconds=1)):
            send_queued_mail.enqueue()
        email.refresh_from_db()
        self.assertEqual(email.status, STATUS.sent)
        self.assertEqual(len(django_mail.outbox), 1)

    def test_delivery_failure_is_requeued_and_later_processor_recovers(self):
        from post_office.django_tasks import send_queued_mail

        with override_settings(
            POST_OFFICE={
                'TASK_DISPATCHER': 'post_office.django_tasks.enqueue',
                'BACKENDS': {'default': 'tests.test_backends.ErrorRaisingBackend'},
                'MAX_RETRIES': 1,
                'RETRY_INTERVAL': datetime.timedelta(seconds=10),
            }
        ):
            email = post_mail.send(sender='from@example.com', recipients=['to@example.com'])
        email.refresh_from_db()
        self.assertEqual(email.status, STATUS.requeued)
        self.assertEqual(email.number_of_retries, 1)
        with mock.patch(
            'post_office.mail.timezone.now', return_value=email.scheduled_time + datetime.timedelta(seconds=1)
        ):
            send_queued_mail.enqueue()
        email.refresh_from_db()
        self.assertEqual(email.status, STATUS.sent)
        self.assertEqual(len(django_mail.outbox), 1)

    def test_cleanup_task_defaults_match_celery_retention(self):
        from post_office.django_tasks import cleanup_mail

        fixed = timezone.now()
        with mock.patch('post_office.django_tasks.now', return_value=fixed):
            with mock.patch('post_office.django_tasks.cleanup_expired_mails') as cleanup:
                cleanup_mail.enqueue()
        cleanup.assert_called_once_with(fixed - datetime.timedelta(days=90), True)
