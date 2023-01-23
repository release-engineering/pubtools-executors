# -*- coding: utf-8 -*-

"""setup.py"""

import os
import re
import sys

# import pkg_resources
import sys
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand


class Tox(TestCommand):
    user_options = [("tox-args=", "a", "Arguments to pass to tox")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.tox_args = None

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import tox
        import shlex

        if self.tox_args:
            errno = tox.cmdline(args=shlex.split(self.tox_args))
        else:
            errno = tox.cmdline(self.test_args)
        sys.exit(errno)


def read_content(filepath):
    with open(filepath) as fobj:
        return fobj.read()


classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: Implementation :: CPython",
    "Programming Language :: Python :: Implementation :: PyPy",
]

# same dependency is called "docker-py" in for Python 2.6 and "docker" on newer Python versions
# Thus, it has to be removed from the list of requirements and added under a different name
PY26_BLACKLISTED_DEPENDENCIES = ["docker"]
PY26_EXTRA_DEPENDENCIES = ["docker-py"]

def building_rpm():
    """True when running within RPM build environment, which tweaks
    the build a little."""
    return 'RPM_PACKAGE_VERSION' in os.environ

def get_requirements():
    """
    Transform a list of requirements so that they are usable by older pip (9.0.0), and newer pip

    Regex extracts name and url from a tox-compatible format, and replaces it with only a name
    (which will be combined with dependency_links) or with PEP-508 compatible dependency.
    """
    with open("requirements.txt") as f:
        reqs = f.read().splitlines()
    
    if sys.version_info < (2, 7):
        reqs = [d for d in reqs if d not in PY26_BLACKLISTED_DEPENDENCIES]
        reqs.extend(PY26_EXTRA_DEPENDENCIES)

    # If we are building an RPM, we don't have pip available, and we want
    # to use the 'name + dependency_link' style
    if building_rpm():
        reqs = sorted(list(set(reqs)))
        pip_version = [0, 0, 0]
    else:
        import pip
        pip_version = [int(i) for i in pip.__version__.split('.')]

    reqs = [req for req in reqs if req != '']
    for i in range(len(reqs)):
        if pip_version < [19, 0, 0]:
            reqs[i] = re.sub(r'-e .*#egg=(.*)-.*', r'\1', reqs[i])
        else:
            reqs[i] = re.sub(r'-e (.*#egg=(.*)-.*)', r'\2 @ \1', reqs[i])

    return reqs


def get_dependency_links():
    """
    Extracts only depenency links for the dependency_links in older versions of pip.
    """
    with open("requirements.txt") as f:
        reqs = f.read().splitlines()
    dependency_links = []
    for req in reqs:
        link = re.subn(r'-e (.*#egg=.*-.*)', r'\1', req)
        if link[1] == 1:
            dependency_links.append(link[0])

    return dependency_links


long_description = read_content("README.rst") + read_content(
    os.path.join("docs/source", "CHANGELOG.rst")
)

extras_require = {"reST": ["Sphinx"]}
if os.environ.get("READTHEDOCS", None):
    extras_require["reST"].append("recommonmark")

setup(
    name="pubtools-executors",
    version="0.0.2",
    description="Pubtools-executors",
    long_description=long_description,
    long_description_content_type='text/x-rst',
    author="Lubomir Gallovic",
    author_email="lgallovi@redhat.com",
    url="https://github.com/release-engineering/pubtools-executors",
    classifiers=classifiers,
    python_requires=">=3.6",
    packages=find_packages(exclude=["tests"]),
    data_files=[],
    install_requires=get_requirements(),
    dependency_links=get_dependency_links(),
    include_package_data=True,
    extras_require=extras_require,
    tests_require=["tox"],
    cmdclass={"test": Tox},
)
