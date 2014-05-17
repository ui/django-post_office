import sys

from multiprocessing import Pool

from django.conf import settings
from django.core.mail import get_connection
from django.db import connection as db_connection
from django.db.models import Q
from django.template import Context, Template

from .compat import string_types
from .models import Email, EmailTemplate, PRIORITY, STATUS
from .settings import get_batch_size, get_email_backend, get_default_priority
from .utils import get_email_template, split_emails, create_attachments
from .logutils import setup_loghandlers

try:
    from django.utils import timezone
    now = timezone.now
except ImportError:
    import datetime
    now = datetime.datetime.now


logger = setup_loghandlers("INFO")


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


def create(sender, to=[], cc=[], bcc=[], subject='', message='', html_message='',
           context=None, scheduled_time=None, headers=None, template=None,
           priority=None, render_on_delivery=False, commit=True):
    """
    Creates an email from supplied keyword arguments. If template is
    specified, email subject and content will be rendered during delivery.
    """
    priority = parse_priority(priority)
    status = None if priority == PRIORITY.now else STATUS.queued

    if context is None:
        context = ''

    # If email is to be rendered during delivery, save all necessary
    # information
    if render_on_delivery:
        email = Email(
            from_email=sender,
            to=_recipients_list_to_str(to),
            cc=_recipients_list_to_str(cc),
            bcc=_recipients_list_to_str(bcc),
            scheduled_time=scheduled_time,
            headers=headers, priority=priority, status=status,
            context=context, template=template
        )

    else:

        if template:
            subject = template.subject
            message = template.content
            html_message = template.html_content

        if context:
            _context = Context(context)
            subject = Template(subject).render(_context)
            message = Template(message).render(_context)
            html_message = Template(html_message).render(_context)

        email = Email(
            from_email=sender,
            to=_recipients_list_to_str(to),
            cc=_recipients_list_to_str(cc),
            bcc=_recipients_list_to_str(bcc),
            subject=subject,
            message=message,
            html_message=html_message,
            scheduled_time=scheduled_time,
            headers=headers, priority=priority, status=status,
        )

    if commit:
        email.save()

    return email


def _recipients_list_to_str(l):
    # ['  rcpt1@example.com  ', 'rcpt2@example.com'] => 'rcpt1@example.com, rcpt2@example.com'
    return ', '.join(map(lambda s: s.strip(), l))


def send(to=[], sender=None, template=None, context={}, subject='',
         message='', html_message='', scheduled_time=None, headers=None,
         priority=None, attachments=None, render_on_delivery=False,
         log_level=2, commit=True, cc=[], bcc=[]):

    if (not isinstance(to, (tuple, list)) or not isinstance(cc, (tuple, list)) or
            not isinstance(bcc, (tuple, list))):
        raise ValueError('Recipient emails must be in list/tuple format')

    if sender is None:
        sender = settings.DEFAULT_FROM_EMAIL

    priority = parse_priority(priority)
    if not commit:
        if priority == PRIORITY.now:
            raise ValueError("send_many() can't be used to send emails with priority = 'now'")
        if attachments:
            raise ValueError("Can't add attachments with send_many()")

    if template:
        if subject:
            raise ValueError('You can\'t specify both "template" and "subject" arguments')
        if message:
            raise ValueError('You can\'t specify both "template" and "message" arguments')
        if html_message:
            raise ValueError('You can\'t specify both "template" and "html_message" arguments')

        # template can be an EmailTemplate instance or name
        if isinstance(template, EmailTemplate):
            template = template
        else:
            template = get_email_template(template)

    emails = [create(sender, to, cc, bcc, subject, message, html_message,
                     context, scheduled_time, headers, template, priority,
                     render_on_delivery, commit=commit)]

    if attachments:
        attachments = create_attachments(attachments)
        for email in emails:
            email.attachments.add(*attachments)

    if priority == PRIORITY.now:
        for email in emails:
            email.dispatch(log_level=log_level)

    return emails


def send_many(kwargs_list):
    """
    Similar to mail.send(), but this function accepts a list of kwargs.
    Internally, it uses Django's bulk_create command for efficiency reasons.
    Currently send_many() can't be used to send emails with priority = 'now'.
    """
    emails = []
    for kwargs in kwargs_list:
        emails.extend(send(commit=False, **kwargs))
    Email.objects.bulk_create(emails)


def get_queued():
    """
    Returns a list of emails that should be sent:
     - Status is queued
     - Has scheduled_time lower than the current time or None
    """
    return Email.objects.filter(status=STATUS.queued) \
        .select_related('template') \
        .filter(Q(scheduled_time__lte=now()) | Q(scheduled_time=None)) \
        .order_by('-priority').prefetch_related('attachments')[:get_batch_size()]


def send_queued(processes=1, log_level=2):
    """
    Sends out all queued mails that has scheduled_time less than now or None
    """
    queued_emails = get_queued()
    total_sent, total_failed = 0, 0
    total_email = len(queued_emails)

    logger.info('Started sending %s emails with %s processes.' %
                (total_email, processes))

    if queued_emails:

        # Don't use more processes than number of emails
        if total_email < processes:
            processes = total_email

        if processes == 1:
            total_sent, total_failed = _send_bulk(queued_emails,
                                                  uses_multiprocessing=False,
                                                  log_level=log_level)
        else:
            email_lists = split_emails(queued_emails, processes)
            pool = Pool(processes)
            results = pool.map(_send_bulk, email_lists)
            total_sent = sum([result[0] for result in results])
            total_failed = sum([result[1] for result in results])
    message = '%s emails attempted, %s sent, %s failed' % (
        total_email,
        total_sent,
        total_failed
    )
    logger.info(message)
    return (total_sent, total_failed)


def _send_bulk(emails, uses_multiprocessing=True, log_level=2):
    # Multiprocessing does not play well with database connection
    # Fix: Close connections on forking process
    # https://groups.google.com/forum/#!topic/django-users/eCAIY9DAfG0
    if uses_multiprocessing:
        db_connection.close()
    sent_count, failed_count = 0, 0
    email_count = len(emails)
    logger.info('Process started, sending %s emails' % email_count)

    # Try to open a connection, if we can't just pass in None as connection
    try:
        connection = get_connection(get_email_backend())
        connection.open()
    except Exception:
        connection = None

    try:
        for email in emails:
            status = email.dispatch(connection, log_level)
            if status == STATUS.sent:
                sent_count += 1
                logger.debug('Successfully sent email #%d' % email.id)
            else:
                failed_count += 1
                logger.debug('Failed to send email #%d' % email.id)
    except Exception as e:
        logger.error(e, exc_info=sys.exc_info(), extra={'status_code': 500})

    if connection:
        connection.close()

    logger.info('Process finished, %s emails attempted, %s sent, %s failed' %
               (email_count, sent_count, failed_count))

    return (sent_count, failed_count)
