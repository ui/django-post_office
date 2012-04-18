from django.core.mail.backends.base import BaseEmailBackend

from .models import Email, PRIORITY, STATUS


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

            for recipient in email.to:
                Email.objects.create(from_email=from_email, to=recipient, subject=subject,
                    message=message, status=STATUS.queued, priority=PRIORITY.medium)

