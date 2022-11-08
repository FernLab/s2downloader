# -*- coding: utf-8 -*-
"""Main for S2Downloader."""

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
import json
import re

import numpy as np
import os
from datetime import datetime

import pandas as pd
import rasterio
import urllib.request

from pystac import Item
from pystac_client import Client

from .utils import saveRasterToDisk, validPixelsFromSCLBand, cloudMaskingFromSCLBand
from .config import Config


def searchDataAtAWS(*, s2_collection: list[str],
                    bb: list[float],
                    props_json: dict,
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
        df_scene_dates_clean = df_scene_dates

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


def s2DataDownloader(*, config_dict: dict):
    """s2DataDownloader.

    Parameters
    ----------
    config_dict : dict
        Content of the user config file.

    Raises
    ------
    Exception
        Failed to save raster to disk.
    """
    try:
        config_dict = Config(**config_dict).dict(by_alias=True)

        # read the variables from the config:
        tile_settings = config_dict['user_settings']['tile_settings']
        aoi_settings = config_dict['user_settings']['aoi_settings']
        result_settings = config_dict['user_settings']['result_settings']
        s2_settings = config_dict['s2_settings']

        download_thumbnails = result_settings['download_thumbnails']
        download_overviews = result_settings['download_overviews']
        only_dates_no_data = result_settings['only_dates_no_data']

        result_dir = result_settings['results_dir']

        target_resolution = result_settings['target_resolution']

        save_to_uint16 = not result_settings["save_raster_dtype_float32"]

        # search for Sentinel-2 data within the bounding box as defined in query_props.json (no data download yet)
        aws_items, date_list, scene_index = searchDataAtAWS(s2_collection=s2_settings['collections'],
                                                            bb=aoi_settings['bounding_box'],
                                                            props_json=tile_settings,
                                                            stac_catalog_url=s2_settings['stac_catalog_url'])

        scene_index.sort()
        selected_scenes_index_list = scene_index

        download_only_one_scene = False
        if download_only_one_scene:
            selected_scenes_index_list = [scene_index[0]]

        data_msg = []

        if download_thumbnails:
            data_msg.append("thumbnail")
        if download_overviews:
            data_msg.append("overview")
        if not only_dates_no_data:
            data_msg.append("data")

        # extract data for all scenes
        scenes_info = {}
        for idx_scene in selected_scenes_index_list:
            current_date = date_list[idx_scene]
            current_year = current_date[:len(current_date) // 2]
            current_month_day = current_date[len(current_date) // 2:]
            current_month = current_month_day[:len(current_month_day) // 2]
            output_raster_directory_tile_date = os.path.join(result_dir, current_year, current_month)

            # get item for selected scene
            aws_item = aws_items[idx_scene]
            print(f"Validating scene ID: {aws_item.id}")

            # Download the SCL band
            band = 'SCL'
            print(f"Retrieving band: {band}")
            file_url = aws_item.assets[band].href
            print(file_url)
            with rasterio.open(file_url) as scl_src:
                nonzero_pixels_per, valid_pixels_per = \
                    validPixelsFromSCLBand(
                        scl_src=scl_src,
                        scl_filter_values=aoi_settings["SCL_filter_values"])

                if nonzero_pixels_per >= aoi_settings["SCL_mask_valid_pixels_min_percentage"]\
                   and valid_pixels_per >= aoi_settings["aoi_min_coverage"]:
                    if (download_thumbnails or download_overviews) or not only_dates_no_data:
                        data_msg = f"Getting {','.join(data_msg)} for: {aws_item.id}"
                    print(data_msg)

                    if download_thumbnails or download_overviews:
                        output_path = os.path.join(result_dir, current_year, current_month)
                        if not os.path.isdir(output_path):
                            os.makedirs(output_path)
                        if download_thumbnails:
                            file_url = aws_item.assets["thumbnail"].href
                            thumbnail_path = os.path.join(output_raster_directory_tile_date,
                                                          f"_{aws_item.id}_{file_url.rsplit('/', 1)[1]}")
                            urllib.request.urlretrieve(file_url, thumbnail_path)
                        if download_overviews:
                            file_url = aws_item.assets["overview"].href
                            overview_path = os.path.join(output_raster_directory_tile_date,
                                                         f"_{aws_item.id}_{file_url.rsplit('/', 1)[1]}")
                            urllib.request.urlretrieve(file_url, overview_path)
                    if only_dates_no_data:
                        item = aws_items[idx_scene]
                        date_str = date_list[idx_scene]
                        date = datetime(year=int(date_str[0:4]), month=int(date_str[4:6]), day=int(date_str[6:8]))
                        scenes_info[date.strftime("%Y-%m-%d")] = {"id": item.to_dict()["id"]}
                    else:
                        # Download all other bands
                        bands = tile_settings["bands"]
                        print(f"Bands to retrieve: {bands}")

                        # Create results directory
                        if not os.path.isdir(output_raster_directory_tile_date):
                            os.makedirs(output_raster_directory_tile_date)

                        output_raster_path = os.path.join(output_raster_directory_tile_date,
                                                          f"_{file_url.split('/')[-2]}")
                        if not os.path.isdir(output_raster_path):
                            os.makedirs(output_raster_path)

                        raster_bands = []
                        bands_crs = []
                        bands_transform = []
                        file_url = None
                        for band in bands:
                            print(f"Retrieving band: {band}")

                            # Get file URL of each band
                            file_url = aws_item.assets[band].href
                            print(file_url)

                            with rasterio.open(file_url) as band_src:
                                raster_band = cloudMaskingFromSCLBand(
                                    band_src=band_src,
                                    scl_src=scl_src,
                                    scl_filter_values=aoi_settings["SCL_filter_values"],
                                    resampling_method=aoi_settings["raster_resampling_method"]
                                )

                                output_band_path = os.path.join(output_raster_path,
                                                                f"{band}.tif")
                                saveRasterToDisk(out_image=raster_band,
                                                 raster_crs=band_src.crs,
                                                 out_transform=band_src.transform,
                                                 output_raster_path=output_band_path,
                                                 save_to_uint16=save_to_uint16)


                        # Save the SCL band
                        output_scl_path = os.path.join(output_raster_directory_tile_date,
                                                       f"_{file_url.split('/')[-2]}_SCL.tif")
                        saveRasterToDisk(out_image=scl_src.read(),
                                         raster_crs=scl_src.crs,
                                         out_transform=scl_src.transform,
                                         output_raster_path=output_scl_path,
                                         save_to_uint16=save_to_uint16)

                    if only_dates_no_data:
                        scenes_info_path = os.path.join(result_dir,
                                                        f"scenes_info_"
                                                        f"{tile_settings['time'].replace('/', '_')}.json")
                        if os.path.exists(scenes_info_path):
                            raise IOError(f"The scenes_info file: {scenes_info_path} already exists.")
                        else:
                            with open(scenes_info_path, "w") as write_file:
                                json.dump(scenes_info, write_file, indent=4)
    except Exception as e:
        raise Exception(f"Failed to run S2DataPortal main process => {e}")
