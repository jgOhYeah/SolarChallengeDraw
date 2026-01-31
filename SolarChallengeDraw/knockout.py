"""knockout.py
Represents the knockout competition.
Written by Jotham Gates, 21/10/2025"""

from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Dict, Iterable, List, Sequence, Tuple, cast
import numpy as np

from car import Car
from knockout_race import (
    FillProbability,
    LoadingPodium,
    LoadingRace,
    Race,
    RaceBranch,
    BranchType,
    Podium,
    Winnable,
)


def add_round(next_round: List[Race]) -> List[Race]:
    """Adds a normal round where the number of competitors are halved in the winners' bracket.
    This works backwards and generates the current round given the next round."""
    races = []
    competitors_in_round = 4 * len(next_round)

    def seed_pair(seed: int) -> int:
        """Returns the pair of a seed.
        (The worst opponent for the current rank).
        The sum of the pair should add to the number of competitors in the round + 1."""
        return competitors_in_round + 1 - seed

    for next_round_race in next_round:
        # Race that determines the left competitor in the next round.
        high_seed = next_round_race.theoretical_winner().seed
        left_race = Race(
            left_branch=RaceBranch(
                seed=high_seed, branch_type=BranchType.DEPENDENT_EDITABLE
            ),
            right_branch=RaceBranch(
                seed=seed_pair(high_seed),
                branch_type=BranchType.DEPENDENT_EDITABLE,
            ),
            winner_next_race=next_round_race,
        )
        races.append(left_race)
        next_round_race.left_branch.prev_race = left_race

        # Race that determines the right competitor in the next round.
        low_seed = next_round_race.theoretical_loser().seed
        right_race = Race(
            left_branch=RaceBranch(
                seed=low_seed,
                branch_type=BranchType.DEPENDENT_EDITABLE,
            ),
            right_branch=RaceBranch(
                seed=seed_pair(low_seed),
                branch_type=BranchType.DEPENDENT_EDITABLE,
            ),
            winner_next_race=next_round_race,
        )
        races.append(right_race)
        next_round_race.right_branch.prev_race = right_race

    return races


def create_empty_draw(competitors: int) -> List[List[Race]]:
    """Creates an empty single elimination draw with optimal seeding."""
    rounds = int(np.ceil(np.log2(competitors)))
    single_elim_final = Race(
        left_branch=RaceBranch(seed=1, branch_type=BranchType.DEPENDENT_EDITABLE),
        right_branch=RaceBranch(
            seed=2,
            branch_type=BranchType.DEPENDENT_EDITABLE,
        ),
    )

    event: List[List[Race]] = [[single_elim_final]]
    for event_round in range(rounds - 2, -1, -1):
        event.append(add_round(event[-1]))

    # Flip the order so that the first round is at the start.
    event = list(reversed(event))
    return event


def print_bracket(event: Iterable[List[Race]]) -> None:
    for round_num, r in enumerate(event):
        print(f"{round_num:5}: {r}")


def add_first_losers(winning_round1: List[Race]) -> List[Race]:
    """Generates the first round of the loser's bracket."""
    losers_round: List[Race] = []
    for i in range(0, len(winning_round1), 2):
        race = Race(
            left_branch=RaceBranch(
                seed=winning_round1[i].theoretical_loser().seed,
                branch_type=BranchType.DEPENDENT_NOT_EDITABLE,
                prev_race=winning_round1[i],
            ),
            right_branch=RaceBranch(
                seed=winning_round1[i + 1].theoretical_loser().seed,
                branch_type=BranchType.DEPENDENT_NOT_EDITABLE,
                prev_race=winning_round1[i + 1],
            ),
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
            left_branch=RaceBranch(
                seed=winner_race.theoretical_loser().seed,
                branch_type=BranchType.DEPENDENT_NOT_EDITABLE,
                prev_race=winner_race,
            ),
            right_branch=RaceBranch(
                seed=loser_race.theoretical_winner().seed,
                branch_type=BranchType.DEPENDENT_EDITABLE,
                prev_race=loser_race,
            ),
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
            left_branch=RaceBranch(
                seed=prev_round[i].theoretical_winner().seed,
                branch_type=BranchType.DEPENDENT_EDITABLE,
                prev_race=prev_round[i],
            ),
            right_branch=RaceBranch(
                seed=prev_round[i + 1].theoretical_winner().seed,
                branch_type=BranchType.DEPENDENT_EDITABLE,
                prev_race=prev_round[i + 1],
            ),
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
        reverse_winners = not bool(i & 0x1)
        losers.append(add_repecharge(winners[i], losers[-1], reverse_winners))

    return losers


def randomise_cars(cars: List[Car]) -> List[Car]:
    """Randomises the cars."""
    rng = np.random.default_rng()
    order = rng.permutation(len(cars))
    return [cars[i] for i in order]


def assign_cars(cars: List[Car], first_round: List[Race], reverse: bool = True) -> None:
    """Assigns cars to the first round of the draw."""
    sorted_cars: List[Car | None] = sorted(
        cars, key=lambda c: cast(Car, c).points, reverse=True
    )  # Set reverse to True to reward higher rather than lower points.
    byes = 2 * len(first_round) - len(sorted_cars)
    sorted_cars.extend([None] * byes)
    assert len(sorted_cars) == 2 * len(
        first_round
    ), "We should have introduced enough byes to obtain the required number of participents, but something went wrong."

    for race in first_round:
        race.left_branch.car = sorted_cars[race.left_branch.seed - 1]
        race.left_branch.branch_type = BranchType.FIXED
        race.left_branch.filled = True
        race.right_branch.car = sorted_cars[race.right_branch.seed - 1]
        race.right_branch.branch_type = BranchType.FIXED
        race.right_branch.filled = True


def add_grand_final(
    winners_final: Race, losers_final: Race, losers_final_repecharge: Race
) -> Tuple[Race, List[Podium]]:
    """Adds a grand final and sets the podium results from winning and loosing."""
    assert (
        winners_final.loser_next_race is losers_final
    ), "The loser of the winners' final should be a contestent in the losers' final."
    podiums = [Podium(i) for i in range(1, 5)]
    grand_final = Race(
        left_branch=RaceBranch(
            seed=winners_final.theoretical_winner().seed,
            branch_type=BranchType.DEPENDENT_EDITABLE,
            prev_race=winners_final,
        ),
        right_branch=RaceBranch(
            seed=losers_final.theoretical_winner().seed,
            branch_type=BranchType.DEPENDENT_EDITABLE,
            prev_race=losers_final,
        ),
        winner_next_race=podiums[0],
        loser_next_race=podiums[1],
    )
    cast(Podium, grand_final.winner_next_race).branch.prev_race = grand_final
    cast(Podium, grand_final.loser_next_race).branch.prev_race = grand_final

    # Link to the grand final.
    assert (
        winners_final.winner_next_race is None
    ), "Should not have a grand final for the winners already."
    winners_final.winner_next_race = grand_final
    assert (
        losers_final.winner_next_race is None
    ), "Should not have a grand final for the losers already."
    losers_final.winner_next_race = grand_final

    # Set the 3rd and 4th place podiums.
    assert (
        losers_final.loser_next_race is None
    ), "Loser should be removed and not have a next race."

    def assign_podium_to_loser(race: Race, podium: Podium):
        race.loser_next_race = podium
        race.loser_next_race.branch.prev_race = race

    assign_podium_to_loser(losers_final, podiums[2])
    assign_podium_to_loser(losers_final_repecharge, podiums[3])

    cast(Podium, losers_final.loser_next_race).branch.prev_race = losers_final

    return grand_final, podiums


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
    LOSERS = "SC"  # SC for secondary knockout.,
    AUXILLIARY = "Auxilliary"
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


class AuxilliaryRaceManager:
    """Class that manages axilliary races."""

    def __init__(self, races: List[Race]) -> None:
        self.races = races

    @classmethod
    def create_empty(cls, max_races: int) -> AuxilliaryRaceManager:
        """Initialises the race manager with a given number of races.

        Args:
            max_races (int): The number of races.
        """
        races = [
            Race(
                left_branch=RaceBranch(-1, BranchType.DEPENDENT_NOT_EDITABLE),
                right_branch=RaceBranch(-1, BranchType.DEPENDENT_NOT_EDITABLE),
                is_auxilliary_race=True,
                race_number=i,
            )
            for i in range(max_races)
        ]
        return AuxilliaryRaceManager(races)

    def _get_first_free(self) -> Race:
        """Returns the first unused auxilliary race.

        Raises:
            LookupError: If there are no spare races.

        Returns:
            Race: The race.
        """
        for race in self.races:
            if (
                race.left_branch.prev_race is None
                and race.right_branch.prev_race is None
            ):
                return race

        raise LookupError("No spare auxilliary races found.")

    def add_race(self, prev_race: Race) -> Race:
        """Adds an auxilliary race in between a provided race and the next losers' race.

        Args:
            prev_race (Race): The race to insert.

        Returns:
            Race: The auxilliary race added.
        """
        assert (
            prev_race.get_expected_competitors(FillProbability.UNLIKELY) == 2
        ), "This function needs to be called on a race with 2 competitors that did not run."
        aux_race = self._get_first_free()
        self._insert(prev_race, aux_race)
        return aux_race

    @classmethod
    def _insert(cls, prev_race: Race, aux_race: Race) -> None:
        """Inserts the auxilliary race in between the loser of the provided race
        and the loser next race.

        Args:
            prev_race (Race): The previous race to insert afterwards.
            aux_race (Race): The auxilliary race to add in.
        """
        # Get the next race and make it point back to the auxilliary race.
        next_race = prev_race.loser_next_race
        assert (
            next_race is not None
        ), "We need a next race / podium to be able to insert an auxilliary race."
        next_race_branches = next_race.get_branches(prev_race)
        assert len(next_race_branches) == 1, "There should only be a single branch."
        next_race_branch = next_race_branches[0]
        next_race_branch.prev_race = aux_race

        # Make the auxilliary race point to the next race.
        aux_race.winner_next_race = next_race

        # Set each branch of the auxilliary race to point to the previous race.
        def set_branch(aux_branch: RaceBranch, prev_branch: RaceBranch) -> None:
            aux_branch.prev_race = prev_race
            aux_branch.car = prev_branch.car
            aux_branch.filled = prev_branch.filled

        set_branch(aux_race.left_branch, prev_race.right_branch)
        set_branch(aux_race.right_branch, prev_race.left_branch)

        # Point forwards from the previous race to the auxilliary race.
        prev_race.loser_next_race = aux_race

    def _remove(self, prev_race: Race) -> None:
        """Removes the auxilliary race from the previous one.

        Args:
            prev_race (Race): The previous race.
        """
        # Get the auxilliary race and check it is ok to remove it.
        aux_race = prev_race.loser_next_race
        assert (
            aux_race is not None and aux_race in self.races
        ), "The previous race must point to an auxilliary race."
        assert (
            not aux_race.is_result_decided()
        ), "It is not reasonable to remove an auxilliary race if the result is decided."

        # Get the next race and make it point back to the previous race.
        next_race = aux_race.winner_next_race
        assert next_race is not None, "The auxilliary race must point to a race."
        next_race_branches = next_race.get_branches(aux_race)
        assert len(next_race_branches) == 1, "There should only be a single branch."
        next_race_branch = next_race_branches[0]
        next_race_branch.prev_race = prev_race

        # Make the auxilliary race point to nothing.
        aux_race.winner_next_race = None

        def set_branch(aux_branch: RaceBranch) -> None:
            aux_branch.prev_race = None
            aux_branch.car = None
            aux_branch.filled = False

        set_branch(aux_race.left_branch)
        set_branch(aux_race.right_branch)

        # Point forwards from the previous race to the next race.
        prev_race.loser_next_race = next_race

    def free_race(self, prev_race: Race) -> None:
        print(f"Freeing aux. race {prev_race.loser_next_race} from {prev_race}")
        self._remove(prev_race)
        # TODO: Reorganise / shuffle.

    class Fields(StrEnum):
        """Fields that represent the auxilliary race manager."""

        RACES = "Races"

    def to_dict(self) -> Dict[AuxilliaryRaceManager.Fields, Any]:
        return {self.Fields.RACES: [r.to_dict() for r in self.races]}


class KnockoutEvent:
    """A class that contains all races for the knockout event."""

    def __init__(
        self,
        winners_bracket: List[List[Race]],
        losers_bracket: List[List[Race]],
        grand_final: Race,
        podiums: List[Podium],
        auxilliary_races: AuxilliaryRaceManager,
        name: str,
    ) -> None:
        self.winners_bracket = winners_bracket
        self.losers_bracket = losers_bracket
        self.grand_final = grand_final
        self.podiums = podiums
        self.auxilliary_races = auxilliary_races
        self.name = name

    @classmethod
    def new_from_cars(
        cls, cars: List[Car], name: str, max_auxilliary_races: int
    ) -> KnockoutEvent:
        """Creates a new, relatively empty knockout event from a list of cars alone.

        Args:
            cars (List[Car]): The cars to use to create the event.
            name (str): The name of the event.
            max_auxilliary_races (int): The maximum number of auxilliary races to allow.

        Returns:
            KnockoutEvent: The knockout event that has been created.
        """
        winners_bracket = create_empty_draw(len(cars))
        assign_cars(cars, winners_bracket[0])
        losers_bracket = create_loosers_draw(winners_bracket)
        assert (
            len(winners_bracket[-1]) == 1
        ), "Should only be one race in the last round."
        assert (
            len(losers_bracket[-1]) == 1
        ), "Should only be one race in the last round."
        grand_final, podiums = add_grand_final(
            winners_bracket[-1][0],
            losers_bracket[-1][0],
            losers_bracket[-2][0],
        )
        auxilliary_races = AuxilliaryRaceManager.create_empty(max_auxilliary_races)
        event = KnockoutEvent(
            winners_bracket=winners_bracket,
            losers_bracket=losers_bracket,
            grand_final=grand_final,
            podiums=podiums,
            auxilliary_races=auxilliary_races,
            name=name,
        )
        event.number_races()
        return event

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

    def number_races(self) -> None:
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
            case RoundType.AUXILLIARY:
                return self.auxilliary_races.races

    def print(self) -> None:
        """Prints the event to the terminal."""
        print("Auxilliary races")
        print_bracket([self.auxilliary_races.races])
        print("Winners:")
        print_bracket(self.winners_bracket)
        print()
        print("Losers:")
        print_bracket(self.losers_bracket)
        print()
        print("Grand final")
        print(repr(self.grand_final))
        print("Event order:")
        print(self.calculate_play_order())

    class Fields(StrEnum):
        """Fields that represent the knockout event."""

        WINNERS_BRACKET = "Winners bracket"
        LOSERS_BRACKET = "Losers bracket"
        NAME = "Event name"
        GRAND_FINAL = "Grand final"
        AUX_RACES = "Aux races"
        PODIUMS = "Podiums"

    def to_dict(self) -> Dict[KnockoutEvent.Fields, Any]:
        """Dumps the knockout event to a dictionary object.

        Returns:
            Dict[KnockoutEvent.Fields, Any]: The dictionary object generated from the event.
        """

        def bracket_to_dict(
            bracket: List[List[Race]],
        ) -> List[List[Dict[Winnable.Fields, Any]]]:
            return [[race.to_dict() for race in round] for round in bracket]

        return {
            self.Fields.NAME: self.name,
            self.Fields.WINNERS_BRACKET: bracket_to_dict(self.winners_bracket),
            self.Fields.LOSERS_BRACKET: bracket_to_dict(self.losers_bracket),
            self.Fields.GRAND_FINAL: self.grand_final.to_dict(),
            self.Fields.AUX_RACES: self.auxilliary_races.to_dict(),
            self.Fields.PODIUMS: [p.to_dict() for p in self.podiums],
        }

    @classmethod
    def from_dict(
        cls, data: Dict[KnockoutEvent.Fields, Any], cars: List[Car]
    ) -> KnockoutEvent:
        """Reconstructs a KnockoutEvent object from a dictionary.

        Args:
            data (Dict[KnockoutEvent.Fields, Any]): The dictionary to load from.
            cars (List[Car]): The list of cars to look up and link to.

        Returns:
            KnockoutEvent: Knockout event created from the dictionary.
        """

        # Make cars easily searchable
        def make_cars_dict() -> Dict[int, Car]:
            """Creates a dictionary of cars to look up by number easily."""
            result: Dict[int, Car] = {}
            for car in cars:
                result[car.car_id] = car
            return result

        cars_dict = make_cars_dict()

        # Dictionary so that races can be searchable as well.
        race_dict: Dict[str, LoadingRace | LoadingPodium] = {}

        def load_bracket(field: KnockoutEvent.Fields) -> List[List[LoadingRace]]:
            """Loads a bracket from the dictionary.

            Args:
                field (KnockoutEvent.Fields): The field to select the bracket to load.

            Returns:
                List[List[LoadingRace]]: The bracket.
            """
            bracket_data: List[List[Dict[Race.Fields, Any]]] = data[field]
            bracket: List[List[LoadingRace]] = []
            for round_data in bracket_data:
                round = LoadingRace.load_round_from_dict(
                    round_data, False, race_dict
                )  # Auxilliary races are packaged in a round, but not brackets.
                bracket.append(round)

            return bracket

        # Brackets and grand final.
        winners_bracket = load_bracket(cls.Fields.WINNERS_BRACKET)
        losers_bracket = load_bracket(cls.Fields.LOSERS_BRACKET)
        grand_final = LoadingRace(data[cls.Fields.GRAND_FINAL], False)
        race_dict[grand_final.name()] = grand_final

        # Aux races
        aux_races_list = LoadingRace.load_round_from_dict(
            round_data=data[cls.Fields.AUX_RACES][AuxilliaryRaceManager.Fields.RACES],
            aux_race=True,
            race_dict=race_dict,
        )
        aux_races = AuxilliaryRaceManager(
            cast(List[Race], aux_races_list)
        )  # Using cast here as python typing is strict for list type checking and I am being lazy.

        # Load podiums
        podiums_data: List[Dict[Podium.Fields, Any]] = data[cls.Fields.PODIUMS]
        podiums = LoadingPodium.load_podiums_from_dict(
            podiums_data=podiums_data, race_dict=race_dict
        )

        # Fix all the links now everything is in memory.
        for round in winners_bracket:
            LoadingRace.fix_round_links(round, race_dict, cars_dict)
        for round in losers_bracket:
            LoadingRace.fix_round_links(round, race_dict, cars_dict)
        grand_final.fix_links(race_dict, cars_dict)
        LoadingRace.fix_round_links(aux_races_list, race_dict, cars_dict)
        LoadingPodium.fix_podiums_links(podiums, race_dict, cars_dict)

        name = data[cls.Fields.NAME]

        # We should be ready to create the event.
        return KnockoutEvent(
            winners_bracket=cast(List[List[Race]], winners_bracket), # Again being lazy when converting from child to parent.
            losers_bracket=cast(List[List[Race]], losers_bracket),
            grand_final=grand_final,
            podiums=cast(List[Podium], podiums),
            auxilliary_races=aux_races,
            name=name,
        )
