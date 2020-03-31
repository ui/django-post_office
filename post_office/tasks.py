"""
This module is autoloaded by Celery.autodiscover_tasks() and by PostOfficeConfig.ready().
It must never be imported elsewhere.
"""
import datetime
from celery import shared_task

from django.utils.timezone import now

from post_office.mail import send_queued
from post_office.utils import cleanup_expired_mails


@shared_task(ignore_result=True)
def send_queued_mail(*args, **kwargs):
    send_queued()


def queued_mail_handler(sender, **kwargs):
    """
    To be called by post_office.signals.email_queued.send()
    """
    send_queued_mail.delay()


@shared_task(ignore_result=True)
def cleanup_mail(*args, **kwargs):
    days = kwargs.get('days', 90)
    cutoff_date = now() - datetime.timedelta(days)
    delete_attachments = kwargs.get('delete_attachments', True)
    cleanup_expired_mails(cutoff_date, delete_attachments)
