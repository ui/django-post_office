from typing import TYPE_CHECKING

from django.core.mail import EmailMessage, EmailMultiAlternatives

if TYPE_CHECKING:
    from .models import Email


class PostOfficeEmailMessage(EmailMessage):
    def __init__(self, email: 'Email', *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.post_office_email = email


class PostOfficeEmailMultiAlternatives(EmailMultiAlternatives):
    def __init__(self, email: 'Email', *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.post_office_email = email
