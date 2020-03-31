from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _
from django.utils.module_loading import import_string


class PostOfficeConfig(AppConfig):
    name = 'post_office'
    verbose_name = _("Post Office")

    def ready(self):
        try:
            self.send_queued_mail = import_string('post_office.tasks.send_queued_mail')
        except ImportError:  # Celery is not installed
            self.send_queued_mail = type('task', (), {'delay': lambda *args: None})
