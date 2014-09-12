# -*- coding: utf-8 -*-
import sys
from os.path import join, dirname
from setuptools import setup, find_packages

VERSION = (0, 0, 1)
__version__ = VERSION
__versionstr__ = '.'.join(map(str, VERSION))

long_description = 'Should have been loaded.'
with open(join(dirname(__file__), 'README')) as f:
    long_description = f.read().strip()


install_requires = [
    'elasticsearch-dsl-py',
    'django',
]

tests_require = ["pytest", "pytest-cov"]

# use external unittest for 2.6
if sys.version_info[:2] == (2, 6):
    tests_require.append('unittest2')

setup(
    name="bungiesearch",
    description="A Django elasticsearch wrapper using elasticsearch's elasticsearch-dsl-py high level library.",
    license="To be determined I guess",
    url="https://github.com/sparrho/bungiesearch?",
    long_description=long_description,
    version=__versionstr__,
    author="Christopher Rabotin",
    author_email="christopher@sparrho.com",
    packages=find_packages(
        where='.',
        exclude=('test*',)
    ),
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
    ],
    install_requires=install_requires,

    test_suite="tests.run_all_tests",
    tests_require=tests_require,
)
