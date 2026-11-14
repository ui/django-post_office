from __future__ import annotations

import base64
from copy import deepcopy
from email import encoders, message_from_bytes, policy
from email.header import Header
from email.message import MIMEPart
from email.mime.base import MIMEBase
from email.mime.nonmultipart import MIMENonMultipart
from typing import TYPE_CHECKING

from django.core.mail import EmailMessage
from django.core.mail.message import DEFAULT_ATTACHMENT_MIME_TYPE

from .settings import PRE_DJANGO_6

if TYPE_CHECKING:
    from .models import Attachment


def _serialize_mime_part(attachment: MIMEBase | MIMEPart) -> tuple[bytes, dict[str, str | Header]]:
    # Serialization can set multipart boundaries, so work on a copy.
    attachment = deepcopy(attachment)
    # Base64-encode leaf payloads so serialization cannot rewrite their line endings.
    for part in attachment.walk():
        if part.is_multipart():
            continue
        data = part.get_payload(decode=True)
        if data is None:
            continue
        del part['Content-Transfer-Encoding']
        part.set_payload(data)
        encoders.encode_base64(part)

    # policy.default uses LF line endings, which the header/body split relies on.
    payload = attachment.as_bytes(policy=policy.default).partition(b'\n\n')[2]
    # Collect headers after serialization so they include any generated boundary.
    return payload, dict(attachment.items())


def attach_to_message(message: EmailMessage, attachment: Attachment) -> None:
    """Read a stored attachment and attach it to a Django email message."""
    with attachment.file.open('rb') as file:
        payload = file.read()
    if not attachment.headers:
        message.attach(attachment.name, payload, mimetype=attachment.mimetype or None)
        return

    headers = dict(attachment.headers)
    mime_headers = {name.lower(): value for name, value in headers.items()}
    content_type = mime_headers.get('content-type', attachment.mimetype or DEFAULT_ATTACHMENT_MIME_TYPE)
    media_type = content_type.partition(';')[0].strip().lower()
    # Match email.message's fallback for malformed media types.
    if media_type.count('/') != 1:
        media_type = 'text/plain'
    maintype, subtype = media_type.split('/')
    is_container = maintype in ('multipart', 'message')
    if not is_container and 'content-transfer-encoding' not in mime_headers:
        # Without a transfer encoding, sending can rewrite line endings in the raw bytes.
        payload = base64.encodebytes(payload)
        headers['Content-Transfer-Encoding'] = 'base64'

    if PRE_DJANGO_6:
        mime_part = MIMENonMultipart(maintype, subtype)
        mime_part.set_payload(payload)
        for key, val in headers.items():
            try:
                mime_part.replace_header(key, val)
            except KeyError:
                mime_part.add_header(key, val)
        if is_container:
            # Restore the child parts from the stored MIME body before attaching.
            mime_part.set_payload(message_from_bytes(mime_part.as_bytes()).get_payload())
    else:
        if 'content-type' not in mime_headers:
            headers['Content-Type'] = content_type
        header_bytes = b''.join(policy.default.fold_binary(name, value) for name, value in headers.items())
        # Parsing restores the child parts of multipart and message attachments.
        mime_part = message_from_bytes(header_bytes + b'\n' + payload, _class=MIMEPart, policy=policy.default)
    message.attach(mime_part)
