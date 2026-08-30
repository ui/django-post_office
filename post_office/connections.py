from threading import local

from django.core.mail import get_connection

from .settings import get_backend, mailers_are_configured


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
            # Django >= 6.1 only; keep the import lazy so older versions import cleanly.
            from django.core.mail import mailers

            # MailerDoesNotExist is a KeyError subclass, so existing handlers keep
            # working while callers get the MAILERS-aware error.
            connection = mailers[alias]
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
