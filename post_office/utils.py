from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files import File
from django.utils.encoding import force_text

from post_office import cache
from .models import Email, PRIORITY, STATUS, EmailTemplate, Attachment
from .settings import get_default_priority
from .validators import validate_email_with_name


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


def get_email_template(name, language=''):
    """
    Function that returns an email template instance, from cache or DB.
    """
    use_cache = getattr(settings, 'POST_OFFICE_CACHE', True)
    if use_cache:
        use_cache = getattr(settings, 'POST_OFFICE_TEMPLATE_CACHE', True)
    if not use_cache:
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
        * Value - file-like object, or a filename to open OR a dict of {'file': file-like-object, 'mimetype': string}

    Returns a list of Attachment objects
    """
    attachments = []
    for filename, filedata in attachment_files.items():

        if isinstance(filedata, dict):
            content = filedata.get('file', None)
            mimetype = filedata.get('mimetype', None)
            headers = filedata.get('headers', None)
        else:
            content = filedata
            mimetype = None
            headers = None

        opened_file = None

        if isinstance(content, str):
            # `content` is a filename - try to open the file
            opened_file = open(content, 'rb')
            content = File(opened_file)

        attachment = Attachment()
        if mimetype:
            attachment.mimetype = mimetype
        attachment.headers = headers
        attachment.file.save(filename, content=content, save=True)

        attachments.append(attachment)

        if opened_file is not None:
            opened_file.close()

    return attachments


def parse_priority(priority):
    if priority is None:
        priority = get_default_priority()
    # If priority is given as a string, returns the enum representation
    if isinstance(priority, str):
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

    if isinstance(emails, str):
        emails = [emails]
    elif emails is None:
        emails = []

    for email in emails:
        try:
            validate_email_with_name(email)
        except ValidationError:
            raise ValidationError('%s is not a valid email address' % email)

    return emails
