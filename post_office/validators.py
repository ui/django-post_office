import re

from django.core.exceptions import ValidationError


email_re = re.compile(r'\b[A-Z0-9._%-]+@[A-Z0-9.-]+\.[A-Z]{2,4}\b', re.IGNORECASE)


def validate_email_with_name(value):
    """
    In addition to validating valid email address, it also accepts email address
    in the format of "Recipient Name <email@example.com>"
    """
    # Try matching straight email address "alice@example.com"
    if email_re.match(value):
        return

    # Now try to match "Alice <alice@example.com>"
    if '<' and '>' in value:
        start = value.find('<') + 1
        end = value.find('>')
        if start < end:
            email = value[start:end]
            if email_re.match(email):
                return

    raise ValidationError('Enter a valid e-mail address.', code='invalid')
