# -*- coding: utf-8 -*-
"""AWS server interaction module for S2Downloader."""

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
import re
from typing import Union

# third party packages
import affine  # BSD
import numpy as np  # BSD license
import pandas as pd     # BSD License (BSD-3-Clause)
import pyproj  # MIT
from pystac_client import Client  # Apache License, Version 2.0
from pystac import Item

from .utils import extendFilepath, saveRasterToDisk


def searchDataAtAWS(*, s2_collection: list[str],
                    bb: list[float],
                    props_json: dict,
                    utm_zone: int,
                    stac_catalog_url: str) -> tuple[list[Item], list[str], list[int]]:
    """Search for Sentinel-2 data in given bounding box as defined in query_props.json (no data download yet).

    Parameters
    ----------
    s2_collection: list[str]
        Contains name of S2 collection at AWS (only tested for [sentinel-s2-l2a-cogs].)
    bb : list[float]
        A list of coordinates of the outer bounding box of all given coordinates.
    props_json: dict
        Dictionary of all search parameters retrieved from json file.
    utm_zone : int
        Best fitting UTM zone number.
    stac_catalog_url : str
        STAC catalog URL.

    Returns
    -------
    : list[Item]
        List of found Items at AWS server.
    : list[str]
        List of available scene dates (duplicates removed).
    : list[int]
        Index of the location of the selected dates in original query output.

    Raises
    ------
    ValueError
        When no data is found at AWS for given parameter settings.
    Exception
        Failed to find data at AWS server.
    """
    try:
        # search AWS collection
        catalogue = Client.open(stac_catalog_url)

        item_search = catalogue.search(
            collections=s2_collection,  # sentinel-s2-l2a-cogs
            bbox=bb,  # bounding box
            # intersects=geoj,   # method can be used instead of bbox, but currently throws error
            query=props_json,  # cloud and data coverage properties
            datetime=props_json['time'],  # time period
            sortby="-properties.datetime"  # sort by data descending (minus sign)
        )

        # proceed if items are found
        if len(list(item_search.items())) == 0:
            raise ValueError("For these settings there is no data to be found at AWS. \n"
                             "Try to adapt your search parameters:\n"
                             "- increase time span,\n"
                             "- allow more cloud coverage,\n"
                             "- reduce data coverage (your polygon(s) may not be affected"
                             " by a smaller tile coverage).")

        # items to list
        items_list = list(item_search.items())
        item_list_dict = [i.to_dict() for i in items_list]

        # print overview of found data
        print("Date                    ID                          UTM Zone    Tile Cloud Cover    Tile Coverage")
        [print(f"{i['properties']['datetime']}    {i['id']}    {i['properties']['sentinel:utm_zone']}"
               f"          {i['properties']['eo:cloud_cover']}                "
               f"{i['properties']['sentinel:data_coverage']}")
         for i in item_list_dict]
        print()

        # collect all ids
        ids = [id_item['id'] for id_item in item_list_dict]
        ids_string = ''.join(ids)

        # collect utm zones
        utm_zone_list = [id_item['properties']['sentinel:utm_zone'] for id_item in item_list_dict]

        # extract dates of available scenes from id search results
        # TODO: This is S2 file name specific regexing,
        #  maybe this can be improved to retrieve dates in a better way from the string
        date_list = re.findall(r"\d{8}", ids_string)

        # store date and utm zone information in dataframe
        df_scene_dates = pd.DataFrame(zip(date_list, utm_zone_list), columns=["dates", "utm_zones"])

        # keep scenes dates that are not duplicated OR where utm_zone fits best
        df_scene_dates_clean = df_scene_dates[~df_scene_dates['dates'].duplicated(keep=False) |
                                              df_scene_dates['utm_zones'].eq(utm_zone)]

        def list2int(input_list):
            return [int(i) for i in input_list]

        # store index number of kept scenes to list and convert list items to integer
        scene_dates_clean_index = df_scene_dates_clean.index.tolist()
        scene_dates_clean_index_int = list2int(scene_dates_clean_index)

        # selected dates to list
        date_list_selected = []
        for idx in scene_dates_clean_index_int:
            date_list_selected.append(date_list[idx])

        return items_list, date_list_selected, scene_dates_clean_index_int
    except Exception as e:  # pragma: no cover
        raise Exception(f"Failed to find data at AWS server => {e}")


def noDataMaskingFromSCLBand(image_stack: np.ndarray, scl: np.ndarray) -> tuple[np.ndarray, float]:
    """Based on the SCL band categorization, the no data values are masked.

    Parameters
    ----------
    image_stack : np.ndarray
        Raster stack containing all bands to be masked.
    scl : np.ndarray
        Raster band containing the SCL information.

    Returns
    -------
    : np.ndarray
        Masked raster data stack.
    : float
        Percentage of valid pixels after masking.

    Raises
    ------
    Exception
        Failed to mask pixels from SCl band.
    """
    try:
        cloud_mask = (scl == 0)

        # use broadcasting to mask image stack
        out_image_stack_masked = np.ma.array(
            image_stack, mask=image_stack * cloud_mask[np.newaxis, :, :])

        # apply nan values to masked pixels
        out_image_stack_masked_nan = out_image_stack_masked.filled(np.nan)

        # calculate number of valid pixels
        pixels_valid_before = np.count_nonzero(image_stack)
        pixels_valid_after = np.count_nonzero(out_image_stack_masked != 0 & ~np.isnan(out_image_stack_masked))

        percentage_true_pixels = (float(pixels_valid_after)/float(pixels_valid_before))*100
        print(f"Valid pixels after no data masking: {percentage_true_pixels} %")

        return out_image_stack_masked_nan, percentage_true_pixels
    except Exception as e:  # pragma: no cover
        raise Exception(f"Failed to mask no data pixels from SCl band => {e}")


def cloudMaskingFromSCLBand(*, image_stack: np.ndarray, scl_filtered: np.ndarray) -> tuple[np.ndarray, float]:
    """Based on the SCL band categorization, the input data is masked (clouds, cloud shadow, snow).

    Parameters
    ----------
    image_stack : np.ndarray
        Raster stack containing all bands to be masked.
    scl_filtered : np.ndarray
        Raster band containing the SCL information.

    Returns
    -------
    : np.ndarray
        Masked raster data stack.
    : float
        Percentage of valid pixels after masking.

    Raises
    ------
    Exception
        Failed to mask pixels from SCl band.
    """
    try:
        print("Mask cloud pixels.")

        # use broadcasting to mask image stack
        out_image_stack_masked = np.ma.array(
            image_stack, mask=image_stack * scl_filtered)

        # apply nan values to masked pixels
        out_image_stack_masked_nan = out_image_stack_masked.filled(np.nan)

        # calculate number of valid pixels
        pixels_valid_before = np.count_nonzero(image_stack)
        pixels_valid_after = np.count_nonzero(out_image_stack_masked != 0 & ~np.isnan(out_image_stack_masked))

        percentage_true_pixels = (float(pixels_valid_after)/float(pixels_valid_before))*100
        print(f"Valid pixels after SCL masking: {percentage_true_pixels} %")

        return out_image_stack_masked_nan, percentage_true_pixels
    except Exception as e:  # pragma: no cover
        raise Exception(f"Failed to mask pixels from SCl band => {e}")


def rasterStackCloudMask(*,
                         out_image: np.ndarray,
                         out_scl: np.ndarray,
                         out_crs: pyproj.crs.crs.CRS,
                         out_transform: affine.Affine,
                         output_raster_path: str,
                         tile_id: str,
                         bands: list[str],
                         cloud_percentage: Union[int, float],
                         aoi_percentage: float,
                         scl_filter_values: list = None,
                         save_to_uint16: bool = True):
    """Reproject (if necessary), crop, cloud mask (if desired) and save raster to disc.

    Parameters
    ----------
    out_image : np.ndarray
        Image stack.
    out_scl : np.ndarray
        SCL band.
    out_crs : pyproj.crs.crs.CRS,
        Output CRS.
    out_transform: afine.Afine
        Output transform.
    output_raster_path : str
        Path to raster output location.
    tile_id: str
        Number of current S2 tile ID.
    bands : list[str]
        List containing all band names of the image stack.
    cloud_percentage: Union[int, float]
        Minimum percentage of valid pixels after cloud masking that need to be available for saving the image.
    aoi_percentage: float
        Minimum percentage of valid pixels in the AOI.
    scl_filter_values: list, default=[0], optional
        List with the values of the SCL Band to filter out
    save_to_uint16 : bool, default=False, optional
        Converts NaN to 0 and saves the raster with the dtype rasterio.uint16.

    Raises
    ------
    Exception
        Failed to preprocess and cloud mask raster stack.
    """
    try:
        # apply no data mask
        out_image_valid, percentage_valid_pixels = noDataMaskingFromSCLBand(image_stack=out_image,
                                                                            scl=out_scl)

        # create cloudmask from SCL_filter_values
        scl_filtered_flat = np.in1d(np.ravel(out_scl), scl_filter_values)
        scl_filtered = np.reshape(scl_filtered_flat, out_scl.shape)

        # apply cloud mask based on SCL band, set cloud pixels to NaN
        out_image_cloud_masked, percentage_true_pixels = cloudMaskingFromSCLBand(image_stack=out_image_valid,
                                                                                 scl_filtered=scl_filtered)

        # check if amount of valid pixels fits to user setting
        if percentage_true_pixels >= cloud_percentage and percentage_valid_pixels >= aoi_percentage:

            # save result to disk
            output_scl_path = extendFilepath(input_file_path=output_raster_path,
                                             suffix='_SCL')

            saveRasterToDisk(out_image=out_image_cloud_masked,
                             raster_crs=out_crs,
                             out_transform=out_transform,
                             bands=bands,
                             output_raster_path=output_raster_path,
                             save_to_uint16=save_to_uint16)

            saveRasterToDisk(out_image=out_scl,
                             raster_crs=out_crs,
                             out_transform=out_transform,
                             bands=bands,
                             output_raster_path=output_scl_path,
                             save_to_uint16=save_to_uint16)
        else:
            print(f"{tile_id} not saved to disk as minimum number of valid pixels is not met.")
    except Exception as e:  # pragma: no cover
        raise Exception(f"Failed to preprocess and cloud mask raster stack => {e}")
