from django.dispatch import Signal

email_queued = Signal(providing_args=['email'])
