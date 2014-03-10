from modeltranslation.translator import translator, TranslationOptions

from .models import EmailTemplate


class EmailTemplateTranslationOptions(TranslationOptions):
    fields = ('subject', 'content', 'html_content', )

translator.register(EmailTemplate, EmailTemplateTranslationOptions)
