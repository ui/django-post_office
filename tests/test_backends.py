import unittest
from email import policy
from email.message import MIMEPart
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from unittest import mock

from django.conf import settings
from django.core.mail import EmailMessage, EmailMultiAlternatives, send_mail
from django.core.mail.backends.base import BaseEmailBackend
from django.test import TestCase
from django.test.utils import override_settings

from post_office.models import PRIORITY, STATUS, Email
from post_office.settings import PRE_DJANGO_6, get_backend


class ErrorRaisingBackend(BaseEmailBackend):
    """
    An EmailBackend that always raises an error during sending
    to test if django_mailer handles sending error correctly
    """

    def send_messages(self, email_messages):
        raise Exception('Fake Error')


class BackendTest(TestCase):
    @override_settings(EMAIL_BACKEND='post_office.EmailBackend')
    def test_email_backend(self):
        """
        Ensure that email backend properly queue email messages.
        """
        send_mail('Test', 'Message', 'from@example.com', ['to@example.com'])
        email = Email.objects.latest('id')
        self.assertEqual(email.subject, 'Test')
        self.assertEqual(email.status, STATUS.queued)
        self.assertEqual(email.priority, PRIORITY.medium)

        # Like Django, message text is sent as written, not rendered as a template (#478).
        send_mail('Token {{ x }}', 'Use {{{TEST}}} and {% if user %}', 'from@example.com', ['to@example.com'])
        email = Email.objects.latest('id')
        self.assertEqual(email.subject, 'Token {{ x }}')
        self.assertEqual(email.message, 'Use {{{TEST}}} and {% if user %}')

    def test_email_backend_setting(self):
        """ """
        old_email_backend = getattr(settings, 'EMAIL_BACKEND', None)
        getattr(settings, 'POST_OFFICE_BACKEND', None)
        if hasattr(settings, 'EMAIL_BACKEND'):
            delattr(settings, 'EMAIL_BACKEND')
        if hasattr(settings, 'POST_OFFICE_BACKEND'):
            delattr(settings, 'POST_OFFICE_BACKEND')

        previous_settings = settings.POST_OFFICE
        delattr(settings, 'POST_OFFICE')
        # If no email backend is set, backend should default to SMTP
        self.assertEqual(get_backend(), 'django.core.mail.backends.smtp.EmailBackend')

        # If EMAIL_BACKEND is set to PostOfficeBackend, use SMTP to send by default
        setattr(settings, 'EMAIL_BACKEND', 'post_office.EmailBackend')
        self.assertEqual(get_backend(), 'django.core.mail.backends.smtp.EmailBackend')

        # If EMAIL_BACKEND is set on new dictionary-styled settings, use that
        setattr(settings, 'POST_OFFICE', {'EMAIL_BACKEND': 'test'})
        self.assertEqual(get_backend(), 'test')
        delattr(settings, 'POST_OFFICE')

        if old_email_backend:
            setattr(settings, 'EMAIL_BACKEND', old_email_backend)
        else:
            delattr(settings, 'EMAIL_BACKEND')
        setattr(settings, 'POST_OFFICE', previous_settings)

    # One test per legacy precedence level. These run on every supported
    # Django version; on 6.1 they exercise the path taken when MAILERS is unset.
    @override_settings(POST_OFFICE={'BACKENDS': {'default': 'tests.backend_one'}})
    def test_backend_precedence_post_office_backends(self):
        self.assertEqual(get_backend(), 'tests.backend_one')

    @override_settings(POST_OFFICE={'EMAIL_BACKEND': 'tests.backend_two'})
    def test_backend_precedence_post_office_email_backend(self):
        with self.assertWarns(DeprecationWarning):
            self.assertEqual(get_backend(), 'tests.backend_two')

    @override_settings(POST_OFFICE={}, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_backend_precedence_django_email_backend(self):
        self.assertEqual(get_backend(), 'django.core.mail.backends.locmem.EmailBackend')

    @override_settings(POST_OFFICE={}, EMAIL_BACKEND='post_office.EmailBackend')
    def test_backend_precedence_post_office_self_reference_falls_back_to_smtp(self):
        self.assertEqual(get_backend(), 'django.core.mail.backends.smtp.EmailBackend')

    @override_settings(EMAIL_BACKEND='post_office.EmailBackend')
    def test_sending_html_email(self):
        """
        "text/html" attachments to Email should be persisted into the database
        """
        message = EmailMultiAlternatives('subject', 'body', 'from@example.com', ['recipient@example.com'])
        message.attach_alternative('html', 'text/html')
        message.send()
        email = Email.objects.latest('id')
        self.assertEqual(email.html_message, 'html')

    @override_settings(EMAIL_BACKEND='post_office.EmailBackend')
    def test_headers_sent(self):
        """
        Test that headers are correctly set on the outgoing emails.
        """
        message = EmailMessage(
            'subject', 'body', 'from@example.com', ['recipient@example.com'], headers={'Reply-To': 'reply@example.com'}
        )
        message.send()
        email = Email.objects.latest('id')
        self.assertEqual(email.headers, {'Reply-To': 'reply@example.com'})

    @override_settings(EMAIL_BACKEND='post_office.EmailBackend')
    def test_reply_to_added_as_header(self):
        """
        Test that 'Reply-To' headers are correctly set on the outgoing emails,
        when EmailMessage property reply_to is set.
        """
        message = EmailMessage(
            'subject',
            'body',
            'from@example.com',
            ['recipient@example.com'],
            reply_to=[
                'replyto@example.com',
            ],
        )
        message.send()
        email = Email.objects.latest('id')
        self.assertEqual(email.headers, {'Reply-To': 'replyto@example.com'})

    @override_settings(EMAIL_BACKEND='post_office.EmailBackend')
    def test_reply_to_favors_explict_header(self):
        """
        Test that 'Reply-To' headers are correctly set, when reply_to property of
        the message object is set and "Reply-To" is also set explictly as a header.
        Then the explicit header value is favored over the message property reply_to,
        adopting the behaviour of message() in django.core.mail.message.EmailMessage.
        """
        message = EmailMessage(
            'subject',
            'body',
            'from@example.com',
            ['recipient@example.com'],
            reply_to=['replyto-from-property@example.com'],
            headers={'Reply-To': 'replyto-from-header@example.com'},
        )
        message.send()
        email = Email.objects.latest('id')
        self.assertEqual(email.headers, {'Reply-To': 'replyto-from-header@example.com'})

    @override_settings(EMAIL_BACKEND='post_office.EmailBackend')
    def test_backend_attachments(self):
        message = EmailMessage('subject', 'body', 'from@example.com', ['recipient@example.com'])

        message.attach('data', b'{}', 'application/json')
        message.send()

        rebuilt = Email.objects.latest('id').email_message().message().get_payload(1)
        self.assertEqual(rebuilt.get_content_type(), 'application/json')

    @override_settings(EMAIL_BACKEND='post_office.EmailBackend')
    def test_legacy_multipart_attachment_round_trip(self):
        message = EmailMessage('subject', 'body', 'from@example.com', ['recipient@example.com'])
        image = MIMEImage(b'GIF89a', _subtype='gif')
        bundle = MIMEMultipart()
        bundle.attach(image)
        message.attach(bundle)
        message.send()

        self.assertIsNone(bundle.get_boundary())
        rebuilt = Email.objects.latest('id').email_message().message().get_payload(1)
        self.assertEqual(rebuilt.get_payload(0).get_payload(decode=True), b'GIF89a')

    @override_settings(EMAIL_BACKEND='post_office.EmailBackend')
    def test_backend_image_attachments(self):
        message = EmailMessage('subject', 'body', 'from@example.com', ['recipient@example.com'])

        image = MIMEImage(b'GIF89a', _subtype='gif')
        image.add_header('Content-Disposition', 'inline', filename='logo.gif')
        image.add_header('Content-ID', '<logo>')
        message.attach(image)
        message.send()

        rebuilt = Email.objects.latest('id').email_message().attachments[0]
        self.assertEqual(rebuilt['Content-ID'], image['Content-ID'])
        self.assertIsInstance(rebuilt, MIMEBase if PRE_DJANGO_6 else MIMEPart)

    @unittest.skipIf(PRE_DJANGO_6, 'Django 6 added MIMEPart attachments')
    @override_settings(EMAIL_BACKEND='post_office.EmailBackend')
    def test_mimepart_attachments_round_trip(self):
        message = EmailMessage('subject', 'body', 'from@example.com', ['recipient@example.com'])
        payload = b'\x00\xff\x80\r\n'
        parts = []
        for content_id, filename in (('<first>', 'same.bin'), ('<second>', 'same.bin'), ('<unnamed>', None)):
            part = MIMEPart(policy=policy.SMTP)
            part.set_content(
                payload,
                maintype='application',
                subtype='octet-stream',
                cte='8bit',
                cid=content_id,
                filename=filename,
                disposition='inline',
            )
            parts.append(part)
        forwarded = MIMEPart()
        forwarded.set_type('message/rfc822')
        forwarded.set_payload([parts[0]])
        for part in [*parts, forwarded]:
            message.attach(part)
        message.send()

        self.assertEqual(parts[0]['Content-Transfer-Encoding'], '8bit')
        rebuilt = Email.objects.latest('id').email_message().message().get_payload()[1:]
        self.assertCountEqual(
            [
                (part['Content-ID'], part.get_filename(), part.get_payload(decode=True))
                for part in rebuilt
                if not part.is_multipart()
            ],
            [('<first>', 'same.bin', payload), ('<second>', 'same.bin', payload), ('<unnamed>', None, payload)],
        )
        self.assertCountEqual(
            [
                (part.get_content_type(), part.get_payload(0).get_payload(decode=True))
                for part in rebuilt
                if part.is_multipart()
            ],
            [('message/rfc822', payload)],
        )

    @override_settings(
        EMAIL_BACKEND='post_office.EmailBackend',
        POST_OFFICE={
            'DEFAULT_PRIORITY': 'now',
            'BACKENDS': {'default': 'django.core.mail.backends.dummy.EmailBackend'},
        },
    )
    def test_default_priority_now(self):
        # If DEFAULT_PRIORITY is "now", mails should be sent right away
        num_sent = send_mail('Test', 'Message', 'from1@example.com', ['to@example.com'])
        email = Email.objects.latest('id')
        self.assertEqual(email.status, STATUS.sent)
        self.assertEqual(num_sent, 1)

    @override_settings(
        EMAIL_BACKEND='post_office.EmailBackend',
        POST_OFFICE={
            'DEFAULT_PRIORITY': 'medium',
            'BACKENDS': {'default': 'django.core.mail.backends.dummy.EmailBackend'},
        },
    )
    @mock.patch('post_office.signals.email_queued.send')
    def test_email_queued_signal(self, mock):
        # If DEFAULT_PRIORITY is not "now", the email_queued signal should be sent
        send_mail('Test', 'Message', 'from1@example.com', ['to@example.com'])
        email = Email.objects.latest('id')
        self.assertEqual(email.status, STATUS.queued)
        self.assertEqual(mock.call_count, 1)
