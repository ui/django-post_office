import time
import os

from django.test import TestCase

from ..lockfile import FileLock, FileLocked


class LockTest(TestCase):

    def test_process_killed_force_unlock(self):
        lockfile = 'test.txt.lock'
        with open(lockfile, 'w+') as f:
            f.write('9999999')
        assert os.path.exists(lockfile)
        with FileLock('test.txt'):
            assert True

    def test_force_unlock_in_same_process(self):
        lockfile = 'test.txt.lock'
        with open(lockfile, 'w+') as f:
            f.write(str(os.getpid()))

        with FileLock('test.txt', force=True):
            assert True

    def test_exception_after_timeout(self):
        lockfile = 'test.txt.lock'
        with open(lockfile, 'w+') as f:
            f.write(str(os.getpid()))

        try:
            with FileLock('test.txt', timeout=1):
                assert False
        except FileLocked:
            assert True

    def test_force_after_timeout(self):
        lockfile = 'test.txt.lock'
        with open(lockfile, 'w+') as f:
            f.write(str(os.getpid()))

        timeout = 1
        start = time.time()
        with FileLock('test.txt', timeout=timeout, force=True):
            assert True
        end = time.time()
        assert end - start > timeout
