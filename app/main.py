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

import gui
import knockout
import car


def get_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tool to generate draws for the VMSVC Don Sheridan Kit Car Challenge.",
        epilog="Written by Jotham Gates, 2025.",
    )
    # parser.add_argument(
    #     "database",
    #     type=str,
    #     default="../database/SolarChallengeDraw.sqlite",
    #     help="The path to the sqlite database to use to store and process the data.",
    # )
    parser.add_argument(
        "-c", "--cars", type=str, default=None, help="CSV file containing cars to load."
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = get_arguments()
    cars = car.load_cars(args.cars)
    knockout_event = knockout.KnockoutEvent(cars, "Test event")
    knockout_event.print()
    gui_ui = gui.Gui()
    gui_ui.knockout._sheet.draw_canvas(knockout_event)
    gui_ui.run()