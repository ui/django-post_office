import django
import json
import os

from datetime import datetime, timedelta

from django.conf import settings as django_settings, settings
from django.core import mail
from django.core import serializers
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.forms.models import modelform_factory
from django.test import TestCase
from django.utils import timezone

from ..models import Email, Log, PRIORITY, STATUS, EmailTemplate, Attachment
from ..mail import send


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

    def test_dispatch(self):
        """
        Ensure that email.dispatch() actually sends out the email
        """
        email = Email.objects.create(to=['to@example.com'], from_email='from@example.com',
                                     subject='Test dispatch', message='Message', backend_alias='locmem')
        email.dispatch()
        self.assertEqual(mail.outbox[0].subject, 'Test dispatch')

    def test_dispatch_with_override_recipients(self):
        previous_settings = settings.POST_OFFICE
        setattr(settings, 'POST_OFFICE', {'OVERRIDE_RECIPIENTS': ['override@gmail.com']})
        email = Email.objects.create(to=['to@example.com'], from_email='from@example.com',
                                     subject='Test dispatch', message='Message', backend_alias='locmem')
        email.dispatch()
        self.assertEqual(mail.outbox[0].to, ['override@gmail.com'])
        settings.POST_OFFICE = previous_settings

    def test_status_and_log(self):
        """
        Ensure that status and log are set properly on successful sending
        """
        email = Email.objects.create(to=['to@example.com'], from_email='from@example.com',
                                     subject='Test', message='Message', backend_alias='locmem', id=333)
        # Ensure that after dispatch status and logs are correctly set
        email.dispatch()
        log = Log.objects.latest('id')
        self.assertEqual(email.status, STATUS.sent)
        self.assertEqual(log.email, email)

    def test_status_and_log_on_error(self):
        """
        Ensure that status and log are set properly on sending failure
        """
        email = Email.objects.create(to=['to@example.com'], from_email='from@example.com',
                                     subject='Test', message='Message',
                                     backend_alias='error')
        # Ensure that after dispatch status and logs are correctly set
        email.dispatch()
        log = Log.objects.latest('id')
        self.assertEqual(email.status, STATUS.failed)
        self.assertEqual(log.email, email)
        self.assertEqual(log.status, STATUS.failed)
        self.assertEqual(log.message, 'Fake Error')
        self.assertEqual(log.exception_type, 'Exception')

    def test_errors_while_getting_connection_are_logged(self):
        """
        Ensure that status and log are set properly on sending failure
        """
        email = Email.objects.create(to=['to@example.com'], subject='Test',
                                     from_email='from@example.com',
                                     message='Message', backend_alias='random')
        # Ensure that after dispatch status and logs are correctly set
        email.dispatch()
        log = Log.objects.latest('id')
        self.assertEqual(email.status, STATUS.failed)
        self.assertEqual(log.email, email)
        self.assertEqual(log.status, STATUS.failed)
        self.assertIn('is not a valid', log.message)

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

        self.assertEqual(form.errors['default_template'],  ['This field is required.'])
        self.assertEqual(form.errors['content'], ["Invalid filter: 'titl'"])
        self.assertIn(form.errors['html_content'],
                      [['Unclosed tags: endblock '],
                       ["Unclosed tag on line 1: 'block'. Looking for one of: endblock."]])
        self.assertIn(form.errors['subject'],
                      [['Empty variable tag'], ['Empty variable tag on line 1']])

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

    def test_send_recipient_display_name(self):
        """
        Regression test for:
        https://github.com/ui/django-post_office/issues/73
        """
        email = send(recipients=['Alice Bob <email@example.com>'], sender='from@a.com')
        self.assertTrue(email.to)

    def test_attachment_filename(self):
        attachment = Attachment()

        attachment.file.save(
            'test.txt',
            content=ContentFile('test file content'),
            save=True
        )
        self.assertEqual(attachment.name, 'test.txt')

        # Test that it is saved to the correct subdirectory
        date = timezone.now().date()
        expected_path = os.path.join('post_office_attachments', str(date.year),
                                     str(date.month), str(date.day))
        self.assertTrue(expected_path in attachment.file.name)

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
                         [('test.txt', 'test file content', 'text/plain')])

    def test_attachments_email_message_with_mimetype(self):
        email = Email.objects.create(to=['to@example.com'],
                                     from_email='from@example.com',
                                     subject='Subject')

        attachment = Attachment()
        attachment.file.save(
            'test.txt', content=ContentFile('test file content'), save=True
        )
        attachment.mimetype = 'text/plain'
        attachment.save()
        email.attachments.add(attachment)
        message = email.email_message()

        self.assertEqual(message.attachments,
                         [('test.txt', 'test file content', 'text/plain')])

    def test_translated_template_uses_default_templates_name(self):
        template = EmailTemplate.objects.create(name='name')
        id_template = template.translated_templates.create(language='id')
        self.assertEqual(id_template.name, template.name)

    def test_models_repr(self):
        self.assertEqual(repr(EmailTemplate(name='test', language='en')),
                         '<EmailTemplate: test en>')
        self.assertEqual(repr(Email(to=['test@example.com'])),
                         "<Email: ['test@example.com']>")

    def test_natural_key(self):
        template = EmailTemplate.objects.create(name='name')
        self.assertEqual(template, EmailTemplate.objects.get_by_natural_key(*template.natural_key()))

        data = serializers.serialize('json', [template], use_natural_primary_keys=True)
        self.assertNotIn('pk', json.loads(data)[0])
        deserialized_objects = serializers.deserialize('json', data, use_natural_primary_keys=True)
        list(deserialized_objects)[0].save()
        self.assertEqual(EmailTemplate.objects.count(), 1)
