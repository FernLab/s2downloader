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

import os
import shutil
import unittest
import pytest

from s2downloader.config import loadConfiguration, Config
from copy import deepcopy


class TestConfig(unittest.TestCase):
    root_path = None
    config_file = None
    configuration = None
    output_data_path = None

    @classmethod
    def setUp(cls) -> None:
        cls.root_path = "./"
        if os.path.basename(os.getcwd()) == "tests":
            cls.root_path = "../"

        cls.config_file = os.path.abspath(f"{cls.root_path}data/default_config.json")
        cls.configuration = loadConfiguration(path=cls.config_file)

        cls.configuration['user_settings']['result_settings']['results_dir'] = "tests/temp_results"

        cls.output_data_path = cls.configuration['user_settings']['result_settings']['results_dir']

        try:
            if os.path.exists(cls.output_data_path):
                shutil.rmtree(cls.output_data_path)
            os.mkdir(cls.output_data_path)
        except OSError:
            print(f"Creation of test data output directory {cls.output_data_path} failed")
            raise

    @classmethod
    def tearDown(cls) -> None:
        # delete test folder
        try:
            if os.path.exists(cls.output_data_path):
                shutil.rmtree(cls.output_data_path)
                print()
        except OSError:
            print("Deletion of the directory %s failed" % cls.output_data_path)
        else:
            print("Successfully deleted the directory %s" % cls.output_data_path)

    def testSentinel2AOISettingsDateRange(self):
        """Test configuration to test time range for the tile settings"""

        config = deepcopy(self.configuration)
        config['user_settings']['aoi_settings']['date_range'] = ["2020-06-01", "2020-09-01"]
        Config(**config)

        config['user_settings']['aoi_settings']['date_range'] = ["2020-06-01"]
        Config(**config)

        config['user_settings']['aoi_settings']['date_range'] = ["2020/06/01"]
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['aoi_settings']['date_range'] = ["2020/06-01"]
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['aoi_settings']['date_range'] = ["2020-06-01-2020-09-01"]
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['aoi_settings']['date_range'] = ["2020/06-01/2020-09-01"]
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['aoi_settings']['date_range'] = ["2020-06-01/2020/09-01"]
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['aoi_settings']['date_range'] = ["2020-09-01/2020-06-01"]
        with pytest.raises(ValueError):
            Config(**config)

    def testSentinel2dataCoverage(self):
        """Test configuration to test coverage for the tile settings"""

        config = deepcopy(self.configuration)
        config['user_settings']['tile_settings']['sentinel:data_coverage'] = {"lt": 80}
        Config(**config)

        config['user_settings']['tile_settings']['sentinel:data_coverage'] = {"xx": 25}
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['tile_settings']['sentinel:data_coverage'] = {"gt": 25, "lt": 70}
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['tile_settings']['sentinel:data_coverage'] = {"gt": -25}
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['tile_settings']['sentinel:data_coverage'] = {"gt": "err"}
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['tile_settings']['sentinel:data_coverage'] = {}
        with pytest.raises(ValueError):
            Config(**config)

    def testSentinel2cloudCoverage(self):
        """Test configuration to test coverage for the tile settings"""

        config = deepcopy(self.configuration)
        config['user_settings']['tile_settings']['eo:cloud_cover'] = {"lt": 80}
        Config(**config)

        config['user_settings']['tile_settings']['eo:cloud_cover'] = {"xx": 25}
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['tile_settings']['eo:cloud_cover'] = {"gt": 25, 'lt': 70}
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['tile_settings']['eo:cloud_cover'] = {"gt": -25}
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['tile_settings']['eo:cloud_cover'] = {"gt": 'err'}
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['tile_settings']['eo:cloud_cover'] = {}
        with pytest.raises(ValueError):
            Config(**config)

    def testSentinel2TileSettingsBands(self):
        """Test configuration to test bands for the tile settings"""

        config = deepcopy(self.configuration)
        config['user_settings']['tile_settings']['bands'] = \
            ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09", "B11", "B12"]
        Config(**config)

        config['user_settings']['tile_settings']['bands'] = \
            ["B01", "B02", "B07", "B08", "B8A", "B09", "B11", "B12"]
        Config(**config)

        config['user_settings']['tile_settings']['bands'] = \
            ["B01"]
        Config(**config)

        config['user_settings']['tile_settings']['bands'] = \
            []
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['tile_settings']['bands'] = \
            ["B01", "B02", "B03", "B02"]
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['tile_settings']['bands'] = \
            ["B01", "B34"]
        with pytest.raises(ValueError):
            Config(**config)

    def testSentinel2SCLFilterValues(self):
        """Test configuration to test SCL filter values for mask"""

        config = deepcopy(self.configuration)
        config['user_settings']['aoi_settings']['SCL_filter_values'] = \
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
        Config(**config)

        config['user_settings']['aoi_settings']['SCL_filter_values'] = \
            [3, 7, 8, 9, 10]
        Config(**config)

        config['user_settings']['aoi_settings']['SCL_filter_values'] = \
            [0]
        Config(**config)

        config['user_settings']['aoi_settings']['SCL_filter_values'] = \
            []
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['aoi_settings']['SCL_filter_values'] = \
            [3, 7, 8, 9, 10, 3]
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['aoi_settings']['SCL_filter_values'] = \
            [3, 33]
        with pytest.raises(ValueError):
            Config(**config)

    def testS2BoundingBox(self):
        """Test configuration and output for BoundingBox Parameter."""

        config = deepcopy(self.configuration)

        config['user_settings']['aoi_settings']['bounding_box'] = [12.1439, 52.3832, 13.4204, 53.0389]
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['aoi_settings']['bounding_box'] = [13.4204, 53.0389]
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['aoi_settings']['bounding_box'] = []
        with pytest.raises(ValueError):
            Config(**config)

    def testTargetResolution(self):
        """Test configuration for results target_resolution Parameter."""

        config = deepcopy(self.configuration)

        config['user_settings']['result_settings']['target_resolution'] = 20
        Config(**config)

        config['user_settings']['result_settings']['target_resolution'] = 60
        Config(**config)

        config['user_settings']['result_settings']['target_resolution'] = 10.0
        Config(**config)

        config['user_settings']['result_settings']['target_resolution'] = 12.1
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['result_settings']['target_resolution'] = 15
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['result_settings']['target_resolution'] = "asas"
        with pytest.raises(ValueError):
            Config(**config)

    def testLoggingLevel(self):
        """Test configuration for results logging_level Parameter."""

        config = deepcopy(self.configuration)

        config['user_settings']['result_settings']['logging_level'] = "DEBUG"
        Config(**config)

        config['user_settings']['result_settings']['logging_level'] = "WARN"
        Config(**config)

        config['user_settings']['result_settings']['logging_level'] = "ERROR"
        Config(**config)

        config['user_settings']['result_settings']['logging_level'] = "Error"
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['result_settings']['logging_level'] = "Something"
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['result_settings']['logging_level'] = 10
        with pytest.raises(ValueError):
            Config(**config)
