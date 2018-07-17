from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import connection as db_connection
from django.db.models import Q
from django.template import Context, Template
from django.utils.timezone import now

from .connections import connections
from .models import Email, EmailTemplate, Log, PRIORITY, STATUS
from .settings import (get_available_backends, get_batch_size,
                       get_log_level, get_sending_order, get_threads_per_process)
from .utils import (get_email_template, parse_emails, parse_priority,
                    split_emails, create_attachments)
from .logutils import setup_loghandlers


logger = setup_loghandlers("INFO")


def create(sender, recipients=None, cc=None, bcc=None, subject='', message='',
           html_message='', context=None, scheduled_time=None, headers=None,
           template=None, priority=None, render_on_delivery=False, commit=True,
           backend=''):
    """
    Creates an email from supplied keyword arguments. If template is
    specified, email subject and content will be rendered during delivery.
    """
    priority = parse_priority(priority)
    status = None if priority == PRIORITY.now else STATUS.queued

    if recipients is None:
        recipients = []
    if cc is None:
        cc = []
    if bcc is None:
        bcc = []
    if context is None:
        context = ''

    # If email is to be rendered during delivery, save all necessary
    # information
    if render_on_delivery:
        email = Email(
            from_email=sender,
            to=recipients,
            cc=cc,
            bcc=bcc,
            scheduled_time=scheduled_time,
            headers=headers, priority=priority, status=status,
            context=context, template=template, backend_alias=backend
        )

    else:

        if template:
            subject = template.subject
            message = template.content
            html_message = template.html_content

        _context = Context(context or {})
        subject = Template(subject).render(_context)
        message = Template(message).render(_context)
        html_message = Template(html_message).render(_context)

        email = Email(
            from_email=sender,
            to=recipients,
            cc=cc,
            bcc=bcc,
            subject=subject,
            message=message,
            html_message=html_message,
            scheduled_time=scheduled_time,
            headers=headers, priority=priority, status=status,
            backend_alias=backend
        )

    if commit:
        email.save()

    return email


def send(recipients=None, sender=None, template=None, context=None, subject='',
         message='', html_message='', scheduled_time=None, headers=None,
         priority=None, attachments=None, render_on_delivery=False,
         log_level=None, commit=True, cc=None, bcc=None, language='',
         backend=''):

    try:
        recipients = parse_emails(recipients)
    except ValidationError as e:
        raise ValidationError('recipients: %s' % e.message)

    try:
        cc = parse_emails(cc)
    except ValidationError as e:
        raise ValidationError('c: %s' % e.message)

    try:
        bcc = parse_emails(bcc)
    except ValidationError as e:
        raise ValidationError('bcc: %s' % e.message)

    if sender is None:
        sender = settings.DEFAULT_FROM_EMAIL

    priority = parse_priority(priority)

    if log_level is None:
        log_level = get_log_level()

    if not commit:
        if priority == PRIORITY.now:
            raise ValueError("send_many() can't be used with priority = 'now'")
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
            # If language is specified, ensure template uses the right language
            if language:
                if template.language != language:
                    template = template.translated_templates.get(language=language)
        else:
            template = get_email_template(template, language)

    if backend and backend not in get_available_backends().keys():
        raise ValueError('%s is not a valid backend alias' % backend)

    email = create(sender, recipients, cc, bcc, subject, message, html_message,
                   context, scheduled_time, headers, template, priority,
                   render_on_delivery, commit=commit, backend=backend)

    if attachments:
        attachments = create_attachments(attachments)
        email.attachments.add(*attachments)

    if priority == PRIORITY.now:
        email.dispatch(log_level=log_level)

    return email


def send_many(kwargs_list):
    """
    Similar to mail.send(), but this function accepts a list of kwargs.
    Internally, it uses Django's bulk_create command for efficiency reasons.
    Currently send_many() can't be used to send emails with priority = 'now'.
    """
    emails = []
    for kwargs in kwargs_list:
        emails.append(send(commit=False, **kwargs))
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
        .order_by(*get_sending_order()).prefetch_related('attachments')[:get_batch_size()]


def send_queued(processes=1, log_level=None):
    """
    Sends out all queued mails that has scheduled_time less than now or None
    """
    queued_emails = get_queued()
    total_sent, total_failed = 0, 0
    total_email = len(queued_emails)

    logger.info('Started sending %s emails with %s processes.' %
                (total_email, processes))

    if log_level is None:
        log_level = get_log_level()

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
            pool.terminate()

            total_sent = sum([result[0] for result in results])
            total_failed = sum([result[1] for result in results])
    message = '%s emails attempted, %s sent, %s failed' % (
        total_email,
        total_sent,
        total_failed
    )
    logger.info(message)
    return (total_sent, total_failed)


def _send_bulk(emails, uses_multiprocessing=True, log_level=None):
    # Multiprocessing does not play well with database connection
    # Fix: Close connections on forking process
    # https://groups.google.com/forum/#!topic/django-users/eCAIY9DAfG0
    if uses_multiprocessing:
        db_connection.close()

    if log_level is None:
        log_level = get_log_level()

    sent_emails = []
    failed_emails = []  # This is a list of two tuples (email, exception)
    email_count = len(emails)

    logger.info('Process started, sending %s emails' % email_count)

    def send(email):
        try:
            email.dispatch(log_level=log_level, commit=False,
                           disconnect_after_delivery=False)
            sent_emails.append(email)
            logger.debug('Successfully sent email #%d' % email.id)
        except Exception as e:
            logger.debug('Failed to send email #%d' % email.id)
            failed_emails.append((email, e))

    # Prepare emails before we send these to threads for sending
    # So we don't need to access the DB from within threads
    for email in emails:
        # Sometimes this can fail, for example when trying to render
        # email from a faulty Django template
        try:
            email.prepare_email_message()
        except Exception as e:
            failed_emails.append((email, e))

    number_of_threads = min(get_threads_per_process(), email_count)
    pool = ThreadPool(number_of_threads)

    pool.map(send, emails)
    pool.close()
    pool.join()

    connections.close()

    # Update statuses of sent and failed emails
    email_ids = [email.id for email in sent_emails]
    Email.objects.filter(id__in=email_ids).update(status=STATUS.sent)

    email_ids = [email.id for (email, e) in failed_emails]
    Email.objects.filter(id__in=email_ids).update(status=STATUS.failed)

    # If log level is 0, log nothing, 1 logs only sending failures
    # and 2 means log both successes and failures
    if log_level >= 1:

        logs = []
        for (email, exception) in failed_emails:
            logs.append(
                Log(email=email, status=STATUS.failed,
                    message=str(exception),
                    exception_type=type(exception).__name__)
            )

        if logs:
            for eachlog in logs:
                eachlog.save()

    if log_level == 2:

        logs = []
        for email in sent_emails:
            logs.append(Log(email=email, status=STATUS.sent))

        if logs:
            for eachlog in logs:
                eachlog.save()

    logger.info(
        'Process finished, %s attempted, %s sent, %s failed' % (
            email_count, len(sent_emails), len(failed_emails)
        )
    )

    return len(sent_emails), len(failed_emails)
