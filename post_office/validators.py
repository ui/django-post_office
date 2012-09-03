from django.core.exceptions import ValidationError
from django.core.validators import validate_email


def validate_email_with_name(value):
    """
    In addition to validating valid email address, it also accepts email address
    in the format of "Recipient Name <email@example.com>"
    """
    try:
        validate_email(value)
    except ValidationError:
        if '<' and '>' in value:
            start = value.find('<') + 1
            end = value.find('>') - 1
            if start < end:
                email = value[start:end]
                validate_email(email)
                return
        raise
