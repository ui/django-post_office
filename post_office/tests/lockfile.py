import time
import os

from django.test import TestCase

from ..lockfile import FileLock, FileLocked


def setup_fake_lock(lock_file_name):
    pid = os.getpid()
    lockfile = '%s.lock' % pid
    try:
        os.remove('test.txt.lock')
    except OSError:
        pass
    os.symlink(lockfile, 'test.txt.lock')


class LockTest(TestCase):

    def test_process_killed_force_unlock(self):
        pid = os.getpid()
        lockfile = '%s.lock' % pid
        setup_fake_lock('test.txt.lock')

        with open(lockfile, 'w+') as f:
            f.write('9999999')
        assert os.path.exists(lockfile)
        with FileLock('test.txt'):
            assert True

    def test_force_unlock_in_same_process(self):
        pid = os.getpid()
        lockfile = '%s.lock' % pid
        os.symlink(lockfile, 'test.txt.lock')

        with open(lockfile, 'w+') as f:
            f.write(str(os.getpid()))

        with FileLock('test.txt', force=True):
            assert True

    def test_exception_after_timeout(self):
        pid = os.getpid()
        lockfile = '%s.lock' % pid
        setup_fake_lock('test.txt.lock')

        with open(lockfile, 'w+') as f:
            f.write(str(os.getpid()))

        try:
            with FileLock('test.txt', timeout=1):
                assert False
        except FileLocked:
            assert True

    def test_force_after_timeout(self):
        pid = os.getpid()
        lockfile = '%s.lock' % pid
        setup_fake_lock('test.txt.lock')

        with open(lockfile, 'w+') as f:
            f.write(str(os.getpid()))

        timeout = 1
        start = time.time()
        with FileLock('test.txt', timeout=timeout, force=True):
            assert True
        end = time.time()
        assert end - start > timeout

    def test_get_lock_pid(self):
        """Ensure get_lock_pid() works properly"""
        with FileLock('test.txt', timeout=1, force=True) as lock:
            self.assertEqual(lock.get_lock_pid(), int(os.getpid()))
