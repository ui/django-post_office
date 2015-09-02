from django.core.exceptions import ValidationError

from ..compat import string_types
from ..mail import create
from ..models import Email, EmailTemplate, PRIORITY
from ..settings import get_log_level
from ..utils import parse_email_template, parse_backend, parse_priority


def send(recipient, sender, template=None, context=None, message='',
         scheduled_time=None, priority=None, render_on_delivery=False,
         log_level=None, commit=True, language='', backend=''):

    priority = parse_priority(priority)

    validate_phonenumbers(recipient)
    validate_phonenumber(sender)

    if log_level is None:
        log_level = get_log_level()

    if not commit:
        if priority == PRIORITY.now:
            raise ValueError("send_many() can't be used with priority = 'now'")

    if template:
        if message:
            raise ValueError('You can\'t specify both "template" and "message" arguments')

        template = parse_email_template(template)

    parse_backend(backend)

    email = create(sender, recipient, message=message, context=context,
                   scheduled_time=scheduled_time, template=template,
                   priority=priority, render_on_delivery=render_on_delivery,
                   commit=commit, backend=backend)

    if priority == PRIORITY.now:
        email.dispatch(log_level=log_level)

    return email


def validate_phonenumber(phonenumber):
    phonenumber = phonenumber.lstrip('+')
    if not phonenumber.isdigit():
        raise ValidationError('%s is not a valid phone number' % phonenumber)
    return True


def validate_phonenumbers(phonenumbers):
    if isinstance(phonenumbers, string_types):
        phonenumbers = [phonenumbers]

    for phonenumber in phonenumbers:
        validate_phonenumber(phonenumber)

    return True
