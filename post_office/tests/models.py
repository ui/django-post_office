from datetime import datetime, timedelta

from django.conf import settings as django_settings
from django.core import mail
from django.core.mail import EmailMultiAlternatives, get_connection
from django.forms.models import modelform_factory
from django.test import TestCase
from django.test.utils import override_settings

from ..models import Email, Log, PRIORITY, STATUS, EmailTemplate
from ..mail import from_template, send


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

    def test_from_template(self):
        """
        Test basic constructing email message with template
        """

        # Test 1, create email object from template, without context
        email_template = EmailTemplate.objects.create(name='welcome',
            subject='Welcome!', content='Hi there!')
        email = from_template('from@example.com', 'to@example.com', email_template)
        self.assertEqual(email.from_email, 'from@example.com')
        self.assertEqual(email.to, 'to@example.com')
        self.assertEqual(email.subject, 'Welcome!')
        self.assertEqual(email.message, 'Hi there!')

        # Passing in template name also works
        email = from_template('from2@example.com', 'to2@example.com',
                              email_template.name)
        self.assertEqual(email.from_email, 'from2@example.com')
        self.assertEqual(email.to, 'to2@example.com')
        self.assertEqual(email.subject, 'Welcome!')
        self.assertEqual(email.message, 'Hi there!')

        # Ensure that subject, message and html_message are correctly rendered
        email_template.subject = "Subject: {{foo}}"
        email_template.content = "Message: {{foo}}"
        email_template.html_content = "HTML: {{foo}}"
        email_template.save()
        email = from_template('from@example.com', 'to@example.com',
                              email_template, context={'foo': 'bar'})

        self.assertEqual(email.subject, 'Subject: bar')
        self.assertEqual(email.message, 'Message: bar')
        self.assertEqual(email.html_message, 'HTML: bar')

    def test_default_sender(self):
        emails = send(['to@example.com'], subject='foo')
        self.assertEqual(emails[0].from_email,
                         django_settings.DEFAULT_FROM_EMAIL)

    def test_send_argument_checking(self):
        """
        mail.send() should raise an Exception if:
        - "template" is used with "subject", "message" or "html_message"
        - recipients is not in tuple or list format
        """
        self.assertRaises(ValueError, send, ['to@example.com'], 'from@a.com',
                          template='foo', subject='bar')
        self.assertRaises(ValueError, send, ['to@example.com'], 'from@a.com',
                          template='foo', message='bar')
        self.assertRaises(ValueError, send, ['to@example.com'], 'from@a.com',
                          template='foo', html_message='bar')
        self.assertRaises(ValueError, send, 'to@example.com', 'from@a.com',
                          template='foo', html_message='bar')

    def test_send_with_template(self):
        """
        Ensure mail.send correctly creates templated emails to recipients
        """
        Email.objects.all().delete()
        headers = {'Reply-to': 'reply@email.com'}
        email_template = EmailTemplate.objects.create(name='foo', subject='bar',
                                                      content='baz')
        scheduled_time = datetime.now() + timedelta(days=1)
        emails = send(['to1@example.com', 'to2@example.com'], 'from@a.com',
                      headers=headers, template=email_template,
                      scheduled_time=scheduled_time)
        self.assertEqual(len(emails), 2)
        self.assertEqual(emails[0].to, 'to1@example.com')
        self.assertEqual(emails[0].headers, headers)
        self.assertEqual(emails[0].scheduled_time, scheduled_time)

        self.assertEqual(emails[1].to, 'to2@example.com')
        self.assertEqual(emails[1].headers, headers)

        # Test without header
        Email.objects.all().delete()
        emails = send(['to1@example.com', 'to2@example.com'], 'from@a.com',
                      template=email_template)
        self.assertEqual(len(emails), 2)
        self.assertEqual(emails[0].to, 'to1@example.com')
        self.assertEqual(emails[0].headers, None)

        self.assertEqual(emails[1].to, 'to2@example.com')
        self.assertEqual(emails[1].headers, None)

    def test_send_without_template(self):
        headers = {'Reply-to': 'reply@email.com'}
        scheduled_time = datetime.now() + timedelta(days=1)        
        emails = send(['to1@example.com', 'to2@example.com'], 'from@a.com',
                      subject='foo', message='bar', html_message='baz',
                      context={'name': 'Alice'}, headers=headers,
                      scheduled_time=scheduled_time, priority=PRIORITY.low)

        self.assertEqual(len(emails), 2)
        self.assertEqual(emails[0].to, 'to1@example.com')
        self.assertEqual(emails[0].subject, 'foo')
        self.assertEqual(emails[0].message, 'bar')
        self.assertEqual(emails[0].html_message, 'baz')
        self.assertEqual(emails[0].headers, headers)
        self.assertEqual(emails[0].priority, PRIORITY.low)
        self.assertEqual(emails[0].scheduled_time, scheduled_time)
        self.assertEqual(emails[1].to, 'to2@example.com')

        # Same thing, but now with context
        emails = send(['to1@example.com'], 'from@a.com',
                      subject='Hi {{ name }}', message='Message {{ name }}',
                      html_message='<b>{{ name }}</b>',
                      context={'name': 'Bob'}, headers=headers)
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0].to, 'to1@example.com')
        self.assertEqual(emails[0].subject, 'Hi Bob')
        self.assertEqual(emails[0].message, 'Message Bob')
        self.assertEqual(emails[0].html_message, '<b>Bob</b>')
        self.assertEqual(emails[0].headers, headers)

    def test_invalid_syntax(self):
        """
        Ensures that invalid template syntax will result in validation errors
        when saving a ModelForm of an EmailTemplate.
        """
        data = dict(
            name='cost',
            subject='Hi there!{{ }}',
            content='Welcome {{ name|titl }} to the site.',
            html_content='{% block content %}<h1>Welcome to the site</h1>'
        )

        EmailTemplateForm = modelform_factory(EmailTemplate)
        form = EmailTemplateForm(data)

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {
            'subject': [u"Empty variable tag"],
            'content': [u"Invalid filter: 'titl'"],
            'html_content': [u"Unclosed tags: endblock "]
        })

    def test_string_priority(self):
        """
        Regression test for:
        https://github.com/ui/django-post_office/issues/23
        """
        emails = send(['to1@example.com'], 'from@a.com', priority='low')

        self.assertEquals(emails[0].priority, PRIORITY.low)

    def test_string_priority_exception(self):
        invalid_priority_send = lambda: send(['to1@example.com'], 'from@a.com', priority='hgh')

        with self.assertRaises(ValueError) as context:
            invalid_priority_send()

        self.assertEquals(
            str(context.exception),
            'Invalid priority, must be one of: low, medium, high, now'
        )
