import time
from datetime import timedelta
from multiprocessing import Process, Queue, Value

from django.db import connection
from django.test import TransactionTestCase

from post_office.dblock import db_lock, TimeoutException, LockedException
from post_office.models import DBMutex


class LockTest(TransactionTestCase):
    def setUp(self):
        if connection.vendor == 'XXXsqlite':
            cursor = connection.cursor()
            cursor.execute('PRAGMA journal_mode=WAL;')
            cursor.execute('PRAGMA synchronous=FULL;')

    def test_lock_expires_by_itself(self):
        with self.assertRaises(TimeoutException):
            with db_lock('test_dblock', timedelta(seconds=1)) as lock:
                self.assertTrue(DBMutex.objects.filter(locked_by=lock.locked_by, lock_id=lock.lock_id).exists())
                time.sleep(1.001)  # task runs too long
        self.assertFalse(DBMutex.objects.filter(locked_by=lock.locked_by, lock_id=lock.lock_id).exists())

    def test_aquire_and_release_locks(self):
        lock1 = db_lock('test_dblock', timedelta(seconds=1))
        self.assertFalse(DBMutex.objects.filter(locked_by=lock1.locked_by, lock_id=lock1.lock_id).exists())
        lock1.acquire()
        self.assertTrue(DBMutex.objects.filter(locked_by=lock1.locked_by, lock_id=lock1.lock_id).exists())
        lock2 = db_lock('test_dblock', timedelta(seconds=1))
        with self.assertRaises(LockedException):
            lock2.acquire()
        lock1.release()
        self.assertFalse(DBMutex.objects.filter(locked_by=lock1.locked_by, lock_id=lock1.lock_id).exists())
        lock2.acquire()
        lock3 = db_lock('test_dblock3', timedelta(seconds=60))
        lock3.acquire()
        self.assertTrue(DBMutex.objects.filter(locked_by=lock3.locked_by, lock_id=lock3.lock_id).exists())
        self.assertTrue(DBMutex.objects.filter(locked_by=lock2.locked_by, lock_id=lock2.lock_id).exists())
        lock2.release()
        self.assertTrue(DBMutex.objects.filter(locked_by=db_lock.locked_by).exists())
        lock3.release()
        self.assertFalse(DBMutex.objects.filter(locked_by=db_lock.locked_by).exists())

    def test_lock_using_decorator(self):
        @db_lock('test_dblock', timedelta(seconds=1))
        def func(sleep_time):
            time.sleep(sleep_time)
            return 'some result'

        self.assertEqual(func(0.2), 'some result')
        with self.assertRaises(TimeoutException):
            func(2.0)

    def test_refuse_to_lock_from_concurrent_task(self):
        def concurrent_task():
            print(f"Locking concurrent {time.monotonic() - time_stamp}")
            with self.assertRaises(LockedException):
                with db_lock('test_dblock', timedelta(seconds=1)):
                    pass

        time_stamp = time.monotonic()
        proc = Process(target=concurrent_task)
        proc.start()
        print(f"Locking main {time.monotonic() - time_stamp}")
        with db_lock('test_dblock', timedelta(seconds=1)) as lock:
            print(f"Locked main {time.monotonic() - time_stamp}")
            self.assertTrue(DBMutex.objects.filter(locked_by=lock.locked_by, lock_id=lock.lock_id).exists())
            time.sleep(0.5)
            print(f"Unlocked main {time.monotonic() - time_stamp}")
        proc.join()

    def test_wait_for_lock_in_concurrent_task(self):
        def concurrent_task(mutex_id):
            print(f"Locking concurrent {time.monotonic() - time_stamp}")
            with db_lock('test_dblock', timedelta(seconds=1), wait=True) as lock:
                print(f"Locked concurrent {time.monotonic() - time_stamp}")
                self.assertGreater(time.monotonic() - time_stamp, 0.5)
                self.assertLess(time.monotonic() - time_stamp, 1.5)
                mutex_id.value = DBMutex.objects.get(locked_by=lock.locked_by, lock_id=lock.lock_id).id

        print("===================================")
        time_stamp = time.monotonic()
        mutex_id = Value('i', 0)
        proc = Process(target=concurrent_task, args=(mutex_id,))
        proc.start()
        print(f"Locking main {time.monotonic() - time_stamp}")
        with db_lock('test_dblock', timedelta(seconds=1)) as lock:
            print(f"Locked main {time.monotonic() - time_stamp}")
            time.sleep(0.5)
            main_mutex_id = DBMutex.objects.get(locked_by=lock.locked_by, lock_id=lock.lock_id).id
        self.assertFalse(DBMutex.objects.filter(locked_by=lock.locked_by, lock_id=lock.lock_id).exists())
        print(f"Unlocked main {time.monotonic() - time_stamp}")
        print(f"Before joining: {mutex_id.value}")
        proc.join()
        print(f"After joining: {mutex_id.value}")
        self.assertNotEqual(mutex_id.value, main_mutex_id)

    def test_lock_timeout_in_concurrent_task(self):
        def concurrent_task(queue):
            print(f"Locking concurrent {time.monotonic() - time_stamp}")
            with self.assertRaises(TimeoutException):
                with db_lock('test_dblock', timedelta(seconds=1)):
                    queue.put('locked')
                    print(f"Locked concurrent {time.monotonic() - time_stamp}")
                    time.sleep(2)
            self.assertGreater(time.monotonic() - time_stamp, 1)
            self.assertLess(time.monotonic() - time_stamp, 2)
            print(f"Unlocked concurrent {time.monotonic() - time_stamp}")
            queue.put('unlocked')

        print("===================================")
        time_stamp = time.monotonic()
        queue = Queue()
        proc = Process(target=concurrent_task, args=(queue,))
        proc.start()
        while queue.get() != 'locked':
            time.sleep(0.1)
        print(f"Running main {time.monotonic() - time_stamp}")
        with self.assertRaises(LockedException):
            db_lock('test_dblock', timedelta(seconds=1)).acquire()
        while queue.get() != 'unlocked':
            time.sleep(0.1)
        print(f"Locking main {time.monotonic() - time_stamp}")
        with db_lock('test_dblock', timedelta(seconds=1)) as lock:
            print(f"Locked main {time.monotonic() - time_stamp}")
            self.assertTrue(DBMutex.objects.filter(locked_by=lock.locked_by, lock_id=lock.lock_id).exists())
        print(f"Unlocked main {time.monotonic() - time_stamp}")
        proc.join()
        self.assertFalse(DBMutex.objects.filter(locked_by=db_lock.locked_by).exists())
