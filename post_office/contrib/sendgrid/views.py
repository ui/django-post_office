import json
import logging
from datetime import datetime

from pytz import utc

from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from post_office.models import Email, Log as EmailLog, STATUS

from sendgrid_backend.decorators import verify_sendgrid_webhook_signature


logger = logging.getLogger(__name__)


ALL_SENDGRID_EVENTS = {
    "Delivery events": [
        # Message has been received by Sendgrid and is ready to be delivered to the final recipient
        'processed',
        # Message has been dropped from Sendgrid's queue and will not be retried
        'dropped',
        # Message has been successfully delivered to the receiving server
        'delivered',
        # Receiving server temporarily rejected the message
        'deferred',
        # Receiving server could not or would not accept mail to this recipient permanently
        # Bounces can be either "conversational" (eg: immediately after being sent), or asynchronous
        # See https://www.twilio.com/docs/sendgrid/ui/sending-email/bounces#asynchronous-bounces
        'bounce',
        # Receiving server could not or would not accept the message temporarily
        'blocked'
    ],
    "Engagement events": [
        # Recipient has opened the HTML message
        'open',
        # Recipient clicked on a link within the message
        'click',
        # Recipient marked message as spam
        'spamreport',
        # Recipient clicked on the 'Opt Out of All Emails' link (available after clicking the message's
        # subscription management link)
        'unsubscribe',
        # Recipient unsubscribed from a specific group either by clicking the link directly or updating their
        # preferences
        'group_unsubscribe',
        # Recipient resubscribed to a specific group by updating their preferences
        'group_resubscribe',
        # Your account status changed because of issues related to compliance with SendGrid's terms of service
        "compliance_suspend",
    ],
}


# We need to coalesce Sendgrid event names to internal statuses
SENDGRID_STATUS_TO_EMAIL_STATUS = {
    # Message has been successfully delivered to the receiving server
    'delivered': STATUS.sent,

    # Message has been dropped from Sendgrid's queue and will not be retried
    'dropped': STATUS.failed,
    # Receiving server could not or would not accept mail to this recipient permanently
    # Bounces can be either "conversational" (eg: immediately after being sent), or asynchronous
    # See https://www.twilio.com/docs/sendgrid/ui/sending-email/bounces#asynchronous-bounces
    'bounce': STATUS.failed,
    # Receiving server could not or would not accept the message temporarily
    'blocked': STATUS.failed,

    # Message has been received by Sendgrid and is ready to be delivered to the final recipient
    'processed': STATUS.queued,

    # Receiving server temporarily rejected the message
    'deferred': STATUS.requeued,
}


# https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/event
# Post office Log objects have a restricted set of status options
SENDGRID_STATUS_TO_EMAIL_LOG_STATUS = {
    # Delivery events
    # Message has been successfully delivered to the receiving server
    'delivered': STATUS.sent,
    # Message has been received by Sendgrid and is ready to be delivered to the final recipient
    'processed': STATUS.sent,  # Email status: queued
    # Receiving server temporarily rejected the message
    'deferred': STATUS.sent,  # Email status: requeued

    # Message has been dropped from Sendgrid's queue and will not be retried
    'dropped': STATUS.failed,
    # Bounces can be either "conversational" (eg: immediately after being sent), or asynchronous
    # See https://www.twilio.com/docs/sendgrid/ui/sending-email/bounces#asynchronous-bounces
    'bounce': STATUS.failed,
    # Receiving server could not or would not accept the message temporarily
    'blocked': STATUS.failed,
}


@csrf_exempt
@require_POST
@verify_sendgrid_webhook_signature
def sendgrid_deliverability_webhook_handler(request: HttpRequest) -> HttpResponse:
    try:
        # Data is coming from JSON, where the root object isn't necessarily
        # guaranteed to be a list.
        # We reverse this because the list appears to be ordered reverse-chronologically
        for msg_dict in reversed(json.loads(request.body)):
            logger.debug(msg_dict)

            # If we can't pick out the exact email, don't try to do anything
            # This can happen if we use django-post_office and generate Emails and Logs
            # before we configure and use this webhook handler
            if email := Email.objects.filter(
                Q(message_id=msg_dict.get('smtp-id', None))
            ).first():
                # Not all webhook events are email status changes
                logger.debug(f"{SENDGRID_STATUS_TO_EMAIL_STATUS.get(msg_dict['event'], None) = }")
                # The value for 'delivered' in SENDGRID_STATUS_TO_EMAIL_STATUS' can be 0, which evaluates to False, so
                # we check explicitly for None
                event_status = SENDGRID_STATUS_TO_EMAIL_STATUS.get(msg_dict['event'], None)
                if event_status is not None:
                    logger.debug(f"{Email.STATUS_CHOICES[event_status][1] = }")

                    # Save both the email status and the corresponding log object, or neither
                    log_datetime = datetime.fromtimestamp(msg_dict.get('timestamp'), tz=utc)
                    with transaction.atomic():
                        logger.debug(f"{email.last_updated} < {log_datetime} -> {email.last_updated < log_datetime}")
                        if email.last_updated < log_datetime:
                            # The UNIX timestamps from Sendgrid only have a time resolution of 1 second.
                            # Sendgrid is sometimes so fast that the time between being processed and delivered is less than 1 second.
                            # Additionally, the events in the webhook are not sorted by time (or they might be sorted by reverse time?)
                            # so on top of relying on timestamp ordering, we also rely on status to avoid overwriting sent status with
                            # queued (from Sendgrid's "processed") status
                            logger.debug(
                                f"not (email.status ({Email.STATUS_CHOICES[email.status][1]}) == STATUS.sent ({Email.STATUS_CHOICES[STATUS.sent][1]}) and "
                                f"msg_dict['event'] ({msg_dict['event']}) == 'processed') -> "
                                f"{not (email.status == STATUS.sent and msg_dict['event'] == 'processed')}"
                            )
                            if not (email.status == STATUS.sent and msg_dict['event'] == "processed"):
                                logger.debug(f"Updating email status to: {EmailLog.STATUS_CHOICES[event_status][1]}")
                                # Avoid calling .save() because that triggers auto_now, which sets last_update to now()
                                Email.objects.filter(pk=email.pk).update(last_updated=log_datetime, status=event_status)

                        EmailLog.objects.create(
                            email=email,
                            date=datetime.utcfromtimestamp(msg_dict.get('timestamp')),
                            status=SENDGRID_STATUS_TO_EMAIL_LOG_STATUS[msg_dict['event']],
                            message=json.dumps(msg_dict),
                        )
                        logger.debug("Done saving webhook email logs")
    except Exception as e:
        logger.error(e)
        # Raise an exception here so Django returns a 500 and emails the admins
        # that something is wrong
        raise Exception(
            "Error when processing Sendgrid Events webhook. "
            "The Sendgrid Events Webhook API may have changed."
        ) from e
    return HttpResponse("ok")
