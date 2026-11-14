"""Signal handling for explicitly configured task dispatchers."""

import inspect

from django.core.exceptions import ImproperlyConfigured
from django.db import transaction

from .settings import get_task_dispatcher


def queued_mail_handler(sender, **kwargs):
    """Enqueue queue processing after commit, using one selected dispatcher."""
    dispatcher = get_task_dispatcher()
    if dispatcher is not None:

        def enqueue():
            result = dispatcher()
            if inspect.isawaitable(result) or inspect.isgenerator(result) or inspect.isasyncgen(result):
                if inspect.iscoroutine(result) or inspect.isgenerator(result):
                    result.close()
                raise ImproperlyConfigured(
                    'POST_OFFICE TASK_DISPATCHER returned an awaitable or generator; '
                    'it must enqueue work synchronously.'
                )

        emails = kwargs.get('emails') or ()
        using = kwargs.get('using') or (emails[0]._state.db if emails else None)
        transaction.on_commit(enqueue, using=using)
