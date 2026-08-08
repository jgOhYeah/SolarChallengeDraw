"""save_load.py
Saves and loads the event to and from a file."""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
import os
from typing import Any, Dict, List, cast
import pandas as pd
import numpy as np
import json
import subprocess
from datetime import datetime
from car import Car
from knockout import KnockoutEvent
from knockout_race import Race, RaceBranch


class Metadata:
    current_hash: str|None = None

    def __init__(self) -> None:
        if self.current_hash is None:
            # Only check the first time to reduce extra process calls.
            self.current_hash = self._get_git_revision_short_hash()
        self.git_hash = self.current_hash

        self.update()

    def update(self) -> None:
        self.git_hash = self.current_hash
        self.modification_date = datetime.now()

    def _get_git_revision_short_hash(self) -> str:
        """Returns the git commit hash for use in the metadata.
        Copied from https://stackoverflow.com/a/21901260

        Returns:
            str: The short hash.
        """
        try:
            result = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode("ascii").strip()
        except:
            result ="???"

        return result

    class Fields(StrEnum):
        GIT_HASH = "Git hash"
        DATE = "Date"

    TIME_FORMAT = "%Y-%m-%d %H:%M"

    def to_dict(self) -> Dict[Metadata.Fields, Any]:
        return {
            self.Fields.GIT_HASH: self.git_hash,
            self.Fields.DATE: self.modification_date.strftime(self.TIME_FORMAT)
        }

    @classmethod
    def from_dict(cls, dict:Dict[Metadata.Fields, Any]) -> Metadata:
        metadata = Metadata()
        metadata.modification_date = datetime.strptime(dict[cls.Fields.DATE], cls.TIME_FORMAT)
        metadata.git_hash = dict[cls.Fields.GIT_HASH]
        return metadata

    def __str__(self) -> str:
        base = f"Modified {self.modification_date.isoformat(sep=' ', timespec='minutes')}, Git commit '{self.git_hash}'"
        if self.current_hash != self.git_hash:
            extras = f" (opened with '{self.current_hash}')"
        else:
            extras = ""

        return base + extras


class Loader(ABC):
    """Base class for a loader that can save and load an event. This allows multiple file formats to be supported eventually."""

    def __init__(
        self,
        cars: List[Car] | None,
        knockout: KnockoutEvent | None,
        metadata: Metadata | None,
        filename: str | None,
    ) -> None:
        self._cars = cars
        self._knockout = knockout
        self._metadata = metadata
        self.filename = filename

    def is_loaded(self) -> bool:
        """Checks if any valid data is provided."""
        return (
            self.filename is not None
            and self._cars is not None
            and self._knockout is not None
        )

    class NotYetLoadedError(Exception):
        """Error that occurs when attempting to access data before it has been loaded."""

        pass

    @property
    def cars(self) -> List[Car]:
        """The list of cars used in the event."""
        if self._cars is not None:
            return self._cars
        else:
            raise self.NotYetLoadedError("The cars have not been loaded yet.")

    @cars.setter
    def cars(self, cars: List[Car]) -> None:
        self._cars = cars

    @property
    def knockout(self) -> KnockoutEvent:
        """Property that contains the knockout event."""
        if self._knockout is not None:
            return self._knockout
        else:
            raise self.NotYetLoadedError("The knockout event has not been loaded yet.")

    @knockout.setter
    def knockout(self, knockout: KnockoutEvent) -> None:
        """Saves the knockout event.

        Args:
            knockout (KnockoutEvent): The event to save.
        """
        self._knockout = knockout

    @property
    def metadata(self) -> Metadata:
        """Property that contains the metadata for the event."""
        if self._metadata is not None:
            return self._metadata
        else:
            raise self.NotYetLoadedError("The metadata has not been loaded yet.")

    @metadata.setter
    def metadata(self, metadata: Metadata) -> None:
        """Saves the metadata for the event.

        Args:
            metadata (Metadata): The metadata to save.
        """
        self._metadata = metadata

    def save(self) -> None:
        """Saves the results"""
        raise NotImplementedError("Saving is not implemented for this loader.")

    def load(self) -> None:
        """Loads the data."""
        raise NotImplementedError("Loading is not implemented for this loader.")

    class NoFilenameProvidedError(Exception):
        """No filename has been provided to save to or load from."""

        pass

    def _check_filename(self) -> None:
        """Checks if a valid filename has been provided to save to / load from.

        Raises:
            self.NoFilenameProvidedError: When there is no filename.
        """
        if self.filename is None:
            raise self.NoFilenameProvidedError("No filename provided to loader.")

    def copy_from(self, loader: Loader) -> None:
        """Copies the event from one loader to another (good for converting file formats)."""
        self.cars = loader.cars
        self.knockout = loader.knockout


class JSONLoader(Loader):
    """Saves and loads knockout events to and from json files."""

    def __init__(
        self,
        filename: str | None = None,
        cars: List[Car] | None = None,
        knockout: KnockoutEvent | None = None,
        metadata: Metadata | None = None,
    ) -> None:
        super().__init__(
            cars=cars, knockout=knockout, filename=filename, metadata=metadata
        )
        self.filename = filename

    class Fields(StrEnum):
        METADATA = "Metadata"
        CARS = "Cars"
        KNOCKOUT = "Knockout"

    def save(self) -> None:
        print(f"Saving to '{self.filename}'")
        cars_list: List[Dict[Car.Fields, Any]] | None = None
        if self._cars is not None:
            cars_list = [c.to_dict() for c in self._cars]

        knockout_dict = self._knockout.to_dict() if self._knockout is not None else None
        metadata_dict = self._metadata.to_dict() if self._metadata is not None else None

        combined = {
            self.Fields.METADATA: metadata_dict,
            self.Fields.CARS: cars_list,
            self.Fields.KNOCKOUT: knockout_dict,
        }
        self._check_filename()
        with open(cast(str, self.filename), "w") as file:
            json.dump(combined, file, indent=4)

    def load(self) -> None:
        """Loads the data from the file."""
        self._check_filename()
        with open(cast(str, self.filename), "r") as file:
            combined_dict = json.load(file)

        # Convert back into car objects.
        cars_list = combined_dict[self.Fields.CARS]
        self._cars = [Car.from_dict(car_entry) for car_entry in cars_list]

        # Get the knockout event back.
        knockout_dict = combined_dict[self.Fields.KNOCKOUT]
        self._knockout = KnockoutEvent.from_dict(knockout_dict, self.cars)

        # Metadata
        metadata_dict = combined_dict[self.Fields.METADATA]
        if metadata_dict is not None:
            self._metadata = Metadata.from_dict(metadata_dict)
        else:
            print("WARNING: No metadata present. Creating fresh metadata.")
            self._metadata = Metadata()


class CarCSVLoader(Loader):
    """Loads cars from a CSV file."""

    def __init__(
        self,
        filename: str | None = None,
        cars: List[Car] | None = None,
        knockout: KnockoutEvent | None = None,
        metadata: Metadata | None = None,
        grand_final_heats: int = 3,  # TODO: Customisable.
    ) -> None:
        super().__init__(
            cars=cars, knockout=knockout, filename=filename, metadata=metadata
        )
        self.grand_final_heats = grand_final_heats

    def load(self) -> None:  # TODO: Randomise cars with a seed if needed.
        self._check_filename()
        car_df = pd.read_csv(cast(str, self.filename))
        self._cars = [
            Car.from_dict(cast(Dict[str, Any], dt))
            for dt in car_df.to_dict(orient="records")
        ]

        aux_races = 2 ** (int(np.ceil(np.log2(len(self._cars)))) - 1) + 2

        self._knockout = KnockoutEvent.new_from_cars(
            cars=self.cars,
            name=os.path.basename(cast(str, self.filename)),
            max_auxilliary_races=aux_races,
            grand_final_heats=self.grand_final_heats,
        )

        self._metadata = Metadata()
