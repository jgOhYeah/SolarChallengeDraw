"""Represents the knockout competition."""

from __future__ import annotations
from dataclasses import dataclass
from typing import List
import numpy as np
import data

NO_SEED = -1000


class KnockoutRace:
    def __init__(
        self,
        event: data.Event,
        race: int,
        round: int,
        car_lane_1: data.Car,
        car_lane_2: data.Car | None,
        winner_next_race: KnockoutRace | None = None,
        loser_next_race: KnockoutRace | None = None,
    ) -> None:
        self._event = event
        self._race = race
        self._round = round
        self._car_lane_1 = car_lane_1
        self._car_lane_2 = car_lane_2
        self._winner_next_race = winner_next_race
        self._loser_next_race = loser_next_race
        self._winner: data.Car | None = None  # May not be needed.

    def is_bye(self) -> bool:
        """Checks if this race is a bye.

        Returns:
            bool: True if the race is a bye.
        """
        return self._car_lane_2 is None

    def __repr__(self) -> str:
        if self.is_bye():
            return f"({self._car_lane_1.car_id}+{self._car_lane_1.points} (bye))"
        else:
            return f"({self._car_lane_1.car_id}+{self._car_lane_1.points},{self._car_lane_2.car_id}+{self._car_lane_2.points})"

    def __str__(self) -> str:
        return repr(self)


class KnockoutEvent:
    def __init__(self, main_event: data.Event, cars: List[data.Car]) -> None:
        """Initialises the knockout event with a list of cars."""
        sorted_cars = sorted(
            cars,
            key=lambda c: c.points if c.points is not None else NO_SEED,
            reverse=True
        )
        min_draw_size = int(2 ** np.ceil(np.log2(len(cars))))
        assert min_draw_size % 2 == 0, "Min draw size should be a power of 2."

        # Create races with the highest and lowest seeds paired.
        actual_races = int(np.ceil(len(cars)/2))
        races: List[None | KnockoutRace] = [None] * actual_races # (min_draw_size // 2)
        race_index = 0
        end = 1
        while len(sorted_cars) > 0:
            high_seed = sorted_cars.pop()
            low_seed = None
            if len(sorted_cars) % 2 != 0:
                # Make a bye whenever we have an uneven number of cars.
                low_seed = sorted_cars.pop(0)
            races[race_index * end] = KnockoutRace(
                event=main_event,
                race=0,
                round=0,
                car_lane_1=high_seed,
                car_lane_2=low_seed,
            )
            if end > 0:
                race_index += 1
            end *= -1

        for r in races:
            print(repr(r))
