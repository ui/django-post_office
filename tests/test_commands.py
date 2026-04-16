import datetime
import os
import threading
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.utils.timezone import now

from post_office.connections import ConnectionHandler
from post_office.models import STATUS, Attachment, Email


class CommandTest(TestCase):
    def test_cleanup_mail_with_orphaned_attachments(self):
        self.assertEqual(Email.objects.count(), 0)
        email = Email.objects.create(to=['to@example.com'], from_email='from@example.com', subject='Subject')

        email.created = now() - datetime.timedelta(31)
        email.save()

        attachment = Attachment()
        attachment.file.save('test.txt', content=ContentFile('test file content'), save=True)
        email.attachments.add(attachment)
        attachment_path = attachment.file.name

        # We have orphaned attachment now
        call_command('cleanup_mail', days=30)
        self.assertEqual(Email.objects.count(), 0)
        self.assertEqual(Attachment.objects.count(), 1)

        # Actually cleanup orphaned attachments
        call_command('cleanup_mail', '-da', days=30)
        self.assertEqual(Email.objects.count(), 0)
        self.assertEqual(Attachment.objects.count(), 0)

        # Check that the actual file has been deleted as well
        self.assertFalse(os.path.exists(attachment_path))

        # Check if the email attachment's actual file have been deleted
        Email.objects.all().delete()
        email = Email.objects.create(to=['to@example.com'], from_email='from@example.com', subject='Subject')
        email.created = now() - datetime.timedelta(31)
        email.save()

        attachment = Attachment()
        attachment.file.save('test.txt', content=ContentFile('test file content'), save=True)
        email.attachments.add(attachment)
        attachment_path = attachment.file.name

        # Simulate that the files have been deleted by accidents
        os.remove(attachment_path)

        # No exceptions should break the cleanup
        call_command('cleanup_mail', '-da', days=30)
        self.assertEqual(Email.objects.count(), 0)
        self.assertEqual(Attachment.objects.count(), 0)

    def test_cleanup_mail(self):
        """
        The ``cleanup_mail`` command deletes mails older than a specified
        amount of days
        """
        self.assertEqual(Email.objects.count(), 0)

        # The command shouldn't delete today's email
        email = Email.objects.create(from_email='from@example.com', to=['to@example.com'])
        call_command('cleanup_mail', days=30)
        self.assertEqual(Email.objects.count(), 1)

        # Email older than 30 days should be deleted
        email.created = now() - datetime.timedelta(31)
        email.save()
        call_command('cleanup_mail', days=30)
        self.assertEqual(Email.objects.count(), 0)

    @override_settings(
        POST_OFFICE={
            'BACKENDS': {
                'default': 'django.core.mail.backends.dummy.EmailBackend',
            },
            'BATCH_SIZE': 1,
        }
    )
    def test_send_queued_mail(self):
        """
        Ensure that ``send_queued_mail`` behaves properly and sends all queued
        emails in two batches.
        """
        # Make sure that send_queued_mail with empty queue does not raise error
        call_command('send_queued_mail', processes=1)

        Email.objects.create(from_email='from@example.com', to=['to@example.com'], status=STATUS.queued)
        Email.objects.create(from_email='from@example.com', to=['to@example.com'], status=STATUS.queued)
        call_command('send_queued_mail', processes=1)
        self.assertEqual(Email.objects.filter(status=STATUS.sent).count(), 2)
        self.assertEqual(Email.objects.filter(status=STATUS.queued).count(), 0)

    def test_successful_deliveries_logging(self):
        """
        Successful deliveries are only logged when log_level is 2.
        """
        email = Email.objects.create(from_email='from@example.com', to=['to@example.com'], status=STATUS.queued)
        call_command('send_queued_mail', log_level=0)
        self.assertEqual(email.logs.count(), 0)

        email = Email.objects.create(from_email='from@example.com', to=['to@example.com'], status=STATUS.queued)
        call_command('send_queued_mail', log_level=1)
        self.assertEqual(email.logs.count(), 0)

        email = Email.objects.create(from_email='from@example.com', to=['to@example.com'], status=STATUS.queued)
        call_command('send_queued_mail', log_level=2)
        self.assertEqual(email.logs.count(), 1)

    def test_failed_deliveries_logging(self):
        """
        Failed deliveries are logged when log_level is 1 and 2.
        """
        email = Email.objects.create(
            from_email='from@example.com', to=['to@example.com'], status=STATUS.queued, backend_alias='error'
        )
        call_command('send_queued_mail', log_level=0)
        self.assertEqual(email.logs.count(), 0)

        email = Email.objects.create(
            from_email='from@example.com', to=['to@example.com'], status=STATUS.queued, backend_alias='error'
        )
        call_command('send_queued_mail', log_level=1)
        self.assertEqual(email.logs.count(), 1)

        email = Email.objects.create(
            from_email='from@example.com', to=['to@example.com'], status=STATUS.queued, backend_alias='error'
        )
        call_command('send_queued_mail', log_level=2)
        self.assertEqual(email.logs.count(), 1)

    @override_settings(
        POST_OFFICE={
            'BACKENDS': {
                'default': 'django.core.mail.backends.dummy.EmailBackend',
            },
            'BATCH_SIZE': 10,
            'THREADS_PER_PROCESS': 2,
        }
    )
    def test_send_queued_mail_threads_use_independent_connections(self):
        """
        Worker threads must each obtain their own thread-local connection from
        ConnectionHandler so that no single connection is shared across threads.
        """
        for _ in range(3):
            Email.objects.create(from_email='from@example.com', to=['to@example.com'], status=STATUS.queued)

        # Map thread_id -> set of connection object ids fetched from ConnectionHandler
        conn_usage: dict[int, set[int]] = {}
        usage_lock = threading.Lock()
        original_getitem = ConnectionHandler.__getitem__

        def tracking_getitem(self, alias):
            conn = original_getitem(self, alias)
            with usage_lock:
                conn_usage.setdefault(threading.current_thread().ident, set()).add(id(conn))
            return conn

        with patch.object(ConnectionHandler, '__getitem__', tracking_getitem):
            call_command('send_queued_mail', processes=1)

        self.assertEqual(Email.objects.filter(status=STATUS.sent).count(), 3)

        self.assertGreater(len(conn_usage), 0, 'No connections were fetched from ConnectionHandler')

        # Build a map from connection id -> set of threads that used it
        conn_to_threads: dict[int, set[int]] = {}
        for tid, conn_ids in conn_usage.items():
            for cid in conn_ids:
                conn_to_threads.setdefault(cid, set()).add(tid)

        shared = {cid: tids for cid, tids in conn_to_threads.items() if len(tids) > 1}
        self.assertFalse(
            shared,
            f'Backend connections were shared across threads - thread safety violated: {shared}',
        )
