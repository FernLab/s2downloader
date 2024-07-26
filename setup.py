#!/usr/bin/env python
# -*- coding: utf-8 -*-

# S2Downloader - The S2Downloader allows to download Sentinel-2 L2A data
#
# Copyright (C) 2022-2023
# - Helmholtz Centre Potsdam - GFZ German Research Centre for Geosciences Potsdam,
#   Germany (https://www.gfz-potsdam.de/)
#
# Licensed only under the EUPL, Version 1.2 or - as soon they will be approved
# by the European Commission - subsequent versions of the EUPL (the "Licence").
# You may not use this work except in compliance with the Licence.
#
# You may obtain a copy of the Licence at:
# https://joinup.ec.europa.eu/software/page/eupl
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

version = {}
with open("s2downloader/version.py") as version_file:
    exec(version_file.read(), version)

req = ['numpy', 'affine', 'pyproj', 'geojson', 'geojson-pydantic', 'rasterio', 'geopandas>=0.11',
       'shapely', 'pystac', 'geopy', 'pystac-client', 'pydantic']

req_setup = []

req_test = ['pytest>=3', 'pytest-cov', 'pytest-reporter-html1', 'urlchecker']

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
    python_requires='>=3.10',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Science/Research',
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
            's2downloader=s2downloader.s2downloader_cli:main',
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
    keywords=['s2downloader',
              'remote sensing',
              'sentinel-2',
              'copernicus',
              'multispectral',
              'satellite imagery',
              'geospatial',
              'mosaic'],
    long_description=readme,
    long_description_content_type='text/x-rst',
    project_urls={
        "Source code": "https://git.gfz-potsdam.de/fernlab/products/data-portal/s2downloader",
        "Issue Tracker": "https://git.gfz-potsdam.de/fernlab/products/data-portal/s2downloader/-/issues",
        "Documentation": "https://fernlab.git-pages.gfz-potsdam.de/products/data-portal/s2downloader/doc/",
        "Change log": "https://git.gfz-potsdam.de/fernlab/products/data-portal/s2downloader/-/blob/main/HISTORY.rst"
    },
    name='s2downloader',
    packages=find_packages(include=['s2downloader', 's2downloader.*']),
    include_package_data=True,
    setup_requires=req_setup,
    test_suite='tests',
    tests_require=req_test,
    url='https://git.gfz-potsdam.de/fernlab/products/data-portal/s2downloader',
    version=version['__version__'],
    zip_safe=False,
)
