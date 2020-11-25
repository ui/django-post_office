"""
Only define the tasks and handler if we can import celery.
This allows the module to be imported in environments without Celery, for
example by other task queue systems such as Huey, which use the same pattern
of auto-discovering tasks in "tasks" submodules.
"""
import datetime

from django.utils.timezone import now

from post_office.mail import send_all_in_queue
from post_office.utils import cleanup_expired_mails

from .settings import get_celery_enabled

try:
    if get_celery_enabled():
        from celery import shared_task
    else:
        raise NotImplementedError()
except (ImportError, NotImplementedError):
    pass
else:
    @shared_task(ignore_result=True)
    def send_queued_mail(*args, **kwargs):
        """
        To be called by the Celery task manager.
        """
        send_all_in_queue()

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
