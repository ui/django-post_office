# -*- coding: utf-8 -*-
from setuptools import setup

setup(
    name='django-post_office',
    version='2.0.2',
    author='Selwin Ong',
    author_email='selwin.ong@gmail.com',
    packages=['post_office'],
    url='https://github.com/ui/django-post_office',
    license='MIT',
    description='A Django app to monitor and send mail asynchronously, complete with template support.',
    long_description=open('README.rst').read(),
    zip_safe=False,
    include_package_data=True,
    package_data={'': ['README.rst']},
    install_requires=['django>=1.4', 'jsonfield'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
