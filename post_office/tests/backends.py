from django.conf import settings
from django.core.mail import backends, EmailMultiAlternatives, send_mail
from django.test import TestCase
from django.test.utils import override_settings

from ..models import Email, STATUS, PRIORITY
from ..settings import get_email_backend


class ErrorRaisingBackend(backends.base.BaseEmailBackend):
    '''
    An EmailBackend that always raises an error during sending
    to test if django_mailer handles sending error correctly
    '''
    def send_messages(self, email_messages):
        raise Exception('Fake Error')


class BackendTest(TestCase):

    @override_settings(EMAIL_BACKEND='post_office.EmailBackend')
    def test_email_backend(self):
        """
        Ensure that email backend properly queue email messages.
        """
        send_mail('Test backend', 'Message', 'from@example.com', ['to@example.com'])
        email = Email.objects.latest('id')
        self.assertEqual(email.subject, 'Test backend')
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
        # If no email backend is set, backend should default to SMTP
        self.assertEqual(get_email_backend(), 'django.core.mail.backends.smtp.EmailBackend')

        # If EMAIL_BACKEND is set to PostOfficeBackend, use SMTP to send by default
        setattr(settings, 'EMAIL_BACKEND', 'post_office.EmailBackend')
        self.assertEqual(get_email_backend(), 'django.core.mail.backends.smtp.EmailBackend')

        # If POST_OFFICE_BACKEND is given, use that
        setattr(settings, 'POST_OFFICE_BACKEND', 'whatever.Whatever')
        self.assertEqual(get_email_backend(), 'whatever.Whatever')

        if old_email_backend:
            setattr(settings, 'EMAIL_BACKEND', old_email_backend)
        else:
            delattr(settings, 'EMAIL_BACKEND')

        if old_post_office_backend:
            setattr(settings, 'POST_OFFICE_BACKEND', old_post_office_backend)
        else:
            delattr(settings, 'POST_OFFICE_BACKEND')

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
