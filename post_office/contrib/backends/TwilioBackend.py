from django.core.mail.backends.base import BaseEmailBackend

from twilio.rest import TwilioRestClient


class TwilioBackend(BaseEmailBackend):

    def send_messages(self, email_messages):
        counter = 0
        for email_message in email_messages:
            if self._send(email_message):
                counter += 1
        return counter

    def _send(self, email_message):
        if not email_message.recipients():
            return False

        for recipient in email_message.recipients():
            pass

        return True
