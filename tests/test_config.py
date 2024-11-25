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
"""Tests for `s2Downloader` package."""

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
        """
        Define the Class method SetUp.

        Raises
        ------
        OSError
            Failed to load the configuration json file.
        """
        cls.root_path = "./"
        if os.path.basename(os.getcwd()) == "tests":
            cls.root_path = "../"

        cls.config_file = os.path.abspath(f"{cls.root_path}data/default_config.json")
        cls.configuration = loadConfiguration(path=cls.config_file)

        cls.configuration['user_settings']['result_settings']['results_dir'] = (
            os.path.abspath(os.path.join(cls.root_path, "tests/temp_results")))

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
        """Define the Class method tearDown."""
        # delete test folder
        try:
            if os.path.exists(cls.output_data_path):
                shutil.rmtree(cls.output_data_path)
                print()
        except OSError:
            print("Deletion of the directory %s failed" % cls.output_data_path)
        else:
            print("Successfully deleted the directory %s" % cls.output_data_path)

    @pytest.mark.subset
    def testS2DownloaderAOISettingsDateRange(self):
        """Test configuration to test time range for the tile settings."""

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

        config['user_settings']['aoi_settings']['date_range'] = ["2016-09-01", "2020-06-01"]
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['aoi_settings']['date_range'] = ["2020-09-01", "2018-06-01"]
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['aoi_settings']['date_range'] = ["2022-09-01", "3024-06-01"]
        with pytest.raises(ValueError):
            Config(**config)

    @pytest.mark.subset
    def testS2DownloaderDataCoverage(self):
        """Test configuration to test coverage for the tile settings."""

        config = deepcopy(self.configuration)
        config['user_settings']['tile_settings']['s2:nodata_pixel_percentage'] = {"lt": 80}
        Config(**config)

        config['user_settings']['tile_settings']['s2:nodata_pixel_percentage'] = {"xx": 25}
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['tile_settings']['s2:nodata_pixel_percentage'] = {"gt": 25, "lt": 70}
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['tile_settings']['s2:nodata_pixel_percentage'] = {"gt": -25}
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['tile_settings']['s2:nodata_pixel_percentage'] = {"gt": "err"}
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['tile_settings']['s2:nodata_pixel_percentage'] = {}
        with pytest.raises(ValueError):
            Config(**config)

    @pytest.mark.subset
    def testS2DownloaderCloudCoverage(self):
        """Test configuration to test coverage for the tile settings."""

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

    @pytest.mark.subset
    def testS2DownloaderTileSettingsBands(self):
        """Test configuration to test bands for the tile settings."""

        config = deepcopy(self.configuration)
        config['user_settings']['tile_settings']['bands'] = \
            ["coastal", "blue", "green", "red", "rededge1", "rededge2", "rededge3", "nir",
             "nir08", "nir09", "swir16", "swir22"]
        Config(**config)

        config['user_settings']['tile_settings']['bands'] = \
            ["coastal", "blue", "rededge3", "nir", "nir08", "nir09", "swir16", "swir22"]
        Config(**config)

        config['user_settings']['tile_settings']['bands'] = \
            ["cirrus"]
        Config(**config)

        config['user_settings']['tile_settings']['bands'] = \
            []
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['tile_settings']['bands'] = \
            ["coastal", "blue", "green", "blue"]
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['tile_settings']['bands'] = \
            ["coastal", "rainbow"]
        with pytest.raises(ValueError):
            Config(**config)

    @pytest.mark.subset
    def testS2DownloaderSCLFilterValues(self):
        """Test configuration to test SCL filter values for mask."""

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

    @pytest.mark.subset
    def testS2BoundingBox(self):
        """Test configuration for BoundingBox Parameter."""

        config = deepcopy(self.configuration)

        config['user_settings']['aoi_settings']['bounding_box'] = [13.4204, 53.0389]
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['aoi_settings']['bounding_box'] = []
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']["tile_settings"]["mgrs:utm_zone"] = {"eq": 32}
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']["tile_settings"]["mgrs:latitude_band"] = {"eq": "U"}
        config['user_settings']["tile_settings"]["mgrs:grid_square"] = {"eq": "UV"}
        Config(**config)

        del config['user_settings']['aoi_settings']['bounding_box']
        Config(**config)

        config['user_settings']["tile_settings"]["mgrs:utm_zone"] = {"eq": "32"}
        with pytest.raises(ValueError):
            Config(**config)

    @pytest.mark.subset
    def testS2Polygon(self):
        """Test configuration for Polygon Parameter."""
        config = deepcopy(self.configuration)

        config['user_settings']['aoi_settings']['polygon'] = None
        Config(**config)

        config['user_settings']['aoi_settings']['polygon'] = {
            "coordinates": [
                [
                    [
                        13.06273559413006,
                        52.377432380433305
                    ],
                    [
                        13.065105498655981,
                        52.37747622057046
                    ],
                    [
                        13.067164203597116,
                        52.37813381740361
                    ],
                    [
                        13.067188142026396,
                        52.37955127060573
                    ],
                    [
                        13.067116326737562,
                        52.38111480022582
                    ],
                    [
                        13.070084692001785,
                        52.38121708528095
                    ],
                    [
                        13.068887770524185,
                        52.38285361393676
                    ],
                    [
                        13.065560328817526,
                        52.38351113068933
                    ],
                    [
                        13.061418980504953,
                        52.38355496479147
                    ],
                    [
                        13.060509320181893,
                        52.381743118963925
                    ],
                    [
                        13.060700827618234,
                        52.38004809910265
                    ],
                    [
                        13.061658364800877,
                        52.37865988781914
                    ],
                    [
                        13.06273559413006,
                        52.377432380433305
                    ]
                ]
            ],
            "type": "Polygon"
        }
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['aoi_settings']['bounding_box'] = []
        Config(**config)

        del config['user_settings']['aoi_settings']['bounding_box']
        Config(**config)

        config['user_settings']["tile_settings"]["mgrs:utm_zone"] = {"eq": 32}
        Config(**config)

        config['user_settings']["tile_settings"]["mgrs:latitude_band"] = {"eq": "U"}
        config['user_settings']["tile_settings"]["mgrs:grid_square"] = {"eq": "UV"}
        with pytest.raises(ValueError):
            Config(**config)

        config['user_settings']['aoi_settings']['polygon'] = None
        Config(**config)

    @pytest.mark.subset
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

    @pytest.mark.subset
    def testStacCatalogURL(self):
        """Test the stac catalog URL."""
        config = deepcopy(self.configuration)
        config['s2_settings']["stac_catalog_url"] = "hts://earth-search.aws.element84.com/v1"
        with pytest.raises(ValueError):
            Config(**config)

    @pytest.mark.subset
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
