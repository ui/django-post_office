import threading

from django.core.mail import get_connection

from .settings import get_backend


# Copied from Django 1.8's django.core.cache.CacheHandler
class ConnectionHandler:
    """
    A Cache Handler to manage access to Cache instances.

    Ensures only one instance of each alias exists per thread. The registry is
    a process-wide dict keyed by (thread_ident, alias) rather than threading.local
    so close() called from one thread can reach and close connections opened by
    worker threads — otherwise SMTP sockets opened inside a ThreadPool worker
    would leak when _send_bulk closes from the main thread.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._connections = {}

    def __getitem__(self, alias):
        key = (threading.get_ident(), alias)
        with self._lock:
            connection = self._connections.get(key)
        if connection is not None:
            return connection

        try:
            backend = get_backend(alias)
        except KeyError:
            raise KeyError('%s is not a valid backend alias' % alias)

        connection = get_connection(backend)
        connection.open()
        with self._lock:
            self._connections[key] = connection
        return connection

    def all(self):
        with self._lock:
            return list(self._connections.values())

    def close(self):
        with self._lock:
            connections = list(self._connections.values())
            # Evict closed connections so the next __getitem__ reopens them.
            # Keeping closed connections cached breaks backends (e.g. Amazon SES)
            # whose close() nulls out internal clients — subsequent batches would
            # hand workers a dead connection and race inside send_messages.
            self._connections.clear()
        for connection in connections:
            connection.close()


connections = ConnectionHandler()
