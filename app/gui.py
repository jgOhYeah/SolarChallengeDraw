"""A GUI for the application.
Written by Jotham Gates, 20/10/2025"""

from __future__ import annotations
from enum import StrEnum
import os
import subprocess
import tkinter as tk
from typing import Callable, List, Literal, Tuple, cast
import numpy as np
import ttkbootstrap as ttk
import ttkbootstrap.constants as ttkc
import ttkbootstrap.tableview as tableview
from abc import ABC, abstractmethod
import datetime
from knockout import KnockoutEvent, Podium, Race, RaceBranch
from car import Car


class AppTab(ABC):
    """Base class for tabs."""

    def __init__(self, root: ttk.Notebook, tab_name: str) -> None:
        """Creates a frame and adds it to the notebook with the provided name."""
        self._frame = ttk.Frame(root)
        root.add(self._frame, text=tab_name)


class EventsTab(AppTab):
    """Class to handle the events tab."""

    def __init__(self, root: ttk.Notebook) -> None:
        super().__init__(root, "Events")

        # Select event dropdown.
        ttk.Label(self._frame, text="Selected event").grid(row=0, column=0)
        event_list = ["2024 Test", "2025 Test", "2026 Test"]
        selected_event_str = tk.StringVar(self._frame, "")
        event_dropdown = ttk.OptionMenu(
            self._frame, selected_event_str, event_list[0], *event_list
        )
        event_dropdown.grid(row=0, column=1)

        # Add new event button.
        ttk.Button(self._frame, text="Add new event").grid(row=0, column=3)

        # Draw the table.
        columns = [
            {"text": "Event ID", "anchor": ttkc.CENTER},
            {"text": "Event name"},
            {"text": "Date"},
            {"text": "# cars"},
        ]

        rows = [
            (123, "2024 Test", datetime.date(2024, 10, 1)),
            (124, "2025 Test", datetime.date(2025, 10, 19)),
            (125, "2026 Test", datetime.date(2026, 10, 1)),
        ]

        dt = tableview.Tableview(
            self._frame, coldata=columns, rowdata=rows, paginated=True, searchable=True
        )
        dt.grid(row=1, column=0, columnspan=4)

        self._frame.columnconfigure(2, weight=1)
        self._frame.rowconfigure(1, weight=1)


class CarsTab(AppTab):
    """Class to handle the cars tab."""

    def __init__(self, root: ttk.Notebook) -> None:
        super().__init__(root, "Cars")


class RoundRobinTab(AppTab):
    """Class to handle the round robin tab."""

    def __init__(self, root: ttk.Notebook) -> None:
        super().__init__(root, "Round robin")


class KnockoutTab(AppTab):
    """Class to handle the knockout round tab."""

    def __init__(self, root: ttk.Notebook) -> None:
        super().__init__(root, "Knockout")

        # Canvas to draw the draw on.
        SCALE = 1
        self._width = 297 * SCALE
        self._height = 210 * SCALE
        self._canvas = ttk.Canvas(self._frame, width=self._width, height=self._height)

        # Setup pan and zoom
        # Based on https://stackoverflow.com/a/60149696
        def zoom_canvas(factor_func: Callable) -> Callable:
            """Creates a function that will zoom the canvas.

            Args:
                factor_func (Callable[[tk.Event[tk.Canvas]], float]): Function that will calculate the scaling factor.

            Returns:
                Callable[[tk.Event[tk.Canvas]], None]: Function that will scale the canvas.
            """

            def do_zoom(event) -> None:
                x = self._canvas.canvasx(event.x)
                y = self._canvas.canvasy(event.y)
                factor = factor_func(event)
                # factor = 1.001 ** event.delta
                self._canvas.scale(tk.ALL, x, y, factor, factor)

            return do_zoom

        # self._canvas.bind(
        #     "<MouseWheel>", zoom_canvas(lambda e: 1.001**e.delta)
        # )  # Windows zoom.
        # self._canvas.bind("<4>", zoom_canvas(lambda _: 1.1))  # Unix zoom in.
        # self._canvas.bind("<5>", zoom_canvas(lambda _: 0.9))  # Unix zoom out.

        # Scrolling
        self._canvas.bind(
            "<ButtonPress-1>", lambda event: self._canvas.scan_mark(event.x, event.y)
        )
        self._canvas.bind(
            "<B1-Motion>",
            lambda event: self._canvas.scan_dragto(event.x, event.y, gain=1),
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

        self._x_scroll_bar.grid(row=1, column=0, sticky="ew")
        self._y_scroll_bar.grid(row=0, column=1, sticky="ns")
        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._frame.grid_rowconfigure(0, weight=1)
        self._frame.grid_columnconfigure(0, weight=1)

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

    def draw(
        self, event: KnockoutEvent, show_seed: bool = True, interactive: bool = True
    ) -> None:
        """Draws the knockout event on the canvas.

        Args:
            event (KnockoutEvent): The event to plot.
        """
        self.draw_tree(event, show_seed, interactive)
        self.draw_notes(
            self._width - self.RIGHT_MARGIN, self._height - self.BOTTOM_MARGIN
        )

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
            self._y_pos: float = self._top_left[1] + KnockoutTab.TEXT_MARGIN

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
                font = (KnockoutTab.FONT, KnockoutTab.FONT_NORMAL_SIZE)

            # Positions and widths
            # Defaults for no bullet point.
            left = self._top_left[0] + KnockoutTab.TEXT_MARGIN
            text_width = (
                self._bottom_right[0] - self._top_left[0] - 2 * KnockoutTab.TEXT_MARGIN
            )
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
            font = (KnockoutTab.FONT, KnockoutTab.FONT_NORMAL_SIZE)
            bullet = False
            if line.startswith("#"):
                # Title.
                font = (KnockoutTab.FONT, KnockoutTab.FONT_TITLE_SIZE)
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

    def draw_notes(self, x: float, y: float) -> None:
        notes_box = KnockoutTab.NotesBox(self._canvas, (x - 500, y - 200), (x, y))
        src_filename = os.path.join(os.path.dirname(__file__), "notes.md")
        notes_box.read_markdown(src_filename)

    def draw_tree(
        self, event: KnockoutEvent, show_seed: bool = True, interactive: bool = True
    ) -> None:
        """Draws the tree of the knockout event on the canvas."""
        HORIZONTAL_LINE_LENGTH = 20
        LABEL_WIDTH = 100
        LABEL_HEIGHT = 30
        SHORT_TEXT_MARGIN = self.TEXT_MARGIN / 2
        WINNERS_INITIAL_SPACING = 55
        LOSERS_INITIAL_SPACING = 80
        TEXT_LINE_HEIGHT = 12
        ARROW_HEIGHT = 15
        ARROW_WIDTH = 20
        BRACKET_VERTICAL_SEPARATION = 50
        FIRST_COLUMN_HINT_WIDTH = LABEL_WIDTH
        column_width = LABEL_WIDTH + 2 * self.TEXT_MARGIN + 2 * HORIZONTAL_LINE_LENGTH

        def draw_bracket_lines(
            x_start: float, x_end: float, y_centre: float, y_separation: float
        ) -> None:
            top_y = y_centre - y_separation / 2
            tee_x = x_end - HORIZONTAL_LINE_LENGTH
            self._canvas.create_line(x_start, top_y, tee_x, top_y)
            bottom_y = y_centre + y_separation / 2
            self._canvas.create_line(x_start, bottom_y, tee_x, bottom_y)
            self._canvas.create_line(
                tee_x,
                top_y,
                tee_x,
                bottom_y,
            )
            self._canvas.create_line(tee_x, y_centre, x_end, y_centre)

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
            if race_branch.branch_type != RaceBranch.BranchType.FIXED:
                # Show a combobox (may need to be non-editable).
                # Create a list of options for the menu.
                current_var = tk.StringVar()

                class StrFixedOptions(StrEnum):
                    EMPTY = ""
                    DNR = "DNR"

                if race_branch.prev_race is not None:
                    values = race_branch.prev_race.get_options()
                else:
                    values = []
                values = (
                    [StrFixedOptions.EMPTY]
                    + [f"{i.car_id}" for i in values]
                    + [StrFixedOptions.DNR]
                )

                def validate(selected: str) -> bool:
                    """Validates the currently selected combobox and updates the races.

                    Args:
                        selected (str): The currently selected value.

                    Returns:
                        bool: Whether the option is valid.
                    """
                    if selected in values:
                        assert (
                            race_branch.prev_race is not None
                        ), "There should be a previous race to select values from."
                        match selected:
                            case StrFixedOptions.EMPTY:
                                race_branch.prev_race.set_winner(Race.WINNER_EMPTY)
                            case StrFixedOptions.DNR:
                                race_branch.prev_race.set_winner(Race.WINNER_DNR)
                            case _:
                                number = int(selected)
                                race_branch.prev_race.set_winner(number)

                        # TODO: Update instead of redrawing.
                        self.clear()
                        self.draw(event, show_seed, interactive)
                        event.print()
                        return True
                    else:
                        # The user somehow put an invalid number in.
                        return False

                combobox = ttk.Combobox(
                    self._frame,
                    values=values,
                    validate="focusin",
                    validatecommand=(self._frame.register(validate), "%P"),
                    state=(
                        ttkc.NORMAL if race_branch.is_editable() else ttkc.DISABLED
                    ),  # TODO: Check.
                )

                # Show the current car if needed.
                if race_branch.car is not None:
                    combobox.current(values.index(f"{race_branch.car.car_id}"))

                self._canvas.create_window(
                    x,
                    y,
                    anchor=ttkc.W,
                    width=LABEL_WIDTH,
                    height=LABEL_HEIGHT,
                    window=combobox,
                )
            elif race_branch.car is not None:
                # Show the numbers as not a dropdown at all.
                self._canvas.create_text(
                    x + LABEL_WIDTH,
                    y - TEXT_LINE_HEIGHT / 2,
                    anchor=ttkc.E,
                    width=LABEL_WIDTH,
                    text=race_branch.car.car_id,
                    font=(self.FONT, self.FONT_NORMAL_SIZE),
                )
                self._canvas.create_text(
                    x + LABEL_WIDTH,
                    y + TEXT_LINE_HEIGHT / 2,
                    anchor=ttkc.E,
                    width=LABEL_WIDTH,
                    text=race_branch.car.car_name,
                    font=(self.FONT, self.FONT_SMALL_SIZE, "italic"),
                )
            else:
                raise NotImplementedError("Does this bit need an implementation???")

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
                font=(self.FONT, self.FONT_SMALL_SIZE),
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
                    font=(self.FONT, self.FONT_SMALL_SIZE),
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
            bracket_x_start = x + LABEL_WIDTH + self.TEXT_MARGIN
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
                    bracket_x_start, y_centre, bracket_x_end, y_centre
                )
                draw_race_number(ttkc.SE)

            if race.is_bye():
                draw_bye()
            else:
                draw_normal_race()

            # Arrows going from the race.
            arrow_x = bracket_x_end - HORIZONTAL_LINE_LENGTH + self.TEXT_MARGIN
            if race.loser_show_label:
                assert (
                    race.loser_next_race is not None
                ), "Show label is True for losers, but no losers to show."
                draw_hint_to_arrow(
                    arrow_x,
                    y_centre + self.TEXT_MARGIN,
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
                    y_centre - self.TEXT_MARGIN,
                    race.winner_next_race,
                    "Winner",
                    race.is_bye(),
                    flip=-1,
                )

            # Extend the line into the next round if needed.
            return bracket_x_end + self.TEXT_MARGIN

        def draw_round(
            x: float,
            y_centre: float,
            y_spacing: float,
            round: List[Race],
            columns_wide: int,
        ) -> float:
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
            next_x = x
            for i, round in enumerate(rounds):
                # Make the round a single column wide for the first and second rounds, 2 for all subsequent to line up with the losers' round.
                cols_wide = 1 if i < 2 else 2
                next_x = draw_round(
                    next_x,
                    y_centre,
                    y_spacing_initial * (2**i),
                    round,
                    columns_wide=cols_wide,
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
            offset = 0
            for i, round in enumerate(rounds):
                spacing = y_spacing_initial * (2 ** (i // 2))
                draw_round(
                    x + i * column_width,
                    y_centre - offset,
                    spacing,
                    round,
                    columns_wide=1,
                )
                if i & 0x01 == 0x00:
                    # Reduction (non-repecharge) round.
                    offset += spacing / 4

            return x + len(rounds) * column_width, y_centre - offset

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
            right_side = draw_race(
                max(winners_end[0], losers_end[0]),
                gf_y_centre,
                losers_end[1] - winners_end[1],
                1,
                event.grand_final,
            )

            # Add a results box.
            assert isinstance(
                event.grand_final.winner_next_race, Podium
            ), "The winner of the grand final must end up with a podium."
            draw_number(
                right_side, gf_y_centre, event.grand_final.winner_next_race.branch
            )

            return right_side + self.TEXT_MARGIN + LABEL_WIDTH

        # Titles
        _, _, _, suptitle_bottom = self._canvas.bbox(
            self._canvas.create_text(
                self.LEFT_MARGIN,
                self.TOP_MARGIN,
                text=event.name,
                font=(self.FONT, self.FONT_SUPTITLE_SIZE),
                anchor=ttkc.NW,
            )
        )

        # Winners' bracket.
        _, _, _, winners_title_bottom = self._canvas.bbox(
            self._canvas.create_text(
                self.LEFT_MARGIN,
                suptitle_bottom + self.TEXT_MARGIN,
                text="Winner's bracket",
                font=(self.FONT, self.FONT_TITLE_SIZE),
                anchor=ttkc.NW,
            )
        )
        winners_height = (len(event.winners_bracket[0]) - 1) * WINNERS_INITIAL_SPACING
        winners_centreline = (
            winners_title_bottom
            + self.TEXT_MARGIN
            + winners_height / 2
            + LABEL_HEIGHT / 2
        )
        win_end = draw_winners_bracket(
            self.LEFT_MARGIN + FIRST_COLUMN_HINT_WIDTH,
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
                self.LEFT_MARGIN,
                winners_bottom + self.TEXT_MARGIN,
                text="Loser's bracket",
                font=(self.FONT, self.FONT_TITLE_SIZE),
                anchor=ttkc.NW,
            )
        )
        losers_height = (len(event.losers_bracket[0]) - 1) * LOSERS_INITIAL_SPACING
        losers_centreline = (
            losers_title_bottom
            + self.TEXT_MARGIN
            + losers_height / 2
            + LABEL_HEIGHT / 2
        )
        lose_end = draw_losers_bracket(
            self.LEFT_MARGIN + FIRST_COLUMN_HINT_WIDTH,
            losers_centreline,
            LOSERS_INITIAL_SPACING,
            event.losers_bracket,
        )

        def mark_line(y: float) -> None:
            """Marks a y coordinate for debugging purposes."""
            self._canvas.create_line(0, y, self._width, y, fill="red")

        # Grand final
        drawing_width = draw_grand_final(win_end, lose_end) + self.RIGHT_MARGIN
        drawing_height = (
            losers_centreline + losers_height / 2 + LABEL_HEIGHT + self.BOTTOM_MARGIN
        )
        self.set_size(self.a_paper_scale((drawing_width, drawing_height)))

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

    def clear(self) -> None:
        self._canvas.delete("all")

    def export(self, output: str, generate_pdf: bool = True) -> None:
        """Exports the canvas as postscript to a file."""
        # Remove the extension if it is one we recognise.
        if output.lower().endswith(".pdf"):
            output = output[:-4]
        elif output.lower().endswith(".ps"):
            output = output[:-3]

        # Export as postscript.
        postscript_file = output + ".ps"
        self._canvas.update()
        self._canvas.postscript(
            file=postscript_file,
            x=0,
            y=0,
            width=self._width,
            height=self._height,
            pagewidth=297,
            pageheight=210,
        )

        # Convert to a pdf
        if generate_pdf:
            process = subprocess.Popen(
                ["ps2pdf", "-dEPSCrop", postscript_file], shell=False
            )
            process.wait()


class Gui:
    def __init__(self) -> None:
        self._root = ttk.Window(title="Solar car draw generator", themename="cosmo")
        # self._root = tk.Tk()
        notebook = ttk.Notebook(self._root)
        # self._events = EventsTab(notebook)
        # self._cars = CarsTab(notebook)
        # self._round_robin = RoundRobinTab(notebook)
        self.knockout = KnockoutTab(notebook)
        notebook.pack(expand=True, fill=ttkc.BOTH)

    def run(self) -> None:
        self._root.mainloop()
        # pass
