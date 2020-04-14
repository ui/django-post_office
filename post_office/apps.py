from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _
from django.utils.module_loading import import_string


class PostOfficeConfig(AppConfig):
    name = 'post_office'
    verbose_name = _("Post Office")

    def ready(self):
        from post_office.signals import email_queued

        try:
            queued_mail_handler = import_string('post_office.tasks.queued_mail_handler')
            email_queued.connect(queued_mail_handler)
        except ImportError:
            pass  # Celery is not installed
