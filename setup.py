#!/usr/bin/env python

import glob
import os
import setuptools

MODULE_DIR = os.path.dirname(__file__)
REQUIREMENTS_FILE = os.path.join(MODULE_DIR, 'requirements.txt')


def _find_files(directory: str) -> list:
    """Locate non-python package files in compatible format with setuptools."""
    paths = []
    for (path, _, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join(MODULE_DIR, path, filename))
    return paths


def _find_requirements(file: str) -> list:
    """Import requirements from an external file in compatible format with setuptools."""
    with open(file, 'rt') as requirements_file:
        requirements = [requirement.strip() for requirement in requirements_file.readlines()]
    return requirements


def _find_scripts(directory: str) -> list:
    """Locate scripts and provide endpoint names compatible with setuptools."""
    scripts = []
    for abs_path in glob.glob(os.path.join(MODULE_DIR, f'{directory}/*.py')):
        filename = os.path.basename(abs_path).rstrip('.py')
        if not filename.startswith('__'):
            scripts.append('{} = defender.scripts.{}:main'.format(filename, filename))
    return scripts


PACKAGE_DATA = {
    '': [
        *_find_files('defender/demodata'),
        *_find_files('defender/html')
    ]
}
PACKAGES = setuptools.find_packages(MODULE_DIR, include=['defender*'], exclude=['*test', '*benchmarks'])


setuptools.setup(
    name='defender',
    version='0.1.0',
    url='https://github.com/dfrtz/project-defender',
    license='Apache Software License',
    author='David Fritz',
    tests_require=['pytest'],
    install_requires=_find_requirements(REQUIREMENTS_FILE),
    description='Security and Defense Device Manager with REST API',
    packages=['defender'],
    platforms='Linux',
    python_requires='>=3.6',
    entry_points={
        'console_scripts': _find_scripts('defender/scripts')
    },
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

