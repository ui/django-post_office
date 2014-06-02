from django.db.models import TextField, SubfieldBase, Field
from django.utils import six
from django.utils.six import with_metaclass
from django.utils.translation import ugettext_lazy as _

from .validators import validate_comma_separated_email_list


class CommaSeparatedEmailField(with_metaclass(SubfieldBase, TextField)):
    default_validators = [validate_comma_separated_email_list]
    description = _("Comma-separated emails")

    def __init__(self, *args, **kwargs):
        kwargs['blank'] = True
        super(CommaSeparatedEmailField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {
            'error_messages': {
                'invalid': _('Enter only email addresses separated by commas.'),
            }
        }
        defaults.update(kwargs)
        return super(CommaSeparatedEmailField, self).formfield(**defaults)

    def get_prep_value(self, value):
        return ', '.join(map(lambda s: s.strip(), value))

    def to_python(self, value):
        if isinstance(value, six.string_types):
            if value == '':
                return []
            else:
                return [s.strip() for s in value.split(',')]
        else:
            return value
