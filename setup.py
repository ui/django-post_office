from ast import literal_eval
import sys
from os.path import dirname, join
from setuptools import setup
from setuptools.command.test import test as TestCommand


class Tox(TestCommand):
    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.tox_args = None

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import tox
        import shlex

        args = self.tox_args
        if args:
            args = shlex.split(self.tox_args)
        errno = tox.cmdline(args=args)
        sys.exit(errno)


with open(join(dirname(__file__), 'post_office/version.txt')) as fh:
    VERSION = '.'.join(map(str, literal_eval(fh.read())))

TESTS_REQUIRE = ['tox >= 2.3']


setup(
    name='django-post_office',
    version=VERSION,
    author='Selwin Ong',
    author_email='selwin.ong@gmail.com',
    packages=['post_office'],
    url='https://github.com/ui/django-post_office',
    license='MIT',
    description='A Django app to monitor and send mail asynchronously, complete with template support.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    zip_safe=False,
    include_package_data=True,
    package_data={'': ['README.rst']},
    python_requires='>=3.9',
    install_requires=[
        'bleach[css]',
        'django>=4.2',
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 4.2',
        'Framework :: Django :: 5.0',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Topic :: Communications :: Email',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    tests_require=TESTS_REQUIRE,
    extras_require={
        'test': TESTS_REQUIRE,
        'prevent-XSS': ['bleach'],
    },
    cmdclass={'test': Tox},
)
