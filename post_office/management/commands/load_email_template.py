import os

from django.core.management.base import BaseCommand

from ...models import EmailTemplate
from ...logutils import setup_loghandlers
from ... import settings

logger = setup_loghandlers()


class Command(BaseCommand):
    help = 'Load an EmailTemplate from Django template files'
    args = 'template_name'

    def handle(self, template_name, *args, **options):
        base_dir = settings.get_template_dir()

        def _get_template(filename):
            with open(os.path.join(base_dir, template_name, filename)) as f:
                content = f.read()
            return content

        try:
            subject = _get_template('subject.txt').strip()
            content = _get_template('content.txt')
            html_content = _get_template('content.html')
        except IOError as e:
            message = str(e)
            message += (
                '\n\nPlease make sure you defined the correct email '
                'template directory structure.\n'
                'You can change the base directory ("{}") by setting '
                'POST_OFFICE["TEMPLATE_DIR"] in your settings file.'
            ).format(base_dir)
            self.stderr.write(message)
            return

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
