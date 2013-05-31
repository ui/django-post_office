from django.conf import settings
from django.template import Context, Template
from django.utils import translation

from .models import Email, EmailTemplate, PRIORITY, STATUS
from .utils import get_email_template, send_mail


def from_template(sender, recipient, template, context={},
                  priority=PRIORITY.medium, language=None):
    """Returns an Email instance from provided template and context."""
    # template can be an EmailTemplate instance of name
    if isinstance(template, EmailTemplate):
        template = template
    else:
        template = get_email_template(template, language)
    status = None if priority == PRIORITY.now else STATUS.queued
    context = Context(context)
    template_content = Template(template.content)
    template_content_html = Template(template.html_content)
    template_subject = Template(template.subject)
    old_language = translation.get_language()
    if language:
        translation.activate(language)
    email = Email.objects.create(
        from_email=sender, to=recipient,
        subject=template_subject.render(context),
        message=template_content.render(context),
        html_message=template_content_html.render(context),
        priority=priority, status=status
    )
    if language:
        translation.activate(old_language)
    return email


def send(recipients, sender=None, template=None, context={}, subject='',
         message='', html_message='', priority=PRIORITY.medium, language=None):

    if not isinstance(recipients, (tuple, list)):
        raise ValueError('Recipient emails must be in list/tuple format')

    if sender is None:
        sender = settings.DEFAULT_FROM_EMAIL

    if language:
        if subject:
            raise ValueError('You can\'t specify both "language" and "subject" arguments')
        if message:
            raise ValueError('You can\'t specify both "language" and "message" arguments')
        if html_message:
            raise ValueError('You can\'t specify both "language" and "html_message" arguments')

    if template:
        if subject:
            raise ValueError('You can\'t specify both "template" and "subject" arguments')
        if message:
            raise ValueError('You can\'t specify both "template" and "message" arguments')
        if html_message:
            raise ValueError('You can\'t specify both "template" and "html_message" arguments')

        emails = [from_template(sender, recipient, template, context, priority,
                                language)
                  for recipient in recipients]
        if priority == PRIORITY.now:
            for email in emails:
                email.dispatch()
    else:
        if context:
            context = Context(context)
            subject = Template(subject).render(context)
            message = Template(message).render(context)
            html_message = Template(html_message).render(context)
        emails = send_mail(subject=subject, message=message, from_email=sender,
                           recipient_list=recipients, html_message=html_message,
                           priority=priority)
    return emails
