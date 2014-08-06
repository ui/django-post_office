from django.core.files.base import ContentFile
from django.core.mail.backends.base import BaseEmailBackend

from .mail import create
from .settings import get_default_priority
from .utils import create_attachments


class EmailBackend(BaseEmailBackend):

    def open(self):
        pass

    def close(self):
        pass

    def send_messages(self, email_messages):
        """
        Queue one or more EmailMessage objects and returns the number of
        email messages sent.
        """
        if not email_messages:
            return

        for email_message in email_messages:
            subject = email_message.subject
            from_email = email_message.from_email
            message = email_message.body
            headers = email_message.extra_headers

            # Check whether email has 'text/html' alternative
            alternatives = getattr(email_message, 'alternatives', ())
            for alternative in alternatives:
                if alternative[1] == 'text/html':
                    html_message = alternative[0]
                    break
            else:
                html_message = ''

            attachment_files = dict([(name, ContentFile(content))
                                    for name, content, _ in email_message.attachments])

            email = create(sender=from_email,
                           recipients=email_message.to, cc=email_message.cc,
                           bcc=email_message.bcc, subject=subject,
                           message=message, html_message=html_message,
                           headers=headers)

            if attachment_files:
                attachments = create_attachments(attachment_files)

                email.attachments.add(*attachments)

            if get_default_priority() == 'now':
                email.dispatch()
