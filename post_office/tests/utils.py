from django.core import mail
from django.core.exceptions import ValidationError
from django.template import TemplateDoesNotExist

from django.test import TestCase
from django.test.utils import override_settings

from ..models import Email, STATUS, PRIORITY, EmailTemplate
from ..utils import send_mail, send_queued_mail, get_email_template, send_templated_mail
from ..validators import validate_email_with_name


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class UtilsTest(TestCase):

    def test_mail_status(self):
        """
        Check that send_mail assigns the right status field to Email instances
        """
        send_mail('subject', 'message', 'from@example.com', ['to@example.com'],
                  priority=PRIORITY.medium)
        email = Email.objects.latest('id')
        self.assertEqual(email.status, STATUS.queued)

        # Emails sent with "now" priority don't get sent right away
        send_mail('subject', 'message', 'from@example.com', ['to@example.com'],
                  priority=PRIORITY.now)
        email = Email.objects.latest('id')
        self.assertEqual(email.status, STATUS.sent)

    def test_send_queued_mail(self):
        """
        Check that only queued messages are sent.
        """
        Email.objects.create(to='to@example.com', from_email='from@example.com',
            subject='Test', message='Message', status=STATUS.sent)
        Email.objects.create(to='to@example.com', from_email='from@example.com',
            subject='Test', message='Message', status=STATUS.failed)
        Email.objects.create(to='to@example.com', from_email='from@example.com',
            subject='Test', message='Message', status=None)

        # This should be the only email that gets sent
        Email.objects.create(to='to@example.com', from_email='from@example.com',
            subject='Queued', message='Message', status=STATUS.queued)
        send_queued_mail()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Queued')

    def test_email_validator(self):
        # These should validate
        validate_email_with_name('email@example.com')
        validate_email_with_name('Alice Bob <email@example.com>')
        Email.objects.create(to='to@example.com', from_email='Alice <from@example.com>',
            subject='Test', message='Message', status=STATUS.sent)

        # Should also support international domains
        validate_email_with_name('Alice Bob <email@example.co.id>')

        # These should raise ValidationError
        self.assertRaises(ValidationError, validate_email_with_name, 'invalid_mail')
        self.assertRaises(ValidationError, validate_email_with_name, 'Alice <invalid_mail>')

    def test_get_template_email(self):
        template_name = 'customer/en/happy-holidays'
        self.assertRaises(EmailTemplate.DoesNotExist, get_email_template, template_name)
        email_template = EmailTemplate.objects.create(name=template_name, content='Happy Holiday!')
        self.assertEqual(email_template, get_email_template(template_name))

    def test_send_templated_email(self):
        template_name = 'customer/en/happy-holidays'
        to_addresses = ['to@example1.com', 'to@example2.com']
        EmailTemplate.objects.create(name=template_name,
            content='Hi {{name}}', html_content='<p>Hi {{name}}</p>',
            subject='Happy Holidays!')
        send_templated_mail(template_name, 'from@example.com',
            to_addresses,
            priority=PRIORITY.medium, context={'name': 'AwesomeBoy'})
        send_queued_mail()
        self.assertEqual(len(mail.outbox), 2)

        for email, to_address in zip(mail.outbox, to_addresses):
            self.assertEqual(email.subject, 'Happy Holidays!')
            self.assertEqual(email.body, 'Hi AwesomeBoy')
            self.assertEqual(email.alternatives, [('<p>Hi AwesomeBoy</p>', 'text/html')])
            self.assertEqual(email.to, [to_address])
