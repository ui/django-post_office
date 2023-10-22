import re
import time
from datetime import timedelta
from multiprocessing.context import TimeoutError
from unittest.mock import MagicMock, patch

import pytz
from django.conf import settings
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from ..mail import _send_bulk, create, get_queued, send, send_many, send_queued
from ..models import PRIORITY, STATUS, Attachment, Email, EmailTemplate
from ..settings import (get_batch_size, get_log_level, get_max_retries,
                        get_retry_timedelta, get_threads_per_process)

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


class SlowTestBackend(mail.backends.base.BaseEmailBackend):
    '''
    An EmailBackend that sleeps for 10 seconds when sending messages
    '''

    def send_messages(self, email_messages):
        time.sleep(5)


class MailTest(TestCase):

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_send_queued_mail(self):
        """
        Check that only queued messages are sent.
        """
        kwargs = {
            'to': ['to@example.com'],
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
            'to': ['to@example.com'],
            'from_email': 'bob@example.com',
            'subject': 'Test',
            'message': 'Message',
            'status': STATUS.queued
        }

        # All three emails should be sent
        self.assertEqual(Email.objects.filter(status=STATUS.sent).count(), 0)
        for i in range(3):
            Email.objects.create(**kwargs)
        total_sent, total_failed, total_requeued = send_queued(processes=2)
        self.assertEqual(total_sent, 3)

    def test_send_bulk(self):
        """
        Ensure _send_bulk() properly sends out emails.
        """
        email = Email.objects.create(
            to=['to@example.com'], from_email='bob@example.com',
            subject='send bulk', message='Message', status=STATUS.queued,
            backend_alias='locmem')
        _send_bulk([email], uses_multiprocessing=False)
        self.assertEqual(Email.objects.get(id=email.id).status, STATUS.sent)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'send bulk')

    @override_settings(EMAIL_BACKEND='post_office.tests.test_mail.ConnectionTestingBackend')
    def test_send_bulk_reuses_open_connection(self):
        """
        Ensure _send_bulk() only opens connection once to send multiple emails.
        """
        global connection_counter
        self.assertEqual(connection_counter, 0)
        email = Email.objects.create(to=['to@example.com'],
                                     from_email='bob@example.com', subject='',
                                     message='', status=STATUS.queued, backend_alias='connection_tester')
        email_2 = Email.objects.create(to=['to@example.com'],
                                       from_email='bob@example.com', subject='',
                                       message='', status=STATUS.queued,
                                       backend_alias='connection_tester')
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
        scheduled_time = timezone.now() + timedelta(days=1)
        Email.objects.create(status=STATUS.queued, scheduled_time=scheduled_time, **kwargs)
        self.assertEqual(list(get_queued()), [queued_email])

        # Email scheduled in the past should be included
        past_email = Email.objects.create(status=STATUS.queued,
                                          scheduled_time=timezone.datetime(2010, 12, 13), **kwargs)
        self.assertEqual(list(get_queued()), [queued_email, past_email])

    def test_get_batch_size(self):
        """
        Ensure BATCH_SIZE setting is read correctly.
        """
        previous_settings = settings.POST_OFFICE
        self.assertEqual(get_batch_size(), 100)
        setattr(settings, 'POST_OFFICE', {'BATCH_SIZE': 10})
        self.assertEqual(get_batch_size(), 10)
        settings.POST_OFFICE = previous_settings

    def test_get_threads_per_process(self):
        """
        Ensure THREADS_PER_PROCESS setting is read correctly.
        """
        previous_settings = settings.POST_OFFICE
        self.assertEqual(get_threads_per_process(), 5)
        setattr(settings, 'POST_OFFICE', {'THREADS_PER_PROCESS': 10})
        self.assertEqual(get_threads_per_process(), 10)
        settings.POST_OFFICE = previous_settings

    def test_get_log_level(self):
        """
        Ensure LOG_LEVEL setting is read correctly.
        """
        previous_settings = settings.POST_OFFICE
        self.assertEqual(get_log_level(), 2)
        setattr(settings, 'POST_OFFICE', {'LOG_LEVEL': 1})
        self.assertEqual(get_log_level(), 1)
        # Restore ``LOG_LEVEL``
        setattr(settings, 'POST_OFFICE', {'LOG_LEVEL': 2})
        settings.POST_OFFICE = previous_settings

    def test_create(self):
        """
        Test basic email creation
        """

        # Test that email is persisted only when commit=True
        email = create(
            sender='from@example.com', recipients=['to@example.com'],
            commit=False
        )
        self.assertEqual(email.id, None)
        email = create(
            sender='from@example.com', recipients=['to@example.com'],
            commit=True
        )
        self.assertNotEqual(email.id, None)

        # Test that email is created with the right status
        email = create(
            sender='from@example.com', recipients=['to@example.com'],
            priority=PRIORITY.now
        )
        self.assertEqual(email.status, None)
        email = create(
            sender='from@example.com', recipients=['to@example.com'],
            priority=PRIORITY.high
        )
        self.assertEqual(email.status, STATUS.queued)

        # Test that email is created with the right content
        context = {
            'subject': 'My subject',
            'message': 'My message',
            'html': 'My html',
        }
        scheduled_time = timezone.now()
        email = create(
            sender='from@example.com', recipients=['to@example.com'],
            subject='Test {{ subject }}', message='Test {{ message }}',
            html_message='Test {{ html }}', context=context,
            scheduled_time=scheduled_time, headers={'header': 'Test header'},
        )
        self.assertEqual(email.from_email, 'from@example.com')
        self.assertEqual(email.to, ['to@example.com'])
        self.assertEqual(email.subject, 'Test My subject')
        self.assertEqual(email.message, 'Test My message')
        self.assertEqual(email.html_message, 'Test My html')
        self.assertEqual(email.scheduled_time, scheduled_time)
        self.assertEqual(email.headers, {'header': 'Test header'})
        self.assertTrue(re.match(r'<\d+\.\d+\.\d+@example.com>', email.message_id))

    def test_send_many(self):
        """Test send_many creates the right emails """
        kwargs_list = [
            {'sender': 'from@example.com', 'recipients': ['a@example.com']},
            {'sender': 'from@example.com', 'recipients': ['b@example.com']},
        ]
        send_many(kwargs_list)
        self.assertEqual(Email.objects.filter(to=['a@example.com']).count(), 1)

    def test_send_with_attachments(self):
        attachments = {
            'attachment_file1.txt': ContentFile('content'),
            'attachment_file2.txt': ContentFile('content'),
        }
        email = send(recipients=['a@example.com', 'b@example.com'],
                     sender='from@example.com', message='message',
                     subject='subject', attachments=attachments)

        self.assertTrue(email.pk)
        self.assertEqual(email.attachments.count(), 2)

    def test_send_with_render_on_delivery(self):
        """
        Ensure that mail.send() create email instances with appropriate
        fields being saved
        """
        template = EmailTemplate.objects.create(
            subject='Subject {{ name }}',
            content='Content {{ name }}',
            html_content='HTML {{ name }}'
        )
        context = {'name': 'test'}
        email = send(recipients=['a@example.com', 'b@example.com'],
                     template=template, context=context,
                     render_on_delivery=True)
        self.assertEqual(email.subject, '')
        self.assertEqual(email.message, '')
        self.assertEqual(email.html_message, '')
        self.assertEqual(email.template, template)

        # context shouldn't be persisted when render_on_delivery = False
        email = send(recipients=['a@example.com'],
                     template=template, context=context,
                     render_on_delivery=False)
        self.assertEqual(email.context, None)

    def test_send_with_attachments_multiple_recipients(self):
        """Test reusing the same attachment objects for several email objects"""
        attachments = {
            'attachment_file1.txt': ContentFile('content'),
            'attachment_file2.txt': ContentFile('content'),
        }
        email = send(recipients=['a@example.com', 'b@example.com'],
                     sender='from@example.com', message='message',
                     subject='subject', attachments=attachments)

        self.assertEqual(email.attachments.count(), 2)
        self.assertEqual(Attachment.objects.count(), 2)

    def test_create_with_template(self):
        """If render_on_delivery is True, subject and content
        won't be rendered, context also won't be saved."""

        template = EmailTemplate.objects.create(
            subject='Subject {{ name }}',
            content='Content {{ name }}',
            html_content='HTML {{ name }}'
        )
        context = {'name': 'test'}
        email = create(
            sender='from@example.com', recipients=['to@example.com'],
            template=template, context=context, render_on_delivery=True
        )
        self.assertEqual(email.subject, '')
        self.assertEqual(email.message, '')
        self.assertEqual(email.html_message, '')
        self.assertEqual(email.context, context)
        self.assertEqual(email.template, template)

    def test_create_with_template_and_empty_context(self):
        """If render_on_delivery is False, subject and content
        will be rendered, context won't be saved."""

        template = EmailTemplate.objects.create(
            subject='Subject {% now "Y" %}',
            content='Content {% now "Y" %}',
            html_content='HTML {% now "Y" %}'
        )
        context = None
        email = create(
            sender='from@example.com', recipients=['to@example.com'],
            template=template, context=context
        )
        today = timezone.datetime.today()
        current_year = today.year
        self.assertEqual(email.subject, 'Subject %d' % current_year)
        self.assertEqual(email.message, 'Content %d' % current_year)
        self.assertEqual(email.html_message, 'HTML %d' % current_year)
        self.assertEqual(email.context, None)
        self.assertIsNotNone(email.template)

    def test_backend_alias(self):
        """Test backend_alias field is properly set."""

        email = send(recipients=['a@example.com'],
                     sender='from@example.com', message='message',
                     subject='subject')
        self.assertEqual(email.backend_alias, '')

        email = send(recipients=['a@example.com'],
                     sender='from@example.com', message='message',
                     subject='subject', backend='locmem')
        self.assertEqual(email.backend_alias, 'locmem')

        with self.assertRaises(ValueError):
            send(recipients=['a@example.com'], sender='from@example.com',
                 message='message', subject='subject', backend='foo')

    @override_settings(LANGUAGES=(('en', 'English'), ('ru', 'Russian')))
    def test_send_with_template(self):
        """If render_on_delivery is False, subject and content
        will be rendered, context won't be saved."""

        template = EmailTemplate.objects.create(
            subject='Subject {{ name }}',
            content='Content {{ name }}',
            html_content='HTML {{ name }}'
        )
        russian_template = EmailTemplate(
            default_template=template,
            language='ru',
            subject='предмет {{ name }}',
            content='содержание {{ name }}',
            html_content='HTML {{ name }}'
        )
        russian_template.save()

        context = {'name': 'test'}
        email = send(recipients=['to@example.com'], sender='from@example.com',
                     template=template, context=context)
        email = Email.objects.get(id=email.id)
        self.assertEqual(email.subject, 'Subject test')
        self.assertEqual(email.message, 'Content test')
        self.assertEqual(email.html_message, 'HTML test')
        self.assertEqual(email.context, None)
        self.assertIsNotNone(email.template)

        # check, if we use the Russian version
        email = send(recipients=['to@example.com'], sender='from@example.com',
                     template=russian_template, context=context)
        email = Email.objects.get(id=email.id)
        self.assertEqual(email.subject, 'предмет test')
        self.assertEqual(email.message, 'содержание test')
        self.assertEqual(email.html_message, 'HTML test')
        self.assertEqual(email.context, None)
        self.assertIsNotNone(email.template)

        # Check that send picks template with the right language
        email = send(recipients=['to@example.com'], sender='from@example.com',
                     template=template, context=context, language='ru')
        email = Email.objects.get(id=email.id)
        self.assertEqual(email.subject, 'предмет test')

        email = send(recipients=['to@example.com'], sender='from@example.com',
                     template=template, context=context, language='ru',
                     render_on_delivery=True)
        self.assertEqual(email.template.language, 'ru')

    def test_send_bulk_with_faulty_template(self):
        template = EmailTemplate.objects.create(
            subject='{% if foo %}Subject {{ name }}',
            content='Content {{ name }}',
            html_content='HTML {{ name }}'
        )
        email = Email.objects.create(to='to@example.com', from_email='from@example.com',
                                     template=template, status=STATUS.queued)
        _send_bulk([email], uses_multiprocessing=False)
        email = Email.objects.get(id=email.id)
        self.assertEqual(email.status, STATUS.sent)

    def test_retry_failed(self):
        self.assertEqual(get_retry_timedelta(), timezone.timedelta(minutes=15))
        self.assertEqual(get_max_retries(), 2)

        # attempt to send email for the first time
        with patch('django.utils.timezone.now', side_effect=lambda: timezone.datetime(2020, 5, 18, 8, 0, 0)):
            email = create('from@example.com', recipients=['to@example.com'], subject='subject', message='message',
                            backend='error')
            self.assertIsNotNone(email.pk)
            self.assertEqual(email.created, timezone.datetime(2020, 5, 18, 8, 0, 0))
            self.assertEqual(email.status, STATUS.queued)
            self.assertIsNone(email.number_of_retries)
            result = send_queued()
            self.assertTupleEqual(result, (0, 0, 1))
            email.refresh_from_db()
            self.assertEqual(email.status, STATUS.requeued)
            self.assertEqual(email.number_of_retries, 1)
            self.assertEqual(email.scheduled_time, timezone.datetime(2020, 5, 18, 8, 15, 0))

        # check that resending before the new scheduled time doesn't do anything
        with patch('django.utils.timezone.now', side_effect=lambda: timezone.datetime(2020, 5, 18, 8, 14, 59)):
            result = send_queued()
            self.assertTupleEqual(result, (0, 0, 0))
            email.refresh_from_db()
            self.assertEqual(email.status, STATUS.requeued)
            self.assertEqual(email.number_of_retries, 1)
            self.assertEqual(email.scheduled_time, timezone.datetime(2020, 5, 18, 8, 15, 0))

        # check that sending after the new scheduled time retries again
        with patch('django.utils.timezone.now', side_effect=lambda: timezone.datetime(2020, 5, 18, 8, 15, 1)):
            result = send_queued()
            self.assertTupleEqual(result, (0, 0, 1))
            email.refresh_from_db()
            self.assertEqual(email.status, STATUS.requeued)
            self.assertEqual(email.number_of_retries, 2)
            self.assertEqual(email.scheduled_time, timezone.datetime(2020, 5, 18, 8, 30, 1))

        # check that any further failed attempt marks the delivery as failed
        with patch('django.utils.timezone.now', side_effect=lambda: timezone.datetime(2020, 5, 18, 8, 30, 2)):
            result = send_queued()
            self.assertTupleEqual(result, (0, 1, 0))
            email.refresh_from_db()
            self.assertEqual(email.status, STATUS.failed)
            self.assertEqual(email.number_of_retries, 2)
            self.assertEqual(email.scheduled_time, timezone.datetime(2020, 5, 18, 8, 30, 1))

    @override_settings(USE_TZ=True)
    def test_expired(self):
        tzinfo = pytz.timezone('Asia/Jakarta')
        email = create('from@example.com', recipients=['to@example.com'], subject='subject', message='message',
                       expires_at=timezone.datetime(2020, 5, 18, 9, 0, 1, tzinfo=tzinfo))
        self.assertEqual(email.expires_at, timezone.datetime(2020, 5, 18, 9, 0, 1, tzinfo=tzinfo))
        msg = email.prepare_email_message()
        self.assertEqual(msg.extra_headers['Expires'], 'Mon, 18 May 09:00:01 +0707')

        # check that email is not sent after its expire_at date
        with patch('django.utils.timezone.now', side_effect=lambda: timezone.datetime(2020, 5, 18, 9, 0, 2, tzinfo=tzinfo)):
            self.assertEqual(email.status, STATUS.queued)
            result = send_queued()
            self.assertTupleEqual(result, (0, 0, 0))
            email.refresh_from_db()

        # check that email is sent before its expire_at date
        with patch('django.utils.timezone.now', side_effect=lambda: timezone.datetime(2020, 5, 18, 9, 0, 0, tzinfo=tzinfo)):
            self.assertEqual(email.status, STATUS.queued)
            result = send_queued()
            self.assertTupleEqual(result, (1, 0, 0))
            email.refresh_from_db()
            self.assertEqual(email.status, STATUS.sent)

    def test_invalid_expired(self):
        with self.assertRaises(ValidationError):
            create('from@example.com', recipients=['to@example.com'], subject='subject',
                           message='message',
                           scheduled_time=timezone.datetime(2020, 5, 18, 9, 0, 1),
                           expires_at=timezone.datetime(2020, 5, 18, 9, 0, 0))

    def test_batch_delivery_timeout(self):
        """
        Ensure that batch delivery timeout is respected.
        """
        email = Email.objects.create(to=['to@example.com'],
                                     from_email='bob@example.com', subject='',
                                     message='', status=STATUS.queued, backend_alias='slow_backend')
        start_time = timezone.now()
        # slow backend sleeps for 5 seconds, so we should get a timeout error since we set
        # BATCH_DELIVERY_TIMEOUT timeout to 2 seconds in test_settings.py
        with self.assertRaises(TimeoutError):
            send_queued()
        end_time = timezone.now()
        # Assert that running time is less than 3 seconds (2 seconds timeout + 1 second buffer)
        self.assertTrue(end_time - start_time < timezone.timedelta(seconds=3))

    @patch('post_office.signals.email_queued.send')
    def test_backend_signal(self, mock):
        """
        Check that the post_office signal handler is fired
        """
        email = send(recipients=['a@example.com'],
                     sender='from@example.com', message='message',
                     subject='subject')
        mock.assert_called_once_with(sender=Email, emails=[email])
