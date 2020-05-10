Changelog
=========

* Allow `tasks.py` to be imported when Celery is not installed. This allows
  auto-discovery by other task systems such as Huey to succeed.

Version 3.4.0 (2020-04-13)
--------------------------
* Signals that emails have been put into the queue.
* [Celery](http://www.celeryproject.org/) integration for immediate asynchronous delivery.
* Changed version handling.

Version 3.3.1 (2020-02-28)
--------------------------
* Drop support for Django < 2.2.
* Revert ``jsonfield2`` back to ``jsonfield`` to make upgrade from < 3.3.0 smoother. Thanks @rpkilby!

Version 3.3.0
-------------
* Support for Django 3.0. Thanks @Mogost!
* Drop support for Django < 1.11 and Python < 3.5. Thanks @Mogost!
* Replace unsupported dependency ``jsonfield`` with supported fork ``jsonfield2``. Thanks @Mogost!
* Added `OVERRIDE_RECIPIENTS` for testing purposes. Thanks @Houtmann!
* Improved admin interface. Thanks @ilikerobots and @cwuebbels!

Version 3.2.1
-------------
* Fix #264: Replace unicode elipsis against 3 dots.

Version 3.2.0
-------------
* Drop support for Python-3.3.
* Drop support for Django-1.8 and 1.9.
* Add functionality to attach images as inlines to email body.
* Add special template engine to render HTML emails with inlined images.
* Update German translation strings.

Version 3.1.0 (2018-07-24)
--------------------------
* Improvements to attachments are handled. Thanks @SeiryuZ!
* Added `--delete-attachments` flag to `cleanup_mail` management command. Thanks @Seiryuz!
* I18n improvements. Thanks @vsevolod-skripnik and @delneg!
* Django admin improvements. Thanks @kakulukia!

Version 3.0.4
-------------
* Added compatibility with Django 2.0. Thanks @PreActionTech and @PetrDlouhy!
* Added natural key support to `EmailTemplate` model. Thanks @maximlomakin!

Version 3.0.3
-------------
* Fixed memory leak when multiprocessing is used.
* Fixed a possible error when adding a new email from Django admin. Thanks @ivlevdenis!

Version 3.0.2
-------------
* `_send_bulk` now properly catches exceptions when preparing email messages.

Version 3.0.1
-------------
* Fixed an infinite loop bug in `send_queued_mail` management command.

Version 3.0.0
-------------
* `_send_bulk` now allows each process to use multiple threads to send emails.
* Added support for mimetypes in email attachments. Thanks @clickonchris!
* An `EmailTemplate` can now be used as defaults multiple times in one language. Thanks @sac7e!
* `send_queued_mail` management command will now check whether there are more queued emails to be sent before exiting.
* Drop support for Django < 1.8. Thanks @fendyh!

Version 2.0.8
-------------
* Django 1.10 compatibility fixes. Thanks @hockeybuggy!
* Fixed an issue where Django would sometimes create migration files for post-office. Thanks @fizista!

Version 2.0.7
-------------
* Fixed an issue with sending email to recipients with display name. Thanks @yprez!

Version 2.0.6
-------------
* Fixes Django 1.10 deprecation warnings and other minor improvements. Thanks @yprez!
* Email.subject can now accept up to 989 characters. This should also fix minor migration issues. Thanks @yprez!

Version 2.0.5
-------------
* Fixes more Django 1.8 deprecation warnings.
* `Email.dispatch()` now closes backend connection by default. Thanks @zwack
* Compatibility fixes for Django 1.9. Thanks @yprez!

Version 2.0.2
-------------
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

Version 0.8.4
-------------
* ``send_queued_mail`` now accepts an extra ``--log-level`` argument.
* ``mail.send()`` now accepts an extra ``log_level`` argument.
* Drop unused/low cardinality indexes to free up RAM on large tables.

Version 0.8.3
-------------
* ``send_queued_mail`` now accepts ``--lockfile`` argument.
* Lockfile implementation has been modified to use symlink, which is an atomic operation
  across platforms.

Version 0.8.2
-------------
* Added ``CONTEXT_FIELD_CLASS`` setting to allow other kinds of context field serializers.

Version 0.8.1
-------------
* Fixed a bug that causes context to be saved when ``render_on_delivery`` is False

Version 0.8.0
-------------
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
