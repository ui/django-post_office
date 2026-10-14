from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PostOfficeConfig(AppConfig):
    name = 'post_office'
    verbose_name = _('Post Office')
    default_auto_field = 'django.db.models.AutoField'

    def ready(self):
        from post_office import tasks
        from post_office.settings import get_celery_enabled, get_config, get_task_dispatcher
        from post_office.signals import email_queued

        if 'TASK_DISPATCHER' in get_config():
            if get_task_dispatcher() is not None:
                from post_office.task_dispatch import queued_mail_handler

                email_queued.connect(queued_mail_handler)
        elif get_celery_enabled():
            email_queued.connect(tasks.queued_mail_handler)
