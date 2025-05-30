"""
A collection of utilities to help process webhook events from email services
"""

import logging
from abc import ABCMeta, abstractmethod
from enum import Enum
from typing import Any

from django.http import HttpRequest, HttpResponse, HttpResponseNotFound
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .models import STATUS


logger = logging.getLogger(__name__)


class Event(Enum):
    # Deliverability
    ACCEPTED = 'accepted'
    DELIVERED = 'delivered'
    DEFERRED = 'deferred'
    HARD_BOUNCE = 'hard_bounce'
    SOFT_BOUNCE = 'soft_bounce'
    REJECTED = 'rejected'

    # Engagement
    OPEN = 'open'
    CLICK = 'click'

    # Complaints & unsubscribes
    SPAM_COMPLAINT = 'spam_complaint'
    UNSUBSCRIBE = 'unsubscribe'
    RESUBSCRIBE = 'resubscribe'

    # Account
    ACCOUNT_SUSPENDED = 'account_suspended'


EVENT_TO_EMAIL_STATUS = {
    Event.ACCEPTED: STATUS.queued,
    Event.DELIVERED: STATUS.sent,
    Event.DEFERRED: STATUS.requeued,
    Event.HARD_BOUNCE: STATUS.failed,
    Event.SOFT_BOUNCE: STATUS.failed,
    Event.REJECTED: STATUS.failed,
    Event.OPEN: None,
    Event.CLICK: None,
    Event.SPAM_COMPLAINT: None,
    Event.UNSUBSCRIBE: None,
    Event.RESUBSCRIBE: None,
    Event.ACCOUNT_SUSPENDED: None,
}


EVENT_TO_EMAIL_LOG_STATUS = {
    Event.ACCEPTED: STATUS.sent,
    Event.DELIVERED: STATUS.sent,
    Event.DEFERRED: STATUS.sent,
    Event.HARD_BOUNCE: STATUS.failed,
    Event.SOFT_BOUNCE: STATUS.failed,
    Event.REJECTED: STATUS.failed,
    Event.OPEN: None,
    Event.CLICK: None,
    Event.SPAM_COMPLAINT: None,
    Event.UNSUBSCRIBE: None,
    Event.RESUBSCRIBE: None,
    Event.ACCOUNT_SUSPENDED: None,
}


class BaseWebhookHandler(View):
    __metaclass__ = ABCMeta

    @csrf_exempt
    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        # The same method as View.dispatch, but we verify the webhook once
        # we verify the HTTP method
        if request.method.lower() in self.http_method_names:
            if not self.verify_webhook(request, *args, **kwargs):
                return HttpResponseNotFound()
            handler = getattr(
                self,
                request.method.lower(),
                self.http_method_not_allowed,
            )
        else:
            handler = self.http_method_not_allowed
        return handler(request, *args, **kwargs)

    @abstractmethod
    def verify_webhook(self, request: HttpRequest, *args, **kwargs) -> bool:
        pass

    @abstractmethod
    def handle_event(self, request: HttpRequest, event: Event, payload: dict[str, Any], *args, **kwargs) -> None:
        pass
