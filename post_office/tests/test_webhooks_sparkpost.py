import base64
import json

from django.test import RequestFactory, TestCase, override_settings

from post_office.models import RecipientDeliveryStatus
from post_office.webhooks.sparkpost import SparkPostWebhookHandler


class SparkPostWebhookHandlerTest(TestCase):
    """Tests for SparkPostWebhookHandler."""

    def setUp(self):
        self.factory = RequestFactory()
        self.handler = SparkPostWebhookHandler()

    def _make_auth_header(self, username, password):
        """Create a Basic Auth header value."""
        credentials = f'{username}:{password}'
        encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        return f'Basic {encoded}'

    def _make_request(self, payload, auth_header=None):
        """Create a POST request with the given payload."""
        request = self.factory.post(
            '/webhooks/sparkpost/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        if auth_header:
            request.META['HTTP_AUTHORIZATION'] = auth_header
        return request

    def _wrap_event(self, event_type, event_data):
        """Wrap event data in SparkPost's msys structure."""
        return [{'msys': {'message_event': {'type': event_type, **event_data}}}]

    # Signature verification tests

    def test_verify_signature_valid(self):
        """Test that valid Basic Auth credentials are accepted."""
        request = self._make_request(
            [],
            auth_header=self._make_auth_header('test-user', 'test-password'),
        )
        self.assertTrue(self.handler.verify_signature(request))

    def test_verify_signature_invalid_password(self):
        """Test that invalid password is rejected."""
        request = self._make_request(
            [],
            auth_header=self._make_auth_header('test-user', 'wrong-password'),
        )
        self.assertFalse(self.handler.verify_signature(request))

    def test_verify_signature_invalid_username(self):
        """Test that invalid username is rejected."""
        request = self._make_request(
            [],
            auth_header=self._make_auth_header('wrong-user', 'test-password'),
        )
        self.assertFalse(self.handler.verify_signature(request))

    def test_verify_signature_missing_header(self):
        """Test that missing Authorization header is rejected."""
        request = self._make_request([])
        self.assertFalse(self.handler.verify_signature(request))

    def test_verify_signature_invalid_format(self):
        """Test that invalid auth formats are rejected."""
        # Non-Basic auth
        request = self._make_request([])
        request.META['HTTP_AUTHORIZATION'] = 'Bearer some-token'
        self.assertFalse(self.handler.verify_signature(request))

        # Invalid base64 (should return False, not raise 500)
        request = self._make_request([])
        request.META['HTTP_AUTHORIZATION'] = 'Basic !!!invalid-base64!!!'
        self.assertFalse(self.handler.verify_signature(request))

    @override_settings(POST_OFFICE={'WEBHOOKS': {'SPARKPOST': {'VERIFY_SIGNATURE': False}}})
    def test_verify_signature_disabled(self):
        """Test that signature verification can be disabled."""
        request = self._make_request([])  # No auth header
        self.assertTrue(self.handler.verify_signature(request))

    # Event parsing tests

    def test_parse_injection_event(self):
        """Test parsing injection event."""
        payload = self._wrap_event(
            'injection',
            {
                'rcpt_to': 'test@example.com',
                'message_id': 'msg-123',
                'timestamp': '1703683200',
            },
        )
        request = self._make_request(payload)
        events = self.handler.parse_events(request)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].raw_event, 'injection')
        self.assertEqual(events[0].delivery_status, RecipientDeliveryStatus.ACCEPTED)
        self.assertEqual(events[0].recipient, 'test@example.com')
        self.assertEqual(events[0].message_id, 'msg-123')

    def test_parse_delivery_event(self):
        """Test parsing delivery event."""
        payload = self._wrap_event(
            'delivery',
            {
                'rcpt_to': 'test@example.com',
                'message_id': 'msg-123',
            },
        )
        request = self._make_request(payload)
        events = self.handler.parse_events(request)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].delivery_status, RecipientDeliveryStatus.DELIVERED)

    def test_parse_open_event(self):
        """Test parsing open event."""
        payload = self._wrap_event(
            'open',
            {
                'rcpt_to': 'test@example.com',
            },
        )
        request = self._make_request(payload)
        events = self.handler.parse_events(request)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].delivery_status, RecipientDeliveryStatus.OPENED)

    def test_parse_initial_open_event(self):
        """Test parsing initial_open event."""
        payload = self._wrap_event(
            'initial_open',
            {
                'rcpt_to': 'test@example.com',
            },
        )
        request = self._make_request(payload)
        events = self.handler.parse_events(request)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].delivery_status, RecipientDeliveryStatus.OPENED)

    def test_parse_click_event(self):
        """Test parsing click event."""
        payload = self._wrap_event(
            'click',
            {
                'rcpt_to': 'test@example.com',
            },
        )
        request = self._make_request(payload)
        events = self.handler.parse_events(request)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].delivery_status, RecipientDeliveryStatus.CLICKED)

    def test_parse_delay_event(self):
        """Test parsing delay event."""
        payload = self._wrap_event(
            'delay',
            {
                'rcpt_to': 'test@example.com',
            },
        )
        request = self._make_request(payload)
        events = self.handler.parse_events(request)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].delivery_status, RecipientDeliveryStatus.DEFERRED)

    def test_parse_spam_complaint_event(self):
        """Test parsing spam_complaint event."""
        payload = self._wrap_event(
            'spam_complaint',
            {
                'rcpt_to': 'test@example.com',
            },
        )
        request = self._make_request(payload)
        events = self.handler.parse_events(request)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].delivery_status, RecipientDeliveryStatus.SPAM_COMPLAINT)

    def test_parse_list_unsubscribe_event(self):
        """Test parsing list_unsubscribe event."""
        payload = self._wrap_event(
            'list_unsubscribe',
            {
                'rcpt_to': 'test@example.com',
            },
        )
        request = self._make_request(payload)
        events = self.handler.parse_events(request)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].delivery_status, RecipientDeliveryStatus.UNSUBSCRIBED)

    def test_parse_link_unsubscribe_event(self):
        """Test parsing link_unsubscribe event."""
        payload = self._wrap_event(
            'link_unsubscribe',
            {
                'rcpt_to': 'test@example.com',
            },
        )
        request = self._make_request(payload)
        events = self.handler.parse_events(request)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].delivery_status, RecipientDeliveryStatus.UNSUBSCRIBED)

    def test_parse_out_of_band_event(self):
        """Test parsing out_of_band bounce event."""
        payload = self._wrap_event(
            'out_of_band',
            {
                'rcpt_to': 'test@example.com',
                'bounce_class': '10',  # Hard bounce
            },
        )
        request = self._make_request(payload)
        events = self.handler.parse_events(request)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].delivery_status, RecipientDeliveryStatus.HARD_BOUNCED)

    def test_parse_policy_rejection_event(self):
        """Test parsing policy_rejection event."""
        payload = self._wrap_event(
            'policy_rejection',
            {
                'rcpt_to': 'test@example.com',
                'bounce_class': '25',  # Admin bounce
            },
        )
        request = self._make_request(payload)
        events = self.handler.parse_events(request)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].delivery_status, RecipientDeliveryStatus.HARD_BOUNCED)

    # Bounce classification tests

    def test_parse_bounce_classification(self):
        """Test bounce classification based on bounce_class."""
        test_cases = [
            # (bounce_class, expected_status, description)
            ('22', RecipientDeliveryStatus.SOFT_BOUNCED, 'soft bounce'),
            ('52', RecipientDeliveryStatus.SOFT_BOUNCED, 'block bounce'),
            ('1', RecipientDeliveryStatus.UNDETERMINED_BOUNCED, 'undetermined'),
            ('10', RecipientDeliveryStatus.HARD_BOUNCED, 'hard bounce'),
            ('25', RecipientDeliveryStatus.HARD_BOUNCED, 'admin bounce'),
        ]

        for bounce_class, expected_status, description in test_cases:
            with self.subTest(description=description, bounce_class=bounce_class):
                payload = self._wrap_event(
                    'bounce',
                    {
                        'rcpt_to': 'test@example.com',
                        'bounce_class': bounce_class,
                    },
                )
                request = self._make_request(payload)
                events = self.handler.parse_events(request)

                self.assertEqual(len(events), 1)
                self.assertEqual(events[0].delivery_status, expected_status)

    # Batch handling tests

    def test_parse_batch_events(self):
        """Test parsing multiple events in a single webhook."""
        payload = [
            {'msys': {'message_event': {'type': 'injection', 'rcpt_to': 'user1@example.com'}}},
            {'msys': {'message_event': {'type': 'delivery', 'rcpt_to': 'user2@example.com'}}},
            {'msys': {'message_event': {'type': 'open', 'rcpt_to': 'user3@example.com'}}},
        ]
        request = self._make_request(payload)
        events = self.handler.parse_events(request)

        self.assertEqual(len(events), 3)
        self.assertEqual(events[0].delivery_status, RecipientDeliveryStatus.ACCEPTED)
        self.assertEqual(events[1].delivery_status, RecipientDeliveryStatus.DELIVERED)
        self.assertEqual(events[2].delivery_status, RecipientDeliveryStatus.OPENED)

    def test_parse_results_wrapper(self):
        """Test parsing payload with results wrapper."""
        payload = {
            'results': [
                {'msys': {'message_event': {'type': 'injection', 'rcpt_to': 'user1@example.com'}}},
                {'msys': {'message_event': {'type': 'delivery', 'rcpt_to': 'user2@example.com'}}},
            ]
        }
        request = self._make_request(payload)
        events = self.handler.parse_events(request)

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].delivery_status, RecipientDeliveryStatus.ACCEPTED)
        self.assertEqual(events[1].delivery_status, RecipientDeliveryStatus.DELIVERED)

    def test_parse_empty_payload(self):
        """Test parsing empty payload."""
        request = self._make_request([])
        events = self.handler.parse_events(request)
        self.assertEqual(len(events), 0)

    def test_parse_event_without_recipient(self):
        """Test that events without recipient are skipped."""
        payload = self._wrap_event(
            'delivery',
            {
                'message_id': 'msg-123',
                # No rcpt_to
            },
        )
        request = self._make_request(payload)
        events = self.handler.parse_events(request)
        self.assertEqual(len(events), 0)

    def test_parse_unknown_event_type(self):
        """Test that unknown event types are skipped."""
        payload = self._wrap_event(
            'unknown_event',
            {
                'rcpt_to': 'test@example.com',
            },
        )
        request = self._make_request(payload)
        events = self.handler.parse_events(request)
        self.assertEqual(len(events), 0)

    def test_parse_timestamp(self):
        """Test that Unix timestamps are correctly parsed."""
        # Integer timestamp
        payload = self._wrap_event(
            'delivery',
            {
                'rcpt_to': 'test@example.com',
                'timestamp': '1703683200',  # 2023-12-27 12:00:00 UTC
            },
        )
        request = self._make_request(payload)
        events = self.handler.parse_events(request)

        self.assertEqual(len(events), 1)
        self.assertIsNotNone(events[0].timestamp)
        self.assertEqual(events[0].timestamp.year, 2023)
        self.assertEqual(events[0].timestamp.month, 12)
        self.assertEqual(events[0].timestamp.day, 27)

        # Fractional timestamp
        payload = self._wrap_event(
            'delivery',
            {
                'rcpt_to': 'test@example.com',
                'timestamp': '1703683200.123456',
            },
        )
        request = self._make_request(payload)
        events = self.handler.parse_events(request)

        self.assertEqual(len(events), 1)
        self.assertIsNotNone(events[0].timestamp)
        self.assertEqual(events[0].timestamp.microsecond, 123456)
