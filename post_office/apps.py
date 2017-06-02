from django.apps import AppConfig


class PostOfficeConfig(AppConfig):
    name = 'post_office'
    verbose_name = "Post Office"

    def ready(self):
        import post_office.signals
