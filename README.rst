==================
Django Post Office
==================

Django Post Office is a simple app to send and manage your emails in Django.
Some awesome features are:

* Allows you to send email asynchronously
* Multi backend support
* Supports HTML email
* Supports database based email templates
* Built in scheduling support
* Works well with task queues like `RQ <http://python-rq.org>`_ or `Celery <http://www.celeryproject.org>`_
* Uses multiprocessing to send a large number of emails in parallel
* Supports multilingual email templates (i18n)


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

If you're still on Django <= 1.6 and use South to manage your migrations,
you'll need to put the following in ``settings.py``:

.. code-block:: python

    SOUTH_MIGRATION_MODULES = {
        "post_office": "post_office.south_migrations",
    }


Quickstart
==========

Send a simple email is really easy:

.. code-block:: python

    from post_office import mail

    mail.send(
        'recipient@example.com', # List of email addresses also accepted
        'from@example.com',
        subject='My email',
        message='Hi there!',
        html_message='Hi <strong>there</strong>!',
    )


If you want to use templates, ensure that Django's admin interface is enabled. Create an
``EmailTemplate`` instance via ``admin`` and do the following:

.. code-block:: python

    from post_office import mail

    mail.send(
        'recipient@example.com', # List of email addresses also accepted
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

+-------------------+----------+-------------------------------------------------+
| Argument          | Required | Description                                     |
+-------------------+----------+-------------------------------------------------+
| recipients        | Yes      | list of recipient email addresses               |
+-------------------+----------+-------------------------------------------------+
| sender            | No       | Defaults to ``settings.DEFAULT_FROM_EMAIL``,    |
|                   |          | display name is allowed (``John <john@a.com>``) |
+-------------------+----------+-------------------------------------------------+
| subject           | No       | Email subject (if ``template`` is not specified)|
+-------------------+----------+-------------------------------------------------+
| message           | No       | Email content (if ``template`` is not specified)|
+-------------------+----------+-------------------------------------------------+
| html_message      | No       | HTML content (if ``template`` is not specified) |
+-------------------+----------+-------------------------------------------------+
| template          | No       | ``EmailTemplate`` instance or name              |
+-------------------+----------+-------------------------------------------------+
| language          | No       | Language in which you want to send the email in |
|                   |          | (if you have multilingual email templates.)     |
+-------------------+----------+-------------------------------------------------+
| cc                | No       | list emails, will appear in ``cc`` field        |
+-------------------+----------+-------------------------------------------------+
| bcc               | No       | list of emails, will appear in `bcc` field      |
+-------------------+----------+-------------------------------------------------+
| attachments       | No       | Email attachments - A dictionary where the keys |
|                   |          | are the filenames and the values are either:    |
|                   |          |                                                 |
|                   |          | * files                                         |
|                   |          | * file-like objects                             |
|                   |          | * full path of the file                         |
+-------------------+----------+-------------------------------------------------+
| context           | No       | A dictionary, used to render templated email    |
+-------------------+----------+-------------------------------------------------+
| headers           | No       | A dictionary of extra headers on the message    |
+-------------------+----------+-------------------------------------------------+
| scheduled_time    | No       | A date/datetime object indicating when the email|
|                   |          | should be sent                                  |
+-------------------+----------+-------------------------------------------------+
| priority          | No       | ``high``, ``medium``, ``low`` or ``now``        |
|                   |          | (send_immediately)                              |
+-------------------+----------+-------------------------------------------------+
| backend           | No       | Alias of the backend you want to use.           |
|                   |          | ``default`` will be used if not specified.      |
+-------------------+----------+-------------------------------------------------+
| render_on_delivery| No       | Setting this to ``True`` causes email to be     |
|                   |          | lazily rendered during delivery. ``template``   |
|                   |          | is required when ``render_on_delivery`` is True.|
|                   |          | This way content is never stored in the DB.     |
|                   |          | May result in significant space savings.        |
+-------------------+----------+-------------------------------------------------+


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
            'attachment1.doc': '/path/to/file/file1.doc',
            'attachment2.txt': ContentFile('file content'),
        }
    )

Template Tags and Variables
---------------------------

``post-office`` supports Django's template tags and variables.
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


Multilingual Email Templates
----------------------------

You can easily create email templates in various different languanges.
For example:

.. code-block:: python

    template = EmailTemplate.objects.create(
        name='hello',
        subject='Hello world!',
    )

    # Add an Indonesian version of this template:
    indonesian_template = template.translated_templates.create(
        language='id',
        subject='Halo Dunia!'
    )

Sending an email using template in a non default languange is
also similarly easy:

.. code-block:: python

    mail.send(
        ['recipient@example.com'],
        'from@example.com',
        template=template, # Sends using the default template
    )

    mail.send(
        ['recipient@example.com'],
        'from@example.com',
        template=template,
        language='id', # Sends using Indonesian template
    )

Custom Email Backends
---------------------

By default, ``post_office`` uses django's ``smtp.EmailBackend``. If you want to
use a different backend, you can do so by configuring ``BACKENDS``.

For example if you want to use `django-ses <https://github.com/hmarr/django-ses>`_::

    POST_OFFICE = {
        'BACKENDS': {
            'default': 'smtp.EmailBackend',
            'ses': 'django_ses.SESBackend',
        }
    }

You can then choose what backend you want to use when sending mail:

.. code-block:: python

    # If you omit `backend_alias` argument, `default` will be used
    mail.send(
        ['recipient@example.com'],
        'from@example.com',
        subject='Hello',
    )

    # If you want to send using `ses` backend
    mail.send(
        ['recipient@example.com'],
        'from@example.com',
        subject='Hello',
        backend='ses',
    )


Management Commands
-------------------

* ``send_queued_mail`` - send queued emails, those aren't successfully sent
  will be marked as ``failed``. Accepts the following arguments:

+---------------------------+-------------------------------------------------+
| Argument                  | Description                                     |
+---------------------------+-------------------------------------------------+
| ``--processes`` or ``-p`` | Number of parallel processes to send email.     |
|                           | Defaults to 1                                   |
+---------------------------+---------+---------------------------------------+
| ``--lockfile`` or ``-L``  | Full path to file used as lock file. Defaults to|
|                           | ``/tmp/post_office.lock``                       |
+---------------------------+-------------------------------------------------+


* ``cleanup_mail`` - delete all emails created before an X number of days
  (defaults to 90).

You may want to set these up via cron to run regularly::

    * * * * * (cd $PROJECT; python manage.py send_queued_mail --processes=1 >> $PROJECT/cron_mail.log 2>&1)
    0 1 * * * (cd $PROJECT; python manage.py cleanup_mail --days=30 >> $PROJECT/cron_mail_cleanup.log 2>&1)

Settings
========
This section outlines all the settings and configurations that you can put
in Django's ``settings.py`` to fine tune ``post-office``'s behavior.

Batch Size
----------

If you may want to limit the number of emails sent in a batch (sometimes useful
in a low memory environment), use the ``BATCH_SIZE`` argument to limit the
number of queued emails fetched in one batch.

.. code-block:: python

    # Put this in settings.py
    POST_OFFICE = {
        'BATCH_SIZE': 5000
    }

Default Priority
----------------

The default priority for emails is ``medium``, but this can be altered by
setting ``DEFAULT_PRIORITY``. Integration with asynchronous email backends
(e.g. based on Celery) becomes trivial when set to ``now``.

.. code-block:: python

    # Put this in settings.py
    POST_OFFICE = {
        'DEFAULT_PRIORITY': 'now'
    }

Log Level
---------

The default log level is 2 (logs both successful and failed deliveries)
This behavior can be changed by setting ``LOG_LEVEL``.

.. code-block:: python

    # Put this in settings.py
    POST_OFFICE = {
        'LOG_LEVEL': 1 # Log only failed deliveries
    }

The different options are:

* ``0`` logs nothing
* ``1`` logs only failed deliveries
* ``2`` logs everything (both successful and failed delivery attempts)


Sending Order
----------------

The default sending order for emails is ``-priority``, but this can be altered by
setting ``SENDING_ORDER``. For example, if you want to send queued emails in FIFO order :

.. code-block:: python

    # Put this in settings.py
    POST_OFFICE = {
        'SENDING_ORDER': ['created']
    }

Context Field Serializer
------------------------

If you need to store complex Python objects for deferred rendering
(i.e. setting ``render_on_delivery=True``), you can specify your own context
field class to store context variables. For example if you want to use
`django-picklefield <https://github.com/gintas/django-picklefield/tree/master/src/picklefield>`_:

.. code-block:: python

    # Put this in settings.py
    POST_OFFICE = {
        'CONTEXT_FIELD_CLASS': 'picklefield.fields.PickledObjectField'
    }

``CONTEXT_FIELD_CLASS`` defaults to ``jsonfield.JSONField``.

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

``send_many()`` is much more performant (generates less database queries) when
sending a large number of emails. ``send_many()`` is almost identical to ``mail.send()``,
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

To run the test suite::

    `which django-admin.py` test post_office --settings=post_office.test_settings --pythonpath=.


Changelog
=========

Version 2.0.6
-------------
* Fixes Django 1.10 deprecation warnings and other minor improvements. Thanks @yprez!
* Email.subject can now accept up to 989 characters. This should also fix minor migration issues. Thanks @yprez!

Version 2.0.5
-------------
* Fixes more Django 1.8 deprecation warnings.
* `Email.dispatch()` now closes backend connection by default. Thanks @zwack
* Compatibility fixes for Django 1.9. Thanks @yprez!

Version 2.0.1
-------------
* Fixes migration related packaging issues.
* Fixes deprecation warning in Django 1.8.

Version 2.0
-----------
* Added multi backend support. Now you can use multiple email backends with ``post-office``!
* Added multi language support. Thanks @jrief!

Version 1.1.2
-------------
* Adds Django 1.8 compatibility.

Version 1.1.1
-------------
* Fixes a migration error. Thanks @garry-cairns!

Version 1.1.0
-------------
* Support for Django 1.7 migrations. If you're still on Django < 1.7,
  South migration files are stored in ``south_migrations`` directory.

Version 1.0.0
-------------
* **IMPORTANT**: in older versions, passing multiple ``recipients`` into
  ``mail.send()`` will create multiple emails, each addressed to one recipient.
  Starting from ``1.0.0``, only one email with multiple recipients will be created.
* Added ``LOG_LEVEL`` setting.
* ``mail.send()`` now supports ``cc`` and ``bcc``.
  Thanks Ștefan Daniel Mihăilă (@stefan-mihaila)!
* Improvements to ``admin`` interface; you can now easily requeue multiple emails.
* ``Log`` model now stores the type of exception caught during sending.
* ``send_templated_mail`` command is now deprecated.
* Added ``EMAIL_BACKEND`` setting to the new dictionary-styled settings.


Full changelog can be found `here <https://github.com/ui/django-post_office/blob/master/CHANGELOG.md>`_.


Created and maintained by the cool guys at `Stamps <https://stamps.co.id>`_,
Indonesia's most elegant CRM/loyalty platform.


.. |Build Status| image:: https://travis-ci.org/ui/django-post_office.png?branch=master
   :target: https://travis-ci.org/ui/django-post_office
