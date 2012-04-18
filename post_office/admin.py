from django.contrib import admin

from .models import Email, Log


def get_message_preview(instance):
    return ('{0}...'.format(instance.message[:25]) if len(instance.message) > 25
            else instance.message)

get_message_preview.short_description = 'Message'


class EmailAdmin(admin.ModelAdmin):
    list_display = ('to', 'subject', get_message_preview, 'status', 'last_updated')


def to(instance):
    return instance.email.to


class LogAdmin(admin.ModelAdmin):
    list_display = ('date', 'email', 'status', get_message_preview)


admin.site.register(Email, EmailAdmin)
admin.site.register(Log, LogAdmin)