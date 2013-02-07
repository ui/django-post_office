# -*- coding: utf-8 -*-
from setuptools import setup

setup(
    name='django-post_office',
    version='0.2.1',
    author='Selwin Ong',
    author_email='selwin.ong@gmail.com',
    packages=['post_office'],
    url='https://github.com/ui/django-post_office',
    license='MIT',
    description='A Django app that allows you to log email activities and send mail asynchronously, complete with template support.',
    long_description=open('README.rst').read(),
    zip_safe=False,
    include_package_data=True,
    package_data = { '': ['README.rst'] },
    install_requires=['django>=1.2'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
