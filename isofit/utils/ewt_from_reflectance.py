#! /usr/bin/env python3
#
#  Copyright 2018 California Institute of Technology
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
# ISOFIT: Imaging Spectrometer Optimal FITting
# Author: Philip G. Brodrick, philip.brodrick@jpl.nasa.gov

import atexit
import logging
import os
import time
from types import SimpleNamespace

import click
import numpy as np
import ray
from osgeo import gdal
from spectral.io import envi

from isofit.core.common import envi_header
from isofit.core.fileio import write_bil_chunk
from isofit.inversion.inverse_simple import invert_liquid_water


def main(args: SimpleNamespace) -> None:
    """
    Calculate Equivalent Water Thickness (EWT) / Canopy Water Content (CWC) for a set of reflectance data, based on
    Beer Lambert Absorption of liquid water.
    """
    logging.basicConfig(
        format="%(levelname)s:%(asctime)s ||| %(message)s",
        level=args.loglevel,
        filename=args.logfile,
        datefmt="%Y-%m-%d,%H:%M:%S",
    )

    if os.path.isfile(args.output_cwc_file):
        dat = gdal.Open(args.output_cwc_file).ReadAsArray()
        if not np.all(dat == -9999):
            logging.info("Existing CWC file found, terminating")
            exit()

    rfl_ds = envi.open(envi_header(args.reflectance_file))
    rfl = rfl_ds.open_memmap(interleave="bip")
    rfls = rfl.shape
    wl = np.array([float(x) for x in rfl_ds.metadata["wavelength"]])

    logging.info("init inversion")
    res_0, abs_co_w = invert_liquid_water(rfl[0, 0, :].copy(), wl, return_abs_co=True)

    logging.info("init inversion complete")

    output_metadata = rfl_ds.metadata
    output_metadata["interleave"] = "bil"
    output_metadata["bands"] = "1"
    output_metadata[
        "description"
    ] = "L2A Canopy Water Content / Equivalent Water Thickness"
    if "emit pge input files" in list(output_metadata.keys()):
        del output_metadata["emit pge input files"]

    img = envi.create_image(
        envi_header(args.output_cwc_file), ext="", metadata=output_metadata, force=True
    )
    del img, rfl_ds
    logging.info("init cwc created")

    # Initialize ray cluster
    start_time = time.time()
    n_cores = args.n_cores
    if args.n_cores == -1:
        n_cores = args.n_cores
    rayargs = {
        "ignore_reinit_error": True,
        "local_mode": args.n_cores == 1,
        "_temp_dir": args.ray_tmp_dir,
        "num_cpus": n_cores,
    }

    ray.init(**rayargs)
    atexit.register(ray.shutdown)

    n_workers = 40  # Hardcoded
    line_breaks = np.linspace(0, rfls[0], n_workers, dtype=int)
    line_breaks = [
        (line_breaks[n], line_breaks[n + 1]) for n in range(len(line_breaks) - 1)
    ]

    start_time = time.time()
    logging.info("Beginning parallel CWC inversions")
    result_list = [
        run_lines.remote(
            args.reflectance_file,
            args.output_cwc_file,
            wl,
            abs_co_w,
            line_breaks[n],
            args.loglevel,
            args.logfile,
        )
        for n in range(len(line_breaks))
    ]
    results = [ray.get(result) for result in result_list]

    total_time = time.time() - start_time
    logging.info(
        f"CWC inversions complete.  {round(total_time,2)}s total, "
        f"{round(rfls[0]*rfls[1]/total_time,4)} spectra/s, "
        f"{round(rfls[0]*rfls[1]/total_time/n_workers,4)} spectra/s/core"
    )


@ray.remote
def run_lines(
    rfl_file: str,
    output_cwc_file: str,
    wl: np.array,
    abs_co_w: np.array,
    startstop: tuple,
    loglevel: str = "INFO",
    logfile=None,
) -> None:
    """
    Run a set of spectra for EWT/CWC.

    Args:
        rfl_file: input reflectance file location
        output_cwc_file: output cwc file location
        wl: wavelengths
        loglevel: output logging level
        logfile: output logging file
    """

    logging.basicConfig(
        format="%(levelname)s:%(asctime)s ||| %(message)s",
        level=loglevel,
        filename=logfile,
        datefmt="%Y-%m-%d,%H:%M:%S",
    )
    rfl = envi.open(envi_header(rfl_file)).open_memmap(interleave="bip")

    start_line, stop_line = startstop
    output_cwc = np.zeros((stop_line - start_line, rfl.shape[1], 1)) - 9999

    for r in range(start_line, stop_line):
        for c in range(rfl.shape[1]):
            meas = rfl[r, c, :]
            if np.all(meas < 0):
                continue
            output_cwc[r - start_line, c, 0] = invert_liquid_water(meas, wl)[0]

        logging.info(f"CWC writing line {r}")

        write_bil_chunk(
            output_cwc[r - start_line, ...].T,
            output_cwc_file,
            r,
            (rfl.shape[0], rfl.shape[1], output_cwc.shape[2]),
        )


@click.command(name="ewt")
@click.argument("reflectance_file")
@click.argument("output_cwc_file", required=False)
@click.option("--loglevel", default="INFO")
@click.option("--logfile")
@click.option("--n_cores", type=int, default=1)
@click.option("--ray_tmp_dir")
@click.option(
    "--debug-args",
    help="Prints the arguments list without executing the command",
    is_flag=True,
)
def _cli(debug_args, **kwargs):
    """\
    Calculate Equivalent Water Thickness (EWT) / Canopy Water Content (CWC) for a set of reflectance data, based on Beer Lambert Absorption of liquid water.
    """
    click.echo("Running EWT from Reflectance")
    if debug_args:
        click.echo("Arguments to be passed:")
        for key, value in kwargs.items():
            click.echo(f"  {key} = {value!r}")
    else:
        # SimpleNamespace converts a dict into dot-notational for backwards compatability with argparse
        main(SimpleNamespace(**kwargs))

    click.echo("Done")


if __name__ == "__main__":
    _cli()
else:
    from isofit import cli

    cli.add_command(_cli)
