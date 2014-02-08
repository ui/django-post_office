from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test.client import Client
from django.test import TestCase

from post_office import mail
from post_office.models import Email


admin_username = 'real_test_admin'
admin_email = 'read@admin.com'
admin_pass = 'admin_pass'


class AdminViewTest(TestCase):
    def setUp(self):
        user = User.objects.create_superuser(admin_username, admin_email, admin_pass)
        self.client = Client()
        self.client.login(username=user.username, password=admin_pass)

    # Small test to make sure the admin interface is loaded
    def test_admin_interface(self):
        response = self.client.get(reverse('admin:index'))
        self.assertEqual(response.status_code, 200)

    def test_admin_change_page(self):
        """Ensure that changing an email object in admin works."""
        mail.send(recipients=['test@example.com'], headers={'foo': 'bar'})
        email = Email.objects.latest('id')
        response = self.client.get(reverse('admin:post_office_email_change', args=[email.id]))
        self.assertEqual(response.status_code, 200)