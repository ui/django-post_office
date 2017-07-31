# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import namedtuple
from uuid import uuid4

from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.db import models
from django.template import Context, Template
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import pgettext_lazy
from django.utils.translation import ugettext_lazy as _
from jsonfield import JSONField

from post_office import cache
from post_office.fields import CommaSeparatedEmailField

from .compat import text_type, smart_text
from .connections import connections
from .settings import context_field_class, get_log_level
from .validators import validate_email_with_name, validate_template_syntax


PRIORITY = namedtuple('PRIORITY', 'low medium high now')._make(range(4))
STATUS = namedtuple('STATUS', 'sent failed queued')._make(range(3))


@python_2_unicode_compatible
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
    subject = models.CharField(_("Subject"), max_length=989, blank=True)
    message = models.TextField(_("Message"), blank=True)
    html_message = models.TextField(_("HTML Message"), blank=True)
    """
    Emails with 'queued' status will get processed by ``send_queued`` command.
    Status field will then be set to ``failed`` or ``sent`` depending on
    whether it's successfully delivered.
    """
    status = models.PositiveSmallIntegerField(
        _("Status"),
        choices=STATUS_CHOICES, db_index=True,
        blank=True, null=True)
    priority = models.PositiveSmallIntegerField(_("Priority"),
                                                choices=PRIORITY_CHOICES,
                                                blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    last_updated = models.DateTimeField(db_index=True, auto_now=True)
    scheduled_time = models.DateTimeField(_('The scheduled sending time'),
                                          blank=True, null=True, db_index=True)
    headers = JSONField(_('Headers'), blank=True, null=True)
    template = models.ForeignKey('post_office.EmailTemplate', blank=True,
                                 null=True, verbose_name=_('Email template'),
                                 on_delete=models.CASCADE)
    context = context_field_class(_('Context'), blank=True, null=True)
    backend_alias = models.CharField(_('Backend alias'), blank=True, default='',
                                     max_length=64)

    class Meta:
        app_label = 'post_office'
        verbose_name = pgettext_lazy("Email address", "Email")
        verbose_name_plural = pgettext_lazy("Email addresses", "Emails")

    def __init__(self, *args, **kwargs):
        super(Email, self).__init__(*args, **kwargs)
        self._cached_email_message = None

    def __str__(self):
        return u'%s' % self.to

    def email_message(self):
        """
        Returns Django EmailMessage object for sending.
        """
        if self._cached_email_message:
            return self._cached_email_message

        return self.prepare_email_message()

    def prepare_email_message(self):
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

        connection = connections[self.backend_alias or 'default']

        if html_message:
            msg = EmailMultiAlternatives(
                subject=subject, body=message, from_email=self.from_email,
                to=self.to, bcc=self.bcc, cc=self.cc,
                headers=self.headers, connection=connection)
            msg.attach_alternative(html_message, "text/html")
        else:
            msg = EmailMessage(
                subject=subject, body=message, from_email=self.from_email,
                to=self.to, bcc=self.bcc, cc=self.cc,
                headers=self.headers, connection=connection)

        for attachment in self.attachments.all():
            msg.attach(attachment.name, attachment.file.read(), mimetype=attachment.mimetype or None)
            attachment.file.close()

        self._cached_email_message = msg
        return msg

    def dispatch(self, log_level=None,
                 disconnect_after_delivery=True, commit=True):
        """
        Sends email and log the result.
        """
        try:
            self.email_message().send()
            status = STATUS.sent
            message = ''
            exception_type = ''
        except Exception as e:
            status = STATUS.failed
            message = str(e)
            exception_type = type(e).__name__

            # If run in a bulk sending mode, reraise and let the outer
            # layer handle the exception
            if not commit:
                raise

        if commit:
            self.status = status
            self.save(update_fields=['status'])

            if log_level is None:
                log_level = get_log_level()

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


@python_2_unicode_compatible
class Log(models.Model):
    """
    A model to record sending email sending activities.
    """

    STATUS_CHOICES = [(STATUS.sent, _("sent")), (STATUS.failed, _("failed"))]

    email = models.ForeignKey(Email, editable=False, related_name='logs',
                              verbose_name=_('Email address'), on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    status = models.PositiveSmallIntegerField(_('Status'), choices=STATUS_CHOICES)
    exception_type = models.CharField(_('Exception type'), max_length=255, blank=True)
    message = models.TextField(_('Message'))

    class Meta:
        app_label = 'post_office'
        verbose_name = _("Log")
        verbose_name_plural = _("Logs")

    def __str__(self):
        return text_type(self.date)


@python_2_unicode_compatible
class EmailTemplate(models.Model):
    """
    Model to hold template information from db
    """
    name = models.CharField(_('Name'), max_length=255, help_text=_("e.g: 'welcome_email'"))
    description = models.TextField(_('Description'), blank=True,
                                   help_text=_("Description of this template."))
    created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    subject = models.CharField(max_length=255, blank=True,
        verbose_name=_("Subject"), validators=[validate_template_syntax])
    content = models.TextField(blank=True,
        verbose_name=_("Content"), validators=[validate_template_syntax])
    html_content = models.TextField(blank=True,
        verbose_name=_("HTML content"), validators=[validate_template_syntax])
    language = models.CharField(max_length=12,
        verbose_name=_("Language"),
        help_text=_("Render template in alternative language"),
        default='', blank=True)
    default_template = models.ForeignKey('self', related_name='translated_templates',
        null=True, default=None, verbose_name=_('Default template'), on_delete=models.CASCADE)

    class Meta:
        app_label = 'post_office'
        unique_together = ('name', 'language', 'default_template')
        verbose_name = _("Email Template")
        verbose_name_plural = _("Email Templates")
        ordering = ['name']

    def __str__(self):
        return u'%s %s' % (self.name, self.language)

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


@python_2_unicode_compatible
class Attachment(models.Model):
    """
    A model describing an email attachment.
    """
    file = models.FileField(_('File'), upload_to=get_upload_path)
    name = models.CharField(_('Name'), max_length=255, help_text=_("The original filename"))
    emails = models.ManyToManyField(Email, related_name='attachments',
                                    verbose_name=_('Email addresses'))
    mimetype = models.CharField(max_length=255, default='', blank=True)

    class Meta:
        app_label = 'post_office'
        verbose_name = _("Attachment")
        verbose_name_plural = _("Attachments")

    def __str__(self):
        return self.name
