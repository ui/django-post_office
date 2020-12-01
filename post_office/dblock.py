import atexit

from datetime import timedelta
import signal
import time
from uuid import uuid4

from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError, DatabaseError, transaction
from django.utils.timezone import now

from post_office.models import DBMutex


class LockedException(Exception):
    pass


class TimeoutException(Exception):
    pass


class db_lock:
    """
    An entity that can lock a named resource and release it through database locking.
    """
    GRANULARITY = timedelta(milliseconds=100)
    locked_by = uuid4()

    def __init__(self, lock_id, timeout=timedelta(minutes=1), wait=False):
        self.lock_id = lock_id[:50]
        if not isinstance(timeout, timedelta):
            raise ValueError("DB lock timeout must be of type timedelta.")
        if timeout.total_seconds() < 1:
            raise ImproperlyConfigured("DB lock timeout must be at least one second.")
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
        if self.wait:
            # the following call may block, until lock is released by another process
            mutex = DBMutex.objects.select_for_update().filter(lock_id=self.lock_id, expires_at__gt=now()).first()
            print(f"1 in transaction: {mutex}")
            while mutex:
                remaining_time = mutex.expires_at - now()
                print(f'Remain: {remaining_time}')
                time.sleep(remaining_time.total_seconds() if remaining_time < self.GRANULARITY else self.GRANULARITY.total_seconds())
                try:
                    mutex.refresh_from_db()
                except DBMutex.DoesNotExist:
                    mutex = None
                print(f"2 in transaction: {mutex}")
            self._mutex = DBMutex.objects.create(
                lock_id=self.lock_id, locked_by=self.locked_by, expires_at=now() + self.timeout)
        else:
            try:
                print(f"Creating mutex: ")
                self._mutex = DBMutex.objects.create(
                    lock_id=self.lock_id, locked_by=self.locked_by, expires_at=now() + self.timeout)
                print(self._mutex)
            except IntegrityError:
                raise LockedException("DB mutex for {} is locked.".format(self.lock_id))

        # install a timeout handler, in case the lock expires without being released
        signal.setitimer(signal.ITIMER_REAL, (self._mutex.expires_at - now()).total_seconds())

    def release(self):
        """
        Release a lock previously acquired.
        """
        if self._mutex:
            signal.setitimer(signal.ITIMER_REAL, 0)
            print(f"Releasing: {self._mutex}")
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
