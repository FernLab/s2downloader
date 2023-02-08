# -*- coding: utf-8 -*-
"""Input data module for S2Downloader."""

# python native libraries
import os
import json
import time

import geopy.distance
from datetime import datetime
from enum import Enum
from json import JSONDecodeError

# third party packages
from pydantic import BaseModel, Field, validator, StrictBool, Extra, HttpUrl, root_validator
from typing import Optional, List, Dict

from .utils import getUTMZoneBB


class ResamplingMethodName(str, Enum):
    """Enum for supported and tested resampling methods."""

    cubic = "cubic"
    bilinear = "bilinear"
    nearest = "nearest"


class S2Platform(str, Enum):
    """Enum for Sentinel-2 platform."""

    S2A = "sentinel-2a"
    S2B = "sentinel-2b"


class TileSettings(BaseModel):
    """Template for Tile settings in config file."""

    platform: Optional[Dict] = Field(
        title="Sentinel-2 platform.",
        description="For which Sentinel-2 platform should data be downloaded.",
        default={"in": [S2Platform.S2A, S2Platform.S2B]}
    )

    data_coverage: Dict = Field(
        title="Data coverage",
        description="Percentage of data coverage.",
        alias="sentinel:data_coverage",
        default={"gt": 10}
    )
    utm_zone: Optional[Dict] = Field(
        title="UTM zone",
        description="UTM zones for which to search data.",
        alias="sentinel:utm_zone",
        default={}
    )
    latitude_band: Optional[Dict] = Field(
        title="Latitude band",
        description="Latitude band for which to search data.",
        alias="sentinel:latitude_band",
        default={}
    )
    grid_square: Optional[Dict] = Field(
        title="Grid square",
        description="Grid square for which to search data.",
        alias="sentinel:grid_square",
        default={}
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

    @validator("data_coverage", "cloud_cover")
    def checkCoverage(cls, v: dict):
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
    def checkBands(cls, v):
        """Check if bands is set correctly."""
        if len(v) == 0 or not set(v).issubset(["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A",
                                               "B09", "B11", "B12"]):
            raise ValueError("Only the following band names are supported: B01, B02, B03, B04, B05, B06, B07,"
                             " B08, B8A, B09, B11, B12.")
        if len(v) != len(set(v)):
            raise ValueError("Remove duplicates.")
        return v


class AoiSettings(BaseModel, extra=Extra.forbid):
    """Template for AOI settings in config file."""

    bounding_box: List[float] = Field(
        title="Bounding Box for AOI.",
        description="SW and NE corner coordinates of AOI Bounding Box.")
    bb_max_utm_zone_overlap: int = Field(
        title="Max overlap of the BB over a second UTM zone.",
        description="Max overlap of the BB over a second UTM zone in meters. It's upper bound is 100km.",
        default=50000,
        gt=0, lt=100000
    )
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
    date_range: List[str] = Field(
        title="Date range.",
        description="List with the start and end date. If the same it is a single date request.",
        unique_items=False,
        min_items=1,
        max_items=2,
        default=["2021-09-01", "2021-09-05"]
    )

    @validator("bounding_box")
    def validateBB(cls, v):
        """Check if the Bounding Box is valid."""
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
    def checkSCLFilterValues(cls, v):
        """Check if SCL_filter_values is set correctly."""
        if not set(v).issubset([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]):
            raise ValueError("Only the following values are allowed: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11.")
        if len(v) != len(set(v)):
            raise ValueError("Remove duplicates.")
        if len(v) == 0:
            raise ValueError("Provide a SCL class for filtering. If no filtering is wanted keep default values and "
                             "set apply_SCL_band_mask to 'False'.")
        return v

    @validator("date_range")
    def checkDateRange(cls, v):
        """Check data range."""
        limit_date = datetime(2017, 4, 1)
        for d in v:
            d_date = datetime.strptime(d, "%Y-%m-%d")
            if d_date < limit_date:
                raise ValueError(f"Invalid date range: {d} should equal or greater than 2017-04-01.")
        if len(v) == 2:
            start_date = datetime.strptime(v[0], "%Y-%m-%d")
            end_date = datetime.strptime(v[1], "%Y-%m-%d")
            if start_date > end_date:
                raise ValueError(f"Invalid date range: {v[0]} should not be greater than {v[1]}.")
        return v


class ResultsSettings(BaseModel, extra=Extra.forbid):
    """Template for raster_saving_settings in config file."""

    request_id: Optional[int] = Field(
        title="Request ID.",
        description="Request ID to identify the request.",
        default=round(time.time() * 1000)
    )
    results_dir: str = Field(
        title="Location of the output directory.",
        description="Define folder where all output data should be stored."
    )
    target_resolution: Optional[int] = Field(
        title="Target resolution.",
        description="Target resolution in meters, it should be either 60, 20 or 10 meters.",
        default=10, ge=10, le=60
    )
    download_data: Optional[StrictBool] = Field(
        title="Download Data.",
        description="For each scene download the data.",
        default=True
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
    logging_level: Optional[str] = Field(
        title="Logging level.",
        description="Logging level, it should be one of: DEBUG, INFO, WARN, or ERROR.",
        default="INFO"
    )

    @validator('logging_level')
    def checkLogLevel(cls, v):
        """Check if logging level is correct."""
        if v not in ["DEBUG", "INFO", "WARN", "ERROR"]:
            raise ValueError("Logging level, it should be one of: DEBUG, INFO, WARN, or ERROR.")
        return v

    @validator('results_dir')
    def checkFolder(cls, v):
        """Check if output folder location is defined - string should not be empty."""
        if v == "":
            raise ValueError("Empty string is not allowed.")
        if os.path.isabs(v) is False:
            v = os.path.realpath(v)
        return v

    @validator('target_resolution')
    def checkTargeResolution(cls, v):
        """Check if the target resolution is either 60, 20 or 10 meters."""
        if not (v == 60 or v == 20 or v == 10):
            raise ValueError(f"The target resolution {v} should either be 60, 20 or 10 meters")
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

    @root_validator(skip_on_failure=True)
    def checkBboxAndSetUTMZone(cls, v):
        """Check BBOX UTM zone coverage and set UTM zone."""
        bb = v["aoi_settings"].__dict__["bounding_box"]
        bb_max_utm_zone_overlap = v["aoi_settings"].__dict__["bb_max_utm_zone_overlap"]
        utm_zone = getUTMZoneBB(bbox=bb, bb_max_utm_zone_overlap=bb_max_utm_zone_overlap)
        v["tile_settings"].__dict__["sentinel:utm_zone"] = {"eq": utm_zone}
        return v


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
