import importlib
from unittest import mock, skipUnless

from django.db import transaction
from django.test import TransactionTestCase
from django.test.utils import override_settings

try:
    import celery  # noqa: F401
except ImportError:
    celery = None


@override_settings(
    POST_OFFICE={
        'BACKENDS': {
            'default': 'django.core.mail.backends.dummy.EmailBackend',
        },
        'CELERY_ENABLED': True,
    }
)
@skipUnless(celery is not None, 'celery is not installed')
class QueuedMailHandlerCeleryTests(TransactionTestCase):
    """
    CELERY_ENABLED + an open transaction must not dispatch send_queued_mail
    until commit (ATOMIC_REQUESTS race; see #518).
    """

    def _reload_celery_tasks(self):
        import post_office.tasks as tasks

        return importlib.reload(tasks)

    def test_send_queued_mail_delay_waits_for_commit(self):
        tasks = self._reload_celery_tasks()
        self.assertTrue(hasattr(tasks, 'send_queued_mail'))

        with mock.patch.object(tasks.send_queued_mail, 'delay') as delay:
            with transaction.atomic():
                tasks.queued_mail_handler(sender=None)
                delay.assert_not_called()
            delay.assert_called_once_with()

    def test_send_queued_mail_delay_runs_without_atomic(self):
        tasks = self._reload_celery_tasks()

        with mock.patch.object(tasks.send_queued_mail, 'delay') as delay:
            tasks.queued_mail_handler(sender=None)
            delay.assert_called_once_with()
