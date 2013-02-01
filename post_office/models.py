from collections import namedtuple

from django.core.mail import EmailMultiAlternatives, get_connection
from django.db import models
from django.utils.encoding import smart_unicode

from .cache import delete_cache
from .settings import get_email_backend
from .validators import validate_email_with_name

try:
    from django.utils.timezone import now
    now = now()
except ImportError:
    from datetime import datetime
    now = datetime.now


PRIORITY = namedtuple('PRIORITY', 'low medium high now')._make(range(4))
STATUS = namedtuple('STATUS', 'sent failed queued')._make(range(3))


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
    created = models.DateTimeField(default=now, db_index=True)
    last_updated = models.DateTimeField(db_index=True, auto_now=True)

    class Meta:
        ordering = ('-created',)

    def __unicode__(self):
        return self.to

    def email_message(self, connection=None):
        """
        Returns a django ``EmailMessage`` or ``EmailMultiAlternatives`` object
        from a ``Message`` instance, depending on whether html_message is empty.
        """
        subject = smart_unicode(self.subject)
        msg = EmailMultiAlternatives(subject, self.message, self.from_email,
                                     [self.to], connection=connection)
        if self.html_message:
            msg.attach_alternative(self.html_message, "text/html")
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

        except Exception, err:
            status = STATUS.failed
            message = unicode(err)

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
    date = models.DateTimeField(default=now, db_index=True)
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
    content = models.TextField()
    created = models.DateTimeField(default=now)
    last_updated = models.DateTimeField(default=now)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return str(self.name)

    def save(self, *args, **kwargs):
        delete_cache(self.name)
        self.last_updated = now
        return super(EmailTemplate, self).save(*args, **kwargs)
