import time
from datetime import timedelta
from multiprocessing import Process, Value

from django.db import connection
from django.test import TransactionTestCase

from post_office.dblock import db_lock, TimeoutException, LockedException
from post_office.models import DBMutex


class LockTest(TransactionTestCase):
    def setUp(self):
        if connection.vendor == 'sqlite':
            cursor = connection.cursor()
            cursor.execute('PRAGMA journal_mode=WAL;')
            cursor.execute('PRAGMA synchronous=FULL;')

    def t_est_lock_expires_by_itself(self):
        with self.assertRaises(TimeoutException):
            with db_lock('test_dblock', timedelta(seconds=1)) as lock:
                self.assertTrue(DBMutex.objects.filter(locked_by=lock.locked_by, lock_id=lock.lock_id).exists())
                time.sleep(1.001)  # task runs too long
        self.assertFalse(DBMutex.objects.filter(locked_by=lock.locked_by, lock_id=lock.lock_id).exists())

    def t_est_aquire_and_release_locks(self):
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

    def t_est_lock_using_decorator(self):
        @db_lock('test_dblock', timedelta(seconds=1))
        def func(sleep_time):
            time.sleep(sleep_time)
            return 'some result'

        self.assertEqual(func(0.2), 'some result')
        with self.assertRaises(TimeoutException):
            func(2.0)

    def t_est_refuse_to_lock_from_concurrent_task(self):
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

    def t_est_wait_for_lock_in_concurrent_task(self):
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
        def concurrent_task():
            print(f"Locking concurrent {time.monotonic() - time_stamp}")
            with self.assertRaises(TimeoutException):
                with db_lock('test_dblock', timedelta(seconds=1)):
                    print(f"Locked concurrent {time.monotonic() - time_stamp}")
                    time.sleep(2)
            self.assertGreater(time.monotonic() - time_stamp, 1)
            self.assertLess(time.monotonic() - time_stamp, 2)
            print(f"Unlocked concurrent {time.monotonic() - time_stamp}")

        print("===================================")
        time_stamp = time.monotonic()
        proc = Process(target=concurrent_task)
        proc.start()
        time.sleep(0.5)
        print(f"Running main {time.monotonic() - time_stamp}")
        with self.assertRaises(LockedException):
            db_lock('test_dblock', timedelta(seconds=1)).acquire()
        print(f"Locked main {time.monotonic() - time_stamp}")
        time.sleep(1)
        with db_lock('test_dblock', timedelta(seconds=1)) as lock:
            print(f"Locked main {time.monotonic() - time_stamp}")
            self.assertTrue(DBMutex.objects.filter(locked_by=lock.locked_by, lock_id=lock.lock_id).exists())
        self.assertFalse(DBMutex.objects.filter(locked_by=lock.locked_by, lock_id=lock.lock_id).exists())
        print(f"Unlocked main {time.monotonic() - time_stamp}")
        proc.join()

    # def t_est_allow_to_lock_again(self):
    #     with db_lock('test_dblock', timedelta(seconds=1)) as lock:
    #         self.assertTrue(DBMutex.objects.filter(locked_by=lock.locked_by, lock_id=lock.lock_id).exists())
    #         time.sleep(0.25)
    #     self.assertFalse(DBMutex.objects.filter(locked_by=lock.locked_by, lock_id=lock.lock_id).exists())
    #     with db_lock('test_dblock', timedelta(seconds=1)) as lock:
    #         self.assertLess(lock.remaining_time, timedelta(seconds=1))
    #         self.assertGreater(lock.remaining_time, timedelta(milliseconds=900))
    #         self.assertTrue(DBMutex.objects.filter(locked_by=lock.locked_by, lock_id=lock.lock_id).exists())
    #     self.assertFalse(DBMutex.objects.filter(locked_by=lock.locked_by, lock_id=lock.lock_id).exists())
    #
    # def t_est_locks_not_interfering(self):
    #     with db_lock('test_dblock1', timedelta(seconds=1)) as lock1:
    #         self.assertTrue(DBMutex.objects.filter(locked_by=lock1.locked_by, lock_id=lock1.lock_id).exists())
    #     with db_lock('test_dblock2', timedelta(seconds=1)) as lock2:
    #         self.assertTrue(DBMutex.objects.filter(locked_by=lock2.locked_by, lock_id=lock2.lock_id).exists())
    #     self.assertFalse(DBMutex.objects.filter(locked_by=lock1.locked_by, lock_id=lock1.lock_id).exists())
    #     self.assertFalse(DBMutex.objects.filter(locked_by=lock2.locked_by, lock_id=lock2.lock_id).exists())

    # def test_process_killed_force_unlock(self):
    #     pid = os.getpid()
    #     lockfile = '%s.lock' % pid
    #     setup_fake_lock('test.lock')
    #
    #     with open(lockfile, 'w+') as f:
    #         f.write('9999999')
    #     assert os.path.exists(lockfile)
    #     with FileLock('test'):
    #         assert True
    #
    # def test_force_unlock_in_same_process(self):
    #     pid = os.getpid()
    #     lockfile = '%s.lock' % pid
    #     os.symlink(lockfile, 'test.lock')
    #
    #     with open(lockfile, 'w+') as f:
    #         f.write(str(os.getpid()))
    #
    #     with FileLock('test', force=True):
    #         assert True
    #
    # def test_exception_after_timeout(self):
    #     pid = os.getpid()
    #     lockfile = '%s.lock' % pid
    #     setup_fake_lock('test.lock')
    #
    #     with open(lockfile, 'w+') as f:
    #         f.write(str(os.getpid()))
    #
    #     try:
    #         with FileLock('test', timeout=1):
    #             assert False
    #     except FileLocked:
    #         assert True
    #
    # def test_force_after_timeout(self):
    #     pid = os.getpid()
    #     lockfile = '%s.lock' % pid
    #     setup_fake_lock('test.lock')
    #
    #     with open(lockfile, 'w+') as f:
    #         f.write(str(os.getpid()))
    #
    #     timeout = 1
    #     start = time.time()
    #     with FileLock('test', timeout=timeout, force=True):
    #         assert True
    #     end = time.time()
    #     assert end - start > timeout
    #
    # def test_get_lock_pid(self):
    #     """Ensure get_lock_pid() works properly"""
    #     with FileLock('test', timeout=1, force=True) as lock:
    #         self.assertEqual(lock.get_lock_pid(), int(os.getpid()))
