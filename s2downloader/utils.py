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

# third party packages
import affine  # BSD
import geopandas
import numpy as np  # BSD license
import pyproj  # MIT
import pystac
import rasterio  # BSD License (BSD)
import rasterio.io
from rasterio.merge import merge
from rasterio.warp import Resampling
from shapely.geometry import box


def saveRasterToDisk(*, out_image: np.ndarray, raster_crs: pyproj.crs.crs.CRS, out_transform: affine.Affine,
                     output_raster_path: str, save_to_uint16: bool = False):
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
    save_to_uint16 : bool, default=False, optional
        Converts NaN to 0 and saves the raster with the dtype rasterio.uint16.

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

        out_image_dtype = out_image.dtype
        if save_to_uint16:
            out_image_dtype = rasterio.uint16
        with rasterio.open(output_raster_path, 'w',
                           driver='GTiff',
                           height=img_height,
                           width=img_width,
                           count=img_count,    # nr of bands
                           dtype=out_image_dtype,
                           crs=raster_crs,
                           transform=out_transform,
                           nodata=0
                           ) as dst:
            if save_to_uint16:
                out_image_uint16 = out_image + 0.5
                np.nan_to_num(out_image_uint16, copy=False, nan=0)
                out_image_uint16 = out_image_uint16.astype(out_image_dtype)
                dst.write(out_image_uint16)
            else:
                dst.write(out_image)

    except Exception as e:  # pragma: no cover
        raise Exception(f"Failed to save raster to disk => {e}")


def validPixelsFromSCLBand(scl_src: rasterio.io.DatasetReader, scl_filter_values: list[int]) -> tuple[float, float]:
    """Percentage of valid SCL band pixels.

    Parameters
    ----------
    scl_src : rasterio.io.DatasetReader
        A DatasetReader for the SCL band.
    scl_filter_values: list, default=[0], optional
        List with the values of the SCL Band to filter out

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
    try:
        scl_band = scl_src.read()
        scl_band_nonzero = np.count_nonzero(scl_band)
        nonzero_pixels_per = (float(scl_band_nonzero) / float(scl_band.size)) * 100
        print(f"Nonzero pixels: {nonzero_pixels_per} %")

        scl_filter_values.append(0)
        scl_band_mask = np.where(np.isin(scl_band, scl_filter_values), 0, 1)
        valid_pixels_per = (float(np.count_nonzero(scl_band_mask)) / float(scl_band_nonzero)) * 100
        print(f"Valid pixels: {valid_pixels_per} %")

        return nonzero_pixels_per, valid_pixels_per
    except Exception as e:  # pragma: no cover
        raise Exception(f"Failed to count the number of valid pixels for the SCl band => {e}")


def cloudMaskingFromSCLBand(*,
                            band_src: rasterio.io.DatasetReader,
                            scl_src: rasterio.io.DatasetReader,
                            scl_filter_values: list[int],
                            target_resolution: int = None,
                            resampling_method: Resampling,
                            ) -> np.ndarray:
    """Based on the SCL band categorization, the input data is masked (clouds, cloud shadow, snow).

    Parameters
    ----------
    band_src : rasterio.io.DatasetReader
        A DatasetReader for a raster band.
    scl_src : rasterio.io.DatasetReader
        A DatasetReader for the SCL band.
    scl_filter_values: list, default=[0], optional
        List with the values of the SCL Band to filter out
    target_resolution: int, default=None, optional
        Target resolution, if None keep original.
    resampling_method: rasterio.wrap.Resampling
        The resampling method for a raster band.

    Returns
    -------
    : np.ndarray
        Masked image band.

    Raises
    ------
    Exception
        Failed to mask pixels from SCL band.
    """
    try:
        band_scale_factor = 1.0

        if target_resolution is not None:
            scl_scale_factor = target_resolution / scl_src.transform[0]
            band_scale_factor = target_resolution / band_src.transform[0]
        else:
            scl_scale_factor = band_src.transform[0] / scl_src.transform[0]

        if scl_scale_factor != 1.0:
            scl_band = scl_src.read(
                out_shape=(
                    scl_src.count,
                    int(scl_src.height * scl_scale_factor),
                    int(scl_src.width * scl_scale_factor)
                ),
                resampling=Resampling.nearest
            )
        else:
            scl_band = scl_src.read()

        if band_scale_factor != 1.0:
            raster_band = band_src.read(
                out_shape=(
                    band_src.count,
                    int(band_src.height * band_scale_factor),
                    int(band_src.width * band_scale_factor)
                ),
                resampling=resampling_method
            )
        else:
            raster_band = band_src.read()

        scl_filter_values.append(0)
        scl_band_mask = np.where(np.isin(scl_band, scl_filter_values), 0, 1)

        # Mask out Clouds
        image_band_masked = raster_band * scl_band_mask
        return image_band_masked
    except Exception as e:  # pragma: no cover
        raise Exception(f"Failed to mask pixels from SCl band => {e}")


def groupItemsPerDate(items_list: list[pystac.item.Item]) -> dict:
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
        date = item.datetime.strftime("%Y%m%d")
        if date in items_per_date.keys():
            items_per_date[date].append(item)
        else:
            items_per_date[date] = [item]
    return items_per_date


def getBoundsUTM(bounds: tuple, utm_zone: int) -> tuple:
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


def mosaicBands(bands: list[str],
                mosaic_dates: dict,
                output_dir: str,
                bounds: tuple,
                resolution: tuple = None,
                resampling_method: Resampling = Resampling.nearest):
    """Create a mosaic for each band.

    Parameters
    ----------
    bands : list[str]
        A list of bands.
    mosaic_dates : dict
        A dictionary with STAC items grouped by date.
    output_dir: str
        Output directory.
    bounds: tuple
        Bounds of the mosaic.
    resolution: tuple, default=None, optional
        Target resolution (x,y) in meters, if None keep original.
    resampling_method: rasterio.wrap.Resampling
        The resampling method for a raster band.
    """
    for date in mosaic_dates.keys():
        for band in bands:
            srcs_to_mosaic = []
            sensor_name = mosaic_dates[date][0].id[0:3]
            for item in mosaic_dates[date]:
                srcs_to_mosaic.append(rasterio.open(item.assets[band].href))

            mosaic_file_path = os.path.join(output_dir, f"{sensor_name}_{date}_{band}.tif")
            arr, out_trans = merge(datasets=srcs_to_mosaic,
                                   target_aligned_pixels=True,
                                   bounds=bounds,
                                   res=resolution,
                                   resampling=resampling_method)
            output_meta = arr.meta.copy()
            output_meta.update({
                "driver": "GTiff"
            })
            with rasterio.open(mosaic_file_path, 'w', **output_meta) as m:
                m.write(arr)
