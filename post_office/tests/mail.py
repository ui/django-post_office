from django.core import mail

from django.test import TestCase
from django.test.utils import override_settings

from ..models import Email, STATUS
from ..mail import send_queued, _send_bulk


connection_counter = 0


class ConnectionTestingBackend(mail.backends.base.BaseEmailBackend):
    '''
    An EmailBackend that increments a global counter when connection is opened
    '''

    def open(self):
        global connection_counter
        connection_counter += 1

    def send_messages(self, email_messages):
        pass


class MailTest(TestCase):

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_queued_mail(self):
        """
        Check that only queued messages are sent.
        """
        Email.objects.create(to='to@example.com', from_email='bob@example.com',
                             subject='Test', message='Message',
                             status=STATUS.sent)
        Email.objects.create(to='to@example.com', from_email='bob@example.com',
                             subject='Test', message='Message',
                             status=STATUS.failed)
        Email.objects.create(to='to@example.com', from_email='bob@example.com',
                             subject='Test', message='Message', status=None)

        # This should be the only email that gets sent
        Email.objects.create(to='to@example.com', from_email='bob@example.com',
                             subject='Queued', message='Message',
                             status=STATUS.queued)
        send_queued()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Queued')

    @override_settings(EMAIL_BACKEND='post_office.tests.mail.ConnectionTestingBackend')
    def test_send_bulk_reuses_open_connection(self):
        """
        Ensure _send_bulk() only opens connection once to send multiple emails.
        """
        global connection_counter
        self.assertEqual(connection_counter, 0)
        email = Email.objects.create(to='to@example.com',
                                     from_email='bob@example.com', subject='',
                                     message='', status=STATUS.queued)
        email_2 = Email.objects.create(to='to@example.com',
                                       from_email='bob@example.com', subject='',
                                       message='', status=STATUS.queued)
        _send_bulk([email, email_2])
        self.assertEqual(connection_counter, 1)
