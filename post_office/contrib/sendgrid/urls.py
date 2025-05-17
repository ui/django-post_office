from django.urls import path

from .views import sendgrid_deliverability_webhook_handler


urlpatterns = [
    path('deliverability', sendgrid_deliverability_webhook_handler, 'sendgrid_deliverability_webhook_handler'),
]
