import logging

from django.test import RequestFactory, TestCase  # noqa: F401

from post_office.webhook import BaseWebhookHandler


class WebhookTest(TestCase):
    def test_unknown_http_method(self):
        factory = RequestFactory()
        request = factory.generic('UNKNOWN', '/', {}, content_type='application/json')

        view = BaseWebhookHandler.as_view()

        with self.assertLogs(level=logging.WARNING) as logging_cm:
            response = view(request)

        self.assertEqual(response.status_code, 405)
        self.assertTrue(len(logging_cm.records), 1)
        self.assertEqual(str(logging_cm.records[0].msg), 'Method Not Allowed (%s): %s')
        self.assertEqual(logging_cm.records[0].args, ('UNKNOWN', '/'))
