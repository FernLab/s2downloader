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

import json
import os

import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.windows import from_bounds
from rasterio.warp import Resampling
import urllib.request

from pystac import Item
from pystac_client import Client

from .utils import saveRasterToDisk, validPixelsFromSCLBand, getBoundsUTM, groupItemsPerDate
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
        print("{:<25} {:<25} {:<10} {:<20} {:<20} {:<15}".format('Date', 'ID', 'UTM Zone', 'Valid Cloud Cover',
                                                                 'Tile Cloud Cover', 'Tile Coverage'))
        for i in item_list_dict:
            print("{:<25} {:<25} {:<10} {:<20} {:<20} {:<15}".format(i['properties']['datetime'],
                                                                     i['id'],
                                                                     i['properties']['sentinel:utm_zone'],
                                                                     str(i['properties']['sentinel:valid_cloud_cover']),
                                                                     i['properties']['eo:cloud_cover'],
                                                                     i['properties']['sentinel:data_coverage']))
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
        target_resolution = 10

        # read the variables from the config:
        tile_settings = config_dict['user_settings']['tile_settings']
        aoi_settings = config_dict['user_settings']['aoi_settings']
        result_settings = config_dict['user_settings']['result_settings']
        s2_settings = config_dict['s2_settings']

        download_thumbnails = result_settings['download_thumbnails']
        download_overviews = result_settings['download_overviews']
        only_dates_no_data = result_settings['only_dates_no_data']

        result_dir = result_settings['results_dir']
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

        items_per_date = groupItemsPerDate(items_list=aws_items)
        scl_filter_values = aoi_settings["SCL_filter_values"]
        scl_filter_values.append(0)
        scenes_info = {}
        for items_date in items_per_date.keys():
            items = items_per_date[items_date]
            num_tiles = len(items)
            sensor_name = items[0].id[0:3]
            bounds_utm = getBoundsUTM(bounds=aoi_settings['bounding_box'],
                                      utm_zone=items[0].properties['sentinel:utm_zone'])
            scl_crs = 32632
            raster_crs = 32632

            if num_tiles > 1:
                scl_mosaic = []
                for item_idx in range(len(items)):
                    scl_src = rasterio.open(items[item_idx].assets["SCL"].href)
                    if item_idx == 0:
                        scl_crs = scl_src.crs
                    scl_mosaic.append(scl_src)

                scl_band, scl_trans = merge(datasets=scl_mosaic,
                                            target_aligned_pixels=True,
                                            bounds=bounds_utm,
                                            res=target_resolution,
                                            resampling=Resampling[aoi_settings["resampling_method"]])
                output_scl_path = os.path.join(result_dir, f"{sensor_name}_{items_date}_SCL.tif")
            elif len(items) == 1:
                file_url = items[0].assets["SCL"].href
                with rasterio.open(file_url) as scl_src:
                    scl_scale_factor = scl_src.transform[0] / target_resolution
                    bb_window = from_bounds(left=bounds_utm[0],
                                            bottom=bounds_utm[1],
                                            right=bounds_utm[2],
                                            top=bounds_utm[3],
                                            transform=scl_src.transform)
                    if scl_scale_factor != 1.0:
                        scl_band = scl_src.read(window=bb_window,
                                                out_shape=(scl_src.count,
                                                           int(bb_window.height * scl_scale_factor),
                                                           int(bb_window.width * scl_scale_factor)
                                                           ),
                                                resampling=Resampling.nearest
                                                )
                    else:
                        scl_band = scl_src.read(window=bb_window)
                    scl_crs = scl_src.crs
                    scl_trans = scl_src.transform
                output_scl_path = os.path.join(result_dir,
                                               f"{file_url.split('/')[-2]}_SCL.tif")
            else:
                raise Exception("Number of items per date is invalid.")
            nonzero_pixels_per, valid_pixels_per = \
                validPixelsFromSCLBand(
                    scl_band=scl_band,
                    scl_filter_values=scl_filter_values)

            if nonzero_pixels_per >= aoi_settings["SCL_mask_valid_pixels_min_percentage"] \
               and valid_pixels_per >= aoi_settings["aoi_min_coverage"]:
                if (download_thumbnails or download_overviews) or not only_dates_no_data:
                    msg = f"Getting {''.join(data_msg)} for: {items[0].id}"
                    print(msg)

                # Create results directory
                if not os.path.isdir(result_dir):
                    os.makedirs(result_dir)

                if download_thumbnails or download_overviews:
                    if num_tiles != 1:
                        raise Exception("Not yet possible to download overviews and thumbnails for mosaics.")
                    else:
                        if download_thumbnails:
                            file_url = items[0].assets["thumbnail"].href
                            thumbnail_path = os.path.join(result_dir,
                                                          f"{items[0].id}_{file_url.rsplit('/', 1)[1]}")
                            urllib.request.urlretrieve(file_url, thumbnail_path)
                        if download_overviews:
                            file_url = items[0].assets["overview"].href
                            overview_path = os.path.join(result_dir,
                                                         f"{items[0].id}_{file_url.rsplit('/', 1)[1]}")
                            urllib.request.urlretrieve(file_url, overview_path)
                if only_dates_no_data:
                    if items_date not in scenes_info:
                        scenes_info[items_date] = list()
                    for item in items:
                        scenes_info[items_date].append({"id": item.to_dict()["id"]})
                else:
                    # Save the SCL band
                    saveRasterToDisk(out_image=scl_band,
                                     raster_crs=scl_crs,
                                     out_transform=scl_trans,
                                     output_raster_path=output_scl_path)

                    # Download all other bands
                    bands = tile_settings["bands"]
                    print(f"Bands to retrieve: {bands}")

                    for band in bands:
                        if num_tiles > 1:
                            srcs_to_mosaic = []
                            for item_idx in range(len(items)):
                                band_src = rasterio.open(items[item_idx].assets[band].href)
                                if item_idx == 0:
                                    raster_crs = band_src.crs
                                srcs_to_mosaic.append(band_src)

                            raster_band, raster_trans = merge(datasets=srcs_to_mosaic,
                                                              target_aligned_pixels=True,
                                                              bounds=bounds_utm,
                                                              res=target_resolution,
                                                              resampling=Resampling[aoi_settings["resampling_method"]])
                            output_band_path = os.path.join(result_dir, f"{sensor_name}_{items_date}_{band}.tif")
                        else:
                            file_url = items[0].assets[band].href
                            with rasterio.open(file_url) as band_src:
                                raster_trans = band_src.transform
                                raster_crs = band_src.crs
                                band_scale_factor = band_src.transform[0] / target_resolution
                                bb_window = from_bounds(left=bounds_utm[0],
                                                        bottom=bounds_utm[1],
                                                        right=bounds_utm[2],
                                                        top=bounds_utm[3],
                                                        transform=band_src.transform)
                                if band_scale_factor != 1.0:
                                    raster_band = band_src.read(window=bb_window,
                                                                out_shape=(band_src.count,
                                                                           int(bb_window.height * band_scale_factor),
                                                                           int(bb_window.width * band_scale_factor)
                                                                           ),
                                                                resampling=Resampling[aoi_settings["resampling_method"]]
                                                                )

                                else:
                                    raster_band = band_src.read(window=bb_window)
                                output_raster_path = os.path.join(result_dir,
                                                                  f"{file_url.split('/')[-2]}")
                                if not os.path.isdir(output_raster_path):
                                    os.makedirs(output_raster_path)
                                output_band_path = os.path.join(output_raster_path,
                                                                f"{band}.tif")
                        if cloudmasking:
                            # Mask out Clouds
                            scl_band_mask = np.where(np.isin(scl_band, scl_filter_values), np.uint16(0), np.uint16(1))
                            raster_band = raster_band * scl_band_mask

                        saveRasterToDisk(out_image=raster_band,
                                         raster_crs=raster_crs,
                                         out_transform=raster_trans,
                                         output_raster_path=output_band_path)
            else:
                print(f"For date {items_date} there is not any available data for the current tile and AOI settings.")

        if only_dates_no_data:
            scenes_info_path = os.path.join(result_dir,
                                            f"scenes_info_"
                                            f"{'_'.join(aoi_settings['date_range'])}.json")
            if os.path.exists(scenes_info_path):
                raise IOError(f"The scenes_info file: {scenes_info_path} already exists.")
            else:
                with open(scenes_info_path, "w") as write_file:
                    json.dump(scenes_info, write_file, indent=4)
    except Exception as e:
        raise Exception(f"Failed to run S2DataPortal main process => {e}")
