from functools import lru_cache
from typing import Any

from django.template import Engine
from django.template.backends.base import BaseEngine
from django.template.loader import get_template, select_template


@lru_cache(maxsize=512)
def compile_template(template_code: str, engine: Engine | BaseEngine) -> Any:
    """
    Returns engine.from_string(template_code), reusing compiled templates for matching source and engine
    while cached (per process). Only use with engines whose templates are safe to share between renders.
    """
    return engine.from_string(template_code)


def render_to_string(template_name, context=None, request=None, using=None):
    """
    Loads a template and renders it with a context. Returns a tuple of the rendered string and a list of
    attached images for the post_office backend, otherwise just the rendered string.

    template_name may be a string or a list of strings.
    """
    if isinstance(template_name, (list, tuple)):
        template = select_template(template_name, using=using)
    else:
        template = get_template(template_name, using=using)
    content = template.render(context, request)
    if hasattr(template, '_attached_images'):
        return content, template._attached_images
    return content
