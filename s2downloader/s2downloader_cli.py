#!/usr/bin/env python

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
"""Console script for s2downloader."""

import argparse
import json
import os
from argparse import ArgumentParser
from json import JSONDecodeError

from s2downloader.config import Config
from s2downloader.s2downloader import s2Downloader


def getArgparser() -> ArgumentParser:
    """
    Get a console argument parser for Sentinel2 Downloader.

    Returns
    -------
    ArgumentParser
        Argument Parser.
    """
    parser = argparse.ArgumentParser(
        prog="S2Downloader",
        usage="S2Downloader [-h] --filepath FILEPATH",
        epilog="Python package to download Sentinel-2 data from the AWS server. Powered by FERN.Lab",
    )

    parser.add_argument(
        "-f", "--filepath", type=str, required=True, help="Path to the config.json file", metavar="FILE"
    )

    return parser


def main(prog_name="S2Downloader") -> int:
    """
    Call the Main function for pipeline test.

    Parameters
    ----------
    prog_name : str
        Program name.

    Returns
    -------
    int : Successful or not the execution.

    Raises
    ------
    OSError
        Failed to load the configuration json file.
    SystemExit
        If S2Downloader main process fails to run.
    """
    try:
        # check current directory
        print(f"Sentinel 2 Download Directory: {os.getcwd()}")

        # if filepath and section were parsed use it instead of test-config
        parser = getArgparser()
        args = parser.parse_args()
        fp = args.filepath

        root_path = "../bin/"
        if (
            os.path.basename(os.getcwd()) == "bin"
            or os.path.basename(os.getcwd()) == "demo"
            or os.path.basename(os.getcwd()) == "test"
            or os.path.basename(os.getcwd()) == os.path.basename(os.path.dirname(os.getcwd()))
        ):
            root_path = "/"

        config_file_path = os.path.abspath(os.path.join(root_path, fp))

        try:
            with open(config_file_path) as config_fp:
                config_dict = json.load(config_fp)
                config = Config(**config_dict).model_dump(by_alias=True)
        except JSONDecodeError as e:
            raise OSError(f"Failed to load the configuration json file => {e}") from e

        # call main function for retrieving Sentinel 2 data from AWS server
        s2Downloader(config_dict=config)
    except Exception as e:
        raise SystemExit(f"Exit in {prog_name} function\n{e}") from e

    print(f"{prog_name} succeeded.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    main(prog_name="S2Downloader")
