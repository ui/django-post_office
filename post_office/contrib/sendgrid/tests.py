import json
import logging
from datetime import datetime
from time import time
from typing import Any
from unittest.mock import Mock

from sendgrid.helpers.eventwebhook import EventWebhook
from sendgrid.helpers.eventwebhook.eventwebhook_header import EventWebhookHeader
from post_office.models import STATUS, Email
from post_office.contrib.sendgrid.views import SendgridWebhookHandler
from pytz import utc

from django.test import RequestFactory, TestCase  # noqa: F401


try:
    from ellipticcurve.ecdsa import Ecdsa
    from ellipticcurve.privateKey import PrivateKey as SigningKey
    from ellipticcurve.publicKey import PublicKey as VerifyKey

    from sendgrid.version import __version__ as sendgrid_version

    # Sendgrid switched over to using python-ecdsa instead of starbank-ecdsa
    # for version 6.12.1 and up
    # We can control what our test code imports, but not what sendgrid imports,
    # and they are not compatible with each other, so we both check for imports
    # and also check the version string
    if sendgrid_version > (6, 12, 0):
        raise AssertionError()
except (ImportError, AssertionError):
    import base64
    import hashlib
    from ecdsa.keys import SigningKey, VerifyingKey as VerifyKey
    from ecdsa.util import sigencode_der, sigdecode_der

    def generate_signing_key():
        return SigningKey.generate()

    def convert_signing_key_to_verify_key(signing_key: SigningKey) -> str:
        return signing_key.get_verifying_key()

    def convert_verify_key_to_base64(verify_key: VerifyKey) -> str:
        return (
            verify_key.to_pem()
            .decode('utf-8')
            .replace('-----BEGIN PUBLIC KEY-----\n', '')
            .replace('\n-----END PUBLIC KEY-----', '')
        )

    def sign_payload(payload: str, signing_key: SigningKey) -> str:
        signature_der = signing_key.sign(payload.encode('utf-8'), hashfunc=hashlib.sha256, sigencode=sigencode_der)
        # Immediately double check that this signature can be verified
        assert signing_key.get_verifying_key().verify(
            signature_der,
            payload.encode('utf-8'),
            hashfunc=hashlib.sha256,
            sigdecode=sigdecode_der,
        )
        return base64.b64encode(signature_der).decode('utf-8')
else:

    def generate_signing_key():
        return SigningKey()

    def convert_signing_key_to_verify_key(signing_key: SigningKey) -> str:
        return signing_key.publicKey()

    def convert_verify_key_to_base64(verify_key: VerifyKey) -> str:
        return (
            verify_key.toPem().replace('\n-----BEGIN PUBLIC KEY-----\n', '').replace('\n-----END PUBLIC KEY-----\n', '')
        )

    def sign_payload(payload: str, signing_key: SigningKey) -> str:
        return Ecdsa.sign(payload, signing_key).toBase64()


def sign_request_data(
    payload: dict[str, Any] | list[Any] | str | int,
    signing_key: SigningKey | None = None,
) -> tuple[str, str, VerifyKey]:
    if signing_key is None:
        signing_key = generate_signing_key()

    timestamp = str(round(time()))
    event_webhook = EventWebhook()

    return (
        sign_payload(timestamp + json.dumps(payload), signing_key),
        timestamp,
        event_webhook.convert_public_key_to_ecdsa(
            convert_verify_key_to_base64(convert_signing_key_to_verify_key(signing_key)),
        ),
    )


def signed_request_and_verify_key(
    payload: dict[str, Any] | list[Any] | str | int,
    signing_key: SigningKey | None = None,
) -> tuple[Mock, VerifyKey]:
    signature, timestamp, verify_key = sign_request_data(payload, signing_key)

    factory = RequestFactory()
    request = factory.post(
        '/',
        data=payload,
        content_type='application/json',
        headers={
            EventWebhookHeader.SIGNATURE: signature,
            EventWebhookHeader.TIMESTAMP: timestamp,
        },
    )

    # Before we do anything else, make sure the signature is verified
    assert EventWebhook().verify_signature(
        request.body.decode('utf-8'),
        signature,
        timestamp,
        verify_key,
    )
    return request, verify_key


PROCESSED_AND_DELIVERED_EVENTS = list(
    reversed(
        [
            {
                'email': 'example@test.com',
                'timestamp': 1748677478,
                'smtp-id': '<14c5d75ce93.dfd.64b469@ismtpd-555>',
                'event': 'processed',
                'category': ['cat facts'],
                'sg_event_id': '59sHF28hMKoAkD6LOG8dIg==',
                'sg_message_id': '14c5d75ce93.dfd.64b469.filter0001.16648.5515E0B88.0',
            },
            {
                'email': 'example@test.com',
                'timestamp': 1748677478,
                'smtp-id': '<14c5d75ce93.dfd.64b469@ismtpd-555>',
                'event': 'delivered',
                'category': ['cat facts'],
                'sg_event_id': 'BbNhWXmbLh5y7iTImHgmoA==',
                'sg_message_id': '14c5d75ce93.dfd.64b469.filter0001.16648.5515E0B88.0',
                'response': '250 OK',
            },
        ]
    )
)


ALL_DELIVERABILITY_EVENTS = list(
    reversed(
        [
            # Received by Sendgrid, queued for sending
            {
                'email': 'example@test.com',
                'timestamp': 1748677468,
                'smtp-id': '<14c5d75ce93.dfd.64b469@ismtpd-555>',
                'event': 'processed',
                'category': ['cat facts'],
                'sg_event_id': '59sHF28hMKoAkD6LOG8dIg==',
                'sg_message_id': '14c5d75ce93.dfd.64b469.filter0001.16648.5515E0B88.0',
            },
            # Temporarily rejected
            {
                'email': 'example@test.com',
                'timestamp': 1748677608,
                'smtp-id': '<14c5d75ce93.dfd.64b469@ismtpd-555>',
                'event': 'deferred',
                'category': ['cat facts'],
                'sg_event_id': 'pvh2J-b4Hr-ZbQsVLGUhfw==',
                'sg_message_id': '14c5d75ce93.dfd.64b469.filter0001.16648.5515E0B88.0',
                'response': '400 try again later',
                'attempt': '5',
            },
            {
                'email': 'example@test.com',
                'timestamp': 1748677628,
                'smtp-id': '<14c5d75ce93.dfd.64b469@ismtpd-555>',
                'event': 'blocked',
                'category': ['cat facts'],
                'sg_event_id': 'Y3iax6IAi2g8aIxPLH2YcQ==',
                'sg_message_id': '14c5d75ce93.dfd.64b469.filter0001.16648.5515E0B88.0',
                'reason': '500 unknown recipient',
                'status': '5.0.0',
            },
            {
                'email': 'example@test.com',
                'timestamp': 1748677478,
                'smtp-id': '<14c5d75ce93.dfd.64b469@ismtpd-555>',
                'event': 'delivered',
                'category': ['cat facts'],
                'sg_event_id': 'BbNhWXmbLh5y7iTImHgmoA==',
                'sg_message_id': '14c5d75ce93.dfd.64b469.filter0001.16648.5515E0B88.0',
                'response': '250 OK',
            },
            {
                'email': 'example@test.com',
                'timestamp': 1748677588,
                'smtp-id': '<14c5d75ce93.dfd.64b469@ismtpd-555>',
                'event': 'dropped',
                'category': ['cat facts'],
                'sg_event_id': 'MY74PHBg8h2R6Gu1eLmK2g==',
                'sg_message_id': '14c5d75ce93.dfd.64b469.filter0001.16648.5515E0B88.0',
                'reason': 'Bounced Address',
                'status': '5.0.0',
            },
            {
                'email': 'example@test.com',
                'timestamp': 1748677618,
                'smtp-id': '<14c5d75ce93.dfd.64b469@ismtpd-555>',
                'event': 'bounce',
                'category': ['cat facts'],
                'sg_event_id': 'uswLJOijC8uqnGK9-5YM5g==',
                'sg_message_id': '14c5d75ce93.dfd.64b469.filter0001.16648.5515E0B88.0',
                'reason': '500 unknown recipient',
                'status': '5.0.0',
            },
        ]
    )
)


ALL_ENGAGEMENT_EVENTS = list(
    reversed(
        [
            {
                'email': 'example@test.com',
                'timestamp': 1748677638,
                'smtp-id': '<14c5d75ce93.dfd.64b469@ismtpd-555>',
                'event': 'open',
                'category': ['cat facts'],
                'sg_event_id': '2MJrTu_olgvCdPSaZkMKNQ==',
                'sg_message_id': '14c5d75ce93.dfd.64b469.filter0001.16648.5515E0B88.0',
                'useragent': 'Mozilla/4.0 (compatible; MSIE 6.1; Windows XP; .NET CLR 1.1.4322; .NET CLR 2.0.50727)',
                'ip': '255.255.255.255',
            },
            {
                'email': 'example@test.com',
                'timestamp': 1748677648,
                'smtp-id': '<14c5d75ce93.dfd.64b469@ismtpd-555>',
                'event': 'click',
                'category': ['cat facts'],
                'sg_event_id': '2x8k8KHmwl4LFlY17rAiAg==',
                'sg_message_id': '14c5d75ce93.dfd.64b469.filter0001.16648.5515E0B88.0',
                'useragent': 'Mozilla/4.0 (compatible; MSIE 6.1; Windows XP; .NET CLR 1.1.4322; .NET CLR 2.0.50727)',
                'ip': '255.255.255.255',
                'url': 'http://www.sendgrid.com/',
            },
            {
                'email': 'example@test.com',
                'timestamp': 1748677658,
                'smtp-id': '<14c5d75ce93.dfd.64b469@ismtpd-555>',
                'event': 'spamreport',
                'category': ['cat facts'],
                'sg_event_id': '9Qg8TEfE4wPybdg4vkWUkw==',
                'sg_message_id': '14c5d75ce93.dfd.64b469.filter0001.16648.5515E0B88.0',
            },
            {
                'email': 'example@test.com',
                'timestamp': 1748677668,
                'smtp-id': '<14c5d75ce93.dfd.64b469@ismtpd-555>',
                'event': 'unsubscribe',
                'category': ['cat facts'],
                'sg_event_id': 'zSpqW79OJCR_OcIDUYLYQA==',
                'sg_message_id': '14c5d75ce93.dfd.64b469.filter0001.16648.5515E0B88.0',
            },
            {
                'email': 'example@test.com',
                'timestamp': 1748677678,
                'smtp-id': '<14c5d75ce93.dfd.64b469@ismtpd-555>',
                'event': 'group_unsubscribe',
                'category': ['cat facts'],
                'sg_event_id': '5r5IxXncIvN3mok5oZgT-w==',
                'sg_message_id': '14c5d75ce93.dfd.64b469.filter0001.16648.5515E0B88.0',
                'useragent': 'Mozilla/4.0 (compatible; MSIE 6.1; Windows XP; .NET CLR 1.1.4322; .NET CLR 2.0.50727)',
                'ip': '255.255.255.255',
                'url': 'http://www.sendgrid.com/',
                'asm_group_id': 10,
            },
            {
                'email': 'example@test.com',
                'timestamp': 1748677688,
                'smtp-id': '<14c5d75ce93.dfd.64b469@ismtpd-555>',
                'event': 'group_resubscribe',
                'category': ['cat facts'],
                'sg_event_id': '2C_RkgO6PR0GixkCzi_Wtw==',
                'sg_message_id': '14c5d75ce93.dfd.64b469.filter0001.16648.5515E0B88.0',
                'useragent': 'Mozilla/4.0 (compatible; MSIE 6.1; Windows XP; .NET CLR 1.1.4322; .NET CLR 2.0.50727)',
                'ip': '255.255.255.255',
                'url': 'http://www.sendgrid.com/',
                'asm_group_id': 10,
            },
        ]
    )
)


ALL_ACCOUNT_EVENTS = list(
    reversed(
        [
            {
                'event': 'account_status_change',
                'sg_event_id': 'MjEzNTg5OTcyOC10ZXJtaW5hdGUtMTcwNzg1MTUzMQ',
                'timestamp': 1709142428,
                'type': 'compliance_suspend',
            },
        ]
    )
)


UNRECOGNIZED_EVENTS = list(
    reversed(
        [
            {
                'email': 'example@test.com',
                'timestamp': 1748677698,
                'smtp-id': '<14c5d75ce93.dfd.64b469@ismtpd-555>',
                'event': 'unrecognized_event',
                'category': ['cat facts'],
                'sg_event_id': '59sHF28hMKoAkD6LOG8dIg==',
                'sg_message_id': '14c5d75ce93.dfd.64b469.filter0001.16648.5515E0B88.0',
            },
        ]
    )
)


class BaseWebhookTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.event_webhook = EventWebhook()


class SendgridWebhookVerificationTestCase(BaseWebhookTestCase):
    def test_signed_data_verifies(self):
        data = {'a': 'A', 'b': 'B', 'c': 'C'}

        self.assertTrue(self.event_webhook.verify_signature(json.dumps(data), *sign_request_data(data)))

    def test_nonverified_webhook(self):
        view = SendgridWebhookHandler.as_view()

        email = Email.objects.create(
            from_email='sender@example.com',
            to='recipient@example.com',
            subject='Test Subject',
            message='Text message',
            html_message='HTML message',
            status=STATUS.queued,
            message_id='<14c5d75ce93.dfd.64b469@ismtpd-555>',
        )

        request, verify_key = signed_request_and_verify_key(ALL_DELIVERABILITY_EVENTS)
        request.headers = dict(request.headers) | {EventWebhookHeader.SIGNATURE: 'somethingthatisnotasignature'}

        with self.settings(SENDGRID_WEBHOOK_VERIFICATION_KEY=convert_verify_key_to_base64(verify_key)):
            response = view(request)

            self.assertEqual(response.status_code, 404)

        email.refresh_from_db()
        self.assertEqual(email.status, STATUS.queued)

        self.assertEqual(email.logs.all().count(), 0)


class SendgridWebhookPostTestCase(BaseWebhookTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.event_webhook = EventWebhook()

    def test_unrecognized_event(self):
        view = SendgridWebhookHandler.as_view()

        email = Email.objects.create(
            from_email='sender@example.com',
            to='recipient@example.com',
            subject='Test Subject',
            message='Text message',
            html_message='HTML message',
            message_id='<14c5d75ce93.dfd.64b469@ismtpd-555>',
            status=STATUS.queued,
        )

        request, verify_key = signed_request_and_verify_key(UNRECOGNIZED_EVENTS)

        with self.settings(SENDGRID_WEBHOOK_VERIFICATION_KEY=convert_verify_key_to_base64(verify_key)):
            logger = 'post_office.contrib.sendgrid.views'
            with self.assertLogs(logger=logger, level=logging.WARNING) as cm:
                response = view(request)

            self.assertTrue(len(cm.output), 1)
            self.assertTrue(cm.output[0].startswith(f'WARNING:{logger}:Received unrecognized webhook event:'))

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.text, 'ok')

        email.refresh_from_db()
        self.assertEqual(email.status, STATUS.queued)


class SendgridWebhookDeliverabilityEventsTestCase(BaseWebhookTestCase):
    def test_real_quick_processed_and_delivered_events(self):
        view = SendgridWebhookHandler.as_view()

        email = Email.objects.create(
            from_email='sender@example.com',
            to='recipient@example.com',
            subject='Test Subject',
            message='Text message',
            html_message='HTML message',
            message_id='<14c5d75ce93.dfd.64b469@ismtpd-555>',
            status=STATUS.queued,
        )
        # Set created and last_updated to 100 seconds before the first event (events are in reverse order)
        Email.objects.filter(id=email.id).update(
            created=datetime.fromtimestamp(float(PROCESSED_AND_DELIVERED_EVENTS[-1]['timestamp'] - 100), tz=utc),
            last_updated=datetime.fromtimestamp(float(PROCESSED_AND_DELIVERED_EVENTS[-1]['timestamp'] - 100), tz=utc),
        )
        email.refresh_from_db()
        self.assertEqual(
            email.created, datetime.fromtimestamp(float(PROCESSED_AND_DELIVERED_EVENTS[-1]['timestamp'] - 100), tz=utc)
        )
        self.assertEqual(
            email.last_updated,
            datetime.fromtimestamp(float(PROCESSED_AND_DELIVERED_EVENTS[-1]['timestamp'] - 100), tz=utc),
        )

        request, verify_key = signed_request_and_verify_key([PROCESSED_AND_DELIVERED_EVENTS[-1]])

        with self.settings(SENDGRID_WEBHOOK_VERIFICATION_KEY=convert_verify_key_to_base64(verify_key)):
            response = view(request)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.text, 'ok')

        email.refresh_from_db()
        self.assertEqual(email.status, STATUS.queued)

        self.assertTrue(email.logs.all().count(), 1)
        self.assertTrue(email.logs.filter(status=STATUS.sent).count(), 1)

        request, verify_key = signed_request_and_verify_key([PROCESSED_AND_DELIVERED_EVENTS[-2]])

        with self.settings(SENDGRID_WEBHOOK_VERIFICATION_KEY=convert_verify_key_to_base64(verify_key)):
            response = view(request)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.text, 'ok')

        email.refresh_from_db()
        self.assertEqual(email.status, STATUS.sent)

        self.assertTrue(email.logs.all().count(), 2)
        self.assertTrue(email.logs.filter(status=STATUS.sent).count(), 2)

    def test_all_deliverability_events(self):
        view = SendgridWebhookHandler.as_view()

        email = Email.objects.create(
            from_email='sender@example.com',
            to='recipient@example.com',
            subject='Test Subject',
            message='Text message',
            html_message='HTML message',
            message_id='<14c5d75ce93.dfd.64b469@ismtpd-555>',
            status=STATUS.queued,
        )

        request, verify_key = signed_request_and_verify_key(ALL_DELIVERABILITY_EVENTS)

        with self.settings(SENDGRID_WEBHOOK_VERIFICATION_KEY=convert_verify_key_to_base64(verify_key)):
            response = view(request)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.text, 'ok')

    def test_all_deliverability_events_with_unknown_email(self):
        view = SendgridWebhookHandler.as_view()

        email = Email.objects.create(
            from_email='sender@example.com',
            to='recipient@example.com',
            subject='Test Subject',
            message='Text message',
            html_message='HTML message',
            message_id='<93ced75c514.dfd.64b469@ismtpd-555>',
            status=STATUS.queued,
        )

        request, verify_key = signed_request_and_verify_key(ALL_DELIVERABILITY_EVENTS)

        with self.settings(SENDGRID_WEBHOOK_VERIFICATION_KEY=convert_verify_key_to_base64(verify_key)):
            logger = 'post_office.contrib.sendgrid.views'
            with self.assertLogs(logger=logger, level=logging.INFO) as cm:
                response = view(request)

            self.assertTrue(len(cm.output), len(ALL_DELIVERABILITY_EVENTS))
            for infologline in cm.output:
                self.assertTrue(
                    infologline.startswith(f'INFO:{logger}:Received webhook without a valid reference to an email:')
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.text, 'ok')

        email.refresh_from_db()
        self.assertEqual(email.status, STATUS.queued)


class SendgridWebhookEngagementEventsTestCase(BaseWebhookTestCase):
    def test_all_engagement_events(self):
        view = SendgridWebhookHandler.as_view()

        email = Email.objects.create(
            from_email='sender@example.com',
            to='recipient@example.com',
            subject='Test Subject',
            message='Text message',
            html_message='HTML message',
            message_id='<14c5d75ce93.dfd.64b469@ismtpd-555>',
            status=STATUS.queued,
        )
        # Set created and last_updated to 100 seconds before the first event (events are in reverse order)
        Email.objects.filter(id=email.id).update(
            created=datetime.fromtimestamp(float(PROCESSED_AND_DELIVERED_EVENTS[-1]['timestamp'] - 100), tz=utc),
            last_updated=datetime.fromtimestamp(float(PROCESSED_AND_DELIVERED_EVENTS[-1]['timestamp'] - 100), tz=utc),
        )
        email.refresh_from_db()
        self.assertEqual(
            email.created, datetime.fromtimestamp(float(PROCESSED_AND_DELIVERED_EVENTS[-1]['timestamp'] - 100), tz=utc)
        )
        self.assertEqual(
            email.last_updated,
            datetime.fromtimestamp(float(PROCESSED_AND_DELIVERED_EVENTS[-1]['timestamp'] - 100), tz=utc),
        )

        request, verify_key = signed_request_and_verify_key(PROCESSED_AND_DELIVERED_EVENTS)

        with self.settings(SENDGRID_WEBHOOK_VERIFICATION_KEY=convert_verify_key_to_base64(verify_key)):
            response = view(request)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.text, 'ok')

        email.refresh_from_db()
        self.assertEqual(email.status, STATUS.sent)
        self.assertTrue(email.logs.filter(status=STATUS.sent).exists())

        request, verify_key = signed_request_and_verify_key(ALL_ENGAGEMENT_EVENTS)

        with self.settings(SENDGRID_WEBHOOK_VERIFICATION_KEY=convert_verify_key_to_base64(verify_key)):
            response = view(request)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.text, 'ok')

        email.refresh_from_db()
        self.assertEqual(email.status, STATUS.sent)
        self.assertTrue(email.logs.filter(status=STATUS.sent).exists())

    def test_engagement_events_mark_email_as_sent(self):
        view = SendgridWebhookHandler.as_view()

        email = Email.objects.create(
            from_email='sender@example.com',
            to='recipient@example.com',
            subject='Test Subject',
            message='Text message',
            html_message='HTML message',
            message_id='<14c5d75ce93.dfd.64b469@ismtpd-555>',
            status=STATUS.queued,
        )
        # Set created and last_updated to 100 seconds before the first event (events are in reverse order)
        Email.objects.filter(id=email.id).update(
            created=datetime.fromtimestamp(float(PROCESSED_AND_DELIVERED_EVENTS[-1]['timestamp'] - 100), tz=utc),
            last_updated=datetime.fromtimestamp(float(PROCESSED_AND_DELIVERED_EVENTS[-1]['timestamp'] - 100), tz=utc),
        )
        email.refresh_from_db()
        self.assertEqual(
            email.created, datetime.fromtimestamp(float(PROCESSED_AND_DELIVERED_EVENTS[-1]['timestamp'] - 100), tz=utc)
        )
        self.assertEqual(
            email.last_updated,
            datetime.fromtimestamp(float(PROCESSED_AND_DELIVERED_EVENTS[-1]['timestamp'] - 100), tz=utc),
        )

        # POST a deliverability event so we have a proper EmailLog to query against
        request, verify_key = signed_request_and_verify_key([PROCESSED_AND_DELIVERED_EVENTS[-1]])

        with self.settings(SENDGRID_WEBHOOK_VERIFICATION_KEY=convert_verify_key_to_base64(verify_key)):
            response = view(request)

            self.assertEqual(response.text, 'ok')

        email.refresh_from_db()
        self.assertEqual(email.status, STATUS.queued)
        self.assertTrue(email.logs.filter(status=STATUS.sent).exists())

        # Now POST an engagement event
        engagement_event = ALL_ENGAGEMENT_EVENTS[-1]
        request, verify_key = signed_request_and_verify_key([engagement_event])

        with self.settings(SENDGRID_WEBHOOK_VERIFICATION_KEY=convert_verify_key_to_base64(verify_key)):
            response = view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, 'ok')

        email.refresh_from_db()
        self.assertEqual(email.status, STATUS.sent)
        self.assertTrue(email.logs.filter(status=STATUS.sent).exists())

    def test_all_engagement_events_with_unknown_email_log(self):
        view = SendgridWebhookHandler.as_view()

        for i, engagement_event in enumerate([ALL_ENGAGEMENT_EVENTS[-1]], 1):
            with self.subTest(i=i, engagement_event=engagement_event):
                email = Email.objects.create(
                    from_email='sender@example.com',
                    to='recipient@example.com',
                    subject='Test Subject',
                    message='Text message',
                    html_message='HTML message',
                    message_id=f'<93ced75c{i}.dfd.64b469@ismtpd-555>',
                    status=STATUS.queued,
                )
                # Set created and last_updated to 100 seconds before the first event (events are in reverse order)
                Email.objects.filter(id=email.id).update(
                    created=datetime.fromtimestamp(
                        float(PROCESSED_AND_DELIVERED_EVENTS[-1]['timestamp'] - 100), tz=utc
                    ),
                    last_updated=datetime.fromtimestamp(
                        float(PROCESSED_AND_DELIVERED_EVENTS[-1]['timestamp'] - 100), tz=utc
                    ),
                )
                email.refresh_from_db()
                self.assertEqual(
                    email.created,
                    datetime.fromtimestamp(float(PROCESSED_AND_DELIVERED_EVENTS[-1]['timestamp'] - 100), tz=utc),
                )
                self.assertEqual(
                    email.last_updated,
                    datetime.fromtimestamp(float(PROCESSED_AND_DELIVERED_EVENTS[-1]['timestamp'] - 100), tz=utc),
                )

                # Now POST an engagement event
                request, verify_key = signed_request_and_verify_key([engagement_event])

                logger = 'post_office.contrib.sendgrid.views'
                with self.assertLogs(logger=logger, level=logging.INFO) as cm:
                    with self.settings(SENDGRID_WEBHOOK_VERIFICATION_KEY=convert_verify_key_to_base64(verify_key)):
                        response = view(request)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.text, 'ok')

                self.assertTrue(len(cm.output), 1)
                for infologline in cm.output:
                    self.assertTrue(
                        infologline.startswith(
                            f'INFO:{logger}:Received webhook without a valid reference to an email log:'
                        )
                    )


class SendgridWebhookAccountEventsTestCase(BaseWebhookTestCase):
    def test_all_account_events(self):
        view = SendgridWebhookHandler.as_view()

        request, verify_key = signed_request_and_verify_key(ALL_ACCOUNT_EVENTS)

        logger = 'post_office.contrib.sendgrid.views'
        with self.assertRaises(Exception) as exc_cm:
            with self.assertLogs(logger=logger, level=logging.ERROR) as logging_cm:
                with self.settings(SENDGRID_WEBHOOK_VERIFICATION_KEY=convert_verify_key_to_base64(verify_key)):
                    view(request)

        self.assertTrue(len(logging_cm.records), 1)
        self.assertEqual('Received webhook regarding account suspension', str(logging_cm.records[0].msg))

        self.assertEqual(
            str(exc_cm.exception),
            ('Error when processing Sendgrid Events webhook. ' 'The Sendgrid Events Webhook API may have changed.'),
        )
