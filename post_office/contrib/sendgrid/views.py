import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any

from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponseNotFound
from post_office.models import Email, Log as EmailLog, STATUS
from post_office.webhook import (
    EVENT_TO_EMAIL_STATUS,
    EVENT_TO_EMAIL_LOG_STATUS,
    Event,
    BaseWebhookHandler,
)
from pytz import utc
from sendgrid_backend.decorators import check_sendgrid_signature


logger = logging.getLogger(__name__)


class DeliverabilityEvent(Enum):
    PROCESSED = 'processed'
    DROPPED = 'dropped'
    DELIVERED = 'delivered'
    DEFERRED = 'deferred'
    BOUNCE = 'bounce'
    BLOCKED = 'blocked'


class EngagementEvent(Enum):
    OPEN = 'open'
    CLICK = 'click'
    SPAMREPORT = 'spamreport'
    UNSUBSCRIBE = 'unsubscribe'
    GROUP_UNSUBSCRIBE = 'group_unsubscribe'
    GROUP_RESUBSCRIBE = 'group_resubscribe'


class AccountEvent(Enum):
    COMPLIANCE_SUSPENDED = 'account_status_change'


SENDGRID_STATUS_TO_EVENT = {
    # Message has been received by Sendgrid and is ready to be delivered to the final recipient
    DeliverabilityEvent.PROCESSED.value: Event.ACCEPTED,
    # Message has been successfully delivered to the receiving server
    DeliverabilityEvent.DELIVERED.value: Event.DELIVERED,
    # Receiving server temporarily rejected the message
    DeliverabilityEvent.DEFERRED.value: Event.DEFERRED,
    # Receiving server could not or would not accept mail to this recipient permanently
    # Bounces can be either "conversational" (eg: immediately after being sent), or asynchronous
    # See https://www.twilio.com/docs/sendgrid/ui/sending-email/bounces#asynchronous-bounces
    DeliverabilityEvent.BOUNCE.value: Event.HARD_BOUNCE,
    # Receiving server could not or would not accept the message temporarily
    DeliverabilityEvent.BLOCKED.value: Event.SOFT_BOUNCE,
    # Message has been dropped from Sendgrid's queue and will not be retried
    DeliverabilityEvent.DROPPED.value: Event.REJECTED,
    EngagementEvent.OPEN.value: Event.OPEN,
    EngagementEvent.CLICK.value: Event.CLICK,
    EngagementEvent.SPAMREPORT.value: Event.SPAM_COMPLAINT,
    EngagementEvent.UNSUBSCRIBE.value: Event.UNSUBSCRIBE,
    EngagementEvent.GROUP_UNSUBSCRIBE.value: Event.UNSUBSCRIBE,
    EngagementEvent.GROUP_RESUBSCRIBE.value: Event.RESUBSCRIBE,
    AccountEvent.COMPLIANCE_SUSPENDED.value: Event.ACCOUNT_SUSPENDED,
}


def serialize_email(email):
    return (
        None
        if email is None
        else {
            'message_id': email.message_id,
            'to': email.to,
            'sent': email.created,
            'subject': email.subject,
        }
    )


class SendgridWebhookHandler(BaseWebhookHandler):
    def verify_webhook(self, request: HttpRequest, *args, **kwargs) -> bool:
        verified = False
        try:
            verified = check_sendgrid_signature(request)
        except Exception:
            verified = False
        finally:
            return verified

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        try:
            # Data is coming from JSON, where the root object isn't necessarily
            # guaranteed to be a list.
            # We reverse this because the list appears to be ordered reverse-chronologically
            for payload in reversed(json.loads(request.body)):
                logger.debug(payload)

                # If we can't pick out the exact email, don't try to do anything
                # This can happen if we use django-post_office and generate Emails and Logs
                # before we configure and use this webhook handler
                email = Email.objects.filter(message_id=payload.get('smtp-id', None)).first()
                event = SENDGRID_STATUS_TO_EVENT.get(payload['event'], payload['event'])

                self.handle_event(request, event, payload, *args, email=email, **kwargs)

        except Exception as e:
            logger.error(e)
            # Raise an exception here so Django returns a 500 and emails the admins
            # that something is wrong
            raise Exception(
                'Error when processing Sendgrid Events webhook. The Sendgrid Events Webhook API may have changed.'
            )
        return HttpResponse('ok')

    def handle_event(
        self, request: HttpRequest, event: Event, payload: dict[str, Any], *args, email: Email | None = None, **kwargs
    ) -> None:
        if event in [
            Event.ACCEPTED,
            Event.DELIVERED,
            Event.DEFERRED,
            Event.HARD_BOUNCE,
            Event.SOFT_BOUNCE,
            Event.REJECTED,
        ]:
            return self.log_deliverability_event(request, event, payload, *args, email=email, **kwargs)
        elif event in [
            Event.OPEN,
            Event.CLICK,
            Event.SPAM_COMPLAINT,
            Event.UNSUBSCRIBE,
            Event.RESUBSCRIBE,
        ]:
            return self.log_engagement_event(request, event, payload, *args, email=email, **kwargs)
        elif event == Event.ACCOUNT_SUSPENDED:
            return self.account_suspended(request, event, payload, *args, email=email, **kwargs)
        return self.unrecognized_event(request, event, payload, *args, email=email, **kwargs)

    def unrecognized_event(
        self,
        request: HttpRequest,
        event: str,
        payload: dict[str, Any] | None = None,
        *args,
        email: Email | None = None,
        **kwargs,
    ) -> None:
        info_dict = json.dumps(
            {
                'request.method': request.method,
                'request.headers': dict(request.headers),
                'request.path': request.path,
                'request.body': json.loads(request.body.decode('utf-8')),
                'event': event,
                'payload': payload,
                'args': args,
                'email': serialize_email(email),
            }
            | kwargs,
            indent='  ',
            cls=DjangoJSONEncoder,
        )
        logger.warning(f'Received unrecognized webhook event:\n{info_dict}')
        return HttpResponseNotFound()

    def log_deliverability_event(
        self, request: HttpRequest, event: Event, payload: dict[str, Any], *args, email: Email | None = None, **kwargs
    ) -> None:
        email_status = EVENT_TO_EMAIL_STATUS[event]
        email_log_status = EVENT_TO_EMAIL_LOG_STATUS[event]

        if email:
            email_last_updated = round(email.last_updated.timestamp())
            # Save both the email status and the corresponding log object, or neither
            with transaction.atomic():
                logger.debug(
                    f'[{event.value}] {email_last_updated} < {payload["timestamp"]} -> {email_last_updated < payload["timestamp"]}'
                )
                log_datetime = datetime.fromtimestamp(payload['timestamp'], tz=utc)
                if email_last_updated <= payload['timestamp']:
                    # The UNIX timestamps from Sendgrid only have a time resolution of 1 second.
                    # Sendgrid is sometimes so fast that the time between being processed and delivered is less than 1 second.
                    # Additionally, the events in the webhook are not sorted by time (or they might be sorted by reverse time?)
                    # so on top of relying on timestamp ordering, we also rely on status to avoid overwriting sent status with
                    # queued (from Sendgrid's "processed") status
                    logger.debug(
                        f'not (email.status ({Email.STATUS_CHOICES[email_status][1]}) == STATUS.sent ({Email.STATUS_CHOICES[STATUS.sent][1]}) and '
                        f"payload['event'] ({payload['event']}) == 'processed') -> "
                        f'{not (email.status == STATUS.sent and payload["event"] == "processed")}'
                    )
                    if not (email.status == STATUS.sent and payload['event'] == 'processed'):
                        logger.debug(f'Updating email status to: {Email.STATUS_CHOICES[email_status][1]}')
                        # Avoid calling .save() because that triggers auto_now, which sets last_update to now()
                        Email.objects.filter(pk=email.pk).update(last_updated=log_datetime, status=email_status)

                EmailLog.objects.create(
                    email=email,
                    date=log_datetime,
                    status=email_log_status,
                    message=json.dumps(payload, indent='  '),
                )
                logger.debug('Done saving webhook email logs')
        else:
            info_dict = json.dumps(
                {
                    'request.method': request.method,
                    'request.headers': dict(request.headers),
                    'request.path': request.path,
                    'request.body': json.loads(request.body.decode('utf-8')),
                    'event': event.value,
                    'payload': payload,
                    'args': args,
                    'email': serialize_email(email),
                }
                | kwargs,
                indent='  ',
                cls=DjangoJSONEncoder,
            )
            logger.info(f'Received webhook without a valid reference to an email:\n{info_dict}')

    def log_engagement_event(
        self, request: HttpRequest, event: Event, payload: dict[str, Any], *args, **kwargs
    ) -> None:
        # Engagement events are not send with an 'smtp-id' key, so we will have to dig out logs by
        # searching EmailLog.message for 'sg_message_id' keys and then grab the email reference
        # from that
        email_log = (
            # Not a great way to check, but if we had a JSONField on EmailLog, then we could use
            # normal Django querying to implement a more exact query
            EmailLog.objects.filter(
                # Search for it assuming JSON formatted for human consumption
                Q(message__contains=f'"sg_message_id": "{payload["sg_message_id"]}"')
                # Also search for the sg_message_id, since it's incredibly unlikely that an
                # unrelated email will somehow contain that substring in any EmailLog.message
                | Q(message__contains=payload['sg_message_id'])
            )
            .select_related('email')
            .first()
        )

        if email_log:
            email = email_log.email

            # Save both the email status and the corresponding log object, or neither
            log_datetime = datetime.fromtimestamp(payload['timestamp'], tz=utc)
            with transaction.atomic():
                logger.debug(
                    f'email.status ({email.status} != STATUS.sent ({STATUS.sent})' f' -> {email.status != STATUS.sent}'
                )
                if email.status != STATUS.sent:
                    logger.debug(f'Updating email status to: {STATUS.sent}')
                    # Avoid calling .save() because that triggers auto_now, which sets last_update to now()
                    Email.objects.filter(pk=email.pk).update(last_updated=log_datetime, status=STATUS.sent)

                EmailLog.objects.create(
                    email=email,
                    date=log_datetime,
                    status=STATUS.sent,
                    message=json.dumps(payload, indent='  '),
                )
                logger.debug('Done saving webhook email logs')
        else:
            info_dict = json.dumps(
                {
                    'request.method': request.method,
                    'request.headers': dict(request.headers),
                    'request.path': request.path,
                    'request.body': json.loads(request.body.decode('utf-8')),
                    'event': event.value,
                    'payload': payload,
                    'args': args,
                }
                | {k: serialize_email(v) if isinstance(v, Email) else v for k, v in kwargs.items()},
                indent='  ',
                cls=DjangoJSONEncoder,
            )
            logger.info(f'Received webhook without a valid reference to an email log:\n{info_dict}')

    def account_suspended(
        self, request: HttpRequest, event: Event, payload: dict[str, Any], *args, email: Email | None = None, **kwargs
    ) -> None:
        # This is a bigger deal than a reference to an email that doesn't exist,
        # so we intentionally raise an exception with all given information
        # In production, this will trigger an email with the exception
        # information to settings.ADMINS
        raise Exception('Received webhook regarding account suspension')
