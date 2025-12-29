"""save_load.py
Saves and loads the event to and from a file."""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Dict, List, cast
import pandas as pd
import numpy as np
import json

from car import Car
from knockout import KnockoutEvent
from knockout_race import Race, RaceBranch


class Loader(ABC):
    """Base class for a loader that can save and load an event. This allows multiple file formats to be supported eventually."""

    def __init__(self, cars: List[Car] | None, knockout: KnockoutEvent | None) -> None:
        self._cars = cars
        self._knockout = knockout

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

    def save(self) -> None:
        """Saves the results"""
        raise NotImplementedError("Saving is not implemented for this loader.")

    def load(self) -> None:
        """Loads the data."""
        raise NotImplementedError("Loading is not implemented for this loader.")


class JSONLoader(Loader):
    """Saves and loads knockout events to and from json files."""

    def __init__(
        self,
        filename: str,
        cars: List[Car] | None = None,
        knockout: KnockoutEvent | None = None,
    ) -> None:
        super().__init__(cars=cars, knockout=knockout)
        self.filename = filename

    class Fields(StrEnum):
        CARS = "Cars"
        KNOCKOUT = "Knockout"

    def save(self) -> None:
        cars_list: List[Dict[Car.Fields, Any]] | None = None
        if self._cars is not None:
            cars_list = [c.to_dict() for c in self._cars]

        knockout_dict = self._knockout.to_dict() if self._knockout is not None else None

        combined = {self.Fields.CARS: cars_list, self.Fields.KNOCKOUT: knockout_dict}
        with open(self.filename, "w") as file:
            json.dump(combined, file, indent=4)


class CarCSVLoader(Loader):
    """Loads cars from a CSV file."""

    def __init__(
        self,
        filename: str,
        cars: List[Car] | None = None,
        knockout: KnockoutEvent | None = None,
    ) -> None:
        super().__init__(cars=cars, knockout=knockout)
        self._filename = filename

    def load(self) -> None:
        car_df = pd.read_csv(self._filename)
        self.cars = [
            Car.from_dict(cast(Dict[str, Any], dt))
            for dt in car_df.to_dict(orient="records")
        ]
