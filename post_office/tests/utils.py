from django.core import mail

from django.test import TestCase
from django.test.utils import override_settings

from ..models import Email, STATUS, PRIORITY
from ..utils import send_mail, send_queued_mails


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class UtilsTest(TestCase):

    def test_mail_status(self):
        """
        Check that send_mail assigns the right status field to Email instances
        """
        send_mail('subject', 'message', 'from@example.com', ['to@example.com'],
                  priority=PRIORITY.medium)
        email = Email.objects.latest('id')
        self.assertEqual(email.status, STATUS.queued)
        
        # Emails sent with "now" priority don't get sent right away
        send_mail('subject', 'message', 'from@example.com', ['to@example.com'],
                  priority=PRIORITY.now)
        email = Email.objects.latest('id')
        self.assertEqual(email.status, STATUS.sent)

    def test_send_queued_mails(self):
        """
        Check that only queued messages are sent.
        """
        Email.objects.create(to='to@example.com', from_email='from@example.com',
            subject='Test', message='Message', status=STATUS.sent)
        Email.objects.create(to='to@example.com', from_email='from@example.com',
            subject='Test', message='Message', status=STATUS.failed)
        Email.objects.create(to='to@example.com', from_email='from@example.com',
            subject='Test', message='Message', status=None)
        
        # This should be the only email that gets sent
        email = Email.objects.create(to='to@example.com', from_email='from@example.com',
            subject='Queued', message='Message', status=STATUS.queued)
        send_queued_mails()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Queued')

