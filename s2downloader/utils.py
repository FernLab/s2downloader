# -*- coding: utf-8 -*-
"""Utils module for S2Downloader."""
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

import affine
import geopandas
import logging
from logging import Logger
import numpy as np
import pyproj
import pystac
import rasterio
import rasterio.io
from shapely.geometry import box, Point
import shapely.geometry as sg


def saveRasterToDisk(*, out_image: np.ndarray, raster_crs: pyproj.crs.crs.CRS, out_transform: affine.Affine,
                     output_raster_path: str):
    """Save raster imagery data to disk.

    Parameters
    ----------
    out_image : np.ndarray
        Array containing output raster data.
    raster_crs : pyproj.crs.crs.CRS
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

        with rasterio.open(output_raster_path, 'w',
                           driver='GTiff',
                           height=img_height,
                           width=img_width,
                           count=img_count,    # nr of bands
                           dtype=out_image.dtype,
                           crs=raster_crs,
                           transform=out_transform,
                           nodata=0
                           ) as dst:
            dst.write(out_image)

    except Exception as e:  # pragma: no cover
        raise Exception(f"Failed to save raster to disk => {e}")


def validPixelsFromSCLBand(*,
                           scl_band: np.ndarray,
                           scl_filter_values: list[int],
                           logger: Logger = None) -> tuple[float, float]:
    """Percentage of valid SCL band pixels.

    Parameters
    ----------
    scl_band : np.ndarray
        The SCL band.
    scl_filter_values: list
        List with the values of the SCL Band to filter out
    logger: Logger
        Logger handler.

    Returns
    -------
    : float
        Percentage of data pixels.
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
        scl_band_nonzero = np.count_nonzero(scl_band)
        nonzero_pixels_per = (float(scl_band_nonzero) / float(scl_band.size)) * 100
        logger.info(f"Nonzero pixels: {nonzero_pixels_per} %")

        scl_band_mask = np.where(np.isin(scl_band, scl_filter_values), 0, 1)
        valid_pixels_per = (float(np.count_nonzero(scl_band_mask)) / float(scl_band.size)) * 100
        logger.info(f"Valid pixels: {valid_pixels_per} %")

        return nonzero_pixels_per, valid_pixels_per
    except Exception as e:  # pragma: no cover
        raise Exception(f"Failed to count the number of valid pixels for the SCl band => {e}")


def groupItemsPerDate(*, items_list: list[pystac.item.Item]) -> dict:
    """Group STAC Items per date.

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
        if date in items_per_date.keys():
            items_per_date[date].append(item)
        else:
            items_per_date[date] = [item]
    return items_per_date


def getBoundsUTM(*, bounds: tuple, utm_zone: int) -> tuple:
    """Get the bounds of a bounding box in UTM coordinates.

    Parameters
    ----------
    bounds : tuple
        Bounds defined as lat/long.
    utm_zone : int
        UTM zone number.

    Returns
    -------
    : tuple
        Bounds reprojected to the UTM zone.
    """
    bounding_box = box(*bounds)
    bbox = geopandas.GeoSeries([bounding_box], crs=4326)
    bbox = bbox.to_crs(crs=32600+utm_zone)
    return tuple(bbox.bounds.values[0])


def getUTMZoneBB(*, bbox: list[float], bb_max_utm_zone_overlap: int = 50000) -> int:
    """Create a mosaic for each band.

    Parameters
    ----------
    bbox : list[float]
        Bounding box bounds.
    bb_max_utm_zone_overlap : int, default=50000, optional
        Max overlap of the BB over a second UTM zone.

    Returns
    -------
    : int
        UTM zone number.

    Raises
    ------
    ValueError
        For invalid Bounding Box.
    """
    bb_geom = sg.box(*bbox, ccw=True)
    utm_df = geopandas.read_file(os.path.abspath("data/World_UTM_Grid.zip"))
    utm_intersections = utm_df.intersection(bb_geom)
    utm_indices = list(utm_intersections.loc[~utm_intersections.is_empty].index)
    utms = utm_intersections.iloc[utm_indices]

    utm_zones = utm_df.iloc[utm_indices]['ZONE'].values
    if np.unique(utm_zones).size == 1:
        return int(np.unique(utm_zones)[0])
    elif np.unique(utm_zones).size == 2:
        min_utm = np.min(utm_zones)
        max_utm = np.max(utm_zones)
        if max_utm > min_utm+1:
            raise ValueError("The bounding box does not overlap over two consecutive UTM zones.")
        else:
            for utm_id in utms.index:
                if 32 in utm_zones and utm_df.iloc[utm_id]['ZONE'] == 33:
                    bb_box = geopandas.GeoSeries(utms.loc[utm_id], crs=4326)
                    bb_box_utm = bb_box.to_crs(32600 + utm_df.iloc[utm_id]['ZONE'])[0]

                    # get coordinates of polygon vertices
                    x, y = bb_box_utm.exterior.coords.xy

                    # get length of bounding box edges
                    edge_length = (
                        Point(x[0], y[0]).distance(Point(x[1], y[1])), Point(x[1], y[1]).distance(Point(x[2], y[2])))

                    # get length of polygon as the longest edge of the bounding box
                    length = max(edge_length)

                    if length > bb_max_utm_zone_overlap:
                        raise ValueError(
                            f"The bounding box overlaps UTM zones 32 and 33, and its a length over the"
                            f" 33 UTM zone is greater than {bb_max_utm_zone_overlap} meters: {length} meters!")
            return int(min_utm)
    else:
        raise ValueError(f"The bounding box overlaps more than 2 UTM zones: {np.unique(utm_zones)}!")
