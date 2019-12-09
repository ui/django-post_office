==================
Django Post Office
==================

Django Post Office is a simple app to send and manage your emails in Django.
Some awesome features are:

* Allows you to send email asynchronously
* Multi backend support
* Supports HTML email
* Supports inlined images in HTML email
* Supports database based email templates
* Supports multilingual email templates (i18n)
* Built in scheduling support
* Works well with task queues like `RQ <http://python-rq.org>`_ or `Celery <http://www.celeryproject.org>`_
* Uses multiprocessing (and threading) to send a large number of emails in parallel


Dependencies
============

* `django >= 1.11 <https://djangoproject.com/>`_
* `jsonfield2 <https://github.com/rpkilby/jsonfield2>`_


Installation
============

|Build Status|
|PyPI version|
|Software license|

* Install from PyPI (or you `manually download from PyPI <http://pypi.python.org/pypi/django-post_office>`_)::

    pip install django-post_office

* Add ``post_office`` to your INSTALLED_APPS in django's ``settings.py``:

  .. code-block:: python

    INSTALLED_APPS = (
        # other apps
        "post_office",
    )

* Run ``migrate``::

    python manage.py migrate

* Set ``post_office.EmailBackend`` as your ``EMAIL_BACKEND`` in django's ``settings.py``:

  .. code-block:: python

    EMAIL_BACKEND = 'post_office.EmailBackend'


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

or, if you use uWSGI_ as application server, add this short snipped  to the
project's ``wsgi.py`` file:

.. code-block:: python

    from django.core.wsgi import get_wsgi_application

    application = get_wsgi_application()

    # add this block of code
    try:
        import uwsgidecorators
        from django.core.management import call_command

        @uwsgidecorators.timer(10)
        def send_queued_mail(num):
            """Send queued mail every 10 seconds"""
            call_command('send_queued_mail', processes=1)

    except ImportError:
        print("uwsgidecorators not found. Cron and timers are disabled")

Alternatively you can also use the decorator ``@uwsgidecorators.cron(minute, hour, day, month, weekday)``.
This will schedule a task at specific times. Use ``-1`` to signal any time, it corresponds to the ``*``
in cron.

Please note that ``uwsgidecorators`` are available only, if the application has been started
with **uWSGI**. However, Django's internal ``./manange.py runserver`` also access this file,
therefore wrap the block into an exception handler as shown above.

This configuration is very useful in environments, such as Docker containers, where you
don't have a running cron-daemon.


Usage
=====

mail.send()
-----------

``mail.send`` is the most important function in this library, it takes these
arguments:

+--------------------+----------+--------------------------------------------------+
| Argument           | Required | Description                                      |
+--------------------+----------+--------------------------------------------------+
| recipients         | Yes      | list of recipient email addresses                |
+--------------------+----------+--------------------------------------------------+
| sender             | No       | Defaults to ``settings.DEFAULT_FROM_EMAIL``,     |
|                    |          | display name is allowed (``John <john@a.com>``)  |
+--------------------+----------+--------------------------------------------------+
| subject            | No       | Email subject (if ``template`` is not specified) |
+--------------------+----------+--------------------------------------------------+
| message            | No       | Email content (if ``template`` is not specified) |
+--------------------+----------+--------------------------------------------------+
| html_message       | No       | HTML content (if ``template`` is not specified)  |
+--------------------+----------+--------------------------------------------------+
| template           | No       | ``EmailTemplate`` instance or name               |
+--------------------+----------+--------------------------------------------------+
| language           | No       | Language in which you want to send the email in  |
|                    |          | (if you have multilingual email templates.)      |
+--------------------+----------+--------------------------------------------------+
| cc                 | No       | list emails, will appear in ``cc`` field         |
+--------------------+----------+--------------------------------------------------+
| bcc                | No       | list of emails, will appear in `bcc` field       |
+--------------------+----------+--------------------------------------------------+
| attachments        | No       | Email attachments - A dictionary where the keys  |
|                    |          | are the filenames and the values are either:     |
|                    |          |                                                  |
|                    |          | * files                                          |
|                    |          | * file-like objects                              |
|                    |          | * full path of the file                          |
+--------------------+----------+--------------------------------------------------+
| context            | No       | A dictionary, used to render templated email     |
+--------------------+----------+--------------------------------------------------+
| headers            | No       | A dictionary of extra headers on the message     |
+--------------------+----------+--------------------------------------------------+
| scheduled_time     | No       | A date/datetime object indicating when the email |
|                    |          | should be sent                                   |
+--------------------+----------+--------------------------------------------------+
| priority           | No       | ``high``, ``medium``, ``low`` or ``now``         |
|                    |          | (send_immediately)                               |
+--------------------+----------+--------------------------------------------------+
| backend            | No       | Alias of the backend you want to use.            |
|                    |          | ``default`` will be used if not specified.       |
+--------------------+----------+--------------------------------------------------+
| render_on_delivery | No       | Setting this to ``True`` causes email to be      |
|                    |          | lazily rendered during delivery. ``template``    |
|                    |          | is required when ``render_on_delivery`` is True. |
|                    |          | This way content is never stored in the DB.      |
|                    |          | May result in significant space savings.         |
+--------------------+----------+--------------------------------------------------+


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
            'attachment3.txt': { 'file': ContentFile('file content'), 'mimetype': 'text/plain'},
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


Inlined Images
--------------

Often one wants to render images inside a template, which are attached as inlined ``MIMEImage`` to
the outgoing email. This requires a slightly modified Django Template Engine, keeping a list of
inlined images, which later will be added to the outgoing message.

First we must add a special Django template backend to our list of template engines:

.. code-block:: python

	TEMPLATES = [
	    {
	        ...
	    }, {
	        'BACKEND': 'post_office.template.backends.post_office.PostOfficeTemplates',
	        'APP_DIRS': True,
	        'DIRS': [],
	        'OPTIONS': {
	            'context_processors': [
	                'django.contrib.auth.context_processors.auth',
	                'django.template.context_processors.debug',
	                'django.template.context_processors.i18n',
	                'django.template.context_processors.media',
	                'django.template.context_processors.static',
	                'django.template.context_processors.tz',
	                'django.template.context_processors.request',
	            ]
	        }
	    }
	]

then we must tell Post-Office to use this template engine:

.. code-block:: python

	POST_OFFICE = {
	    'TEMPLATE_ENGINE': 'post_office',
	}

In templates used to render HTML for emails add

.. code-block:: Django

	{% load ... post_office %}

	<p>... somewhere in the body ...</p>
	<img src="{% inline_image 'path/to/image.png' %}" />

Here the templatetag named ``inline_image`` is used to keep track of inlined images. It takes a single
parameter. This can either be the relative path to an image file located in one of the ``static``
directories, or the absolute path to an image file, or an image-file object itself. Templates
rendered using this templatetag, render a reference ID for each given image, and store these images
inside the context of the adopted template engine. Later on, when the rendered template is passed
to the mailing library, those images will be transferred to the email message object as
``MIMEImage``-attachments.

To send an email containing both, a plain text body and some HTML with inlined images, use the
following code snippet:

.. code-block:: python

	from django.core.mail import EmailMultiAlternatives

	subject, body, from_email, to_email = "Hello", "Plain text body", "no-reply@example.com", "john@example.com"
	email_message = EmailMultiAlternatives(subject, body, from_email, [to_email])
	template = get_template('email-template-name.html', using='post_office')
	context = {...}
	html = template.render(context)
	email_message.attach_alternative(html, 'text/html')
	template.attach_related(email_message)
	email_message.send()

To send an email containing HTML with inlined images, but without a plain text body, use this
code snippet:

.. code-block:: python

	from django.core.mail import EmailMultiAlternatives

	subject, from_email, to_email = "Hello", "no-reply@example.com", "john@example.com"
	template = get_template('email-template-name.html', using='post_office')
	context = {...}
	html = template.render(context)
	email_message = EmailMultiAlternatives(subject, html, from_email, [to_email])
	email_message.content_subtype = 'html'
	template.attach_related(email_message)
	email_message.send()



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

+---------------------------+--------------------------------------------------+
| Argument                  | Description                                      |
+---------------------------+--------------------------------------------------+
| ``--processes`` or ``-p`` | Number of parallel processes to send email.      |
|                           | Defaults to 1                                    |
+---------------------------+--------------------------------------------------+
| ``--lockfile`` or ``-L``  | Full path to file used as lock file. Defaults to |
|                           | ``/tmp/post_office.lock``                        |
+---------------------------+--------------------------------------------------+


* ``cleanup_mail`` - delete all emails created before an X number of days
  (defaults to 90).

+---------------------------+--------------------------------------------------+
| Argument                  | Description                                      |
+---------------------------+--------------------------------------------------+
| ``--days`` or ``-d``      | Email older than this argument will be deleted.  |
|                           | Defaults to 90                                   |
+---------------------------+--------------------------------------------------+
| ``--delete-attachments``  | Flag to delete orphaned attachment records and   |
|      or ``-da``           | files on disk. If flag does not exist,           |
|                           | attachments will be ignored by the cleanup.      |
+---------------------------+--------------------------------------------------+


You may want to set these up via cron to run regularly::

    * * * * * (cd $PROJECT; python manage.py send_queued_mail --processes=1 >> $PROJECT/cron_mail.log 2>&1)
    0 1 * * * (cd $PROJECT; python manage.py cleanup_mail --days=30 --delete-attachments >> $PROJECT/cron_mail_cleanup.log 2>&1)

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
        'BATCH_SIZE': 50
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

Override Recipients
-------------------

Defaults to ``None``. This option is useful if you want to redirect all emails to specified a few email for development purposes.

.. code-block:: python

    # Put this in settings.py
    POST_OFFICE = {
        'OVERRIDE_RECIPIENTS': ['to@example.com', 'to2@example.com']
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
-------------

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


Threads
-------

``post-office`` >= 3.0 allows you to use multiple threads to dramatically speed up
the speed at which emails are sent. By default, ``post-office`` uses 5 threads per process.
You can tweak this setting by changing ``THREADS_PER_PROCESS`` setting.

This may dramatically increase the speed of bulk email delivery, depending on which email
backends you use. In my tests, multi threading speeds up email backends that use HTTP based
(REST) delivery mechanisms but doesn't seem to help SMTP based backends.

.. code-block:: python

    # Put this in settings.py
    POST_OFFICE = {
        'THREADS_PER_PROCESS': 10
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

You can run the full test suite with::

    tox

or::

    python setup.py test


Changelog
=========

Full changelog can be found `here <https://github.com/ui/django-post_office/blob/master/CHANGELOG.md>`_.


Created and maintained by the cool guys at `Stamps <https://stamps.co.id>`_,
Indonesia's most elegant CRM/loyalty platform.


.. |Build Status| image:: https://travis-ci.org/ui/django-post_office.png?branch=master
   :target: https://travis-ci.org/ui/django-post_office

.. |PyPI version| image:: https://img.shields.io/pypi/v/django-post_office.svg
   :target: https://pypi.org/project/django-post_office/

.. |Software license| image:: https://img.shields.io/pypi/l/django-post_office.svg

.. _uWSGI: https://uwsgi-docs.readthedocs.org/en/latest/
