import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any

from pytz import utc

from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from post_office.models import Email, Log as EmailLog, STATUS
from post_office.webhook import Event, BaseWebhookHandler

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
    DeliverabilityEvent.PROCESSED.value: Event.ACCEPTED,
    DeliverabilityEvent.DELIVERED.value: Event.DELIVERED,
    DeliverabilityEvent.DEFERRED.value: Event.DEFERRED,
    DeliverabilityEvent.BOUNCE.value: Event.HARD_BOUNCE,
    DeliverabilityEvent.BLOCKED.value: Event.SOFT_BOUNCE,
    DeliverabilityEvent.DROPPED.value: Event.REJECTED,
    EngagementEvent.OPEN.value: Event.OPEN,
    EngagementEvent.CLICK.value: Event.CLICK,
    EngagementEvent.SPAMREPORT.value: Event.SPAM_COMPLAINT,
    EngagementEvent.UNSUBSCRIBE.value: Event.UNSUBSCRIBED,
    EngagementEvent.GROUP_UNSUBSCRIBE.value: Event.UNSUBSCRIBED,
    EngagementEvent.GROUP_RESUBSCRIBE.value: Event.RESUBSCRIBED,
    AccountEvent.COMPLIANCE_SUSPENDED.value: Event.ACCOUNT_SUSPENDED,
}


EVENT_TO_EMAIL_STATUS = {
    # Message has been received by Sendgrid and is ready to be delivered to the final recipient
    Event.ACCEPTED.value: STATUS.queued,
    # Message has been successfully delivered to the receiving server
    Event.DELIVERED.value: STATUS.sent,
    # Receiving server temporarily rejected the message
    Event.DEFERRED.value: STATUS.requeued,
    # Receiving server could not or would not accept mail to this recipient permanently
    # Bounces can be either "conversational" (eg: immediately after being sent), or asynchronous
    # See https://www.twilio.com/docs/sendgrid/ui/sending-email/bounces#asynchronous-bounces
    Event.HARD_BOUNCE.value: STATUS.failed,
    # Receiving server could not or would not accept the message temporarily
    Event.SOFT_BOUNCE.value: STATUS.failed,
    # Message has been dropped from Sendgrid's queue and will not be retried
    Event.REJECTED.value: STATUS.failed,
    Event.OPEN.value: None,
    Event.CLICK.value: None,
    Event.SPAM_COMPLAINT.value: None,
    Event.UNSUBSCRIBED.value: None,
    Event.RESUBSCRIBED.value: None,
    AccountEvent.COMPLIANCE_SUSPENDED: None,
}


EVENT_TO_EMAIL_LOG_STATUS = {
    # Message has been received by Sendgrid and is ready to be delivered to the final recipient
    Event.ACCEPTED.value: STATUS.sent,
    # Message has been successfully delivered to the receiving server
    Event.DELIVERED.value: STATUS.sent,
    # Receiving server temporarily rejected the message
    Event.DEFERRED.value: STATUS.sent,
    # Receiving server could not or would not accept mail to this recipient permanently
    # Bounces can be either "conversational" (eg: immediately after being sent), or asynchronous
    # See https://www.twilio.com/docs/sendgrid/ui/sending-email/bounces#asynchronous-bounces
    Event.HARD_BOUNCE.value: STATUS.failed,
    # Receiving server could not or would not accept the message temporarily
    Event.SOFT_BOUNCE.value: STATUS.failed,
    # Message has been dropped from Sendgrid's queue and will not be retried
    Event.REJECTED.value: STATUS.failed,
    Event.OPEN.value: None,
    Event.CLICK.value: None,
    Event.SPAM_COMPLAINT.value: None,
    Event.UNSUBSCRIBED.value: None,
    Event.RESUBSCRIBED.value: None,
    Event.ACCOUNT_SUSPENDED.value: None,
}


class SendgridWebhookHandler(BaseWebhookHandler):
    def verify_webhook(self, request: HttpRequest, *args, **kwargs) -> bool:
        return check_sendgrid_signature(request)

    @csrf_exempt
    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        try:
            # Data is coming from JSON, where the root object isn't necessarily
            # guaranteed to be a list.
            # We reverse this because the list appears to be ordered reverse-chronologically
            for msg_dict in reversed(json.loads(request.body)):
                logger.debug(msg_dict)

                # If we can't pick out the exact email, don't try to do anything
                # This can happen if we use django-post_office and generate Emails and Logs
                # before we configure and use this webhook handler
                email = Email.objects.filter(message_id=msg_dict.get('smtp-id', None)).first()
                event = SENDGRID_STATUS_TO_EVENT.get(msg_dict['event'], None)

                if event is not None:
                    self.process_event(request, event, email=email, data=msg_dict)
                else:
                    self.unrecognized_event(request, msg_dict['event'], email=email, data=msg_dict)

        except Exception as e:
            logger.error(e)
            # Raise an exception here so Django returns a 500 and emails the admins
            # that something is wrong
            raise Exception(
                'Error when processing Sendgrid Events webhook. The Sendgrid Events Webhook API may have changed.'
            ) from e
        return HttpResponse('ok')

    def accepted(self, request: HttpRequest, *args, email: Email | None = None, **kwargs) -> None:
        self.log_deliverability_event(request, *args, event=Event.ACCEPTED, email=email, **kwargs)

    def delivered(self, request: HttpRequest, *args, email: Email | None = None, **kwargs) -> None:
        self.log_deliverability_event(request, *args, event=Event.DELIVERED, email=email, **kwargs)

    def deferred(self, request: HttpRequest, *args, email: Email | None = None, **kwargs) -> None:
        self.log_deliverability_event(request, *args, event=Event.DEFERRED, email=email, **kwargs)

    def hard_bounce(self, request: HttpRequest, *args, email: Email | None = None, **kwargs) -> None:
        self.log_deliverability_event(request, *args, event=Event.HARD_BOUNCE, email=email, **kwargs)

    def soft_bounce(self, request: HttpRequest, *args, email: Email | None = None, **kwargs) -> None:
        self.log_deliverability_event(request, *args, event=Event.SOFT_BOUNCE, email=email, **kwargs)

    def rejected(self, request: HttpRequest, *args, email: Email | None = None, **kwargs) -> None:
        self.log_deliverability_event(request, *args, event=Event.REJECTED, email=email, **kwargs)

    def log_deliverability_event(
        self, request: HttpRequest, *args, event: Event, email: Email, data: dict[str, Any], **kwargs
    ) -> None:
        email_status = EVENT_TO_EMAIL_STATUS[event.value]
        email_log_status = EVENT_TO_EMAIL_LOG_STATUS[event.value]

        if email:
            # Save both the email status and the corresponding log object, or neither
            log_datetime = datetime.fromtimestamp(data['timestamp'], tz=utc)
            with transaction.atomic():
                logger.debug(f'{email.last_updated} < {log_datetime} -> {email.last_updated < log_datetime}')

                if email.last_updated < log_datetime:
                    # The UNIX timestamps from Sendgrid only have a time resolution of 1 second.
                    # Sendgrid is sometimes so fast that the time between being processed and delivered is less than 1 second.
                    # Additionally, the events in the webhook are not sorted by time (or they might be sorted by reverse time?)
                    # so on top of relying on timestamp ordering, we also rely on status to avoid overwriting sent status with
                    # queued (from Sendgrid's "processed") status
                    logger.debug(
                        f'not (email.status ({Email.STATUS_CHOICES[email_status][1]}) == STATUS.sent ({Email.STATUS_CHOICES[STATUS.sent][1]}) and '
                        f"data['event'] ({data['event']}) == 'processed') -> "
                        f'{not (email.status == STATUS.sent and data["event"] == "processed")}'
                    )
                    if not (email.status == STATUS.sent and data['event'] == 'processed'):
                        logger.debug(f'Updating email status to: {Email.STATUS_CHOICES[email_status][1]}')
                        # Avoid calling .save() because that triggers auto_now, which sets last_update to now()
                        Email.objects.filter(pk=email.pk).update(last_updated=log_datetime, status=email_status)

                EmailLog.objects.create(
                    email=email,
                    date=log_datetime,
                    status=email_log_status,
                    message=json.dumps(data, indent='  '),
                )
                logger.debug('Done saving webhook email logs')
        else:
            logger.info("Received webhook without a valid reference to an email:\n" f"{json.dumps(data, indent='  ')}")

    def opened(self, request: HttpRequest, *args, email: Email | None = None, **kwargs) -> None:
        self.log_engagement_event(request, *args, event=Event.OPEN, email=email, **kwargs)

    def clicked(self, request: HttpRequest, *args, email: Email | None = None, **kwargs) -> None:
        self.log_engagement_event(request, *args, event=Event.CLICK, email=email, **kwargs)

    def spam_complaint(self, request: HttpRequest, *args, email: Email | None = None, **kwargs) -> None:
        self.log_engagement_event(request, *args, event=Event.SPAM_COMPLAINT, email=email, **kwargs)

    def unsubscribed(self, request: HttpRequest, *args, email: Email | None = None, **kwargs) -> None:
        self.log_engagement_event(request, *args, event=Event.UNSUBSCRIBED, email=email, **kwargs)

    def resubscribed(self, request: HttpRequest, *args, email: Email | None = None, **kwargs) -> None:
        self.log_engagement_event(request, *args, event=Event.RESUBSCRIBED, email=email, **kwargs)

    def log_engagement_event(
        self, request: HttpRequest, *args, event: Event, email: Email, data: dict[str, Any], **kwargs
    ) -> None:
        email_log = (
            EmailLog.objects.filter(
                Q(message__contains=f'"sg_message_id": "{data["sg_message_id"]}"')
                | Q(message__contains=data['sg_message_id'])
            )
            .select_related('email')
            .first()
        )

        if email_log:
            email = email_log.email

            # Save both the email status and the corresponding log object, or neither
            log_datetime = datetime.fromtimestamp(data['timestamp'], tz=utc)
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
                    message=json.dumps(data, indent='  '),
                )
                logger.debug('Done saving webhook email logs')
        else:
            logger.info(
                "Received webhook without a valid reference to an email log:\n" f"{json.dumps(data, indent='  ')}"
            )

    def account_suspended(
        self, request: HttpRequest, *args, email: Email | None = None, data: dict[str, Any], **kwargs
    ) -> None:
        # This is a bigger deal than a reference to an email that doesn't exist,
        # so we intentionally raise an exception with all given information
        raise Exception("Received webhook regarding account suspension:\n" f"{json.dumps(data, indent='  ')}")
