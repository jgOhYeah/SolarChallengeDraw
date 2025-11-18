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
from knockout_sheet import InteractiveNumberBoxFactory, PrintNumberBoxFactory
import gui
import knockout
import car


def get_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tool to generate draws for the VMSVC Don Sheridan Kit Car Challenge.",
        epilog="Written by Jotham Gates, 2025.",
    )
    parser.add_argument(
        "-c", "--cars", type=str, default=None, help="CSV file containing cars to load."
    )
    parser.add_argument(
        "-g",
        "--ghostscript",
        default=None,
        help="The name / path to the Ghostscript installation. This is required for exporting PDFs. On Linux and macOS this defaults to `gs`. On Windows this defaults to `gswin64c.exe`.",
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
    cars = car.load_cars(args.cars)
    knockout_event = knockout.KnockoutEvent(cars, "Test event")
    knockout_event.print()
    gui_ui = gui.Gui(ghostscript_location(args.ghostscript))
    gui_ui.knockout.draw_event(knockout_event)
    gui_ui.run()
