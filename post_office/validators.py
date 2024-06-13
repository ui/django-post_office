from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.template import Template, TemplateSyntaxError, TemplateDoesNotExist
from django.utils.encoding import force_str


def validate_email_with_name(value, validate_tld=False):
    """
    Validate email address.

    Both "Recipient Name <email@example.com>" and "email@example.com" are valid.
    """
    value = force_str(value)

    recipient = value
    if '<' in value and '>' in value:
        start = value.find('<') + 1
        end = value.find('>')
        if start < end:
            recipient = value[start:end]

    if validate_tld:
        from .tlds import TLD
        tld = recipient.rsplit('.', 1)[-1].upper()
        if tld not in TLD:
            raise ValidationError('Invalid top level domain.')

    validate_email(recipient)


def validate_comma_separated_emails(value, validate_tld=False):
    """
    Validate every email address in a comma separated list of emails.
    """
    if not isinstance(value, (tuple, list)):
        raise ValidationError('Email list must be a list/tuple.')

    for email in value:
        try:
            validate_email_with_name(email, validate_tld)
        except ValidationError:
            raise ValidationError('Invalid email: %s' % email, code='invalid')


def validate_template_syntax(source):
    """
    Basic Django Template syntax validation. This allows for robuster template
    authoring.
    """
    try:
        Template(source)
    except (TemplateSyntaxError, TemplateDoesNotExist) as err:
        raise ValidationError(str(err))
