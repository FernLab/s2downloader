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
"""Utils module for S2Downloader."""

import logging
from datetime import datetime
from logging import Logger

import affine
import geopandas
import numpy as np
import pystac
import rasterio
import rasterio.io
from pyproj import Proj, Transformer
from pyproj.crs.crs import CRS
from shapely.geometry import Polygon, box
from shapely.ops import transform


def saveRasterToDisk(*, out_image: np.ndarray, raster_crs: CRS, out_transform: affine.Affine, output_raster_path: str):
    """
    Save raster imagery data to disk.

    Parameters
    ----------
    out_image : np.ndarray
        Array containing output raster data.
    raster_crs : CRS
        Output raster coordinate system.
    out_transform : affine.Affine
        Output raster transformation parameters.
    output_raster_path : str
        Path to raster output location.

    Raises
    ------
    Exception
        Failed to save raster to disk.
    """
    try:
        img_height = None
        img_width = None
        img_count = None
        # save raster to disk
        # for 2D images
        if out_image.ndim == 2:
            img_height = out_image.shape[0]
            img_width = out_image.shape[1]
            img_count = 1
            out_image = out_image[np.newaxis, :, :]

        # for 3D images
        if out_image.ndim == 3:
            img_height = out_image.shape[1]
            img_width = out_image.shape[2]
            img_count = out_image.shape[0]

        with rasterio.open(
            output_raster_path,
            "w",
            driver="GTiff",
            height=img_height,
            width=img_width,
            count=img_count,  # nr of bands
            dtype=out_image.dtype,
            crs=raster_crs,
            transform=out_transform,
            compress="lzw",
            nodata=0,
        ) as dst:
            dst.write(out_image)

    except Exception as e:  # pragma: no cover
        raise Exception(f"Failed to save raster to disk => {e}") from e


def validPixelsFromSCLBand(
    *, scl_band: np.ndarray, scl_filter_values: list[int], aoi_mask: np.ndarray = None, logger: Logger = None
) -> tuple[float, float, float]:
    """
    Percentage of valid SCL band pixels.

    Parameters
    ----------
    scl_band : np.ndarray
        The SCL band.
    scl_filter_values: list
        List with the values of the SCL Band to filter out.
    aoi_mask : np.ndarray
        AOI mask in case it is defined as a Polygon.
    logger: Logger
        Logger handler.

    Returns
    -------
    : float
        Percentage of data pixels.
    : float
        Percentage of masked pixels.
    : float
        Percentage of non-masked out pixels

    Raises
    ------
    Exception
        Failed to calculate percentage of valid SCL band pixels.
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    try:
        aoi_size = scl_band.size
        scl_band_nonzero = np.count_nonzero(scl_band)
        if aoi_mask is not None:
            aoi_size = aoi_size - np.count_nonzero(aoi_mask is False)
        nonzero_pixels_per = (float(scl_band_nonzero) / float(aoi_size)) * 100
        logger.info(f"Nonzero pixels: {nonzero_pixels_per} %")

        scl_band_scl_mask = np.where(np.isin(scl_band, scl_filter_values), 1, 0)
        masked_pixels_per = (float(np.count_nonzero(scl_band_scl_mask)) / float(scl_band_nonzero)) * 100
        logger.info(f"Masked pixels: {masked_pixels_per} %")

        scl_band_mask = np.where(np.isin(scl_band, scl_filter_values), 0, 1)
        valid_pixels_per = (float(np.count_nonzero(scl_band_mask * scl_band)) / float(aoi_size)) * 100
        logger.info(f"Valid pixels: {valid_pixels_per} %")

        return nonzero_pixels_per, masked_pixels_per, valid_pixels_per
    except Exception as e:  # pragma: no cover
        raise Exception(f"Failed to count the number of valid pixels for the SCl band => {e}") from e


def groupItemsPerDate(*, items_list: list[pystac.item.Item]) -> dict:
    """
    Group STAC Items per date.

    Parameters
    ----------
    items_list : list[pystac.item.Item]
        List of STAC items.

    Returns
    -------
    : dict
        A dictionary with item grouped by date.
    """
    items_per_date = {}
    for item in items_list:
        date = item.datetime.strftime("%Y-%m-%d")
        if date in items_per_date:
            items_per_date[date].append(item)
        else:
            items_per_date[date] = [item]
    return items_per_date


def projectPolygon(poly: Polygon, source_crs: int, target_crs: int) -> Polygon:
    """
    Project polygon.

    Parameters
    ----------
    poly : Polygon
        AOI defined either as a bounding box or a Polygon.
    source_crs : int
        Source CRS code.
    target_crs : int
        Target CRS code.

    Returns
    -------
    : Polygon
        Projected polygon to the target CRS.
    """
    source_proj = Proj(f"epsg:{source_crs}")
    target_proj = Proj(f"epsg:{target_crs}")
    transformer = Transformer.from_proj(source_proj, target_proj, always_xy=True)

    def project_coords(x: float, y: float, z: float = None) -> tuple[float, ...]:
        """
        Project a pair of coordinates (x,y).

        Parameters
        ----------
        x : float
            X coordinate.
        y: float
            Y coordinate.
        z: float
            Z coordinate.

        Returns
        -------
        Tuple : Transform of two coordinates.
        """
        return transformer.transform(x, y, z)

    return transform(project_coords, poly)


def getBoundsUTM(*, bounds: tuple, bb_crs: int) -> tuple:
    """
    Get the bounds of a bounding box in UTM coordinates.

    Parameters
    ----------
    bounds : tuple
        Bounds defined as lat/long.
    bb_crs : int
        UTM zone number.

    Returns
    -------
    : tuple
        Bounds reprojected to the UTM zone.
    """
    bounding_box = box(*bounds)
    bbox = geopandas.GeoSeries([bounding_box], crs=4326)
    bbox = bbox.to_crs(crs=bb_crs)
    return tuple(bbox.bounds.values[0])


def getUTMZoneBB(*, tiles_gpd: geopandas.GeoDataFrame, bbox: tuple, logger: Logger = None) -> int:
    """
    Get the UTM zone for the bounding box.

    Parameters
    ----------
    tiles_gpd : geopandas.GeoDataFrame
        Path to the tiles shapefile.
    bbox : tuple
        The bounds defined as lat/long.
    logger: Logger
        Logger handler.

    Returns
    -------
    : int
        The UTM zone.
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    bb_crs = 0
    bounding_box = box(*bbox)

    tiles_intersections = tiles_gpd.intersection(bounding_box)
    s2_indices = list(tiles_intersections.loc[~tiles_intersections.is_empty].index)
    s2_tiles = tiles_gpd.iloc[s2_indices]

    # group tiles per EPSG code
    s2_tiles_g = s2_tiles.groupby(by="EPSG")

    # check if the polygon fits within one EPGS code
    fits_one_epgs = False
    if len(s2_tiles_g) != 1:
        f = ""
        for f in s2_tiles_g["EPSG"]:
            tiles_polygon = s2_tiles.loc[f[0] == s2_tiles.EPSG].geometry.union_all()
            if tiles_polygon.contains(bounding_box):
                fits_one_epgs = True
                break

        # Remove the polygon and add the intersections
        if fits_one_epgs:
            bb_crs = int(f[0])
        else:
            logger.warning("The bounding box it is not contained by a single UTM zone")
    else:
        bb_crs = int(list(s2_tiles_g.groups)[0])

    utm_zone = bb_crs
    if bb_crs != 0:
        utm_zone = bb_crs - 32600
        if (bb_crs - 32600) > 100:
            utm_zone = bb_crs - 32700

    return utm_zone


def remove_duplicates_and_ensure_data_consistency(item_list_dict: list) -> list:
    """
    Remove dicts with duplicate date based on highest s2:processing_baseline and check data consistency.

    Parameters
    ----------
    item_list_dict : list
        Contains the dicts of all queried data.

    Returns
    -------
    : list
       Contains remaining data dicts.
    """
    # find duplicates based on the date and tile location of the images, for dates only compare yyyy-mm-dd part
    duplicates = {}
    for item in item_list_dict:
        date_part = datetime.strptime(item["properties"]["datetime"][:10], "%Y-%m-%d")
        key = (
            date_part,
            item["properties"]["mgrs:utm_zone"],
            item["properties"]["mgrs:latitude_band"],
            item["properties"]["mgrs:grid_square"],
        )
        if key in duplicates:
            duplicates[key].append(item)
        else:
            duplicates[key] = [item]

    # for each group of duplicates, find the one with the highest value of s2:processing_baseline
    for _, items in duplicates.items():
        if len(items) > 1:  # Only if there are duplicates
            max_b_item = max(items, key=lambda x: x["properties"]["s2:processing_baseline"])
            items.remove(max_b_item)
            for item in items:
                item_list_dict.remove(item)

    # for remaining list without duplicate dates, keep only data that is comparable to each other,
    item_list_dict = [
        item
        for item in item_list_dict
        if (
            float(item["properties"]["s2:processing_baseline"]) >= 4.0
            and item["properties"]["earthsearch:boa_offset_applied"] is True
        )
        or (
            float(item["properties"]["s2:processing_baseline"]) < 4.0
            and item["properties"]["earthsearch:boa_offset_applied"] is False
        )
    ]

    return item_list_dict
