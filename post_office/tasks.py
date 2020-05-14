import datetime

from django.utils.timezone import now

from post_office.mail import send_queued
from post_office.utils import cleanup_expired_mails

# Only define the tasks and handler if we can import celery.
# This allows the module to be imported in environments without Celery, for
# example by other task queue systems such as Huey, which use the same pattern
# of auto-discovering tasks in "tasks" submodules
try:
    from celery import shared_task
except ImportError:
    pass
else:
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
