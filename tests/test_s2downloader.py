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
import fnmatch
import json
import os
import shutil
import unittest

import numpy
import pytest
import rasterio

from rasterio.crs import CRS
from s2downloader.s2downloader import s2Downloader
from s2downloader.config import loadConfiguration, Config
from copy import deepcopy


def find_files(base_dir: str, pattern: str) -> list[str]:
    """
    Return list of files matching a pattern in the base folder.

    Parameters
    ----------
    base_dir: str
        Base directory.
    pattern: str
        Pattern for the file's name.

    Returns
    -------
    list
        List of filenames.
    """
    return [n for n in fnmatch.filter(os.listdir(os.path.realpath(base_dir)), pattern) if
            os.path.isfile(os.path.join(os.path.realpath(base_dir), n))]


class TestS2Downloader(unittest.TestCase):
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
        cls.configuration['user_settings']['result_settings']['path_to_logfile'] = cls.output_data_path
        cls.configuration['user_settings']['aoi_settings']['SCL_filter_values'] = [3, 6]
        cls.configuration['user_settings']['aoi_settings']['date_range'] = ["2021-09-04", "2021-09-05"]

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
        except OSError:
            print("Deletion of the directory %s failed" % cls.output_data_path)
        else:
            print("Successfully deleted the directory %s" % cls.output_data_path)

    @pytest.mark.subset
    def testS2DownloaderBBDefault(self):
        """Test configuration default settings."""

        config = deepcopy(self.configuration)

        Config(**config)
        s2Downloader(config_dict=config)

        # check output
        # number of files:
        filecount = sum([len(files) for r, d, files in os.walk(self.output_data_path)])
        assert filecount == 6

        # features of two files:
        path = os.path.abspath(
            os.path.join(self.output_data_path, "20210905_S2B_SCL.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint8"
            assert expected_res.shape == (86, 104)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=776160.0,
                                                                      bottom=5810680.0,
                                                                      right=777200.0,
                                                                      top=5811540.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32632)
            assert numpy.isclose([776160.0, 10.0, 0.0, 5811540.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

        path = os.path.abspath(
            os.path.join(self.output_data_path, "20210905_S2B_blue.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint16"
            assert expected_res.shape == (86, 104)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=776160.0,
                                                                      bottom=5810680.0,
                                                                      right=777200.0,
                                                                      top=5811540.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32632)
            assert numpy.isclose([776160.0, 10.0, 0.0, 5811540.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

        path = os.path.abspath(
            os.path.join(self.output_data_path, "20210905_S2B_coastal.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint16"
            assert expected_res.shape == (86, 104)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=776160.0,
                                                                      bottom=5810680.0,
                                                                      right=777200.0,
                                                                      top=5811540.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32632)
            assert numpy.isclose([776160.0, 10.0, 0.0, 5811540.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

        path = os.path.abspath(
            os.path.join(self.output_data_path, "20210905_S2B_rededge1.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint16"
            assert expected_res.shape == (86, 104)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=776160.0,
                                                                      bottom=5810680.0,
                                                                      right=777200.0,
                                                                      top=5811540.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32632)
            assert numpy.isclose([776160.0, 10.0, 0.0, 5811540.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

    def testS2DownloaderPolyDefault(self):
        """Test configuration default settings with the AOI as a Polygon."""

        config = deepcopy(self.configuration)
        config['user_settings']['aoi_settings']['bounding_box'] = []
        config['user_settings']['aoi_settings']['aoi_min_coverage'] = 65
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

        Config(**config)
        s2Downloader(config_dict=config)

        # check output
        # number of files:
        filecount = sum([len(files) for r, d, files in os.walk(self.output_data_path)])
        assert filecount == 6

        # features of two files:
        path = os.path.abspath(
            os.path.join(self.output_data_path, "20210905_S2B_SCL.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint8"
            assert expected_res.shape == (72, 68)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=776300.0,
                                                                      bottom=5810780.0,
                                                                      right=776980.0,
                                                                      top=5811500.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32632)
            assert numpy.isclose([776300.0, 10.0, 0.0, 5811500.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

        path = os.path.abspath(
            os.path.join(self.output_data_path, "20210905_S2B_blue.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint16"
            assert expected_res.shape == (72, 68)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=776300.0,
                                                                      bottom=5810780.0,
                                                                      right=776980.0,
                                                                      top=5811500.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32632)
            assert numpy.isclose([776300.0, 10.0, 0.0, 5811500.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

        path = os.path.abspath(
            os.path.join(self.output_data_path, "20210905_S2B_coastal.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint16"
            assert expected_res.shape == (72, 68)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=776300.0,
                                                                      bottom=5810780.0,
                                                                      right=776980.0,
                                                                      top=5811500.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32632)
            assert numpy.isclose([776300.0, 10.0, 0.0, 5811500.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

        path = os.path.abspath(
            os.path.join(self.output_data_path, "20210905_S2B_rededge1.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint16"
            assert expected_res.shape == (72, 68)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=776300.0,
                                                                      bottom=5810780.0,
                                                                      right=776980.0,
                                                                      top=5811500.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32632)
            assert numpy.isclose([776300.0, 10.0, 0.0, 5811500.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

    @pytest.mark.subset
    def testS2DownloaderPolygonSCLMasking(self):
        """Test the SCL masking funktion with a polygon."""

        config = deepcopy(self.configuration)

        config["user_settings"]["aoi_settings"]["bounding_box"] = []
        config["user_settings"]["aoi_settings"]["date_range"] = ["2022-11-13", "2022-11-15"]
        config["user_settings"]["aoi_settings"]["apply_SCL_band_mask"] = True
        config["user_settings"]["aoi_settings"]["SCL_filter_values"] = [6]
        config["user_settings"]["aoi_settings"]["aoi_min_coverage"] = 40
        config["user_settings"]["tile_settings"]["bands"] = ["blue"]
        config["user_settings"]["aoi_settings"]["polygon"] = {
            "coordinates": [
                [
                    [
                        12.372813890692186,
                        52.39177608469933
                    ],
                    [
                        12.395726318929974,
                        52.37029771627479
                    ],
                    [
                        12.439587252984921,
                        52.36510137895499
                    ],
                    [
                        12.50276009084007,
                        52.376192820350695
                    ],
                    [
                        12.50276009084007,
                        52.402760977453624
                    ],
                    [
                        12.477392759576304,
                        52.429812092951295
                    ],
                    [
                        12.448588564078165,
                        52.39067744502387
                    ],
                    [
                        12.392289454694065,
                        52.426319339598905
                    ],
                    [
                        12.372813890692186,
                        52.39177608469933
                    ]
                ]
            ],
            "type": "Polygon"
        }

        Config(**config)
        s2Downloader(config_dict=config)

        # check output
        # number of files:
        filecount = sum([len(files) for r, d, files in os.walk(self.output_data_path)])
        assert filecount == 4

        # features of SCL band:
        path = os.path.abspath(
            os.path.join(self.output_data_path, "20221114_S2A_SCL.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint8"
            assert expected_res.shape == (734, 896)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=729460.0,
                                                                      bottom=5807220.0,
                                                                      right=738420.0,
                                                                      top=5814560.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32632)
            assert numpy.isclose([729460.0, 10.0, 0.0, 5814560.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()
            scl_np_array = expected_res.read()
            unique, counts = numpy.unique(scl_np_array, return_counts=True)
            pixel_count_dict = dict(zip(unique, counts))
            assert pixel_count_dict == {
                numpy.uint8(0): numpy.int64(387083),
                numpy.uint8(4): numpy.int64(54092),
                numpy.uint8(5): numpy.int64(70305),
                numpy.uint8(6): numpy.int64(144919),
                numpy.uint8(7): numpy.int64(1265)
            }
            assert (
                           pixel_count_dict[numpy.uint8(4)] +
                           pixel_count_dict[numpy.uint8(5)] +
                           pixel_count_dict[numpy.uint8(7)] +
                           pixel_count_dict[numpy.uint8(6)]
                   ) / scl_np_array.size == numpy.float64(0.4114274158232775)
            assert pixel_count_dict[numpy.uint8(6)] / (
                    pixel_count_dict[numpy.uint8(4)] +
                    pixel_count_dict[numpy.uint8(5)] +
                    pixel_count_dict[numpy.uint8(7)] +
                    pixel_count_dict[numpy.uint8(6)]
            ) == numpy.float64(0.535584538456137)
            assert 1 - (
                    (pixel_count_dict[numpy.uint8(6)] +
                     pixel_count_dict[numpy.uint8(0)]
                     ) / scl_np_array.size
            ) == numpy.float64(0.19107325321136626)

        # check pixel percentage
        scenes_info_path = os.path.join(self.output_data_path, find_files(self.output_data_path,
                                                                          "scenes_info_*.json")[0])
        with open(scenes_info_path) as info_json:
            info_dict = json.load(info_json)
            assert info_dict["20221114"]["nonzero_pixels"] == 41.14274158232775
            assert info_dict["20221114"]["masked_pixels"] == 53.5584538456137
            assert info_dict["20221114"]["valid_pixels"] == 19.107325321136628

        # features of blue masked band:
        path = os.path.abspath(
            os.path.join(self.output_data_path, "20221114_S2A_blue.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint16"
            assert expected_res.shape == (734, 896)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=729460.0,
                                                                      bottom=5807220.0,
                                                                      right=738420.0,
                                                                      top=5814560.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32632)
            assert numpy.isclose([729460.0, 10.0, 0.0, 5814560.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()
            assert numpy.count_nonzero(expected_res.read()) == 125662

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
        s2Downloader(config_dict=config)

        # check output
        # number of files:
        filecount = sum([len(files) for r, d, files in os.walk(self.output_data_path)])
        assert filecount == 6

        # features of two files:
        path = os.path.abspath(
            os.path.join(self.output_data_path, "20210427_S2B_SCL.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint8"
            assert expected_res.shape == (2828, 3742)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=448340.0,
                                                                      bottom=6043220.0,
                                                                      right=485760.0,
                                                                      top=6071500.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32632)
            assert numpy.isclose([448340.0, 10.0, 0.0, 6071500.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

        path = os.path.abspath(
            os.path.join(self.output_data_path, "20210427_S2B_blue.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint16"
            assert expected_res.shape == (2828, 3742)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=448340.0,
                                                                      bottom=6043220.0,
                                                                      right=485760.0,
                                                                      top=6071500.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32632)
            assert numpy.isclose([448340.0, 10.0, 0.0, 6071500.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

        path = os.path.abspath(
            os.path.join(self.output_data_path, "20210427_S2B_coastal.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint16"
            assert expected_res.shape == (2828, 3742)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=448340.0,
                                                                      bottom=6043220.0,
                                                                      right=485760.0,
                                                                      top=6071500.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32632)
            assert numpy.isclose([448340.0, 10.0, 0.0, 6071500.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

        path = os.path.abspath(
            os.path.join(self.output_data_path, "20210427_S2B_rededge1.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint16"
            assert expected_res.shape == (2828, 3742)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=448340.0,
                                                                      bottom=6043220.0,
                                                                      right=485760.0,
                                                                      top=6071500.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32632)
            assert numpy.isclose([448340.0, 10.0, 0.0, 6071500.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

    @pytest.mark.subset
    def testS2Downloader2UTMs(self):
        """Test downloader for 2 UTMs."""

        config = deepcopy(self.configuration)
        config["user_settings"]["tile_settings"]["bands"] = ["blue"]
        config["user_settings"]["aoi_settings"]["bounding_box"] = [11.53953018718721,
                                                                   51.9893919386015,
                                                                   12.22833075284612,
                                                                   52.36055456486244]
        config["user_settings"]["aoi_settings"]["date_range"] = ['2021-09-02', '2021-09-03']
        Config(**config)
        s2Downloader(config_dict=config)

        # check output
        # number of files:
        filecount = sum([len(files) for r, d, files in os.walk(self.output_data_path)])
        assert filecount == 4

        # features of two files:
        path = os.path.abspath(
            os.path.join(self.output_data_path, "20210903_S2A_SCL.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint8"
            assert expected_res.shape == (4314, 4872)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=672920.0, bottom=5762920.0,
                                                                      right=721640.0, top=5806060.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32632)
            assert numpy.isclose([672920.0, 10.0, 0.0, 5806060.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

        path = os.path.abspath(
            os.path.join(self.output_data_path, "20210903_S2A_blue.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint16"
            assert expected_res.shape == (4314, 4872)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=672920.0, bottom=5762920.0,
                                                                      right=721640.0, top=5806060.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32632)
            assert numpy.isclose([672920.0, 10.0, 0.0, 5806060.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

    def testS2DownloaderChoose1UTMfrom2(self):
        """Test downloader for 2 UTMs."""

        config = deepcopy(self.configuration)
        config["user_settings"]["aoi_settings"]["bounding_box"] = [13.10766141955574, 53.452302211632144,
                                                                   13.237473951256504, 53.50549339832173]
        config["user_settings"]["aoi_settings"]["date_range"] = ["2018-07-01", "2018-07-02"]
        config['user_settings']["tile_settings"]["mgrs:utm_zone"] = {"in": [33]}
        config['user_settings']["tile_settings"]["bands"] = ["coastal"]
        config["user_settings"]["aoi_settings"]["apply_SCL_band_mask"] = False
        config["user_settings"]["aoi_settings"]["aoi_min_coverage"] = 20
        Config(**config)
        s2Downloader(config_dict=config)

        # check output
        # number of files:
        filecount = sum([len(files) for r, d, files in os.walk(self.output_data_path)])
        assert filecount == 4

        # features of two files:
        path = os.path.abspath(
            os.path.join(self.output_data_path, "20180701_S2A_SCL.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint8"
            assert expected_res.shape == (614, 876)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=374340.0, bottom=5924040.0,
                                                                      right=383100.0, top=5930180.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32633)

        config['user_settings']["tile_settings"]["mgrs:utm_zone"] = {"in": [32]}
        Config(**config)
        s2Downloader(config_dict=config)

        # features of two files:
        path = os.path.abspath(
            os.path.join(self.output_data_path, "20180701_S2A_SCL.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint8"
            assert expected_res.shape == (642, 896)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=772360.0, bottom=5930460.0,
                                                                      right=781320.0, top=5936880.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32632)

    def testS2Downloader2UTMsSouthernHemisphere(self):
        """Test downloader for 2 UTM tiles in southern hemisphere and west of Greenwich combined with SCL-masking."""

        config = deepcopy(self.configuration)
        config["user_settings"]["tile_settings"]["bands"] = ["blue"]
        config["user_settings"]["aoi_settings"]["bounding_box"] = [-72.21253483033124,
                                                                   -41.341630665653824,
                                                                   -71.50872541102595,
                                                                   -41.00765157647477]
        config["user_settings"]["aoi_settings"]["apply_SCL_band_mask"] = True
        config["user_settings"]["aoi_settings"]["SCL_filter_values"] = [6]
        config["user_settings"]["aoi_settings"]["date_range"] = ['2022-12-31']
        Config(**config)
        s2Downloader(config_dict=config)

        # check output
        # number of files:
        filecount = sum([len(files) for r, d, files in os.walk(self.output_data_path)])
        assert filecount == 4

        # features of two files:
        path = os.path.abspath(
            os.path.join(self.output_data_path, "20221231_S2B_SCL.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint8"
            assert expected_res.shape == (3922, 6038)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=733220.0, bottom=5417440.0,
                                                                      right=793600.0, top=5456660.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32718)
            assert numpy.isclose([733220.0, 10.0, 0.0, 5456660.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

        path = os.path.abspath(
            os.path.join(self.output_data_path, "20221231_S2B_blue.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint16"
            assert expected_res.shape == (3922, 6038)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=733220.0, bottom=5417440.0,
                                                                      right=793600.0, top=5456660.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32718)
            assert numpy.isclose([733220.0, 10.0, 0.0, 5456660.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()
            assert numpy.count_nonzero(expected_res.read()) == 21661720.0

    def testS2DownloaderTileIDEQ(self):
        """Test downloading a single TileID."""

        config = deepcopy(self.configuration)
        config["user_settings"]["aoi_settings"]["bounding_box"] = []
        config['user_settings']["tile_settings"]["mgrs:utm_zone"] = {"eq": 33}
        config['user_settings']["tile_settings"]["mgrs:latitude_band"] = {"eq": "U"}
        config['user_settings']["tile_settings"]["mgrs:grid_square"] = {"eq": "UV"}
        config['user_settings']['aoi_settings']['date_range'] = ["2018-06-06"]
        config['user_settings']['aoi_settings']["SCL_filter_values"] = [3, 7, 8, 9, 10]

        Config(**config)
        s2Downloader(config_dict=config)

        path = os.path.abspath(
            os.path.join(self.output_data_path,
                         "33/U/UV/2018/06/S2B_MSIL2A_20180606T102019_N0500_R065_T33UUV_20230824T062839/SCL.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint8"
            assert expected_res.shape == (10980, 10980)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=300000.0,
                                                                      bottom=5890200.0,
                                                                      right=409800.0,
                                                                      top=6000000.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32633)
            assert numpy.isclose([300000.0, 10.0, 0.0, 6000000.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

        path = os.path.abspath(
            os.path.join(self.output_data_path,
                         "33/U/UV/2018/06/S2B_MSIL2A_20180606T102019_N0500_R065_T33UUV_20230824T062839/coastal.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint16"
            assert expected_res.shape == (10980, 10980)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=300000.0,
                                                                      bottom=5890200.0,
                                                                      right=409800.0,
                                                                      top=6000000.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32633)
            assert numpy.isclose([300000.0, 10.0, 0.0, 6000000.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

        path = os.path.abspath(
            os.path.join(self.output_data_path,
                         "33/U/UV/2018/06/S2B_MSIL2A_20180606T102019_N0500_R065_T33UUV_20230824T062839/blue.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint16"
            assert expected_res.shape == (10980, 10980)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=300000.0,
                                                                      bottom=5890200.0,
                                                                      right=409800.0,
                                                                      top=6000000.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32633)
            assert numpy.isclose([300000.0, 10.0, 0.0, 6000000.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

        path = os.path.abspath(
            os.path.join(self.output_data_path,
                         "33/U/UV/2018/06/S2B_MSIL2A_20180606T102019_N0500_R065_T33UUV_20230824T062839/rededge1.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint16"
            assert expected_res.shape == (10980, 10980)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=300000.0,
                                                                      bottom=5890200.0,
                                                                      right=409800.0,
                                                                      top=6000000.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32633)
            assert numpy.isclose([300000.0, 10.0, 0.0, 6000000.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

    def testS2DownloaderTileIDEQ_false(self):
        """Test downloading a single TileID, but for a wrongly returned image."""

        config = deepcopy(self.configuration)
        config["user_settings"]["aoi_settings"]["bounding_box"] = []
        config['user_settings']["tile_settings"]["mgrs:utm_zone"] = {"eq": 33}
        config['user_settings']["tile_settings"]["mgrs:latitude_band"] = {"eq": "U"}
        config['user_settings']["tile_settings"]["mgrs:grid_square"] = {"eq": "UV"}
        config['user_settings']['aoi_settings']['date_range'] = ["2018-06-06"]
        config["user_settings"]["tile_settings"]["bands"] = ["coastal"]
        config['user_settings']['aoi_settings']["SCL_filter_values"] = [3, 7, 8, 9, 10]

        Config(**config)
        s2Downloader(config_dict=config)

        path = os.path.abspath(
            os.path.join(self.output_data_path,
                         "33/U/UV/2018/06/S2B_MSIL2A_20180606T102019_N0208_R065_T33UUV_20180606T190659/SCL.tif"))
        self.assertFalse(os.path.isfile(path))

    def testS2DownloaderTileIDIN(self):
        """Test downloading multiple TileIDs."""

        config = deepcopy(self.configuration)
        config["user_settings"]["aoi_settings"]["bounding_box"] = []
        config['user_settings']["tile_settings"]["mgrs:utm_zone"] = {"in": [32, 33]}
        config['user_settings']["tile_settings"]["mgrs:latitude_band"] = {"eq": "U"}
        config['user_settings']["tile_settings"]["mgrs:grid_square"] = {"in": ["UV", "QE"]}
        config['user_settings']['aoi_settings']['date_range'] = ["2018-06-06"]
        config['user_settings']['aoi_settings']["SCL_filter_values"] = [3, 7, 8, 9, 10]
        config["user_settings"]["tile_settings"]["bands"] = ["coastal"]

        Config(**config)
        s2Downloader(config_dict=config)

        path = os.path.abspath(
            os.path.join(self.output_data_path,
                         "33/U/UV/2018/06/S2B_MSIL2A_20180606T102019_N0500_R065_T33UUV_20230824T062839/SCL.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint8"
            assert expected_res.shape == (10980, 10980)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=300000.0,
                                                                      bottom=5890200.0,
                                                                      right=409800.0,
                                                                      top=6000000.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32633)
            assert numpy.isclose([300000.0, 10.0, 0.0, 6000000.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

        path = os.path.abspath(
            os.path.join(self.output_data_path,
                         "32/U/QE/2018/06/S2B_MSIL2A_20180606T102019_N0500_R065_T32UQE_20230824T062839/SCL.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint8"
            assert expected_res.shape == (10980, 10980)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=699960.0,
                                                                      bottom=5890200.0,
                                                                      right=809760.0,
                                                                      top=6000000.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32632)
            assert numpy.isclose([699960.0, 10.0, 0.0, 6000000.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

    def testS2DownloaderOnlyDates(self):
        """Test configuration to test only dates download for the tile settings."""

        config = deepcopy(self.configuration)
        scene_tif_path = os.path.join(self.output_data_path, "20210905_S2B_rededge1.tif")

        config["user_settings"]["result_settings"]["download_data"] = False
        config["user_settings"]["tile_settings"]["bands"] = ["rededge1"]
        s2Downloader(config_dict=config)
        scenes_info_path = os.path.join(self.output_data_path, find_files(self.output_data_path,
                                                                          "scenes_info_*.json")[0])
        with open(scenes_info_path) as json_file:
            data = json.load(json_file)
            assert list(data.keys())[0] == "20210905"

        if os.path.exists(scene_tif_path):
            assert False

        os.remove(scenes_info_path)
        config["user_settings"]["result_settings"]["download_data"] = True
        config["user_settings"]["tile_settings"]["bands"] = ["rededge1"]
        s2Downloader(config_dict=config)
        if not os.path.exists(scene_tif_path):
            assert False
        with rasterio.open(scene_tif_path) as expected_res:
            assert expected_res.dtypes[0] == "uint16"
            assert expected_res.shape == (86, 104)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=776160.0,
                                                                      bottom=5810680.0,
                                                                      right=777200.0,
                                                                      top=5811540.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32632)
            assert numpy.isclose([776160.0, 10.0, 0.0, 5811540.0, 0.0, -10.0],
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
        s2Downloader(config_dict=config)

        if len(os.listdir(self.output_data_path, )) != 2:
            assert False

    def testS2DownloaderErrorNoItemsAtAWS(self):
        """Test configuration for error when search parameters do not yield a result."""

        config = deepcopy(self.configuration)

        config['user_settings']['tile_settings']['bands'] = ["coastal"]
        config['user_settings']['tile_settings']['eo:cloud_cover'] = {"eq": 0}
        config['user_settings']['tile_settings']['s2:nodata_pixel_percentage'] = {"eq": 0}
        config['user_settings']['aoi_settings']['date_range'] = ["2021-09-01", "2021-09-02"]

        Config(**config)
        with pytest.raises(Exception) as exinfo:
            s2Downloader(config_dict=config)

        if exinfo.value.args is not None:
            message = exinfo.value.args[0]
            assert str(message).__contains__('Failed to find data at AWS server')

    def testS2DownloaderThumbnailsOverviews(self):
        """Test configuration to download thumbnails and overviews for the tile settings."""

        config = deepcopy(self.configuration)

        config["user_settings"]["result_settings"]["download_overviews"] = True
        config["user_settings"]["result_settings"]["download_thumbnails"] = True
        config["user_settings"]["result_settings"]["download_data"] = False
        config["user_settings"]["aoi_settings"]["date_range"] = ['2021-09-08', '2021-09-08']
        config['user_settings']["tile_settings"]["eo:cloud_cover"] = {"lte": 2}

        s2Downloader(config_dict=config)

        scene_path = os.path.join(self.output_data_path, "S2B_32UQD_20210908_0_L2A_TCI.tif")

        if not os.path.exists(scene_path):
            assert False

        if not os.path.exists(
                os.path.join(
                    self.output_data_path, "S2B_32UQD_20210908_0_L2A_thumbnail.jpg")):
            assert False

        with rasterio.open(scene_path) as expected_res:
            assert expected_res.dtypes[0] == "uint8"
            assert expected_res.shape == (10980, 10980)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=699960.0, bottom=5790240.0,
                                                                      right=809760.0, top=5900040.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32632)
            assert numpy.isclose([699960.0, 10.0, 0.0, 5900040.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()
