"""
This module is autoloaded by Celery.autodiscover_tasks() and by PostOfficeConfig.ready().
It must never be imported elsewhere.
"""
from celery import shared_task

from post_office.mail import send_queued


@shared_task(ignore_result=True)
def send_queued_mail(*args, **kwargs):
    send_queued()
