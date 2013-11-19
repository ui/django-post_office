from django.core.files.base import ContentFile
from django.core.mail.backends.base import BaseEmailBackend

from .mail import create


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
        num_sent = 0

        for email in email_messages:
            num_sent += 1
            subject = email.subject
            from_email = email.from_email
            message = email.body
            headers = email.extra_headers

            # Check whether email has 'text/html' alternative
            alternatives = getattr(email, 'alternatives', ())
            for alternative in alternatives:
                if alternative[1] == 'text/html':
                    html_message = alternative[0]
                    break
            else:
                html_message = ''

            attachments = {name: ContentFile(content)
                           for name, content, _ in email.attachments}

            for recipient in email.to:
                create(sender=from_email, recipient=recipient, subject=subject,
                       message=message, html_message=html_message, headers=headers,
                       attachments=attachments)
