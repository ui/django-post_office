from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PostOfficeConfig(AppConfig):
    name = 'post_office'
    verbose_name = _("Post Office")

    def ready(self):
        from post_office import tasks
        from post_office.signals import email_queued

        email_queued.connect(tasks.queued_mail_handler)
