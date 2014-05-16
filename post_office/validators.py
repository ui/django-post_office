from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.template import Template, TemplateSyntaxError
from django.utils.encoding import force_text

from .compat import text_type


def validate_email_with_name(value):
    """
    Validate email address.

    Both "Recipient Name <email@example.com>" and "email@example.com" are valid.
    """
    value = force_text(value)

    if '<' and '>' in value:
        start = value.find('<') + 1
        end = value.find('>')
        if start < end:
            recipient = value[start:end]
    else:
        recipient = value

    validate_email(recipient)


def validate_comma_separated_email_list(value):
    """
    Validate every email address in a comma separated list of emails.
    """
    value = force_text(value)

    emails = [email.strip() for email in value.split(',')]

    for email in emails:
        try:
            validate_email(email)
        except ValidationError:
            raise ValidationError('Invalid email: %s' % email, code='invalid')


def validate_template_syntax(source):
    """
    Basic Django Template syntax validation. This allows for robuster template
    authoring.
    """
    try:
        t = Template(source)
    except TemplateSyntaxError as err:
        raise ValidationError(text_type(err))
