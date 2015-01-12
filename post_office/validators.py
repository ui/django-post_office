import re

from django.core.exceptions import ValidationError
from django.core.validators import validate_email as validate_plain_email, EmailValidator
from django.template import Template, TemplateSyntaxError
from django.utils.encoding import force_text

from .compat import text_type

class FullEmailValidator(EmailValidator):
    """ Simple validator that passes for email addresses bearing a display name
    i.e. John Smith <john.smith@acme.gov>

    Both "Recipient Name <email@example.com>" and "email@example.com" are valid.

    """
    def __call__(self, value):
        try:
            res = super(FullEmailValidator, self).__call__(value)
        except ValidationError:
            try:
                split_address = re.match(r'(.+) \<(.+@.+)\>', value)
                display_name, email = split_address.groups()
                super(FullEmailValidator, self).__call__(email)
            except AttributeError:
                raise ValidationError(self.message, code=self.code)

validate_email_with_name = FullEmailValidator(**dict(validate_plain_email.__dict__))


def validate_comma_separated_emails(value):
    """
    Validate every email address in a comma separated list of emails.
    """
    if not isinstance(value, (tuple, list)):
        raise ValidationError('Email list must be a list/tuple.')

    for email in value:
        try:
            validate_email_with_name(email)
        except ValidationError:
            raise ValidationError('Invalid email: %s' % email, code='invalid')


def validate_template_syntax(source):
    """
    Basic Django Template syntax validation. This allows for robuster template
    authoring.
    """
    try:
        Template(source)
    except TemplateSyntaxError as err:
        raise ValidationError(text_type(err))
