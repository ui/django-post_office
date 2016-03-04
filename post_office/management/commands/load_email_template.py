from django.core.management.base import BaseCommand
from django.template import loader

from ...models import EmailTemplate
from ...logutils import setup_loghandlers

logger = setup_loghandlers()


def _get_template(template_name):
    """Find the template and return the raw template file content"""

    template = loader.get_template(template_name)
    content = template.template.source
    content = content.strip()
    return content


class Command(BaseCommand):
    help = 'Load an EmailTemplate from Django template files'
    args = 'template_name'

    def handle(self, template_name, *args, **options):
        template_data = {
            'subject': _get_template(template_name + '/subject.txt'),
            'content': _get_template(template_name + '/content.txt'),
            'html_content': _get_template(template_name + '/content.html'),
        }

        EmailTemplate.objects.update_or_create(name=template_name,
                                               defaults=template_data)
        logger.info('Loaded template: %s', template_name)
