import os
from email.mime.image import MIMEImage
from django.core.mail import EmailMultiAlternatives
from django.core.mail.message import SafeMIMEMultipart, SafeMIMEText
from django.core.files.images import ImageFile
from django.template.loader import get_template
from django.test import TestCase
from django.test.utils import override_settings

from post_office.models import Email, EmailTemplate, STATUS
from post_office.template import render_to_string
from post_office.template.backends.post_office import PostOfficeTemplates
from post_office.mail import send, send_queued


class HTMLMailTest(TestCase):

    def test_text(self):
        template = get_template('hello.html', using='post_office')
        self.assertIsInstance(template.backend, PostOfficeTemplates)
        context = {'foo': "Bar"}
        content = template.render(context)
        self.assertHTMLEqual(content, '<h1>Bar</h1>')

    def test_html(self):
        template = get_template('image.html', using='post_office')
        body = template.render({'imgsrc': 'dummy.png'})
        self.assertHTMLEqual(body, """
<h3>Testing image attachments</h3>
<img src="cid:f5c66340b8af7dc946cd25d84fdf8c90" width="200" />
""")
        subject = "[Django Post-Office unit tests] attached image"
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

    def test_mixed(self):
        body = "Testing mixed text and html attachments"
        html, attached_images = render_to_string('image.html', {'imgsrc': 'dummy.png'}, using='post_office')
        subject = "[django-SHOP unit tests] attached image"
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

    def test_image(self):
        relfilename = 'static/dummy.png'
        filename = os.path.join(os.path.dirname(__file__), relfilename)
        imagefile = ImageFile(open(filename, 'rb'), name=relfilename)
        template = get_template('image.html', using='post_office')
        body = template.render({'imgsrc': imagefile})
        self.assertHTMLEqual(body, """
<h3>Testing image attachments</h3>
<img src="cid:f5c66340b8af7dc946cd25d84fdf8c90" width="200" />
""")
        subject = "[Django Post-Office unit tests] attached image"
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

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', POST_OFFICE={
        'BACKENDS': {'locmem': 'django.core.mail.backends.locmem.EmailBackend'},
        'TEMPLATE_ENGINE': 'post_office',
    })
    def test_send_with_html_template(self):
        template = EmailTemplate.objects.create(
            name="Test Inlined Images",
            subject="[django-SHOP unit tests] attached image",
            html_content="""
{% load post_office %}
<h3>Testing image attachments</h3>
<img src="{% inline_image imgsrc %}" width="200" />"""
        )
        filename = os.path.join(os.path.dirname(__file__), 'static/dummy.png')
        context = {'imgsrc': filename}
        queued_mail = send(recipients=['to@example.com'], sender='from@example.com',
                     template=template, context=context, render_on_delivery=True)
        queued_mail = Email.objects.get(id=queued_mail.id)
        send_queued()
        self.assertEqual(Email.objects.get(id=queued_mail.id).status, STATUS.sent)
