import os
import sys

# fix sys path so we don't need to setup PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))


from django.conf import settings


settings.configure(
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
        },
    },
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'TIMEOUT': 36000,
            'KEY_PREFIX': 'post-office',
        },
        'post_office': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'TIMEOUT': 36000,
            'KEY_PREFIX': 'post-office',
        }
    },
    INSTALLED_APPS = (
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'post_office',
    ),
    DEFAULT_FROM_EMAIL='default@example.com',
    ROOT_URLCONF = 'post_office.test_urls',
    TEST_RUNNER = 'django.test.simple.DjangoTestSuiteRunner',
)

from django.test.utils import get_runner

def usage():
    return """
    Usage: python runtests.py [UnitTestClass].[method]

    You can pass the Class name of the `UnitTestClass` you want to test.

    Append a method name if you only want to test a specific method of that class.
    """


def main():
    TestRunner = get_runner(settings)

    test_runner = TestRunner()
    if len(sys.argv) == 2:
        test_case = '.' + sys.argv[1]
    elif len(sys.argv) == 1:
        test_case = ''
    else:
        print(usage())
        sys.exit(1)
    failures = test_runner.run_tests(['post_office'])

    sys.exit(failures)

if __name__ == '__main__':
    main()
