#!/usr/bin/env python3
"""main.py
usage: main.py [-h] database

Tool to generate draws for the VMSVC Don Sheridan Kit Car Challenge.

positional arguments:
  database    The path to the sqlite database to use to store and process the data.

options:
  -h, --help  show this help message and exit

Written by Jotham Gates, 2025.
"""

import argparse
import platform
import gui
from save_load import CarCSVLoader


def get_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tool to generate draws for the VMSVC Don Sheridan Kit Car Challenge.",
        epilog="Written by Jotham Gates, 2025.",
    )
    load_args = parser.add_mutually_exclusive_group()
    load_args.add_argument(
        "-c",
        "--cars",
        type=str,
        default=None,
        help="CSV file containing carss to load.",
    )
    load_args.add_argument(
        "-j",
        "--json",
        type=str,
        default=None,
        help="Existing knockout event saved in the JSON format to load.",
    )
    parser.add_argument(
        "-g",
        "--ghostscript",
        default=None,
        help="The name / path to the Ghostscript installation. This is required for exporting PDFs. On Linux and macOS this defaults to `gs`. On Windows this defaults to `gswin64c.exe`.",
    )
    parser.add_argument(
        "-s",
        "--show-seeds",
        action="store_true",
        help="If provided, shows the predicted seed position for each race entrant.",
    )
    csv_group = parser.add_argument_group(
        title="Parameters used when loading from CSVs",
        description="These parameters are only used when loading and creating an event from CSV file.",
    )
    csv_group.add_argument(
        "-r",
        "--randomise",
        action="store_true",
        help="If provided, randomises the list of cars prior to seeding for fairness.",
    )
    csv_group.add_argument(
        "--rng-seed",
        type=int,
        default=None,
        help="Seed for the random number generator that randomises the cars. This allows for backtracking / predictability if need be whilst remaining fair.",
    )
    csv_group.add_argument("-a", "--aux-races", type=int, default=None)
    csv_group.add_argument(
        "-b",
        "--gf-heats",
        type=int,
        default=3,
        help="The number of heats to do a best of in the grand final.",
    )
    return parser.parse_args()


def ghostscript_location(provided: str | None) -> str:
    """Returns the name of the Ghostscript binary depending on the operating system and what is provided.

    Args:
        provided (str | None): The provided entry.

    Returns:
        str: Path / filename for Ghostscript.
    """
    if provided is None:
        # Need to guess what the programme is called.
        match platform.system():
            case "Windows":
                return "gswin64c.exe"
            case "Linux" | "Darwin":
                return "gs"
            case _:
                message = "The operating system isn't known. Please explicitely provide the name / path for Ghostscript."
                print(message)
                raise ValueError(message)
    else:
        # Use what was provided.
        return provided


if __name__ == "__main__":
    args = get_arguments()
    gui_ui = gui.Gui(
        ghostscript_path=ghostscript_location(provided=args.ghostscript),
        initial_csv=args.cars,
        initial_json=args.json,
        csv_load_settings=CarCSVLoader.CSVLoadSettings(
            grand_final_heats=args.gf_heats,
            randomise=args.randomise,
            aux_races=args.aux_races,
            random_seed=args.rng_seed,
        ),
        show_seed=args.show_seeds,
    )
    gui_ui.run()
