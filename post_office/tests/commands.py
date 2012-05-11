import datetime

from django.core.management import call_command
from django.test import TestCase

from ..models import Email


class CommandTest(TestCase):

    def test_cleanup_mail(self):
        """
        The ``cleanup_mail`` command deletes mails older than a specified
        amount of days
        """
        today = datetime.date.today()
        self.assertEqual(Email.objects.count(), 0)

        # The command shouldn't delete today's email
        Email.objects.create(from_email='from@example.com', to='to@example.com')
        call_command('cleanup_mail', days=30)
        self.assertEqual(Email.objects.count(), 1)

        # Email older than 30 days should get deleted
        prev = today - datetime.timedelta(31)
        Email.objects.create(from_email='from@example.com', to='to@example.com', created=prev)
        call_command('cleanup_mail', days=30)
        self.assertEqual(Email.objects.count(), 1)