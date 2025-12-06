"""knockout_sheet_elements.py
Classes and tools that help with specific elements when rendering knockout draws.
Written by Jotham Gates, 29/11/2025"""

from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum, StrEnum, auto
import tkinter as tk
from typing import Iterable, List, Literal, Tuple, TYPE_CHECKING, Type, cast
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
FIRST_COLUMN_HINT_WIDTH = LABEL_WIDTH + 50
COLUMN_WIDTH = LABEL_WIDTH + 2 * TEXT_MARGIN + 2 * HORIZONTAL_LINE_LENGTH
AUX_RACES_SECTION_WIDTH = COLUMN_WIDTH + LABEL_WIDTH + 2 * TEXT_MARGIN + ARROW_WIDTH


class NumberBox(ABC):
    """An abstract class that represents a numbered box in a race that shows car numbers."""

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
        super().__init__(
            x, y, race_branch, aux_race_manager, sheet, override_type_editable
        )
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
            return InitialNumberBox(
                x, y, race_branch, aux_race_manager, sheet, override_type_editable
            )


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
        return PrintNumberBox(
            x, y, race_branch, aux_race_manager, sheet, override_type_editable
        )


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


class HintArrow(ABC):
    """Class that draws a hint arrow."""

    def __init__(
        self,
        sheet: KnockoutSheet,
        text_handle: int,
        direction: Literal["to"] | Literal["from"],
    ) -> None:
        self._sheet = sheet
        self._text_handle = text_handle
        self._direction = direction

    def _text(
        self,
        result: BranchResult,
        race_name: str,
        dnr_expected: bool,
        present_tense: bool,
        car_number: int | None,
    ) -> str:
        # Who does this hint pertain to
        qualifier_str: str
        if not dnr_expected:
            # Normal
            match result:
                case BranchResult.WINNER:
                    qualifier_str = "Winner"
                case BranchResult.LOSER:
                    qualifier_str = "Loser"
                case _:
                    raise ValueError("The result needs to be a winner or a loser.")
        else:
            # DNR.
            if car_number is None:
                # Not provided, assume there are multiple competitors who DNR'd.
                qualifier_str = "Both"
            else:
                # A single car number was provided.
                qualifier_str = f"{car_number}"

        dnr_str = ""
        if dnr_expected:
            dnr_str = f" {'because' if present_tense else 'if'} DNR"

        return f"{qualifier_str} {self._direction} {race_name}{dnr_str}"

    @abstractmethod
    def update(self) -> None:
        pass

    def _dnr_likely_number(self, race:Race) -> Tuple[bool, int|None]:
        """Works out if a DNR is likely for the arrow and if so, should a car number be shown.

        Args:
            race (Race): The race to look at.

        Returns:
            Tuple[bool, int|None]: If a DNR is likely and whether the number should be shown.
        """
        # Is a DNR for this arrow likely and will it be one or both cars?
        dnr_likely = (
            race.get_expected_competitors(FillProbability.LIKELY) < 2
        )
        car_number: int | None = None
        options = race.get_options()
        if len(options) == 1:
            car_number = options[0].car_id
        
        return dnr_likely, car_number

class HintToArrow(HintArrow):
    """Class for a hint to arrow."""

    def __init__(
        self,
        sheet: KnockoutSheet,
        current_race: Race | Podium,
        x: float,
        y: float,
        result: BranchResult,
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
        sheet.canvas.create_line(points, arrow="last", smooth=True)
        text_handle = sheet.canvas.create_text(
            x + ARROW_WIDTH + SHORT_TEXT_MARGIN,
            y + ARROW_HEIGHT * flip,
            anchor=ttkc.W,
            font=(FONT, FONT_SMALL_SIZE),
        )
        super().__init__(sheet, text_handle, "to")
        self._result = result
        self._current_race = current_race
        self.update()

    def update(self) -> None:
        race_name: str | None = None
        assert isinstance(
            self._current_race, Race
        ), "The current race on the to arrow must be a Race, not a podium."

        match self._result:
            case BranchResult.WINNER:
                if self._current_race.winner_next_race is not None:
                    race_name = self._current_race.winner_next_race.name()
            case BranchResult.LOSER:
                if self._current_race.loser_next_race is not None:
                    race_name = self._current_race.loser_next_race.name()

            case _:
                raise LookupError("Only winning and loosing is allowed here.")

        if race_name is not None:
            # This arrow has something to point to.
            dnr_likely, car_number =self._dnr_likely_number(self._current_race)
            self._sheet.canvas.itemconfigure(
                self._text_handle,
                text=self._text(
                    result=self._result,
                    race_name=race_name,
                    dnr_expected=dnr_likely,
                    present_tense=self._current_race is None
                    or self._current_race.is_result_decided(),
                    car_number=car_number,
                ),
            )
        else:
            # This arrow has nowhere to point to.
            self._sheet.canvas.itemconfigure(
                self._text_handle, text="Race currently unused"
            )


class HintFromArrow(HintArrow):
    def __init__(
        self,
        sheet: KnockoutSheet,
        race_branch: RaceBranch | None,
        x: float,
        y: float,
    ) -> None:
        """Draws and arrow to show which race a competitor is coming from.

        Args:
            sheet (KnockoutSheet): The sheet to draw on.
            race_branch (RaceBranch | None): The branch to use.
            x (float): The x coordinate for the RIGHT side of the label.
            y (float): The y centre coordinate.
        """
        text_handle = self._draw(sheet, x, y)
        self._race_branch = race_branch
        super().__init__(sheet, text_handle, "from")
        self.update()

    def _draw(self, sheet: KnockoutSheet, x: float, y: float) -> int:
        """Draws the arrow. This is placed into its own method so that different styles may be used.

        Args:
            sheet (KnockoutSheet): The sheet to draw on (self._sheet is not defined yet).

        Returns:
            int: The handle of the text.
        """
        points = [x - ARROW_WIDTH - SHORT_TEXT_MARGIN, y, x - SHORT_TEXT_MARGIN, y]
        sheet.canvas.create_line(points, arrow="last", smooth=True)

        return sheet.canvas.create_text(
            x - ARROW_WIDTH - 2 * SHORT_TEXT_MARGIN,
            y,
            anchor=ttkc.E,
            font=(FONT, FONT_SMALL_SIZE),
        )

    def set_branch(self, branch: RaceBranch | None) -> None:
        """Sets the race branch if it has changed. This is most likely to occur for auxilliary races.

        Args:
            branch (RaceBranch): The race branch to update.
        """
        self._race_branch = branch

    def update(self) -> None:
        if self._race_branch is not None and self._race_branch.prev_race is not None:
            # We have a branch provided and it has a previous race. Act as normal.
            dnr_expected = self._race_branch.fill_probability(False)
            car_number : None | int = None
            if dnr_expected:
                options = self._race_branch.prev_race.get_options()
                if len(options) == 1:
                    car_number = options[0].car_id

            self._sheet.canvas.itemconfigure(
                self._text_handle,
                text=self._text(
                    result=self._race_branch.branch_result(),
                    race_name=self._race_branch.prev_race.name(),
                    dnr_expected=dnr_expected
                    == FillProbability.UNLIKELY,
                    present_tense=self._race_branch.prev_race.is_result_decided(),
                    car_number=car_number
                ),
            )
        else:
            # Not enough information provided. Put a blank message in.
            self._sheet.canvas.itemconfigure(self._text_handle, text="Currently empty")


class HintFromAboveArrow(HintFromArrow):
    """Class that draws a hint from arrow and placed the arrow above the
    prospective number box instead of the East."""

    def _draw(self, sheet: KnockoutSheet, x: float, y: float) -> int:
        arrow_x = x - SHORT_TEXT_MARGIN
        arrow_y = y
        text_x = arrow_x - 2 * ARROW_WIDTH / 3 + TEXT_MARGIN
        text_y = y - ARROW_HEIGHT - TEXT_MARGIN
        points = [
            text_x - SHORT_TEXT_MARGIN,
            text_y,
            arrow_x - 2 * ARROW_WIDTH / 3,
            text_y,
            arrow_x - ARROW_WIDTH,
            0.5 * (text_y + arrow_y),
            arrow_x - 2 * ARROW_WIDTH / 3,
            arrow_y,
            arrow_x,
            arrow_y,
        ]
        sheet.canvas.create_line(points, arrow="last", smooth=True)

        return sheet.canvas.create_text(
            text_x,
            text_y,
            anchor=ttkc.W,
            font=(FONT, FONT_SMALL_SIZE),
        )


class ShowFromArrow(Enum):
    HIDE = auto()
    TO_EAST = auto()
    TO_NORTH = auto()


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
        self._number_boxes: Tuple[Tuple[NumberBox, HintFromArrow | None], ...]
        self._lineset: BracketLineSet
        self._results_box: Tuple[NumberBox, HintFromArrow | None] | None = (
            None  # Only used if requested to show the results.
        )
        self._winner_to: HintToArrow | None = None
        self._loser_to: HintToArrow | None = None

    def draw_number(
        self,
        x: float,
        y: float,
        race_branch: RaceBranch | None,
        show_from_arrow: ShowFromArrow,
        override_type_editable: bool = False,
    ) -> Tuple[NumberBox, HintFromArrow | None]:
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
        # Draw the box for the number.
        number_box = self._numbers_factory.create(
            x=x,
            y=y,
            race_branch=race_branch,
            aux_race_manager=self._event.auxilliary_races,
            sheet=self._sheet,
            override_type_editable=override_type_editable,
        )

        # Draw the from hint.
        from_arrow: HintFromArrow | None = None
        match show_from_arrow:
            case ShowFromArrow.TO_EAST:
                from_arrow = HintFromArrow(self._sheet, race_branch, x, y)
            case ShowFromArrow.TO_NORTH:
                from_arrow = HintFromAboveArrow(self._sheet, race_branch, x, y)
            case ShowFromArrow.HIDE:
                pass
            case _:
                raise NotImplementedError("The requested direction is not set.")

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

        return number_box, from_arrow

    def draw_race(
        self,
        x: float,
        y_centre: float,
        y_spacing: float,
        columns_wide: int,
        race: Race,
        show_result_box: bool,
        show_from_arrow: Tuple[ShowFromArrow, ShowFromArrow] | Tuple[ShowFromArrow],
        show_winner_label: bool,
        show_loser_label: bool,
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
            show_from_arrow (Tuple[bool, bool]): Whether to show an arrow from the previous races.

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
            assert (
                len(show_from_arrow) == 2
            ), "The show_from_arrow tuple should be of length 2."
            self._number_boxes = (
                self.draw_number(x, top_y, race.left_branch, show_from_arrow[0]),
                self.draw_number(x, bottom_y, race.right_branch, show_from_arrow[1]),
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
            assert (
                len(show_from_arrow) >= 1
            ), "The show_from_arrow tuple should be at least of length 1. Only the first element is used."
            self._number_boxes = (
                self.draw_number(
                    x, y_centre, race.theoretical_winner(), show_from_arrow[0]
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
        if show_loser_label:
            self._loser_to = HintToArrow(
                self._sheet, race, arrow_x, y_centre + TEXT_MARGIN, BranchResult.LOSER
            )

        if show_winner_label:
            self._winner_to = HintToArrow(
                self._sheet,
                race,
                arrow_x,
                y_centre - TEXT_MARGIN,
                BranchResult.WINNER,
                -1,
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
                show_from_arrow=ShowFromArrow.HIDE,
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
        for (number_box, arrow), branch in zip(self._number_boxes, new_branches):
            number_box.set_race_branch(branch)
            if arrow is not None:
                arrow.set_branch(branch)

        self._lineset.update_branches(new_branches)

        # Update the output box.
        if self._results_box is not None:
            if race.winner_next_race is not None:
                # We can provide an actual branch.
                branch = race.winner_next_race.get_single_branch(race)
            else:
                # We can't provide an actual branch.
                branch = None

            number_box, arrow = self._results_box
            number_box.set_race_branch(branch)
            if arrow is not None:
                arrow.set_branch(branch)

    def update(self) -> None:
        """Updates the elements in the drawing of the race."""
        for number_box, arrow in self._number_boxes:
            number_box.update()
            if arrow is not None:
                arrow.update()

        if self._results_box is not None:
            number_box, arrow = self._results_box
            number_box.update()
            if arrow is not None:
                arrow.update()

        if self._winner_to is not None:
            self._winner_to.update()

        if self._loser_to is not None:
            self._loser_to.update()

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
            y_centre = self._box.y_pos + BRACKET_VERTICAL_SEPARATION + TEXT_MARGIN
            drawing.draw_race(
                x=top_left[0] + TEXT_MARGIN + ARROW_WIDTH,
                y_centre=y_centre,
                y_spacing=BRACKET_VERTICAL_SEPARATION,
                columns_wide=1,
                race=race,
                show_from_arrow=(ShowFromArrow.TO_NORTH, ShowFromArrow.TO_NORTH),
                show_winner_label=True,
                show_loser_label=False,
                show_result_box=True,
            )
            self._box.y_pos += 2 * BRACKET_VERTICAL_SEPARATION + TEXT_MARGIN

        self._event = event

    def update(self):
        for race, drawing in zip(self._event.auxilliary_races.races, self._races):
            drawing.assign_race(race)
            drawing.update()
