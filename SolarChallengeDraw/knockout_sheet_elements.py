"""knockout_sheet_elements.py
Classes and tools that help with specific elements when rendering knockout draws.
Written by Jotham Gates, 29/11/2025"""

from __future__ import annotations
from abc import ABC, abstractmethod
from enum import StrEnum
import tkinter as tk
from typing import Iterable, List, Literal, Tuple, TYPE_CHECKING, cast
import numpy as np
import ttkbootstrap as ttk
import ttkbootstrap.constants as ttkc

if TYPE_CHECKING:
    # We are in type checking mode and are allowed a circular import. This is always skipped in runtime.
    # https://stackoverflow.com/a/39757388
    from knockout_sheet import KnockoutSheet

from knockout import AuxilliaryRaceManager, KnockoutEvent
from knockout_race import (
    BranchResult,
    Podium,
    RaceBranch,
    FillProbability,
    Race,
    BranchType,
)

# Settings
LEFT_MARGIN = 10
TOP_MARGIN = 10
RIGHT_MARGIN = TOP_MARGIN
BOTTOM_MARGIN = TOP_MARGIN
TEXT_MARGIN = 10
FONT = "Arial"
FONT_SMALL_SIZE = 7
FONT_NORMAL_SIZE = 10
FONT_TITLE_SIZE = 15
FONT_SUPTITLE_SIZE = 30
HORIZONTAL_LINE_LENGTH = 20
LABEL_WIDTH = 100
LABEL_HEIGHT = 30
SHORT_TEXT_MARGIN = TEXT_MARGIN / 2
WINNERS_INITIAL_SPACING = 55
LOSERS_INITIAL_SPACING = 80
TEXT_LINE_HEIGHT = 12
ARROW_HEIGHT = 15
ARROW_WIDTH = 20
BRACKET_VERTICAL_SEPARATION = 50
BRACKET_LINE_THICKNESS = 2
FIRST_COLUMN_HINT_WIDTH = LABEL_WIDTH
COLUMN_WIDTH = LABEL_WIDTH + 2 * TEXT_MARGIN + 2 * HORIZONTAL_LINE_LENGTH
AUX_RACES_SECTION_WIDTH = COLUMN_WIDTH + LABEL_WIDTH + 2 * TEXT_MARGIN


class NumberBox(ABC):
    """An abstract class that represents a numbered box in a race that shows car numbers."""

    def __init__(
        self,
        x: float,
        y: float,
        race_branch: RaceBranch | None,
        aux_race_manager: AuxilliaryRaceManager,
        sheet: KnockoutSheet,
        override_type_editable: bool
    ) -> None:
        """Initialises the number box.

        Args:
            x (float): The x coordinate of the west side.
            y (float): The y coordinate of the horizontal centre line.
            race_branch (RaceBranch): The race branch whose number we are to show.
            aux_race_manager (AuxilliaryRaceManager): Manager for auxilliary races.
            sheet (KnockoutSheet): The sheet that is to be called back upon update.
        """
        self._race_branch = race_branch
        self._aux_race_manager = aux_race_manager
        self._sheet = sheet
        self._override_type_editable = override_type_editable
        self._draw(x, y)

    @abstractmethod
    def _draw(self, x: float, y: float) -> None:
        """Abstract method that creates and draws the objects.

        Args:
            x (float): The x coordinate of the west side.
            y (float): The y coordinate of the horizontal centre line.
        """
        pass

    @abstractmethod
    def update(self) -> None:
        """Updates any text, styling or state if the data in self._race_branch. has changed."""
        pass

    def set_race_branch(self, branch: RaceBranch | None) -> None:
        self._race_branch = branch
        self.update()

    class StrFixedOptions(StrEnum):
        EMPTY = ""
        DNR = "DNR"
        NOT_APPLICABLE = "N/A"

    def _get_options(self) -> List[str]:
        """Create a list of options for the menu.

        Returns:
            List[str]: A list of values to show in the dropdown.
        """
        if self._race_branch is not None:
            # A valid race branch has been provided.
            if self._race_branch.prev_race is not None:
                values = self._race_branch.prev_race.get_options()
            else:
                values = []

            if (
                not self._race_branch.is_editable(self._override_type_editable)
                and self._race_branch.fill_probability() == FillProbability.IMPOSSIBLE
            ):
                # It is impossible to fill this and we can add a N/A without being noticed.
                na_list = [self.StrFixedOptions.NOT_APPLICABLE.value]
            else:
                na_list = []

            values = (
                [self.StrFixedOptions.EMPTY]
                + [f"{i.car_id}" for i in values]
                + [self.StrFixedOptions.DNR]
                + na_list
            )
            return values
        else:
            # No race branch has been provided to generate options.
            return [self.StrFixedOptions.EMPTY]

    def _display_text(self) -> str:
        """Returns a string for the text that should be displayed in the box."""
        if self._race_branch is not None:
            # Normal, race branch provided.
            if self._race_branch.car is not None:
                text = f"{self._race_branch.car.car_id}"
            elif self._race_branch.filled:
                # Filled as empty (DNR)
                text = self.StrFixedOptions.DNR
            elif self._race_branch.fill_probability() == FillProbability.IMPOSSIBLE:
                # Impossible to fill.
                text = self.StrFixedOptions.NOT_APPLICABLE
            else:
                # Actually empty.
                text = self.StrFixedOptions.EMPTY
        else:
            # No branch provided.
            text = self.StrFixedOptions.EMPTY
        assert text in self._get_options(), "The displayed text must be an option."
        return text


class InteractiveNumberBox(NumberBox):
    """An interactive NumberBox that is implemented using a combobox (drop down menu).
    This is ideal for showing on screen, but exports as a bitmap and may not render
    if offscreen when exporting to PDF."""

    def __init__(
        self,
        x: float,
        y: float,
        race_branch: RaceBranch | None,
        aux_race_manager: AuxilliaryRaceManager,
        sheet: KnockoutSheet,
        override_type_editable: bool,
    ) -> None:
        """Initialises the number box.

        Args:
            x (float): The x coordinate of the left hand side.
            y (float): The y coordinate of the middle.
            race_branch (RaceBranch | None): The branch to represent. None can
                be used for an empty box.
            aux_race_manager (AuxilliaryRaceManager): The auxilliary race
                manager to send when editing results.
            sheet (KnockoutSheet): The sheet that the box is being drawn on.
            override_type_editable (bool, optional): Whether to treat
                BranchType.DEPENDENT_NOT_EDITABLE as
                BranchType.DEPENDENT_EDITABLE. Defaults to False.
        """
        super().__init__(x, y, race_branch, aux_race_manager, sheet, override_type_editable)
        self._in_update = False  # Signals if a change to the combobox should be ignored (somewhat like a semaphore).

    def _combobox_state(self) -> str:
        """Returns the current state string for whether the combobox should be editable.

        Returns:
            str: State string recognised by ttk.
        """
        return (
            ttkc.NORMAL
            if self._race_branch is not None
            and self._race_branch.is_editable(self._override_type_editable)
            else ttkc.DISABLED
        )

    def _draw(self, x: float, y: float) -> None:
        # Show a combobox (may need to be non-editable).

        def validate(selected: str) -> bool:
            """Validates the currently selected combobox.

            Args:
                selected (str): The currently selected value.

            Returns:
                bool: Whether the option is valid.
            """
            return selected in self._get_options()

        def update_races(selected: str) -> None:
            """Updates the race draw with a new winner for this number."""
            if self._race_branch is not None and validate(selected):
                assert (
                    self._race_branch.prev_race is not None
                ), "There should be a previous race to select values from."
                match selected:
                    case self.StrFixedOptions.EMPTY:
                        self._race_branch.prev_race.set_winner(
                            Race.WINNER_EMPTY, self._aux_race_manager
                        )
                    case self.StrFixedOptions.DNR:
                        self._race_branch.prev_race.set_winner(
                            Race.WINNER_DNR, self._aux_race_manager
                        )
                    case _:
                        number = int(selected)
                        self._race_branch.prev_race.set_winner(
                            number, self._aux_race_manager
                        )

                self._sheet.update()

        current_var = tk.StringVar()

        def on_write(var: str, index: str, mode: str):
            """Called on the text variable being updated."""
            if not self._in_update:
                update_races(current_var.get())

        self._combobox = ttk.Combobox(
            self._sheet.canvas,
            validate="all",
            validatecommand=(self._sheet.canvas.register(validate), "%P"),
            textvariable=current_var,
        )

        # Add the trace after writing the initial value to the combobox.
        current_var.trace_add("write", on_write)

        self.update()
        self._sheet.canvas.create_window(
            x,
            y,
            anchor=ttkc.W,
            width=LABEL_WIDTH,
            height=LABEL_HEIGHT,
            window=self._combobox,
        )

    def update(self) -> None:
        self._in_update = True
        options = self._get_options()
        self._combobox["values"] = options
        self._combobox["state"] = self._combobox_state()
        # Show the current car if needed.
        self._combobox.current(options.index(self._display_text()))
        self._in_update = False


class PrintNumberBox(NumberBox):
    """Class that draws a box around a number that can be printed but is not editable."""

    def _draw(self, x: float, y: float) -> None:
        self._rectangle = self._sheet.canvas.create_rectangle(
            x, y - LABEL_HEIGHT / 2, x + LABEL_WIDTH, y + LABEL_HEIGHT / 2, fill="#fff"
        )
        self._text = self._sheet.canvas.create_text(
            x + LABEL_WIDTH / 2,
            y,
            anchor=ttkc.CENTER,
            font=(FONT, FONT_NORMAL_SIZE),
        )
        self.update()

    def update(self) -> None:
        self._sheet.canvas.itemconfigure(self._text, text=self._display_text())
        if self._race_branch is None:
            fill_probability = FillProbability.IMPOSSIBLE
        else:
            fill_probability = self._race_branch.fill_probability()
        dash, outline = fill_probability_style(fill_probability)
        self._sheet.canvas.itemconfigure(self._rectangle, dash=dash, outline=outline)


class InitialNumberBox(NumberBox):
    def _draw(self, x: float, y: float) -> None:
        assert (
            self._race_branch is not None and self._race_branch.car is not None
        ), "The initial number box cannot cope with no RaceBranch provided or None car ID currently."
        # Show the numbers as not a dropdown at all.
        self._line1 = self._sheet.canvas.create_text(
            x + LABEL_WIDTH,
            y - TEXT_LINE_HEIGHT / 2,
            anchor=ttkc.E,
            width=LABEL_WIDTH,
            text=self._line1_text(),
            font=(FONT, FONT_NORMAL_SIZE),
        )
        self._line2 = self._sheet.canvas.create_text(
            x + LABEL_WIDTH,
            y + TEXT_LINE_HEIGHT / 2,
            anchor=ttkc.E,
            width=LABEL_WIDTH,
            text=self._line2_text(),
            font=(FONT, FONT_SMALL_SIZE, "italic"),
        )

    def _line1_text(self) -> str:
        assert (
            self._race_branch is not None and self._race_branch.car is not None
        ), "The initial number box cannot cope with no RaceBranch provided or None car ID currently."
        return f"{self._race_branch.car.car_id}"

    def _line2_text(self) -> str:
        assert (
            self._race_branch is not None and self._race_branch.car is not None
        ), "The initial number box cannot cope with no RaceBranch provided or None car ID currently."
        return f"{self._race_branch.car.car_name}"

    def update(self) -> None:
        self._sheet.canvas.itemconfigure(self._line1, text=self._line1_text())
        self._sheet.canvas.itemconfigure(self._line2, text=self._line2_text())


class NumberBoxFactory(ABC):
    """Abstract class that creates a number box at a specified location."""

    @abstractmethod
    def _create_not_fixed(
        self,
        x: float,
        y: float,
        race_branch: RaceBranch | None,
        aux_race_manager: AuxilliaryRaceManager,
        sheet: KnockoutSheet,
        override_type_editable: bool = False,
    ) -> NumberBox:
        pass

    def create(
        self,
        x: float,
        y: float,
        race_branch: RaceBranch | None,
        aux_race_manager: AuxilliaryRaceManager,
        sheet: KnockoutSheet,
        override_type_editable: bool = False,
    ) -> NumberBox:
        if race_branch is None or race_branch.branch_type != BranchType.FIXED:
            return self._create_not_fixed(
                x, y, race_branch, aux_race_manager, sheet, override_type_editable
            )
        else:
            return InitialNumberBox(x, y, race_branch, aux_race_manager, sheet, override_type_editable)


class InteractiveNumberBoxFactory(NumberBoxFactory):
    def _create_not_fixed(
        self,
        x: float,
        y: float,
        race_branch: RaceBranch | None,
        aux_race_manager: AuxilliaryRaceManager,
        sheet: KnockoutSheet,
        override_type_editable: bool = False,
    ) -> NumberBox:
        return InteractiveNumberBox(
            x=x,
            y=y,
            race_branch=race_branch,
            aux_race_manager=aux_race_manager,
            sheet=sheet,
            override_type_editable=override_type_editable,
        )


class PrintNumberBoxFactory(NumberBoxFactory):
    def _create_not_fixed(
        self,
        x: float,
        y: float,
        race_branch: RaceBranch | None,
        aux_race_manager: AuxilliaryRaceManager,
        sheet: KnockoutSheet,
        override_type_editable: bool = False,
    ) -> NumberBox:
        return PrintNumberBox(x, y, race_branch, aux_race_manager, sheet, override_type_editable)


def fill_probability_style(
    probability: FillProbability,
) -> Tuple[Tuple[float, float], str]:
    """Returns the dash and line colour that represents a given probability.

    Args:
        probability (FillProbability): The probability to look up.

    Raises:
        ValueError: If an unkown probability is provided.

    Returns:
        Tuple[Tuple[float, float], str]: The dash and colour settings.
    """
    dash: tuple
    outline: str
    match probability:
        case FillProbability.IMPOSSIBLE:
            # canvas.itemconfigure(line, dash=(10))
            dash = (1, 2)
            outline = "#A5A5A5"

        case FillProbability.UNLIKELY:
            dash = (3, 3)
            outline = "#000000"

        case (
            FillProbability.LIKELY | FillProbability.GUARANTEED | FillProbability.UNKOWN
        ):
            dash = ()
            outline = "#000000"

        case _:
            raise ValueError("???")

    return dash, outline


class BracketLineSet(ABC):
    """Class for bracket lines."""

    def __init__(
        self,
        canvas: ttk.Canvas,
        x_tee_start: float,
        x_end: float,
        y_centre: float,
        branches: Tuple[RaceBranch] | Tuple[RaceBranch, RaceBranch],
    ) -> None:
        # The line from the tee (or start for a bye) to the end.
        self._tee_line = canvas.create_line(
            x_tee_start, y_centre, x_end, y_centre, width=BRACKET_LINE_THICKNESS
        )
        self._canvas = canvas
        self._branches = branches
        self.update()

    @abstractmethod
    def update(self) -> None:
        """Updates the line styles depending on the probability that the line will be needed."""
        pass

    def _update_line(self, lines: Iterable[int], probability: FillProbability) -> None:
        """Updates the tee line with the probability that 2 lines are filled."""
        dash, outline = fill_probability_style(probability)

        for line in lines:
            self._canvas.itemconfigure(line, dash=dash, fill=outline)

    def update_branches(
        self, branches: Tuple[RaceBranch] | Tuple[RaceBranch, RaceBranch]
    ) -> None:
        assert len(branches) == len(
            self._branches
        ), "The length of the branches must not change (converting between a bye and normal race is not allowed)."
        self._branches = branches
        self.update()


class BracketLineSetNormal(BracketLineSet):
    def __init__(
        self,
        canvas: ttk.Canvas,
        x_start: float,
        x_end: float,
        y_centre: float,
        race_branches: Tuple[RaceBranch, RaceBranch],
        y_separation: float,
    ) -> None:
        # Line from the right side of the bracket to the end.
        tee_x = x_end - HORIZONTAL_LINE_LENGTH

        # Top lines
        top_y = y_centre - y_separation / 2
        self._top_lines = (
            canvas.create_line(
                x_start, top_y, tee_x, top_y, width=BRACKET_LINE_THICKNESS
            ),
            canvas.create_line(
                tee_x, top_y, tee_x, y_centre, width=BRACKET_LINE_THICKNESS
            ),
        )

        # Bottom lines
        bottom_y = y_centre + y_separation / 2
        self._bottom_lines = (
            canvas.create_line(
                x_start, bottom_y, tee_x, bottom_y, width=BRACKET_LINE_THICKNESS
            ),
            canvas.create_line(
                tee_x, y_centre, tee_x, bottom_y, width=BRACKET_LINE_THICKNESS
            ),
        )

        super().__init__(canvas, tee_x, x_end, y_centre, race_branches)

    def update(self) -> None:
        assert len(self._branches) == 2, "Check to keep type checking happy."

        # Tee line
        self._update_line(
            (self._tee_line,),
            max(
                self._branches[0].fill_probability(),
                self._branches[1].fill_probability(),
            ),
        )

        # Top
        self._update_line(self._top_lines, self._branches[0].fill_probability())

        # Bottom
        self._update_line(self._bottom_lines, self._branches[1].fill_probability())


class BracketLineSetBye(BracketLineSet):
    def __init__(
        self,
        canvas: ttk.Canvas,
        x_start: float,
        x_end: float,
        y_centre: float,
        race_branch: RaceBranch,
    ) -> None:
        super().__init__(canvas, x_start, x_end, y_centre, (race_branch,))

    def update(self) -> None:
        self._update_line((self._tee_line,), self._branches[0].fill_probability())


class NotesBox:
    """Class that handles items in the notes box."""

    def __init__(
        self,
        canvas: ttk.Canvas,
        top_left: Tuple[float, float],
        bottom_right: Tuple[float, float],
    ) -> None:
        """Creates an empty notes box.

        Args:
            canvas (ttk.Canvas): The canvas to draw on.
            top_left (Tuple[float, float]): The top left coordinates.
            bottom_right (Tuple[float, float]): The bottom right coordinates.
        """
        self._canvas = canvas
        self._top_left = top_left
        self._bottom_right = bottom_right
        self._canvas.create_rectangle(self._top_left, self._bottom_right)
        self.y_pos: float = self._top_left[1] + TEXT_MARGIN

    def add_text(
        self, text: str, font: tuple | None = None, bullet_point: bool = False
    ) -> None:
        """Adds text to the notes box.

        Args:
            text (str): The text to show.
            font (tuple | None, optional): Font and size specification if needed. Defaults to None.
            bullet_point (bool, optional): If True, shows a bullet point. Defaults to False.
        """
        # Specify the font if left blank.
        if font is None:
            font = (FONT, FONT_NORMAL_SIZE)

        # Positions and widths
        # Defaults for no bullet point.
        left = self._top_left[0] + TEXT_MARGIN
        text_width = self._bottom_right[0] - self._top_left[0] - 2 * TEXT_MARGIN
        if bullet_point:
            # Adding a bullet point.
            BULLET_POINT_WIDTH = 15
            left += BULLET_POINT_WIDTH
            text_width -= BULLET_POINT_WIDTH
            self._canvas.create_text(
                left,
                self.y_pos,
                anchor=ttkc.NE,
                font=font,
                text="• ",
                width=BULLET_POINT_WIDTH,
            )

        # Draw the text.
        _, _, _, bottom = self._canvas.bbox(
            self._canvas.create_text(
                left,
                self.y_pos,
                anchor=ttkc.NW,
                font=font,
                text=text,
                width=text_width,
            )
        )
        self.y_pos = bottom

    def process_markdown_line(self, line: str) -> None:
        """Very basic formatter for extremely limited markdown."""
        line = line.strip()

        # Headings and bullet points.
        font = (FONT, FONT_NORMAL_SIZE)
        bullet = False
        if line.startswith("#"):
            # Title.
            font = (FONT, FONT_TITLE_SIZE)
            line = line.lstrip("# ")
        elif line.startswith("-"):
            # Bullet point.
            bullet = True
            line = line.lstrip("- ")

        self.add_text(line, font, bullet)

    def read_markdown(self, filename: str) -> None:
        """Reads a markdown file.

        The parser is extremely basic.

        Args:
            filename (str): The name of the file to read.
        """
        with open(filename) as file:
            for line in file.readlines():
                self.process_markdown_line(line)


class RaceDrawing:
    """Class that draws a race."""

    def __init__(
        self,
        sheet: KnockoutSheet,
        event: KnockoutEvent,
        numbers_factory: NumberBoxFactory,
        show_seed: bool,
    ) -> None:
        """Initialises the race drawing on the provided sheet.

        Args:
            sheet (KnockoutSheet): The sheet to draw on.
            event (KnockoutEvent): The event containing the race to draw.
            numbers_factory (NumberBoxFactory): The factory to use when creating numbers boxes (allows print / screen selection).
            show_seed (bool): Whether to print the expected seed of the position in the box.
        """
        self._sheet = sheet
        self._event = event
        self._numbers_factory = numbers_factory
        self._show_seed = show_seed
        self._number_boxes: Tuple[NumberBox, NumberBox] | Tuple[NumberBox]
        self._lineset: BracketLineSet
        self._results_box: NumberBox | None = (
            None  # Only used if requested to show the results.
        )

    def draw_number(
        self,
        x: float,
        y: float,
        race_branch: RaceBranch | None,
        override_type_editable: bool = False,
    ) -> NumberBox:
        """Draws a numbers box at the specified position.

        Args:
            x (float): The left-most coordinate of the box.
            y (float): The box centreline.
            race_branch (RaceBranch): The branch the box is to get its data from
                and possible update.
            override_type_editable (bool, Optional): If True, treats
                DEPENDENT_NOT_EDITABLE as DEPENDENT_EDITABLE. Defaults to False.

        Returns:
            NumberBox: The created number box.
        """
        number_box = self._numbers_factory.create(
            x=x,
            y=y,
            race_branch=race_branch,
            aux_race_manager=self._event.auxilliary_races,
            sheet=self._sheet,
            override_type_editable=override_type_editable,
        )

        if race_branch is not None:
            # Draw the seed.
            if self._show_seed:
                self._sheet.canvas.create_text(
                    x + SHORT_TEXT_MARGIN,
                    y,
                    anchor=ttkc.W,
                    text=race_branch.seed,
                    fill="red",
                )

            # Arrow hinting where the competitor came from.
            show_label = False
            text = ""
            match race_branch.branch_result():
                case BranchResult.WINNER:
                    if (
                        race_branch.prev_race is not None
                        and race_branch.prev_race.winner_show_label
                        and not isinstance(
                            race_branch.prev_race.winner_next_race, Podium
                        )
                    ):
                        # Show the winner's label.
                        show_label = True
                        text = "Winner"

                case BranchResult.LOSER:
                    if (
                        race_branch.prev_race is not None
                        and race_branch.prev_race.loser_show_label
                        and not isinstance(
                            race_branch.prev_race.loser_next_race, Podium
                        )
                    ):
                        # Show the winner's label.
                        show_label = True
                        text = "Loser"

            if show_label:
                self.draw_hint_from_arrow(
                    x - SHORT_TEXT_MARGIN, y, cast(Race, race_branch.prev_race), text
                )

        return number_box

    def draw_hint_to_arrow(
        self,
        x: float,
        y: float,
        to_race: Race | Podium,
        result_name: str,
        if_dnr: bool = False,
        flip: Literal[-1] | Literal[1] = 1,
    ) -> None:
        """Draws an arrow to show where to proceed from a race."""
        points = [
            x,
            y,
            x + ARROW_WIDTH / 3,
            y + ARROW_HEIGHT * flip,
            x + 2 * ARROW_WIDTH / 3,
            y + ARROW_HEIGHT * flip,
            x + ARROW_WIDTH,
            y + ARROW_HEIGHT * flip,
        ]
        self._sheet.canvas.create_line(points, arrow="last", smooth=True)
        if_dnr_text = ""
        if if_dnr:
            if_dnr_text = " if DNR"

        self._sheet.canvas.create_text(
            x + ARROW_WIDTH + SHORT_TEXT_MARGIN,
            y + ARROW_HEIGHT * flip,
            text=f"{result_name} to {to_race.name()}{if_dnr_text}",
            anchor=ttkc.W,
            font=(FONT, FONT_SMALL_SIZE),
        )

    def draw_hint_from_arrow(
        self,
        x: float,
        y: float,
        from_race: Race | Podium,
        result_name: str,
        if_dnr: bool = False,
    ) -> None:
        """Draws and arrow to show which race a competitor is coming from.
        This complements draw_hint_to_arrow().

        Args:
            x (float): The x coordinate for the RIGHT side of the label.
            y (float): The y centre coordinate.
            from_race (Race | Podium): The race the arrow is coming from.
            result_name (str): "Winner" or "Loser"
            if_dnr (bool, optional): Adds an "if DNR" qualifier. Defaults to False.
        """
        points = [x - ARROW_WIDTH, y, x, y]
        self._sheet.canvas.create_line(points, arrow="last", smooth=True)

        if_dnr_text = ""
        if if_dnr:
            if_dnr_text = " if DNR"

        text_left_x, _, _, _ = self._sheet.canvas.bbox(
            self._sheet.canvas.create_text(
                x - ARROW_WIDTH - SHORT_TEXT_MARGIN,
                y,
                text=f"{result_name} from {from_race.name()}{if_dnr_text}",
                anchor=ttkc.E,
                font=(FONT, FONT_SMALL_SIZE),
            )
        )

    def draw_race(
        self,
        x: float,
        y_centre: float,
        y_spacing: float,
        columns_wide: int,
        race: Race,
        show_result_box: bool,
    ) -> float:
        """Draws a race.

        Args:
            x (float): The x location of the left side of the race.
            y_centre (float): The centreline of the race.
            y_spacing (float): The spacing between the inputs of the race.
            columns_wide (int): The number of columns wide to made the bracket.
            race (Race): The race to draw.
            show_result_box (bool): When True, draws the result of the race
                next to it (only enable for the grand final and auxilliary races).

        Returns:
            float: The x coordinate of the right side of the race.
        """
        bracket_x_start = x + LABEL_WIDTH + TEXT_MARGIN
        bracket_x_end = (
            bracket_x_start
            + 2 * HORIZONTAL_LINE_LENGTH
            + (columns_wide - 1) * COLUMN_WIDTH
        )

        def draw_race_number(
            anchor: Literal["nw", "n", "ne", "w", "center", "e", "sw", "s", "se"],
        ) -> None:
            """Draws the race number."""
            self._sheet.canvas.create_text(
                bracket_x_end - HORIZONTAL_LINE_LENGTH - SHORT_TEXT_MARGIN,
                y_centre,
                anchor=anchor,
                text=race.name(),
            )

        def draw_normal_race() -> None:
            top_y = y_centre - y_spacing / 2
            bottom_y = y_centre + y_spacing / 2
            assert not race.is_bye(), f"Use {draw_bye.__name__}() for a bye."
            self._number_boxes = (
                self.draw_number(x, top_y, race.left_branch),
                self.draw_number(x, bottom_y, race.right_branch),
            )
            self._lineset = BracketLineSetNormal(
                self._sheet.canvas,
                bracket_x_start,
                bracket_x_end,
                y_centre,
                (race.left_branch, race.right_branch),
                y_spacing,
            )
            draw_race_number(ttkc.E)

        def draw_bye() -> None:
            assert race.is_bye(), f"Use {draw_normal_race.__name__}() for non-byes."
            self._number_boxes = (
                self.draw_number(
                    x,
                    y_centre,
                    race.theoretical_winner(),
                ),
            )
            self._lineset = BracketLineSetBye(
                self._sheet.canvas,
                bracket_x_start,
                bracket_x_end,
                y_centre,
                race.theoretical_winner(),
            )
            draw_race_number(ttkc.SE)

        if race.is_bye():
            draw_bye()
        else:
            draw_normal_race()

        # Arrows going from the race.
        arrow_x = bracket_x_end - HORIZONTAL_LINE_LENGTH + TEXT_MARGIN
        if race.loser_show_label:
            assert (
                race.loser_next_race is not None
            ), "Show label is True for losers, but no losers to show."
            self.draw_hint_to_arrow(
                arrow_x,
                y_centre + TEXT_MARGIN,
                race.loser_next_race,
                "Loser",
                race.is_bye(),
            )

        if race.winner_show_label:
            assert (
                race.winner_next_race is not None
            ), "Show label is True for winners, but no winners to show."
            self.draw_hint_to_arrow(
                arrow_x,
                y_centre - TEXT_MARGIN,
                race.winner_next_race,
                "Winner",
                race.is_bye(),
                flip=-1,
            )

        right_side = bracket_x_end + TEXT_MARGIN

        # Draw the results box if needed.
        if show_result_box:
            self._results_box = self.draw_number(
                x=right_side,
                y=y_centre,
                race_branch=(
                    race.winner_next_race.get_single_branch(race)
                    if race.winner_next_race is not None
                    else None
                ),
                override_type_editable=True,
            )
            right_side += LABEL_WIDTH

        # Extend the line into the next round if needed.
        return right_side

    def assign_race(self, race: Race) -> None:
        """Assigns a new race to the race."""

        # Update the input boxes and lines.
        new_branches = race.get_branches()
        assert len(new_branches) == len(
            self._number_boxes
        ), "Currently the number of branches when updating must be the same."
        for i, branch in enumerate(new_branches):
            self._number_boxes[i].set_race_branch(branch)

        self._lineset.update_branches(new_branches)

        # Update the output box.
        if self._results_box is not None:
            if race.winner_next_race is not None:
                # We can provide an actual branch.
                branch = race.winner_next_race.get_single_branch(race)
            else:
                # We can't provide an actual branch.
                branch = None

            self._results_box.set_race_branch(branch)

    def update(self) -> None:
        """Updates the elements in the drawing of the race."""
        for number_box in self._number_boxes:
            number_box.update()
        
        if self._results_box is not None:
            self._results_box.update()

        self._lineset.update()


class AuxilliaryRaceSheet:
    """Class that draws the auxilliary races in their box."""

    def __init__(
        self,
        sheet: KnockoutSheet,
        event: KnockoutEvent,
        numbers_factory: NumberBoxFactory,
        top_left: Tuple[float, float],
        bottom_right: Tuple[float, float],
    ) -> None:
        """Initialises the section for auxilliary races and draws them.

        Args:
            sheet (KnockoutSheet): The sheet to draw on.
            event (KnockoutEvent): The event to draw.
            numbers_factory (NumberBoxFactory): The number boxes to create.
            top_left (Tuple[float, float]): The top left coordinates of the box.
            bottom_right (Tuple[float, float]): The bottom right coordinates of the box.
        """
        # Create a box to put the races in.
        self._box = NotesBox(
            canvas=sheet.canvas, top_left=top_left, bottom_right=bottom_right
        )
        self._box.add_text("Auxilliary races", (FONT, FONT_TITLE_SIZE))
        self._box.add_text(
            "Auxilliary races are only used if there is a DNR in a primary knockout race with two competitors."
        )

        # Create and draw the races.
        self._races: List[RaceDrawing] = []
        for race in event.auxilliary_races.races:
            drawing = RaceDrawing(
                sheet=sheet,
                event=event,
                numbers_factory=numbers_factory,
                show_seed=False,
            )
            self._races.append(drawing)
            y_centre = self._box.y_pos + BRACKET_VERTICAL_SEPARATION
            drawing.draw_race(
                x=top_left[0] + TEXT_MARGIN,
                y_centre=y_centre,
                y_spacing=BRACKET_VERTICAL_SEPARATION,
                columns_wide=1,
                race=race,
                show_result_box=True,
            )
            self._box.y_pos += 2 * BRACKET_VERTICAL_SEPARATION

        self._event = event

    def update(self):
        for race, drawing in zip(self._event.auxilliary_races.races, self._races):
            drawing.assign_race(race)
            drawing.update()
