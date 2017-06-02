import datetime

from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.timezone import now

from ..models import Email, STATUS


class CommandTest(TestCase):

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
