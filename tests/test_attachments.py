from email import message_from_bytes, policy
from email.generator import BytesGenerator
from email.message import Message
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.test import SimpleTestCase

from post_office.attachments import attach_to_message
from post_office.models import Attachment


class StoredAttachmentTest(SimpleTestCase):
    def test_attachment_without_headers_uses_stored_mimetype(self):
        attachment = Attachment(name='data', file=ContentFile(b'{}', name='data'), mimetype='application/json')
        message = EmailMessage(body='Body')

        attach_to_message(message, attachment)

        self.assertEqual(message.attachments, [('data', b'{}', 'application/json')])

    def test_raw_binary_attachment_with_headers(self):
        raw = b'\x00\xffa\nb\rc'
        attachment = Attachment(name='x.bin', file=ContentFile(raw, name='x.bin'), headers={'Content-ID': '<x>'})
        message = EmailMessage(body='Body')

        attach_to_message(message, attachment)

        wire = BytesIO()
        BytesGenerator(wire, policy=policy.SMTP).flatten(message.message())
        sent = message_from_bytes(wire.getvalue()).get_payload(1)
        assert isinstance(sent, Message)
        self.assertEqual(sent['Content-ID'], '<x>')
        self.assertEqual(sent.get_content_type(), 'application/octet-stream')
        self.assertEqual(sent.get_payload(decode=True), raw)

    def test_content_type_header_takes_precedence_over_stored_mimetype(self):
        attachment = Attachment(
            name='bundle',
            file=ContentFile(b'--example\nContent-Type: text/plain\n\nchild\n--example--\n', name='bundle'),
            mimetype='application/octet-stream',
            headers={'content-type': 'Multipart/Mixed; boundary="example"'},
        )
        message = EmailMessage(body='Body')

        attach_to_message(message, attachment)

        part = message.attachments[0]
        self.assertEqual(part.get_content_type(), 'multipart/mixed')
        self.assertEqual(part.get_payload(0).get_payload(decode=True), b'child')
