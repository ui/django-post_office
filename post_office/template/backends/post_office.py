from typing import Any

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.http import HttpRequest
from django.template import TemplateDoesNotExist
from django.template.backends.base import BaseEngine
from django.template.backends.django import Template as DjangoTemplate, reraise, get_installed_libraries
from django.template.context import make_context
from django.template.engine import Engine

from post_office.settings import PRE_DJANGO_6
from post_office.template import compile_template


class Template(DjangoTemplate):
    def __init__(self, template, backend):
        super().__init__(template, backend)
        self._attached_images = []

    def render(self, context: dict[str, Any] | None = None, request: HttpRequest | None = None) -> str:
        # The compiled template is shared, so images from the latest render are kept on this wrapper.
        self._attached_images = []
        context = make_context(context, request, autoescape=self.backend.engine.autoescape)
        # Stored on the context rather than its template because it survives the copies made by `include ... only`
        context._post_office_attached_images = self._attached_images
        try:
            return self.template.render(context)
        except TemplateDoesNotExist as exc:
            reraise(exc, self.backend)

    def attach_related(self, email_message):
        assert isinstance(email_message, EmailMultiAlternatives), 'Parameter must be of type EmailMultiAlternatives'
        if PRE_DJANGO_6:
            email_message.mixed_subtype = 'related'
        for attachment in self._attached_images:
            email_message.attach(attachment)


class PostOfficeTemplates(BaseEngine):
    """
    Customized Template Engine which keeps track on referenced images and stores them as attachments
    to be used in multipart email messages.
    """

    app_dirname = 'templates'

    def __init__(self, params):
        params = params.copy()
        options = params.pop('OPTIONS').copy()
        options.setdefault('autoescape', True)
        options.setdefault('debug', settings.DEBUG)
        options.setdefault(
            'file_charset',
            settings.FILE_CHARSET if settings.is_overridden('FILE_CHARSET') else 'utf-8',
        )
        libraries = options.get('libraries', {})
        options['libraries'] = self.get_templatetag_libraries(libraries)
        super().__init__(params)
        self.engine = Engine(self.dirs, self.app_dirs, **options)

    def from_string(self, template_code):
        return Template(compile_template(template_code, self.engine), self)

    def get_template(self, template_name):
        try:
            template = self.engine.get_template(template_name)
            return Template(template, self)
        except TemplateDoesNotExist as exc:
            reraise(exc, self)

    def get_templatetag_libraries(self, custom_libraries):
        libraries = get_installed_libraries()
        libraries.update(custom_libraries)
        return libraries
