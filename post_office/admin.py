from django.contrib import admin
from django.utils.text import Truncator

from .models import Email, Log, EmailTemplate, BaseEmailTemplate


def get_message_preview(instance):
    return (u'{0}...'.format(instance.message[:25]) if len(instance.message) > 25
            else instance.message)

get_message_preview.short_description = 'Message'


class LogInline(admin.StackedInline):
    model = Log
    extra = 0


class EmailAdmin(admin.ModelAdmin):
    list_display = ('to', 'subject', get_message_preview, 'status', 'last_updated')
    inlines = [LogInline]


def to(instance):
    return instance.email.to


class LogAdmin(admin.ModelAdmin):
    list_display = ('date', 'email', 'status', get_message_preview)


class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'description_shortened', 'subject', 'created')
    search_fields = ('name', 'description', 'subject')
    fieldsets = [
        (None, {
            'fields': ('name', 'description'),
        }),
        ('Email', {
            'fields': ('base_template', 'subject', 'content', 'html_content'),
        }),
    ]

    def description_shortened(self, instance):
        return Truncator(instance.description.split('\n')[0]).chars(200)
    description_shortened.short_description = 'description'
    description_shortened.admin_order_field = 'description'


class BaseEmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    fieldsets = [
        ('Email', {
            'fields': ('name', 'html_content'),
        })
    ]


admin.site.register(Email, EmailAdmin)
admin.site.register(Log, LogAdmin)
admin.site.register(EmailTemplate, EmailTemplateAdmin)
admin.site.register(BaseEmailTemplate, BaseEmailTemplateAdmin)
