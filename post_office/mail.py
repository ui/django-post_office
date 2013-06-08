from django.conf import settings
from django.template import Context, Template

from .models import Email, EmailTemplate, PRIORITY, STATUS
from .utils import get_email_template, send_mail


def from_template(sender, recipient, template, context={},
                  headers=None, priority=PRIORITY.medium):
    """Returns an Email instance from provided template and context."""
    # template can be an EmailTemplate instance of name
    if isinstance(template, EmailTemplate):
        template = template
    else:
        template = get_email_template(template)
    status = None if priority == PRIORITY.now else STATUS.queued
    context = Context(context)
    template_content = Template(template.content)
    template_content_html = Template(template.html_content)
    template_subject = Template(template.subject)
    return Email.objects.create(
        from_email=sender, to=recipient,
        subject=template_subject.render(context),
        message=template_content.render(context),
        html_message=template_content_html.render(context),
        headers=headers, priority=priority, status=status
    )


def send(recipients, sender=None, template=None, context={}, subject='',
         message='', html_message='', headers=None, priority=PRIORITY.medium):

    if not isinstance(recipients, (tuple, list)):
        raise ValueError('Recipient emails must be in list/tuple format')

    if sender is None:
        sender = settings.DEFAULT_FROM_EMAIL

    if template:
        if subject:
            raise ValueError('You can\'t specify both "template" and "subject" arguments')
        if message:
            raise ValueError('You can\'t specify both "template" and "message" arguments')
        if html_message:
            raise ValueError('You can\'t specify both "template" and "html_message" arguments')

        emails = [from_template(sender, recipient, template, context, headers, priority)
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
                           headers=headers, priority=priority)
    return emails
