import base64
import os
import unittest
from email.mime.image import MIMEImage

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
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

    def _send_html_email(self, html_message):
        return send(
            recipients=['john@example.com'],
            subject='HTML preview',
            message='Plain text body',
            html_message=html_message,
        )

    def test_email_preview_view(self):
        """The preview view serves the HTML body unsanitized, in a sandboxed document."""
        email = self._send_html_email(
            '<html><head><style>h1 { color: red; }</style></head><body><h1>Styled</h1></body></html>'
        )
        response = self.client.get(reverse('admin:post_office_email_preview', args=[email.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Type'].startswith('text/html'))
        self.assertTrue(response['Content-Security-Policy'].startswith('sandbox'))
        # Unlike the inline admin preview, the <style> block must survive.
        self.assertContains(response, '<style>h1 { color: red; }</style>')

    @override_settings(EMAIL_BACKEND='post_office.EmailBackend')
    def test_email_preview_view_inline_image(self):
        """cid: references are replaced by data: URIs, since the sandboxed preview cannot use the session."""
        template = get_template('image.html', using='post_office')
        body = template.render({'imgsrc': 'dummy.png'})
        msg = EmailMultiAlternatives('attached image', 'Plain text body', to=['john@example.com'])
        msg.attach_alternative(body, 'text/html')
        template.attach_related(msg)
        msg.send()

        email = Email.objects.latest('id')
        image_parts = [p for p in email.email_message().message().walk() if p.get_content_type() == 'image/png']
        image_data = base64.b64encode(image_parts[0].get_payload(decode=True)).decode('ascii')

        response = self.client.get(reverse('admin:post_office_email_preview', args=[email.pk]))
        self.assertContains(response, 'Testing image attachments')
        self.assertContains(response, f'src="data:image/png;base64,{image_data}"')
        self.assertNotContains(response, 'cid:')

    def _send_html_email_with_image(self, html, content_id):
        """Send an HTML email with ``dummy.png`` attached inline under the given Content-ID."""
        msg = EmailMultiAlternatives('inline image', 'Plain text body', to=['john@example.com'])
        msg.attach_alternative(html, 'text/html')
        with open(os.path.join(os.path.dirname(__file__), 'static/dummy.png'), 'rb') as f:
            image = MIMEImage(f.read())
        image.add_header('Content-Disposition', 'inline', filename='dummy.png')
        image.add_header('Content-ID', f'<{content_id}>')
        msg.attach(image)
        with override_settings(EMAIL_BACKEND='post_office.EmailBackend'):
            msg.send()
        email = Email.objects.latest('id')
        image_data = base64.b64encode(image.get_payload(decode=True)).decode('ascii')
        return email, f'data:image/png;base64,{image_data}'

    def test_email_preview_view_cid_quoted_img(self):
        email, data_uri = self._send_html_email_with_image('<img src="cid:abc">', 'abc')
        response = self.client.get(reverse('admin:post_office_email_preview', args=[email.pk]))
        self.assertContains(response, f'<img src="{data_uri}">')
        self.assertNotContains(response, 'cid:')

    def test_email_preview_view_cid_css_url(self):
        """An unquoted CSS ``url(cid:...)`` reference ends at the closing parenthesis."""
        email, data_uri = self._send_html_email_with_image(
            '<div style="background-image: url(cid:abc)">Hello</div>', 'abc'
        )
        response = self.client.get(reverse('admin:post_office_email_preview', args=[email.pk]))
        self.assertContains(response, f'<div style="background-image: url({data_uri})">Hello</div>')
        self.assertNotContains(response, 'cid:')

    def test_email_preview_view_cid_uppercase_scheme(self):
        """URI schemes are case-insensitive, so ``CID:`` must be recognised too."""
        email, data_uri = self._send_html_email_with_image('<img src="CID:abc">', 'abc')
        response = self.client.get(reverse('admin:post_office_email_preview', args=[email.pk]))
        self.assertContains(response, f'<img src="{data_uri}">')
        self.assertNotContains(response, 'CID:')

    def test_email_preview_view_cid_unknown_unchanged(self):
        """References to a Content-ID that is not attached are left untouched."""
        email, data_uri = self._send_html_email_with_image('<img src="cid:nope">', 'abc')
        response = self.client.get(reverse('admin:post_office_email_preview', args=[email.pk]))
        self.assertContains(response, '<img src="cid:nope">')
        self.assertNotContains(response, data_uri)

    def test_email_preview_view_cid_inside_word_unchanged(self):
        """``cid:`` inside a longer word (``acid:``) is not a URI scheme and must not be rewritten."""
        email, data_uri = self._send_html_email_with_image('<p>acid:abc</p><img src="cid:abc">', 'abc')
        response = self.client.get(reverse('admin:post_office_email_preview', args=[email.pk]))
        self.assertContains(response, '<p>acid:abc</p>')
        self.assertContains(response, f'<img src="{data_uri}">')

    def test_change_view_cid_longer_than_md5_unchanged(self):
        """A Content-ID that merely starts with 32 hex characters is not rewritten to the image URL."""
        content_id = 32 * 'a' + '-extra'
        email, _ = self._send_html_email_with_image(f'<img src="cid:{content_id}">', content_id)
        response = self.client.get(reverse('admin:post_office_email_change', args=[email.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(
            response, reverse('admin:post_office_email_image', kwargs={'pk': email.pk, 'content_id': 32 * 'a'})
        )

    @override_settings(EMAIL_BACKEND='post_office.EmailBackend')
    def test_change_view_cid_uppercase_scheme(self):
        """The change view rewrites ``CID:`` references to the admin image URL as well."""
        template = get_template('image.html', using='post_office')
        body = template.render({'imgsrc': 'dummy.png'}).replace('cid:', 'CID:')
        self.assertIn('CID:', body)
        msg = EmailMultiAlternatives('attached image', 'Plain text body', to=['john@example.com'])
        msg.attach_alternative(body, 'text/html')
        template.attach_related(msg)
        msg.send()

        email = Email.objects.latest('id')
        image_parts = [p for p in email.email_message().message().walk() if p.get_content_type() == 'image/png']
        content_id = image_parts[0]['Content-Id'][1:33]
        response = self.client.get(reverse('admin:post_office_email_change', args=[email.pk]))
        self.assertContains(
            response, reverse('admin:post_office_email_image', kwargs={'pk': email.pk, 'content_id': content_id})
        )
        self.assertNotContains(response, 'CID:')

    def test_email_preview_view_plaintext_only(self):
        email = send(recipients=['john@example.com'], subject='Plain', message='Plain text body')
        response = self.client.get(reverse('admin:post_office_email_preview', args=[email.pk]))
        self.assertEqual(response.status_code, 404)

    def test_email_preview_view_requires_login(self):
        email = self._send_html_email('<p>Hello</p>')
        anonymous = Client()
        for url in (
            reverse('admin:post_office_email_preview', args=[email.pk]),
            reverse('admin:post_office_email_image', kwargs={'pk': email.pk, 'content_id': 32 * '0'}),
            reverse('admin:resend', args=[email.pk]),
        ):
            response = anonymous.get(url)
            self.assertEqual(response.status_code, 302, url)
            self.assertIn(reverse('admin:login'), response['Location'])
        self.assertEqual(email.logs.count(), 0)  # resend was not executed for the anonymous user

    def test_email_preview_view_object_permission(self):
        email = self._send_html_email('<p>Hello</p>')
        preview_url = reverse('admin:post_office_email_preview', args=[email.pk])
        image_url = reverse('admin:post_office_email_image', kwargs={'pk': email.pk, 'content_id': 32 * '0'})
        resend_url = reverse('admin:resend', args=[email.pk])

        staff = get_user_model().objects.create_user(username='staff', password='secret', is_staff=True)
        client = Client()
        client.force_login(staff)
        for url in (preview_url, image_url, resend_url):
            self.assertEqual(client.get(url).status_code, 403, url)

        staff.user_permissions.add(Permission.objects.get(content_type__app_label='post_office', codename='view_email'))
        self.assertEqual(client.get(preview_url).status_code, 200)
        self.assertEqual(client.get(image_url).status_code, 404)  # allowed, but no such image
        self.assertEqual(client.get(resend_url).status_code, 403)  # resend needs change permission

    @override_settings(DEFAULT_CHARSET='iso-8859-1')
    def test_email_preview_view_non_utf8_charset(self):
        """The HTML part is decoded using its declared charset, not hard-coded UTF-8."""
        email = self._send_html_email('<p>Café</p>')
        response = self.client.get(reverse('admin:post_office_email_preview', args=[email.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<p>Café</p>')

    def test_change_view_preview_button(self):
        html_email = self._send_html_email('<p>Hello</p>')
        response = self.client.get(reverse('admin:post_office_email_change', args=[html_email.pk]))
        self.assertContains(response, reverse('admin:post_office_email_preview', args=[html_email.pk]))

        text_email = send(recipients=['john@example.com'], subject='Plain', message='Plain text body')
        response = self.client.get(reverse('admin:post_office_email_change', args=[text_email.pk]))
        self.assertNotContains(response, reverse('admin:post_office_email_preview', args=[text_email.pk]))
