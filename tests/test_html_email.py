import os
import unittest
from email.mime.image import MIMEImage

from django.contrib.auth import get_user_model
from django.core.files.images import ImageFile
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.test import Client, TestCase
from django.test.utils import override_settings
from django.urls import reverse

from post_office.mail import send, send_queued
from post_office.models import STATUS, Email, EmailTemplate
from post_office.settings import PRE_DJANGO_6
from post_office.template import render_to_string
from post_office.template.backends.post_office import PostOfficeTemplates

if PRE_DJANGO_6:
    from django.core.mail.message import SafeMIMEMultipart, SafeMIMEText


class HTMLMailTest(TestCase):
    def test_text(self):
        template = get_template('hello.html', using='post_office')
        self.assertIsInstance(template.backend, PostOfficeTemplates)
        context = {'foo': 'Bar'}
        content = template.render(context)
        self.assertHTMLEqual(content, '<h1>Bar</h1>')

    @unittest.skipUnless(PRE_DJANGO_6, 'Test for Django < 6.0')
    def test_html(self):
        template = get_template('image.html', using='post_office')
        body = template.render({'imgsrc': 'dummy.png'})
        self.assertHTMLEqual(
            body,
            """
<h3>Testing image attachments</h3>
<img src="cid:f5c66340b8af7dc946cd25d84fdf8c90" width="200" />
""",
        )
        subject = '[Django Post-Office unit tests] attached image'
        msg = EmailMultiAlternatives(subject, body, to=['john@example.com'])
        template.attach_related(msg)
        msg.content_subtype = 'html'
        self.assertEqual(msg.mixed_subtype, 'related')
        # this message can be send by email
        parts = msg.message().walk()
        part = next(parts)
        self.assertIsInstance(part, SafeMIMEMultipart)
        part = next(parts)
        self.assertIsInstance(part, SafeMIMEText)
        self.assertHTMLEqual(part.get_payload(), body)
        part = next(parts)
        self.assertIsInstance(part, MIMEImage)
        self.assertEqual(part.get_content_type(), 'image/png')
        self.assertEqual(part['Content-Disposition'], 'inline; filename="f5c66340b8af7dc946cd25d84fdf8c90"')
        self.assertEqual(part.get_content_disposition(), 'inline')
        self.assertEqual(part.get_filename(), 'f5c66340b8af7dc946cd25d84fdf8c90')
        self.assertEqual(part['Content-ID'], '<f5c66340b8af7dc946cd25d84fdf8c90>')

    @unittest.skipUnless(PRE_DJANGO_6, 'Test for Django < 6.0')
    def test_mixed(self):
        body = 'Testing mixed text and html attachments'
        html, attached_images = render_to_string('image.html', {'imgsrc': 'dummy.png'}, using='post_office')
        subject = '[django-SHOP unit tests] attached image'
        msg = EmailMultiAlternatives(subject, body, to=['john@example.com'])
        msg.attach_alternative(html, 'text/html')
        for attachment in attached_images:
            msg.attach(attachment)
        msg.mixed_subtype = 'related'
        # this message can be send by email
        parts = msg.message().walk()
        part = next(parts)
        self.assertIsInstance(part, SafeMIMEMultipart)
        part = next(parts)
        self.assertIsInstance(part, SafeMIMEMultipart)
        part = next(parts)
        self.assertIsInstance(part, SafeMIMEText)
        self.assertEqual(part.get_content_type(), 'text/plain')
        self.assertHTMLEqual(part.get_payload(), body)
        part = next(parts)
        self.assertIsInstance(part, SafeMIMEText)
        self.assertEqual(part.get_content_type(), 'text/html')
        self.assertHTMLEqual(part.get_payload(), html)
        part = next(parts)
        self.assertIsInstance(part, MIMEImage)
        self.assertEqual(part.get_content_type(), 'image/png')

    @unittest.skipUnless(PRE_DJANGO_6, 'Test for Django < 6.0')
    def test_image(self):
        relfilename = 'static/dummy.png'
        filename = os.path.join(os.path.dirname(__file__), relfilename)
        imagefile = ImageFile(open(filename, 'rb'), name=relfilename)
        template = get_template('image.html', using='post_office')
        body = template.render({'imgsrc': imagefile})
        self.assertHTMLEqual(
            body,
            """
<h3>Testing image attachments</h3>
<img src="cid:f5c66340b8af7dc946cd25d84fdf8c90" width="200" />
""",
        )
        subject = '[Django Post-Office unit tests] attached image'
        msg = EmailMultiAlternatives(subject, body, to=['john@example.com'])
        template.attach_related(msg)
        # this message can be send by email
        parts = msg.message().walk()
        part = next(parts)
        self.assertIsInstance(part, SafeMIMEMultipart)
        part = next(parts)
        self.assertIsInstance(part, SafeMIMEText)
        self.assertEqual(part.get_payload(), body)
        part = next(parts)
        self.assertIsInstance(part, MIMEImage)
        self.assertEqual(part.get_content_type(), 'image/png')
        self.assertEqual(part['Content-Disposition'], 'inline; filename="f5c66340b8af7dc946cd25d84fdf8c90"')
        self.assertEqual(part.get_content_disposition(), 'inline')
        self.assertEqual(part.get_filename(), 'f5c66340b8af7dc946cd25d84fdf8c90')
        self.assertEqual(part['Content-ID'], '<f5c66340b8af7dc946cd25d84fdf8c90>')

    @unittest.skipIf(PRE_DJANGO_6, 'Test for Django >= 6.0')
    def test_html_django6(self):
        """Django 6+ version: mixed_subtype removed, message() returns EmailMessage."""
        template = get_template('image.html', using='post_office')
        body = template.render({'imgsrc': 'dummy.png'})
        self.assertHTMLEqual(
            body,
            """
<h3>Testing image attachments</h3>
<img src="cid:f5c66340b8af7dc946cd25d84fdf8c90" width="200" />
""",
        )
        subject = '[Django Post-Office unit tests] attached image'
        msg = EmailMultiAlternatives(subject, body, to=['john@example.com'])
        template.attach_related(msg)
        msg.content_subtype = 'html'
        # mixed_subtype no longer exists in Django 6+
        # this message can be send by email
        message = msg.message()
        parts = list(message.walk())
        # Check that we have the expected parts: root, body, and image
        self.assertGreaterEqual(len(parts), 2)
        # Find the image part
        image_parts = [p for p in parts if p.get_content_type() == 'image/png']
        self.assertEqual(len(image_parts), 1)
        image_part = image_parts[0]
        self.assertEqual(image_part['Content-Disposition'], 'inline; filename="f5c66340b8af7dc946cd25d84fdf8c90"')
        self.assertEqual(image_part.get_content_disposition(), 'inline')
        self.assertEqual(image_part.get_filename(), 'f5c66340b8af7dc946cd25d84fdf8c90')
        self.assertEqual(image_part['Content-ID'], '<f5c66340b8af7dc946cd25d84fdf8c90>')

    @unittest.skipIf(PRE_DJANGO_6, 'Test for Django >= 6.0')
    def test_mixed_django6(self):
        """Django 6+ version: mixed_subtype removed, message() returns EmailMessage."""
        body = 'Testing mixed text and html attachments'
        html, attached_images = render_to_string('image.html', {'imgsrc': 'dummy.png'}, using='post_office')
        subject = '[django-SHOP unit tests] attached image'
        msg = EmailMultiAlternatives(subject, body, to=['john@example.com'])
        msg.attach_alternative(html, 'text/html')
        for attachment in attached_images:
            msg.attach(attachment)
        # mixed_subtype no longer exists in Django 6+
        # this message can be send by email
        message = msg.message()
        parts = list(message.walk())
        # Check that we have the expected content types
        content_types = [p.get_content_type() for p in parts]
        self.assertIn('text/plain', content_types)
        self.assertIn('text/html', content_types)
        self.assertIn('image/png', content_types)

    @unittest.skipIf(PRE_DJANGO_6, 'Test for Django >= 6.0')
    def test_image_django6(self):
        """Django 6+ version: message() returns EmailMessage instead of SafeMIME*."""
        relfilename = 'static/dummy.png'
        filename = os.path.join(os.path.dirname(__file__), relfilename)
        imagefile = ImageFile(open(filename, 'rb'), name=relfilename)
        template = get_template('image.html', using='post_office')
        body = template.render({'imgsrc': imagefile})
        self.assertHTMLEqual(
            body,
            """
<h3>Testing image attachments</h3>
<img src="cid:f5c66340b8af7dc946cd25d84fdf8c90" width="200" />
""",
        )
        subject = '[Django Post-Office unit tests] attached image'
        msg = EmailMultiAlternatives(subject, body, to=['john@example.com'])
        template.attach_related(msg)
        # this message can be send by email
        message = msg.message()
        parts = list(message.walk())
        # Find the image part
        image_parts = [p for p in parts if p.get_content_type() == 'image/png']
        self.assertEqual(len(image_parts), 1)
        image_part = image_parts[0]
        self.assertEqual(image_part['Content-Disposition'], 'inline; filename="f5c66340b8af7dc946cd25d84fdf8c90"')
        self.assertEqual(image_part.get_content_disposition(), 'inline')
        self.assertEqual(image_part.get_filename(), 'f5c66340b8af7dc946cd25d84fdf8c90')
        self.assertEqual(image_part['Content-ID'], '<f5c66340b8af7dc946cd25d84fdf8c90>')

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        POST_OFFICE={
            'BACKENDS': {'default': 'django.core.mail.backends.locmem.EmailBackend'},
            'TEMPLATE_ENGINE': 'post_office',
        },
    )
    def test_send_with_html_template(self):
        template = EmailTemplate.objects.create(
            name='Test Inlined Images',
            subject='[django-SHOP unit tests] attached image',
            html_content="""
{% load post_office %}
<h3>Testing image attachments</h3>
<img src="{% inline_image imgsrc %}" width="200" />""",
        )
        filename = os.path.join(os.path.dirname(__file__), 'static/dummy.png')
        context = {'imgsrc': filename}
        queued_mail = send(
            recipients=['to@example.com'],
            sender='from@example.com',
            template=template,
            context=context,
            render_on_delivery=True,
        )
        queued_mail = Email.objects.get(id=queued_mail.id)
        send_queued()
        self.assertEqual(Email.objects.get(id=queued_mail.id).status, STATUS.sent)


class EmailAdminTest(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.user = get_user_model().objects.create_superuser(
            username='testuser', password='secret', email='test@example.com'
        )
        self.client.force_login(self.user)

    @unittest.skipUnless(PRE_DJANGO_6, 'Test for Django < 6.0')
    @override_settings(EMAIL_BACKEND='post_office.EmailBackend')
    def test_email_change_view(self):
        template = get_template('image.html', using='post_office')
        body = template.render({'imgsrc': 'dummy.png'})
        subject = '[Django Post-Office unit tests] attached image'
        msg = EmailMultiAlternatives(subject, body, to=['john@example.com'])
        msg.content_subtype = 'html'
        template.attach_related(msg)
        msg.send()

        # check that in the Email's detail view, the message is rendered
        self.assertEqual(Email.objects.count(), 1)  # TODO: remove this
        email = Email.objects.latest('id')
        parts = email.email_message().message().walk()
        part = next(parts)
        self.assertIsInstance(part, SafeMIMEMultipart)
        part = next(parts)
        self.assertIsInstance(part, SafeMIMEText)
        part = next(parts)
        self.assertEqual(part.get_content_type(), 'image/png')
        content_id = part['Content-Id'][1:33]
        email_change_url = reverse('admin:post_office_email_change', args=(email.pk,))
        response = self.client.get(email_change_url, follow=True)
        self.assertContains(response, '[Django Post-Office unit tests] attached image')
        email_image_url = reverse('admin:post_office_email_image', kwargs={'pk': email.pk, 'content_id': content_id})
        self.assertContains(response, 'Testing image attachments')

        # check that inlined images are accessible through Django admin URL
        response = self.client.get(email_image_url)
        self.assertEqual(response.get('Content-Type'), 'image/png')

    @unittest.skipIf(PRE_DJANGO_6, 'Test for Django >= 6.0')
    @override_settings(EMAIL_BACKEND='post_office.EmailBackend')
    def test_email_change_view_django6(self):
        """Django 6+ version: message() returns EmailMessage instead of SafeMIME*."""
        template = get_template('image.html', using='post_office')
        body = template.render({'imgsrc': 'dummy.png'})
        subject = '[Django Post-Office unit tests] attached image'
        msg = EmailMultiAlternatives(subject, body, to=['john@example.com'])
        msg.content_subtype = 'html'
        template.attach_related(msg)
        msg.send()

        # check that in the Email's detail view, the message is rendered
        self.assertEqual(Email.objects.count(), 1)  # TODO: remove this
        email = Email.objects.latest('id')
        message = email.email_message().message()
        parts = list(message.walk())
        # Find the image part and get its content id
        image_parts = [p for p in parts if p.get_content_type() == 'image/png']
        self.assertEqual(len(image_parts), 1)
        content_id = image_parts[0]['Content-Id'][1:33]
        email_change_url = reverse('admin:post_office_email_change', args=(email.pk,))
        response = self.client.get(email_change_url, follow=True)
        self.assertContains(response, '[Django Post-Office unit tests] attached image')
        email_image_url = reverse('admin:post_office_email_image', kwargs={'pk': email.pk, 'content_id': content_id})
        self.assertContains(response, 'Testing image attachments')

        # check that inlined images are accessible through Django admin URL
        response = self.client.get(email_image_url)
        self.assertEqual(response.get('Content-Type'), 'image/png')
