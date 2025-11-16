"""knockout_sheet.py
Classes and tools to render a knockout event and export it as a PDF.
Written by Jotham Gates, 09/11/2025"""

from __future__ import annotations
from abc import ABC, abstractmethod
from enum import StrEnum
import os
import subprocess
import tkinter as tk
from typing import List, Literal, Tuple, cast
import numpy as np
import ttkbootstrap as ttk
import ttkbootstrap.constants as ttkc
from knockout import KnockoutEvent, Podium, Race, RaceBranch

# Settings
LEFT_MARGIN = 10
TOP_MARGIN = LEFT_MARGIN
RIGHT_MARGIN = LEFT_MARGIN
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

    def _get_options(self) -> List[str]:
        """Create a list of options for the menu.

        Returns:
            List[str]: A list of values to show in the dropdown.
        """
        if self._race_branch.prev_race is not None:
            values = self._race_branch.prev_race.get_options()
        else:
            values = []
        values = (
            [self.StrFixedOptions.EMPTY]
            + [f"{i.car_id}" for i in values]
            + [self.StrFixedOptions.DNR]
        )
        return values

    def _display_text(self) -> str:
        """Returns a string for the text that should be displayed in the box."""
        if self._race_branch.car is not None:
            text = f"{self._race_branch.car.car_id}"
        else:
            text = self.StrFixedOptions.EMPTY
        # TODO: Update for DNR.
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
        canvas.create_rectangle(
            x,
            y - LABEL_HEIGHT / 2,
            x + LABEL_WIDTH,
            y + LABEL_HEIGHT / 2,
            dash=(3, 3),
            fill="#fff",
        )
        self._text = canvas.create_text(
            x + LABEL_WIDTH / 2,
            y,
            anchor=ttkc.CENTER,
            text=self._display_text(),
            font=(FONT, FONT_NORMAL_SIZE),
        )

    def update(self, canvas: ttk.Canvas) -> None:
        canvas.itemconfigure(self._text, text=self._display_text())


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
        if race_branch.branch_type != RaceBranch.BranchType.FIXED:
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


class KnockoutSheet:
    """Class that draws and manages the knockout tree structure."""

    def __init__(
        self, frame: ttk.Frame, start_row: int | None, start_column: int | None
    ) -> None:
        self._frame = frame

        # Canvas to draw the draw on.
        SCALE = 1
        self._width = 297 * SCALE
        self._height = 210 * SCALE
        self._canvas = ttk.Canvas(self._frame, width=self._width, height=self._height)
        self._number_boxes: List[NumberBox] = []

        # Add to the screen.
        if start_row is not None and start_column is not None:
            self._setup_gui(start_row, start_column)

    def _setup_gui(self, start_row: int, start_column: int) -> None:
        """Sets up the canvas and adds scrolling.

        Args:
            start_row (int): The row to put the canvas in the grid of the frame.
            start_column (int): The column to put the canvas in the grid of the frame.
        """
        # Scrolling by clicking and dragging.
        self._canvas.bind(
            "<ButtonPress-1>", lambda event: self._canvas.scan_mark(event.x, event.y)
        )
        self._canvas.bind(
            "<B1-Motion>",
            lambda event: self._canvas.scan_dragto(event.x, event.y, gain=1),
        )

        # Linux scrolling using the mousewheel and trackpad.
        # Based on https://stackoverflow.com/questions/17355902/tkinter-binding-mousewheel-to-scrollbar
        # Scrolling up and down.
        self._canvas.bind("<4>", lambda event: self._canvas.yview_scroll(-1, "units"))
        self._canvas.bind("<5>", lambda event: self._canvas.yview_scroll(1, "units"))

        # Scrolling left and right.
        self._canvas.bind(
            "<Shift-4>", lambda event: self._canvas.xview_scroll(-1, "units")
        )
        self._canvas.bind(
            "<Shift-5>", lambda event: self._canvas.xview_scroll(1, "units")
        )

        # Windows scrolling using the mousewheel and trackpad. # TODO: Test
        self._canvas.bind(
            "<MouseWheel>",
            lambda event: self._canvas.yview_scroll(
                int(-1 * (event.delta / 120)), "units"
            ),
        )
        self._canvas.bind(
            "<Shift-MouseWheel>",
            lambda event: self._canvas.yview_scroll(
                int(-1 * (event.delta / 120)), "units"
            ),
        )

        # Scroll bars.
        # Based on https://stackoverflow.com/a/68723221
        self._x_scroll_bar = ttk.Scrollbar(
            self._frame, orient="horizontal", command=self._canvas.xview
        )
        self._y_scroll_bar = ttk.Scrollbar(
            self._frame, orient="vertical", command=self._canvas.yview
        )
        self._canvas.configure(
            yscrollcommand=self._y_scroll_bar.set, xscrollcommand=self._x_scroll_bar.set
        )
        self._canvas.configure(scrollregion=(0, 0, self._width, self._height))

        self._x_scroll_bar.grid(row=start_row + 1, column=start_column, sticky="ew")
        self._y_scroll_bar.grid(row=start_row, column=start_column + 1, sticky="ns")
        self._canvas.grid(row=start_row, column=start_column, sticky="nsew")
        self._frame.grid_rowconfigure(start_row, weight=1)
        self._frame.grid_columnconfigure(start_column, weight=1)

    def draw_canvas(
        self, event: KnockoutEvent, numbers: NumberBoxFactory, show_seed: bool = True
    ) -> None:
        """Draws the knockout event on the canvas.

        Args:
            event (KnockoutEvent): The event to plot.
        """
        self._clear()
        self.draw_tree(event, numbers, show_seed)
        self.draw_notes(event, self._width - RIGHT_MARGIN, self._height - BOTTOM_MARGIN)

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

    def draw_notes(self, event: KnockoutEvent, x: float, y: float) -> None:
        notes_box = KnockoutSheet.NotesBox(self._canvas, (x - 450, y - 300), (x, y))
        src_filename = os.path.join(os.path.dirname(__file__), "notes.md")
        notes_box.read_markdown(src_filename)
        notes_box.add_text(
            f"Rounds will be run in the following order:\n{event.calculate_play_order()}",
            bullet_point=True,
        )

    def draw_tree(
        self, event: KnockoutEvent, numbers: NumberBoxFactory, show_seed: bool = True
    ) -> None:
        """Draws the tree of the knockout event on the canvas."""

        def draw_bracket_lines(
            x_start: float, x_end: float, y_centre: float, y_separation: float
        ) -> None:
            top_y = y_centre - y_separation / 2
            tee_x = x_end - HORIZONTAL_LINE_LENGTH
            self._canvas.create_line(
                x_start, top_y, tee_x, top_y, width=BRACKET_LINE_THICKNESS
            )
            bottom_y = y_centre + y_separation / 2
            self._canvas.create_line(
                x_start, bottom_y, tee_x, bottom_y, width=BRACKET_LINE_THICKNESS
            )
            self._canvas.create_line(
                tee_x, top_y, tee_x, bottom_y, width=BRACKET_LINE_THICKNESS
            )
            self._canvas.create_line(
                tee_x, y_centre, x_end, y_centre, width=BRACKET_LINE_THICKNESS
            )

        def draw_number(x: float, y: float, race_branch: RaceBranch) -> None:
            # Draw the seed.
            if show_seed:
                self._canvas.create_text(
                    x + SHORT_TEXT_MARGIN,
                    y,
                    anchor=ttkc.W,
                    text=race_branch.seed,
                    fill="red",
                )
            self._number_boxes.append(
                numbers.create(self._canvas, x, y, race_branch, self)
            )

            # Arrow hinting where the competitor came from.
            show_label = False
            text = ""
            match race_branch.branch_result():
                case RaceBranch.BranchResult.WINNER:
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

                case RaceBranch.BranchResult.LOSER:
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
                draw_hint_from_arrow(
                    x - SHORT_TEXT_MARGIN, y, cast(Race, race_branch.prev_race), text
                )

        def draw_hint_to_arrow(
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
            self._canvas.create_line(points, arrow="last", smooth=True)
            if_dnr_text = ""
            if if_dnr:
                if_dnr_text = " if DNR"

            self._canvas.create_text(
                x + ARROW_WIDTH + SHORT_TEXT_MARGIN,
                y + ARROW_HEIGHT * flip,
                text=f"{result_name} to {to_race.name()}{if_dnr_text}",
                anchor=ttkc.W,
                font=(FONT, FONT_SMALL_SIZE),
            )

        def draw_hint_from_arrow(
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
            self._canvas.create_line(points, arrow="last", smooth=True)

            if_dnr_text = ""
            if if_dnr:
                if_dnr_text = " if DNR"

            text_left_x, _, _, _ = self._canvas.bbox(
                self._canvas.create_text(
                    x - ARROW_WIDTH - SHORT_TEXT_MARGIN,
                    y,
                    text=f"{result_name} from {from_race.name()}{if_dnr_text}",
                    anchor=ttkc.E,
                    font=(FONT, FONT_SMALL_SIZE),
                )
            )

        def draw_race(
            x: float, y_centre: float, y_spacing: float, columns_wide: int, race: Race
        ) -> float:
            """Draws a race.

            Args:
                x (float): The x location of the left side of the race.
                y_centre (float): The centreline of the race.
                y_spacing (float): The spacing between the inputs of the race.
                columns_wide (int): The number of columns wide to made the bracket.
                race (Race): The race to draw.

            Returns:
                float: The x coordinate of the right side of the race.
            """
            bracket_x_start = x + LABEL_WIDTH + TEXT_MARGIN
            bracket_x_end = (
                bracket_x_start
                + 2 * HORIZONTAL_LINE_LENGTH
                + (columns_wide - 1) * column_width
            )

            def draw_race_number(
                anchor: Literal["nw", "n", "ne", "w", "center", "e", "sw", "s", "se"],
            ) -> None:
                """Draws the race number."""
                self._canvas.create_text(
                    bracket_x_end - HORIZONTAL_LINE_LENGTH - SHORT_TEXT_MARGIN,
                    y_centre,
                    anchor=anchor,
                    text=race.name(),
                )

            def draw_normal_race() -> None:
                top_y = y_centre - y_spacing / 2
                bottom_y = y_centre + y_spacing / 2
                assert not race.is_bye(), f"Use {draw_bye.__name__}() for a bye."
                draw_number(
                    x,
                    top_y,
                    race.left_branch,
                )
                draw_number(
                    x,
                    bottom_y,
                    race.right_branch,
                )
                draw_bracket_lines(
                    bracket_x_start,
                    bracket_x_end,
                    y_centre,
                    y_spacing,
                )
                draw_race_number(ttkc.E)

            def draw_bye() -> None:
                assert race.is_bye(), f"Use {draw_normal_race.__name__}() for non-byes."
                draw_number(
                    x,
                    y_centre,
                    race.theoretical_winner(),
                )
                self._canvas.create_line(
                    bracket_x_start,
                    y_centre,
                    bracket_x_end,
                    y_centre,
                    width=BRACKET_LINE_THICKNESS,
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
                draw_hint_to_arrow(
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
                draw_hint_to_arrow(
                    arrow_x,
                    y_centre - TEXT_MARGIN,
                    race.winner_next_race,
                    "Winner",
                    race.is_bye(),
                    flip=-1,
                )

            # Extend the line into the next round if needed.
            return bracket_x_end + TEXT_MARGIN

        def round_height(round: List[Race], y_spacing: float) -> float:
            """Calculates the height of a round.

            Args:
                round (List[Race]): The round to look at.
                y_spacing (float): The y spacing between branches in the round.

            Returns:
                float: The height in pixels.
            """
            return (2 * len(round) - 1) * y_spacing / 2 + LABEL_HEIGHT

        def draw_round_box(
            x_end: float,
            y_centre: float,
            height: float,
            offset: float,
            next_round_height: float,
            next_round_offset: float,
            round_name: str,
        ) -> None:
            """Draws a box around a round in either the winners' or losers' brackets.

            Args:
                x (float): The left coordinate of the races in the round.
                y_centre (float): The y coordinate of the centreline of the round.
                y_spacing (float): The y spacing between branches in the round.
                round (List[Race]): The round itself.
                columns_wide (int): The number of columns wide to draw the round to make it line up correctly.
                round_name (str): Round name to print.

            Returns:
                float: The x coordinate of the right side of the races in the round.
            """
            # Draw the box and title.
            BOX_PADDING = 20
            BOX_FILL = "#cff9f3"
            TEXT_FILL = "#1E7B6D"
            box_centre = x_end - HORIZONTAL_LINE_LENGTH - TEXT_MARGIN
            box_half_width = HORIZONTAL_LINE_LENGTH + TEXT_MARGIN + BOX_PADDING
            next_round_top = y_centre - next_round_height / 2 - next_round_offset
            preferred_text_location = y_centre - (height / 2) - offset
            text_y_bottom = min(next_round_top, preferred_text_location) - TEXT_MARGIN

            _, text_y_top, _, _ = self._canvas.bbox(
                self._canvas.create_text(
                    box_centre,
                    text_y_bottom,
                    anchor=ttkc.S,
                    text=round_name,
                    width=2 * box_half_width - 2 * TEXT_MARGIN,
                    font=(FONT, FONT_NORMAL_SIZE, "bold"),
                    fill=TEXT_FILL,
                )
            )
            rect = self._canvas.create_rectangle(
                box_centre - box_half_width,
                text_y_top - TEXT_MARGIN,
                box_centre + box_half_width,
                y_centre - offset + (height / 2) + BOX_PADDING,
                width=0,
                fill=BOX_FILL,
                outline=BOX_FILL,
            )
            self._canvas.tag_lower(rect)

        def draw_round(
            x: float,
            y_centre: float,
            y_spacing: float,
            round: List[Race],
            columns_wide: int,
        ) -> float:
            """Draws a round in either the winners' or losers' brackets.

            Args:
                x (float): The left coordinate of the races in the round.
                y_centre (float): The y coordinate of the centreline of the round.
                y_spacing (float): The y spacing between branches in the round.
                round (List[Race]): The round itself.
                columns_wide (int): The number of columns wide to draw the round to make it line up correctly.

            Returns:
                float: The x coordinate of the right side of the races in the round.
            """
            # Draw the races
            x_end = -1.0
            for i, race in enumerate(round):
                race_y_centre = (i + 0.5 - len(round) / 2) * y_spacing + y_centre
                x_end = draw_race(x, race_y_centre, y_spacing / 2, columns_wide, race)

            return x_end

        def draw_winners_bracket(
            x: float,
            y_centre: float,
            y_spacing_initial: float,
            rounds: List[List[Race]],
        ) -> Tuple[float, float]:
            def y_spacing(index) -> float:
                return y_spacing_initial * (2**index)

            next_x = x
            for i, round in enumerate(rounds):
                # Make the round a single column wide for the first and second rounds, 2 for all subsequent to line up with the losers' round.
                cols_wide = 1 if i < 2 else 2
                next_x = draw_round(
                    next_x,
                    y_centre,
                    y_spacing(i),
                    round,
                    columns_wide=cols_wide,
                )
                draw_round_box(
                    next_x,
                    y_centre,
                    round_height(round, y_spacing(i)),
                    0,
                    (
                        0
                        if i + 1 == len(rounds)
                        else round_height(rounds[i + 1], y_spacing(i + 1))
                    ),
                    0,
                    f"P{i+1}",
                )

            return x + len(rounds) * column_width, y_centre

        def draw_losers_bracket(
            x: float,
            y_centre: float,
            y_spacing_initial: float,
            rounds: List[List[Race]],
        ) -> Tuple[float, float]:
            """Draws the losers bracket.

            Args:
                x (float): The initial x position for the left hand label.
                y_centre (float): The initial centre line in the first round.
                y_spacing_initial (float): The spacing in the first round.
                rounds (List[List[Race]]): The rounds to plot.

            Returns:
                Tuple[float, float]: The x coordinate at the end of the bracket and the centreline of the right hand side.
            """

            # TODO: Handle byes in the losers' round.
            def y_spacing(index: int) -> float:
                """Calculates the required spacing for a round."""
                return y_spacing_initial * (2 ** (index // 2))

            def y_offset(index: int) -> float:
                """Calculates the required offset for a round."""
                index += 1
                assert index >= 0, "Index shouldn't be negative."
                index &= 0xFFFE  # Round down to the nearest multiple of 2.
                if index == 0:
                    return 0
                else:
                    return y_spacing(index - 1) / 4 + y_offset(index - 2)

            next_x = x
            for i, round in enumerate(rounds):
                next_x = draw_round(
                    next_x,
                    y_centre - y_offset(i),
                    y_spacing(i),
                    round,
                    columns_wide=1,
                )
                draw_round_box(
                    next_x,
                    y_centre,
                    round_height(round, y_spacing(i)),
                    y_offset(i),
                    (
                        0
                        if i + 1 == len(rounds)
                        else round_height(rounds[i + 1], y_spacing(i + 1))
                    ),
                    y_offset(i + 1),
                    f"SC{i+1}",
                )

            return x + len(rounds) * column_width, y_centre - y_offset(len(rounds))

        def draw_grand_final(
            winners_end: Tuple[float, float], losers_end: Tuple[float, float]
        ) -> float:
            """Draws the grand final and any extended lines from the previous rounds.

            Args:
                winners_end (Tuple[float, float]): The x and y coordinates of the end of the winners round.
                losers_end (Tuple[float, float]): The x and y coordinates of the end of the losers round.

            Returns:
                float: The x coordinate of the right side of the label.
            """
            # Main bracket.
            gf_y_centre = (winners_end[1] + losers_end[1]) / 2
            gf_y_spacing = 2 * (losers_end[1] - winners_end[1])
            right_side = draw_round(
                max(winners_end[0], losers_end[0]),
                gf_y_centre,
                gf_y_spacing,
                [event.grand_final],
                1,
            )
            draw_round_box(
                right_side,
                gf_y_centre,
                round_height([event.grand_final], gf_y_spacing),
                0,
                0,
                0,
                f"Grand final",
            )

            # Add a results box.
            assert isinstance(
                event.grand_final.winner_next_race, Podium
            ), "The winner of the grand final must end up with a podium."
            draw_number(
                right_side, gf_y_centre, event.grand_final.winner_next_race.branch
            )

            return right_side + TEXT_MARGIN + LABEL_WIDTH

        # Titles
        _, _, _, suptitle_bottom = self._canvas.bbox(
            self._canvas.create_text(
                LEFT_MARGIN,
                TOP_MARGIN,
                text=event.name,
                font=(FONT, FONT_SUPTITLE_SIZE),
                anchor=ttkc.NW,
            )
        )

        # Winners' bracket.
        _, _, _, winners_title_bottom = self._canvas.bbox(
            self._canvas.create_text(
                LEFT_MARGIN,
                suptitle_bottom + TEXT_MARGIN,
                text="Primary draw",
                font=(FONT, FONT_TITLE_SIZE),
                anchor=ttkc.NW,
            )
        )
        winners_height = round_height(event.winners_bracket[0], WINNERS_INITIAL_SPACING)
        winners_centreline = (
            winners_title_bottom + TEXT_MARGIN + winners_height / 2 + LABEL_HEIGHT / 2
        )
        win_end = draw_winners_bracket(
            LEFT_MARGIN + FIRST_COLUMN_HINT_WIDTH,
            winners_centreline,
            WINNERS_INITIAL_SPACING,
            event.winners_bracket,
        )

        # Losers' bracket
        winners_bottom = (
            winners_centreline
            + winners_height / 2
            + LABEL_HEIGHT
            + BRACKET_VERTICAL_SEPARATION
        )
        _, _, _, losers_title_bottom = self._canvas.bbox(
            self._canvas.create_text(
                LEFT_MARGIN,
                winners_bottom + TEXT_MARGIN,
                text="Second chance draw",
                font=(FONT, FONT_TITLE_SIZE),
                anchor=ttkc.NW,
            )
        )
        losers_height = round_height(event.losers_bracket[0], LOSERS_INITIAL_SPACING)
        losers_centreline = (
            losers_title_bottom + TEXT_MARGIN + losers_height / 2 + LABEL_HEIGHT / 2
        )
        lose_end = draw_losers_bracket(
            LEFT_MARGIN + FIRST_COLUMN_HINT_WIDTH,
            losers_centreline,
            LOSERS_INITIAL_SPACING,
            event.losers_bracket,
        )

        def mark_line(y: float) -> None:
            """Marks a y coordinate for debugging purposes."""
            self._canvas.create_line(0, y, self._width, y, fill="red")

        # Grand final
        drawing_width = draw_grand_final(win_end, lose_end) + RIGHT_MARGIN
        drawing_height = (
            losers_centreline + losers_height / 2 + LABEL_HEIGHT + BOTTOM_MARGIN
        )
        self.set_size(self.a_paper_scale((drawing_width, drawing_height)))

    def update(self) -> None:
        """Updates each item on the sheet."""
        for box in self._number_boxes:
            box.update(self._canvas)

    def _clear(self) -> None:
        """Clears everything from the canvas.
        This may not be 100% memory leak free, so minimise the use of this."""
        self._canvas.delete("all")
        self._number_boxes.clear()

    def a_paper_scale(self, min_dimensions: Tuple[float, float]) -> Tuple[float, float]:
        """Calculates the minimum size in the A paper ratio."""
        min_width, min_height = min_dimensions
        height = max(min_height, min_width / np.sqrt(2))
        width = height * np.sqrt(2)
        return width, height

    def set_size(self, dimensions: Tuple[float, float]) -> None:
        """Sets the size of the canvas."""
        width, height = dimensions
        self._canvas.config(width=width, height=height)
        self._canvas.config(scrollregion=(0, 0, width, height))
        self._width = width
        self._height = height
        print(f"New size: {dimensions}")

    def export(
        self,
        ghostscript_path: str,
        output: str,
        pdf_width_mm: float,
        pdf_height_mm: float,
        save_ps: bool = False,
        generate_pdf: bool = True,
    ) -> None:
        """Exports the canvas as postscript to a file."""
        # Remove the extension if it is one we recognise.
        if output.lower().endswith(".pdf"):
            output = output[:-4]
        elif output.lower().endswith(".ps"):
            output = output[:-3]

        # Export as postscript.
        postscript_file = output + ".ps"
        pdf_file = output + ".pdf"
        self._canvas.update()
        postscript = cast(
            str,
            self._canvas.postscript(
                x=0,
                y=0,
                width=self._width,
                height=self._height,
                pagewidth=297,
                pageheight=210,
                pageanchor=ttkc.NE,
            ),
        ).encode()

        if save_ps:
            # We need to save the postscript file.
            with open(postscript_file, "wb") as file:
                file.write(postscript)

        if generate_pdf:
            # We need to generate the PDF.
            def mm_to_pt(mm: float) -> float:
                """Converts mm to post script points (1/72")"""
                return mm * 72 / 25.4

            args = [
                ghostscript_path,
                "-dNOPAUSE",
                "-dBATCH",
                "-dSAFER",
                "-sDEVICE=pdfwrite",
                f"-sOutputFile={pdf_file}",
                f"-dDEVICEWIDTHPOINTS={mm_to_pt(pdf_width_mm):f}",
                f"-dDEVICEHEIGHTPOINTS={mm_to_pt(pdf_height_mm):f}",
                "-dFitPage",
                "-",
            ]
            print(" ".join(args))
            process = subprocess.Popen(args, stdin=subprocess.PIPE)
            process.communicate(postscript, timeout=30)
            process.wait()
