# -*- coding: utf-8 -*-

# S2Downloader - The S2Downloader allows to download Sentinel-2 L2A data
#
# Copyright (C) 2022-2023
# - Helmholtz Centre Potsdam - GFZ German Research Centre for Geosciences Potsdam,
#   Germany (https://www.gfz-potsdam.de/)
#
# Licensed only under the EUPL, Version 1.2 or - as soon they will be approved
# by the European Commission - subsequent versions of the EUPL (the "Licence").
# You may not use this work except in compliance with the Licence.
#
# You may obtain a copy of the Licence at:
# https://joinup.ec.europa.eu/software/page/eupl
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Main for S2Downloader."""

import json
import logging
import sys
import time
from datetime import datetime
from logging import Logger
import os

import geopandas
import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.merge import merge
from rasterio.windows import from_bounds, Window, bounds
from rasterio.warp import Resampling
import urllib.request
from shapely.geometry import shape
from shapely import bounds as shp_bounds
from typing import Dict, Union

from pystac import Item
from pystac_client import Client

from .utils import (saveRasterToDisk, validPixelsFromSCLBand, getBoundsUTM,
                    groupItemsPerDate, getUTMZoneBB, remove_duplicates_and_ensure_data_consistency, projectPolygon)
from .config import Config


def searchDataAtAWS(*,
                    s2_collection: list[str],
                    bb: Union[list[float], None],
                    polygon: Union[Dict, None],
                    date_range: list[str],
                    props_json: dict,
                    stac_catalog_url: str,
                    logger: Logger = None) -> list[Item]:
    """Search for Sentinel-2 data in given bounding box as defined in query_props.json (no data download yet).

    Parameters
    ----------
    s2_collection: list[str]
        Contains name of S2 collection at AWS (only tested for [sentinel-s2-l2a-cogs].)
    bb : list[float]
        A list of coordinates of the outer bounding box of all given coordinates.
    polygon : Dict
        AOI defined as a Polygon.
    date_range: list[str]
        List with the start and end date. If the same it is a single date request.
    props_json: dict
        Dictionary of all search parameters retrieved from json file.
    stac_catalog_url : str
        STAC catalog URL.
    logger: Logger
        Logger handler.

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
    if logger is None:
        logger = logging.getLogger(__name__)
    try:
        # search AWS collection
        catalogue = Client.open(url=stac_catalog_url)
        item_search = catalogue.search(
            collections=s2_collection,  # sentinel-s2-l2a-cogs
            bbox=bb,  # bounding box
            intersects=polygon,
            query=props_json,  # cloud and data coverage properties
            datetime=date_range,  # time period
            # sortby="-properties.datetime"  # sort by data descending (minus sign) ->
            # deactivated: error for catalog v1
        )

        # proceed if items are found
        if len(list(item_search.items())) == 0:

            # close log-file to avoid problems with deleting the files
            if logger.hasHandlers():
                for handler in logger.handlers[:]:
                    logger.removeHandler(handler)
                    handler.flush()
                    handler.close()

            raise ValueError("For these settings there is no data to be found at AWS. \n"
                             "Try to adapt your search parameters:\n"
                             "- increase time span,\n"
                             "- allow more cloud coverage,\n"
                             "- increase nodata pixel percentage (your polygon(s) may not be affected"
                             " by a higher nodata pixel availability).")

        # items to list
        items_list = list(item_search.items())
        item_list_dict = [i.to_dict() for i in items_list]

        # filter duplicates for s2:processing_baseline and earthsearch:boa_offset_applied,
        # if collection equals sentinel-2-l2a
        if s2_collection[0] == 'sentinel-2-l2a':
            item_list_dict = remove_duplicates_and_ensure_data_consistency(item_list_dict)
            filtered_ids = [item['id'] for item in item_list_dict]
            items_list = [item for item in items_list if item.id in filtered_ids]

        # print overview of found data
        logger.info("{:<30} {:<25} {:<12} {:<10} {:<22} {:<15}".format('Date', 'ID', 'UTM Zone', 'EPSG',
                                                                       'Tile Cloud Cover %', 'Tile NoData %'))
        for i in item_list_dict:
            logger.info("{:<30} {:<25} {:<12} {:<10} {:<22} {:<15}\n".format(
                i['properties']['datetime'],
                i['id'],
                i['properties']['mgrs:utm_zone'],
                i['properties']['proj:epsg'],
                i['properties']['eo:cloud_cover'],
                i['properties']['s2:nodata_pixel_percentage']))

        return items_list
    except Exception as e:  # pragma: no cover
        raise Exception(f"Failed to find data at AWS server => {e}")


def downloadMosaic(*, config_dict: dict):
    """downloadMosaic.

    Parameters
    ----------
    config_dict : dict
        Content of the user config file.

    Raises
    ------
    Exception
        Failed to save raster to disk.
    """
    # read the variables from the config:
    tile_settings = config_dict['user_settings']['tile_settings']
    aoi_settings = config_dict['user_settings']['aoi_settings']
    bbox = tuple(aoi_settings['bounding_box'])
    aoi_is_bb = True
    if "polygon" in aoi_settings and aoi_settings['polygon'] is not None:
        bbox = tuple(shp_bounds(shape(aoi_settings['polygon'])))
        aoi_is_bb = False
    result_settings = config_dict['user_settings']['result_settings']
    s2_settings = config_dict['s2_settings']

    result_dir = result_settings['results_dir']
    download_data = result_settings['download_data']
    download_thumbnails = result_settings['download_thumbnails']
    download_overviews = result_settings['download_overviews']
    target_resolution = result_settings['target_resolution']
    logging_dir = result_settings['path_to_logfile']
    logging_level = logging.getLevelName(result_settings['logging_level'])

    logFormatter = logging.Formatter("[%(levelname)-5.5s]  %(message)s")
    logger = logging.getLogger(__name__)

    fileHandler = logging.FileHandler("{0}/{1}.log".format(logging_dir, "s2DataDownloader"), mode='w')
    fileHandler.setFormatter(logFormatter)
    logger.addHandler(fileHandler)

    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setFormatter(logFormatter)
    logger.addHandler(consoleHandler)
    logger.setLevel(logging_level)

    cloudmasking = aoi_settings["apply_SCL_band_mask"]
    tiles_path = config_dict['s2_settings']['tiles_definition_path']

    try:
        op_start = time.time()
        tiles_gpd = geopandas.read_file(tiles_path,
                                        bbox=bbox)
        logger.debug(f"Loading Sentinel-2 tiles took {(time.time() - op_start) * 1000} msecs.")
        utm_zone = getUTMZoneBB(tiles_gpd=tiles_gpd, bbox=bbox)
        if utm_zone != 0 and tile_settings["mgrs:utm_zone"] == {}:
            tile_settings["mgrs:utm_zone"] = {"eq": utm_zone}
    except (IOError, FileNotFoundError) as err:
        logger.warning(f"It is not possible to determine in which UTM zone is the bounding-box: {err}")

    # search for Sentinel-2 data within the bounding box as defined in query_props.json (no data download yet)
    aws_items = searchDataAtAWS(s2_collection=s2_settings['collections'],
                                bb=aoi_settings['bounding_box'] if aoi_is_bb else None,
                                polygon=aoi_settings['polygon'],
                                date_range=aoi_settings['date_range'],
                                props_json=tile_settings,
                                stac_catalog_url=s2_settings['stac_catalog_url'],
                                logger=logger)

    data_msg = []
    if download_thumbnails:
        data_msg.append("thumbnail")
    if download_overviews:
        data_msg.append("overview")
    if download_data:
        data_msg.append("data")

    items_per_date = groupItemsPerDate(items_list=aws_items)
    scl_filter_values = aoi_settings["SCL_filter_values"]
    scenes_info = {}
    for items_date in items_per_date.keys():
        items = items_per_date[items_date]
        num_tiles = len(items)
        sensor_name = items[0].id[0:3]
        aoi_utm = None
        if aoi_is_bb:
            bounds_utm = getBoundsUTM(bounds=bbox, bb_crs=items[0].properties['proj:epsg'])
        else:
            aoi_utm = projectPolygon(poly=shape(aoi_settings['polygon']),
                                     source_crs=4326,
                                     target_crs=items[0].properties['proj:epsg']).buffer(target_resolution * 1.5)
            bounds_utm = tuple(shp_bounds(aoi_utm))
        scl_src = None
        scl_crs = 0
        raster_crs = 0
        scl_bb_window = None
        output_scl_path = os.path.join(result_dir, f"{items_date.replace('-', '')}_{sensor_name}_SCL.tif")

        if num_tiles > 1:
            scl_mosaic = []
            new_bounds = None
            for item_idx in range(len(items)):
                scl_src = rasterio.open(items[item_idx].assets["scl"].href)
                if item_idx == 0:
                    scl_crs = scl_src.crs
                    scl_bb_window = from_bounds(left=bounds_utm[0],
                                                bottom=bounds_utm[1],
                                                right=bounds_utm[2],
                                                top=bounds_utm[3],
                                                transform=scl_src.transform).round_lengths().round_offsets()
                    new_bounds = bounds(scl_bb_window, scl_src.transform)
                scl_mosaic.append(scl_src)

            scl_band, scl_trans = merge(datasets=scl_mosaic,
                                        target_aligned_pixels=True,
                                        bounds=new_bounds,
                                        res=target_resolution,
                                        resampling=Resampling[aoi_settings["resampling_method"]])
        elif len(items) == 1:
            file_url = items[0].assets["scl"].href
            with rasterio.open(file_url) as scl_src:
                scl_scale_factor = scl_src.transform[0] / target_resolution
                scl_bb_window = from_bounds(left=bounds_utm[0],
                                            bottom=bounds_utm[1],
                                            right=bounds_utm[2],
                                            top=bounds_utm[3],
                                            transform=scl_src.transform).round_lengths().round_offsets()
                dst_height = int(scl_bb_window.height * scl_scale_factor)
                dst_width = int(scl_bb_window.width * scl_scale_factor)
                if scl_scale_factor != 1.0:
                    scl_band = scl_src.read(window=scl_bb_window,
                                            out_shape=(scl_src.count,
                                                       dst_height,
                                                       dst_width),
                                            resampling=Resampling.nearest)
                else:
                    scl_band = scl_src.read(window=scl_bb_window)
                scl_crs = scl_src.crs
                scl_trans_win = scl_src.window_transform(scl_bb_window)
                scl_trans = rasterio.Affine(scl_src.transform[0] / scl_scale_factor,
                                            0,
                                            scl_trans_win[2],
                                            0,
                                            scl_src.transform[4] / scl_scale_factor,
                                            scl_trans_win[5])
        else:
            raise Exception("Number of items per date is invalid.")

        aoi_mask = None
        if not aoi_is_bb:
            raster_shape = np.shape(scl_band[0])
            aoi_mask = geometry_mask([aoi_utm],
                                     transform=scl_trans,
                                     invert=True,
                                     out_shape=raster_shape)
            scl_band[0] = np.where(aoi_mask, scl_band[0], 0)
        nonzero_pixels_per, masked_pixels_per, valid_pixels_per = \
            validPixelsFromSCLBand(
                scl_band=scl_band,
                scl_filter_values=scl_filter_values,
                aoi_mask=aoi_mask,
                logger=logger)

        scenes_info[items_date.replace('-', '')] = {
            "item_ids": list(),
            "nonzero_pixels": nonzero_pixels_per,
            "masked_pixels": masked_pixels_per,
            "valid_pixels": valid_pixels_per,
            "data_available": False,
            "error_info": ""
        }
        if nonzero_pixels_per >= aoi_settings["aoi_min_coverage"] \
                and masked_pixels_per <= aoi_settings["SCL_masked_pixels_max_percentage"] \
                and valid_pixels_per >= aoi_settings["valid_pixels_min_percentage"]:
            try:
                if (download_thumbnails or download_overviews) or download_data:
                    msg = f"Getting {''.join(data_msg)} for: {items[0].id}"
                    logger.info(msg)

                # Create results directory
                if not os.path.isdir(result_dir):
                    os.makedirs(result_dir)

                if download_thumbnails or download_overviews:
                    if num_tiles != 1:
                        raise Exception("Not yet possible to download overviews and thumbnails for mosaics.")
                    else:
                        if download_thumbnails:
                            file_url = items[0].assets["thumbnail"].href
                            logger.info(file_url)
                            thumbnail_path = os.path.join(result_dir,
                                                          f"{items[0].id}_{file_url.rsplit('/', 1)[1]}")
                            urllib.request.urlretrieve(file_url, thumbnail_path)
                        if download_overviews:
                            file_url = items[0].assets["visual"].href
                            logger.info(file_url)
                            overview_path = os.path.join(result_dir,
                                                         f"{items[0].id}_{file_url.rsplit('/', 1)[1]}")
                            urllib.request.urlretrieve(file_url, overview_path)

                if download_data:
                    scl_band_mask = None
                    # Save the SCL band
                    saveRasterToDisk(out_image=scl_band,
                                     raster_crs=scl_crs,
                                     out_transform=scl_trans,
                                     output_raster_path=output_scl_path)

                    if cloudmasking:
                        # Mask out Clouds
                        scl_band_mask = np.where(np.isin(scl_band, scl_filter_values + [0]),
                                                 np.uint16(0), np.uint16(1))
                    del scl_band

                    # Download all other bands
                    bands = tile_settings["bands"]
                    logger.info(f"Bands to retrieve: {bands}")

                    for band in bands:
                        output_band_path = os.path.join(result_dir,
                                                        f"{items_date.replace('-', '')}_{sensor_name}_{band}.tif")
                        if num_tiles > 1:
                            srcs_to_mosaic = []
                            bounds_window = None
                            for item_idx in range(len(items)):
                                file_url = items[item_idx].assets[band].href
                                logger.info(file_url)
                                band_src = rasterio.open(file_url)
                                if item_idx == 0:
                                    raster_crs = band_src.crs
                                    win_scale_factor = band_src.transform[0] / scl_src.transform[0]
                                    bb_window = Window(scl_bb_window.col_off / win_scale_factor,
                                                       scl_bb_window.row_off / win_scale_factor,
                                                       scl_bb_window.width / win_scale_factor,
                                                       scl_bb_window.height / win_scale_factor)
                                    bounds_window = bounds(bb_window, band_src.transform)
                                srcs_to_mosaic.append(band_src)
                            op_start = time.time()
                            raster_band, raster_trans = \
                                merge(datasets=srcs_to_mosaic,
                                      target_aligned_pixels=True,
                                      bounds=bounds_window,
                                      res=target_resolution,
                                      resampling=Resampling[aoi_settings["resampling_method"]])
                            logger.debug(f"Merging band {band} took {(time.time() - op_start) * 1000} msecs.")
                        else:
                            file_url = items[0].assets[band].href
                            logger.info(file_url)
                            with rasterio.open(file_url) as band_src:
                                raster_crs = band_src.crs
                                band_scale_factor = band_src.transform[0] / target_resolution
                                win_scale_factor = band_src.transform[0] / scl_src.transform[0]
                                bb_window = Window(scl_bb_window.col_off / win_scale_factor,
                                                   scl_bb_window.row_off / win_scale_factor,
                                                   scl_bb_window.width / win_scale_factor,
                                                   scl_bb_window.height / win_scale_factor)
                                op_start = time.time()
                                if band_scale_factor != 1.0:
                                    raster_band = \
                                        band_src.read(window=bb_window,
                                                      out_shape=(band_src.count,
                                                                 dst_height,
                                                                 dst_width),
                                                      resampling=Resampling[aoi_settings["resampling_method"]])
                                else:
                                    raster_band = band_src.read(window=bb_window)
                                logger.debug(f"Reading band {band} took {(time.time() - op_start) * 1000} msecs.")
                                raster_trans_win = band_src.window_transform(bb_window)
                                raster_trans = rasterio.Affine(band_src.transform[0] / band_scale_factor,
                                                               0,
                                                               raster_trans_win[2],
                                                               0,
                                                               band_src.transform[4] / band_scale_factor,
                                                               raster_trans_win[5])
                        if not aoi_is_bb:
                            raster_band = raster_band * aoi_mask
                        if cloudmasking:
                            op_start = time.time()
                            raster_band = raster_band * scl_band_mask
                            logger.debug(f"Masking band {band} took {(time.time() - op_start) * 1000} msecs.")

                        op_start = time.time()
                        saveRasterToDisk(out_image=raster_band,
                                         raster_crs=raster_crs,
                                         out_transform=raster_trans,
                                         output_raster_path=output_band_path)
                        logger.debug(f"Saving band {band} to disk took {(time.time() - op_start) * 1000} msecs.")
                        del raster_band
            except Exception as err:
                logger.error(f"For date {items_date} there was an exception: {err}")
                scenes_info[items_date.replace('-', '')]["error_info"] = f"Failed to download scenes:{err}."
            else:
                scenes_info[items_date.replace('-', '')]["data_available"] = True
                for item in items:
                    scenes_info[items_date.replace('-', '')]["item_ids"].append({"id": item.to_dict()["id"]})
        else:
            logger.error(f"For date {items_date} there is not any"
                         f" available data for the current tile and AOI settings.")

    scenes_info_path = os.path.join(result_dir,
                                    f"scenes_info_{datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}.json")
    if os.path.exists(scenes_info_path):
        raise IOError(f"The scenes_info file: {scenes_info_path} already exists.")
    else:
        with open(scenes_info_path, "w") as write_file:
            json.dump(scenes_info, write_file, indent=4)

    # close log-file to avoid problems with deleting the files
    if logger.hasHandlers():
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.flush()
            handler.close()


def downloadTileID(*, config_dict: dict):
    """downloadTileID.

    Parameters
    ----------
    config_dict : dict
        Content of the user config file.

    Raises
    ------
    Exception
        Failed to save raster to disk.
    """
    # read the variables from the config:
    tile_settings = config_dict['user_settings']['tile_settings']
    aoi_settings = config_dict['user_settings']['aoi_settings']
    result_settings = config_dict['user_settings']['result_settings']
    s2_settings = config_dict['s2_settings']

    result_dir = result_settings['results_dir']
    download_data = result_settings['download_data']
    download_thumbnails = result_settings['download_thumbnails']
    download_overviews = result_settings['download_overviews']
    target_resolution = result_settings['target_resolution']
    logging_level = logging.getLevelName(result_settings['logging_level'])

    logFormatter = logging.Formatter("[%(levelname)-5.5s]  %(message)s")
    logger = logging.getLogger(__name__)

    fileHandler = logging.FileHandler("{0}/{1}.log".format(result_dir, "s2DataDownloader"), mode='w')
    fileHandler.setFormatter(logFormatter)
    logger.addHandler(fileHandler)

    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setFormatter(logFormatter)
    logger.addHandler(consoleHandler)
    logger.setLevel(logging_level)

    cloudmasking = aoi_settings["apply_SCL_band_mask"]

    # search for Sentinel-2 data within the bounding box as defined in query_props.json (no data download yet)
    aws_items = searchDataAtAWS(s2_collection=s2_settings['collections'],
                                bb=None,
                                polygon=None,
                                date_range=aoi_settings['date_range'],
                                props_json=tile_settings,
                                stac_catalog_url=s2_settings['stac_catalog_url'],
                                logger=logger)

    data_msg = []
    if download_thumbnails:
        data_msg.append("thumbnail")
    if download_overviews:
        data_msg.append("overview")
    if download_data:
        data_msg.append("data")

    items_per_date = groupItemsPerDate(items_list=aws_items)
    scl_filter_values = aoi_settings["SCL_filter_values"]
    scenes_info = {}
    for items_date in items_per_date.keys():
        scenes_info[items_date.replace('-', '')] = {
            "item_ids": list(),
            "nonzero_pixels": list(),
            "masked_pixels": list(),
            "valid_pixels": list(),
            "data_available": list(),
            "error_info": list()
        }
        for item in items_per_date[items_date]:
            scenes_info[items_date.replace('-', '')]["item_ids"].append({"id": item.id})
            output_path = os.path.join(result_dir,
                                       f"{item.properties['mgrs:utm_zone']}",
                                       f"{item.properties['mgrs:latitude_band']}",
                                       f"{item.properties['mgrs:grid_square']}",
                                       f"{items_date.split('-')[0]}",
                                       f"{items_date.split('-')[1]}",
                                       f"{item.properties['s2:product_uri'].split('.')[0]}")
            output_scl_path = os.path.join(output_path, "SCL.tif")

            file_url = item.assets["scl"].href
            with rasterio.open(file_url) as scl_src:
                scl_trans = scl_src.transform
                scl_scale_factor = scl_src.transform[0] / target_resolution
                if scl_scale_factor != 1.0:
                    dst_height = int(scl_src.height * scl_scale_factor)
                    dst_width = int(scl_src.width * scl_scale_factor)
                    scl_band = scl_src.read(out_shape=(scl_src.count,
                                                       dst_height,
                                                       dst_width),
                                            resampling=Resampling.nearest)
                    scl_trans = rasterio.Affine(scl_src.transform[0] / scl_scale_factor,
                                                0,
                                                scl_src.transform[2],
                                                0,
                                                scl_src.transform[4] / scl_scale_factor,
                                                scl_src.transform[5])
                else:
                    scl_band = scl_src.read()
            scl_crs = scl_src.crs

            nonzero_pixels_per, masked_pixels_per, valid_pixels_per = \
                validPixelsFromSCLBand(
                    scl_band=scl_band,
                    scl_filter_values=scl_filter_values,
                    logger=logger)

            scenes_info[items_date.replace('-', '')]["nonzero_pixels"].append(nonzero_pixels_per)
            scenes_info[items_date.replace('-', '')]["masked_pixels"].append(masked_pixels_per)
            scenes_info[items_date.replace('-', '')]["valid_pixels"].append(valid_pixels_per)

            if nonzero_pixels_per >= aoi_settings["aoi_min_coverage"] \
                    and masked_pixels_per <= aoi_settings["SCL_masked_pixels_max_percentage"] \
                    and valid_pixels_per >= aoi_settings["valid_pixels_min_percentage"]:
                try:
                    if (download_thumbnails or download_overviews) or download_data:
                        msg = f"Getting {''.join(data_msg)} for: {item.id}"
                        logger.info(msg)

                    # Create results directory
                    if not os.path.isdir(result_dir):
                        os.makedirs(result_dir)

                    if download_thumbnails or download_overviews:
                        os.makedirs(name=output_path, exist_ok=True)
                        if download_thumbnails:
                            file_url = item.assets["thumbnail"].href
                            logger.info(file_url)
                            thumbnail_path = os.path.join(output_path,
                                                          f"{item.id}_{file_url.rsplit('/', 1)[1]}")
                            urllib.request.urlretrieve(file_url, thumbnail_path)
                        if download_overviews:
                            file_url = item.assets["visual"].href
                            logger.info(file_url)
                            overview_path = os.path.join(output_path,
                                                         f"{item.id}_{file_url.rsplit('/', 1)[1]}")
                            urllib.request.urlretrieve(file_url, overview_path)

                    if download_data:
                        scl_band_mask = None
                        os.makedirs(name=output_path, exist_ok=True)

                        # Save the SCL band
                        saveRasterToDisk(out_image=scl_band.astype(rasterio.uint8),
                                         raster_crs=scl_crs,
                                         out_transform=scl_trans,
                                         output_raster_path=output_scl_path)

                        if cloudmasking:
                            # Mask out Clouds
                            scl_band_mask = np.where(np.isin(scl_band, scl_filter_values + [0]),
                                                     np.uint16(0), np.uint16(1))
                        del scl_band

                        # Download all other bands
                        bands = tile_settings["bands"]
                        logger.info(f"Bands to retrieve: {bands}")

                        for band in bands:
                            output_band_path = os.path.join(output_path, f"{band}.tif")

                            file_url = item.assets[band].href
                            logger.info(file_url)
                            with rasterio.open(file_url) as band_src:
                                raster_crs = band_src.crs
                                raster_trans = band_src.transform
                                band_scale_factor = band_src.transform[0] / target_resolution
                                op_start = time.time()
                                if band_scale_factor != 1.0:
                                    raster_band = \
                                        band_src.read(out_shape=(band_src.count,
                                                                 dst_height,
                                                                 dst_width),
                                                      resampling=Resampling[aoi_settings["resampling_method"]])
                                    raster_trans = rasterio.Affine(band_src.transform[0] / band_scale_factor,
                                                                   0,
                                                                   band_src.transform[2],
                                                                   0,
                                                                   band_src.transform[4] / band_scale_factor,
                                                                   band_src.transform[5])
                                else:
                                    raster_band = band_src.read()
                                logger.debug(f"Reading band {band} took {(time.time() - op_start) * 1000} msecs.")
                            if cloudmasking:
                                op_start = time.time()
                                raster_band = raster_band * scl_band_mask
                                logger.debug(f"Masking band {band} took {(time.time() - op_start) * 1000} msecs.")

                            op_start = time.time()
                            saveRasterToDisk(out_image=raster_band,
                                             raster_crs=raster_crs,
                                             out_transform=raster_trans,
                                             output_raster_path=output_band_path)
                            logger.debug(f"Saving band {band} to disk took {(time.time() - op_start) * 1000} msecs.")
                            del raster_band
                except Exception as err:
                    scenes_info[items_date.replace('-', '')]["data_available"].append(False)
                    logger.error(f"For date {items_date} there was an exception: {err}")
                    scenes_info[items_date.replace('-', '')]["error_info"].append(f"Failed to download scenes:{err}.")
                else:
                    scenes_info[items_date.replace('-', '')]["data_available"].append(True)
                    scenes_info[items_date.replace('-', '')]["error_info"].append("")
            else:
                scenes_info[items_date.replace('-', '')]["data_available"].append(False)
                scenes_info[items_date.replace('-', '')]["error_info"].append("")
                logger.error(f"For date {items_date} there is not any"
                             f" available data for the current tile and AOI settings.")

    scenes_info_path = os.path.join(result_dir,
                                    f"scenes_info_{datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}.json")
    if os.path.exists(scenes_info_path):
        raise IOError(f"The scenes_info file: {scenes_info_path} already exists.")
    else:
        with open(scenes_info_path, "w") as write_file:
            json.dump(scenes_info, write_file, indent=4)

    # close log-file to avoid problems with deleting the files
    if logger.hasHandlers():
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.flush()
            handler.close()


def s2Downloader(*, config_dict: dict):
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
        config_dict = Config(**config_dict).model_dump(by_alias=True)
        if (len(config_dict['user_settings']['aoi_settings']['bounding_box']) == 0 and
                "polygon" in config_dict['user_settings']['aoi_settings'] and
                config_dict['user_settings']['aoi_settings']["polygon"] is None):
            downloadTileID(config_dict=config_dict)
        else:
            downloadMosaic(config_dict=config_dict)
    except Exception as e:
        raise Exception(f"Failed to run S2Downloader main process => {e}")
