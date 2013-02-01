==================
Django Post Office
==================

Django Post Office is a simple app that allows you to log email activities and
asynchronously send emails in django. Supports HTML email.

The concept is similar to `django-mailer <https://github.com/jtauber/django-mailer>`_ and
`django-mailer-2 <https://github.com/SmileyChris/django-mailer-2>`_. I maintained `my own fork of
django-mailer-2 here <https://github.com/selwin/django-mailer>`_ until I decided to make one from scratch
because I wanted a cleaner code base.

``post_office`` is implemented as a Django ``EmailBackend`` so you don't need to
change any of your code to start sending email asynchronously.


Dependencies
============

* `django >= 1.2 <http://djangoproject.com/>`_


Installation
============

* Install via pypi::

    pip install django-post_office

* Add ``post_office`` to your INSTALLED_APPS in django's ``settings.py``::

    INSTALLED_APPS = (
        # other apps
        "post_office",
    )

* Run ``syncdb``::

    python manage.py syncdb

* Set ``post_office.EmailBackend`` as your ``EMAIL_BACKEND`` in django's ``settings.py``::

    EMAIL_BACKEND = 'post_office.EmailBackend'


Usage
=====

If you use ``post_office``'s ``EmailBackend``, it will automatically queue emails sent using
django's ``send_mail`` in the database.

To actually send them out, run ``python manage.py send_queued_mail``. You can schedule this
to run regularly via cron::

    * * * * * (/usr/bin/python manage.py send_queued_mail >> send_mail.log 2>&1)


By default, ``post_office`` uses django's SMTP ``EmailBackend``. If you want to
use a different backend, you can do so by changing ``POST_OFFICE_BACKEND``.

For example if you want to use `django-ses <https://github.com/hmarr/django-ses>`_::

    POST_OFFICE_BACKEND = 'django_ses.SESBackend'

You can view also queued emails along with their statuses if you have django's
admin interface enabled::

    INSTALLED_APPS = (
        # ...
        'django.contrib.admin',
        # ...
    )

Management Commands
-------------------

* ``send_queued_mail`` - send queued emails, those that aren't successfully
  sent they will be marked as ``failed``.

* ``cleanup_mail`` - delete all emails created before an X number of days
  (defaults to 90).

You may want to set these up via cron to run regularly::

    * * * * * (cd $PROJECT; python manage.py send_queued_mail >> $PROJECT/cron_mail.log 2>&1)
    0 1 * * * (cd $PROJECT; python manage.py cleanup_mail --days=30 >> $PROJECT/cron_mail_cleanup.log 2>&1)

Lower Level Usage
-----------------

``post_office`` also comes with a ``send_mail`` command similar to django's.
It accepts two extra arguments, ``html_message`` and
``priority`` (``high``, ``medium``, ``low`` or ``now``).

Here's how to use it::

    from post_office import send_mail, PRIORITY
    send_mail('subject', 'plaintext message', 'from@example.com', ['to@example.com'],
              '<p>HTML message</p>', priority=PRIORITY.medium)

``post_office`` is also task queue friendly. Passing ``now`` as priority into
``send_mail`` will deliver the email right away, regardless of how many emails
you have in your queue::

    from post_office import send_mail, PRIORITY
    send_mail('subject', 'plaintext message', 'from@example.com', ['to@example.com'],
              '<p>HTML message</p>', priority=PRIORITY.now)

This is useful if you already use something like `django-rq <https://github.com/ui/django-rq>`_
to send emails asynchronously and only need to store email activities and logs.


Templated email
---------------
``post_office`` now supports templated email from database with basic caching support.
``post_office`` will create a database table to store your email templates that can be used to send emails with context.

Basic usage::

    1. Create EmailTemplate object

        from post_office.models import EmailTemplate
        email_template = EmailTemplate.objects.create(name='template_name',
            subject='your_subject', content='your_content, {{name}}',
            html_content='<p>your html content {{name}}</p>')

    2. Send templated email

        from post_office.utils import send_templated_mail
        send_templated_mail(template_name, 'from@example.com', ['to@example.com'],
            priority=PRIORITY.medium, context={'name': 'AwesomeBoy'})

    3. (Optional) Add caching for templated email by adding this settings in your settings file

        ## Enable caching support for post_office templated email
        ## Without this key caching support will be turned off
        ## All cache key will be prefixed by post_office:template:
        POST_OFFICE_TEMPLATE_CACHE = True

        ## This is optional, if 'post_office' key is non existent, it will use
        ## 'default' key
        CACHES = {
                    'post_office': {
                        'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
                        'LOCATION': '127.0.0.1:11211',
                    }
                }

Testing
=======


To run ``post_office``'s test suite::

    django-admin.py test post_office --settings=post_office.tests.settings --pythonpath=.



Changelog
=========

Version 0.1.5
-------------
* Errors when opening connection in ``Email.dispatch`` method are now logged
