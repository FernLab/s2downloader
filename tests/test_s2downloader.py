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


class TestSentinel2Downloader(unittest.TestCase):
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

    def testS2DownloaderDefault(self):
        """Test configuration default settings."""

        config = deepcopy(self.configuration)

        Config(**config)
        s2DataDownloader(config_dict=config)

        # check output
        # number of files:
        filecount = sum([len(files) for r, d, files in os.walk(self.output_data_path)])
        assert filecount == 6

        # features of two files:
        path = os.path.abspath(
            os.path.join(self.output_data_path, "S2B_20210905_SCL.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint8"
            assert expected_res.shape == (82, 100)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=367820.0,
                                                                      bottom=5804700.0,
                                                                      right=368820.0,
                                                                      top=5805520.0)
            assert expected_res.read_crs() == CRS.from_epsg(32633)
            assert numpy.isclose([367820.0, 10.0, 0.0, 5805520.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

        path = os.path.abspath(
            os.path.join(self.output_data_path, "S2B_20210905_B02.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint16"
            assert expected_res.shape == (82, 100)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=367820.0,
                                                                      bottom=5804700.0,
                                                                      right=368820.0,
                                                                      top=5805520.0)
            assert expected_res.read_crs() == CRS.from_epsg(32633)
            assert numpy.isclose([367820.0, 10.0, 0.0, 5805520.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

        path = os.path.abspath(
            os.path.join(self.output_data_path, "S2B_20210905_B01.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint16"
            assert expected_res.shape == (82, 100)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=367820.0,
                                                                      bottom=5804700.0,
                                                                      right=368820.0,
                                                                      top=5805520.0)
            assert expected_res.read_crs() == CRS.from_epsg(32633)
            assert numpy.isclose([367820.0, 10.0, 0.0, 5805520.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

        path = os.path.abspath(
            os.path.join(self.output_data_path, "S2B_20210905_B05.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint16"
            assert expected_res.shape == (82, 100)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=367820.0,
                                                                      bottom=5804700.0,
                                                                      right=368820.0,
                                                                      top=5805520.0)
            assert expected_res.read_crs() == CRS.from_epsg(32633)
            assert numpy.isclose([367820.0, 10.0, 0.0, 5805520.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

    def testS2DownloaderCenterUTM(self):
        """Test within a single tile in the center."""

        config = deepcopy(self.configuration)
        config["user_settings"]["aoi_settings"]["bounding_box"] = [8.201791423733251,
                                                                   54.536254520651106,
                                                                   8.778773634098867,
                                                                   54.78797740272492]
        config["user_settings"]["aoi_settings"]["date_range"] = ["2021-04-27"]
        config["user_settings"]["aoi_settings"]["SCL_filter_values"] = [3]

        Config(**config)
        s2DataDownloader(config_dict=config)

        # check output
        # number of files:
        filecount = sum([len(files) for r, d, files in os.walk(self.output_data_path)])
        assert filecount == 6

        # features of two files:
        path = os.path.abspath(
            os.path.join(self.output_data_path, "S2B_20210427_SCL.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint8"
            assert expected_res.shape == (2826, 3742)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=448340.0,
                                                                      bottom=6043240.0,
                                                                      right=485760.0,
                                                                      top=6071500.0)
            assert expected_res.read_crs() == CRS.from_epsg(32632)
            assert numpy.isclose([448340.0, 10.0, 0.0, 6071500.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

        path = os.path.abspath(
            os.path.join(self.output_data_path, "S2B_20210427_B02.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint16"
            assert expected_res.shape == (2826, 3742)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=448340.0,
                                                                      bottom=6043240.0,
                                                                      right=485760.0,
                                                                      top=6071500.0)
            assert expected_res.read_crs() == CRS.from_epsg(32632)
            assert numpy.isclose([448340.0, 10.0, 0.0, 6071500.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

        path = os.path.abspath(
            os.path.join(self.output_data_path, "S2B_20210427_B01.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint16"
            assert expected_res.shape == (2826, 3742)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=448340.0,
                                                                      bottom=6043240.0,
                                                                      right=485760.0,
                                                                      top=6071500.0)
            assert expected_res.read_crs() == CRS.from_epsg(32632)
            assert numpy.isclose([448340.0, 10.0, 0.0, 6071500.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

        path = os.path.abspath(
            os.path.join(self.output_data_path, "S2B_20210427_B05.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint16"
            assert expected_res.shape == (2826, 3742)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=448340.0,
                                                                      bottom=6043240.0,
                                                                      right=485760.0,
                                                                      top=6071500.0)
            assert expected_res.read_crs() == CRS.from_epsg(32632)
            assert numpy.isclose([448340.0, 10.0, 0.0, 6071500.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

    def testS2Downloader2UTMs(self):
        """Test downloader for 2 UTMs."""

        config = deepcopy(self.configuration)
        config["user_settings"]["aoi_settings"]["bounding_box"] = [11.53953018718721,
                                                                   51.9893919386015,
                                                                   12.22833075284612,
                                                                   52.36055456486244]
        config["user_settings"]["aoi_settings"]["date_range"] = ['2021-09-02', '2021-09-03']
        Config(**config)
        s2DataDownloader(config_dict=config)

        # check output
        # number of files:
        filecount = sum([len(files) for r, d, files in os.walk(self.output_data_path)])
        assert filecount == 6

        # features of two files:
        path = os.path.abspath(
            os.path.join(self.output_data_path, "S2A_20210903_SCL.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint8"
            assert expected_res.shape == (4315, 4874)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=672920.0, bottom=5762900.0,
                                                                      right=721660.0, top=5806050.0)
            assert expected_res.read_crs() == CRS.from_epsg(32632)
            assert numpy.isclose([672920.0, 10.0, 0.0, 5806050.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

        path = os.path.abspath(
            os.path.join(self.output_data_path, "S2A_20210903_B02.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint16"
            assert expected_res.shape == (4315, 4874)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=672920.0, bottom=5762900.0,
                                                                      right=721660.0, top=5806050.0)
            assert expected_res.read_crs() == CRS.from_epsg(32632)
            assert numpy.isclose([672920.0, 10.0, 0.0, 5806050.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

    def testS2DownloaderOnlyDates(self):
        """Test configuration to test only dates download for the tile settings"""

        config = deepcopy(self.configuration)
        scenes_info_path = os.path.join(self.output_data_path, "scenes_info_2021-09-04_2021-09-05.json")
        scene_tif_path = os.path.join(self.output_data_path, "S2B_20210905_B05.tif")

        config["user_settings"]["result_settings"]["download_data"] = False
        s2DataDownloader(config_dict=config)
        with open(scenes_info_path) as json_file:
            data = json.load(json_file)
            assert list(data.keys())[0] == "2021-09-05"

        if os.path.exists(scene_tif_path):
            assert False

        with pytest.raises(Exception) as exinfo:
            s2DataDownloader(config_dict=config)

        if exinfo.value.args is not None:
            message = exinfo.value.args[0]
            assert str(message).__contains__('.json already exists.')

        os.remove(scenes_info_path)
        config["user_settings"]["result_settings"]["download_data"] = True
        s2DataDownloader(config_dict=config)
        if not os.path.exists(scene_tif_path):
            assert False
        with rasterio.open(scene_tif_path) as expected_res:
            assert expected_res.dtypes[0] == "uint16"
            assert expected_res.shape == (82, 100)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=367820.0,
                                                                      bottom=5804700.0,
                                                                      right=368820.0,
                                                                      top=5805520.0)
            assert expected_res.read_crs() == CRS.from_epsg(32633)
            assert numpy.isclose([367820.0, 10.0, 0.0, 5805520.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

    def testS2DownloaderNoDataCoverage(self):
        """Test configuration for a case which the data coverage is not satisfied."""

        config = deepcopy(self.configuration)
        config['user_settings']['aoi_settings']['bounding_box'] = [14.8506420088255027, 52.2861358927904121,
                                                                   14.9743949098159135, 52.3514856977076875]
        config['user_settings']['aoi_settings']['date_range'] = ["2021-06-19"]
        Config(**config)
        s2DataDownloader(config_dict=config)

        if len(os.listdir(self.output_data_path,)) != 2:
            assert False

    def testS2DownloaderErrorNoItemsAtAWS(self):
        """Test configuration for error when search parameters do not yield a result"""

        config = deepcopy(self.configuration)

        config['user_settings']['tile_settings']['bands'] = ["B01"]
        config['user_settings']['tile_settings']['eo:cloud_cover'] = {"eq": 0}
        config['user_settings']['tile_settings']['sentinel:data_coverage'] = {"eq": 100}
        config['user_settings']['aoi_settings']['date_range'] = ["2021-09-01", "2021-09-02"]

        Config(**config)
        with pytest.raises(Exception) as exinfo:
            s2DataDownloader(config_dict=config)

        if exinfo.value.args is not None:
            message = exinfo.value.args[0]
            assert str(message).__contains__('Failed to find data at AWS server')

    def testS2DownloaderThumbnailsOverviews(self):
        """Test configuration to download thumbnails and overviews for the tile settings"""

        config = deepcopy(self.configuration)
        config["user_settings"]["result_settings"]["download_overviews"] = True
        config["user_settings"]["result_settings"]["download_thumbnails"] = True
        config["user_settings"]["result_settings"]["download_data"] = False

        s2DataDownloader(config_dict=config)

        scene_path = os.path.join(self.output_data_path, "S2B_33UUU_20210905_0_L2A_L2A_PVI.tif")

        if not os.path.exists(scene_path):
            assert False

        if not os.path.exists(
            os.path.join(
                self.output_data_path, "S2B_33UUU_20210905_0_L2A_preview.jpg")
        ):
            assert False

        with rasterio.open(scene_path) as expected_res:
            assert expected_res.dtypes[0] == "uint8"
            assert expected_res.shape == (343, 343)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=300000.0, bottom=5790280.0,
                                                                      right=409760.0, top=5900040.0)
            assert expected_res.read_crs() == CRS.from_epsg(32633)
            assert numpy.isclose([300000.0, 320.0, 0.0, 5900040.0, 0.0, -320.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()
