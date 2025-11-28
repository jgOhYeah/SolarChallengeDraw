import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../SolarChallengeDraw"))
)
from knockout import *
from car import *
import unittest


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

        # Add some winners.
        assert (
            left_race.left_branch.car is not None
            and right_race.left_branch.car is not None
        ), "Initial competitors incorrect."
        left_race.set_winner(left_race.left_branch.car.car_id)
        right_race.set_winner(right_race.left_branch.car.car_id)

        # print(left_race, right_race)
        # print(winner_race, loser_race)
        # print(next_loser_race)

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
        left_race.set_winner(left_race.left_branch.car.car_id)

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
        right_race.set_winner(right_race.left_branch.car.car_id)

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

class TestCar(unittest.TestCase):
    def test_load_csv(self) -> None:
        csv_cars = load_cars(os.path.join(os.path.dirname(__file__), "test_cars.csv"))
        list_cars = [
            Car(101, 1, "Flying fish", True, True, True, 1),
            Car(102, 1, "Curious cat", True, True, True, 1),
            Car(103, 1, "Hungry horse", True, True, True, 2),
            Car(104, 2, "Percy penguin", True, True, True, 3),
            Car(105, 3, "Munching mouse", True, True, True, 4),
            Car(106, 3, "Busy bee", True, True, True, 4)
        ]
        self.assertEqual(csv_cars, list_cars, "The loaded CSV file does not match the theoretically equivalent list.")

class TestEvent(unittest.TestCase):
    def test_create(self):
        cars = [
            Car(101, 1, "Flying fish", True, True, True, 1),
            Car(102, 1, "Curious cat", True, True, True, 1),
            Car(103, 1, "Hungry horse", True, True, True, 2),
            Car(104, 2, "Percy penguin", True, True, True, 3),
            Car(105, 3, "Munching mouse", True, True, True, 4),
            Car(106, 3, "Busy bee", True, True, True, 4)
        ]
        event = KnockoutEvent(cars, "Test")

if __name__ == "__main__":
    # race = TestRace()
    # race.test_is_editable()
    unittest.main()
