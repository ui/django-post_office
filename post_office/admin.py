from django.contrib import admin
from django.utils.text import Truncator

from .models import Email, Log, EmailTemplate


def get_message_preview(instance):
    return (u'{0}...'.format(instance.message[:25]) if len(instance.message) > 25
            else instance.message)

get_message_preview.short_description = 'Message'


class LogInline(admin.StackedInline):
    model = Log
    extra = 0


class EmailAdmin(admin.ModelAdmin):
    list_display = ('to', 'subject', 'template', 'status', 'last_updated')
    inlines = [LogInline]

    def queryset(self, request):
        return super(EmailAdmin, self).queryset(request).select_related('template')


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
            'fields': ('subject', 'content', 'html_content'),
        }),
    ]

    def description_shortened(self, instance):
        return Truncator(instance.description.split('\n')[0]).chars(200)
    description_shortened.short_description = 'description'
    description_shortened.admin_order_field = 'description'


admin.site.register(Email, EmailAdmin)
admin.site.register(Log, LogAdmin)
admin.site.register(EmailTemplate, EmailTemplateAdmin)
