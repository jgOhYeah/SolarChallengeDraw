"""Represents the knockout competition."""

from __future__ import annotations
from abc import ABC
from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable, List, Tuple, cast
import numpy as np
from car import Car
from abc import ABC, abstractmethod


class Winnable(ABC):
    @abstractmethod
    def update_from_prev_race(self, prev_race: Race, competitor: Car | None) -> None:
        """Updates the competitors / result of this event based on the previous race.

        Args:
            prev_race (Race): The previous race that impacts this one.
            competitor (Car | None): The car (or no car) that feeds into this race.
        """
        pass


class Podium(Winnable):
    """Class for a placing in the tournament."""

    def __init__(self, position: int) -> None:
        self.position = position
        self.car: Car | None = None

    def update_from_prev_race(self, prev_race: Race, competitor: Car | None) -> None:
        self.car = competitor

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


class Race(Winnable):
    """Class that represents a knockout race."""

    def __init__(
        self,
        left_seed: int,
        right_seed: int,
        left_prev_race: Race | None = None,
        right_prev_race: Race | None = None,
        winner_next_race: Race | Podium | None = None,
        loser_next_race: Race | Podium | None = None,
    ):
        self.left_seed = left_seed
        self.right_seed = right_seed
        self.left_prev_race = left_prev_race
        self.right_prev_race = right_prev_race
        self.winner_next_race: Race | Podium | None = winner_next_race
        self.loser_next_race: Race | Podium | None = loser_next_race
        self.left_car: Car | None = None
        self.right_car: Car | None = None
        self.race_number: int = 0

    def theoretical_winner(self) -> int:
        return min(self.left_seed, self.right_seed)

    def theoretical_loser(self) -> int:
        return max(self.left_seed, self.right_seed)

    def has_competitors(self) -> bool:
        """Returns true if there is at least one car specified for the race.

        Returns:
            bool: If at least one can is specified.
        """
        return self.left_car is not None or self.right_car is not None

    def is_bye(self) -> bool:
        """Checks if there is only a single competitor specified, makng the race a bye.

        Returns:
            bool: True when the race is a bye.
        """
        # return self.has_competitors() and (
        #     self.left_car is None or self.right_car is None
        # ) # TODO: Fix bye detection in first round without compromising next rounds.
        return self.left_prev_race is None and self.right_prev_race is not None or self.left_prev_race is not None and self.right_prev_race is None

    def bye_winner(self) -> Car:
        assert self.is_bye(), "This race must be a bye to call this method."
        return cast(Car, self.left_car if self.left_car is not None else self.right_car)

    WINNER_EMPTY = -1
    WINNER_DNR = -2

    def get_options(self) -> None | List[Car]:
        """Returns a list of options that may win the race.

        Returns:
            None | Tuple[Car] | Tuple[Car, Car]:
                - None if the entrants are not decided yet.
                - Tuple[Car] if a single car is eligible (a bye).
                - Tuple[Car, Car] if two cars are eligible (a race).
        """
        if self.left_car is not None and self.right_car is not None:
            # Both cars (normal race with both competitors)
            return [self.left_car, self.right_car]
        elif self.left_car is not None:
            # Left car only (bye)
            return [self.left_car]
        elif self.right_car is not None:
            # Right car only (bye)
            return [self.right_car]
        else:
            # No competitors.
            return None

    def set_winner(self, car_number: int) -> None:
        """Sets the winner of the race.

        Args:
            car_number (int): The number of the car that won the race.

        Raises:
            NotImplementedError: If the race was a DNR (TODO).
            ValueError: If the car number is not part of the race.
        """
        # Default is clearing the winners and losers.
        winner = None
        loser = None
        if car_number == self.WINNER_DNR:
            # Both failed to run. # TODO: Handle
            raise NotImplementedError("DNR is not implemented yet.")
        elif self.left_car is not None and car_number == self.left_car.car_id:
            # Left car won.
            winner = self.left_car
            loser = self.right_car
        elif self.right_car is not None and car_number == self.right_car.car_id:
            # Right car won.
            winner = self.right_car
            loser = self.left_car
        elif car_number == self.WINNER_EMPTY:
            # Reset back to empty.
            pass
        else:
            # Unrecognised car.
            raise ValueError(
                f"Car {car_number} is not a known competitor in race {str(self)}."
            )

        # Propagate the result.
        if self.winner_next_race is not None:
            self.winner_next_race.update_from_prev_race(self, winner)
        if self.loser_next_race is not None:
            self.loser_next_race.update_from_prev_race(self, loser)

    def update_from_prev_race(self, prev_race: Race, competitor: Car | None) -> None:
        """Sets a competitor of a current race based on updating the previous race.

        Args:
            prev_race (Race): The previous race.
            competitor (Car | None): The winner of the previous race.

        Raises:
            ValueError: If the provided previous race is not actually a previous race.
        """
        if prev_race is self.left_prev_race:
            self.left_car = competitor
        elif prev_race is self.right_prev_race:
            self.right_car = competitor
        else:
            raise ValueError(f"Race {prev_race} is not a previous race of race {self}.")

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
        left_race = Race(
            left_seed=high_seed,
            right_seed=seed_pair(high_seed),
            winner_next_race=next_round_race,
        )
        races.append(left_race)
        next_round_race.left_prev_race = left_race
        low_seed = next_round_race.theoretical_loser()
        right_race = Race(
            left_seed=low_seed,
            right_seed=seed_pair(low_seed),
            winner_next_race=next_round_race,
        )
        races.append(right_race)
        next_round_race.right_prev_race = right_race

    return races


def create_empty_draw(competitors: int) -> List[List[Race]]:
    """Creates an empty single elimination draw with optimal seeding."""
    rounds = int(np.ceil(np.log2(competitors)))
    grand_final = Race(1, 2, None)

    event: List[List[Race]] = [[grand_final]]
    for event_round in range(rounds - 2, -1, -1):
        event.append(add_round(event[-1]))

    # Flip the order so that the first round is at the start.
    event = list(reversed(event))
    return event


def print_event(event: Iterable[List[Race]]) -> None:
    for round_num, r in enumerate(event):
        print(f"{round_num:5}: {r}")


def add_first_losers(winning_round1: List[Race]) -> List[Race]:
    """Generates the first round of the loser's bracket."""
    losers_round: List[Race] = []
    for i in range(0, len(winning_round1), 2):
        race = Race(
            left_seed=winning_round1[i].theoretical_loser(),
            right_seed=winning_round1[i + 1].theoretical_loser(),
            left_prev_race=winning_round1[i],
            right_prev_race=winning_round1[i + 1],
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
            left_prev_race=winner_race,
            right_prev_race=loser_race,
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
            left_prev_race=prev_round[i],
            right_prev_race=prev_round[i + 1],
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
        losers.append(add_repecharge(winners[i], losers[-1], reverse_winners))

    return losers


def assign_cars(cars: List[Car], first_round: List[Race]) -> None:
    """Assigns cars to the first round of the draw."""
    sorted_cars: List[Car | None] = sorted(
        cars, key=lambda c: cast(Car, c).points, reverse=False
    )  # Set reverse to True to reward higher rather than lower points.
    byes = 2 * len(first_round) - len(sorted_cars)
    sorted_cars.extend([None] * byes)
    assert len(sorted_cars) == 2 * len(
        first_round
    ), "We should have introduced enough byes to obtain the required number of participents, but something went wrong."

    for race in first_round:
        race.left_car = sorted_cars[race.left_seed - 1]
        race.right_car = sorted_cars[race.right_seed - 1]


def add_grand_final(winners_final: Race, losers_final: Race) -> Race:
    """Adds a grand final and sets the podium results from winning and loosing."""
    assert (
        winners_final.loser_next_race is losers_final
    ), "The loser of the winners' final should be a contestent in the losers' final."
    grand_final = Race(
        winners_final.theoretical_winner(),
        losers_final.theoretical_winner(),
        left_prev_race=winners_final,
        right_prev_race=losers_final,
        winner_next_race=Podium(1),
        loser_next_race=Podium(2),
    )

    # Link to the grand final.
    assert (
        winners_final.winner_next_race is None
    ), "Should not have a grand final for the winners already."
    winners_final.winner_next_race = grand_final
    assert (
        losers_final.winner_next_race is None
    ), "Should not have a grand final for the losers already."
    losers_final.winner_next_race = grand_final

    # Set the 3rd place podium.
    assert (
        losers_final.loser_next_race is None
    ), "Loser should be removed and not have a next race."
    losers_final.loser_next_race = Podium(3)

    return grand_final


def number_races_in_round(races: List[Race], start: int) -> int:
    """Adds the race number to each race in a round.

    Args:
        races (List[Race]): The races to annotate.
        start (int): The number to assign to the first race.

    Returns:
        int: The number after the last race.
    """
    for i, race in enumerate(races):
        race.race_number = i + start

    return len(races) + start


class RoundType(StrEnum):
    """Enumerator that represents the type of a round."""

    WINNERS = "P"  # P for primary knockout.
    LOSERS = "SC"  # SC for secondary knockout.
    GRAND_FINAL = "Grand final"


@dataclass
class RoundId:
    """Class that identifies a round."""

    round_type: RoundType
    round_index: int | None = None

    def __repr__(self) -> str:
        if self.round_index is not None:
            return f"{self.round_type.value}{self.round_index+1}"
        else:
            return self.round_type.value

    def __str__(self) -> str:
        return repr(self)


class KnockoutEvent:
    """A class that contains all races for the knockout event."""

    def __init__(self, cars: List[Car], name: str) -> None:
        self.winners_bracket = create_empty_draw(len(cars))
        assign_cars(cars, self.winners_bracket[0])
        self.losers_bracket = create_loosers_draw(self.winners_bracket)
        self.name = name
        assert (
            len(self.winners_bracket[-1]) == 1
        ), "Should only be one race in the last round."
        assert (
            len(self.losers_bracket[-1]) == 1
        ), "Should only be one race in the last round."
        self.grand_final = add_grand_final(
            self.winners_bracket[-1][0], self.losers_bracket[-1][0]
        )
        self._number_races()

    def calculate_play_order(self) -> List[RoundId]:
        """Determines the order that the event should be played.
        An example ordering for a 32 car draw is:
        P1, SC1, P2, SC2, SC3, P3, SC4, SC5, P4, SC6, SC7, P5, SC8, GF

        This ordering aims to keep the winners and loosers brackets somewhat in
        sync as there is approximately double the losers' rounds than winners'.

        Returns:
            List[RoundId]: The play order of the event.
        """
        # Initial winners and losers rounds.
        play_order: List[RoundId] = [
            RoundId(RoundType.WINNERS, 0),
            RoundId(RoundType.LOSERS, 0),
        ]

        # Patterns of 1 winners' round followed by 2 losers' rounds to keep them somewhat in sync.
        for winners_index in range(1, len(self.winners_bracket)):
            play_order.append(RoundId(RoundType.WINNERS, winners_index))
            play_order.append(RoundId(RoundType.LOSERS, 2 * winners_index - 1))
            if len(self.losers_bracket) > 2 * winners_index:
                # The last pattern won't have 2 losers rounds back to back.
                play_order.append(RoundId(RoundType.LOSERS, 2 * winners_index))

        # Add the grand final and check the process worked correctly.
        play_order.append(RoundId(RoundType.GRAND_FINAL))
        assert (
            len(play_order) == len(self.winners_bracket) + len(self.losers_bracket) + 1
        ), "Incorrect number of rounds in the play order."
        return play_order

    def _number_races(self) -> None:
        # Assigns a number to each race, based on the play order.
        play_order = self.calculate_play_order()
        start_number = 1
        for round_id in play_order:
            start_number = number_races_in_round(self.get_round(round_id), start_number)

    def get_round(self, id: RoundId) -> List[Race]:
        """Gets the round corresponding to a given RoundId object.

        Args:
            id (RoundId): The id to search for.

        Raises:
            KeyError: If the round could not be found.
        Returns:
            List[Race]: The corresponding round.
        """

        def check_length(bracket: List[List[Race]]) -> List[Race]:
            if id.round_index is None or id.round_index >= len(bracket):
                raise KeyError(f"Round {str(id)} could not be found in this event.")
            else:
                return bracket[id.round_index]

        match id.round_type:
            case RoundType.WINNERS:
                return check_length(self.winners_bracket)
            case RoundType.LOSERS:
                return check_length(self.losers_bracket)

            case RoundType.GRAND_FINAL:
                return [self.grand_final]

    def print(self) -> None:
        """Prints the event to the terminal."""
        print("Winners:")
        print_event(self.winners_bracket)
        print()
        print("Losers:")
        print_event(self.losers_bracket)
        print()
        print("Grand final")
        print(repr(self.grand_final))
        print("Event order:")
        print(self.calculate_play_order())
