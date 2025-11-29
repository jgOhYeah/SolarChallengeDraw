"""knockout_sheet_elements.py
Classes and tools that help with specific elements when rendering knockout draws.
Written by Jotham Gates, 29/11/2025"""

from __future__ import annotations
from abc import ABC, abstractmethod
from enum import StrEnum
import tkinter as tk
from typing import Iterable, List, Tuple, TYPE_CHECKING
import numpy as np
import ttkbootstrap as ttk
import ttkbootstrap.constants as ttkc

if TYPE_CHECKING:
    # We are in type checking mode and are allowed a circular import. This is always skipped in runtime.
    # https://stackoverflow.com/a/39757388
    from knockout_sheet import KnockoutSheet

from knockout_race import (
    RaceBranch,
    FillProbability,
    Race,
    BranchType
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
column_width = LABEL_WIDTH + 2 * TEXT_MARGIN + 2 * HORIZONTAL_LINE_LENGTH


class NumberBox(ABC):
    """An abstract class that represents a numbered box in a race that shows car numbers."""

    def __init__(
        self,
        canvas: ttk.Canvas,
        x: float,
        y: float,
        race_branch: RaceBranch,
        sheet: KnockoutSheet,
    ) -> None:
        """Initialises the number box.

        Args:
            canvas (ttk.Canvas): The canvas to draw on.
            x (float): The x coordinate of the west side.
            y (float): The y coordinate of the horizontal centre line.
            race_branch (RaceBranch): The race brnach whose number we are to show.
            sheet (KnockoutSheet): The sheet that is to be called back upon update.
        """
        self._race_branch = race_branch
        self._draw(canvas, x, y, sheet)

    @abstractmethod
    def _draw(
        self, canvas: ttk.Canvas, x: float, y: float, sheet: KnockoutSheet
    ) -> None:
        """Abstract method that creates and draws the objects.

        Args:
            canvas (ttk.Canvas): The canvas to draw on.
            x (float): The x coordinate of the west side.
            y (float): The y coordinate of the horizontal centre line.
            sheet (KnockoutSheet): The sheet that is to be called back upon update.
        """
        pass

    @abstractmethod
    def update(self, canvas: ttk.Canvas) -> None:
        """Updates any text, styling or state if the data in self._race_branch. has changed.

        Args:
            canvas (ttk.Canvas): The canvas to draw on if needed.
        """
        pass

    class StrFixedOptions(StrEnum):
        EMPTY = ""
        DNR = "DNR"
        NOT_APPLICABLE = "N/A"

    def _get_options(self) -> List[str]:
        """Create a list of options for the menu.

        Returns:
            List[str]: A list of values to show in the dropdown.
        """
        if self._race_branch.prev_race is not None:
            values = self._race_branch.prev_race.get_options()
        else:
            values = []

        if (
            not self._race_branch.is_editable()
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

    def _display_text(self) -> str:
        """Returns a string for the text that should be displayed in the box."""
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

        assert text in self._get_options(), "The displayed text must be an option."
        return text


class InteractiveNumberBox(NumberBox):
    """An interactive NumberBox that is implemented using a combobox (drop down menu).
    This is ideal for showing on screen, but exports as a bitmap and may not render
    if offscreen when exporting to PDF."""

    def __init__(
        self,
        canvas: ttk.Canvas,
        x: float,
        y: float,
        race_branch: RaceBranch,
        sheet: KnockoutSheet,
    ) -> None:
        super().__init__(canvas, x, y, race_branch, sheet)
        self._in_update = False  # Signals if a change to the combobox should be ignored (somewhat like a semaphore).

    def _combobox_state(self) -> str:
        """Returns the current state string for whether the combobox should be editable.

        Returns:
            str: State string recognised by ttk.
        """
        return ttkc.NORMAL if self._race_branch.is_editable() else ttkc.DISABLED

    def _draw(
        self, canvas: ttk.Canvas, x: float, y: float, sheet: KnockoutSheet
    ) -> None:
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
            if validate(selected):
                assert (
                    self._race_branch.prev_race is not None
                ), "There should be a previous race to select values from."
                match selected:
                    case self.StrFixedOptions.EMPTY:
                        self._race_branch.prev_race.set_winner(Race.WINNER_EMPTY)
                    case self.StrFixedOptions.DNR:
                        self._race_branch.prev_race.set_winner(Race.WINNER_DNR)
                    case _:
                        number = int(selected)
                        self._race_branch.prev_race.set_winner(number)

                sheet.update()

        current_var = tk.StringVar()

        def on_write(var: str, index: str, mode: str):
            """Called on the text variable being updated."""
            if not self._in_update:
                update_races(current_var.get())

        self._combobox = ttk.Combobox(
            canvas,
            validate="all",
            validatecommand=(canvas.register(validate), "%P"),
            textvariable=current_var,
        )

        # Add the trace after writing the initial value to the combobox.
        current_var.trace_add("write", on_write)

        self.update(canvas)
        canvas.create_window(
            x,
            y,
            anchor=ttkc.W,
            width=LABEL_WIDTH,
            height=LABEL_HEIGHT,
            window=self._combobox,
        )

    def update(self, canvas: tk.Canvas) -> None:
        self._in_update = True
        options = self._get_options()
        self._combobox["values"] = options
        self._combobox["state"] = self._combobox_state()
        # Show the current car if needed.
        self._combobox.current(options.index(self._display_text()))
        self._in_update = False


class PrintNumberBox(NumberBox):
    """Class that draws a box around a number that can be printed but is not editable."""

    def _draw(
        self, canvas: ttk.Canvas, x: float, y: float, sheet: KnockoutSheet
    ) -> None:
        self._rectangle = canvas.create_rectangle(
            x, y - LABEL_HEIGHT / 2, x + LABEL_WIDTH, y + LABEL_HEIGHT / 2, fill="#fff"
        )
        self._text = canvas.create_text(
            x + LABEL_WIDTH / 2,
            y,
            anchor=ttkc.CENTER,
            font=(FONT, FONT_NORMAL_SIZE),
        )
        self.update(canvas)

    def update(self, canvas: ttk.Canvas) -> None:
        canvas.itemconfigure(self._text, text=self._display_text())
        dash, outline = fill_probability_style(self._race_branch.fill_probability())
        canvas.itemconfigure(self._rectangle, dash=dash, outline=outline)


class InitialNumberBox(NumberBox):
    def _draw(
        self, canvas: ttk.Canvas, x: float, y: float, sheet: KnockoutSheet
    ) -> None:
        assert (
            self._race_branch.car is not None
        ), "The initial number box cannot cope with None car ID currently."
        # Show the numbers as not a dropdown at all.
        self._line1 = canvas.create_text(
            x + LABEL_WIDTH,
            y - TEXT_LINE_HEIGHT / 2,
            anchor=ttkc.E,
            width=LABEL_WIDTH,
            text=self._line1_text(),
            font=(FONT, FONT_NORMAL_SIZE),
        )
        self._line2 = canvas.create_text(
            x + LABEL_WIDTH,
            y + TEXT_LINE_HEIGHT / 2,
            anchor=ttkc.E,
            width=LABEL_WIDTH,
            text=self._line2_text(),
            font=(FONT, FONT_SMALL_SIZE, "italic"),
        )

    def _line1_text(self) -> str:
        assert (
            self._race_branch.car is not None
        ), "The initial number box cannot cope with None car ID currently."
        return f"{self._race_branch.car.car_id}"

    def _line2_text(self) -> str:
        assert (
            self._race_branch.car is not None
        ), "The initial number box cannot cope with None car ID currently."
        return f"{self._race_branch.car.car_name}"

    def update(self, canvas: ttk.Canvas) -> None:
        canvas.itemconfigure(self._line1, text=self._line1_text())
        canvas.itemconfigure(self._line2, text=self._line2_text())


class NumberBoxFactory(ABC):
    """Abstract class that creates a number box at a specified location."""

    @abstractmethod
    def _create_not_fixed(
        self,
        canvas: ttk.Canvas,
        x: float,
        y: float,
        race_branch: RaceBranch,
        sheet: KnockoutSheet,
    ) -> NumberBox:
        pass

    def create(
        self,
        canvas: ttk.Canvas,
        x: float,
        y: float,
        race_branch: RaceBranch,
        sheet: KnockoutSheet,
    ) -> NumberBox:
        if race_branch.branch_type != BranchType.FIXED:
            return self._create_not_fixed(canvas, x, y, race_branch, sheet)
        else:
            return InitialNumberBox(canvas, x, y, race_branch, sheet)


class InteractiveNumberBoxFactory(NumberBoxFactory):
    def _create_not_fixed(
        self,
        canvas: ttk.Canvas,
        x: float,
        y: float,
        race_branch: RaceBranch,
        sheet: KnockoutSheet,
    ) -> NumberBox:
        return InteractiveNumberBox(canvas, x, y, race_branch, sheet)


class PrintNumberBoxFactory(NumberBoxFactory):
    def _create_not_fixed(
        self,
        canvas: ttk.Canvas,
        x: float,
        y: float,
        race_branch: RaceBranch,
        sheet: KnockoutSheet,
    ) -> NumberBox:
        return PrintNumberBox(canvas, x, y, race_branch, sheet)


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
        self, canvas: ttk.Canvas, x_tee_start: float, x_end: float, y_centre: float
    ) -> None:
        # The line from the tee (or start for a bye) to the end.
        self._tee_line = canvas.create_line(
            x_tee_start, y_centre, x_end, y_centre, width=BRACKET_LINE_THICKNESS
        )
        self.update(canvas)

    @abstractmethod
    def update(self, canvas: ttk.Canvas) -> None:
        """Updates the line styles depending on the probability that the line will be needed."""
        pass

    def _update_line(
        self, canvas: ttk.Canvas, lines: Iterable[int], probability: FillProbability
    ) -> None:
        """Updates the tee line with the probability that 2 lines are filled."""
        dash, outline = fill_probability_style(probability)

        for line in lines:
            canvas.itemconfigure(line, dash=dash, fill=outline)


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
        self._branches = race_branches
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

        super().__init__(canvas, tee_x, x_end, y_centre)

    def update(self, canvas: ttk.Canvas) -> None:
        # Tee line
        self._update_line(
            canvas,
            (self._tee_line,),
            max(
                self._branches[0].fill_probability(),
                self._branches[1].fill_probability(),
            ),
        )

        # Top
        self._update_line(canvas, self._top_lines, self._branches[0].fill_probability())

        # Bottom
        self._update_line(
            canvas, self._bottom_lines, self._branches[1].fill_probability()
        )


class BracketLineSetBye(BracketLineSet):
    def __init__(
        self,
        canvas: ttk.Canvas,
        x_start: float,
        x_end: float,
        y_centre: float,
        race_branch: RaceBranch,
    ) -> None:
        self._branch = race_branch
        super().__init__(canvas, x_start, x_end, y_centre)

    def update(self, canvas: ttk.Canvas) -> None:
        self._update_line(canvas, (self._tee_line,), self._branch.fill_probability())

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
        self._y_pos: float = self._top_left[1] + TEXT_MARGIN

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
                self._y_pos,
                anchor=ttkc.NE,
                font=font,
                text="• ",
                width=BULLET_POINT_WIDTH,
            )

        # Draw the text.
        _, _, _, bottom = self._canvas.bbox(
            self._canvas.create_text(
                left,
                self._y_pos,
                anchor=ttkc.NW,
                font=font,
                text=text,
                width=text_width,
            )
        )
        self._y_pos = bottom

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
