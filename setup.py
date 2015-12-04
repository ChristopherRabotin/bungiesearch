# -*- coding: utf-8 -*-
import sys
from os.path import join, dirname
from setuptools import setup, find_packages

VERSION = (1, 3, 0)
__version__ = VERSION
__versionstr__ = '.'.join(map(str, VERSION))

long_description = 'Should have been loaded from README.md.'
with open(join(dirname(__file__), 'README.rst')) as f:
    long_description = f.read().strip()


install_requires = [
    'django>=1.6',
    'elasticsearch-dsl>=0.0.4',
    'elasticsearch>=1.0.0,<=2.1.0'
    'python-dateutil',
    'six',
]

tests_require = []

# use external unittest for 2.6
if sys.version_info[:2] == (2, 6):
    tests_require.append('unittest2')

setup(
    name="bungiesearch",
    description="A Django elasticsearch wrapper and helper using elasticsearch-dsl-py high level library.",
    license="BSD-3",
    url="https://github.com/ChristopherRabotin/bungiesearch",
    long_description=long_description,
    version=__versionstr__,
    author="Christopher Rabotin",
    author_email="christopher.rabotin@gmail.com",
    packages=find_packages(
        where='.',
        exclude=('bungiesearch/tests',)
    ),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Framework :: Django"
    ],
    keywords="elasticsearch haystack django bungiesearch",
    install_requires=install_requires,
    dependency_links=['https://github.com/elasticsearch/elasticsearch-dsl-py#egg=elasticsearch-dsl-py'],
)
