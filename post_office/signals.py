
from django.db.models.signals import post_init
from django.dispatch import receiver

from .models import Email
from .fields import CommaSeparatedEmailField


@receiver(post_init, sender=Email)
def on_email_post_init(sender, instance, **kwargs):
    for field in {"to", "cc", "bcc"}:
        value = CommaSeparatedEmailField.parse_value(getattr(instance, field))
        setattr(instance, field, value)
