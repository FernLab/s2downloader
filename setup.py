#!/usr/bin/env python

"""The setup script."""

# S2Downloader, Python Boilerplate contains all the boilerplate you need to create a Python package.
#
# Copyright (c) 2022, FernLab (GFZ Potsdam, fernlab@gfz-potsdam.de)
#
# This software was developed within the context [...]
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

version = {}
with open("s2downloader/version.py") as version_file:
    exec(version_file.read(), version)

req = ['gdal', 'affine', 'pyproj', 'numpy', 'matplotlib', 'geojson', 'rasterio',
       'pandas', 'geopandas>=0.11', 'shapely', 'rtree', 'python-dateutil', 'pystac', 'pystac_client', 'pydantic']

req_setup = ['pytest-runner']

req_test = ['pytest>=3', 'pytest-cov', 'pytest-reporter-html1', 'urlchecker==0.0.32']

req_doc = [
    'sphinx>=4.1.1',
    'sphinx-argparse',
    'sphinx-autodoc-typehints',
    'sphinx_rtd_theme',
    'numpydoc'
]

req_lint = ['flake8', 'pycodestyle', 'pydocstyle']

req_dev = ['twine'] + req_setup + req_test + req_doc + req_lint

setup(
    author="FernLab",
    author_email='fernlab@gfz-potsdam.de',
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10'
    ],
    description="Downloader for Sentinel-2 from aws.",
    entry_points={
        'console_scripts': [
            's2downloader=bin.s2downloader_cli:main',
        ],
    },
    extras_require={
        "doc": req_doc,
        "test": req_test,
        "lint": req_lint,
        "dev": req_dev
    },
    install_requires=req,
    license="Apache Software License 2.0",
    include_package_data=True,
    keywords='s2downloader',
    long_description=readme,
    name='s2downloader',
    packages=find_packages(include=['s2downloader', 's2downloader.*']),
    setup_requires=req_setup,
    test_suite='tests',
    tests_require=req_test,
    url='https://git.gfz-potsdam.de/fernlab/s2downloader',
    version=version['__version__'],
    zip_safe=False,
)
