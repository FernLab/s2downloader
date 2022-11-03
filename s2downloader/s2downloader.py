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

import numpy as np
import os
from datetime import datetime

import rasterio
import urllib.request


from .aws_interaction import rasterStackCloudMask
from s2downloader.aws_interaction import searchDataAtAWS


def s2DataDownloader(*,
                     collections: list[str],
                     utm_zone: int,
                     stac_catalog_url: str,
                     tile_id: str,
                     tile_settings: dict,
                     bounding_box: list[float],
                     aoi_settings: dict,
                     aoi_name: str,
                     result_dir: str,
                     save_to_uint16: bool = True,
                     raster_stacking: bool = False,
                     download_thumbnails: bool = False,
                     download_overviews: bool = False,
                     only_dates_no_data: bool = False,
                     download_only_one_scene: bool = False):
    """s2DataDownloader.

        Parameters
    ----------
    stac_catalog_url: str
        STAC catalog URL.
    collections : list[str]
        List of STAC collections.
    utm_zone: int
        UTM zone.
    tile_id: str
        Tile ID.
    tile_settings: dict
        Tile setting for the query_props.
    bounding_box: list[float],
        Bounding box.
    aoi_settings: dict
        AOI settings as a dictionary.
    aoi_name: str
        Name of AOI to distinguish request.
    result_dir: str
        Path to the result dir.
    save_to_uint16: bool, default=True, optional
        Save raster with dtype uint16.
    raster_stacking: bool, default=False, optional
        Stack all the bands into a single .tif file.
    download_thumbnails: bool, default=False, optional
        Download the thumbnails.
    download_overviews: bool, default=False, optional
        Download the overviews.
    only_dates_no_data: bool, default=False, optional
        Download only the list of dates for the available scenes, but not the data.
    download_only_one_scene: bool, default=False, optional
        Download only one scene, the most recent scene.

    Raises
    ------
    Exception
        Failed to save raster to disk.
    """
    try:
        # search for Sentinel-2 data within the bounding box as defined in query_props.json (no data download yet)
        aws_items, date_list, scene_index = searchDataAtAWS(s2_collection=collections,
                                                            bb=bounding_box,
                                                            props_json=tile_settings,
                                                            utm_zone=utm_zone,
                                                            stac_catalog_url=stac_catalog_url)

        scene_index.sort()
        selected_scenes_index_list = scene_index
        if download_only_one_scene:
            selected_scenes_index_list = [scene_index[0]]

        # extract data for all scenes
        scenes_info = {}
        for idx_scene in selected_scenes_index_list:
            current_date = date_list[idx_scene]
            current_year = current_date[:len(current_date) // 2]
            current_month_day = current_date[len(current_date) // 2:]
            current_month = current_month_day[:len(current_month_day) // 2]
            output_raster_directory_tile_date = os.path.join(result_dir, tile_id,
                                                             current_year, current_month)

            # get item for selected scene
            aws_item = aws_items[idx_scene]
            data_msg = []
            if download_thumbnails:
                data_msg.append("thumbnail")
            if download_overviews:
                data_msg.append("overview")
            if not only_dates_no_data:
                data_msg.append("data")
            if (download_thumbnails or download_overviews) or not only_dates_no_data:
                data_msg = f"Getting {','.join(data_msg)} for: {aws_item.id}"
                print(data_msg)

            if download_thumbnails or download_overviews:
                output_path = os.path.join(result_dir, tile_id, current_year, current_month)
                if not os.path.isdir(output_path):
                    os.makedirs(output_path)
                if download_thumbnails:
                    file_url = aws_item.assets["thumbnail"].href
                    thumbnail_path = os.path.join(output_raster_directory_tile_date,
                                                  f"{aoi_name}"
                                                  f"_{aws_item.id}_{file_url.rsplit('/', 1)[1]}")
                    urllib.request.urlretrieve(file_url, thumbnail_path)
                if download_overviews:
                    file_url = aws_item.assets["overview"].href
                    overview_path = os.path.join(output_raster_directory_tile_date,
                                                 f"{aoi_name}"
                                                 f"_{aws_item.id}_{file_url.rsplit('/', 1)[1]}")
                    urllib.request.urlretrieve(file_url, overview_path)

            bands = tile_settings["bands"]
            if only_dates_no_data:
                item = aws_items[idx_scene]
                date_str = date_list[idx_scene]
                date = datetime(year=int(date_str[0:4]), month=int(date_str[4:6]), day=int(date_str[6:8]))
                scenes_info[date.strftime("%Y-%m-%d")] = {"id": item.to_dict()["id"]}
            else:
                # add SCL band to cloud masking
                bands.append("SCL")

                # get URL for each band of one scene
                out_image_stack_tmp = []

                # processing for each band individually
                print(f"Bands to retrieve: {bands}")
                print("SCL band temporally retrieved for cloud masking, will be deleted at the end.")

                raster_crs = None
                file_url = None
                out_transform = None
                for band in bands:
                    print()
                    print(f"Retrieving band: {band}")

                    # Get file URL of each band
                    file_url = aws_item.assets[band].href
                    print(file_url)

                    with rasterio.open(file_url) as src:
                        out_image = src.read()
                        raster_crs = src.crs
                        out_transform = src.transform

                    # save band to tmp list
                    out_image_stack_tmp.append(out_image)

                # stack raster bands from list
                if raster_stacking:
                    print("Stack all bands.")
                    out_image_stack = np.concatenate(out_image_stack_tmp, axis=0, out=None)

                    # remove SCL band from list
                    out_scl = out_image_stack[-1, :, :]
                    out_image_stack = out_image_stack[:-1, :, :]
                    bands = bands[:-1]

                    # create folder for tile
                    if not os.path.isdir(output_raster_directory_tile_date):
                        os.makedirs(output_raster_directory_tile_date)

                    # build output raster path from URL
                    output_raster_path = os.path.join(output_raster_directory_tile_date,
                                                      f"{aoi_name}_{file_url.split('/')[-2]}.tif")

                    rasterStackCloudMask(out_image=out_image_stack,
                                         out_scl=out_scl,
                                         out_crs=raster_crs,
                                         out_transform=out_transform,
                                         output_raster_path=output_raster_path,
                                         tile_id=tile_id,
                                         bands=bands,
                                         cloud_percentage=aoi_settings["SCL_mask_valid_pixels_min_percentage"],
                                         aoi_percentage=aoi_settings["aoi_min_coverage"],
                                         scl_filter_values=aoi_settings["SCL_filter_values"],
                                         save_to_uint16=save_to_uint16)
            if only_dates_no_data:
                scenes_info_path = os.path.join(result_dir,
                                                f"scenes_info_{tile_id}_"
                                                f"{tile_settings['time'].replace('/', '_')}.json")
                if os.path.exists(scenes_info_path):
                    raise IOError(f"The scenes_info file: {scenes_info_path} already exists.")
                else:
                    with open(scenes_info_path, "w") as write_file:
                        json.dump(scenes_info, write_file, indent=4)
    except Exception as e:
        raise Exception(f"Failed to run S2DataPortal main process => {e}")
