from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _
from django.utils.module_loading import import_string


class PostOfficeConfig(AppConfig):
    name = 'post_office'
    verbose_name = _("Post Office")

    def ready(self):
        from post_office.signals import email_queued

        try:
            self._send_queued_mail = import_string('post_office.tasks.send_queued_mail')
        except ImportError:
            pass  # Celery is not installed
        else:
            email_queued.connect(self.send_queued_mail)

    def send_queued_mail(self, **kwargs):
        self._send_queued_mail.delay()
