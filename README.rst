==================
Django Post Office
==================

Django Post Office is a simple app that allows you to send email asynchronously
in Django. Supports HTML email, database backed templates and logging.

``post_office`` is implemented as a Django ``EmailBackend`` so you don't need to
change any of your code to start sending email asynchronously.


Dependencies
============

* `django >= 1.2 <http://djangoproject.com/>`_


Installation
============

.. image:: https://travis-ci.org/ui/django-post_office.png?branch=master


* Install from PyPI (or you can `manually download it from PyPI <http://pypi.python.org/pypi/django-post_office>`_)::

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
        'from@example.com',
        ['recipient1@example.com', 'recipient2@example.com'],
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

============ ======== =========================
Argument     Required Description
============ ======== =========================
sender       Yes      email address, display name is allowed (``John <john@example.com>``)
recipients   Yes      list of recipient email addresses
template     No       ``EmailTemplate`` instance or name
context      No       A dictionary used when email is being rendered
subject      No       Email subject (if ``template`` is not specified)
message      No       Email content (if ``template`` is not specified)
html_message No       Email's HTML content (if ``template`` is not specified)
priority     No       ``high``, ``medium``, ``low`` or ``now`` (send immediately)
============ ======== =========================

Here are a few examples.

If you just want to send out emails without using database templates. You can
call the ``send`` command without the ``template`` argument.

.. code-block:: python
    
    from post_office import mail
    
    mail.send(
        'from@example.com',
        ['recipient1@example.com', 'recipient2@example.com'],
        subject='Welcome!',
        message='Welcome home, {{ name }}!',
        html_message='Welcome home, <b>{{ name }}</b>!',
        context={'name': 'Alice'},
    )

``post_office`` is also task queue friendly. Passing ``now`` as priority into
``send_mail`` will deliver the email right away (instead of queuing it),
regardless of how many emails you have in your queue:

.. code-block:: python

    from post_office import mail

    mail.send(
        'from@example.com',
        ['recipient1@example.com'],
        template='welcome_email',
        context={'foo': 'bar'},
        priority='now',
    )

This is useful if you already use something like `django-rq <https://github.com/ui/django-rq>`_
to send emails asynchronously and only need to store email related activities and logs.


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
        html_content='Hi <b>{{ name }}</b>, how are you feeling today?',
    )

    mail.send(
        'from@example.com',
        ['recipient@example.com'],
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


Caching
-------

By default, ``post_office`` will cache ``EmailTemplate``s if Django's caching
mechanism is configured. If for some reason you want to disable caching, you can
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


Management Commands
-------------------

* ``send_queued_mail`` - send queued emails, those that aren't successfully
  sent they will be marked as ``failed``.

* ``cleanup_mail`` - delete all emails created before an X number of days
  (defaults to 90).

You may want to set these up via cron to run regularly::

    * * * * * (cd $PROJECT; python manage.py send_queued_mail >> $PROJECT/cron_mail.log 2>&1)
    0 1 * * * (cd $PROJECT; python manage.py cleanup_mail --days=30 >> $PROJECT/cron_mail_cleanup.log 2>&1)


Testing
=======

To run ``post_office``'s test suite::

    `which django-admin.py` test post_office --settings=post_office.test_settings --pythonpath=.


Changelog
=========

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
