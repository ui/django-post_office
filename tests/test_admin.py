import base64
import os

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.base import ContentFile
from django.test import Client, TestCase
from django.test.utils import override_settings
from django.urls import reverse

from post_office.admin import AttachmentInline
from post_office.models import Attachment, Email, EmailTemplate


class MockRequest:
    pass


class MockSuperUser:
    def has_perm(self, perm, obj=None):
        return True


class EmailAdminTest(TestCase):
    def setUp(self):
        self.site = AdminSite()

        self.request = MockRequest()
        self.request.user = MockSuperUser()

    def test_attachmentinline_contentdisposition_header(self):
        email = Email.objects.create(to=['to@example.com'], from_email='from@example.com', subject='Subject')

        mt = 'text/plain'
        attachment_1 = Attachment(mimetype=mt, headers={'X-Custom-Header': 'Nope'})
        attachment_1.file.save('test_attachment_1.txt', content=ContentFile('test file content 1'), save=True)
        email.attachments.add(attachment_1)

        attachment_2 = Attachment(mimetype=mt, headers={'Content-Disposition': 'attachment; filename="test.txt"'})
        attachment_2.file.save('test_attachment_2.txt', content=ContentFile('test file content 2'), save=True)
        email.attachments.add(attachment_2)

        attachment_3 = Attachment(mimetype=mt, headers={'Content-Disposition': 'inline something'})
        attachment_3.file.save('test_attachment_3.txt', content=ContentFile('test file content 3'), save=True)
        email.attachments.add(attachment_3)

        email.email_message()

        attachment_inline = AttachmentInline(Email, self.site)
        attachment_inline.parent_obj = email

        qs_result = attachment_inline.get_queryset(self.request)
        with self.assertNumQueries(1):
            non_inline_attachments = [a_through.attachment for a_through in qs_result]

        self.assertIn(attachment_1, non_inline_attachments)
        self.assertIn(attachment_2, non_inline_attachments)
        self.assertNotIn(attachment_3, non_inline_attachments)
        self.assertEqual(len(non_inline_attachments), 2)


class EmailTemplateAdminPreviewTest(TestCase):
    """The EmailTemplate admin renders a template with its example context in a sandboxed preview."""

    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_superuser(
            username='admin', password='secret', email='a@example.com'
        )
        self.client.force_login(self.user)
        self.template = EmailTemplate.objects.create(
            name='welcome',
            subject='Welcome {{ name }}',
            content='Hi {{ name }}, <b>not bold</b>',
            html_content='<h1>Hello {{ name }}</h1>',
            example_context={'name': 'Alice'},
        )

    def preview_url(self, template, part):
        return reverse('admin:post_office_emailtemplate_preview', kwargs={'pk': template.pk, 'part': part})

    def test_html_preview_renders_example_context(self):
        response = self.client.get(self.preview_url(self.template, 'html'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Type'].startswith('text/html'))
        self.assertTrue(response['Content-Security-Policy'].startswith('sandbox'))
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response['Referrer-Policy'], 'no-referrer')
        self.assertContains(response, '<h1>Hello Alice</h1>')

    def test_text_preview_is_escaped(self):
        response = self.client.get(self.preview_url(self.template, 'text'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Security-Policy'].startswith('sandbox'))
        self.assertContains(response, '<pre style="white-space: pre-wrap;">Hi Alice, &lt;b&gt;not bold&lt;/b&gt;</pre>')

    def test_translated_template_uses_default_example_context(self):
        translation = self.template.translated_templates.create(language='nl', html_content='<p>Hallo {{ name }}</p>')
        response = self.client.get(self.preview_url(translation, 'html'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<p>Hallo Alice</p>')

    def test_preview_without_example_context(self):
        self.template.example_context = None
        self.template.save()
        response = self.client.get(self.preview_url(self.template, 'html'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<h1>Hello </h1>')

    @override_settings(POST_OFFICE={'TEMPLATE_ENGINE': 'post_office'})
    def test_html_preview_embeds_inline_images(self):
        self.template.html_content = '{% load post_office %}<img src="{% inline_image imgsrc %}">'
        self.template.example_context = {'imgsrc': os.path.join(os.path.dirname(__file__), 'static/dummy.png')}
        self.template.save()
        with open(os.path.join(os.path.dirname(__file__), 'static/dummy.png'), 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('ascii')

        response = self.client.get(self.preview_url(self.template, 'html'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'src="data:image/png;base64,{image_data}"')
        self.assertNotContains(response, 'cid:')

    def test_template_error_is_shown_in_preview(self):
        # ``objects.create`` skips the model validators, just like an import or a shell session does.
        self.template.html_content = '{% if %}'
        self.template.save()
        response = self.client.get(self.preview_url(self.template, 'html'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Security-Policy'].startswith('sandbox'))
        self.assertContains(response, 'Unexpected end of expression')

    def test_unknown_part_or_template_is_404(self):
        response = self.client.get(self.preview_url(self.template, 'subject'))
        self.assertEqual(response.status_code, 404)
        self.template.pk = self.template.pk + 1000
        response = self.client.get(self.preview_url(self.template, 'html'))
        self.assertEqual(response.status_code, 404)

    def test_preview_requires_login(self):
        anonymous = Client()
        response = anonymous.get(self.preview_url(self.template, 'html'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('admin:login'), response['Location'])

    def test_preview_requires_view_permission(self):
        staff = get_user_model().objects.create_user(username='staff', password='secret', is_staff=True)
        client = Client()
        client.force_login(staff)
        url = self.preview_url(self.template, 'html')
        self.assertEqual(client.get(url).status_code, 403)

        permission = Permission.objects.get(content_type__app_label='post_office', codename='view_emailtemplate')
        staff.user_permissions.add(permission)
        self.assertEqual(client.get(url).status_code, 200)

    def test_change_view_shows_preview_iframes(self):
        translation = self.template.translated_templates.create(
            language='nl', subject='Welkom {{ name }}', content='Hallo {{ name }}'
        )
        response = self.client.get(reverse('admin:post_office_emailtemplate_change', args=[self.template.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome Alice')
        self.assertContains(response, 'Welkom Alice')  # the inline renders the translation's subject
        for template, part in ((self.template, 'html'), (self.template, 'text'), (translation, 'text')):
            self.assertContains(response, f'src="{self.preview_url(template, part)}" sandbox')
        # The translation has no HTML content, so it gets no HTML preview.
        self.assertNotContains(response, self.preview_url(translation, 'html'))

    def test_rendered_subject_is_escaped(self):
        self.template.subject = '<b>{{ name }}</b>'
        self.template.save()
        response = self.client.get(reverse('admin:post_office_emailtemplate_change', args=[self.template.pk]))
        self.assertContains(response, '&lt;b&gt;Alice&lt;/b&gt;')
        self.assertNotContains(response, '<b>Alice</b>')

    def test_non_object_example_context_shows_an_error(self):
        # The admin form rejects this, but the field can be set from code.
        self.template.example_context = ['not', 'an', 'object']
        self.template.save()
        response = self.client.get(self.preview_url(self.template, 'html'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'must be a JSON object, not list')
        response = self.client.get(reverse('admin:post_office_emailtemplate_change', args=[self.template.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'must be a JSON object, not list')

    def test_add_view_has_no_preview(self):
        response = self.client.get(reverse('admin:post_office_emailtemplate_add'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<iframe')

    def test_example_context_is_editable_in_admin(self):
        data = {
            'name': 'welcome',
            'description': '',
            'subject': 'Welcome {{ name }}',
            'content': 'Hi {{ name }}',
            'html_content': '<h1>Hello {{ name }}</h1>',
            'language': '',
            'example_context': '{"name": "Bob"}',
            'translated_templates-TOTAL_FORMS': '0',
            'translated_templates-INITIAL_FORMS': '0',
            'translated_templates-MIN_NUM_FORMS': '0',
            'translated_templates-MAX_NUM_FORMS': '1000',
        }
        response = self.client.post(reverse('admin:post_office_emailtemplate_change', args=[self.template.pk]), data)
        self.assertEqual(response.status_code, 302, response.content[:2000])
        self.template.refresh_from_db()
        self.assertEqual(self.template.example_context, {'name': 'Bob'})

        data['example_context'] = '[1, 2]'
        response = self.client.post(reverse('admin:post_office_emailtemplate_change', args=[self.template.pk]), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The example context must be a JSON object.')
        self.template.refresh_from_db()
        self.assertEqual(self.template.example_context, {'name': 'Bob'})
