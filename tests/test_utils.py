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

from s2downloader.utils import getUTMZoneBB
from s2downloader.config import loadConfiguration


class TestUtils(unittest.TestCase):
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
        # delete testfolder
        try:
            if os.path.exists(cls.output_data_path):
                shutil.rmtree(cls.output_data_path)
                print()
        except OSError:
            print("Deletion of the directory %s failed" % cls.output_data_path)
        else:
            print("Successfully deleted the directory %s" % cls.output_data_path)

    def testGetUTMZoneBB(self):
        """Test getUTMZoneBB for different bounding boxes."""

        # Pure 32 UTM zone
        bb = [10.3564989947897175, 52.2069411524857401, 10.7103272880104043, 52.3674037585556391]
        utm_zone = getUTMZoneBB(bbox=bb)
        assert utm_zone == 32

        # 32 and 33 UTM zone tiles, but within 32 UTM zone overlap
        bb = [11.53953018718721, 51.9893919386015, 12.22833075284612, 52.36055456486244]
        utm_zone = getUTMZoneBB(bbox=bb)
        assert utm_zone == 32

        # 32 and 33 UTM zone tiles, but within 33 UTM zone
        bb = [13.4697892262127823, 52.2322959775096649, 13.7618500803157531, 52.3647370564987682]
        utm_zone = getUTMZoneBB(bbox=bb)
        assert utm_zone == 33

        # Pure 33 UTM zone
        bb = [14.9487927124571911, 52.2439379656995300, 15.2357887972764274, 52.3856451927234446]
        utm_zone = getUTMZoneBB(bbox=bb)
        assert utm_zone == 33
