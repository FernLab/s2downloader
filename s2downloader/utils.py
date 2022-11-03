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
import numpy as np  # BSD license
import pyproj  # MIT
import rasterio  # BSD License (BSD)


def extendFilepath(*, input_file_path: str, prefix: str = '', suffix: str = '') -> str:
    """Generate output path for tif from given directory and filename.

    Parameters
    ----------
    input_file_path : str
        Path to directory including the filename that should be altered.
    prefix : str (optional)
        Content that should be concatenated before the name of the file. Default: empty
    suffix : str (optional)
        Content that should be concatenated after the name and before the extension of the file. Default: empty

    Returns
    -------
    : str
        Newly concatenated output path.

    Raises
    ------
    Exception
        Failed to extend filename.
    """
    try:
        dir_name = os.path.dirname(input_file_path)
        file_name = os.path.basename(input_file_path)
        file_base, file_extension = os.path.splitext(file_name)

        return os.path.join(dir_name, f"{prefix}{file_base}{suffix}{file_extension}")
    except Exception as e:  # pragma: no cover
        raise Exception(f"Failed to extend filename => {e}")


def saveRasterToDisk(*, out_image: np.ndarray, raster_crs: pyproj.crs.crs.CRS, out_transform: affine.Affine,
                     bands: list[str], output_raster_path: str, save_to_uint16: bool = False):
    """Save raster imagery data to disk.

    Parameters
    ----------
    out_image : np.ndarray
        Array containing output raster data.
    raster_crs : pyproj.crs.crs.CRS
        Output raster coordinate system.
    out_transform : affine.Affine
        Output raster transformation parameters.
    bands : list[str]
        List containing all band names of the image stack.
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
            for index, band_name in enumerate(bands):
                dst.set_band_description(index, f"'Band':{band_name}")
    except Exception as e:  # pragma: no cover
        raise Exception(f"Failed to save raster to disk => {e}")
