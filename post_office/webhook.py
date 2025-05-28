"""
A collection of utilities to help process webhook events from email services
"""

import json
import logging
from abc import ABCMeta, abstractmethod
from enum import Enum
from typing import Any

from django.http import HttpRequest, HttpResponse, HttpResponseNotFound
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .models import Email


logger = logging.getLogger(__name__)


class Event(Enum):
    # Deliverability
    ACCEPTED = 'accepted'
    DELIVERED = 'delivered'
    DEFERRED = 'deferred'
    HARD_BOUNCE = 'hard_bounce'
    SOFT_BOUNCE = 'soft_bounced'
    REJECTED = 'rejected'

    # Engagement
    OPEN = 'opened'
    CLICK = 'clicked'

    # Complaints & unsubscribes
    SPAM_COMPLAINT = 'spam_complaint'
    UNSUBSCRIBED = 'unsubscribed'
    RESUBSCRIBED = 'resubscribed'

    # Account
    ACCOUNT_SUSPENDED = 'account_suspended'


class BaseWebhookHandler(View):
    __metaclass__ = ABCMeta

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs) -> HttpResponse:
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

    def process_event(self, request: HttpRequest, event: Event, email: Email | None = None, *args, **kwargs) -> None:
        handler = getattr(self, event.value, None)
        if handler:
            return handler(request, *args, email=email, **kwargs)
        return HttpResponseNotFound()

    def unrecognized_event(
        self,
        request: HttpRequest,
        event: str,
        *args,
        email: Email | None = None,
        data: dict[str, Any] | None = None,
        **kwargs,
    ) -> None:
        logger.warning(f"Received unrecognized webhook event:\n{json.dumps(data, indent='  ')}")

    def accepted(self, request: HttpRequest, *args, email: Email | None = None, **kwargs) -> None:
        pass

    def delivered(self, request: HttpRequest, *args, email: Email | None = None, **kwargs) -> None:
        pass

    def deferred(self, request: HttpRequest, *args, email: Email | None = None, **kwargs) -> None:
        pass

    def hard_bounce(self, request: HttpRequest, *args, email: Email | None = None, **kwargs) -> None:
        pass

    def soft_bounce(self, request: HttpRequest, *args, email: Email | None = None, **kwargs) -> None:
        pass

    def rejected(self, request: HttpRequest, *args, email: Email | None = None, **kwargs) -> None:
        pass

    def opened(self, request: HttpRequest, *args, email: Email | None = None, **kwargs) -> None:
        pass

    def clicked(self, request: HttpRequest, *args, email: Email | None = None, **kwargs) -> None:
        pass

    def spam_complaint(self, request: HttpRequest, *args, email: Email | None = None, **kwargs) -> None:
        pass

    def unsubscribed(self, request: HttpRequest, *args, email: Email | None = None, **kwargs) -> None:
        pass

    def resubscribed(self, request: HttpRequest, *args, email: Email | None = None, **kwargs) -> None:
        pass

    def account_suspended(self, request: HttpRequest, *args, email: Email | None = None, **kwargs) -> None:
        pass
