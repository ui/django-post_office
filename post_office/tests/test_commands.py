import datetime
import os

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.timezone import now

from ..models import Attachment, Email, STATUS


class CommandTest(TestCase):

    def test_cleanup_mail_with_orphaned_attachments(self):
        self.assertEqual(Email.objects.count(), 0)
        email = Email.objects.create(to=['to@example.com'],
                                     from_email='from@example.com',
                                     subject='Subject')

        email.created = now() - datetime.timedelta(31)
        email.save()

        attachment = Attachment()
        attachment.file.save(
            'test.txt', content=ContentFile('test file content'), save=True
        )
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
        email = Email.objects.create(to=['to@example.com'],
                                     from_email='from@example.com',
                                     subject='Subject')
        email.created = now() - datetime.timedelta(31)
        email.save()

        attachment = Attachment()
        attachment.file.save(
            'test.txt', content=ContentFile('test file content'), save=True
        )
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
        email = Email.objects.create(from_email='from@example.com',
                                     to=['to@example.com'])
        call_command('cleanup_mail', days=30)
        self.assertEqual(Email.objects.count(), 1)

        # Email older than 30 days should be deleted
        email.created = now() - datetime.timedelta(31)
        email.save()
        call_command('cleanup_mail', days=30)
        self.assertEqual(Email.objects.count(), 0)

    TEST_SETTINGS = {
        'BACKENDS': {
            'default': 'django.core.mail.backends.dummy.EmailBackend',
        },
        'BATCH_SIZE': 1
    }

    @override_settings(POST_OFFICE=TEST_SETTINGS)
    def test_send_queued_mail(self):
        """
        Ensure that ``send_queued_mail`` behaves properly and sends all queued
        emails in two batches.
        """
        # Make sure that send_queued_mail with empty queue does not raise error
        call_command('send_queued_mail', processes=1)

        Email.objects.create(from_email='from@example.com',
                             to=['to@example.com'], status=STATUS.queued)
        Email.objects.create(from_email='from@example.com',
                             to=['to@example.com'], status=STATUS.queued)
        call_command('send_queued_mail', processes=1)
        self.assertEqual(Email.objects.filter(status=STATUS.sent).count(), 2)
        self.assertEqual(Email.objects.filter(status=STATUS.queued).count(), 0)

    def test_successful_deliveries_logging(self):
        """
        Successful deliveries are only logged when log_level is 2.
        """
        email = Email.objects.create(from_email='from@example.com',
                                     to=['to@example.com'], status=STATUS.queued)
        call_command('send_queued_mail', log_level=0)
        self.assertEqual(email.logs.count(), 0)

        email = Email.objects.create(from_email='from@example.com',
                                     to=['to@example.com'], status=STATUS.queued)
        call_command('send_queued_mail', log_level=1)
        self.assertEqual(email.logs.count(), 0)

        email = Email.objects.create(from_email='from@example.com',
                                     to=['to@example.com'], status=STATUS.queued)
        call_command('send_queued_mail', log_level=2)
        self.assertEqual(email.logs.count(), 1)

    def test_failed_deliveries_logging(self):
        """
        Failed deliveries are logged when log_level is 1 and 2.
        """
        email = Email.objects.create(from_email='from@example.com',
                                     to=['to@example.com'], status=STATUS.queued,
                                     backend_alias='error')
        call_command('send_queued_mail', log_level=0)
        self.assertEqual(email.logs.count(), 0)

        email = Email.objects.create(from_email='from@example.com',
                                     to=['to@example.com'], status=STATUS.queued,
                                     backend_alias='error')
        call_command('send_queued_mail', log_level=1)
        self.assertEqual(email.logs.count(), 1)

        email = Email.objects.create(from_email='from@example.com',
                                     to=['to@example.com'], status=STATUS.queued,
                                     backend_alias='error')
        call_command('send_queued_mail', log_level=2)
        self.assertEqual(email.logs.count(), 1)
