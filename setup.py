#!/usr/bin/env python

from distutils.core import setup

setup(
    name='defender',
    version='0.1.0',
    url='https://github.com/dfrtz/project-defender',
    license='Apache Software License',
    author='David Fritz',
    tests_require=['pytest'],
    install_requires=[],
    description='Home Defense Device Manager with REST API',
    packages=['defender'],
    platforms='Linux',
    classifiers = [
        'Programming Language :: Python',
        'Development Status :: 4 - Beta',
        'Natural Language :: English',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX',
        'Topic :: Office/Business',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
    ],
)
