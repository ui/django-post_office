"""
A collection of utilities to help process webhook events from email services
"""

from abc import ABCMeta, abstractmethod
from enum import Enum

from django.http import HttpRequest, HttpResponse, HttpResponseNotFound
from django.views import View

from .models import Email


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
    SUSPENDED = 'account_suspended'


class BaseWebhookHandler(View):
    __metaclass__ = ABCMeta

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
        handler = getattr(self, Event.ACCEPTED.value, self.unrecognized_event)
        return handler(request, email, *args, **kwargs)

    def unrecognized_event(self, request: HttpRequest, event: str, *args, email: Email | None = None, **kwargs) -> None:
        pass

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
