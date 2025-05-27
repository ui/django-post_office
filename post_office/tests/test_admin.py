import json
import os

from datetime import datetime, timedelta

from django.conf import settings as django_settings, settings
from django.contrib.admin.sites import AdminSite
from django.core import mail
from django.core import serializers
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.forms.models import modelform_factory
from django.test import TestCase
from django.utils import timezone

from ..admin import AttachmentInline
from ..models import Email, Log, PRIORITY, STATUS, EmailTemplate, Attachment
from ..mail import send


class MockRequest:
    pass


class MockSuperUser:
    def has_perm(self, perm, obj=None):
        return True


class EmailAdminTest(TestCase):
    def setUp(self):
        self.site = AdminSite()

        self.request = MockRequest()
        self.request.user = MockSuperUser()

    def test_attachmentinline_contentdisposition_header(self):
        email = Email.objects.create(to=['to@example.com'], from_email='from@example.com', subject='Subject')

        mt = 'text/plain'
        attachment_1 = Attachment(mimetype=mt, headers={"Doesn't Have Content-Disposition Header": 'Nope'})
        attachment_1.file.save('test_attachment_1.txt', content=ContentFile('test file content 1'), save=True)
        email.attachments.add(attachment_1)

        attachment_2 = Attachment(
            mimetype=mt, headers={'Content-Disposition': "Content-Disposition header doesn't start with 'inline'"}
        )
        attachment_2.file.save('test_attachment_2.txt', content=ContentFile('test file content 2'), save=True)
        email.attachments.add(attachment_2)

        attachment_3 = Attachment(mimetype=mt, headers={'Content-Disposition': 'inline something'})
        attachment_3.file.save('test_attachment_3.txt', content=ContentFile('test file content 3'), save=True)
        email.attachments.add(attachment_3)

        message = email.email_message()

        attachment_inline = AttachmentInline(Email, self.site)
        attachment_inline.parent_obj = email

        qs_result = attachment_inline.get_queryset(self.request)
        non_inline_attachments = [a_through.attachment for a_through in qs_result]

        self.assertIn(attachment_1, non_inline_attachments)
        self.assertIn(attachment_2, non_inline_attachments)
        self.assertNotIn(attachment_3, non_inline_attachments)
        self.assertEqual(len(non_inline_attachments), 2)
