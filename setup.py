"""Setup configuration and dependencies for the textology library."""

import os
from pathlib import Path

from setuptools import find_packages
from setuptools import setup

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))


def _find_version(module_path: str, file: str = "__init__.py") -> str:
    """Locate semantic version from a text file in a compatible format with setuptools."""
    # Do not import the module within the library, as this can cause an infinite import. Read manually.
    init_file = os.path.join(ROOT_DIR, module_path, file)
    with open(init_file, "rt", encoding="utf-8") as file_in:
        for line in file_in.readlines():
            if "__version__" in line:
                # Example:
                # __version__ = "1.2.3" -> 1.2.3
                version = line.split()[2].replace('"', "")
    return version


def read_requirements_file(extra_type: str | None) -> list[str]:
    """Read local requirement file basic on the type."""
    extra_type = f"-{extra_type}" if extra_type else ""
    with open(f"requirements{extra_type}.txt", encoding="utf-8") as input_file:
        lines = (line.strip() for line in input_file)
        return [req for req in lines if req and not req.startswith("#")]


setup(
    name="defender",
    description="Security and Defense Device Manager with REST API",
    long_description=Path("README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    version=_find_version("defender"),
    author="David Fritz",
    url="https://github.com/dfrtz/project-defender",
    project_urls={
        "Issue Tracker": "https://github.com/dfrtz/project-defender/issues",
        "Source Code": "https://github.com/dfrtz/project-defender",
    },
    license="Apache Software License",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Environment :: Web",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Software Development",
        "Topic :: Scientific/Engineering",
        "Typing :: Typed",
        "Operating System :: POSIX :: Linux",
    ],
    platforms=[
        "Linux",
    ],
    test_suite="pytest",
    packages=find_packages(ROOT_DIR, include=["defender*"], exclude=["*test", "tests*"]),
    include_package_data=True,
    python_requires=">=3.6",
    install_requires=read_requirements_file(None),
    extras_require={
        "dev": [
            *read_requirements_file(None),
            *read_requirements_file("dev"),
        ],
    },
    entry_points={
        "console_scripts": [
            "defend = defender.scripts.defend:main",
        ]
    },
)
