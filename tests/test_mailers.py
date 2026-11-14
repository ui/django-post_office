"""
Tests for Django 6.1+ ``settings.MAILERS`` support. Everything here is skipped
on older Django versions; behaviour shared with the legacy configuration is
tested elsewhere and runs everywhere.
"""

import unittest
import warnings
from unittest import mock

from django.conf import settings
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
POST_OFFICE_BACKEND = 'post_office.EmailBackend'


def post_office_config(**extra):
    """POST_OFFICE settings with ``extra`` merged in, so overrides keep MAX_RETRIES etc."""
    return {**settings.POST_OFFICE, **extra}


class QueueSubclassBackend(PostOfficeEmailBackend):
    """A user subclass of the post_office queue backend."""


class ConstructionForbiddenBackend(BaseEmailBackend):
    """A backend that must never be instantiated by a mere alias lookup."""

    def __init__(self, *args, **kwargs):
        raise AssertionError('backend was constructed')


@unittest.skipUnless(DJANGO_HAS_MAILERS, 'settings.MAILERS requires Django >= 6.1')
class MailersTestCase(TestCase):
    """
    ConnectionHandler caches per thread and consults the cache before settings,
    so an alias resolved by an earlier test would leak into (and out of) the
    override_settings() block. post_office deliberately has no production hook
    for this, so tests clear the cache explicitly.
    """

    def setUp(self):
        connections.close()

    def tearDown(self):
        connections.close()


class MailersConnectionTest(MailersTestCase):
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


class MailersSendTest(MailersTestCase):
    @override_settings(MAILERS={'default': {'BACKEND': LOCMEM}, 'locmem': {'BACKEND': LOCMEM}})
    def test_send_accepts_mailers_alias(self):
        email = send(
            recipients=['to@example.com'], sender='from@example.com', subject='s', message='m', backend='locmem'
        )
        self.assertEqual(email.backend_alias, 'locmem')
        self.assertEqual(email.status, STATUS.queued)

    @override_settings(MAILERS={'default': {'BACKEND': LOCMEM}})
    def test_send_rejects_alias_not_in_mailers(self):
        # 'locmem' exists only in POST_OFFICE['BACKENDS'], which MAILERS supersedes
        with self.assertRaises(ValueError):
            send(recipients=['to@example.com'], sender='from@example.com', subject='s', message='m', backend='locmem')

    @override_settings(MAILERS={'default': {'BACKEND': LOCMEM}, 'locmem': {'BACKEND': LOCMEM}})
    def test_dispatch_through_mailers_alias(self):
        email = send(
            recipients=['to@example.com'],
            sender='from@example.com',
            subject='s',
            message='m',
            backend='locmem',
            priority='now',
        )
        self.assertEqual(email.status, STATUS.sent)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['to@example.com'])


class PostOfficeMailerOptionsTest(MailersTestCase):
    """
    post_office reads its configuration from POST_OFFICE, never from mailer
    OPTIONS. These tests pin that decision. ``mailers`` is used directly rather
    than ``connections`` so nothing here dispatches through the queue backend.
    """

    @override_settings(MAILERS={'default': {'BACKEND': POST_OFFICE_BACKEND}})
    def test_post_office_mailer_without_options(self):
        from django.core.mail import mailers

        self.assertIsInstance(mailers['default'], PostOfficeEmailBackend)
        send_mail('Test', 'Message', 'from@example.com', ['to@example.com'])
        self.assertEqual(Email.objects.latest('id').status, STATUS.queued)

    @override_settings(MAILERS={'default': {'BACKEND': POST_OFFICE_BACKEND, 'OPTIONS': {}}})
    def test_post_office_mailer_with_empty_options(self):
        from django.core.mail import mailers

        self.assertIsInstance(mailers['default'], PostOfficeEmailBackend)

    @override_settings(MAILERS={'default': {'BACKEND': POST_OFFICE_BACKEND, 'OPTIONS': {'default_priority': 'now'}}})
    def test_post_office_mailer_rejects_options(self):
        from django.core.mail import InvalidMailer, mailers

        with self.assertRaises(InvalidMailer):
            mailers['default']


class DeliveryMailerTest(MailersTestCase):
    """
    A MAILERS alias pointing at post_office's queue backend cannot deliver; the
    worker must be redirected to POST_OFFICE['DEFAULT_MAILER'] and every
    redirect target that would still recurse must be rejected.
    """

    @override_settings(
        MAILERS={'default': {'BACKEND': POST_OFFICE_BACKEND}, 'locmem': {'BACKEND': LOCMEM}},
        POST_OFFICE=post_office_config(DEFAULT_MAILER='locmem'),
    )
    def test_delivers_through_default_mailer(self):
        # An explicit request for the queue alias is redirected to DEFAULT_MAILER
        self.assertIsInstance(connections['default'], mail.backends.locmem.EmailBackend)

        # An unaliased email resolves DEFAULT_MAILER directly, never touching the queue backend
        send_mail('Test', 'Message', 'from@example.com', ['to@example.com'])
        email = Email.objects.get()
        self.assertEqual(email.status, STATUS.queued)
        with mock.patch.object(PostOfficeEmailBackend, '__init__', side_effect=AssertionError('queue constructed')):
            email.dispatch()
        self.assertEqual(email.status, STATUS.sent)
        self.assertEqual(len(mail.outbox), 1)

        # An email explicitly aliased to the queue is delivered too, not requeued
        email = send(
            recipients=['to@example.com'], sender='from@example.com', subject='s', message='m', backend='default'
        )
        email.dispatch()
        self.assertEqual(email.status, STATUS.sent)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(Email.objects.count(), 2)

    @override_settings(
        MAILERS={'default': {'BACKEND': 'post_office.backends.EmailBackend'}, 'locmem': {'BACKEND': LOCMEM}},
        POST_OFFICE=post_office_config(DEFAULT_MAILER='locmem'),
    )
    def test_equivalent_backend_path_redirects(self):
        self.assertIsInstance(connections['default'], mail.backends.locmem.EmailBackend)

    @override_settings(
        MAILERS={'default': {'BACKEND': POST_OFFICE_BACKEND}},
        POST_OFFICE=post_office_config(DEFAULT_MAILER='default'),
    )
    def test_direct_self_reference(self):
        from django.core.mail import InvalidMailer

        with self.assertRaises(InvalidMailer) as ctx:
            connections['default']
        self.assertIn("'default'", str(ctx.exception))
        self.assertIn('DEFAULT_MAILER', str(ctx.exception))

    @override_settings(
        MAILERS={'default': {'BACKEND': POST_OFFICE_BACKEND}, 'queue2': {'BACKEND': POST_OFFICE_BACKEND}},
        POST_OFFICE=post_office_config(DEFAULT_MAILER='queue2'),
    )
    def test_indirect_self_reference(self):
        from django.core.mail import InvalidMailer

        with self.assertRaises(InvalidMailer) as ctx:
            connections['default']
        self.assertIn("'default'", str(ctx.exception))
        self.assertIn("'queue2'", str(ctx.exception))

    @override_settings(
        MAILERS={
            'default': {'BACKEND': POST_OFFICE_BACKEND},
            'queue2': {'BACKEND': 'tests.test_mailers.QueueSubclassBackend'},
        },
        POST_OFFICE=post_office_config(DEFAULT_MAILER='queue2'),
    )
    def test_subclass_delivery_mailer_is_rejected(self):
        from django.core.mail import InvalidMailer

        with self.assertRaises(InvalidMailer) as ctx:
            connections['default']
        self.assertIn("'queue2'", str(ctx.exception))

    @override_settings(
        MAILERS={'default': {'BACKEND': POST_OFFICE_BACKEND}},
        POST_OFFICE=post_office_config(DEFAULT_MAILER='nope'),
    )
    def test_missing_delivery_mailer(self):
        from django.core.mail import InvalidMailer, MailerDoesNotExist

        with self.assertRaises(InvalidMailer) as ctx:
            connections['default']
        self.assertIn("'nope'", str(ctx.exception))
        self.assertIn('DEFAULT_MAILER', str(ctx.exception))
        self.assertIsInstance(ctx.exception.__cause__, MailerDoesNotExist)

    @override_settings(MAILERS={'default': {'BACKEND': POST_OFFICE_BACKEND}})
    def test_unset_default_mailer(self):
        # DEFAULT_MAILER falls back to 'default', which is the queue itself.
        from django.core.mail import InvalidMailer

        self.assertNotIn('DEFAULT_MAILER', settings.POST_OFFICE)
        with self.assertRaises(InvalidMailer) as ctx:
            connections['default']
        self.assertIn("'default'", str(ctx.exception))
        self.assertIn('DEFAULT_MAILER', str(ctx.exception))
