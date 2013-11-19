from django.core.files.base import ContentFile
from django.core.mail.backends.base import BaseEmailBackend

from .models import Email, PRIORITY, STATUS
from .utils import add_attachments


class EmailBackend(BaseEmailBackend):

    def open(self):
        pass

    def close(self):
        pass

    def send_messages(self, email_messages):
        """
        Queue one or more EmailMessage objects and returns the number of
        email_message messages sent.
        """
        if not email_messages:
            return
        num_sent = 0

        for email_message in email_messages:
            num_sent += 1
            subject = email_message.subject
            from_email = email_message.from_email
            message = email_message.body
            headers = email_message.extra_headers

            # Check whether email_message has 'text/html' alternative
            alternatives = getattr(email_message, 'alternatives', ())
            for alternative in alternatives:
                if alternative[1] == 'text/html':
                    html_message = alternative[0]
                    break
            else:
                html_message = ''

            for recipient in email_message.to:
                email = Email.objects.create(from_email=from_email, to=recipient,
                                             subject=subject, html_message=html_message,
                                             message=message, status=STATUS.queued,
                                             headers=headers, priority=PRIORITY.medium)

                if email_message.attachments:
                    attachments = {name: ContentFile(content) for
                                   name, content, _ in email_message.attachments}
                    add_attachments(email, attachments)
