import re

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.template import TemplateDoesNotExist, TemplateSyntaxError
from django.template.base import TextNode
from django.utils.encoding import force_str

from .settings import get_template_engine


def validate_email_with_name(value):
    """
    Validate email address.

    Both "Recipient Name <email@example.com>" and "email@example.com" are valid.
    """
    value = force_str(value)

    # Newlines would allow injecting extra headers (e.g. "Bcc:") through the display name.
    if '\n' in value or '\r' in value:
        raise ValidationError('Email address must not contain line breaks.', code='invalid')

    recipient = value
    if '<' in value and '>' in value:
        start = value.find('<') + 1
        end = value.find('>')
        if start < end:
            recipient = value[start:end]
            if value[end + 1 :].strip():
                raise ValidationError('Unexpected text after email address.', code='invalid')

    validate_email(recipient)


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


# Template delimiters that Django silently renders as literal text when they are
# malformed, e.g. "{{ user.fullname }" or "{ if user %}". Each pattern is matched
# against text outside of tags, so a hit means the tag was never recognized.
MALFORMED_TAG_PATTERNS = [
    # "{{ name }", "{{ name ]}", or a variable tag split over several lines
    (re.compile(r'\{\{'), 'Unclosed variable tag'),
    # "{% if x }", "{% if x %"
    (re.compile(r'\{%'), 'Unclosed block tag'),
    # "{# note" (single-line comments can't span lines either)
    (re.compile(r'\{#'), 'Unclosed comment tag'),
    # "{ name }}" - restricted to a plain variable name so CSS such as "a{b:c}}" is not flagged
    (re.compile(r'(?<!\{)\{[ \t]*[\w.]+[ \t]*\}\}'), 'Variable tag is missing an opening brace'),
    # "{ if x %}" - requires whitespace before "%}" so CSS such as "a{width:100%}" is not flagged
    (re.compile(r'(?<!\{)\{[ \t]*\w[^{}\n]*[ \t]%\}'), 'Block tag is missing an opening brace'),
]


def find_malformed_tags(template):
    """
    Return error messages for template tags that the Django template engine did
    not recognize and would output as plain text.

    Text inside {% verbatim %} and {% comment %} blocks is not inspected.
    """
    errors = []
    for node in template.nodelist.get_nodes_by_type(TextNode):
        token = getattr(node, 'token', None)
        for pattern, message in MALFORMED_TAG_PATTERNS:
            for match in pattern.finditer(node.s):
                if token is not None:
                    lineno = token.lineno + node.s.count('\n', 0, match.start())
                    errors.append(f'{message} on line {lineno}: {_context_of(node.s, match)!r}')
                else:
                    errors.append(f'{message}: {_context_of(node.s, match)!r}')
    return errors


def _context_of(text, match):
    line_start = text.rfind('\n', 0, match.start()) + 1
    line_end = text.find('\n', match.end())
    if line_end == -1:
        line_end = len(text)
    return text[line_start:line_end].strip()[:80]


def validate_template_syntax(source):
    """
    Basic Django Template syntax validation. This allows for robuster template
    authoring.

    The template is compiled with the engine configured for rendering emails, and
    tags that are malformed in a way Django silently ignores (e.g. a missing brace
    in "{{ user.fullname }") are reported as well.
    """
    try:
        template = get_template_engine().from_string(source)
    except (TemplateSyntaxError, TemplateDoesNotExist) as err:
        raise ValidationError(str(err))

    # Only Django template backends expose the compiled nodelist.
    compiled = getattr(template, 'template', None)
    if hasattr(compiled, 'nodelist'):
        errors = find_malformed_tags(compiled)
        if errors:
            raise ValidationError(errors)
