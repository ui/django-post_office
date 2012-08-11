==================
Django Post Office
==================

Django Post Office is a simple mail queuing and logging app that allows you to
keep track of email activities and send mails asynchronously in django.

The concept is similar to `django-mailer <https://github.com/jtauber/django-mailer>`_ and
`django-mailer-2 <https://github.com/SmileyChris/django-mailer-2>`_. I maintained `my own fork of
django-mailer-2 here <https://github.com/selwin/django-mailer>`_ until I decided to make one from scratch
because I wanted a cleaner code base.

``post_office`` is implemented as a Django ``EmailBackend`` so you don't need to change any of your code
to start sending email asynchronously.


Dependencies
============

- `django >= 1.2 <http://djangoproject.com/>`_


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

Management Commands
-------------------

* ``send_queued_mail`` will send queued emails. If there are any
   failures, they will be marked deferred and will not be attempted again by
   ``send_queued_mail``.

* ``cleanup_mail`` will delete mails created before an X number of days
   (defaults to 90).

You may want to set these up via cron to run regularly::

    * * * * * (cd $PROJECT; python manage.py send_queued_mail >> $PROJECT/cron_mail.log 2>&1)
    0 1 * * * (cd $PROJECT; python manage.py cleanup_mail --days=30 >> $PROJECT/cron_mail_cleanup.log 2>&1)

Lower Level Usage
-----------------

``post_office`` also comes with a ``send_mail`` command that is very similar to django's,
except that it accepts two extra arguments ``html_message`` and
``priority`` (``high``, ``medium``, ``low`` or ``now``).

Here's how to use it::
    
    from post_office import send_mail, PRIORITY
    send_mail('subject', 'plaintext message', 'from@example.com', ['to@example.com'],
              '<p>HTML message</p>', priority=PRIORITY.medium)

``post_office`` is also task queue friendly. Passing ``now`` as priority into ``send_mail``
will deliver the email right away, even if there's another active process
running ``send_queued_mail`` processing a thousand other messages::
    
    from post_office import send_mail, PRIORITY
    send_mail('subject', 'plaintext message', 'from@example.com', ['to@example.com'],
              '<p>HTML message</p>', priority=PRIORITY.now)

This is also useful if you already use something like `django-rq <https://github.com/ui/django-rq>`_
to send emails asynchronously and only need to store email activities and logs.
