from django.contrib import admin

from .models import Email, Log, EmailTemplate


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
    list_filter = ('status',)
    search_fields = ('to', 'subject')


def to(instance):
    return instance.email.to


class LogAdmin(admin.ModelAdmin):
    list_display = ('date', 'email', 'status', get_message_preview)
    list_filter = ('status',)
    search_fields = ('email__to',)


class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'created')
    search_fields = ('name', 'subject')

admin.site.register(Email, EmailAdmin)
admin.site.register(Log, LogAdmin)
admin.site.register(EmailTemplate, EmailTemplateAdmin)
