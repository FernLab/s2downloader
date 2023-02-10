# -*- coding: utf-8 -*-
"""Utils module for S2Downloader."""

import affine
import geopandas
import logging
from logging import Logger
import numpy as np
import pyproj
import pystac
import rasterio
import rasterio.io
from shapely.geometry import box


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


def getBoundsUTM(*, bounds: tuple, bb_crs: int) -> tuple:
    """Get the bounds of a bounding box in UTM coordinates.

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


def getUTMZoneBB(*, tiles_gpd: geopandas.GeoDataFrame, bbox: list[float], logger: Logger = None) -> int:
    """Get the UTM zone for the bounding box.

    Parameters
    ----------
    tiles_gpd : geopandas.GeoDataFrame
        Path to the tiles shapefile.
    bbox : list[float]
        The bounds defined as lat/long.
    logger: Logger
        Logger handler.

    Returns
    -------
    : tuple
        Bounds reprojected to the UTM zone.

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
        for f in s2_tiles_g['EPSG']:
            tiles_polygon = s2_tiles.loc[s2_tiles.EPSG == f[0]].geometry.unary_union
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
