from django.test import TestCase, override_settings
from django.utils import timezone

from post_office.models import RecipientDeliveryStatus
from post_office.settings import get_webhook_config
from post_office.webhooks.base import ESPEvent


class ESPEventTest(TestCase):
    """Tests for the ESPEvent dataclass."""

    def test_create_full_event(self):
        """Test creating an ESPEvent with all fields."""
        now = timezone.now()
        event = ESPEvent(
            raw_event='delivered',
            delivery_status=RecipientDeliveryStatus.DELIVERED,
            recipient='test@example.com',
            message_id='<abc123@example.com>',
            timestamp=now,
            subject='Test Subject',
            to_addresses=['test@example.com', 'other@example.com'],
        )
        self.assertEqual(event.message_id, '<abc123@example.com>')
        self.assertEqual(event.timestamp, now)
        self.assertEqual(event.subject, 'Test Subject')
        self.assertEqual(event.to_addresses, ['test@example.com', 'other@example.com'])


class WebhookConfigTest(TestCase):
    """Tests for webhook configuration helpers."""

    def test_get_webhook_config_exists(self):
        """Test getting configuration for a configured provider."""
        config = get_webhook_config('SES')
        self.assertTrue(config['VERIFY_SIGNATURE'])

    @override_settings(POST_OFFICE={})
    def test_get_webhook_config_no_webhooks(self):
        """Test getting configuration when no webhooks are configured."""
        config = get_webhook_config('SES')
        self.assertEqual(config, {})

    def test_get_webhook_config_different_provider(self):
        """Test getting configuration for a provider that isn't configured."""
        config = get_webhook_config('NON_EXISTENT')
        self.assertEqual(config, {})
