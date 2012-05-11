==================
Django Post Office
==================

Django Post Office is a simple mail queuing app that allows you to send mails asynchronously in django.
The concept is very similar to `django-mailer <https://github.com/jtauber/django-mailer>`_ and
`django-mailer-2 <https://github.com/SmileyChris/django-mailer-2>`_. I maintained `my own fork of
django-mailer-2 here <https://github.com/selwin/django-mailer>`_ until I decided to make one from scratch
because I wanted a cleaner code base.

``post_office`` is implemented as a Django ``EmailBackend`` so you don't need to change any of your code
to start sending email asynchronously.


Dependencies
============

- `django > 1.2 <http://djangoproject.com/>`_: http://djangoproject.com/


Installation
============

* Copy ``post_office`` to your ``PYTHONPATH``
* Add ``post_office`` to your INSTALLED_APPS in django's ``settings.py``::
    
    INSTALLED_APPS = (
        # other apps
        "post_office",
    )

* Set ``post_office.EmailBackend`` as your ``EMAIL_BACKEND`` in django's ``settings.py``::

    EMAIL_BACKEND = 'post_office.EMAIL_BACKEND'


Usage
=====

If you use ``post_office``'s ``EmailBackend``, it will automatically queue emails sent using
django's ``send_mail`` in the database.

To actually send them out, run ``python manage.py send_mail``. You can schedule this
to run regularly via cron::
    
    * * * * * (/usr/bin/python manage.py send_mail >> send_mail.log 2>&1)


By default, ``post_office`` uses django's SMTP ``EmailBackend``. If you want to use a different one,
you can do so by changing ``POST_OFFICE_BACKEND``.

For example if you want to use `django-ses <https://github.com/hmarr/django-ses>`_)::

    POST_OFFICE_BACKEND = 'django_ses.SESBackend'

You can view also queued emails along with their statuses if you have django's admin interface enabled::
    
    INSTALLED_APPS = (
        # ...
        'django.contrib.admin',
        # ...
    )

Sending HTML Email
------------------

``post_office`` also comes with a ``send_mail`` command that is very similar to django's,
except that it accepts two extra arguments ``html_message`` and ``priority`` (``high``, ``medium`` or ``low``).

Here's how to use it::
    
    send_mail('subject', 'plaintext message', 'from@example.com', ['to@example.com'],
              '<p>HTML message</p>', priority='medium')
