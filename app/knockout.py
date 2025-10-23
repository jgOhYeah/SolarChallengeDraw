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
        theoretical_seed_winner: int,
        race: int|None=None,
        car_lane_1: data.Car | None = None,
        car_lane_2: data.Car | None = None,
        winner_next_race: KnockoutRace | None = None,
        loser_next_race: KnockoutRace | None = None,
    ) -> None:
        self._race = race
        self.theoretical_seed_winner = theoretical_seed_winner
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
        id = f"Race {f'{self._race:>03d}' if self._race else '?'}"
        if self.is_empty():
            return id + "(___+_, ___+_)"
        if self.is_bye():
            return (
                id
                + f"({cast(data.Car, self._car_lane_1).car_id}+{cast(data.Car, self._car_lane_1).points} (bye))"
            )
        else:
            return (
                id
                + f"({cast(data.Car, self._car_lane_1).car_id}+{cast(data.Car, self._car_lane_1).points},{cast(data.Car, self._car_lane_2).car_id}+{cast(data.Car, self._car_lane_2).points})"
            )

    def __str__(self) -> str:
        return repr(self)


class RoundType(Enum):
    """Represents the type of round (winner's and loser's)"""

    INITIAL = auto()
    WINNERS = auto()
    LOSERS = auto()


class KnockoutRound:
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
    
def is_power_of_2(n:int) -> bool:
    """https://stackoverflow.com/a/57025941"""
    return (n & (n-1) == 0) and n != 0

def generate_tree(unsorted: List[data.Car]) -> List[KnockoutRound]:
    rounds = int(np.ceil(np.log2(len(unsorted))))
    min_draw_size = 2 ** rounds
    event = [KnockoutRound(rounds, RoundType.WINNERS, [KnockoutRace(rounds, 1)])]

    def make_round(nextRound:KnockoutRound) -> KnockoutRound:
        """Makes the current round based on the next one."""
        races_in_round = 2*len(nextRound)
        races: List[KnockoutRace] = []
        for r in range(0, races_in_round, 2):
            high_seed = nextRound.races[r//2].theoretical_seed_winner
            low_seed = races_in_round + 1 - high_seed
            high_seed_race = KnockoutRace(
                theoretical_seed_winner=high_seed,
                winner_next_race=nextRound.races[r//2]
            )
            races.append(high_seed_race)
            low_seed_race = KnockoutRace(
                theoretical_seed_winner=low_seed,
                winner_next_race=nextRound.races[r//2]
            )
            races.append(low_seed_race)

        return KnockoutRound(nextRound.round-1, RoundType.WINNERS, races)

    for i in range(rounds-1):
        event.append(make_round(event[i]))

    return event


# def generate_seed_order(unsorted: List[data.Car]) -> List[data.Car | None]:
#     """Takes a list of cars and re-orders them to be ready for pairing in the first round.

#     Args:
#         unsorted (List[data.Car]): The unsorted list of cars.

#     Returns:
#         List[data.Car | None]: List of cars, ready for the first round. Cars with a None as the next element are awarded a bye.
#     """
#     sorted_cars = sorted(
#         unsorted,
#         key=lambda c: c.points if c.points is not None else NO_SEED,
#         reverse=True,
#     )
#     # Calculate the minimum draw size. This must be a power of 2.
#     min_draw_size = int(2 ** np.ceil(np.log2(len(unsorted))))

#     # Create race pairs with the highest and lowest seeds paired.
#     # races: List[None | KnockoutRace] = [None] * (min_draw_size // 2)
#     race_cars: List[data.Car | None] = [None] * min_draw_size

#     def is_bye_needed(races_filled: int) -> bool:
#         """Determines if a bye is needed to get the required number of races."""
#         byes = min_draw_size - len(unsorted)
#         return races_filled < byes

#     def add_race_at_index(index: int, bye: bool) -> None:
#         """Places the current highest and lowest seeds in the car list at the given race index."""
#         high_seed = sorted_cars.pop()
#         low_seed = None
#         if not bye:
#             # Make a bye whenever we have an uneven number of cars.
#             low_seed = sorted_cars.pop(0)

#         race_cars[2 * index] = high_seed
#         race_cars[2 * index + 1] = low_seed

#     division_queue = [(0, len(race_cars) // 2 - 1)]
#     for races_filled in range(0, len(race_cars) // 2, 2):
#         min_race, max_race = division_queue.pop(0)

#         # Add a race with the highest and lowest seeds paired at each end.
#         add_race_at_index(min_race, is_bye_needed(races_filled))
#         add_race_at_index(max_race, is_bye_needed(races_filled + 1))

#         # Split the field in 2.
#         upper_div = (min_race + 1, max_race // 2)
#         lower_div = (max_race // 2+1, max_race - 1)
#         division_queue.append(upper_div)
#         division_queue.append(lower_div)

#     assert is_power_of_2(len(race_cars)), "The generated list of cars and byes must be a power of 2."
#     return race_cars


# class InitialKnockoutRound(KnockoutRound):
#     def __init__(self, cars: List[data.Car | None], race_offset=0, round=0) -> None:
#         """Initialises the knockout event with a list of cars."""
#         races = []
#         for i in range(0, len(cars), 2):
#             races.append(KnockoutRace(
#                 race=race_offset+i//2,
#                 round=round,
#                 car_lane_1=cars[i],
#                 car_lane_2=cars[i+1]
#             ))

#         super().__init__(0, RoundType.INITIAL, cast(List[KnockoutRace], races))


# class SubsequentRound(KnockoutRound):
#     """Represents subsequent rounds."""
#     def __init__(
#         self,
#         round: int,
#         index_start: int,
#         previous_round: KnockoutRound,
#         round_type: RoundType,
#     ) -> None:
#         # Create a new list of races and link the races from the previous round to this.
#         races: List[KnockoutRace] = []
#         for race in range(len(previous_round.races) // 2):
#             # Create the new round.
#             this_race = KnockoutRace(
#                 race + index_start,
#                 round=round,
#             )
#             races.append(this_race)

#             # Link the precessing round to this one.
#             match round_type:
#                 case RoundType.WINNERS:
#                     previous_round.races[2 * race]._winner_next_race = this_race
#                     previous_round.races[2 * race + 1]._winner_next_race = this_race
#                 case RoundType.LOSERS:
#                     previous_round.races[2 * race]._loser_next_race = this_race
#                     previous_round.races[2 * race + 1]._loser_next_race = this_race

#         super().__init__(round, round_type, races)


class KnockoutEvent:
    """Class for managing a knockout event."""

    def __init__(self, cars: List[data.Car]) -> None:
        # seeded_cars = generate_seed_order(cars)
        # rounds: List[KnockoutRound] = [InitialKnockoutRound(seeded_cars)]
        # round_number = 1
        # races = len(rounds[-1])
        # while len(rounds[-1]) > 1:
        #     rounds.append(
        #         SubsequentRound(round_number, races, rounds[-1], RoundType.WINNERS)
        #     )
        #     round_number += 1
        #     races += len(rounds[-1])
        print(generate_tree(cars))
