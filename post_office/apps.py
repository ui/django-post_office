from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _
from django.utils.module_loading import import_string


class PostOfficeConfig(AppConfig):
    name = 'post_office'
    verbose_name = _("Post Office")

    def ready(self):
        try:
            self.send_queued_mail_task = import_string('post_office.tasks.send_queued_mail')
        except ImportError:  # Celery is not installed
            self.send_queued_mail_task = type('task', (), {'delay': lambda *args: None})

    def send_queued_mail(self):
        self.send_queued_mail_task.delay()
