#!/usr/bin/env python

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


def find_files(base_dir, pattern):
    """Return list of files matching a pattern in the base folder.

    Parameters:
    -----------
    base_dir: str
        Base directory.
    pattern: str
        Pattern for the file's name.

    Returns:
    --------
    :list
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
        """Define the Class method SetUp."""
        cls.root_path = "./"
        if os.path.basename(os.getcwd()) == "tests":
            cls.root_path = "../"

        cls.config_file = os.path.abspath(f"{cls.root_path}data/default_config.json")
        cls.configuration = loadConfiguration(path=cls.config_file)

        cls.configuration['user_settings']['result_settings']['results_dir'] = "tests/temp_results"

        cls.output_data_path = cls.configuration['user_settings']['result_settings']['results_dir']
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

    def testS2DownloaderDefault(self):
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
                                                                      bottom=5810700.0,
                                                                      right=777200.0,
                                                                      top=5811560.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32632)
            assert numpy.isclose([776160.0, 10.0, 0.0, 5811560.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

        path = os.path.abspath(
            os.path.join(self.output_data_path, "20210905_S2B_B02.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint16"
            assert expected_res.shape == (86, 104)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=776160.0,
                                                                      bottom=5810700.0,
                                                                      right=777200.0,
                                                                      top=5811560.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32632)
            assert numpy.isclose([776160.0, 10.0, 0.0, 5811560.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

        path = os.path.abspath(
            os.path.join(self.output_data_path, "20210905_S2B_B01.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint16"
            assert expected_res.shape == (86, 104)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=776160.0,
                                                                      bottom=5810700.0,
                                                                      right=777200.0,
                                                                      top=5811560.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32632)
            assert numpy.isclose([776160.0, 10.0, 0.0, 5811560.0, 0.0, -10.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()

        path = os.path.abspath(
            os.path.join(self.output_data_path, "20210905_S2B_B05.tif"))
        self.assertEqual((str(path), os.path.isfile(path)), (str(path), True))
        with rasterio.open(path) as expected_res:
            assert expected_res.dtypes[0] == "uint16"
            assert expected_res.shape == (86, 104)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=776160.0,
                                                                      bottom=5810700.0,
                                                                      right=777200.0,
                                                                      top=5811560.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32632)
            assert numpy.isclose([776160.0, 10.0, 0.0, 5811560.0, 0.0, -10.0],
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
            os.path.join(self.output_data_path, "20210427_S2B_B02.tif"))
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
            os.path.join(self.output_data_path, "20210427_S2B_B01.tif"))
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
            os.path.join(self.output_data_path, "20210427_S2B_B05.tif"))
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

    def testS2Downloader2UTMs(self):
        """Test downloader for 2 UTMs."""

        config = deepcopy(self.configuration)
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
        assert filecount == 6

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
            os.path.join(self.output_data_path, "20210903_S2A_B02.tif"))
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

    def testS2Downloader2UTMsSouthernHemisphere(self):
        """Test downloader for 2 UTM tiles in southern hemisphere and west of Greenwich."""

        config = deepcopy(self.configuration)
        config["user_settings"]["aoi_settings"]["bounding_box"] = [-72.21253483033124,
                                                                   -41.341630665653824,
                                                                   -71.50872541102595,
                                                                   -41.00765157647477]

        config["user_settings"]["aoi_settings"]["date_range"] = ['2022-12-31']
        Config(**config)
        s2Downloader(config_dict=config)

        # check output
        # number of files:
        filecount = sum([len(files) for r, d, files in os.walk(self.output_data_path)])
        assert filecount == 6

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
            os.path.join(self.output_data_path, "20221231_S2B_B02.tif"))
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

    def testS2DownloaderTileIDEQ(self):
        """Test downloading a single TileID."""

        config = deepcopy(self.configuration)
        config["user_settings"]["aoi_settings"]["bounding_box"] = []
        config['user_settings']["tile_settings"]["sentinel:utm_zone"] = {"eq": 33}
        config['user_settings']["tile_settings"]["sentinel:latitude_band"] = {"eq": "U"}
        config['user_settings']["tile_settings"]["sentinel:grid_square"] = {"eq": "UV"}
        config['user_settings']['aoi_settings']['date_range'] = ["2018-06-06"]
        config['user_settings']['aoi_settings']["SCL_filter_values"] = [3, 7, 8, 9, 10]

        Config(**config)
        s2Downloader(config_dict=config)

        path = os.path.abspath(
            os.path.join(self.output_data_path,
                         "33/U/UV/2018/06/S2B_MSIL2A_20180606T102019_N0208_R065_T33UUV_20180606T190659/SCL.tif"))
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
                         "33/U/UV/2018/06/S2B_MSIL2A_20180606T102019_N0208_R065_T33UUV_20180606T190659/B01.tif"))
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
                         "33/U/UV/2018/06/S2B_MSIL2A_20180606T102019_N0208_R065_T33UUV_20180606T190659/B02.tif"))
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
                         "33/U/UV/2018/06/S2B_MSIL2A_20180606T102019_N0208_R065_T33UUV_20180606T190659/B05.tif"))
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

    def testS2DownloaderTileIDIN(self):
        """Test downloading multiple TileIDs."""

        config = deepcopy(self.configuration)
        config["user_settings"]["aoi_settings"]["bounding_box"] = []
        config['user_settings']["tile_settings"]["sentinel:utm_zone"] = {"in": [32, 33]}
        config['user_settings']["tile_settings"]["sentinel:latitude_band"] = {"eq": "U"}
        config['user_settings']["tile_settings"]["sentinel:grid_square"] = {"in": ["UV", "QE"]}
        config['user_settings']['aoi_settings']['date_range'] = ["2018-06-06"]
        config['user_settings']['aoi_settings']["SCL_filter_values"] = [3, 7, 8, 9, 10]
        config["user_settings"]["tile_settings"]["bands"] = ["B01"]

        Config(**config)
        s2Downloader(config_dict=config)

        path = os.path.abspath(
            os.path.join(self.output_data_path,
                         "33/U/UV/2018/06/S2B_MSIL2A_20180606T102019_N0208_R065_T33UUV_20180606T190659/SCL.tif"))
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
                         "32/U/QE/2018/06/S2B_MSIL2A_20180606T102019_N0208_R065_T32UQE_20180606T190659/SCL.tif"))
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
        """Test configuration to test only dates download for the tile settings"""

        config = deepcopy(self.configuration)
        scene_tif_path = os.path.join(self.output_data_path, "20210905_S2B_B05.tif")

        config["user_settings"]["result_settings"]["download_data"] = False
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
        s2Downloader(config_dict=config)
        if not os.path.exists(scene_tif_path):
            assert False
        with rasterio.open(scene_tif_path) as expected_res:
            assert expected_res.dtypes[0] == "uint16"
            assert expected_res.shape == (86, 104)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=776160.0,
                                                                      bottom=5810700.0,
                                                                      right=777200.0,
                                                                      top=5811560.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32632)
            assert numpy.isclose([776160.0, 10.0, 0.0, 5811560.0, 0.0, -10.0],
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
        """Test configuration for error when search parameters do not yield a result"""

        config = deepcopy(self.configuration)

        config['user_settings']['tile_settings']['bands'] = ["B01"]
        config['user_settings']['tile_settings']['eo:cloud_cover'] = {"eq": 0}
        config['user_settings']['tile_settings']['sentinel:data_coverage'] = {"eq": 100}
        config['user_settings']['aoi_settings']['date_range'] = ["2021-09-01", "2021-09-02"]

        Config(**config)
        with pytest.raises(Exception) as exinfo:
            s2Downloader(config_dict=config)

        if exinfo.value.args is not None:
            message = exinfo.value.args[0]
            assert str(message).__contains__('Failed to find data at AWS server')

    def testS2DownloaderThumbnailsOverviews(self):
        """Test configuration to download thumbnails and overviews for the tile settings"""

        config = deepcopy(self.configuration)
        config["user_settings"]["result_settings"]["download_overviews"] = True
        config["user_settings"]["result_settings"]["download_thumbnails"] = True
        config["user_settings"]["result_settings"]["download_data"] = False

        s2Downloader(config_dict=config)

        scene_path = os.path.join(self.output_data_path, "S2B_32UQD_20210905_0_L2A_L2A_PVI.tif")

        if not os.path.exists(scene_path):
            assert False

        if not os.path.exists(
            os.path.join(
                self.output_data_path, "S2B_32UQD_20210905_0_L2A_preview.jpg")):
            assert False

        with rasterio.open(scene_path) as expected_res:
            assert expected_res.dtypes[0] == "uint8"
            assert expected_res.shape == (343, 343)
            assert expected_res.bounds == rasterio.coords.BoundingBox(left=699960.0, bottom=5790280.0,
                                                                      right=809720.0, top=5900040.0)
            assert expected_res.read_crs() == CRS().from_epsg(code=32632)
            assert numpy.isclose([699960.0, 320.0, 0.0, 5900040.0, 0.0, -320.0],
                                 expected_res.read_transform(),
                                 rtol=0,
                                 atol=1e-4,
                                 equal_nan=False).all()
