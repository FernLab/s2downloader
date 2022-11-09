#!/usr/bin/env python

"""Tests for `s2downloader` package."""

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

import json
import os
import shutil
import unittest

import numpy
import pytest
import rasterio

from rasterio.crs import CRS
from s2downloader.s2downloader import s2DataDownloader
from s2downloader.config import loadConfiguration, Config
from copy import deepcopy


class TestSentinel2Portal(unittest.TestCase):
    root_path = None
    config_file = None
    configuration = None
    output_data_path = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.root_path = "./"
        if os.path.basename(os.getcwd()) == "tests":
            cls.root_path = "../"

        cls.config_file = os.path.abspath(f"{cls.root_path}data/default_config.json")
        cls.configuration = loadConfiguration(path=cls.config_file)

        cls.configuration['user_settings']['result_settings']['results_dir'] = "tests/temp_results"

        cls.output_data_path = cls.configuration['user_settings']['result_settings']['results_dir']

        if not os.path.exists(cls.output_data_path):
            try:
                os.mkdir(cls.output_data_path)
            except OSError:
                print(f"Creation of test data output directory {cls.output_data_path} failed")
                raise
        else:
            raise Exception(f'Test directory {cls.output_data_path} already exists!')

    @classmethod
    def tearDown(cls) -> None:
        # delete testfolder
        try:
            if os.path.exists(cls.output_data_path):
                shutil.rmtree(cls.output_data_path)
        except OSError:
            print("Deletion of the directory %s failed" % cls.output_data_path)
        else:
            print("Successfully deleted the directory %s" % cls.output_data_path)

    def testS2DownloaderDefault(self):
        """Test configuration default settings."""

        config = deepcopy(self.configuration)

        Config(**config)
        s2DataDownloader(config_dict=config)

        # check output
        
