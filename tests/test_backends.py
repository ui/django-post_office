import os
import unittest
import warnings
from email import policy
from email.message import MIMEPart
from email.mime.image import MIMEImage
from unittest import mock

from django.conf import settings
from django.core.files.images import File
from django.core.mail import EmailMessage, EmailMultiAlternatives, send_mail
from django.core.mail.backends.base import BaseEmailBackend
from django.test import TestCase
from django.test.utils import override_settings

from post_office.models import PRIORITY, STATUS, Email
from post_office.settings import PRE_DJANGO_6, get_backend, to_attachment_part


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

        message.attach('attachment.txt', b'attachment content')
        message.send()

        email = Email.objects.latest('id')
        self.assertEqual(email.attachments.count(), 1)
        self.assertEqual(email.attachments.all()[0].name, 'attachment.txt')
        self.assertEqual(email.attachments.all()[0].file.read(), b'attachment content')

    @override_settings(EMAIL_BACKEND='post_office.EmailBackend')
    def test_backend_image_attachments(self):
        message = EmailMessage('subject', 'body', 'from@example.com', ['recipient@example.com'])

        filename = os.path.join(os.path.dirname(__file__), 'static/dummy.png')
        fileobj = File(open(filename, 'rb'), name='dummy.png')
        image = MIMEImage(fileobj.read())
        image.add_header('Content-Disposition', 'inline', filename='dummy.png')
        image.add_header('Content-ID', '<{dummy.png}>')
        message.attach(image)
        message.send()

        email = Email.objects.latest('id')
        self.assertEqual(email.attachments.count(), 1)
        self.assertEqual(email.attachments.all()[0].name, 'dummy.png')
        self.assertEqual(email.attachments.all()[0].file.read(), image.get_payload().encode())
        self.assertEqual(email.attachments.all()[0].headers.get('Content-ID'), '<{dummy.png}>')
        self.assertEqual(email.attachments.all()[0].headers.get('Content-Disposition'), 'inline; filename="dummy.png"')

    @unittest.skipIf(PRE_DJANGO_6, 'MIMEPart attachments require Django >= 6.0')
    @override_settings(EMAIL_BACKEND='post_office.EmailBackend')
    def test_backend_mimepart_image_attachments(self):
        """Django 6+ apps attach email.message.MIMEPart instead of the deprecated MIMEBase."""
        message = EmailMessage('subject', 'body', 'from@example.com', ['recipient@example.com'])
        with open(os.path.join(os.path.dirname(__file__), 'static/dummy.png'), 'rb') as f:
            raw_image = f.read()
        image = MIMEPart()
        image.set_content(
            raw_image, maintype='image', subtype='png', disposition='inline', filename='dummy.png', cid='<{dummy.png}>'
        )
        message.attach(image)
        message.send()

        attachment = Email.objects.latest('id').attachments.get()
        self.assertEqual(attachment.name, 'dummy.png')
        self.assertEqual(attachment.mimetype, 'image/png')
        self.assertEqual(attachment.file.read(), image.get_payload().encode())
        self.assertEqual(attachment.headers.get('Content-ID'), '<{dummy.png}>')
        self.assertEqual(attachment.headers.get('Content-Disposition'), 'inline; filename="dummy.png"')

    @override_settings(EMAIL_BACKEND='post_office.EmailBackend')
    def test_backend_image_attachment_round_trip(self):
        """A stored image attachment is rebuilt into a sendable message with its original bytes."""
        with open(os.path.join(os.path.dirname(__file__), 'static/dummy.png'), 'rb') as f:
            raw_image = f.read()
        image = MIMEImage(raw_image)
        image.add_header('Content-Disposition', 'inline', filename='dummy.png')
        image.add_header('Content-ID', '<{dummy.png}>')
        message = EmailMessage('subject', 'body', 'from@example.com', ['recipient@example.com'])
        message.attach(to_attachment_part(image))
        message.send()

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            rebuilt = Email.objects.latest('id').email_message().message()
        self.assertEqual([str(w.message) for w in caught if 'MIMEBase' in str(w.message)], [])

        image_parts = [part for part in rebuilt.walk() if part.get_content_type() == 'image/png']
        self.assertEqual(len(image_parts), 1)
        self.assertEqual(image_parts[0].get_payload(decode=True), raw_image)
        self.assertEqual(image_parts[0]['Content-ID'], '<{dummy.png}>')
        self.assertEqual(image_parts[0].get_filename(), 'dummy.png')

    @override_settings(EMAIL_BACKEND='post_office.EmailBackend')
    def test_backend_mimepart_payload_round_trips(self):
        binary = MIMEPart(policy=policy.SMTP)
        binary.set_content(
            b'\x00\xff\x80\r\n', maintype='application', subtype='octet-stream', cte='8bit', filename='binary.bin'
        )
        multipart = MIMEPart()
        multipart.make_mixed()
        multipart.attach(binary)
        multipart.add_header('Content-Disposition', 'attachment', filename='bundle.mime')
        forwarded = MIMEPart()
        forwarded.set_type('message/rfc822')
        forwarded.set_payload([binary])
        forwarded.add_header('Content-Disposition', 'attachment', filename='forwarded.eml')
        unnamed = []
        for cid in ('<first>', '<second>'):
            part = MIMEPart()
            part.set_content(b'GIF89a', maintype='image', subtype='gif', disposition='inline', cid=cid)
            unnamed.append(part)

        for parts in ([binary], [multipart], [forwarded], unnamed):
            with self.subTest(content_types=[part.get_content_type() for part in parts]):
                message = EmailMessage('subject', 'body', 'from@example.com', ['recipient@example.com'])
                for part in parts:
                    if PRE_DJANGO_6:
                        # Exercise the backend directly; old Django attach() rejects MIMEPart.
                        message.attachments.append(part)
                    else:
                        message.attach(part)
                message.send()
                email = Email.objects.latest('id')
                self.assertEqual(email.attachments.count(), len(parts))
                attachments = email.email_message().attachments
                for original, rebuilt in zip(parts, attachments):
                    self.assertEqual(rebuilt.get_filename(), original.get_filename())
                    self.assertEqual(rebuilt['Content-ID'], original['Content-ID'])
                    self.assertEqual(rebuilt.get_content_type(), original.get_content_type())
                    self.assertEqual(
                        [part.get_payload(decode=True) for part in rebuilt.walk() if not part.is_multipart()],
                        [part.get_payload(decode=True) for part in original.walk() if not part.is_multipart()],
                    )
                self.assertEqual(binary['Content-Transfer-Encoding'], '8bit')

    def test_to_attachment_part(self):
        image = MIMEImage(b'GIF89a\x01\x00\x01\x00\x00\xff\x00,')
        image.add_header('Content-ID', '<logo>')
        part = to_attachment_part(image)
        if PRE_DJANGO_6:
            self.assertIs(part, image)
        else:
            self.assertIsInstance(part, MIMEPart)
            self.assertEqual(part['Content-ID'], '<logo>')
            self.assertEqual(part.get_content_type(), 'image/gif')
            self.assertEqual(part.get_payload(decode=True), image.get_payload(decode=True))

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
