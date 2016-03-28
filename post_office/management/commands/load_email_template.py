import os

from django.core.management.base import BaseCommand

from ...models import EmailTemplate
from ...logutils import setup_loghandlers
from ... import settings

logger = setup_loghandlers()


def _get_template(template_name, filename):
    """Find the template and return the raw template file content"""

    path = settings.get_template_dir()

    with open(os.path.join(path, template_name, filename)) as f:
        content = f.read()

    return content


class Command(BaseCommand):
    help = 'Load an EmailTemplate from Django template files'
    args = 'template_name'

    def handle(self, template_name, *args, **options):
        subject = _get_template(template_name, 'subject.txt').strip()
        content = _get_template(template_name, 'content.txt')
        html_content = _get_template(template_name, 'content.html')

        fields = {
            'subject': subject,
            'content': content,
            'html_content': html_content,
        }
        template, created = EmailTemplate.objects.get_or_create(
            name=template_name, defaults=fields)

        if not created:  # update fields
            for k, v in fields.items():
                setattr(template, k, v)
            template.save()

        logger.info('Loaded template: %s', template_name)
