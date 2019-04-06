#!/usr/bin/env python3

import glob
import os
import setuptools

MODULE_DIR = os.path.dirname(__file__)
PACKAGES = setuptools.find_packages(MODULE_DIR, include=['defender*'], exclude=['*test', '*benchmarks'])
REQUIREMENTS_FILE = os.path.join(MODULE_DIR, 'requirements.txt')
with open(REQUIREMENTS_FILE, 'rt') as requirements_file:
    REQUIREMENTS = [requirement.strip() for requirement in requirements_file.readlines()]


def _find_files(directory):
    """Locate non-python package files in compatible format with setuptools."""
    paths = []
    for (path, _, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join(MODULE_DIR, path, filename))
    return paths


def _find_scripts(directory):
    """Locate scripts and provide endpoint names compatible with setuptools."""
    scripts = []
    for abs_path in glob.glob(os.path.join(MODULE_DIR, f'{directory}/*.py')):
        filename = os.path.basename(abs_path).rstrip('.py')
        if not filename.startswith('__'):
            scripts.append('{} = defender.scripts.{}:main'.format(filename, filename))
    return scripts


ENTRY_POINTS = _find_scripts('defender/scripts')
PACKAGE_DATA = {
    '': [
        *_find_files('defender/demodata'),
        *_find_files('defender/html')
    ]
}


setuptools.setup(
    name='defender',
    version='0.1.0',
    url='https://github.com/dfrtz/project-defender',
    license='Apache Software License',
    author='David Fritz',
    tests_require=['pytest'],
    install_requires=REQUIREMENTS,
    description='Security and Defense Device Manager with REST API',
    packages=['defender'],
    platforms='Linux',
    python_requires='>=3.5',
    entry_points={'console_scripts': ENTRY_POINTS},
    classifiers=[
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
