from django.contrib import admin
from django.forms.widgets import TextInput
from django.utils.text import Truncator

from .fields import CommaSeparatedEmailField
from .models import Email, Log, EmailTemplate, STATUS


def get_message_preview(instance):
    return (u'{0}...'.format(instance.message[:25]) if len(instance.message) > 25
            else instance.message)

get_message_preview.short_description = 'Message'


class LogInline(admin.StackedInline):
    model = Log
    extra = 0


class CommaSeparatedEmailWidget(TextInput):

    def __init__(self, *args, **kwargs):
        super(CommaSeparatedEmailWidget, self).__init__(*args, **kwargs)
        self.attrs.update({'class': 'vTextField'})

    def _format_value(self, value):
        return ','.join([item for item in value])


def requeue(modeladmin, request, queryset):
    """An admin action to requeue emails."""
    queryset.update(status=STATUS.queued)


requeue.short_description = 'Requeue selected emails'


class EmailAdmin(admin.ModelAdmin):
    list_display = ('id', 'to_display', 'subject', 'template',
                    'status', 'last_updated')
    inlines = [LogInline]
    list_filter = ['status']
    formfield_overrides = {
        CommaSeparatedEmailField: {'widget': CommaSeparatedEmailWidget}
    }
    actions = [requeue]

    def get_queryset(self, request):
        return super(EmailAdmin, self).get_queryset(request).select_related('template')

    def to_display(self, instance):
        return ', '.join(instance.to)

    to_display.short_description = 'to'
    to_display.admin_order_field = 'to'


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
