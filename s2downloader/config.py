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
"""Input data module for S2Downloader."""

# python native libraries
import os
import json
import time

import geopy.distance
from datetime import datetime, date
from enum import Enum
from json import JSONDecodeError

import pydantic
# third party packages
from geojson_pydantic import Polygon
from pydantic import BaseModel, Field, StrictBool, field_validator, HttpUrl, model_validator, TypeAdapter
from pydantic_core import ValidationError
from typing import Optional, List, Dict, Union


class ResamplingMethodName(str, Enum):
    """Enum for supported and tested resampling methods."""

    cubic = "cubic"
    bilinear = "bilinear"
    nearest = "nearest"


class S2Platform(str, Enum):
    """Enum for Sentinel-2 platform."""

    S2A = "sentinel-2a"
    S2B = "sentinel-2b"


class TileSettings(BaseModel, extra='forbid'):
    """Template for Tile settings in config file."""

    platform: Optional[Dict] = Field(
        title="Sentinel-2 platform.",
        description="For which Sentinel-2 platform should data be downloaded.",
        default={"in": [S2Platform.S2A, S2Platform.S2B]}
    )

    nodata_pixel_percentage: Dict = Field(
        title="NoData pixel percentage",
        description="Percentage of NoData pixel.",
        alias="s2:nodata_pixel_percentage",
        default={"gt": 10}
    )
    utm_zone: Dict = Field(
        title="UTM zone",
        description="UTM zones for which to search data.",
        alias="mgrs:utm_zone"
    )
    latitude_band: Dict = Field(
        title="Latitude band",
        description="Latitude band for which to search data.",
        alias="mgrs:latitude_band"
    )
    grid_square: Dict = Field(
        title="Grid square",
        description="Grid square for which to search data.",
        alias="mgrs:grid_square"
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
        default=["blue", "green", "rededge1"]
    )

    @field_validator("nodata_pixel_percentage", "cloud_cover")
    def checkCoverage(cls, v: dict):
        """Check if coverage equations are set correctly."""
        if len(v.keys()) != 1:
            raise ValueError("It should be a dictionary with one key (operator) value (integer) pair.")
        for key in v.keys():
            if key not in ["lte", "lt", "eq", "gte", "gt"]:
                raise ValueError("The operator should be one of: lte, lt, eq, gte or gt.")
            value = v[key]
            if not isinstance(value, int) or value < 0 or value > 100:
                raise ValueError(f"The value ({str(value)}) should be an integer between 0 and 100.")
        return v

    @field_validator("bands")
    def checkBands(cls, v):
        """Check if bands is set correctly."""
        if len(v) == 0 or not set(v).issubset(["coastal", "blue", "green", "red", "rededge1", "rededge2", "rededge3",
                                               "nir", "nir08", "nir09", "swir16", "swir22"]):
            raise ValueError("Only the following band names are supported: coastal, blue, green, red, rededge1,"
                             " rededge2, rededge3, nir, nir08, nir09, swir16, swir22.")
        if len(v) != len(set(v)):
            raise ValueError("Remove duplicates.")
        return v

    @field_validator("utm_zone", "latitude_band", "grid_square")
    def checkTileInfo(cls, v: dict, field: pydantic.ValidationInfo):
        """Check if tile info is set correctly."""
        v_type = str
        if field.field_name == "utm_zone":
            v_type = int
        if len(v.keys()) > 0:
            for key in v.keys():
                if key in ["eq"]:
                    if not isinstance(v[key], v_type):
                        raise ValueError(f"For operator eq the value ({str(v[key])}) should be a {str(v_type)}.")
                elif key in ["in"]:
                    if not isinstance(v[key], list):
                        raise ValueError(f"For operator eq the value ({str(v[key])}) should be a list.")
                    else:
                        for vv in v[key]:
                            if not isinstance(vv, v_type):
                                raise ValueError(f"For operator in the value ({str(vv)}) should be a {str(v_type)}.")
                else:
                    raise ValueError("The operator should either be eq or in.")
        return v


class AoiSettings(BaseModel, extra='forbid'):
    """Template for AOI settings in config file."""

    bounding_box: Union[List[float], None] = Field(
        title="Bounding Box for AOI.",
        description="SW and NE corner coordinates of AOI Bounding Box.",
        max_length=4,
        default=None
    )
    polygon: Union[Polygon, None] = Field(
        title="Polygon for the AOI.",
        description="Polygon defined as in GeoJson.",
        default=None
    )
    apply_SCL_band_mask: Optional[StrictBool] = Field(
        title="Apply a filter mask from SCL.",
        description="Define if SCL masking should be applied.",
        default=True)
    SCL_filter_values: List[int] = Field(
        title="SCL values for the filter mask.",
        description="Define which values of SCL band should be applied as filter.",
        default=[3, 7, 8, 9, 10])
    aoi_min_coverage: float = Field(
        title="Minimum percentage of valid pixels after noData filtering.",
        description="Define a minimum percentage of pixels that should be valid (not noData) after noData filtering"
                    " in the aoi.",
        default=0.0, ge=0.0, le=100.0)
    SCL_masked_pixels_max_percentage: float = Field(
        title="Maximum percentage of SCL masked pixels after noData filtering.",
        description="Define a maximum percentage of pixels that are filtered by a cloud mask "
                    "after noData filtering in the aoi.",
        default=0.0, ge=0.0, le=100.0)
    valid_pixels_min_percentage: float = Field(
        title="Minimum percentage of valid pixels after noData filtering and cloud masking.",
        description="Define a minimum percentage of pixels that should be valid after noData filtering and cloud "
                    "masking in the AOI.",
        default=0.0, ge=0.0, le=100.0)
    resampling_method: ResamplingMethodName = Field(
        title="Rasterio resampling method name.",
        description="Define the method to be used when resampling.",
        default=ResamplingMethodName.cubic)
    date_range: List[str] = Field(
        title="Date range.",
        description="List with the start and end date. If the same it is a single date request.",
        min_length=1,
        max_length=2,
        default=["2021-09-01", "2021-09-05"]
    )

    @field_validator("bounding_box")
    def validateBB(cls, v):
        """Check if the Bounding Box is valid."""
        if len(v) != 0:
            if len(v) != 4:
                raise ValueError("Bounding Box needs two pairs of lat/lon coordinates.")

            if v[0] >= v[2] or v[1] >= v[3]:
                raise ValueError("Bounding Box coordinates are not valid.")
            coords_nw = (v[3], v[0])
            coords_ne = (v[3], v[2])
            coords_sw = (v[1], v[0])

            ew_dist = geopy.distance.geodesic(coords_nw, coords_ne).km
            ns_dist = geopy.distance.geodesic(coords_nw, coords_sw).km
            if ew_dist > 500 or ns_dist > 500:
                raise ValueError("Bounding Box is too large. It should be max 500*500km.")

        return v

    @field_validator("SCL_filter_values")
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

    @field_validator("date_range")
    def checkDateRange(cls, v):
        """Check data range."""
        limit_date = datetime(2017, 4, 1)
        today = datetime.strptime(date.today().strftime("%Y-%m-%d"), "%Y-%m-%d")
        error_msg = "Invalid date range:"
        for d in v:
            try:
                d_date = datetime.strptime(d, "%Y-%m-%d")
                if d_date < limit_date:
                    error_msg = f"{error_msg} {d} should equal or greater than 2017-04-01"
                if d_date > today:
                    error_msg = f"{error_msg} {d} should not be in the future"
            except Exception as err:
                error_msg = f"{error_msg} {err}"

        if error_msg == "Invalid date range:":
            if len(v) == 2:
                start_date = datetime.strptime(v[0], "%Y-%m-%d")
                end_date = datetime.strptime(v[1], "%Y-%m-%d")
                if start_date > end_date:
                    raise ValueError(f"{error_msg} {v[0]} should not be greater than {v[1]}.")
            return v
        else:
            raise ValueError(f"{error_msg}.")


class ResultsSettings(BaseModel, extra='forbid'):
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
    path_to_logfile: Optional[str] = Field(
        title="Path to the logfile directory.",
        description="Path to the directory, where the logfile should be stored. Logfile name is s2DataDownloader.log",
        default=results_dir
    )

    @field_validator('logging_level')
    def checkLogLevel(cls, v):
        """Check if logging level is correct."""
        if v not in ["DEBUG", "INFO", "WARN", "ERROR"]:
            raise ValueError("Logging level, it should be one of: DEBUG, INFO, WARN, or ERROR.")
        return v

    @field_validator('results_dir', 'path_to_logfile')
    def checkFolder(cls, v):
        """Check if folder location is defined - string should not be empty."""
        if v == "":
            raise ValueError("Empty string is not allowed.")
        if os.path.isabs(v) is False:
            v = os.path.realpath(v)
        return v

    @field_validator('target_resolution')
    def checkTargeResolution(cls, v):
        """Check if the target resolution is either 60, 20 or 10 meters."""
        if not (v == 60 or v == 20 or v == 10):
            raise ValueError(f"The target resolution {v} should either be 60, 20 or 10 meters")
        return v


class UserSettings(BaseModel, extra='forbid'):
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

    @model_validator(mode='before')
    def checkBboxAndSetUTMZone(cls, v):
        """Check BBOX UTM zone coverage and set UTM zone."""
        bb = v["aoi_settings"]["bounding_box"] if ("bounding_box" in v["aoi_settings"] and
                                                   len(v["aoi_settings"]["bounding_box"])) else None
        polygon = v["aoi_settings"]["polygon"] if "polygon" in v["aoi_settings"] else None
        utm_zone = v["tile_settings"]["mgrs:utm_zone"]
        latitude_band = v["tile_settings"]["mgrs:latitude_band"]
        grid_square = v["tile_settings"]["mgrs:grid_square"]

        if bb is not None:
            if polygon is not None:
                raise ValueError("Expected bbox OR polygon, not both.")
            if len(utm_zone.keys()) != 0 and len(latitude_band.keys()) != 0 and len(grid_square.keys()) != 0:
                raise ValueError("Both AOI and TileID info are set, only one should be set")
        else:
            if (polygon is None and
                    (len(utm_zone.keys()) == 0 or len(latitude_band.keys()) == 0 or len(grid_square.keys()) == 0)):
                raise ValueError("Either AOI (bbox OR polygon) or TileID info (utm_zone, latitude_band and "
                                 "grid_square) should be provided.")
            if (polygon is not None and len(utm_zone.keys()) != 0 and len(latitude_band.keys()) != 0 and
                    len(grid_square.keys()) != 0):
                raise ValueError("Both Polygon and TileID info are set, only one should be set")
        return v


class S2Settings(BaseModel, extra='forbid'):
    """Template for S2 settings in config file."""

    collections: List[str] = Field(
        title="Definition of data collection to be searched for.",
        description="Define S2 data collection.",
        default=["sentinel-2-l2a"]
    )

    stac_catalog_url: Optional[str] = Field(
        title="STAC catalog URL.",
        description="URL to access the STAC catalog.",
        default="https://earth-search.aws.element84.com/v1"
    )

    tiles_definition_path: str = Field(
        title="Tiles definition path.",
        description="Path to a shapefile.zip describing the tiles and its projections.",
        default="data/sentinel_2_index_shapefile_attr.zip"
    )

    @field_validator('stac_catalog_url')
    def check_stac_catalog_url(cls, v):
        """Check if the URL is valid."""
        ta = TypeAdapter(HttpUrl)
        try:
            ta.validate_strings(v, strict=True)
        except ValidationError as err:
            raise ValueError(f"The stac_catalog_string is invalid:{err}.")
        return v

    @field_validator('tiles_definition_path')
    def check_tiles_definition(cls, v):
        """Check if the tiles definition path exists."""
        v_abs = os.path.abspath(v)
        if not os.path.exists(v_abs):
            v_parent = os.path.abspath(os.path.join(os.pardir, v))
            if not os.path.exists(v_parent):
                raise ValueError(f"Tiles definition path is invalid: {v}")
            else:
                v = v_parent
        return v


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
            config = Config(**config).model_dump(by_alias=True)
    except JSONDecodeError as e:
        raise IOError(f'Failed to load the configuration json file => {e}')
    return config
