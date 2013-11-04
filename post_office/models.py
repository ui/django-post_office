import sys
import warnings

from collections import namedtuple

from django.core.mail import EmailMultiAlternatives, get_connection
from django.db import models

try:
    from django.utils.encoding import smart_text # For Django >= 1.5
except ImportError:
    from django.utils.encoding import smart_unicode as smart_text

from django.template import Context, Template

from jsonfield import JSONField
from post_office import cache
from .settings import get_email_backend
from .validators import validate_email_with_name, validate_template_syntax


PRIORITY = namedtuple('PRIORITY', 'low medium high now')._make(range(4))
STATUS = namedtuple('STATUS', 'sent failed queued')._make(range(3))


# TODO: This will be deprecated, replaced by mail.from_template
class EmailManager(models.Manager):
    def from_template(self, from_email, to_email, template,
                      context={}, priority=PRIORITY.medium):
        warnings.warn(
            "`Email.objects.from_template()` is deprecated and will be removed "
            "in a future relase. Use `post_office.mail.from_template` instead.",
            DeprecationWarning)

        status = None if priority == PRIORITY.now else STATUS.queued
        context = Context(context)
        template_content = Template(template.content)
        template_content_html = Template(template.html_content)
        template_subject = Template(template.subject)
        return Email.objects.create(
            from_email=from_email, to=to_email,
            subject=template_subject.render(context),
            message=template_content.render(context),
            html_message=template_content_html.render(context),
            priority=priority, status=status
        )


class Email(models.Model):
    """
    A model to hold email information.
    """

    PRIORITY_CHOICES = [(PRIORITY.low, 'low'), (PRIORITY.medium, 'medium'),
                        (PRIORITY.high, 'high'), (PRIORITY.now, 'now')]
    STATUS_CHOICES = [(STATUS.sent, 'sent'), (STATUS.failed, 'failed'), (STATUS.queued, 'queued')]

    from_email = models.CharField(max_length=254, validators=[validate_email_with_name])
    to = models.EmailField(max_length=254)
    subject = models.CharField(max_length=255, blank=True)
    message = models.TextField(blank=True)
    html_message = models.TextField(blank=True)
    """
    Emails having 'queued' status will get processed by ``send_all`` command.
    This status field will then be set to ``failed`` or ``sent`` depending on
    whether it's successfully delivered.
    """
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES, db_index=True,
                                              blank=True, null=True)
    priority = models.PositiveSmallIntegerField(choices=PRIORITY_CHOICES, blank=True,
                                                null=True, db_index=True)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    last_updated = models.DateTimeField(db_index=True, auto_now=True)
    scheduled_time = models.DateTimeField(blank=True, null=True, db_index=True)
    objects = EmailManager()
    headers = JSONField(blank=True, null=True)

    class Meta:
        ordering = ('-created',)

    def __unicode__(self):
        return self.to

    def email_message(self, connection=None):
        """
        Returns a django ``EmailMessage`` or ``EmailMultiAlternatives`` object
        from a ``Message`` instance, depending on whether html_message is empty.
        """
        subject = smart_text(self.subject)
        msg = EmailMultiAlternatives(subject, self.message, self.from_email,
                                     [self.to], connection=connection,
                                     headers=self.headers)
        if self.html_message:
            msg.attach_alternative(self.html_message, "text/html")

        for attachment in self.attachments.all():
            msg.attach(attachment.name, attachment.file.read())

        return msg

    def dispatch(self, connection=None):
        """
        Actually send out the email and log the result
        """
        connection_opened = False
        try:
            if connection is None:
                connection = get_connection(get_email_backend())
                connection.open()
                connection_opened = True

            self.email_message(connection=connection).send()
            status = STATUS.sent
            message = 'Sent'

            if connection_opened:
                connection.close()

        except Exception as err:
            status = STATUS.failed
            message = sys.exc_info()[1]

        self.status = status
        self.save()
        self.logs.create(status=status, message=message)
        return status

    def save(self, *args, **kwargs):
        self.full_clean()
        return super(Email, self).save(*args, **kwargs)


class Log(models.Model):
    """
    A model to record sending email sending activities.
    """

    STATUS_CHOICES = [(STATUS.sent, 'sent'), (STATUS.failed, 'failed')]

    email = models.ForeignKey(Email, editable=False, related_name='logs')
    date = models.DateTimeField(auto_now_add=True, db_index=True)
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES, db_index=True)
    message = models.TextField()

    class Meta:
        ordering = ('-date',)

    def __unicode__(self):
        return str(self.date)


class EmailTemplate(models.Model):
    """
    Model to hold template information from db
    """
    name = models.CharField(max_length=255, help_text=("Example: 'emails/customers/id/welcome.html'"))
    subject = models.CharField(max_length=255, blank=True,
                               validators=[validate_template_syntax])
    content = models.TextField(blank=True,
                               validators=[validate_template_syntax])
    html_content = models.TextField(blank=True,
                                    validators=[validate_template_syntax])
    created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return str(self.name)

    def save(self, *args, **kwargs):
        template = super(EmailTemplate, self).save(*args, **kwargs)
        cache.delete(self.name)
        return template


class Attachment(models.Model):
    """
    A model describing an email attachment.
    """
    def get_upload_path(self, filename):
        """Overriding to store the original filename"""
        if not self.name:
            self.name = filename  # set original filename

        return 'post_office_attachments/' + filename

    email = models.ForeignKey(Email, related_name='attachments')
    file = models.FileField(upload_to=get_upload_path)
    name = models.CharField(max_length=255, help_text='The original filename')
