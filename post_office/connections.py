from threading import local

from django.core.mail import get_connection

from .backends import EmailBackend as PostOfficeEmailBackend
from .settings import get_backend, get_default_mailer, mailers_are_configured


def _resolve_mailer(alias):
    """
    Resolve ``alias`` through Django 6.1+ ``settings.MAILERS``.

    A mailer that is itself a post_office queue backend cannot deliver anything:
    sending through it would just enqueue a new Email row, forever. Such aliases
    are redirected to POST_OFFICE['DEFAULT_MAILER'], and every redirect
    target that would still recurse is rejected with an error naming the source
    alias, the delivery alias and the setting to fix.

    The check is ``isinstance`` on the resolved instance, never a match on the
    dotted path, so equivalent paths and user subclasses are all caught.
    """
    # Django >= 6.1 only; keep the import lazy so older versions import cleanly.
    from django.core.mail import InvalidMailer, MailerDoesNotExist, mailers

    # MailerDoesNotExist is a KeyError subclass, so existing handlers keep
    # working while callers get the MAILERS-aware error.
    mailer = mailers[alias]
    if not isinstance(mailer, PostOfficeEmailBackend):
        return mailer

    delivery_alias = get_default_mailer()
    try:
        delivery_mailer = mailers[delivery_alias]
    except MailerDoesNotExist as exc:
        raise InvalidMailer(
            f"Mailer {alias!r} queues to post_office, but POST_OFFICE['DEFAULT_MAILER'] "
            f'({delivery_alias!r}) is not a configured mailer.',
            alias=alias,
        ) from exc
    # Covers a direct self-reference (including DEFAULT_MAILER left unset, which
    # defaults to 'default') and a different alias that also queues.
    if isinstance(delivery_mailer, PostOfficeEmailBackend):
        raise InvalidMailer(
            f"Mailer {alias!r} queues to post_office, and POST_OFFICE['DEFAULT_MAILER'] "
            f'({delivery_alias!r}) also queues to post_office. Set it to a mailer that delivers email.',
            alias=alias,
        )
    return delivery_mailer


# Copied from Django 1.8's django.core.cache.CacheHandler
class ConnectionHandler:
    """
    A Cache Handler to manage access to Cache instances.

    Ensures only one instance of each alias exists per thread.
    """

    def __init__(self):
        self._connections = local()

    def __getitem__(self, alias):
        try:
            return self._connections.connections[alias]
        except AttributeError:
            self._connections.connections = {}
        except KeyError:
            pass

        if mailers_are_configured():
            # Cached under the requested alias: a redirected alias and its delivery
            # alias used directly hold two instances per thread. Accepted trade-off.
            connection = _resolve_mailer(alias)
        else:
            try:
                backend = get_backend(alias)
            except KeyError:
                raise KeyError('%s is not a valid backend alias' % alias)
            connection = get_connection(backend)

        connection.open()
        self._connections.connections[alias] = connection
        return connection

    def all(self):
        return getattr(self._connections, 'connections', {}).values()

    def close(self):
        for connection in self.all():
            connection.close()
        # Evict closed connections so the next __getitem__ reopens them.
        # Keeping closed connections cached breaks backends (e.g. Amazon SES)
        # whose close() nulls out internal clients — subsequent batches would
        # hand workers a dead connection and race inside send_messages.
        self._connections.connections = {}


connections = ConnectionHandler()
