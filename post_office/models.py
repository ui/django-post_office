import os
import random
import re
import string
import sys
import warnings
from uuid import uuid4

from collections import namedtuple

from django.conf import settings
from django.core.mail import EmailMessage, EmailMultiAlternatives, get_connection
from django.db import models

from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    from django.utils.encoding import smart_text # For Django >= 1.5
except ImportError:
    from django.utils.encoding import smart_unicode as smart_text

from django.template import Context, Template

from jsonfield import JSONField
from post_office import cache
from .compat import text_type
from .settings import get_email_backend, context_field_class
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
    priority = models.PositiveSmallIntegerField(choices=PRIORITY_CHOICES,
                                                blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    last_updated = models.DateTimeField(db_index=True, auto_now=True)
    scheduled_time = models.DateTimeField(blank=True, null=True, db_index=True)
    headers = JSONField(blank=True, null=True)
    template = models.ForeignKey('post_office.EmailTemplate', blank=True, null=True)
    context = context_field_class(blank=True)

    objects = EmailManager()

    def __unicode__(self):
        return self.to

    def email_message(self, connection=None):
        """
        Returns a django ``EmailMessage`` or ``EmailMultiAlternatives`` object
        from a ``Message`` instance, depending on whether html_message is empty.

        settings.POST_OFFICE_INLINE_IMAGES: Images located in static folder which
        are used in the email will be attached as inline image. But only if this
        settings set to True.
        """
        subject = smart_text(self.subject)

        if self.template is not None:
            _context = Context(self.context)
            subject = Template(self.template.subject).render(_context)
            message = Template(self.template.content).render(_context)
            html_message = Template(self.template.html_content).render(_context)
            # render email template in base template if base template set
            if self.template.base_template is not None:
                _context = Context({
                    'inner_content': html_message
                })
                html_message = Template(self.template.base_template.html_content) \
                        .render(_context)

        else:
            subject = self.subject
            message = self.message
            html_message = self.html_message
        
        if html_message:
            msg = EmailMultiAlternatives(subject, message, self.from_email,
                                         [self.to], connection=connection,
                                         headers=self.headers)

            if getattr(settings, 'POST_OFFICE_INLINE_IMAGES', False):
                image_pattern = """<img\s*.*src=['"](?P<img_src>%s[^'"]*)['"].*\/>""" \
                    % settings.STATIC_URL
                image_matches = re.findall(image_pattern, html_message)
                added_images = {}
                attach_images = []
                chars = string.ascii_uppercase + string.digits
                for image_match in image_matches:
                    if image_match not in added_images:
                        img_content_cid = ''.join(random.choice(chars) for x in range(6))
                        on_disk_path = os.path.join(settings.STATIC_ROOT,
                            image_match.replace(settings.STATIC_URL, ''))
                        img_data = open(on_disk_path, 'rb').read()
                        img = MIMEImage(img_data)
                        img.add_header('Content-ID', '<%s>' % img_content_cid)
                        # split image path and keep filename
                        img.add_header(u'Content-Disposition',
                            'inline; filename="%s"' % image_match.split('/')[-1])
                        attach_images.append(img)
                        added_images[image_match] = img_content_cid

                        html_message = string.replace(html_message,
                            image_match, 'cid:%s' % img_content_cid)

                related = MIMEMultipart('related')
                html_part = MIMEText(html_message.encode('utf-8'), 'html', 'utf-8')
                related.attach(html_part)
                for image in attach_images:
                    related.attach(image)

                msg.attach(related)
                msg.mixed_subtype = 'alternative'
                msg.content_subtype = 'html'
            else:
                msg.attach_alternative(html_message, "text/html")
        else:
            msg = EmailMessage(subject, message, self.from_email,
                               [self.to], connection=connection,
                               headers=self.headers)

        for attachment in self.attachments.all():
            msg.attach(attachment.name, attachment.file.read())

        return msg

    def dispatch(self, connection=None, log_level=2):
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

        # If log level is 0, log nothing, 1 logs only sending failures
        # and 2 means log both successes and failures
        if log_level == 1:
            if status == STATUS.failed:
                self.logs.create(status=status, message=message)
        elif log_level == 2:
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
    date = models.DateTimeField(auto_now_add=True)
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES)
    message = models.TextField()

    class Meta:
        ordering = ('-date',)

    def __unicode__(self):
        return text_type(self.date)


class EmailTemplate(models.Model):
    """
    Model to hold template information from db
    """
    name = models.CharField(max_length=255, help_text=("Example: 'emails/customers/id/welcome.html'"))
    description = models.TextField(blank=True,
                                   help_text='Description of this email template.')
    subject = models.CharField(max_length=255, blank=True,
                               validators=[validate_template_syntax])
    content = models.TextField(blank=True,
                               validators=[validate_template_syntax])
    html_content = models.TextField(blank=True,
                                    validators=[validate_template_syntax])
    created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    base_template = models.ForeignKey('post_office.BaseEmailTemplate',
                                      blank=True, null=True)

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        template = super(EmailTemplate, self).save(*args, **kwargs)
        cache.delete(self.name)
        return template


class BaseEmailTemplate(models.Model):
    """
    A model to add base `skeleton` template for email templates. When sending emails in
    different languages or for different purposes you can add a base template which
    is the same for all emails. This means less content in EmailTemplate. The
    child template (EmailTemplate) will be rendered in template
    variable {{ inner_content }}.
    """
    name = models.CharField(max_length=255)
    html_content = models.TextField(validators=[validate_template_syntax],
                                    help_text=("EmailTemplate will be rendered in template variable {{ inner_content }}"))

    def __unicode__(self):
        return unicode(self.name)


class Attachment(models.Model):
    """
    A model describing an email attachment.
    """
    def get_upload_path(self, filename):
        """Overriding to store the original filename"""
        if not self.name:
            self.name = filename  # set original filename

        filename = '{name}.{ext}'.format(name=uuid4().hex, ext=filename.split('.')[-1])

        return 'post_office_attachments/' + filename

    file = models.FileField(upload_to=get_upload_path)
    name = models.CharField(max_length=255, help_text='The original filename')
    emails = models.ManyToManyField(Email, related_name='attachments')
