.. _usage:

Usage
=====

Expected Input Configuration
----------------------------

The package expects a configuration file in ``json`` format, like the `default_config.json`_ in the repository . A valid configuration for downloading data might look like follows:

.. code-block:: json

    {
        "user_settings": {
            "tile_settings": {
                "platform" : {"in": ["sentinel-2b", "sentinel-2a"]},
                "sentinel:data_coverage": {"ge": 0},
                "sentinel:utm_zone": {},
                "sentinel:latitude_band": {},
                "sentinel:grid_square": {},
                "eo:cloud_cover": {"le": 100},
                "bands": ["B01","B02", "B05"]
            },
            "aoi_settings": {
                "bounding_box": [13.058397, 52.376620, 13.073049, 52.383835],
                "apply_SCL_band_mask": true,
                "SCL_filter_values": [3, 7, 8, 9, 10],
                "SCL_mask_valid_pixels_min_percentage": 10,
                "aoi_min_coverage": 90,
                "resampling_method": "cubic",
                "date_range": ["2021-09-04", "2021-09-05"]
            },
            "result_settings": {
                "results_dir": "data/data_output/",
                "target_resolution": 10,
                "download_data": true,
                "download_thumbnails": false,
                "download_overviews": false,
                "logging_level": "INFO"
            }
        },
        "s2_settings": {
            "collections": [
                "sentinel-s2-l2a-cogs"
            ]
        }
    }


In the following, the parameter configuration is described in detail:

User Settings
#############

Tile Settings
=============

.. list-table::
    :header-rows: 1
    :class: tight-table

    * - Parameter
      - Description
      - Examples
    * - ``Platform``
      - Which satellite to use. Default: both A and B.
      - ``"platform" : {"in": ["sentinel-2b", "sentinel-2a"]}``
    * - ``sentinel:data_coverage``
      - Defines how much a requested Sentinel-2 tile is covered by data. Leave empty to only validate the AOI for data coverage.
      - ``"sentinel:data_coverage": {"eq": 100}``, ``"sentinel:data_coverage": {"gt": 80}``
    * - ``UTM zone``
      - Preferred UTM zone. Can be an integer from 1 to 60 or empty if no preference is desired.
      - ``"sentinel:utm_zone": {}``
    * - Latitude Band
      - The latitude band of a preferred UTM zone or tile. Example: "U" for tile 32UQC.
      - ``"sentinel:latitude_band": {}``
    * - Grid Square
      - The grid square if only a certain tile should be downloaded. Example: "QC" for tile 32UQC.
      - ``"sentinel:grid_square": {}``
    * - ``eo:cloud_cover``
      - The amount of clouds that are allowed at the **entire** Sentinel-2 scene. Leave empty to only validate the AOI for cloud coverage.
      - ``"eo:cloud_cover": {"eq": 0}``, ``"eo:cloud_cover": {"lt": 20}``
    * - ``bands``
      - Defines which Sentinel-2 bands to download. You may choose from these options: ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B09", "B11", "B12"].
      - ``"bands": ["B01", "B05","B08"]``


AOI Settings
============

.. list-table::
    :header-rows: 1
    :class: tight-table

    * - Parameter
      - Description
      - Examples
    * - ``Bounding Box``
      - The BoundingBox of the AOI in lat/lon format.
      - ``"bounding_box": [13.058397, 52.376620, 13.073049, 52.383835]``
    * - ``apply_SCL_band_mask``
      - Boolean Variable. If set to true the SCL band of Sentinel-2 is used to mask out pixels. The SCL band is saved along to an extra file.
      - ``"apply_SCL_band_mask": true``
    * - ``SCL_filter_values``
      - List of integer-Values corresponding to the SCL classes. It's default classes are: cloud shadow (class 3), clouds (classes 7, 8, 9) and thin cirrus (class 10).
      - ``"SCL_filter_values": [3, 7, 8, 9, 10]"``
    * - ``SCL_mask_valid_pixels_min_percentage``
      - If cloud masking based on the SCL band is applied, it may happen that images are saved which contain only very few valid pixels. Here the user can define a percentage value of minimum valid pixels that should be left over after masking in order to save the image.
      - ``"SCL_mask_valid_pixels_min_percentage": 70``
    * - ``aoi_min_coverage``
      - User defined threshold for noData values inside the AOI. It may happen due to Sentinel-2 data tile structure that parts of the AOI have noData values. Here the user can define a percentage value of minimum valid pixels inside the AOI.
      - ``"aoi_min_coverage": 90``
    * - ``resampling_method``
      - User definition of the resampling method that should be used. Currently, these options are supported: nearest, bilinear, cubic.
      - ``"resampling_method": "nearest"``, ``"resampling_method": "bilinear"``, ``"resampling_method": "cubic"``
    * - ``date_range``
      - The period of time data should be looked for, defined by starting and end date. It is also possible to provide just a single day.
      - ``"date_range": ["2021-09-04", "2021-09-05"]``

Result Settings
===============

.. list-table::
    :header-rows: 1
    :class: tight-table

    * - Parameter
      - Description
      - Examples
    * - ``results_dir``
      - Output directory to which the downloaded data should be saved to.
      - ``"results_dir": "data_output/"``
    * - ``target_resolution``
      - The spatial resolution the output tif file(s) should have in meters. It should be either 10, 20 or 60.
      - ``"target_resolution": 10``
    * - ``download_data``
      - Boolean variable, If set to true the scenes are downloaded. If set to false only a list of available data is saved as a JSON file but no data is downloaded.
      - ``"download_data": true``
    * - ``download_thumbnails``
      - Boolean variable. If this parameter is set to true the thumbnail for each available scenes is downloaded.
      - ``"download_thumbnails": false``
    * - ``download_overviews``
      - Boolean variable. If this parameter is set to true the overview for each available scenes is downloaded.
      - ``"download_overviews": false``
    * - ``logging_level``
      - Logging level, it should be one of: DEBUG, INFO, WARN, or ERROR.
      - ``"logging_level": "INFO"``


S2 Settings
###########

**Note:** The S2 settings are not to be altered by the user!

.. list-table::
    :header-rows: 1
    :class: tight-table

    * - Parameter
      - Description
      - Examples
    * - ``collections``
      - The Sentinel-2 preprocessing level of data to be downloaded. Currently only the S2 L2A download is tested.
      - ``"collections": ["sentinel-s2-l2a-cogs"]``

Expected Output
---------------

The following files are saved within the defined output folder:

.. code-block::

  - <date_sensor_band>.tif
  - <date_sensor>_SCL.tif
  - <sensor_tile_date>_0_L2A_L2A_PVI.tif
  - <sensor_tile_date>_0_L2A_preview.jpg
  - s2DataDownloader.log
  - scenes_info_<daterange>.json

**date_sensor_band.tif**
The tif file of each band. Example: 20210905_S2B_B01.tif for date 2021-09-05, sensor B and band 1.

**date_sensor_SCL.tif**
The tif file for the scl band of the according date. Example: 20210905_S2B_SCL.tif

**sensor_tile_date_0_L2A_L2A_PVI.tif**
If "download_overviews" is set to true this file contains the overview per sensor, tile and date. Example: S2B_33UUU_20210908_0_L2A_L2A_PVI.tif

**sensor_tile_date_0_L2A_preview.jpg**
If "download_thumbnails" is set to true this file contains the thumbnail per sensor, tile and date. Example: S2B_33UUU_20210908_0_L2A_preview.jpg

**s2DataDownloader.log**
The log file containing all logs. The logging level can be set in the result settings in the config.json.

**scenes_info_daterange.json**
The information about the scenes for a certain date range. Example: scenes_info_2021-09-04_2021-09-05.json.

.. code-block:: json

    {
        "20210905": {
            "item_ids": [
                {
                    "id": "S2B_33UUU_20210905_0_L2A"
                }
            ],
            "nonzero_pixels": 100.0,
            "valid_pixels": 100.0,
            "data_available": true,
            "error_info": ""
        }
    }

For each date the following information is saved:

**item_ids:** The items (scenes) found at aws for that date.

**nonzero_pixels:** Percentage of pixels with non zero values.

**valid_pixels:** Percentage of pixels with valid data.

**data_available:** If false no data for this date was found.

**error_info:** If any error occurred during the download the error message will be saved here.
