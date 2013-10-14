from datetime import date, datetime

from django.core import mail
from django.conf import settings

from django.test import TestCase
from django.test.utils import override_settings

from ..settings import get_batch_size
from ..models import Email, PRIORITY, STATUS
from ..mail import create, get_queued, send_queued, _send_bulk


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
        for i in range(3):
            Email.objects.create(**kwargs)
        total_sent, total_failed = send_queued(processes=2)
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

    def test_get_queued(self):
        """
        Ensure get_queued returns only emails that should be sent
        """
        kwargs = {
            'to': 'to@example.com',
            'from_email': 'bob@example.com',
            'subject': 'Test',
            'message': 'Message',
        }
        self.assertEqual(list(get_queued()), [])

        # Emails with statuses failed, sent or None shouldn't be returned
        Email.objects.create(status=STATUS.failed, **kwargs)
        Email.objects.create(status=None, **kwargs)
        Email.objects.create(status=STATUS.sent, **kwargs)
        self.assertEqual(list(get_queued()), [])

        # Email with queued status and None as scheduled_time should be included
        queued_email = Email.objects.create(status=STATUS.queued,
                                            scheduled_time=None, **kwargs)
        self.assertEqual(list(get_queued()), [queued_email])

        # Email scheduled for the future should not be included
        Email.objects.create(status=STATUS.queued,
                             scheduled_time=date(2020, 12, 13), **kwargs)
        self.assertEqual(list(get_queued()), [queued_email])

        # Email scheduled in the past should be included
        past_email = Email.objects.create(status=STATUS.queued,
                                          scheduled_time=date(2010, 12, 13), **kwargs)
        self.assertEqual(list(get_queued()), [queued_email, past_email])

    def test_get_batch_size(self):
        """
        Ensure BATCH_SIZE setting is read correctly.
        """
        self.assertEqual(get_batch_size(), 5000)
        setattr(settings, 'POST_OFFICE', {'BATCH_SIZE': 100})
        self.assertEqual(get_batch_size(), 100)

    def test_create(self):
        """
        Test basic email creation
        """

        # Test that email is persisted only when commi=True
        email = create(
            sender='from@example.com', recipient='to@example.com',
            commit=False
        )
        self.assertEqual(email.id, None)
        email = create(
            sender='from@example.com', recipient='to@example.com',
            commit=True
        )
        self.assertNotEqual(email.id, None)

        # Test that email is created with the right status
        email = create(
            sender='from@example.com', recipient='to@example.com',
            priority=PRIORITY.now
        )
        self.assertEqual(email.status, None)
        email = create(
            sender='from@example.com', recipient='to@example.com',
            priority=PRIORITY.high
        )
        self.assertEqual(email.status, STATUS.queued)

        # Test that email is created with the right content
        context = {
            'subject': 'My subject',
            'message': 'My message',
            'html': 'My html',
        }
        now = datetime.now()
        email = create(
            sender='from@example.com', recipient='to@example.com',
            subject='Test {{ subject }}', message='Test {{ message }}',
            html_message='Test {{ html }}', context=context,
            scheduled_time=now, headers={'header': 'Test header'},
        )
        self.assertEqual(email.from_email, 'from@example.com')
        self.assertEqual(email.to, 'to@example.com')
        self.assertEqual(email.subject, 'Test My subject')
        self.assertEqual(email.message, 'Test My message')
        self.assertEqual(email.html_message, 'Test My html')
        self.assertEqual(email.scheduled_time, now)
        self.assertEqual(email.headers, {'header': 'Test header'})

        