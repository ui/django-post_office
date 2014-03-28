==================
Django Post Office
==================

Django Post Office is a simple app to send and manage your emails in Django.
Some awesome features are:

* Allows you to send email asynchronously
* Supports HTML email
* Supports database based email templates
* Built in scheduling support 
* Works well with task queues like `RQ <http://python-rq.org>`_ or `Celery <http://www.celeryproject.org>`_
* Uses multiprocessing to send a large number of emails in parallel


Dependencies
============

* `django >= 1.4 <http://djangoproject.com/>`_
* `django-jsonfield <https://github.com/bradjasper/django-jsonfield>`_


Installation
============

|Build Status|


* Install from PyPI (or you `manually download from PyPI <http://pypi.python.org/pypi/django-post_office>`_)::

    pip install django-post_office

* Add ``post_office`` to your INSTALLED_APPS in django's ``settings.py``:

.. code-block:: python

    INSTALLED_APPS = (
        # other apps
        "post_office",
    )

* Run ``syncdb``::

    python manage.py syncdb

* Set ``post_office.EmailBackend`` as your ``EMAIL_BACKEND`` in django's ``settings.py``::

    EMAIL_BACKEND = 'post_office.EmailBackend'


Quickstart
==========

To get started, make sure you have Django's admin interface enabled. Create an
``EmailTemplate`` instance via ``/admin`` and you can start sending emails.

.. code-block:: python

    from post_office import mail

    mail.send(
        ['recipient1@example.com'],
        'from@example.com',
        template='welcome_email', # Could be an EmailTemplate instance or name
        context={'foo': 'bar'},
    )

The above command will put your email on the queue so you can use the
command in your webapp without slowing down the request/response cycle too much.
To actually send them out, run ``python manage.py send_queued_mail``.
You can schedule this management command to run regularly via cron::

    * * * * * (/usr/bin/python manage.py send_queued_mail >> send_mail.log 2>&1)


Usage
=====

mail.send()
-----------

``mail.send`` is the most important function in this library, it takes these
arguments:

================== ======== =========================
Argument           Required Description
================== ======== =========================
recipients         Yes      list of recipient email addresses
sender             No       Defaults to ``settings.DEFAULT_FROM_EMAIL``, display name is allowed (``John <john@example.com>``)
template           No       ``EmailTemplate`` instance or name
context            No       A dictionary used when email is being rendered
subject            No       Email subject (if ``template`` is not specified)
message            No       Email content (if ``template`` is not specified)
html_message       No       Email's HTML content (if ``template`` is not specified)
headers            No       A dictionary of extra headers to put on the message
scheduled_time     No       A date/datetime object indicating when the email should be sent
priority           No       ``high``, ``medium``, ``low`` or ``now`` (send immediately)
attachments        No       Email attachments - A dictionary where the keys are the wanted filenames,
                            and the values are either files or file-like objects, or full path of
                            the file.
render_on_delivery No       Setting this to ``True`` causes email to be rendered
                            from ``template`` during delivery. Content is never stored
                            in the DB. Usage may result in significant space savings.
================== ======== =========================

Here are a few examples.

If you just want to send out emails without using database templates. You can
call the ``send`` command without the ``template`` argument.

.. code-block:: python

    from post_office import mail

    mail.send(
        ['recipient1@example.com'],
        'from@example.com',
        subject='Welcome!',
        message='Welcome home, {{ name }}!',
        html_message='Welcome home, <b>{{ name }}</b>!',
        headers={'Reply-to': 'reply@example.com'},
        scheduled_time=date(2014, 1, 1),
        context={'name': 'Alice'},
    )

``post_office`` is also task queue friendly. Passing ``now`` as priority into
``send_mail`` will deliver the email right away (instead of queuing it),
regardless of how many emails you have in your queue:

.. code-block:: python

    from post_office import mail

    mail.send(
        ['recipient1@example.com'],
        'from@example.com',
        template='welcome_email',
        context={'foo': 'bar'},
        priority='now',
    )

This is useful if you already use something like `django-rq <https://github.com/ui/django-rq>`_
to send emails asynchronously and only need to store email related activities and logs.

If you want to send an email with attachments:

.. code-block:: python

    from django.core.files.base import ContentFile
    from post_office import mail

    mail.send(
        ['recipient1@example.com'],
        'from@example.com',
        template='welcome_email',
        context={'foo': 'bar'},
        priority='now',
        attachments={
            'attachment1.doc', '/path/to/file/file1.doc',
            'attachment2.txt', ContentFile('file content'),
        }
    )

Template Tags and Variables
---------------------------

``post-office`` supports Django's template tags and variables when.
For example, if you put "Hello, {{ name }}" in the subject line and pass in
``{'name': 'Alice'}`` as context, you will get "Hello, Alice" as subject:

.. code-block:: python

    from post_office.models import EmailTemplate
    from post_office import mail

    EmailTemplate.objects.create(
        name='morning_greeting',
        subject='Morning, {{ name|capfirst }}',
        content='Hi {{ name }}, how are you feeling today?',
        html_content='Hi <strong>{{ name }}</strong>, how are you feeling today?',
    )

    mail.send(
        ['recipient@example.com'],
        'from@example.com',
        template='morning_greeting',
        context={'name': 'alice'},
    )

    # This will create an email with the following content:
    subject = 'Morning, Alice',
    content = 'Hi alice, how are you feeling today?'
    content = 'Hi <strong>alice</strong>, how are you feeling today?'


Custom Email Backends
---------------------

By default, ``post_office`` uses django's SMTP ``EmailBackend``. If you want to
use a different backend, you can do so by changing ``POST_OFFICE_BACKEND``.

For example if you want to use `django-ses <https://github.com/hmarr/django-ses>`_::

    POST_OFFICE_BACKEND = 'django_ses.SESBackend'
    

Management Commands
-------------------

* ``send_queued_mail`` - send queued emails, those aren't successfully sent
  will be marked as ``failed``. If you have a lot of emails, you can
  pass in ``-p`` or ``--processes`` flag to use multiple processes.

* ``cleanup_mail`` - delete all emails created before an X number of days
  (defaults to 90).

You may want to set these up via cron to run regularly::

    * * * * * (cd $PROJECT; python manage.py send_queued_mail --processes=1 >> $PROJECT/cron_mail.log 2>&1)
    0 1 * * * (cd $PROJECT; python manage.py cleanup_mail --days=30 >> $PROJECT/cron_mail_cleanup.log 2>&1)


Logging
-------

You can configure ``post-office``'s logging from Django's ``settings.py``. For
example:

.. code-block:: python
    
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "post_office": {
                "format": "[%(levelname)s]%(asctime)s PID %(process)d: %(message)s",
                "datefmt": "%d-%m-%Y %H:%M:%S",
            },
        },
        "handlers": {
            "post_office": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "post_office"
            },
            # If you use sentry for logging
            'sentry': {
                'level': 'ERROR',
                'class': 'raven.contrib.django.handlers.SentryHandler',
            },
        },
        'loggers': {
            "post_office": {
                "handlers": ["post_office", "sentry"],
                "level": "INFO"
            },
        },
    }

Batch Size
----------

If you may want to limit the number of emails sent in a batch (sometimes useful
in a low memory environment), use the ``BATCH_SIZE`` argument to limit the
number of queued emails fetched in one batch. 

.. code-block:: python

    POST_OFFICE = {
        'BATCH_SIZE': 5000
    }

Default priority
----------------

The default priority for emails is ``medium``, but this can be altered by
setting ``DEFAULT_PRIORITY``. Integration with asynchronous email backends
(e.g. based on Celery) becomes trivial when set to ``now``.

.. code-block:: python

    POST_OFFICE = {
        'DEFAULT_PRIORITY': 'now'
    }


Performance
===========

Caching
-------

if Django's caching mechanism is configured, ``post_office`` will cache
``EmailTemplate`` instances . If for some reason you want to disable caching,
set ``POST_OFFICE_CACHE`` to ``False`` in ``settings.py``:

.. code-block:: python

    ## All cache key will be prefixed by post_office:template:
    ## To turn OFF caching, you need to explicitly set POST_OFFICE_CACHE to False in settings
    POST_OFFICE_CACHE = False

    ## Optional: to use a non default cache backend, add a "post_office" entry in CACHES
    CACHES = {
        'post_office': {
            'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
            'LOCATION': '127.0.0.1:11211',
        }
    }


send_many()
-----------

Starting from version 0.6.0, ``post-office`` includes ``mail.send_many()``
that's much more performant (generates less database queries) when
sending a large number of emails. Since this function uses Django's
`bulk_create <https://docs.djangoproject.com/en/1.5/ref/models/querysets/#bulk-create>`_ command, it's only usable on Django >= 1.4.

Behavior wise, ``mail.send_many()`` is almost identical to ``mail.send()``,
with the exception that it accepts a list of keyword arguments that you'd
usually pass into ``mail.send()``:

.. code-block:: python

    from post_office import mail
    
    first_email = {
        'sender': 'from@example.com',
        'recipients': ['alice@example.com'],
        'subject': 'Hi!',
        'message': 'Hi Alice!'
    }
    second_email = {
        'sender': 'from@example.com',
        'recipients': ['bob@example.com'],
        'subject': 'Hi!',
        'message': 'Hi Bob!'
    }
    kwargs_list = [first_email, second_email]

    mail.send_many(kwargs_list)

Attachments are not supported with ``mail.send_many()``.


Running Tests
=============

To run ``post_office``'s test suite::

    `which django-admin.py` test post_office --settings=post_office.test_settings --pythonpath=.


Changelog
=========

0.8.0
----------
* Added a new setting ``DEFAULT_PRIORITY`` to set the default priority for emails.
  Thanks Maik Hoepfel (@maikhoepfel)!
* ``mail.send()`` gains a ``render_on_delivery`` argument that may potentially
  result in significant storage space savings.
* Uses a new locking mechanism that can detect zombie PID files.

Version 0.7.2
-------------
* Made a few tweaks that makes ``post_office`` much more efficient on systems with
  large number of rows (millions).

Version 0.7.1
-------------
* Python 3 compatibility fix.

Version 0.7.0
-------------
* Added support for sending attachments. Thanks @yprez!
* Added ``description`` field to ``EmailTemplate`` model to store human readable
  description of templates. Thanks Michael P. Jung (@bikeshedder)!
* Changed ``django-jsonfield`` dependency to ``jsonfield`` for Python 3 support reasons.
* Minor bug fixes.

Version 0.6.0
-------------
* Support for Python 3!
* Added mail.send_many() that's much more performant when sending
  a large number emails

Version 0.5.2
-------------
* Added logging
* Added BATCH_SIZE configuration option

Version 0.5.1
-------------
* Fixes various multiprocessing bugs

Version 0.5.0
-------------
* Email sending can now be parallelized using multiple processes (multiprocessing)
* Email templates are now validated before save
* Fixed a bug where custom headers aren't properly sent

Version 0.4.0
-------------
* Added support for sending emails with custom headers (you'll need to run 
  South when upgrading from earlier versions)
* Added support for scheduled email sending
* Backend now properly persist emails with HTML alternatives

Version 0.3.1
-------------
* **IMPORTANT**: ``mail.send`` now expects recipient email addresses as the first
 argument. This change is to allow optional ``sender`` parameter which defaults
 to ``settings.DEFAULT_FROM_EMAIL``
* Fixed a bug where all emails sent from ``mail.send`` have medium priority

Version 0.3.0
-------------
* **IMPORTANT**: added South migration. If you use South and had post-office
  installed before 0.3.0, you may need to manually resolve migration conflicts
* Allow unicode messages to be displayed in ``/admin``
* Introduced a new ``mail.send`` function that provides a nicer API to send emails
* ``created`` fields now use ``auto_now_add``
* ``last_updated`` fields now use ``auto_now``

Version 0.2.1
-------------
* Fixed typo in ``admin.py``

Version 0.2
-----------
* Allows sending emails via database backed templates

Version 0.1.5
-------------
* Errors when opening connection in ``Email.dispatch`` method are now logged


.. |Build Status| image:: https://travis-ci.org/ui/django-post_office.png?branch=master
   :target: https://travis-ci.org/ui/django-post_office
