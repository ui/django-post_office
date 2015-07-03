from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.mail import get_connection
from django.core.validators import validate_email
from django.db.models import Q

try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text

from post_office import cache
from .compat import string_types
from .models import Email, PRIORITY, STATUS, EmailTemplate, Attachment
from .settings import get_default_priority, get_email_backend

try:
    from django.utils import timezone
    now = timezone.now
except ImportError:
    import datetime
    now = datetime.datetime.now


def send_mail(subject, message, from_email, recipient_list, html_message='',
              scheduled_time=None, headers=None, priority=PRIORITY.medium):
    """
    Add a new message to the mail queue. This is a replacement for Django's
    ``send_mail`` core email method.
    """

    subject = force_text(subject)
    status = None if priority == PRIORITY.now else STATUS.queued
    emails = []
    for address in recipient_list:
        emails.append(
            Email.objects.create(
                from_email=from_email, to=address, subject=subject,
                message=message, html_message=html_message, status=status,
                headers=headers, priority=priority, scheduled_time=scheduled_time
            )
        )
    if priority == PRIORITY.now:
        for email in emails:
            email.dispatch()
    return emails


def send_queued_mail():
    """
    Sends out all queued mails that has scheduled_time less than now or None
    """
    sent_count = 0
    failed_count = 0
    queued_emails = Email.objects.filter(status=STATUS.queued) \
        .filter(Q(scheduled_time__lte=now()) | Q(scheduled_time=None)) \
        .order_by('-priority')

    if queued_emails:

        # Try to open a connection, if we can't just pass in None as connection
        try:
            connection = get_connection(get_email_backend())
            connection.open()
        except Exception:
            connection = None

        for mail in queued_emails:
            status = mail.dispatch(connection)
            if status == STATUS.sent:
                sent_count += 1
            else:
                failed_count += 1
        if connection:
            connection.close()
    print('%s emails attempted, %s sent, %s failed' % (
        len(queued_emails), sent_count, failed_count)
    )


def get_email_template(name, language=''):
    """
    Function that returns an email template instance, from cache or DB.
    """
    if hasattr(settings, 'POST_OFFICE_CACHE') and settings.POST_OFFICE_TEMPLATE_CACHE is False:
        return EmailTemplate.objects.get(name=name, language=language)
    else:
        composite_name = '%s:%s' % (name, language)
        email_template = cache.get(composite_name)
        if email_template is not None:
            return email_template
        else:
            email_template = EmailTemplate.objects.get(name=name,
                                                       language=language)
            cache.set(composite_name, email_template)
            return email_template


def split_emails(emails, split_count=1):
    # Group emails into X sublists
    # taken from http://www.garyrobinson.net/2008/04/splitting-a-pyt.html
    # Strange bug, only return 100 email if we do not evaluate the list
    if list(emails):
        return [emails[i::split_count] for i in range(split_count)]


def create_attachments(attachment_files):
    """
    Create Attachment instances from files

    attachment_files is a dict of:
        * Key - the filename to be used for the attachment.
        * Value - file-like object, or a filename to open.

    Returns a list of Attachment objects
    """
    attachments = []
    for filename, content in attachment_files.items():
        opened_file = None

        if isinstance(content, string_types):
            # `content` is a filename - try to open the file
            opened_file = open(content, 'rb')
            content = File(opened_file)

        attachment = Attachment()
        attachment.file.save(filename, content=content, save=True)

        attachments.append(attachment)

        if opened_file is not None:
            opened_file.close()

    return attachments


def parse_priority(priority):
    if priority is None:
        priority = get_default_priority()
    # If priority is given as a string, returns the enum representation
    if isinstance(priority, string_types):
        priority = getattr(PRIORITY, priority, None)

        if priority is None:
            raise ValueError('Invalid priority, must be one of: %s' %
                             ', '.join(PRIORITY._fields))
    return priority


def parse_emails(emails):
    """
    A function that returns a list of valid email addresses.
    This function will also convert a single email address into
    a list of email addresses.
    None value is also converted into an empty list.
    """

    if isinstance(emails, string_types):
        emails = [emails]
    elif emails is None:
        emails = []

    for email in emails:
        try:
            validate_email(email)
        except ValidationError:
            raise ValidationError('%s is not a valid email address' % email)

    return emails
