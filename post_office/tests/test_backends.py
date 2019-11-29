import os
from email.mime.image import MIMEImage
from django.conf import settings
from django.core.files.images import File
from django.core.mail import EmailMultiAlternatives, send_mail, EmailMessage
from django.core.mail.backends.base import BaseEmailBackend
from django.test import TestCase
from django.test.utils import override_settings

from ..models import Email, STATUS, PRIORITY
from ..settings import get_backend


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

    def test_email_backend_setting(self):
        """

        """
        old_email_backend = getattr(settings, 'EMAIL_BACKEND', None)
        old_post_office_backend = getattr(settings, 'POST_OFFICE_BACKEND', None)
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

    @override_settings(EMAIL_BACKEND='post_office.EmailBackend')
    def test_sending_html_email(self):
        """
        "text/html" attachments to Email should be persisted into the database
        """
        message = EmailMultiAlternatives('subject', 'body', 'from@example.com',
                                         ['recipient@example.com'])
        message.attach_alternative('html', "text/html")
        message.send()
        email = Email.objects.latest('id')
        self.assertEqual(email.html_message, 'html')

    @override_settings(EMAIL_BACKEND='post_office.EmailBackend')
    def test_headers_sent(self):
        """
        Test that headers are correctly set on the outgoing emails.
        """
        message = EmailMessage('subject', 'body', 'from@example.com',
                               ['recipient@example.com'],
                               headers={'Reply-To': 'reply@example.com'})
        message.send()
        email = Email.objects.latest('id')
        self.assertEqual(email.headers, {'Reply-To': 'reply@example.com'})

    @override_settings(EMAIL_BACKEND='post_office.EmailBackend')
    def test_backend_attachments(self):
        message = EmailMessage('subject', 'body', 'from@example.com',
                               ['recipient@example.com'])

        message.attach('attachment.txt', b'attachment content')
        message.send()

        email = Email.objects.latest('id')
        self.assertEqual(email.attachments.count(), 1)
        self.assertEqual(email.attachments.all()[0].name, 'attachment.txt')
        self.assertEqual(email.attachments.all()[0].file.read(), b'attachment content')

    @override_settings(EMAIL_BACKEND='post_office.EmailBackend')
    def test_backend_image_attachments(self):
        message = EmailMessage('subject', 'body', 'from@example.com',
                               ['recipient@example.com'])

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

    @override_settings(
        EMAIL_BACKEND='post_office.EmailBackend',
        POST_OFFICE={
            'DEFAULT_PRIORITY': 'now',
            'BACKENDS': {'default': 'django.core.mail.backends.dummy.EmailBackend'}
        }
    )
    def test_default_priority_now(self):
        # If DEFAULT_PRIORITY is "now", mails should be sent right away
        send_mail('Test', 'Message', 'from1@example.com', ['to@example.com'])
        email = Email.objects.latest('id')
        self.assertEqual(email.status, STATUS.sent)
