from django.db.models import TextField
from django.utils.translation import ugettext_lazy as _

from .validators import validate_comma_separated_email_list


class CommaSeparatedEmailField(TextField):
    default_validators = [validate_comma_separated_email_list]
    description = _("Comma-separated emails")

    def formfield(self, **kwargs):
        defaults = {
            'error_messages': {
                'invalid': _('Enter only email addresses separated by commas.'),
            }
        }
        defaults.update(kwargs)
        return super(CommaSeparatedEmailField, self).formfield(**defaults)
