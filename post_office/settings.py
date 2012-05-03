from django.conf import settings


def get_backend():
    from django.conf import settings
    if hasattr(settings, 'POST_OFFICE_BACKEND'):
        backend = getattr(settings, 'POST_OFFICE_BACKEND')
    else:
        backend = getattr(settings, 'EMAIL_BACKEND',
                          'django.core.mail.backends.smtp.EmailBackend')
        # If EMAIL_BACKEND is set to use PostOfficeBackend
        # and POST_OFFICE_BACKEND is not set, fall back to SMTP
        if 'post_office' in backend:
            backend = 'django.core.mail.backends.smtp.EmailBackend'
    return backend