# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import sys
from uuid import uuid4

from collections import namedtuple

from django.conf import settings
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.db import models
from django.utils.translation import ugettext_lazy as _
from post_office.fields import CommaSeparatedEmailField

try:
    from django.utils.encoding import smart_text  # For Django >= 1.5
except ImportError:
    from django.utils.encoding import smart_unicode as smart_text

from django.template import Context, Template

from jsonfield import JSONField
from post_office import cache
from .compat import text_type
from .connections import connections
from .settings import context_field_class, get_log_level
from .validators import validate_email_with_name, validate_template_syntax


PRIORITY = namedtuple('PRIORITY', 'low medium high now')._make(range(4))
STATUS = namedtuple('STATUS', 'sent failed queued')._make(range(3))


class Email(models.Model):
    """
    A model to hold email information.
    """

    PRIORITY_CHOICES = [(PRIORITY.low, _("low")), (PRIORITY.medium, _("medium")),
                        (PRIORITY.high, _("high")), (PRIORITY.now, _("now"))]
    STATUS_CHOICES = [(STATUS.sent, _("sent")), (STATUS.failed, _("failed")),
                      (STATUS.queued, _("queued"))]

    from_email = models.CharField(_("Email From"), max_length=254,
                                  validators=[validate_email_with_name])
    to = CommaSeparatedEmailField(_("Email To"))
    cc = CommaSeparatedEmailField(_("Cc"))
    bcc = CommaSeparatedEmailField(("Bcc"))
    subject = models.CharField(_("Subject"), max_length=255, blank=True)
    message = models.TextField(_("Message"), blank=True)
    html_message = models.TextField(_("HTML Message"), blank=True)
    """
    Emails with 'queued' status will get processed by ``send_queued`` command.
    Status field will then be set to ``failed`` or ``sent`` depending on
    whether it's successfully delivered.
    """
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES, db_index=True,
                                              blank=True, null=True)
    priority = models.PositiveSmallIntegerField(choices=PRIORITY_CHOICES,
                                                blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    last_updated = models.DateTimeField(db_index=True, auto_now=True)
    scheduled_time = models.DateTimeField(blank=True, null=True, db_index=True)
    headers = JSONField(blank=True, null=True)
    template = models.ForeignKey('post_office.EmailTemplate', blank=True, null=True)
    context = context_field_class(blank=True, null=True)
    backend_alias = models.CharField(blank=True, default='', max_length=64)

    class Meta:
        app_label = 'post_office'

    def __unicode__(self):
        return u'%s' % self.to

    def email_message(self, connection=None):
        """
        Returns a django ``EmailMessage`` or ``EmailMultiAlternatives`` object,
        depending on whether html_message is empty.
        """
        subject = smart_text(self.subject)

        if self.template is not None:
            _context = Context(self.context)
            subject = Template(self.template.subject).render(_context)
            message = Template(self.template.content).render(_context)
            html_message = Template(self.template.html_content).render(_context)

        else:
            subject = self.subject
            message = self.message
            html_message = self.html_message

        if html_message:
            msg = EmailMultiAlternatives(
                subject=subject, body=message, from_email=self.from_email,
                to=self.to, bcc=self.bcc, cc=self.cc,
                connection=connection, headers=self.headers)
            msg.attach_alternative(html_message, "text/html")
        else:
            msg = EmailMessage(
                subject=subject, body=message, from_email=self.from_email,
                to=self.to, bcc=self.bcc, cc=self.cc,
                connection=connection, headers=self.headers)

        for attachment in self.attachments.all():
            msg.attach(attachment.name, attachment.file.read())

        return msg

    def dispatch(self, log_level=None, disconnect_after_delivery=True):
        """
        Actually send out the email and log the result
        """

        if log_level is None:
            log_level = get_log_level()

        connection = None
        try:
            connection = connections[self.backend_alias or 'default']
            self.email_message(connection=connection).send()
            status = STATUS.sent
            message = ''
            exception_type = ''
        except:
            status = STATUS.failed
            exception, message, _ = sys.exc_info()
            exception_type = exception.__name__

        if connection and disconnect_after_delivery:
            connection.close()

        self.status = status
        self.save()

        # If log level is 0, log nothing, 1 logs only sending failures
        # and 2 means log both successes and failures
        if log_level == 1:
            if status == STATUS.failed:
                self.logs.create(status=status, message=message,
                                 exception_type=exception_type)
        elif log_level == 2:
            self.logs.create(status=status, message=message,
                             exception_type=exception_type)

        return status

    def save(self, *args, **kwargs):
        self.full_clean()
        return super(Email, self).save(*args, **kwargs)


class Log(models.Model):
    """
    A model to record sending email sending activities.
    """

    STATUS_CHOICES = [(STATUS.sent, _("sent")), (STATUS.failed, _("failed"))]

    email = models.ForeignKey(Email, editable=False, related_name='logs')
    date = models.DateTimeField(auto_now_add=True)
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES)
    exception_type = models.CharField(max_length=255, blank=True)
    message = models.TextField()

    class Meta:
        app_label = 'post_office'

    def __unicode__(self):
        return text_type(self.date)


class EmailTemplate(models.Model):
    """
    Model to hold template information from db
    """
    name = models.CharField(max_length=255, help_text=_("e.g: 'welcome_email'"))
    description = models.TextField(blank=True,
        help_text=_("Description of this template."))
    created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    subject = models.CharField(max_length=255, blank=True,
        verbose_name=_("Subject"), validators=[validate_template_syntax])
    content = models.TextField(blank=True,
        verbose_name=_("Content"), validators=[validate_template_syntax])
    html_content = models.TextField(blank=True,
        verbose_name=_("HTML content"), validators=[validate_template_syntax])
    language = models.CharField(max_length=12, choices=settings.LANGUAGES,
        help_text=_("Render template in alternative language"),
        default='', blank=True)
    default_template = models.ForeignKey('self', related_name='translated_templates',
        null=True, default=None)

    class Meta:
        app_label = 'post_office'
        unique_together = ('language', 'default_template')
        verbose_name = _("Email Template")
        verbose_name_plural = _("Email Templates")

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        # If template is a translation, use default template's name
        if self.default_template and not self.name:
            self.name = self.default_template.name

        template = super(EmailTemplate, self).save(*args, **kwargs)
        cache.delete(self.name)
        return template


def get_upload_path(instance, filename):
    """Overriding to store the original filename"""
    if not instance.name:
        instance.name = filename  # set original filename

    filename = '{name}.{ext}'.format(name=uuid4().hex,
                                     ext=filename.split('.')[-1])

    return 'post_office_attachments/' + filename


class Attachment(models.Model):
    """
    A model describing an email attachment.
    """
    file = models.FileField(upload_to=get_upload_path)
    name = models.CharField(max_length=255, help_text=_("The original filename"))
    emails = models.ManyToManyField(Email, related_name='attachments')

    class Meta:
        app_label = 'post_office'
