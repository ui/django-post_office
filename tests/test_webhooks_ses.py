import json
from datetime import datetime, timezone

from django.test import RequestFactory, TestCase, override_settings
from unittest import mock

try:
    from cryptography.hazmat.primitives import serialization
except ImportError:  # pragma: no cover - optional dependency
    serialization = None

from post_office.models import RecipientDeliveryStatus
from post_office.webhooks.ses import SESWebhookHandler, verify_ses_signature, _is_valid_cert_url


class SESWebhookHandlerTest(TestCase):
    """Tests for SESWebhookHandler.parse_events()."""

    def setUp(self):
        self.factory = RequestFactory()
        self.handler = SESWebhookHandler()

    def _make_sns_payload(self, message):
        """Helper to wrap a message in SNS notification format."""
        return {
            'Type': 'Notification',
            'MessageId': 'test-message-id',
            'Message': json.dumps(message),
        }

    def _make_request(self, payload):
        """Helper to create a POST request with JSON payload."""
        return self.factory.post(
            '/webhook/ses/',
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_parse_delivery_multiple_recipients(self):
        """Test parsing a SES delivery with multiple recipients."""
        expected_timestamp = datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        message = {
            'notificationType': 'Delivery',
            'mail': {
                'messageId': 'abc123',
                'destination': ['user1@example.com', 'user2@example.com', 'user3@example.com'],
                'timestamp': '2024-01-02T03:04:05Z',
            },
            'delivery': {
                'recipients': ['user1@example.com', 'user2@example.com'],
            },
        }
        payload = self._make_sns_payload(message)
        request = self._make_request(payload)
        events = self.handler.parse_events(request)

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].recipient, 'user1@example.com')
        self.assertEqual(events[1].recipient, 'user2@example.com')
        self.assertEqual(events[0].timestamp, expected_timestamp)
        self.assertEqual(events[1].timestamp, expected_timestamp)
        self.assertEqual(
            events[0].to_addresses,
            ['user1@example.com', 'user2@example.com', 'user3@example.com'],
        )
        self.assertEqual(
            events[1].to_addresses,
            ['user1@example.com', 'user2@example.com', 'user3@example.com'],
        )

    def test_parse_bounce_permanent(self):
        """Test parsing a SES permanent bounce."""
        message = {
            'notificationType': 'Bounce',
            'mail': {
                'messageId': 'abc123',
                'destination': ['invalid@example.com'],
            },
            'bounce': {
                'bounceType': 'Permanent',
                'bouncedRecipients': [
                    {'emailAddress': 'invalid@example.com'},
                ],
            },
        }
        payload = self._make_sns_payload(message)
        request = self._make_request(payload)
        events = self.handler.parse_events(request)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].raw_event, 'Bounce:Permanent')
        self.assertEqual(events[0].delivery_status, RecipientDeliveryStatus.HARD_BOUNCED)
        self.assertEqual(events[0].recipient, 'invalid@example.com')

    def test_parse_bounce_transient(self):
        """Test parsing a SES transient (soft) bounce."""
        message = {
            'notificationType': 'Bounce',
            'mail': {
                'messageId': 'abc123',
                'destination': ['user@example.com'],
            },
            'bounce': {
                'bounceType': 'Transient',
                'bouncedRecipients': [
                    {'emailAddress': 'user@example.com'},
                ],
            },
        }
        payload = self._make_sns_payload(message)
        request = self._make_request(payload)
        events = self.handler.parse_events(request)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].delivery_status, RecipientDeliveryStatus.SOFT_BOUNCED)

    def test_parse_complaint(self):
        """Test parsing a SES complaint notification."""
        message = {
            'notificationType': 'Complaint',
            'mail': {
                'messageId': 'abc123',
                'destination': ['user@example.com'],
            },
            'complaint': {
                'complainedRecipients': [
                    {'emailAddress': 'user@example.com'},
                ],
            },
        }
        payload = self._make_sns_payload(message)
        request = self._make_request(payload)
        events = self.handler.parse_events(request)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].raw_event, 'Complaint')
        self.assertEqual(events[0].delivery_status, RecipientDeliveryStatus.SPAM_COMPLAINT)

    @override_settings(POST_OFFICE={'WEBHOOKS': {'SES': {'VERIFY_SIGNATURE': False}}})
    def test_parse_subscription_confirmation(self):
        """Test handling SNS subscription confirmation."""
        payload = {
            'Type': 'SubscriptionConfirmation',
            'TopicArn': 'arn:aws:sns:us-east-1:123456789:ses-notifications',
            'SubscribeURL': 'https://sns.us-east-1.amazonaws.com/?Action=ConfirmSubscription',
        }
        request = self._make_request(payload)
        response = self.handler.post(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['status'], 'subscription_confirmation_received')
        self.assertIn('subscribe_url', response_data)

    def test_parse_empty_message(self):
        """Test parsing an empty SNS message."""
        payload = {
            'Type': 'Notification',
            'Message': '',
        }
        request = self._make_request(payload)
        events = self.handler.parse_events(request)
        self.assertEqual(len(events), 0)

    def test_parse_unknown_notification_type(self):
        """Test that unknown notification types are ignored."""
        message = {
            'notificationType': 'UnknownType',
            'mail': {
                'messageId': 'abc123',
                'destination': ['user@example.com'],
            },
        }
        payload = self._make_sns_payload(message)
        request = self._make_request(payload)
        events = self.handler.parse_events(request)
        self.assertEqual(len(events), 0)


@mock.patch('post_office.webhooks.ses._get_aws_certificate')
class SESSignatureVerificationTest(TestCase):
    """Sanity checks for SES signature verification."""

    PUBLIC_KEY_PEM = (
        '-----BEGIN PUBLIC KEY-----\n'
        'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAqPgA9zEJUzmT3m4r8/AR\n'
        '+KuWX0ZJX0Bqn5vrPm9SwJ0u1TksrfM5VYqMMk6xj9adPBPdZkZvM6ZaD0R55VnL\n'
        'NpL/kvV5lfVs8Z24PDddscHf3H6Xm5tGcvlFgKjNvqkqsXFBBn6kSMg+co0qKSxm\n'
        'NddvRyLwb0mBZOydWDuYN60all9hHWRoEgdgMxQkzVl4dvprTVN7RISiDV/VdXAX\n'
        'fqcbpY/r4Cw5sqSiU6X1s0VOcLEx66cBcB8ytbZPj3GF0szbfAznninusR6fJoDP\n'
        'x98f69MyNh7Z3RY1s5JcUtnPtxTCVNdrlLriEy+0mY7UuYlft8la7HUhCoK3r27i\n'
        'hwIDAQAB\n'
        '-----END PUBLIC KEY-----\n'
    )
    SIGNATURE_V1 = (
        'FtDWpJjF7n6p8mljZsWbxdEK/cNRmONTdFmw89mSKPv4u8GMcBWNLv4qwXDxd5Xh1OwwrCkL'
        'BIt9t/kVAdSAsj1wqSPPcOrh+H3O3ElX/qqQu8qg2hZpE7Pu0q6vFOlHnoPRkwug2RvkLd3'
        'nYKhGBJ0/eRXqgZhsWhI8XnZmnBUWrtfA6yY1xF2BHZHs0t9VmlN4nemTEgcLir1gjKiynh'
        'Qwv0JED7vKZwJG9BvGn2H7DOdmZNdUBkNlr+Q3P1HnABSV8hnUnt50Y1VprLZk7siJkFJJK'
        '7z48OAQi4itFRCL5dH3t78+V5EOQkJ/DhnNWQQCLNx48Ad/XQLLjF8OfA=='
    )
    SIGNATURE_V2 = (
        'QV+fkjUjIVAHE7bi+d2PM21GVCZBkNsKUcrQAFlZRs6MOlZwKkhX0C+0emHwCAURBEU6Rd/h'
        'JQOU2/Lm+tbV+4V1SJf29UpnOBS/NKK3cwFR6ffH/wObTK2a3kGETw58Tc5SC2LHdTXrbmv'
        '/QJBESSKRyDewAnvwxmeP18sxTjILYYSnU2AWED06GOyuGAQF3aF06JUuRqadzxYX6m3Ziw'
        'c5sMN/7zeMkeLbJecu1Ak1gBWSHe4Gvyqk+iMekPnVVzRlJ2Ba0zSU5XIkfRHjOypQj7yHF'
        'l6Gw0YDLW0idRLNKcBzdezvFUR7r8KmO/zAdOgjshR67bFT63ODIqMPqA=='
    )

    def setUp(self):
        if serialization is None:
            self.skipTest('cryptography is required for SES signature tests')

        self.public_key = serialization.load_pem_public_key(self.PUBLIC_KEY_PEM.encode('ascii'))

    def _build_payload(self, signature_version, signature):
        return {
            'Type': 'Notification',
            'Message': 'Hello',
            'MessageId': 'mid-1',
            'Timestamp': '2024-01-01T00:00:00Z',
            'TopicArn': 'arn:aws:sns:us-east-1:123456789:ses-notifications',
            'SigningCertURL': 'https://sns.us-east-1.amazonaws.com/SimpleNotificationService-abc123def456.pem',
            'SignatureVersion': signature_version,
            'Signature': signature,
        }

    def test_verify_signature_version_1(self, mocked_cert):
        mocked_cert.return_value = self.public_key
        payload = self._build_payload('1', self.SIGNATURE_V1)

        self.assertTrue(verify_ses_signature(payload))

    def test_verify_signature_version_2_fails_on_mismatch(self, mocked_cert):
        mocked_cert.return_value = self.public_key
        payload = self._build_payload('2', self.SIGNATURE_V2)

        self.assertTrue(verify_ses_signature(payload))
        payload['Message'] = 'Tampered'
        self.assertFalse(verify_ses_signature(payload))

    def test_cert_url_validation(self, mocked_cert):
        """Test that certificate URL validation is strict."""
        # Valid URLs
        valid_urls = [
            'https://sns.us-east-1.amazonaws.com/SimpleNotificationService-abc123.pem',
            'https://sns.eu-west-2.amazonaws.com/cert.pem',
            'https://sns.ap-southeast-1.amazonaws.com/any-name.pem',
            'https://sns.us-gov-west-1.amazonaws.com/foo.pem',
        ]
        for url in valid_urls:
            with self.subTest(url=url):
                self.assertTrue(_is_valid_cert_url(url), f'Expected valid: {url}')

        # Invalid URLs - must all be rejected
        invalid_urls = [
            # Wrong scheme
            'http://sns.us-east-1.amazonaws.com/cert.pem',
            # Non-SNS AWS hosts
            'https://s3.us-east-1.amazonaws.com/cert.pem',
            'https://ec2.us-east-1.amazonaws.com/cert.pem',
            # Spoofed domains
            'https://sns.us-east-1.amazonaws.com.evil.com/cert.pem',
            'https://evil-amazonaws.com/cert.pem',
            'https://sns.us-east-1.fake-amazonaws.com/cert.pem',
            # Invalid path (not .pem)
            'https://sns.us-east-1.amazonaws.com/../etc/passwd',
            # Invalid region format
            'https://sns.invalid.amazonaws.com/cert.pem',
            'https://sns.amazonaws.com/cert.pem',
        ]
        for url in invalid_urls:
            with self.subTest(url=url):
                self.assertFalse(_is_valid_cert_url(url), f'Expected invalid: {url}')
