from django.conf import settings
from django.core.mail import get_connection
from django.utils.encoding import force_unicode

from post_office import cache
from .models import Email, PRIORITY, STATUS, EmailTemplate
from .settings import get_email_backend


def send_mail(subject, message, from_email, recipient_list, html_message='',
              priority=PRIORITY.medium, headers=''):
    """
    Add a new message to the mail queue.

    This is a replacement for Django's ``send_mail`` core email method.

    The `fail_silently``, ``auth_user`` and ``auth_password`` arguments are
    only provided to match the signature of the emulated function. These
    arguments are not used.
    """

    subject = force_unicode(subject)
    status = None if priority == PRIORITY.now else STATUS.queued
    emails = []
    for address in recipient_list:
        emails.append(
            Email.objects.create(
                from_email=from_email, to=address, subject=subject,
                message=message, html_message=html_message, status=status,
                priority=priority, headers=headers
            )
        )
    if priority == PRIORITY.now:
        for email in emails:
            email.dispatch()
    return emails


def send_queued_mail():
    """
    Sends out all queued mails
    """
    sent_count = 0
    failed_count = 0
    queued_emails = Email.objects.filter(status=STATUS.queued).order_by('-priority')

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
    print '{0} emails attempted, {1} sent, {2} failed'.format(len(queued_emails),
                                                              sent_count, failed_count)


def send_templated_mail(template_name, from_address, to_addresses, context={}, priority=PRIORITY.medium, headers=''):
    email_template = get_email_template(template_name)
    for address in to_addresses:
        email = Email.objects.from_template(from_address, address, email_template,
            context, priority, headers)
        if priority == PRIORITY.now:
            email.dispatch()


def get_email_template(name):
    """
    Function to get email template object that checks from cache first if caching is enabled
    """
    if hasattr(settings, 'POST_OFFICE_CACHE') and settings.POST_OFFICE_TEMPLATE_CACHE is False:
        return EmailTemplate.objects.get(name=name)
    else:
        email_template = cache.get(name)
        if email_template is not None:
            return email_template
        else:
            email_template = EmailTemplate.objects.get(name=name)
            cache.set(name, email_template)
            return email_template
