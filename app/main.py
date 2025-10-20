#!/usr/bin/env python3
import argparse
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass
import datetime
from typing import Self

import gui

def get_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tool to generate draws for the VMSVC Don Sheridan Kit Car Challenge.",
        epilog="Written by Jotham Gates, 2025.",
    )
    parser.add_argument(
        "database",
        type=str,
        help="The path to the sqlite database to use to store and process the data.",
    )
    return parser.parse_args()


@dataclass
class Event:
    event_id: int | None = None
    event_date: datetime.date = datetime.date.today()
    event_name: str | None = None

    def insert(self, cur: sqlite3.Cursor) -> int:
        """Inserts the event into the database and sets the event_id.

        Args:
            cur (sqlite3.Cursor): The database cursor.
        """
        cur.execute(
            "INSERT INTO event(event_date,event_name) VALUES (?, ?) RETURNING event_id",
            (self.event_date, self.event_name),
        )
        event_id: int = cur.fetchall()[0][0]
        self.event_id = event_id
        return event_id


@dataclass
class Car:
    event_id: int
    car_id: int
    school_id: int
    car_name: str
    car_scruitineered: bool
    present_round_robin: bool
    present_knockout: bool

    def insert(self, con: sqlite3.Connection) -> None:
        """Inserts the car into the database.

        Args:
            con (sqlite3.Cursor): The database connection.
        """
        con.execute("INSERT INTO ")


class Database:
    """Class that handles connecting to the database."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self.con: sqlite3.Connection
        self._register_datetime_adaptors()

    def _register_datetime_adaptors(self) -> None:
        """Registers adaptors.
        Copied from https://docs.python.org/3/library/sqlite3.html#adapter-and-converter-recipes
        """

        def adapt_date_iso(val):
            """Adapt datetime.date to ISO 8601 date."""
            return val.isoformat()

        def adapt_datetime_iso(val):
            """Adapt datetime.datetime to timezone-naive ISO 8601 date."""
            return val.replace(tzinfo=None).isoformat()

        def adapt_datetime_epoch(val):
            """Adapt datetime.datetime to Unix timestamp."""
            return int(val.timestamp())

        sqlite3.register_adapter(datetime.date, adapt_date_iso)
        sqlite3.register_adapter(datetime.datetime, adapt_datetime_iso)
        sqlite3.register_adapter(datetime.datetime, adapt_datetime_epoch)

        def convert_date(val):
            """Convert ISO 8601 date to datetime.date object."""
            return datetime.date.fromisoformat(val.decode())

        def convert_datetime(val):
            """Convert ISO 8601 datetime to datetime.datetime object."""
            return datetime.datetime.fromisoformat(val.decode())

        def convert_timestamp(val):
            """Convert Unix epoch timestamp to datetime.datetime object."""
            return datetime.datetime.fromtimestamp(int(val))

        sqlite3.register_converter("date", convert_date)
        sqlite3.register_converter("datetime", convert_datetime)
        sqlite3.register_converter("timestamp", convert_timestamp)

    def __enter__(self) -> Self:
        self.con = sqlite3.connect(self._db_path)
        return self

    def __exit__(self, type, value, tb):
        if self.con:
            self.con.commit()
            self.con.close()


if __name__ == "__main__":
    args = get_arguments()
    db = Database(args.database)
    with db:
        # event = Event(event_name="Test event from python")
        # event.insert(db.con.cursor())
        gui_ui = gui.Gui()
        gui_ui.run()