from collections import OrderedDict
from email.mime.base import MIMEBase
from django.core.files.base import ContentFile
from django.core.mail.backends.base import BaseEmailBackend

from .settings import get_default_priority


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
        from .mail import create
        from .utils import create_attachments

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
                if alternative[1].startswith('text/html'):
                    html_message = alternative[0]
                    break
            else:
                html_message = ''

            attachment_files = {}
            for attachment in email_message.attachments:
                if isinstance(attachment, MIMEBase):
                    attachment_files[attachment.get_filename()] = {
                        'file': ContentFile(attachment.get_payload()),
                        'mimetype': attachment.get_content_type(),
                        'headers': OrderedDict(attachment.items()),
                    }
                else:
                    attachment_files[attachment[0]] = ContentFile(attachment[1])

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
