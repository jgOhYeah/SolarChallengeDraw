"""Represents the knockout competition."""

from __future__ import annotations
from abc import ABC
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, cast
import numpy as np
import data

NO_SEED = -1000


class KnockoutRace:
    def __init__(
        self,
        race: int,
        round: int,
        car_lane_1: data.Car | None = None,
        car_lane_2: data.Car | None = None,
        winner_next_race: KnockoutRace | None = None,
        loser_next_race: KnockoutRace | None = None,
    ) -> None:
        self._race = race
        self._round = round
        self._car_lane_1 = car_lane_1
        self._car_lane_2 = car_lane_2
        self._winner_next_race = winner_next_race
        self._loser_next_race = loser_next_race
        self._winner: data.Car | None = None  # May not be needed.

    def is_empty(self) -> bool:
        """Checks if there are any cars assigned to this race."""
        assert (
            self._car_lane_1 is not None or self._car_lane_2 is None
        ), "The car in lane 1 cannot be left blank when the car in lane 2 is filled in."
        return self._car_lane_1 is None

    def is_bye(self) -> bool:
        """Checks if this race is a bye.

        Returns:
            bool: True if the race is a bye.
        """
        return self._car_lane_1 is not None and self._car_lane_2 is None

    def __repr__(self) -> str:
        id = f"Race {self._round}.{self._race:>03d}"
        if self.is_empty():
            return id + "(___+_, ___+_)"
        if self.is_bye():
            return id + f"({cast(data.Car, self._car_lane_1).car_id}+{cast(data.Car, self._car_lane_1).points} (bye))"
        else:
            return id + f"({cast(data.Car, self._car_lane_1).car_id}+{cast(data.Car, self._car_lane_1).points},{cast(data.Car, self._car_lane_2).car_id}+{cast(data.Car, self._car_lane_2).points})"

    def __str__(self) -> str:
        return repr(self)


class RoundType(Enum):
    """Represents the type of round (winner's and loser's)"""

    INITIAL = auto()
    WINNERS = auto()
    LOSERS = auto()


class KnockoutRound(ABC):
    """Base class for knockout rounds."""

    def __init__(
        self, round: int, round_type: RoundType, races: List[KnockoutRace]
    ) -> None:
        self.round = round
        self.round_type = round_type
        self.races = races

        for r in races:
            print(repr(r))
    
    def __len__(self) -> int:
        return len(self.races)


class InitialKnockoutRound(KnockoutRound):
    def __init__(self, cars: List[data.Car]) -> None:
        """Initialises the knockout event with a list of cars."""
        sorted_cars = sorted(
            cars,
            key=lambda c: c.points if c.points is not None else NO_SEED,
            reverse=True,
        )
        # Calculate the minimum draw size. This must be a power of 2.
        min_draw_size = int(2 ** np.ceil(np.log2(len(cars))))

        # Create races with the highest and lowest seeds paired.
        races: List[None | KnockoutRace] = [None] * (min_draw_size // 2)

        def is_bye_needed(races_filled: int) -> bool:
            """Determines if a bye is needed to get the required number of races."""
            byes = min_draw_size - len(cars)
            res = races_filled < byes
            return res

        for race_number in range(len(races)):
            high_seed = sorted_cars.pop()
            low_seed = None
            if not is_bye_needed(race_number):
                # Make a bye whenever we have an uneven number of cars.
                low_seed = sorted_cars.pop(0)
            # Alternate ends of the draw (1st and last as first race, 2nd and 2nd last as last race).
            index = race_number // 2 if race_number % 2 == 0 else -race_number // 2
            races[index] = KnockoutRace(
                race=0,
                round=0,
                car_lane_1=high_seed,
                car_lane_2=low_seed,
            )

        # Fix the race numbers.
        for i, race in enumerate(races):
            assert race is not None, "No None races should have made it to here."
            race._race = i

        super().__init__(0, RoundType.INITIAL, cast(List[KnockoutRace], races))


class SubsequentRound(KnockoutRound):
    """Represents subsequent rounds."""
    def __init__(
        self,
        round: int,
        index_start: int,
        previous_round: KnockoutRound,
        round_type: RoundType,
    ) -> None:
        # Create a new list of races and link the races from the previous round to this.
        races: List[KnockoutRace] = []
        for race in range(len(previous_round.races) // 2):
            # Create the new round.
            this_race = KnockoutRace(
                race + index_start,
                round=round,
            )
            races.append(this_race)

            # Link the precessing round to this one.
            match round_type:
                case RoundType.WINNERS:
                    previous_round.races[2*race]._winner_next_race = this_race
                    previous_round.races[2*race+1]._winner_next_race = this_race
                case RoundType.LOSERS:
                    previous_round.races[2*race]._loser_next_race = this_race
                    previous_round.races[2*race+1]._loser_next_race = this_race

        super().__init__(round, round_type, races)

class KnockoutEvent:
    """Class for managing a knockout event."""
    def __init__(self, cars: List[data.Car]) -> None:
        rounds: List[KnockoutRound] = [
            InitialKnockoutRound(cars)
        ]
        round_number = 1
        races = len(rounds[-1])
        while len(rounds[-1]) > 1:
            rounds.append(SubsequentRound(round_number, races, rounds[-1], RoundType.WINNERS))
            round_number += 1