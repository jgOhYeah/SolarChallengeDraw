"""Represents the knockout competition."""

from __future__ import annotations
from abc import ABC
from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterable, List, cast
import numpy as np
from car import Car


class Podium:
    """Class for a placing in the tournament."""

    def __init__(self, position: int) -> None:
        self.position = position

    def __str__(self) -> str:
        last_digit = self.position % 10
        match last_digit:
            case 1:
                suffix = "st"
            case 2:
                suffix = "nd"
            case 3:
                suffix = "rd"
            case _:
                suffix = "th"

        return f"{self.position}{suffix} place"


class Race:
    """Class that represents a knockout race."""
    def __init__(
        self,
        left_seed: int,
        right_seed: int,
        winner_next_race: Race | Podium | None = None,
        loser_next_race: Race | Podium | None = None,
    ):
        self.left_seed = left_seed
        self.right_seed = right_seed
        self.winner_next_race: Race | Podium | None = winner_next_race
        self.loser_next_race: Race | Podium | None = loser_next_race
        self.left_car: Car | None = None
        self.right_car: Car | None = None

    def theoretical_winner(self) -> int:
        return min(self.left_seed, self.right_seed)

    def theoretical_loser(self) -> int:
        return max(self.left_seed, self.right_seed)

    def __repr__(self) -> str:
        def car_none_str(car_none: Car | None):
            """Calls repr if this is a car, puts a placeholder in otherwise."""
            if car_none is None:
                return "<___, __>"
            else:
                return repr(car_none)

        return f"({self.left_seed:>2d} {car_none_str(self.left_car)}, {self.right_seed:>2d} {car_none_str(self.right_car)})"

def add_round(next_round: List[Race]) -> List[Race]:
    """Adds a normal round where the number of competitors are halved."""
    races = []
    competitors_in_round = 4 * len(next_round)

    def seed_pair(seed: int) -> int:
        """Returns the pair of a seed.
        (The worst opponent for the current rank).
        The sum of the pair should add to the number of competitors in the round + 1."""
        return competitors_in_round + 1 - seed

    for next_round_race in next_round:
        high_seed = next_round_race.theoretical_winner()
        races.append(
            Race(
                left_seed=high_seed,
                right_seed=seed_pair(high_seed),
                winner_next_race=next_round_race,
            )
        )
        low_seed = next_round_race.theoretical_loser()
        races.append(
            Race(
                left_seed=low_seed,
                right_seed=seed_pair(low_seed),
                winner_next_race=next_round_race,
            )
        )

    return races

def create_empty_draw(competitors:int) -> List[List[Race]]:
    """Creates an empty single elimination draw with optimal seeding."""
    rounds = int(np.ceil(np.log2(competitors)))
    grand_final = Race(1, 2, None)

    event: List[List[Race]] = [[grand_final]]
    for event_round in range(rounds - 2, -1, -1):
        event.append(add_round(event[-1]))

    # Flip the order so that the first round is at the start.
    event = list(reversed(event))
    return event

def print_event(event:Iterable[List[Race]]) -> None:
    for round_num, r in enumerate(event):
        print(f"{round_num:5}: {r}")

def add_first_losers(winning_round1: List[Race]) -> List[Race]:
    """Generates the first round of the loser's bracket."""
    losers_round: List[Race] = []
    for i in range(0, len(winning_round1), 2):
        race = Race(
            left_seed=winning_round1[i].theoretical_loser(),
            right_seed=winning_round1[i + 1].theoretical_loser(),
        )
        winning_round1[i].loser_next_race = race
        winning_round1[i + 1].loser_next_race = race
        losers_round.append(race)

    return losers_round


def add_repecharge(
    winners_round: List[Race], losers_round: List[Race], reverse_winners: bool
) -> List[Race]:
    """Adds a round where the losers of the winner's round compete with those already in the losers' bracket.
    reverse_winners allows the order of the winners to be reversed to avoid repeat races for as long as possible.
    """
    assert len(winners_round) == len(
        losers_round
    ), "The lengths of the winner's and loser's rounds must be equal."

    # Reverse the winning bracket if needed.
    if reverse_winners:
        ordered_winners = reversed(winners_round)
    else:
        ordered_winners = winners_round

    # Pair the rounds into races.
    round: List[Race] = []
    for winner_race, loser_race in zip(ordered_winners, losers_round):
        race = Race(
            left_seed=winner_race.theoretical_loser(),
            right_seed=loser_race.theoretical_winner(),
        )
        winner_race.loser_next_race = race
        loser_race.winner_next_race = race
        round.append(race)

    return round


def forward_knockout(prev_round: List[Race]) -> List[Race]:
    """Creates the next round from the previous."""
    races: List[Race] = []
    for i in range(0, len(prev_round), 2):
        # For each pair of races in the previous round, consolidate.
        race = Race(
            left_seed=prev_round[i].theoretical_winner(),
            right_seed=prev_round[i + 1].theoretical_winner(),
        )
        prev_round[i].winner_next_race = race
        prev_round[i + 1].winner_next_race = race
        races.append(race)

    return races


def create_loosers_draw(winners: List[List[Race]]) -> List[List[Race]]:
    """Creates the loosers' round of a double elimination tournament from a single elimination tournament.
    This also links the losers from the winning bracket to the correct spots in the single.
    """
    # Add the initial round and repecharge.
    first_round = add_first_losers(winners[0])
    losers: List[List[Race]] = [
        first_round,
        add_repecharge(winners[1], first_round, False),
    ]
    for i in range(2, len(winners)):
        # Round with losers other than the initial winners' round, add 2 losers' rounds.
        # Decrease in number.
        losers.append(forward_knockout(losers[-1]))
        
        # Add the repecharge.
        reverse_winners = bool(i & 0x1)
        losers.append(
            add_repecharge(winners[i], losers[-1], reverse_winners)
        )

    return losers

def assign_cars(cars:List[Car], first_round:List[Race]) -> None:
    """Assigns cars to the first round of the draw."""
    sorted_cars: List[Car|None] = sorted(cars, key=lambda c: cast(Car,c).points, reverse=False) # Set reverse to True to reward higher rather than lower points.
    byes = 2*len(first_round) - len(sorted_cars)
    sorted_cars.extend([None] * byes)
    assert len(sorted_cars) == 2*len(first_round), "We should have introduced enough byes to obtain the required number of participents, but something went wrong."

    for race in first_round:
        race.left_car = sorted_cars[race.left_seed-1]
        race.right_car = sorted_cars[race.right_seed-1]

def add_grand_final(winners_final: Race, losers_final: Race) -> Race:
    """Adds a grand final and sets the podium results from winning and loosing."""
    assert winners_final.loser_next_race is losers_final, "The loser of the winners' final should be a contestent in the losers' final."
    grand_final = Race(
        winners_final.theoretical_winner(),
        losers_final.theoretical_winner(),
        winner_next_race=Podium(1),
        loser_next_race=Podium(2)
    )

    # Link to the grand final.
    assert winners_final.winner_next_race is None, "Should not have a grand final for the winners already."
    winners_final.winner_next_race = grand_final
    assert losers_final.winner_next_race is None, "Should not have a grand final for the losers already."
    losers_final.winner_next_race = grand_final

    # Set the 3rd place podium.
    assert losers_final.loser_next_race is None, "Loser should be removed and not have a next race."
    losers_final.loser_next_race = Podium(3)

    return grand_final

class KnockoutEvent:
    """A class that contains all races for the knockout event."""
    def __init__(self, cars: List[Car]) -> None:
        self.winners_bracket = create_empty_draw(len(cars))
        assign_cars(cars, self.winners_bracket[0])
        self.losers_bracket = create_loosers_draw(self.winners_bracket)

        assert len(self.winners_bracket[-1]) == 1, "Should only be one race in the last round."
        assert len(self.losers_bracket[-1]) == 1, "Should only be one race in the last round."
        self.grand_final = add_grand_final(self.winners_bracket[-1][0], self.losers_bracket[-1][0])

    def print(self) -> None:
        print("Winners:")
        print_event(self.winners_bracket)
        print()
        print("Losers:")
        print_event(self.losers_bracket)
        print()
        print("Grand final")
        print(repr(self.grand_final))