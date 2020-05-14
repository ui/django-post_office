from django.forms import formset_factory
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from post_office.admin import EmailTemplateAdminForm


User = get_user_model()


class EmailTemplateFormTest(TestCase):
    def setUp(self) -> None:
        self.form_set = formset_factory(EmailTemplateAdminForm,
                                        extra=2)
        self.client = Client()
        self.user = User.objects.create_superuser(username='testuser', password='abc123456', email="testemail@test.com")
        self.client.force_login(self.user)

    def test_can_create_a_email_template_with_the_same_attributes(self):
        email_template = {
            'form-TOTAL_FORMS': '3',
            'form-INITIAL_FORMS': '0',
            'form-MAX_NUM_FORMS': '',
            'name': 'Test',
            'email_photos-TOTAL_FORMS': '1', 'email_photos-INITIAL_FORMS': '0',
            'email_photos-MIN_NUM_FORMS': '0', 'email_photos-MAX_NUM_FORMS': '1', 'email_photos-0-id': '',
            'email_photos-0-email_template': '', 'email_photos-0-photo': '', 'email_photos-__prefix__-id': '',
            'email_photos-__prefix__-email_template': '', 'email_photos-__prefix__-photo': '',
            'translated_templates-TOTAL_FORMS': '2', 'translated_templates-INITIAL_FORMS': '0',
            'translated_templates-MIN_NUM_FORMS': '0', 'translated_templates-MAX_NUM_FORMS': '2',
            'translated_templates-0-language': 'es', 'translated_templates-0-subject': '',
            'translated_templates-0-content': '', 'translated_templates-0-html_content': '',
            'translated_templates-0-id': '', 'translated_templates-0-default_template': '',
            'translated_templates-1-language': 'es', 'translated_templates-1-subject': '',
            'translated_templates-1-content': '', 'translated_templates-1-html_content': '',
            'translated_templates-1-id': '', 'translated_templates-1-default_template': '',
            'translated_templates-__prefix__-language': 'es', 'translated_templates-__prefix__-subject': '',
            'translated_templates-__prefix__-content': '', 'translated_templates-__prefix__-html_content': '',
            'translated_templates-__prefix__-id': '', 'translated_templates-__prefix__-default_template': '',
            '_save': 'Save'
        }

        add_template_url = reverse('admin:post_office_emailtemplate_add')

        response = self.client.post(add_template_url, email_template, follow=True)
        self.assertContains(response, "Duplicate template for language &#39;Spanish&#39;.",
                            html=True)
