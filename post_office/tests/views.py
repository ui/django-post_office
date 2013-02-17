from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test.client import Client
from django.test import TestCase


admin_username = 'real_test_admin'
admin_email = 'read@admin.com'
admin_pass = 'admin_pass'


class AdminViewTest(TestCase):
    def setUp(self):
        user = User.objects.create_superuser(admin_username, admin_email, admin_pass)
        self.client = Client()
        self.client.login(username=user.username, password=user.password)

    # Small test to make sure the admin interface is loaded
    def test_admin_interface(self):
        response = self.client.get(reverse('admin:index'))
        self.assertEqual(response.status_code, 200)
