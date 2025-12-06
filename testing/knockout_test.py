import os
import sys

import ttkbootstrap as ttk
from typing import Callable, Tuple
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../SolarChallengeDraw"))
)
from knockout_race import *
from knockout import *
from car import *
from knockout_sheet import *
from knockout_sheet_elements import *


class TestRace(unittest.TestCase):
    def test_branch_result(self):
        branch = RaceBranch(1, BranchType.DEPENDENT_EDITABLE, None, None, False)
        self.assertEqual(
            branch.branch_result(),
            BranchResult.NEITHER,
            "Branch is not the result of a previous race.",
        )

        # Create a set of races.
        left_race, right_race, winner_race, loser_race = self.create_4_races()
        self.assertEqual(
            left_race.left_branch.branch_result(),
            BranchResult.NEITHER,
            "Initial branch.",
        )
        self.assertEqual(
            left_race.right_branch.branch_result(),
            BranchResult.NEITHER,
            "Initial branch.",
        )
        self.assertEqual(
            right_race.left_branch.branch_result(),
            BranchResult.NEITHER,
            "Initial branch.",
        )
        self.assertEqual(
            right_race.right_branch.branch_result(),
            BranchResult.NEITHER,
            "Initial branch.",
        )
        self.assertEqual(
            winner_race.left_branch.branch_result(),
            BranchResult.WINNER,
            "Result is a winner.",
        )
        self.assertEqual(
            winner_race.right_branch.branch_result(),
            BranchResult.WINNER,
            "Result is a winner.",
        )
        self.assertEqual(
            loser_race.left_branch.branch_result(),
            BranchResult.LOSER,
            "Result is a loser.",
        )
        self.assertEqual(
            loser_race.right_branch.branch_result(),
            BranchResult.LOSER,
            "Result is a loser.",
        )

    def test_get_branches(self):
        races = self.create_4_races()
        # Test unfiltered.
        for r in races:
            branches = r.get_branches()
            self.assertIn(r.left_branch, branches, "Left branch, unfiltered.")
            self.assertIn(r.right_branch, branches, "Right branch, unfiltered.")
            self.assertEqual(len(branches), 2, "Number of elements in branch.")

        # Test filtered.
        left_race, right_race, winner_race, loser_race = races

        def test_filtered(search_race: Race, filter_race: Race):
            """When both branches aren't pointing to the same race, checks if a single branch is returned that points to the previous race."""
            branches = search_race.get_branches(filter_race)
            self.assertEqual(len(branches), 1, "Len of a filtered set of branches.")
            self.assertIs(
                branches[0].prev_race,
                filter_race,
                "Returned branch has the correct previous race.",
            )

        test_filtered(winner_race, left_race)
        test_filtered(winner_race, right_race)
        test_filtered(loser_race, left_race)
        test_filtered(loser_race, right_race)

        # Test where both branches of a race point back to a single race.
        prev_race = races[3]
        aux_race = Race(
            left_branch=RaceBranch(
                -1, BranchType.DEPENDENT_NOT_EDITABLE, prev_race, None, False
            ),
            right_branch=RaceBranch(
                -1, BranchType.DEPENDENT_NOT_EDITABLE, prev_race, None, False
            ),
            winner_next_race=None,
            loser_next_race=None,
            is_auxilliary_race=True,
            race_number=45,
        )
        prev_race.winner_next_race = None
        prev_race.loser_next_race = aux_race

        # Unfiltered.
        branches = aux_race.get_branches()
        self.assertEqual(
            len(branches),
            2,
            "The incorrect number of branches are returned when both branches in a race point to the previous race.",
        )
        self.assertIn(
            aux_race.left_branch,
            branches,
            "Left branch isn't in the previous race when both point to the same race.",
        )
        self.assertIn(
            aux_race.right_branch,
            branches,
            "Right branch isn't in the previous race when both point to the same race.",
        )

        # Filtered (we should expect 2 branches as both will match the filter).
        branches = aux_race.get_branches(prev_race)
        self.assertEqual(
            len(branches),
            2,
            "When filtering, there should be 2 branches returned as both point to the previous race.",
        )
        self.assertIn(
            aux_race.left_branch,
            branches,
            "Left branch isn't in the previous race when both point to the same race and filtered.",
        )
        self.assertIn(
            aux_race.right_branch,
            branches,
            "Right branch isn't in the previous race when both point to the same race and filtered.",
        )

    def test_is_bye(self):
        left_race, right_race, winner_race, loser_race = self.create_4_races_with_bye()
        self.assertTrue(left_race.is_bye(), "The left race should be a bye.")
        self.assertFalse(right_race.is_bye(), "The right race should not be a bye.")
        self.assertFalse(
            winner_race.is_bye(), "(Winner) Non-fixed races should not be byes."
        )
        self.assertFalse(
            loser_race.is_bye(), "(Loser) Non-fixed races should not be byes."
        )

    def test_is_editable(self):
        left_race, right_race, winner_race, loser_race = self.create_4_races_with_bye()
        self.assertFalse(
            left_race.left_branch.is_editable(),
            "Left race, left branch should not be editable.",
        )
        self.assertFalse(
            left_race.right_branch.is_editable(),
            "Left race, right branch should not be editable.",
        )
        self.assertFalse(
            right_race.left_branch.is_editable(),
            "Right race, left branch should not be editable.",
        )
        self.assertFalse(
            right_race.right_branch.is_editable(),
            "Right race, right branch should not be editable.",
        )
        self.assertTrue(
            winner_race.left_branch.is_editable(),
            "Winner race, left branch should be editable.",
        )
        self.assertTrue(
            winner_race.right_branch.is_editable(),
            "Winner race, right branch should be editable.",
        )
        self.assertFalse(
            loser_race.left_branch.is_editable(),
            "Loser race, left branch should not be editable.",
        )
        self.assertFalse(
            loser_race.right_branch.is_editable(),
            "Loser race, right branch should not be editable.",
        )

        next_loser_race = Race(
            left_branch=RaceBranch(3, BranchType.DEPENDENT_EDITABLE, winner_race),
            right_branch=RaceBranch(4, BranchType.DEPENDENT_EDITABLE, loser_race),
        )
        winner_race.loser_next_race = next_loser_race
        loser_race.winner_next_race = next_loser_race

        self.assertFalse(
            next_loser_race.left_branch.is_editable(),
            "This race should not be editable without cars.",
        )
        self.assertFalse(
            next_loser_race.right_branch.is_editable(),
            "This race should not be editable without cars.",
        )

        aux_race_manager = AuxilliaryRaceManager(1)

        # Add some winners.
        assert (
            left_race.left_branch.car is not None
            and right_race.left_branch.car is not None
        ), "Initial competitors incorrect."
        left_race.set_winner(left_race.left_branch.car.car_id, aux_race_manager)
        right_race.set_winner(right_race.left_branch.car.car_id, aux_race_manager)

        # Now check if editable
        self.assertTrue(
            next_loser_race.left_branch.is_editable(),
            "Result of a normal race should be editable.",
        )
        self.assertTrue(
            next_loser_race.right_branch.is_editable(),
            "Result of a bye should be editable.",
        )

    def test_has_competitors(self):
        left_race, right_race, winner_race, loser_race = self.create_4_races_with_bye()
        self.assertTrue(left_race.branches_filled(), "Initial should have competitors.")
        self.assertTrue(
            right_race.branches_filled(), "Initial should have competitors."
        )
        self.assertFalse(
            winner_race.branches_filled(), "Subsequent should not have competitors yet."
        )
        self.assertFalse(
            loser_race.branches_filled(), "Subsequent should not have competitors yet."
        )

        # Set competitors for one side of winner.
        assert left_race.left_branch.car is not None, "Testing error"
        left_race.set_winner(left_race.left_branch.car.car_id, AuxilliaryRaceManager(1))

        # Tests with a single competitor filled.
        self.assertFalse(
            winner_race.branches_filled(check_any=False),
            "Not all competitors provided.",
        )
        self.assertTrue(
            winner_race.branches_filled(check_any=True),
            "Check any with a single competitor.",
        )
        self.assertTrue(
            winner_race.branches_filled(filter_prev_race=left_race, check_any=False),
            "Filter a single race.",
        )
        self.assertFalse(
            loser_race.branches_filled(check_any=False),
            "Not all competitors provided.",
        )
        self.assertTrue(
            loser_race.branches_filled(check_any=True),
            "This should be a bye that has the empty branch marked.",
        )
        self.assertTrue(
            loser_race.branches_filled(filter_prev_race=left_race, check_any=False),
            "Filter a single race.",
        )

        # Fill the second competitor.
        assert right_race.left_branch.car is not None, "Testing error"
        right_race.set_winner(
            right_race.left_branch.car.car_id, AuxilliaryRaceManager(1)
        )

        # Tests with both competitors filled.
        self.assertTrue(
            winner_race.branches_filled(), "Both competitors should have been provided."
        )
        self.assertTrue(
            loser_race.branches_filled(),
            "The bye should have been successfully handled in the loser's race.",
        )

    def create_4_races_with_bye(self) -> Tuple[Race, Race, Race, Race]:
        left_race, right_race, winner_race, loser_race = self.create_4_races()
        cars = [Car(i, i, f"Car {i}", True, True, True) for i in range(3)]
        left_race.left_branch.car = cars[0]
        left_race.left_branch.filled = True
        left_race.right_branch.car = None
        left_race.right_branch.filled = True
        right_race.left_branch.car = cars[1]
        right_race.left_branch.filled = True
        right_race.right_branch.car = cars[2]
        right_race.right_branch.filled = True

        return left_race, right_race, winner_race, loser_race

    def create_4_races(self) -> Tuple[Race, Race, Race, Race]:
        left_race = Race(
            left_branch=RaceBranch(1, BranchType.FIXED, None, None),
            right_branch=RaceBranch(4, BranchType.FIXED, None, None),
        )
        right_race = Race(
            left_branch=RaceBranch(2, BranchType.FIXED, None, None),
            right_branch=RaceBranch(3, BranchType.FIXED, None, None),
        )
        winner_race = Race(
            left_branch=RaceBranch(1, BranchType.DEPENDENT_EDITABLE, left_race),
            right_branch=RaceBranch(2, BranchType.DEPENDENT_EDITABLE, right_race),
        )
        loser_race = Race(
            left_branch=RaceBranch(
                4, BranchType.DEPENDENT_NOT_EDITABLE, left_race, None
            ),
            right_branch=RaceBranch(
                3, BranchType.DEPENDENT_NOT_EDITABLE, right_race, None
            ),
        )
        left_race.winner_next_race = winner_race
        left_race.loser_next_race = loser_race
        right_race.winner_next_race = winner_race
        right_race.loser_next_race = loser_race
        return left_race, right_race, winner_race, loser_race


# class TestRace(unittest.TestCase):
#     def test_expected_competitors(self):
#         race = Race(
#             RaceBranch(1, BranchType.DEPENDENT_EDITABLE, prev_race=None),
#             right_branch=RaceBranch(2, BranchType.DEPENDENT_EDITABLE, prev_race=None)
#         )


def make_demo_list() -> List[Car]:
    return [
        Car(101, 1, "Flying fish", True, True, True, 1),  # Last place seed.
        Car(102, 1, "Curious cat", True, True, True, 2),
        Car(103, 1, "Hungry horse", True, True, True, 3),
        Car(104, 2, "Percy penguin", True, True, True, 3),
        Car(105, 3, "Munching mouse", True, True, True, 4),  # Second place seed.
        Car(106, 3, "Busy bee", True, True, True, 5),  # First place seed
    ]


def load_demo_list() -> List[Car]:
    return load_cars(relative_path("test_cars.csv"))


# class TestCar(unittest.TestCase):


def relative_path(filename: str) -> str:
    """Converts a filename into a path relative to the current file.

    Args:
        filename (str): The filename.

    Returns:
        str: The path relative to __file__.
    """
    return os.path.join(os.path.dirname(__file__), filename)


class TestEvent(unittest.TestCase):
    def test_create(self):
        cars = make_demo_list()
        event = KnockoutEvent(cars, "Test", 1)

        # There should be 4 races in the first round.
        self.assertEqual(
            len(event.winners_bracket[0]),
            4,
            f"There are {len(cars)} competitors so the first round should have 4 races.",
        )

        # Because there are 6 competitors, the first and second seeds should have a bye.
        self.assertTrue(
            event.winners_bracket[0][0].is_bye(),
            "The first placed seed should have a bye.",
        )
        self.assertFalse(
            event.winners_bracket[0][1].is_bye(), "The second race should not be a bye."
        )
        self.assertTrue(
            event.winners_bracket[0][2].is_bye(),
            "The second place seed should have a bye.",
        )
        self.assertFalse(
            event.winners_bracket[0][3].is_bye(), "The fourth race should not be a bye."
        )

        # Check the expected seeds are in their spots.
        self.assertEqual(
            cast(Car, event.winners_bracket[0][0].left_branch.car).car_id,
            106,
            "The first-placed seed is car 106.",
        )
        self.assertEqual(
            cast(Car, event.winners_bracket[0][2].left_branch.car).car_id,
            105,
            "The second-placed seed should be here given the current sorting rules.",
        )

    def test_load_csv(self) -> None:
        csv_cars = load_demo_list()
        list_cars = make_demo_list()
        self.assertListEqual(
            csv_cars,
            list_cars,
            "The loaded CSV file does not match the theoretically equivalent list.",
        )

    def test_randomise(self) -> None:
        cars = make_demo_list()
        randomised = randomise_cars(cars)

        self.assertCountEqual(
            cars, randomised, "The cars lists need to be the same length."
        )
        self.assertNotEqual(cars, randomised, "Randomising failed.")
        for c in cars:
            self.assertIn(c, randomised, "At least one car is not in the output.")

    def test_aux_races(self) -> None:
        """Tests if the auxilliary races are behaving correctly."""
        # Create the event.
        cars = make_demo_list()
        event = KnockoutEvent(cars, self.test_aux_races.__name__, 3)

        # Check that no auxilliary races are used.
        for a in event.auxilliary_races.races:
            self.assertTrue(
                a.left_branch.car is None and a.right_branch.car is None,
                "No auxilliary races should be allocated yet.",
            )

        # Initial checks.
        prev_race = event.winners_bracket[0][1]
        next_race = prev_race.loser_next_race
        self.assertIsInstance(
            next_race,
            Race,
            "Issue with this test, the loser's next race should be an actual one.",
        )
        next_race = cast(Race, next_race)
        self.assertEqual(
            next_race.get_single_branch(prev_race).branch_result(),
            BranchResult.LOSER,
            "The loser's next race incorrectly has the wrong result type.",
        )

        # Mark a race as DNR.
        prev_race.set_winner(Race.WINNER_DNR, event.auxilliary_races)

        # Check the auxilliary race has been created and points to the previous race.
        aux_race = event.auxilliary_races.races[0]
        self.assertIs(
            aux_race.left_branch.car,
            prev_race.right_branch.car,
            "The left car of the previous race has not been copied to the right car of the auxilliary race.",
        )
        self.assertIs(
            aux_race.left_branch.prev_race,
            prev_race,
            "The left branch of the auxilliary race does not point to the previous race.",
        )
        self.assertEqual(
            aux_race.left_branch.branch_result(),
            BranchResult.LOSER,
            "An auxilliary race should be the result of a loss (left branch).",
        )
        self.assertIs(
            aux_race.right_branch.car,
            prev_race.left_branch.car,
            "The right car of the previous race has not been copied to the left car of the auxilliary race.",
        )
        self.assertIs(
            aux_race.right_branch.prev_race,
            prev_race,
            "The right branch of the auxilliary race does not point to the previous race.",
        )
        self.assertEqual(
            aux_race.right_branch.branch_result(),
            BranchResult.LOSER,
            "An auxilliary race should be the result of a loss (right branch).",
        )

        # Check that the previous race points to the auxilliary race and has the correct results.

        # Check that the


class TestSheet(unittest.TestCase):
    GHOSTSCRIPT_PATH = "gs"
    PAGE_WIDTH = 297
    PAGE_HEIGHT = 210

    def compare_postscript(
        self, sheet1: KnockoutSheet, sheet2: KnockoutSheet
    ) -> None:
        sheet1_ps = sheet1.export(
            ghostscript_path=self.GHOSTSCRIPT_PATH,
            output="",
            pdf_width_mm=self.PAGE_WIDTH,
            pdf_height_mm=self.PAGE_HEIGHT,
            save_ps=False,
            generate_pdf=False,
            surpress_output=True,
        )
        sheet2_ps = sheet2.export(
            ghostscript_path=self.GHOSTSCRIPT_PATH,
            output="",
            pdf_width_mm=self.PAGE_WIDTH,
            pdf_height_mm=self.PAGE_HEIGHT,
            save_ps=False,
            generate_pdf=False,
            surpress_output=True,
        )
        self.compare_line_by_line(sheet1_ps, sheet2_ps)

    def compare_postscript_files(
        self, sheet1: KnockoutSheet, sheet2: KnockoutSheet
    ) -> None:
        """Exports both provided sheets as postscript and compares them line by line."""
        sheet1_filename = relative_path("sheet1.ps")
        sheet2_filename = relative_path("sheet2.ps")
        sheet1.export(
            ghostscript_path=self.GHOSTSCRIPT_PATH,
            output=sheet1_filename,
            pdf_width_mm=self.PAGE_WIDTH,
            pdf_height_mm=self.PAGE_HEIGHT,
            save_ps=True,
            generate_pdf=False,
            surpress_output=True,
        )
        sheet2.export(
            ghostscript_path=self.GHOSTSCRIPT_PATH,
            output=sheet2_filename,
            pdf_width_mm=self.PAGE_WIDTH,
            pdf_height_mm=self.PAGE_HEIGHT,
            save_ps=True,
            generate_pdf=False,
            surpress_output=True,
        )

        with open(sheet1_filename) as sheet1_ps:
            with open(relative_path(sheet2_filename)) as sheet2_ps:
                self.compare_line_by_line(sheet1_ps.readlines(), sheet2_ps.readlines())

    def compare_line_by_line(
        self, sheet1_lines: Iterable[str], sheet2_lines: Iterable[str]
    ) -> None:
        """Compares 2 iterable objects line by line."""
        for line_number, (sheet1_line, sheet2_line) in enumerate(
            zip(sheet1_lines, sheet2_lines)
        ):
            self.assertEqual(
                sheet1_line.strip(), sheet2_line.strip(), f"Line {line_number} does not match."
            )

    def event_to_sheet(self, event: KnockoutEvent) -> Tuple[KnockoutSheet, ttk.Window]:
        frame = ttk.Window()
        sheet = KnockoutSheet(frame, None, None)
        sheet.draw_canvas(event, PrintNumberBoxFactory(), False)
        return sheet, frame

    def test_postscript_write(self) -> None:
        """Compares the exported postscript saved to a file compared to the version kept in RAM."""
        sheet, frame = self.event_to_sheet(
            KnockoutEvent(make_demo_list(), self.test_postscript_write.__name__, 2)
        )
        sheet_filename = relative_path(self.test_postscript_write.__name__ + ".ps")
        list_version = sheet.export(
            self.GHOSTSCRIPT_PATH,
            sheet_filename,
            self.PAGE_WIDTH,
            self.PAGE_HEIGHT,
            True,
            False,
            True,
        )
        with open(sheet_filename, "r") as file:
            self.compare_line_by_line(list_version.split("\n"), file.readlines())

    def test_csv_hardcoded(self) -> None:
        """Tests if the postscript output from an event loaded from a CSV is idential to an event loaded from a list of cars."""
        csv_cars = load_demo_list()
        list_cars = make_demo_list()

        csv_sheet, frame1 = self.event_to_sheet(
            KnockoutEvent(csv_cars, self.test_csv_hardcoded.__name__, 2)
        )
        list_sheet, frame2 = self.event_to_sheet(
            KnockoutEvent(list_cars, self.test_csv_hardcoded.__name__, 2)
        )

        self.compare_postscript(csv_sheet, list_sheet)
        frame1.destroy()
        frame2.destroy()

    def compare_fresh_updated_draws(
        self, updater: Callable[[Callable[[RoundId, int, int], None]], None],
        name: str = "Test",
        save_end_result:bool = False
    ) -> None:
        cars = make_demo_list()
        fresh_event = KnockoutEvent(cars, name, 4)
        updated_event = KnockoutEvent(cars, name, 4)
        updated_sheet, updated_window = self.event_to_sheet(updated_event)

        def update(round: RoundId, race: int, winner: int) -> None:
            """Updates both sheets and redraws the updated one."""
            fresh_event.get_round(round)[race].set_winner(
                winner, fresh_event.auxilliary_races
            )
            updated_event.get_round(round)[race].set_winner(
                winner, updated_event.auxilliary_races
            )
            updated_sheet.update()

        # update(RoundId(RoundType.WINNERS, 0), 0, 106)
        updater(update)

        # Now render the other sheet and compare.
        fresh_sheet, fresh_window = self.event_to_sheet(fresh_event)
        if save_end_result:
            fresh_sheet.export(
                ghostscript_path=self.GHOSTSCRIPT_PATH,
                output=relative_path(f"{name}_fresh.ps"),
                pdf_width_mm=self.PAGE_WIDTH,
                pdf_height_mm=self.PAGE_HEIGHT,
                save_ps=True,
                generate_pdf=False,
                surpress_output=True
            )
            updated_sheet.export(
                ghostscript_path=self.GHOSTSCRIPT_PATH,
                output=relative_path(f"{name}_updates.ps"),
                pdf_width_mm=self.PAGE_WIDTH,
                pdf_height_mm=self.PAGE_HEIGHT,
                save_ps=True,
                generate_pdf=False,
                surpress_output=True
            )
        self.compare_postscript(fresh_sheet, updated_sheet)

    def test_fresh_updated_single(self):
        """Compares a freshly drawn sheet vs an empty sheet that has been updated to set a single race winner."""

        def run_updates(update: Callable[[RoundId, int, int], None]) -> None:
            update(RoundId(RoundType.WINNERS, 0), 0, 106)

        self.compare_fresh_updated_draws(run_updates)

    def test_fresh_updated_first_round(self) -> None:
        """Compares a freshly drawn sheet vs an empty sheet that has been updated for the first round."""

        def run_updates(update: Callable[[RoundId, int, int], None]) -> None:
            update(RoundId(RoundType.WINNERS, 0), 0, 106)
            update(RoundId(RoundType.WINNERS, 0), 1, 104)
            update(RoundId(RoundType.WINNERS, 0), 2, Race.WINNER_DNR)
            update(RoundId(RoundType.WINNERS, 0), 3, Race.WINNER_DNR)

        self.compare_fresh_updated_draws(run_updates)

    def test_fresh_updated_all_rounds(self) -> None:
        """Compares a freshly drawn sheet vs an empty sheet that has been updated for all rounds."""

        def run_updates(update: Callable[[RoundId, int, int], None]) -> None:
            # Primary first round.
            update(RoundId(RoundType.WINNERS, 0), 0, 106)
            update(RoundId(RoundType.WINNERS, 0), 1, 104)
            update(RoundId(RoundType.WINNERS, 0), 2, Race.WINNER_DNR)
            update(RoundId(RoundType.WINNERS, 0), 3, Race.WINNER_DNR)

            # Auxilliary race.
            update(RoundId(RoundType.AUXILLIARY, 0), 0, 101)

            # Secondary first round.
            update(RoundId(RoundType.LOSERS, 0), 0, 102)
            update(RoundId(RoundType.LOSERS, 0), 1, 101)

            # Primary second round.
            update(RoundId(RoundType.WINNERS, 1), 0, 106)
            # The second race is N/A as there were two DNRs before it.

            # Secondary second round.
            update(RoundId(RoundType.LOSERS, 1), 0, 104)
            update(RoundId(RoundType.LOSERS, 1), 1, 101)

            # Secondary third round.
            update(RoundId(RoundType.LOSERS, 2), 0, 104)

            # Primary third round.
            update(RoundId(RoundType.WINNERS, 2), 0, 106)

            # Secondary fourth round.
            update(RoundId(RoundType.LOSERS, 3), 0, 104)

            # Grand final.
            update(RoundId(RoundType.GRAND_FINAL, 0), 0, 106)

        self.compare_fresh_updated_draws(run_updates, "AllRounds", False)

    # def test_do_undo(self) -> None:
    #     # TODO:
    #     pass


if __name__ == "__main__":
    # race = TestRace()
    # race.test_is_editable()
    unittest.main()
