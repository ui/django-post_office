from django.conf import settings as django_settings
from django.core import mail
from django.core.mail import EmailMultiAlternatives, get_connection
from django.test import TestCase
from django.test.utils import override_settings

from ..models import Email, Log, STATUS, PRIORITY, EmailTemplate


class ModelTest(TestCase):

    def test_email_message(self):
        """
        Test to make sure that model's "email_message" method
        returns proper ``EmailMultiAlternatives`` with html attachment.
        """

        email = Email.objects.create(to='to@example.com',
            from_email='from@example.com', subject='Subject',
            message='Message', html_message='<p>HTML</p>')
        message = email.email_message()
        self.assertTrue(isinstance(message, EmailMultiAlternatives))
        self.assertEqual(message.from_email, 'from@example.com')
        self.assertEqual(message.to, ['to@example.com'])
        self.assertEqual(message.subject, 'Subject')
        self.assertEqual(message.body, 'Message')
        self.assertEqual(message.alternatives, [('<p>HTML</p>', 'text/html')])


    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_dispatch(self):
        """
        Ensure that email.dispatch() actually sends out the email
        """
        email = Email.objects.create(to='to@example.com', from_email='from@example.com',
                                     subject='Test dispatch', message='Message')
        email.dispatch()
        self.assertEqual(mail.outbox[0].subject, 'Test dispatch')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_status_and_log(self):
        """
        Ensure that status and log are set properly on successful sending
        """
        email = Email.objects.create(to='to@example.com', from_email='from@example.com',
                                     subject='Test', message='Message')
        # Ensure that after dispatch status and logs are correctly set
        email.dispatch()
        log = Log.objects.latest('id')
        self.assertEqual(email.status, STATUS.sent)
        self.assertEqual(log.email, email)

    @override_settings(EMAIL_BACKEND='post_office.tests.backends.ErrorRaisingBackend')
    def test_status_and_log_on_error(self):
        """
        Ensure that status and log are set properly on sending failure
        """
        email = Email.objects.create(to='to@example.com', from_email='from@example.com',
                                     subject='Test', message='Message')
        # Ensure that after dispatch status and logs are correctly set
        email.dispatch()
        log = Log.objects.latest('id')
        self.assertEqual(email.status, STATUS.failed)
        self.assertEqual(log.email, email)
        self.assertEqual(log.status, STATUS.failed)
        self.assertEqual(log.message, 'Fake Error')

    def test_dispatch_uses_opened_connection(self):
        """
        Test that the ``dispatch`` method uses the argument supplied connection.
        We test this by overriding the email backend with a dummy backend,
        but passing in a previously opened connection from locmem backend.
        """
        email = Email.objects.create(to='to@example.com', from_email='from@example.com',
                                     subject='Test', message='Message')
        django_settings.EMAIL_BACKEND = \
            'django.core.mail.backends.dummy.EmailBackend'
        email.dispatch()
        # Outbox should be empty since dummy backend doesn't do anything
        self.assertEqual(len(mail.outbox), 0)

        # Message should go to outbox since locmem connection is explicitly passed in
        connection = get_connection('django.core.mail.backends.locmem.EmailBackend')
        email.dispatch(connection=connection)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(EMAIL_BACKEND='random.backend')
    def test_errors_while_getting_connection_are_logged(self):
        """
        Ensure that status and log are set properly on sending failure
        """
        email = Email.objects.create(to='to@example.com', from_email='from@example.com',
                                     subject='Test', message='Message')
        # Ensure that after dispatch status and logs are correctly set
        email.dispatch()
        log = Log.objects.latest('id')
        self.assertEqual(email.status, STATUS.failed)
        self.assertEqual(log.email, email)
        self.assertEqual(log.status, STATUS.failed)
        self.assertIn('does not define a "backend" class', log.message)

    def test_email_template(self):
        """
        Ensure that when saving email template, cache are set
        """
        EmailTemplate.objects.create(name='customer/en/welcome', content='test')


