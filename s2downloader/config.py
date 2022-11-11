# -*- coding: utf-8 -*-
"""Input data module for S2Downloader."""

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


# python native libraries
import os
import json
import re
import geopy.distance
from datetime import datetime
from enum import Enum
from json import JSONDecodeError

# third party packages
from pydantic import BaseModel, Field, validator, StrictBool, Extra, HttpUrl
from typing import Optional, List, Dict


class ResamplingMethodName(str, Enum):
    """Enum for supported and tested resampling methods."""

    cubic = "cubic"
    bilinear = "bilinear"
    nearest = "nearest"


class TileSettings(BaseModel):
    """Template for Tile settings in config file."""

    data_coverage: Dict = Field(
        title="Data coverage",
        description="Percentage of data coverage.",
        alias="sentinel:data_coverage",
        default={"gt": 10}
    )
    cloud_cover: Dict = Field(
        title="Cloud coverage",
        description="Percentage of cloud coverage.",
        alias="eo:cloud_cover",
        default={"lt": 20}
    )
    bands: List[str] = Field(
        title="Bands",
        description="List of bands.",
        default=["B02", "B03", "B05"]
    )
    time: str = Field(
        title="Time range",
        description="Time range expressed as two dates start/end."
    )

    @validator("data_coverage", "cloud_cover")
    def check_coverage(cls, v: dict):
        """Check if coverage equations are set correctly."""
        if len(v.keys()) != 1:
            raise ValueError("It should be a dictionary with one key (operator) value (integer) pair.")
        for key in v.keys():
            if key not in ["le", "lt", "eq", "ge", "gt"]:
                raise ValueError("The operator should be one of: le, lt, eq, ge or gt.")
            value = v[key]
            if not isinstance(value, int) or value < 0 or value > 100:
                raise ValueError(f"The value ({str(value)}) should be an integer between 0 and 100.")
        return v

    @validator("bands")
    def check_bands(cls, v):
        """Check if bands is set correctly."""
        if len(v) == 0 or not set(v).issubset(["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A",
                                               "B09", "B11", "B12"]):
            raise ValueError("Only the following band names are supported: B01, B02, B03, B04, B05, B06, B07,"
                             " B08, B8A, B09, B11, B12.")
        if len(v) != len(set(v)):
            raise ValueError("Remove duplicates.")
        return v

    @validator("time")
    def check_time(cls, v):
        """Check if time parameter is a date or a date range (start/end)."""
        if "/" in v:
            try:
                pattern = re.compile(r'^(\d{4}-\d{2}-\d{2})/(\d{4}-\d{2}-\d{2})$')
                dates = pattern.search(v)
                if dates is None:
                    raise ValueError("It does not match the format yyyy-mm-dd/yyyy-mm-dd")
                start = datetime.strptime(dates[1], '%Y-%m-%d')
                end = datetime.strptime(dates[2], '%Y-%m-%d')
                if start >= end:
                    raise ValueError("start >= end.")
            except Exception as err:
                raise ValueError(f"The time range {v} is incorrect: {err}.")
        else:
            try:
                pattern = re.compile(r'^(\d{4}-\d{2}-\d{2})$')
                dates = pattern.search(v)
                if dates is None:
                    raise ValueError("It does not match the format yyyy-mm-dd")
                datetime.strptime(dates[1], '%Y-%m-%d')
            except Exception as err:
                raise ValueError(f"The time {v} is incorrect: {err}.")
        return v


class AoiSettings(BaseModel, extra=Extra.forbid):
    """Template for AOI settings in config file."""

    bounding_box: List[float] = Field(
        title="Bounding Box for AOI.",
        description="SW and NE corner coordinates of AOI Bounding Box.")
    apply_SCL_band_mask: Optional[StrictBool] = Field(
        title="Apply a filter mask from SCL.",
        description="Define if SCL masking should be applied.",
        default=True)
    SCL_filter_values: List[int] = Field(
        title="SCL values for the filter mask.",
        description="Define which values of SCL band should be applied as filter.",
        default=[3, 7, 8, 9, 10])
    SCL_mask_valid_pixels_min_percentage: float = Field(
        title="Minimum percentage of valid pixels after cloud masking.",
        description="Define a minimum percentage of pixels that should be valid after cloud masking in the AOI.",
        default=0.0, ge=0.0, le=100.0)
    aoi_min_coverage: float = Field(
        title="Minimum percentage of valid pixels after noData filtering.",
        description="Define a minimum percentage of pixels that should be valid (not noData) after noData filtering"
                    " in the aoi.",
        default=0.0, ge=0.0, le=100.0)
    resampling_method: ResamplingMethodName = Field(
        title="Rasterio resampling method name.",
        description="Define the method to be used when resampling.",
        default=ResamplingMethodName.cubic)

    @validator('bounding_box')
    def validate_BB(cls, v):
        """Check BoundingBox coordinates."""
        if len(v) != 4:
            raise ValueError("Bounding Box needs two pairs of lat/lon coordinates.")
        if v[0] >= v[2] or v[1] >= v[3]:
            raise ValueError("Bounding Box coordinates are not valid.")
        coords_nw = (v[3], v[0])
        coords_ne = (v[3], v[2])
        coords_sw = (v[1], v[0])

        ew_dist = geopy.distance.geodesic(coords_nw, coords_ne).km
        ns_dist = geopy.distance.geodesic(coords_nw, coords_sw).km

        if ew_dist > 50 or ns_dist > 50:
            raise ValueError("Bounding Box is too large. It should be max 50*50km.")

        return v

    @validator("SCL_filter_values")
    def check_scl_filter_values(cls, v):
        """Check if SCL_filter_values is set correctly."""
        if not set(v).issubset([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]):
            raise ValueError("Only the following values are allowed: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11.")
        if len(v) != len(set(v)):
            raise ValueError("Remove duplicates.")
        if len(v) == 0:
            raise ValueError("Provide a SCL class for filtering. If no filtering is wanted keep default values and "
                             "set apply_SCL_band_mask to 'False'.")
        return v


class ResultsSettings(BaseModel, extra=Extra.forbid):
    """Template for raster_saving_settings in config file."""

    results_dir: str = Field(
        title="Location of the output directory.",
        description="Define folder where all output data should be stored."
    )
    only_dates_no_data: Optional[StrictBool] = Field(
        title="Download Dates.",
        description="Get only list of dates for all available scenes without downloading the scenes.",
        default=False
    )
    download_thumbnails: Optional[StrictBool] = Field(
        title="Download thumbnails.",
        description="For each scene download the provided thumbnail.",
        default=False
    )
    download_overviews: Optional[StrictBool] = Field(
        title="Download preview.",
        description="For each scene download the provided preview.",
        default=False
    )
    download_only_one_scene: Optional[StrictBool] = Field(
        title="Download only one scene.",
        description="Downloads only the most recent scene from the available scenes.",
        default=False
    )

    @validator('results_dir')
    def check_folder(cls, v):
        """Check if output folder location is defined - string should not be empty."""
        if v == "":
            raise ValueError("Empty string is not allowed.")
        if os.path.isabs(v) is False:
            v = os.path.realpath(v)
        return v


class UserSettings(BaseModel, extra=Extra.forbid):
    """Template for user_path_settings in config file."""

    aoi_settings: AoiSettings = Field(
        title="AOI Settings", description=""
    )

    tile_settings: TileSettings = Field(
        title="Tile Settings.", description=""
    )

    result_settings: ResultsSettings = Field(
        title="Result Settings.", description=""
    )


class S2Settings(BaseModel, extra=Extra.forbid):
    """Template for S2 settings in config file."""

    collections: List[str] = Field(
        title="Definition of data collection to be searched for.",
        description="Define S2 data collection.",
        default=["sentinel-s2-l2a-cogs"]
    )

    stac_catalog_url: Optional[HttpUrl] = Field(
        title="STAC catalog URL.",
        description="URL to access the STAC catalog.",
        default="https://earth-search.aws.element84.com/v0"
    )


class Config(BaseModel):
    """Template for the Sentinel 2 portal configuration file."""

    user_settings: UserSettings = Field(
        title="User settings.", description=""
    )

    s2_settings: S2Settings = Field(
        title="Sentinel 2 settings.", description=""
    )


def loadConfiguration(*, path: str) -> dict:
    """Load configuration json file.

    Parameters
    ----------
    path : str
        Path to the configuration json file.

    Returns
    -------
    : dict
        A dictionary containing configurations.

    Raises
    ------
    JSONDecodeError
        If failed to parse the json file to the dictionary.
    FileNotFoundError
        Config file not found.
    IOError
        Invalid JSON file.
    ValueError
        Invalid value for configuration object.
    """
    try:
        with open(path) as config_fp:
            config = json.load(config_fp)
            config = Config(**config).dict(by_alias=True)
    except JSONDecodeError as e:
        raise IOError(f'Failed to load the configuration json file => {e}')
    return config
