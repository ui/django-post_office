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
        kwargs = {
            'to': 'to@example.com',
            'from_email': 'bob@example.com',
            'subject': 'Test',
            'message': 'Message',
        }
        failed_mail = Email.objects.create(status=STATUS.failed, **kwargs)
        none_mail = Email.objects.create(status=None, **kwargs)

        # This should be the only email that gets sent
        queued_mail = Email.objects.create(status=STATUS.queued, **kwargs)
        send_queued()
        self.assertNotEqual(Email.objects.get(id=failed_mail.id).status, STATUS.sent)
        self.assertNotEqual(Email.objects.get(id=none_mail.id).status, STATUS.sent)
        self.assertEqual(Email.objects.get(id=queued_mail.id).status, STATUS.sent)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_queued_mail_multi_processes(self):
        """
        Check that send_queued works well with multiple processes
        """
        kwargs = {
            'to': 'to@example.com',
            'from_email': 'bob@example.com',
            'subject': 'Test',
            'message': 'Message',
            'status': STATUS.queued
        }
        
        # All three emails should be sent
        self.assertEqual(Email.objects.filter(status=STATUS.sent).count(), 0)
        Email.objects.create(**kwargs)
        Email.objects.create(**kwargs)
        Email.objects.create(**kwargs)
        total_sent, total_failed = send_queued(num_processes=2)
        self.assertEqual(total_sent, 3)
        
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_bulk(self):
        """
        Ensure _send_bulk() properly sends out emails.
        """
        email = Email.objects.create(
            to='to@example.com', from_email='bob@example.com',
            subject='send bulk', message='Message', status=STATUS.queued)
        _send_bulk([email])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'send bulk')

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
