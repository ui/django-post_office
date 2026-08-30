"""
Tests for Django 6.1+ ``settings.MAILERS`` support. Everything here is skipped
on older Django versions; behaviour shared with the legacy configuration is
tested elsewhere and runs everywhere.
"""

import unittest
import warnings

from django.core import mail
from django.core.mail import send_mail
from django.core.mail.backends.base import BaseEmailBackend
from django.test import TestCase
from django.test.utils import override_settings

from post_office import EmailBackend as PostOfficeEmailBackend
from post_office.connections import connections
from post_office.mail import send
from post_office.models import STATUS, Email
from post_office.settings import DJANGO_HAS_MAILERS

from .test_backends import ErrorRaisingBackend

LOCMEM = 'django.core.mail.backends.locmem.EmailBackend'


class ConstructionForbiddenBackend(BaseEmailBackend):
    """A backend that must never be instantiated by a mere alias lookup."""

    def __init__(self, *args, **kwargs):
        raise AssertionError('backend was constructed')


@unittest.skipUnless(DJANGO_HAS_MAILERS, 'settings.MAILERS requires Django >= 6.1')
class MailersConnectionTest(TestCase):
    def setUp(self):
        # ConnectionHandler caches per thread and consults the cache before
        # settings, so an alias resolved by an earlier test would leak into the
        # override_settings() block. Stage 2b replaces this with a
        # setting_changed receiver.
        connections.close()

    def tearDown(self):
        connections.close()

    @override_settings(
        MAILERS={'default': {'BACKEND': LOCMEM}, 'error': {'BACKEND': 'tests.test_backends.ErrorRaisingBackend'}}
    )
    def test_resolves_through_mailers(self):
        self.assertIsInstance(connections['default'], mail.backends.locmem.EmailBackend)
        self.assertIsInstance(connections['error'], ErrorRaisingBackend)

    @override_settings(MAILERS={'default': {'BACKEND': LOCMEM}})
    def test_no_deprecation_warning(self):
        from django.utils.deprecation import RemovedInDjango70Warning

        with warnings.catch_warnings():
            warnings.simplefilter('error', RemovedInDjango70Warning)
            connections['default']

    @override_settings(MAILERS={'default': {'BACKEND': LOCMEM}})
    def test_post_office_backends_ignored(self):
        # 'locmem' is defined in POST_OFFICE['BACKENDS'] but not in MAILERS
        with self.assertRaises(KeyError) as ctx:
            connections['locmem']
        self.assertIn('locmem', str(ctx.exception))

    @override_settings(
        MAILERS={'default': {'BACKEND': LOCMEM}, 'boom': {'BACKEND': 'tests.test_mailers.ConstructionForbiddenBackend'}}
    )
    def test_backend_constructed_only_at_dispatch(self):
        email = send(recipients=['to@example.com'], sender='from@example.com', subject='s', message='m', backend='boom')
        self.assertEqual(email.backend_alias, 'boom')
        with self.assertRaises(AssertionError):
            connections['boom']


@unittest.skipUnless(DJANGO_HAS_MAILERS, 'settings.MAILERS requires Django >= 6.1')
class MailersSendTest(TestCase):
    def setUp(self):
        connections.close()

    def tearDown(self):
        connections.close()

    @override_settings(MAILERS={'default': {'BACKEND': LOCMEM}, 'ses': {'BACKEND': LOCMEM}})
    def test_send_accepts_mailers_alias(self):
        email = send(recipients=['to@example.com'], sender='from@example.com', subject='s', message='m', backend='ses')
        self.assertEqual(email.backend_alias, 'ses')
        self.assertEqual(email.status, STATUS.queued)

    @override_settings(MAILERS={'default': {'BACKEND': LOCMEM}})
    def test_send_rejects_alias_not_in_mailers(self):
        # 'locmem' exists only in POST_OFFICE['BACKENDS'], which MAILERS supersedes
        with self.assertRaises(ValueError):
            send(recipients=['to@example.com'], sender='from@example.com', subject='s', message='m', backend='locmem')

    @override_settings(MAILERS={'default': {'BACKEND': LOCMEM}, 'ses': {'BACKEND': LOCMEM}})
    def test_dispatch_through_mailers_alias(self):
        email = send(
            recipients=['to@example.com'],
            sender='from@example.com',
            subject='s',
            message='m',
            backend='ses',
            priority='now',
        )
        self.assertEqual(email.status, STATUS.sent)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['to@example.com'])


@unittest.skipUnless(DJANGO_HAS_MAILERS, 'settings.MAILERS requires Django >= 6.1')
class PostOfficeMailerOptionsTest(TestCase):
    """
    post_office reads its configuration from POST_OFFICE, never from mailer
    OPTIONS. These tests pin that decision. ``mailers`` is used directly rather
    than ``connections`` so nothing here dispatches through the queue backend.
    """

    @override_settings(MAILERS={'default': {'BACKEND': 'post_office.EmailBackend'}})
    def test_post_office_mailer_without_options(self):
        from django.core.mail import mailers

        self.assertIsInstance(mailers['default'], PostOfficeEmailBackend)
        send_mail('Test', 'Message', 'from@example.com', ['to@example.com'])
        self.assertEqual(Email.objects.latest('id').status, STATUS.queued)

    @override_settings(MAILERS={'default': {'BACKEND': 'post_office.EmailBackend', 'OPTIONS': {}}})
    def test_post_office_mailer_with_empty_options(self):
        from django.core.mail import mailers

        self.assertIsInstance(mailers['default'], PostOfficeEmailBackend)

    @override_settings(
        MAILERS={'default': {'BACKEND': 'post_office.EmailBackend', 'OPTIONS': {'default_priority': 'now'}}}
    )
    def test_post_office_mailer_rejects_options(self):
        from django.core.mail import InvalidMailer, mailers

        with self.assertRaises(InvalidMailer):
            mailers['default']
