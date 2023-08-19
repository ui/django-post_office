import atexit
from datetime import timedelta
import signal
import time
from uuid import uuid4

from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError, DatabaseError
from django.utils.timezone import now

from post_office.models import DBMutex


class LockedException(Exception):
    pass


class TimeoutException(Exception):
    pass


class db_lock:
    """
    An entity that can lock a shared resource and release it through database locking.
    Locks can be acquired by different hosts, since the source of truth is handled by the database.

    Usage:

    ```
    # Lock a critical section of code
    with db_lock('my_lock', timedelta(seconds=30)):
        do_something()
    ```
    The section inside the ``with`` statement will run for a maximum of 30 seconds. If that
    time elapses before leaving the block, a ``TimeoutException`` is raised.

    If another process attempts to run a critical section of code, using the same resource
    identifier while the above block is running, a ``LockedException`` is raised.

    ```
    # Blocking variant of the above
    with db_lock('my_lock', wait=True):
        do_something()
    ```
    By using the parameter ``wait=True``, the critical section of code is only entered after
    mutexes from other processes have been released. A ``LockedException`` will not be raised.

    ```
    # Running critical section until it expires
    with db_lock('my_lock') as lock:
        while lock.remaining_time > timedelta(seconds=1):
            do_something()  # never requires more than one second
    ```
    By querying the remaining time left over for the acquisition of the lock, one can
    avoid a ``TimeoutException`` to be raised.

    ```
    # Use a decorator to mark a whole function as critical
    @db_lock('my_lock')
    def do_something():
        # do somethinge here
    ```
    This function may raise a ``LockedException`` or a ``TimeoutException``.

    ```
    # Lock critical section of code explicitly
    lock = db_lock('my_lock')
    lock.acquire()
    do_something()
    lock.release()
    ```
    A lock can also be acquired and released explicitly. This is error-prone, because it relies
    upon releasing the lock.
    """
    GRANULARITY = timedelta(milliseconds=100)
    locked_by = uuid4()

    def __init__(self, lock_id, timeout=timedelta(minutes=1), wait=False):
        self.lock_id = lock_id[:50]
        if not isinstance(timeout, timedelta):
            raise ValueError("DB lock timeout must be of type timedelta.")
        if timeout < self.GRANULARITY:
            raise ImproperlyConfigured("DB lock timeout must be at least {}.".format(self.GRANULARITY))
        self.timeout = timeout
        self.wait = wait
        self._mutex = None

    def __call__(self, func):
        return self._decorate(func)

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, type, value, traceback):
        self.release()

    @property
    def remaining_time(self):
        """
        @:return: The remaining time until this lock expires.
        """
        return self._mutex.expires_at - now()

    def acquire(self):
        """
        Aquires a mutual exclusive lock in the database.
        """
        def stop_on_alarm(*args):
            raise TimeoutException()

        signal.signal(signal.SIGALRM, stop_on_alarm)
        granularity = self.GRANULARITY.total_seconds()
        while self.wait:
            # the following call may block, until lock is released by another process
            mutex = DBMutex.objects.filter(lock_id=self.lock_id, expires_at__gt=now()).first()
            while mutex:
                remaining = mutex.expires_at - now()
                time.sleep(remaining.total_seconds() if remaining < self.GRANULARITY else granularity)
                try:
                    mutex.refresh_from_db()
                except DBMutex.DoesNotExist:
                    mutex = None
            try:
                self._mutex = DBMutex.objects.create(
                    lock_id=self.lock_id, locked_by=self.locked_by, expires_at=now() + self.timeout)
                break
            except IntegrityError:  # NOQA
                # very rare: other process acquired a lock between exiting inner loop and
                # creating DBMutex object
                continue
        else:
            try:
                self._mutex = DBMutex.objects.create(
                    lock_id=self.lock_id, locked_by=self.locked_by, expires_at=now() + self.timeout)
            except IntegrityError:
                raise LockedException("DB mutex for {} is locked.".format(self.lock_id))

        # install a timeout handler, in case the lock expires before being released
        signal.setitimer(signal.ITIMER_REAL, (self._mutex.expires_at - now()).total_seconds())

    def release(self):
        """
        Release a lock previously acquired.
        """
        if self._mutex:
            signal.setitimer(signal.ITIMER_REAL, 0)
            self._mutex.delete()
            self._mutex = None

    def _decorate(self, func):
        def wrapper(*args, **kwargs):
            with self:
                 result = func(*args, **kwargs)
            return result
        return wrapper

    @classmethod
    def _release_all_locks(cls):
        """
        Release all locks assigned to the running instance.
        """
        try:
            DBMutex.objects.filter(locked_by=cls.locked_by).delete()
        except DatabaseError:
            pass


atexit.register(db_lock._release_all_locks)
