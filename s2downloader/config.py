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
import json
import os
import time
from datetime import date, datetime
from enum import Enum
from json import JSONDecodeError
from typing import Any, Dict, List, Optional, Union

import geopy.distance
import pydantic

# third party packages
from geojson_pydantic import Polygon
from pydantic import BaseModel, Field, HttpUrl, StrictBool, TypeAdapter, field_validator, model_validator
from pydantic_core import ValidationError


class ResamplingMethodName(str, Enum):
    """Enum for supported and tested resampling methods."""

    cubic = "cubic"
    bilinear = "bilinear"
    nearest = "nearest"


class S2Platform(str, Enum):
    """Enum for Sentinel-2 platform."""

    S2A = "sentinel-2a"
    S2B = "sentinel-2b"


class TileSettings(BaseModel, extra="forbid"):
    """Template for Tile settings in config file."""

    platform: Optional[Dict] = Field(
        title="Sentinel-2 platform.",
        description="For which Sentinel-2 platform should data be downloaded.",
        default={"in": [S2Platform.S2A, S2Platform.S2B]},
    )

    nodata_pixel_percentage: Dict = Field(
        title="NoData pixel percentage",
        description="Percentage of NoData pixel.",
        alias="s2:nodata_pixel_percentage",
        default={"gt": 10},
    )
    utm_zone: Dict = Field(title="UTM zone", description="UTM zones for which to search data.", alias="mgrs:utm_zone")
    latitude_band: Dict = Field(
        title="Latitude band", description="Latitude band for which to search data.", alias="mgrs:latitude_band"
    )
    grid_square: Dict = Field(
        title="Grid square", description="Grid square for which to search data.", alias="mgrs:grid_square"
    )
    cloud_cover: Dict = Field(
        title="Cloud coverage", description="Percentage of cloud coverage.", alias="eo:cloud_cover", default={"lt": 20}
    )
    bands: List[str] = Field(title="Bands", description="List of bands.", default=["blue", "green", "rededge1"])

    @field_validator("nodata_pixel_percentage", "cloud_cover")
    def checkCoverage(cls, v: Dict[str, int]) -> Dict[str, int]:  # noqa: N805
        """
        Validate that the coverage dictionary has the correct format and values.

        The dictionary must contain exactly one key-value pair. The key must be
        a valid operator (`lte`, `lt`, `eq`, `gte`, or `gt`), and the value must be
        an integer between 0 and 100 (inclusive).

        Parameters
        ----------
        v : dict of str, int
            A dictionary with a single key-value pair, where the key is a
            string operator (`lte`, `lt`, `eq`, `gte`, or `gt`), and the value
            is an integer (0-100).

        Returns
        -------
        dict of str, int
            The validated input dictionary.

        Raises
        ------
        ValueError
            If the dictionary does not contain exactly one key-value pair.
        ValueError
            If the key is not one of the allowed operators (`lte`, `lt`, `eq`, `gte`, `gt`).
        ValueError
            If the value is not an integer between 0 and 100 (inclusive).
        """
        if len(v.keys()) != 1:
            raise ValueError("It should be a dictionary with one key (operator) value (integer) pair.")
        for key in v:
            if key not in ["lte", "lt", "eq", "gte", "gt"]:
                raise ValueError("The operator should be one of: lte, lt, eq, gte or gt.")
            value = v[key]
            if not isinstance(value, int) or value < 0 or value > 100:
                raise ValueError(f"The value ({str(value)}) should be an integer between 0 and 100.")
        return v

    @field_validator("bands")
    def checkBands(cls, v: List[str]) -> List[str]:  # noqa: N805
        """
        Validate that the bands list is correctly set.

        The list must contain only supported band names, and no duplicates are allowed.
        The supported band names are:
        - "coastal"
        - "blue"
        - "green"
        - "red"
        - "rededge1"
        - "rededge2"
        - "rededge3"
        - "nir"
        - "nir08"
        - "nir09"
        - "cirrus"
        - "swir16"
        - "swir22"

        Parameters
        ----------
        v : list of str
            A list of band names to validate.

        Returns
        -------
        list of str
            The validated list of band names.

        Raises
        ------
        ValueError
            If the list contains unsupported band names.
        ValueError
            If the list contains duplicate band names.
        ValueError
            If the list is empty.
        """
        if len(v) == 0 or not set(v).issubset([
            "coastal",
            "blue",
            "green",
            "red",
            "rededge1",
            "rededge2",
            "rededge3",
            "nir",
            "nir08",
            "nir09",
            "cirrus",
            "swir16",
            "swir22",
        ]):
            raise ValueError(
                "Only the following band names are supported: coastal, blue, green, red, rededge1,"
                " rededge2, rededge3, nir, nir08, nir09, cirrus, swir16, swir22."
            )
        if len(v) != len(set(v)):
            raise ValueError("Remove duplicates.")
        return v

    @field_validator("utm_zone", "latitude_band", "grid_square")
    def checkTileInfo(cls, v: Dict[str, Any], field: pydantic.ValidationInfo) -> Dict[str, Any]:  # noqa: N805
        """
        Validate that the tile information dictionary is correctly set.

        The dictionary should have keys corresponding to supported operators (`eq`, `in`),
        with the following conditions:
        - If the operator is `eq`, the value must match the expected type:
          - `str` for general fields
          - `int` for the field `utm_zone`.
        - If the operator is `in`, the value must be a list of the expected type.
        - Unsupported operators will raise an error.

        Parameters
        ----------
        v : dict of str, Any
            The tile information dictionary containing operators and their corresponding values.
        field : pydantic.ValidationInfo
            Information about the field being validated, used to determine the expected value type.

        Returns
        -------
        dict of str, Any
            The validated input dictionary.

        Raises
        ------
        ValueError
            If unsupported operators are used.
        ValueError
            If the value for the `eq` operator is not of the expected type.
        ValueError
            If the value for the `in` operator is not a list or contains elements of the wrong type.
        """
        v_type = str
        if field.field_name == "utm_zone":
            v_type = int
        if len(v.keys()) > 0:
            for key in v:
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


class AoiSettings(BaseModel, extra="forbid"):
    """Template for AOI settings in config file."""

    bounding_box: Union[List[float], None] = Field(
        title="Bounding Box for AOI.",
        description="SW and NE corner coordinates of AOI Bounding Box.",
        max_length=4,
        default=None,
    )
    polygon: Union[Polygon, None] = Field(
        title="Polygon for the AOI.", description="Polygon defined as in GeoJson.", default=None
    )
    apply_SCL_band_mask: Optional[StrictBool] = Field(  # noqa: N815
        title="Apply a filter mask from SCL.", description="Define if SCL masking should be applied.", default=True
    )
    SCL_filter_values: List[int] = Field(
        title="SCL values for the filter mask.",
        description="Define which values of SCL band should be applied as filter.",
        default=[3, 7, 8, 9, 10],
    )
    aoi_min_coverage: float = Field(
        title="Minimum percentage of valid pixels after noData filtering.",
        description="Define a minimum percentage of pixels that should be valid (not noData) after noData filtering"
        " in the aoi.",
        default=0.0,
        ge=0.0,
        le=100.0,
    )
    SCL_masked_pixels_max_percentage: float = Field(
        title="Maximum percentage of SCL masked pixels after noData filtering.",
        description="Define a maximum percentage of pixels that are filtered by a cloud mask "
        "after noData filtering in the aoi.",
        default=0.0,
        ge=0.0,
        le=100.0,
    )
    valid_pixels_min_percentage: float = Field(
        title="Minimum percentage of valid pixels after noData filtering and cloud masking.",
        description="Define a minimum percentage of pixels that should be valid after noData filtering and cloud "
        "masking in the AOI.",
        default=0.0,
        ge=0.0,
        le=100.0,
    )
    resampling_method: ResamplingMethodName = Field(
        title="Rasterio resampling method name.",
        description="Define the method to be used when resampling.",
        default=ResamplingMethodName.cubic,
    )
    date_range: List[str] = Field(
        title="Date range.",
        description="List with the start and end date. If the same it is a single date request.",
        min_length=1,
        max_length=2,
        default=["2021-09-01", "2021-09-05"],
    )

    @field_validator("bounding_box")
    def validateBB(cls, v: List[float]) -> List[float]:  # noqa: N805
        """
        Validate that the bounding box (BB) is properly defined and within the allowable size.

        The bounding box must:
        - Contain exactly four values representing two latitude-longitude pairs in the order:
          [west_lon, south_lat, east_lon, north_lat].
        - Have coordinates where `west_lon < east_lon` and `south_lat < north_lat`.
        - Define a rectangular region that does not exceed 500x500 km in size.

        Parameters
        ----------
        v : list of float
            A list containing four float values representing the bounding box.

        Returns
        -------
        list of float
            The validated bounding box.

        Raises
        ------
        ValueError
            If the bounding box does not contain exactly four coordinates.
        ValueError
            If the coordinates are not logically ordered (`west_lon >= east_lon` or `south_lat >= north_lat`).
        ValueError
            If the bounding box exceeds the maximum size of 500x500 km.
        """
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
    def checkSCLFilterValues(cls, v: List[int]) -> List[int]:  # noqa: N805
        """
        Validate that the SCL filter values are correctly set.

        The SCL (Scene Classification Layer) filter values must:
        - Be a subset of the allowed values: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11].
        - Contain no duplicate values.
        - Contain at least one value (cannot be an empty list).

        Parameters
        ----------
        v : list of int
            A list of integers representing the SCL filter values.

        Returns
        -------
        list of int
            The validated list of SCL filter values.

        Raises
        ------
        ValueError
            If the values are not a subset of the allowed SCL values.
        ValueError
            If the list contains duplicate values.
        ValueError
            If the list is empty.
        """
        if not set(v).issubset([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]):
            raise ValueError("Only the following values are allowed: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11.")
        if len(v) != len(set(v)):
            raise ValueError("Remove duplicates.")
        if len(v) == 0:
            raise ValueError(
                "Provide a SCL class for filtering. If no filtering is wanted keep default values and "
                "set apply_SCL_band_mask to 'False'."
            )
        return v

    @field_validator("date_range")
    def checkDateRange(cls, v: List[str]) -> List[str]:  # noqa: N805
        """
        Validate that the date range is correctly set.

        The date range must:
        - Contain valid date strings in the format `YYYY-MM-DD`.
        - Be within the range of `2017-04-01` to today's date.
        - If two dates are provided, the start date must not be later than the end date.

        Parameters
        ----------
        v : list of str
            A list of date strings to validate.

        Returns
        -------
        list of str
            The validated list of date strings.

        Raises
        ------
        ValueError
            If any date is before `2017-04-01`.
        ValueError
            If any date is in the future.
        ValueError
            If the start date is greater than the end date when two dates are provided.
        ValueError
            If the date format is invalid.
        """
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


class ResultsSettings(BaseModel, extra="forbid"):
    """Template for raster_saving_settings in config file."""

    request_id: Optional[int] = Field(
        title="Request ID.", description="Request ID to identify the request.", default=round(time.time() * 1000)
    )
    results_dir: str = Field(
        title="Location of the output directory.", description="Define folder where all output data should be stored."
    )
    target_resolution: Optional[int] = Field(
        title="Target resolution.",
        description="Target resolution in meters, it should be either 60, 20 or 10 meters.",
        default=10,
        ge=10,
        le=60,
    )
    download_data: Optional[StrictBool] = Field(
        title="Download Data.", description="For each scene download the data.", default=True
    )
    download_thumbnails: Optional[StrictBool] = Field(
        title="Download thumbnails.", description="For each scene download the provided thumbnail.", default=False
    )
    download_overviews: Optional[StrictBool] = Field(
        title="Download preview.", description="For each scene download the provided preview.", default=False
    )
    logging_level: Optional[str] = Field(
        title="Logging level.",
        description="Logging level, it should be one of: DEBUG, INFO, WARN, or ERROR.",
        default="INFO",
    )
    path_to_logfile: str = Field(
        title="Path to the logfile directory.",
        description="Path to the directory, where the logfile should be stored. Logfile name is s2DataDownloader.log",
    )

    @field_validator("logging_level")
    def checkLogLevel(cls, v: str) -> str:  # noqa: N805
        """
        Validate that the logging level is correct.

        The logging level must be one of the following:
        - "DEBUG"
        - "INFO"
        - "WARN"
        - "ERROR"

        Parameters
        ----------
        v : str
            The logging level to validate.

        Returns
        -------
        str
            The validated logging level.

        Raises
        ------
        ValueError
            If the logging level is not one of the allowed values.
        """
        if v not in ["DEBUG", "INFO", "WARN", "ERROR"]:
            raise ValueError("Logging level, it should be one of: DEBUG, INFO, WARN, or ERROR.")
        return v

    @field_validator("results_dir", "path_to_logfile")
    def checkFolder(cls, v: str) -> str:  # noqa: N805
        """
        Validate that a folder path is defined and is not an empty string.

        If the folder path is relative, it will be converted to an absolute path.

        Parameters
        ----------
        v : str
            The folder path to validate.

        Returns
        -------
        str
            The validated folder path, converted to an absolute path if it was relative.

        Raises
        ------
        ValueError
            If the folder path is an empty string.
        """
        if v == "":
            raise ValueError("Empty string is not allowed.")
        if os.path.isabs(v) is False:
            v = os.path.realpath(v)
        return v

    @field_validator("target_resolution")
    def checkTargeResolution(cls, v: int) -> int:  # noqa: N805
        """
        Validate that the target resolution is correct.

        The target resolution must be one of the following values:
        - 60
        - 20
        - 10

        Parameters
        ----------
        v : int
            The target resolution to validate.

        Returns
        -------
        int
            The validated target resolution.

        Raises
        ------
        ValueError
            If the target resolution is not one of the allowed values.
        """
        if not (v == 60 or v == 20 or v == 10):
            raise ValueError(f"The target resolution {v} should either be 60, 20 or 10 meters")
        return v


class UserSettings(BaseModel, extra="forbid"):
    """Template for user_path_settings in config file."""

    aoi_settings: AoiSettings = Field(title="AOI Settings", description="")

    tile_settings: TileSettings = Field(title="Tile Settings.", description="")

    result_settings: ResultsSettings = Field(title="Result Settings.", description="")

    @model_validator(mode="before")
    def checkBboxAndSetUTMZone(cls, v: Dict[str, Any]) -> Dict[str, Any]:  # noqa: N805
        """
        Validate the bounding box (BBOX) and set the UTM zone.

        This function ensures that either the BBOX or polygon information is provided in the AOI settings,
        but not both. It also validates that if no AOI is provided, the TileID information
        (utm_zone, latitude_band, grid_square) is fully specified.

        Parameters
        ----------
        v : dict
            A dictionary containing AOI settings (`bounding_box` or `polygon`) and TileID information
            (`mgrs:utm_zone`, `mgrs:latitude_band`, `mgrs:grid_square`).

        Returns
        -------
        dict
            The validated input dictionary.

        Raises
        ------
        ValueError
            If both BBOX and polygon are set in AOI settings.
        ValueError
            If both AOI settings (BBOX or polygon) and TileID information are set.
        ValueError
            If neither AOI settings nor complete TileID information is provided.
        ValueError
            If polygon and TileID information are both set.
        """
        bb = (
            v["aoi_settings"]["bounding_box"]
            if ("bounding_box" in v["aoi_settings"] and len(v["aoi_settings"]["bounding_box"]))
            else None
        )
        polygon = v["aoi_settings"].get("polygon", None)
        utm_zone = v["tile_settings"]["mgrs:utm_zone"]
        latitude_band = v["tile_settings"]["mgrs:latitude_band"]
        grid_square = v["tile_settings"]["mgrs:grid_square"]

        if bb is not None:
            if polygon is not None:
                raise ValueError("Expected bbox OR polygon, not both.")
            if len(utm_zone.keys()) != 0 and len(latitude_band.keys()) != 0 and len(grid_square.keys()) != 0:
                raise ValueError("Both AOI and TileID info are set, only one should be set")
        else:
            if polygon is None and (
                len(utm_zone.keys()) == 0 or len(latitude_band.keys()) == 0 or len(grid_square.keys()) == 0
            ):
                raise ValueError(
                    "Either AOI (bbox OR polygon) or TileID info (utm_zone, latitude_band and "
                    "grid_square) should be provided."
                )
            if (
                polygon is not None
                and len(utm_zone.keys()) != 0
                and len(latitude_band.keys()) != 0
                and len(grid_square.keys()) != 0
            ):
                raise ValueError("Both Polygon and TileID info are set, only one should be set")
        return v


class S2Settings(BaseModel, extra="forbid"):
    """Template for S2 settings in config file."""

    collections: List[str] = Field(
        title="Definition of data collection to be searched for.",
        description="Define S2 data collection.",
        default=["sentinel-2-l2a"],
    )

    stac_catalog_url: Optional[str] = Field(
        title="STAC catalog URL.",
        description="URL to access the STAC catalog.",
        default="https://earth-search.aws.element84.com/v1",
    )

    tiles_definition_path: str = Field(
        title="Tiles definition path.",
        description="Path to a shapefile.zip describing the tiles and its projections.",
        default="data/sentinel_2_index_shapefile_attr.zip",
    )

    @field_validator("stac_catalog_url")
    def check_stac_catalog_url(cls, v: str) -> str:  # noqa: N805
        """
        Validate that the STAC catalog URL is a valid HTTP/HTTPS URL.

        Parameters
        ----------
        v : str
            The STAC catalog URL to validate.

        Returns
        -------
        str
            The validated STAC catalog URL.

        Raises
        ------
        ValueError
            If the URL is not a valid HTTP/HTTPS URL.
        """
        ta = TypeAdapter(HttpUrl)
        try:
            ta.validate_strings(v, strict=True)
        except ValidationError as err:
            raise ValueError(f"The stac_catalog_string is invalid:{err}.") from err
        return v

    @field_validator("tiles_definition_path")
    def check_tiles_definition(cls, v: str) -> str:  # noqa: N805
        """
        Validate that the tiles definition path exists.

        If the provided path is relative, it will be checked against its absolute path.
        If the path does not exist, the parent directory will also be checked.

        Parameters
        ----------
        v : str
            The path to the tiles definition file to validate.

        Returns
        -------
        str
            The absolute path of the tiles definition file if it exists.

        Raises
        ------
        ValueError
            If the path or its parent directory does not exist.
        """
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

    user_settings: UserSettings = Field(title="User settings.", description="")

    s2_settings: S2Settings = Field(title="Sentinel 2 settings.", description="")


def loadConfiguration(*, path: str) -> dict:
    """
    Load configuration json file.

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
    OSError
        Failed to load the configuration json file.
    """
    try:
        with open(path) as config_fp:
            config = json.load(config_fp)
            config = Config(**config).model_dump(by_alias=True)
    except JSONDecodeError as e:
        raise OSError(f"Failed to load the configuration json file => {e}") from e
    return config
