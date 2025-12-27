"""knockout_race.py
Represents each race in a knockout competition.
Written by Jotham Gates, 29/11/2025"""

from __future__ import annotations
from abc import ABC, abstractproperty
from dataclasses import dataclass
from enum import Enum, IntEnum, StrEnum, auto
from typing import Iterable, List, Literal, Tuple, cast, TYPE_CHECKING
import numpy as np
from car import Car
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    # We are in type checking mode and are allowed a circular import. This is always skipped in runtime.
    # https://stackoverflow.com/a/39757388
    from knockout import AuxilliaryRaceManager


class BranchType(Enum):
    """Represents the type of the branch and whether the value should be edited."""

    FIXED = (
        auto()
    )  # Used for the initial round where the competitors are fixed (not editable).
    DEPENDENT_EDITABLE = (
        auto()
    )  # This branch depends on a previous race and may be edited.
    DEPENDENT_NOT_EDITABLE = (
        auto()
    )  # This branch depends on a previous race, but may not be edited.


class FillProbability(IntEnum):
    """Enum that represents the probability of a branch having a competitor in it."""

    IMPOSSIBLE = auto()
    UNLIKELY = auto()
    LIKELY = auto()
    GUARANTEED = auto()
    UNKOWN = auto()


class BranchResult(Enum):
    """Represents if a branch is the result of a win or a lose from the previous race."""

    NEITHER = auto()
    WINNER = auto()
    LOSER = auto()


@dataclass
class RaceBranch:
    """Class that represents a branch (competitor) of a race."""

    seed: int
    branch_type: BranchType
    prev_race: Race | None = None
    car: Car | None = None
    filled: bool = False

    def is_editable(self, override_type_editable: bool = False) -> bool:
        """Checks if the race branch is editable.

        Args:
            override_type_editable (bool, optional): If True, treats
                BranchType.DEPENDENT_NOT_EDITABLE as if it were
                BranchType.DEPENDENT_EDITABLE. Defaults to False.

        Returns:
            bool: Whether the branch is allowed to be edited.
        """
        ok_type = self.branch_type == BranchType.DEPENDENT_EDITABLE or (
            override_type_editable
            and self.branch_type == BranchType.DEPENDENT_NOT_EDITABLE
        )
        all_competitors_available = True
        if self.prev_race is not None:
            # We need to check the previous race.
            all_competitors_available = self.prev_race.branches_filled()

        return (
            ok_type
            and not self.is_depended_on()
            and all_competitors_available
            and self.fill_probability(include_self_filled=False)
            > FillProbability.IMPOSSIBLE
        )

    def is_depended_on(self) -> bool:
        """Checks if another race has a result and depends on the current one."""

        def race_decided(race: Race | Podium | None) -> bool:
            return race is not None and race.is_result_decided()

        return self.prev_race is not None and (
            race_decided(self.prev_race.winner_next_race)
            or race_decided(self.prev_race.loser_next_race)
        )

    def branch_result(self) -> BranchResult:
        """Works out if the branch is a result of a win, loss or other condition from the previous round."""
        if (
            self.prev_race is not None
            and self.prev_race.loser_next_race is not None
            and self in self.prev_race.loser_next_race.get_branches(self.prev_race)
        ):
            return BranchResult.LOSER
        elif (
            self.prev_race is not None
            and self.prev_race.winner_next_race is not None
            and self in self.prev_race.winner_next_race.get_branches(self.prev_race)
        ):
            return BranchResult.WINNER
        else:
            return BranchResult.NEITHER

    def fill_probability(self, include_self_filled: bool = True) -> FillProbability:
        """Works out the probability that the branch has a competitor in it.

        Args:
            include_self_filled (bool, optional): Whether to include the fact
                that the branch may actually be filled (with or without a car
                rather than only relying on previous races. Defaults to True.

        Returns:
            FillProbability: The probability that the branch may be filled (or
                actually is filled if include_self_filled = True).
        """

        def car_assign_prob() -> (
            Literal[FillProbability.IMPOSSIBLE] | Literal[FillProbability.GUARANTEED]
        ):
            """The probability based on whether a car has been assigned assuming this branch is filled.

            Returns:
                Literal[FillProbability.IMPOSSIBLE] | Literal[FillProbability.GUARANTEED]: The possible extremes of probability.
            """
            if self.car is None:
                return FillProbability.IMPOSSIBLE
            else:
                return FillProbability.GUARANTEED

        if include_self_filled and self.filled:
            # Work out the probability based on whether we have been assigned a car or not.
            return car_assign_prob()
        else:
            match self.branch_result():
                case BranchResult.WINNER:
                    assert (
                        self.prev_race is not None
                    ), "The branch is the result of a win, so there should be a previous race."
                    return self.prev_race.winner_probability()
                case BranchResult.LOSER:
                    # Branch is likely to be filled if there is more than one competitor in the previous race.
                    assert (
                        self.prev_race is not None
                    ), "The branch is the result of a loss, so there should be a previous race."
                    match self.prev_race.get_expected_competitors(
                        FillProbability.LIKELY
                    ):
                        case 2:
                            # Both competitors are likely to be filled, so we will probably have a loser.
                            return FillProbability.LIKELY
                        case 1:
                            # Not likely to be filled as there aren't enough likely competitors to fill a loser.
                            return FillProbability.UNLIKELY
                        case 0:
                            # No competitors as the previous race is impossible.
                            return FillProbability.IMPOSSIBLE
                        case _:
                            raise LookupError(
                                "There shouldn't be more than 2 competitors."
                            )

                case BranchResult.NEITHER:
                    return car_assign_prob()


class Winnable(ABC):
    @abstractmethod
    def update_from_prev_race(
        self, prev_race: Race, competitor: Car | None, filled: bool
    ) -> None:
        """Updates the competitors / result of this event based on the previous race.

        Args:
            prev_race (Race): The previous race that impacts this one.
            competitor (Car | None): The car (or no car) that feeds into this race.
        """
        pass

    @abstractmethod
    def get_branches(
        self, filter_prev_race: Race | None = None
    ) -> Tuple[RaceBranch] | Tuple[RaceBranch, RaceBranch]:
        """Returns one or both branches of the race / podium.

        Args:
            filter_prev_race (Race | None, optional): An optional previous race
                to only return branches that correspond to it. Defaults to None.

        Raises:
            ValueError: If the provided previous race is not actually a previous race.

        Returns:
            Tuple[RaceBranch] | Tuple[RaceBranch, RaceBranch]: One or more branches.
        """
        pass

    def get_single_branch(self, filter_prev_race: Race) -> RaceBranch:
        """Like get_branches, but forces a previous race and returns a single branch. This will return the first branch if multiple branches have the same previous race."""
        branch = self.get_branches(filter_prev_race)
        return branch[0]

    @abstractmethod
    def get_expected_competitors(self, min_fill_probability: FillProbability) -> int:
        """Returns the number of competitors expected with at least the given fill probability. This may be 1 for a bye or podium and 2 for a race."""
        pass

    def branches_filled(
        self,
        filter_prev_race: Race | None = None,
        check_any: bool = False,
        include_impossible: bool = True,
        include_impossible_future: bool = False,
    ) -> bool:
        """Returns true if any/all branches have been specified for the race / podium.
        Each branch may be filled with either a car or None to indicate an empty spot.

        Args:
            filter_prev_race (Race | None, optional): If a previous race is provided,
                only looks in the branch corresponding to this race. This is
                useful for checking if a previous race has been descided. Defaults to
                None.
            check_any (bool, optional): If True, returns True if any competitor is
                set. If False, requires that all competitors be set. Defaults to
                False.
            include_impossible (bool, optional): If True, treats impossible to fill
                branches as filled. Defaults to True.
            include_impossible_future (bool, optional): If True, checks future races
                to check if they are filled in the case of impossible to fill branches.
                Defaults to False.
        Returns:
            bool: If the required number of competitors for the provided previous race
        """
        # Possible to add cars, we need to check each branch.
        branches = self.get_branches(filter_prev_race)
        for b in branches:
            # Automatically treat impossible fills as filled.
            impossible_fill = (
                b.prev_race is not None
                and b.prev_race.winner_probability() == FillProbability.IMPOSSIBLE
            )
            filled = b.filled or (include_impossible and impossible_fill)
            if not filled and impossible_fill and include_impossible_future:
                # Check if the branch is used in the future.
                filled = b.is_depended_on()

            if filled and check_any:
                return True

            if not filled and not check_any:
                return False

        # We got to the end and all are filled if they need to be or none are.
        return not check_any

    def winner_probability(self) -> FillProbability:
        """Returns the probability that there is a winner for the race / podium.

        The likelyhood is the maximum probability of the previous race's
        branches being filled with LIKELY as the allowed maximum due to a
        potential DNR."""
        max_probability = max([b.fill_probability() for b in self.get_branches()])
        return min(max_probability, FillProbability.LIKELY)

    @abstractmethod
    def is_result_decided(self) -> bool:
        """Checks if the result for the current race or podium is decided."""
        pass

    @abstractmethod
    def name(self) -> str:
        """Returns a short name for the race/position."""
        pass

    @property
    @abstractmethod
    def is_auxilliary_race(self) -> bool:
        """Checks if the current race / podium is an auxilliary race."""
        pass


class Podium(Winnable):
    """Class for a placing in the tournament."""

    def __init__(
        self, position: int, prev_race: Race | None = None, car: Car | None = None
    ) -> None:
        self.position = position
        self.branch: RaceBranch = RaceBranch(
            seed=position,
            branch_type=BranchType.DEPENDENT_NOT_EDITABLE,
            prev_race=prev_race,
            car=car,
        )

    def update_from_prev_race(
        self, prev_race: Race, competitor: Car | None, filled: bool
    ) -> None:
        self.branch.car = competitor
        self.branch.filled = filled

    def get_branches(
        self, filter_prev_race: Race | None = None
    ) -> Tuple[RaceBranch] | Tuple[RaceBranch]:
        if filter_prev_race is None or self.branch.prev_race is filter_prev_race:
            # We are allowed to return the branch.
            return (self.branch,)
        else:
            # Invalid previous race.
            raise ValueError("The provided previous race is not linked to this podium.")

    def get_expected_competitors(self, min_fill_probability: FillProbability) -> int:
        return 1

    def is_result_decided(self) -> bool:
        # return self.branch.car is not None
        return False  # We always need to be able to edit the input branch of a podium (avoids not being able to edit the results of the grand final).

    def name(self) -> str:
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

    @property
    def is_auxilliary_race(self) -> bool:
        return False


class Race(Winnable):
    """Class that represents a knockout race."""

    def __init__(
        self,
        left_branch: RaceBranch,
        right_branch: RaceBranch,
        winner_next_race: Race | Podium | None = None,
        loser_next_race: Race | Podium | None = None,
        is_auxilliary_race: bool = False,
        race_number: int = 0,
    ):
        self.left_branch = left_branch
        self.right_branch = right_branch
        self.winner_next_race: Race | Podium | None = winner_next_race
        self.loser_next_race: Race | Podium | None = loser_next_race
        self.race_number: int = race_number
        self._is_auxilliary_race = is_auxilliary_race

    def theoretical_winner(self) -> RaceBranch:
        """Calculates the theoretical winner based on seeding.
        Returns:
            RaceBranch: the race branch with the lowest seed.
        """
        if self.left_branch.seed < self.right_branch.seed:
            return self.left_branch
        else:
            return self.right_branch

    def theoretical_loser(self) -> RaceBranch:
        """Calculates the theoretical loser based on seeding.
        Returns:
            RaceBranch: the race branch with the highest seed.
        """
        if self.left_branch.seed > self.right_branch.seed:
            return self.left_branch
        else:
            return self.right_branch

    def get_branches(
        self, filter_prev_race: Race | None = None
    ) -> Tuple[RaceBranch] | Tuple[RaceBranch, RaceBranch]:
        """Returns one or both branches of the race.

        Args:
            filter_prev_race (Race | None, optional): _description_. Defaults to None.

        Raises:
            ValueError: If the provided previous race is not actually a previous race.

        Returns:
            Tuple[RaceBranch] | Tuple[RaceBranch, RaceBranch]: One or more branches.
        """
        if filter_prev_race is None:
            # Not filtering, everything.
            return self.left_branch, self.right_branch
        elif filter_prev_race is self.left_branch.prev_race:
            if filter_prev_race is self.right_branch.prev_race:
                # Both branches point to the same previous race (used in auxilliary races).
                return self.left_branch, self.right_branch
            else:
                # Left only.
                return (self.left_branch,)
        elif filter_prev_race is self.right_branch.prev_race:
            # Right only.
            return (self.right_branch,)
        else:
            raise ValueError("The provided previous race is not a previous race.")

    def is_bye(self) -> bool:
        """Checks if there is only a single competitor specified, makng the race a bye.

        Returns:
            bool: True when the race is a bye.
        """
        return self.get_expected_competitors(FillProbability.UNLIKELY) == 1 and (
            self.left_branch.branch_type == BranchType.FIXED
            or self.right_branch.branch_type == BranchType.FIXED
        )

    WINNER_EMPTY = -1
    WINNER_DNR = -2

    def get_options(self) -> List[Car]:
        """Returns a list of options that may win the race.

        Returns:
            List[Car]: The possible winners of the race.
        """
        if self.left_branch.car is not None and self.right_branch.car is not None:
            # Both cars (normal race with both competitors)
            return [self.left_branch.car, self.right_branch.car]
        elif self.left_branch.car is not None:
            # Left car only (bye)
            return [self.left_branch.car]
        elif self.right_branch.car is not None:
            # Right car only (bye)
            return [self.right_branch.car]
        else:
            # No competitors.
            return []

    def set_winner(
        self, car_number: int, auxilliary_manager: AuxilliaryRaceManager
    ) -> None:
        """Sets the winner of the race.

        Args:
            car_number (int): The number of the car that won the race.

        Raises:
            NotImplementedError: If the race was a DNR (TODO).
            ValueError: If the car number is not part of the race.
        """

        def optional_update(
            race: Race | Podium | None, competitor: Car | None, filled: bool
        ) -> None:
            """Updates the next race if it exists."""
            if race is not None:
                race.update_from_prev_race(self, competitor, filled)

        def add_dnr():
            # This is a DNR - (no winner).
            optional_update(self.winner_next_race, None, True)
            if (
                self.loser_next_race is not None
                and not self.loser_next_race.is_auxilliary_race
            ):
                # There is a loser's race we need to deal with.
                # We don't already have an auxilliary race in place and are allowed to add one.
                options = self.get_options()
                if len(options) == 2:
                    # We need to add an auxilliary race as we have 2 competitors vying to win the losing spot.
                    # Clear the current loser's race before adding the auxilliary race.
                    optional_update(self.loser_next_race, None, False)
                    auxilliary_manager.add_race(self)
                elif len(options) == 1:
                    # We have a single competitor. Drop then straight into the loosing spot.
                    optional_update(self.loser_next_race, options[0], True)
                else:
                    assert False, "There should only be 1 or 2 options."

        # Remove the auxilliary race if no longer a DNR.
        if (
            self.loser_next_race is not None
            and self.loser_next_race.is_auxilliary_race
            and car_number != self.WINNER_DNR
        ):
            # The race was, but is no longer a DNR.
            auxilliary_manager.free_race(self)

        # Options and actions.
        if car_number == self.WINNER_DNR:
            # Both failed to run.
            add_dnr()

        elif (
            self.left_branch.car is not None
            and car_number == self.left_branch.car.car_id
        ):
            # Left car won.
            optional_update(self.winner_next_race, self.left_branch.car, True)
            optional_update(self.loser_next_race, self.right_branch.car, True)
        elif (
            self.right_branch.car is not None
            and car_number == self.right_branch.car.car_id
        ):
            # Right car won.
            optional_update(self.winner_next_race, self.right_branch.car, True)
            optional_update(self.loser_next_race, self.left_branch.car, True)
        elif car_number == self.WINNER_EMPTY:
            # Reset back to empty.
            optional_update(self.winner_next_race, None, False)
            optional_update(self.loser_next_race, None, False)
        else:
            # Unrecognised car.
            raise ValueError(
                f"Car {car_number} is not a known competitor in race {str(self)}."
            )

    def update_from_prev_race(
        self, prev_race: Race, competitor: Car | None, filled: bool
    ) -> None:
        """Sets a competitor of a current race based on updating the previous race.

        Args:
            prev_race (Race): The previous race.
            competitor (Car | None): The winner of the previous race.

        Raises:
            ValueError: If the provided previous race is not actually a previous race.
        """
        branch = self.get_branches(prev_race)
        assert len(branch) == 1, "Should only be 1 branch returned."
        branch[0].car = competitor
        branch[0].filled = filled

    def get_expected_competitors(self, min_fill_probability: FillProbability) -> int:
        return int(self.left_branch.fill_probability() >= min_fill_probability) + int(
            self.right_branch.fill_probability() >= min_fill_probability
        )

    def is_result_decided(self) -> bool:
        """Checks if the result for the current race is decided."""

        def check_race(race: Race | Podium | None) -> bool:
            """Checks if the result of a future race have been decided."""
            if race is not None:
                return race.branches_filled(
                    self, include_impossible=False, include_impossible_future=True
                )
            else:
                # Nothing here to be decided.
                return False

        return check_race(self.winner_next_race) or check_race(self.loser_next_race)

    def __repr__(self) -> str:
        def car_none_str(car_none: Car | None):
            """Calls repr if this is a car, puts a placeholder in otherwise."""
            if car_none is None:
                return "<___, __>"
            else:
                return repr(car_none)

        return f"{self.name()}({self.left_branch.seed:>2d} {car_none_str(self.left_branch.car)}, {self.right_branch.seed:>2d} {car_none_str(self.right_branch.car)})"

    def name(self) -> str:
        prefix = "AR" if self.is_auxilliary_race else "R"
        return f"{prefix}{self.race_number}"

    @property
    def is_auxilliary_race(self) -> bool:
        return self._is_auxilliary_race
