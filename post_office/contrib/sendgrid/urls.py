from django.urls import path

from .views import SendgridWebhookHandler


urlpatterns = [
    path('', SendgridWebhookHandler.as_view(), name='sendgrid_webhook_handler'),
]
