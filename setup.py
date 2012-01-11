#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Setup script for speedparser."""

from setuptools import setup, find_packages
import sys, os

try:
    from speedparser import VERSION
    version = ".".join(map(str, VERSION))
except:
    version = '0.1.6'

# some trove classifiers:

# License :: OSI Approved :: MIT License
# Intended Audience :: Developers
# Operating System :: POSIX

setup(
    name='speedparser',
    version=version,
    description="feedparser but faster and worse",
    long_description=open('README.rst').read(),
    # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Operating System :: POSIX',
        'Development Status :: 4 - Beta',
    ],
    keywords='feedparser rss atom rdf lxml',
    author='Jason Moiron',
    author_email='jason@hiidef.com',

    url='https://github.com/hiidef/speedparser/',
    license='MIT',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,
    test_suite="tests",
    install_requires=[
      # -*- Extra requirements: -*-
      # 'feedparser>=0.5',
      'lxml',
    ],
    entry_points="""
    # -*- Entry points: -*-
    """,
)
