"""Optional Django 6.0+ Tasks integration for the existing mail queue."""

import datetime

from django.core.exceptions import ImproperlyConfigured
from django.utils.timezone import now

try:
    from django.tasks import task
except ImportError as exc:
    raise ImproperlyConfigured('The Django Tasks dispatcher requires Django 6.0 or newer.') from exc

from .mail import send_queued_mail_until_done
from .utils import cleanup_expired_mails


@task
def send_queued_mail():
    send_queued_mail_until_done()


@task
def cleanup_mail(days=90, delete_attachments=True):
    cutoff_date = now() - datetime.timedelta(days=days)
    cleanup_expired_mails(cutoff_date, delete_attachments)


def enqueue():
    send_queued_mail.enqueue()
