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
"""Tests for `s2downloader` package."""

import os
import shutil
import unittest

import geopandas
import pytest

from s2downloader.config import loadConfiguration
from s2downloader.utils import getUTMZoneBB


class TestUtils(unittest.TestCase):
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
        cls.tiles_path = cls.configuration['s2_settings']['tiles_definition_path']

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
        # delete testfolder
        try:
            if os.path.exists(cls.output_data_path):
                shutil.rmtree(cls.output_data_path)
                print()
        except OSError:
            print("Deletion of the directory %s failed" % cls.output_data_path)
        else:
            print("Successfully deleted the directory %s" % cls.output_data_path)

    @pytest.mark.subset
    def testGetUTMZoneBB(self):
        """Test getUTMZoneBB for different bounding boxes."""

        tiles_gpd = geopandas.read_file(self.tiles_path)

        # Pure 32 UTM zone
        bb = (10.3564989947897175, 52.2069411524857401, 10.7103272880104043, 52.3674037585556391)
        utm_zone = getUTMZoneBB(tiles_gpd=tiles_gpd, bbox=bb)
        assert utm_zone == 32

        # 32 and 33 UTM zone tiles, but within 32 UTM zone overlap
        bb = (11.53953018718721, 51.9893919386015, 12.22833075284612, 52.36055456486244)
        utm_zone = getUTMZoneBB(tiles_gpd=tiles_gpd, bbox=bb)
        assert utm_zone == 32

        # 32 and 33 UTM zone tiles, but within 33 UTM zone
        bb = (13.4697892262127823, 52.2322959775096649, 13.7618500803157531, 52.3647370564987682)
        utm_zone = getUTMZoneBB(tiles_gpd=tiles_gpd, bbox=bb)
        assert utm_zone == 33

        # Pure 33 UTM zone
        bb = (14.9487927124571911, 52.2439379656995300, 15.2357887972764274, 52.3856451927234446)
        utm_zone = getUTMZoneBB(tiles_gpd=tiles_gpd, bbox=bb)
        assert utm_zone == 33
