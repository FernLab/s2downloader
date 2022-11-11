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
import os
from datetime import datetime

import rasterio
import urllib.request

from pystac import Item
from pystac_client import Client

from .utils import saveRasterToDisk, validPixelsFromSCLBand, cloudMaskingFromSCLBand
from .config import Config


def searchDataAtAWS(*, s2_collection: list[str],
                    bb: list[float],
                    date_range: list[str],
                    props_json: dict,
                    stac_catalog_url: str) -> list[Item]:
    """Search for Sentinel-2 data in given bounding box as defined in query_props.json (no data download yet).

    Parameters
    ----------
    s2_collection: list[str]
        Contains name of S2 collection at AWS (only tested for [sentinel-s2-l2a-cogs].)
    bb : list[float]
        A list of coordinates of the outer bounding box of all given coordinates.
    date_range: list[str]
        List with the start and end date. If the same it is a single date request.
    props_json: dict
        Dictionary of all search parameters retrieved from json file.
    stac_catalog_url : str
        STAC catalog URL.

    Returns
    -------
    : list[Item]
        List of found Items at AWS server.

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
            datetime=date_range,  # time period
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

        return items_list
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

        save_to_uint16 = not result_settings["save_raster_dtype_float32"]
        cloudmasking = aoi_settings["apply_SCL_band_mask"]

        # search for Sentinel-2 data within the bounding box as defined in query_props.json (no data download yet)
        aws_items = searchDataAtAWS(s2_collection=s2_settings['collections'],
                                    bb=aoi_settings['bounding_box'],
                                    date_range=aoi_settings['date_range'],
                                    props_json=tile_settings,
                                    stac_catalog_url=s2_settings['stac_catalog_url'])

        data_msg = []
        if download_thumbnails:
            data_msg.append("thumbnail")
        if download_overviews:
            data_msg.append("overview")
        if not only_dates_no_data:
            data_msg.append("data")

        # extract data for all scenes
        scenes_info = {}
        for aws_item in aws_items:
            # get item for selected scene
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
                        msg = f"Getting {''.join(data_msg)} for: {aws_item.id}"
                    print(msg)

                    # Create results directory
                    if not os.path.isdir(result_dir):
                        os.makedirs(result_dir)

                    if download_thumbnails or download_overviews:
                        if download_thumbnails:
                            file_url = aws_item.assets["thumbnail"].href
                            thumbnail_path = os.path.join(result_dir,
                                                          f"_{aws_item.id}_{file_url.rsplit('/', 1)[1]}")
                            urllib.request.urlretrieve(file_url, thumbnail_path)
                        if download_overviews:
                            file_url = aws_item.assets["overview"].href
                            overview_path = os.path.join(result_dir,
                                                         f"_{aws_item.id}_{file_url.rsplit('/', 1)[1]}")
                            urllib.request.urlretrieve(file_url, overview_path)
                    if only_dates_no_data:
                        date = datetime.strptime(aws_item.properties['datetime'], "%Y-%m-%dT%H:%M:%SZ")
                        scenes_info[date.strftime("%Y-%m-%d")] = {"id": aws_item.to_dict()["id"]}
                    else:
                        # Download all other bands
                        bands = tile_settings["bands"]
                        print(f"Bands to retrieve: {bands}")

                        output_raster_path = os.path.join(result_dir,
                                                          f"{file_url.split('/')[-2]}")
                        if not os.path.isdir(output_raster_path):
                            os.makedirs(output_raster_path)

                        file_url = None
                        for band in bands:
                            print(f"Retrieving band: {band}")

                            # Get file URL of each band
                            file_url = aws_item.assets[band].href
                            print(file_url)

                            with rasterio.open(file_url) as band_src:
                                if cloudmasking:
                                    raster_band = cloudMaskingFromSCLBand(
                                        band_src=band_src,
                                        scl_src=scl_src,
                                        scl_filter_values=aoi_settings["SCL_filter_values"]
                                    )
                                else:
                                    raster_band = band_src.read()

                                output_band_path = os.path.join(output_raster_path,
                                                                f"{band}.tif")
                                saveRasterToDisk(out_image=raster_band,
                                                 raster_crs=band_src.crs,
                                                 out_transform=band_src.transform,
                                                 output_raster_path=output_band_path,
                                                 save_to_uint16=save_to_uint16)

                        # Save the SCL band
                        output_scl_path = os.path.join(result_dir,
                                                       f"{file_url.split('/')[-2]}_SCL.tif")
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
