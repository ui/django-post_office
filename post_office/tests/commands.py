import datetime

from django.core.management import call_command
from django.test import TestCase

from ..models import Email, STATUS

try:
    from django.utils.timezone import now
    now = now
except ImportError:
    now = datetime.now


class CommandTest(TestCase):

    def test_cleanup_mail(self):
        """
        The ``cleanup_mail`` command deletes mails older than a specified
        amount of days
        """
        self.assertEqual(Email.objects.count(), 0)

        # The command shouldn't delete today's email
        email = Email.objects.create(from_email='from@example.com', to='to@example.com')
        call_command('cleanup_mail', days=30)
        self.assertEqual(Email.objects.count(), 1)

        # Email older than 30 days should be deleted
        email.created = now() - datetime.timedelta(31)
        email.save()
        call_command('cleanup_mail', days=30)
        self.assertEqual(Email.objects.count(), 0)

    def test_send_queued_mail(self):
        """
        Quick check that ``send_queued_mail`` doesn't error out.
        """
        # Make sure that send_queued_mail with empty queue does not raise error
        call_command('send_queued_mail', processes=1)

        Email.objects.create(from_email='from@example.com', to='to@example.com',
                             status=STATUS.queued)
        call_command('send_queued_mail', processes=1)
        self.assertEqual(Email.objects.filter(status=STATUS.sent).count(), 1)

