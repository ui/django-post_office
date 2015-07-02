from datetime import datetime, timedelta

from django.conf import settings as django_settings
from django.core import mail
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage, EmailMultiAlternatives, get_connection
from django.forms.models import modelform_factory
from django.test import TestCase
from django.test.utils import override_settings

from ..models import Email, Log, PRIORITY, STATUS, EmailTemplate, Attachment
from ..mail import send, _send_bulk


class ModelTest(TestCase):

    def test_email_message(self):
        """
        Test to make sure that model's "email_message" method
        returns proper email classes.
        """

        # If ``html_message`` is set, ``EmailMultiAlternatives`` is expected
        email = Email.objects.create(to=['to@example.com'],
                                     from_email='from@example.com', subject='Subject',
                                     message='Message', html_message='<p>HTML</p>')
        message = email.email_message()
        self.assertEqual(type(message), EmailMultiAlternatives)
        self.assertEqual(message.from_email, 'from@example.com')
        self.assertEqual(message.to, ['to@example.com'])
        self.assertEqual(message.subject, 'Subject')
        self.assertEqual(message.body, 'Message')
        self.assertEqual(message.alternatives, [('<p>HTML</p>', 'text/html')])

        # Without ``html_message``, ``EmailMessage`` class is expected
        email = Email.objects.create(to=['to@example.com'],
                                     from_email='from@example.com', subject='Subject',
                                     message='Message')
        message = email.email_message()
        self.assertEqual(type(message), EmailMessage)
        self.assertEqual(message.from_email, 'from@example.com')
        self.assertEqual(message.to, ['to@example.com'])
        self.assertEqual(message.subject, 'Subject')
        self.assertEqual(message.body, 'Message')

    def test_email_message_render(self):
        """
        Ensure Email instance with template is properly rendered.
        """
        template = EmailTemplate.objects.create(
            subject='Subject {{ name }}',
            content='Content {{ name }}',
            html_content='HTML {{ name }}'
        )
        context = {'name': 'test'}
        email = Email.objects.create(to=['to@example.com'], template=template,
                                     from_email='from@e.com', context=context)
        message = email.email_message()
        self.assertEqual(message.subject, 'Subject test')
        self.assertEqual(message.body, 'Content test')
        self.assertEqual(message.alternatives[0][0], 'HTML test')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_dispatch(self):
        """
        Ensure that email.dispatch() actually sends out the email
        """
        email = Email.objects.create(to=['to@example.com'], from_email='from@example.com',
                                     subject='Test dispatch', message='Message')
        email.dispatch()
        self.assertEqual(mail.outbox[0].subject, 'Test dispatch')

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_status_and_log(self):
        """
        Ensure that status and log are set properly on successful sending
        """
        email = Email.objects.create(to=['to@example.com'], from_email='from@example.com',
                                     subject='Test', message='Message')
        # Ensure that after dispatch status and logs are correctly set
        email.dispatch()
        log = Log.objects.latest('id')
        self.assertEqual(email.status, STATUS.sent)
        self.assertEqual(log.email, email)

    @override_settings(EMAIL_BACKEND='post_office.tests.test_backends.ErrorRaisingBackend')
    def test_status_and_log_on_error(self):
        """
        Ensure that status and log are set properly on sending failure
        """
        email = Email.objects.create(to=['to@example.com'], from_email='from@example.com',
                                     subject='Test', message='Message')
        # Ensure that after dispatch status and logs are correctly set
        email.dispatch()
        log = Log.objects.latest('id')
        self.assertEqual(email.status, STATUS.failed)
        self.assertEqual(log.email, email)
        self.assertEqual(log.status, STATUS.failed)
        self.assertEqual(log.message, 'Fake Error')
        self.assertEqual(log.exception_type, 'Exception')

    def test_dispatch_uses_opened_connection(self):
        """
        Test that the ``dispatch`` method uses the argument supplied connection.
        We test this by overriding the email backend with a dummy backend,
        but passing in a previously opened connection from locmem backend.
        """
        email = Email.objects.create(to=['to@example.com'], from_email='from@example.com',
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
        email = Email.objects.create(to=['to@example.com'], from_email='from@example.com',
                                     subject='Test', message='Message')
        # Ensure that after dispatch status and logs are correctly set
        email.dispatch()
        log = Log.objects.latest('id')
        self.assertEqual(email.status, STATUS.failed)
        self.assertEqual(log.email, email)
        self.assertEqual(log.status, STATUS.failed)
        self.assertIn('does not define a "backend"', log.message)

    def test_default_sender(self):
        email = send(['to@example.com'], subject='foo')
        self.assertEqual(email.from_email,
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
        self.assertRaises(ValueError, send, cc='cc@example.com', sender='from@a.com',
                          template='foo', html_message='bar')
        self.assertRaises(ValueError, send, bcc='bcc@example.com', sender='from@a.com',
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
        email = send(recipients=['to1@example.com', 'to2@example.com'], sender='from@a.com',
                     headers=headers, template=email_template,
                     scheduled_time=scheduled_time)
        self.assertEqual(email.to, ['to1@example.com', 'to2@example.com'])
        self.assertEqual(email.headers, headers)
        self.assertEqual(email.scheduled_time, scheduled_time)

        # Test without header
        Email.objects.all().delete()
        email = send(recipients=['to1@example.com', 'to2@example.com'], sender='from@a.com',
                     template=email_template)
        self.assertEqual(email.to, ['to1@example.com', 'to2@example.com'])
        self.assertEqual(email.headers, None)

    def test_send_without_template(self):
        headers = {'Reply-to': 'reply@email.com'}
        scheduled_time = datetime.now() + timedelta(days=1)
        email = send(sender='from@a.com',
                     recipients=['to1@example.com', 'to2@example.com'],
                     cc=['cc1@example.com', 'cc2@example.com'],
                     bcc=['bcc1@example.com', 'bcc2@example.com'],
                     subject='foo', message='bar', html_message='baz',
                     context={'name': 'Alice'}, headers=headers,
                     scheduled_time=scheduled_time, priority=PRIORITY.low)

        self.assertEqual(email.to, ['to1@example.com', 'to2@example.com'])
        self.assertEqual(email.cc, ['cc1@example.com', 'cc2@example.com'])
        self.assertEqual(email.bcc, ['bcc1@example.com', 'bcc2@example.com'])
        self.assertEqual(email.subject, 'foo')
        self.assertEqual(email.message, 'bar')
        self.assertEqual(email.html_message, 'baz')
        self.assertEqual(email.headers, headers)
        self.assertEqual(email.priority, PRIORITY.low)
        self.assertEqual(email.scheduled_time, scheduled_time)

        # Same thing, but now with context
        email = send(['to1@example.com'], 'from@a.com',
                     subject='Hi {{ name }}', message='Message {{ name }}',
                     html_message='<b>{{ name }}</b>',
                     context={'name': 'Bob'}, headers=headers)
        self.assertEqual(email.to, ['to1@example.com'])
        self.assertEqual(email.subject, 'Hi Bob')
        self.assertEqual(email.message, 'Message Bob')
        self.assertEqual(email.html_message, '<b>Bob</b>')
        self.assertEqual(email.headers, headers)

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

        EmailTemplateForm = modelform_factory(EmailTemplate,
                                              exclude=['template'])
        form = EmailTemplateForm(data)

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {
            'default_template': [u'This field is required.'],
            'content': [u"Invalid filter: 'titl'"],
            'html_content': [u'Unclosed tags: endblock '],
            'language': [u'This field is required.'],
            'subject': [u'Empty variable tag']
        })

    def test_string_priority(self):
        """
        Regression test for:
        https://github.com/ui/django-post_office/issues/23
        """
        email = send(['to1@example.com'], 'from@a.com', priority='low')
        self.assertEqual(email.priority, PRIORITY.low)

    def test_default_priority(self):
        email = send(recipients=['to1@example.com'], sender='from@a.com')
        self.assertEqual(email.priority, PRIORITY.medium)

    def test_string_priority_exception(self):
        invalid_priority_send = lambda: send(['to1@example.com'], 'from@a.com', priority='hgh')

        with self.assertRaises(ValueError) as context:
            invalid_priority_send()

        self.assertEqual(
            str(context.exception),
            'Invalid priority, must be one of: low, medium, high, now'
        )

    def test_attachment_filename(self):
        attachment = Attachment()

        attachment.file.save(
            'test.txt',
            content=ContentFile('test file content'),
            save=True
        )
        self.assertEquals(attachment.name, 'test.txt')

    def test_attachments_email_message(self):
        email = Email.objects.create(to=['to@example.com'],
                                     from_email='from@example.com',
                                     subject='Subject')

        attachment = Attachment()
        attachment.file.save(
            'test.txt', content=ContentFile('test file content'), save=True
        )
        email.attachments.add(attachment)
        message = email.email_message()

        self.assertEqual(message.attachments,
                         [('test.txt', b'test file content', None)])
