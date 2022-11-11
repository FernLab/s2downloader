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

# third party packages
import affine  # BSD
import geopandas
import numpy as np  # BSD license
import pyproj  # MIT
import rasterio  # BSD License (BSD)
import rasterio.io
from rasterio.enums import Resampling
from rasterio.windows import from_bounds
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


def validPixelsFromSCLBand(scl_src: rasterio.io.DatasetReader,
                           scl_filter_values: list[int],
                           bounds_utm: tuple) -> tuple[float, float]:
    """Percentage of valid SCL band pixels.

    Parameters
    ----------
    scl_src : rasterio.io.DatasetReader
        A DatasetReader for the SCL band.
    scl_filter_values: list, default=[0], optional
        List with the values of the SCL Band to filter out
    bounds_utm: tuple
        Bounds of the bounding box in UTM coordinates.

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
        scl_band = scl_src.read(window=from_bounds(left=bounds_utm[0],
                                                   bottom=bounds_utm[1],
                                                   right=bounds_utm[2],
                                                   top=bounds_utm[3],
                                                   transform=scl_src.transform))
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
                            bounds_utm: tuple
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
    bounds_utm: tuple
        Bounds of the bounding box in UTM coordinates.

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
        scl_scale_factor = scl_src.transform[0] / band_src.transform[0]
        if scl_scale_factor != 1.0:
            scl_band = scl_src.read(
                window=from_bounds(left=bounds_utm[0],
                                   bottom=bounds_utm[1],
                                   right=bounds_utm[2],
                                   top=bounds_utm[3],
                                   transform=scl_src.transform),
                out_shape=(
                    scl_src.count,
                    int(scl_src.height * scl_scale_factor),
                    int(scl_src.width * scl_scale_factor)
                ),
                resampling=Resampling.nearest
            )
        else:
            scl_band = scl_src.read(window=from_bounds(left=bounds_utm[0],
                                                       bottom=bounds_utm[1],
                                                       right=bounds_utm[2],
                                                       top=bounds_utm[3],
                                                       transform=scl_src.transform))

        raster_band = band_src.read(window=from_bounds(left=bounds_utm[0],
                                                       bottom=bounds_utm[1],
                                                       right=bounds_utm[2],
                                                       top=bounds_utm[3],
                                                       transform=band_src.transform))

        scl_filter_values.append(0)
        scl_band_mask = np.where(np.isin(scl_band, scl_filter_values), 0, 1)

        # Mask out Clouds
        image_band_masked = raster_band * scl_band_mask

        return image_band_masked
    except Exception as e:  # pragma: no cover
        raise Exception(f"Failed to mask pixels from SCl band => {e}")


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
