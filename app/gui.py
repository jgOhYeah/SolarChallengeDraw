"""A GUI for the application.
Written by Jotham Gates, 20/10/2025"""

import subprocess
import tkinter as tk
from typing import Callable, List, Self, Tuple, cast
import numpy as np
import ttkbootstrap as ttk
import ttkbootstrap.constants as ttkc
import ttkbootstrap.tableview as tableview
from abc import ABC, abstractmethod
import datetime
from knockout import KnockoutEvent, Race
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
        SCALE = 5
        self.width = 297 * SCALE
        self.height = 210 * SCALE
        self._canvas = ttk.Canvas(self._frame, width=self.width, height=self.height)

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

        self._canvas.bind(
            "<ButtonPress-1>", lambda event: self._canvas.scan_mark(event.x, event.y)
        )
        self._canvas.bind(
            "<B1-Motion>",
            lambda event: self._canvas.scan_dragto(event.x, event.y, gain=1),
        )
        self._canvas.bind(
            "<MouseWheel>", zoom_canvas(lambda e: 1.001**e.delta)
        )  # Windows zoom.
        self._canvas.bind("<4>", zoom_canvas(lambda _: 1.1))  # Unix zoom in.
        self._canvas.bind("<5>", zoom_canvas(lambda _: 0.9))  # Unix zoom out.

        self._canvas.pack(fill=ttkc.BOTH, expand=True)

    def draw(self, event: KnockoutEvent) -> None:
        """Draws the knockout event on the canvas.

        Args:
            event (KnockoutEvent): The event to plot.
        """
        HORIZONTAL_LINE_LENGTH = 20
        LABEL_WIDTH = 80
        LABEL_HEIGHT = 20
        TEXT_MARGIN = 10
        ROUND_WIDTH = 2 * HORIZONTAL_LINE_LENGTH + LABEL_WIDTH + 2 * TEXT_MARGIN
        INITIAL_SPACING = 55
        TEXT_LINE_HEIGHT = 12
        FONT = "Arial"
        FONT_SMALL_SIZE = 7
        FONT_NORMAL_SIZE = 10
        FONT_TITLE_SIZE = 15
        FONT_SUPTITLE_SIZE = 30
        LEFT_MARGIN = 10
        TOP_MARGIN = 10

        def draw_bracket_lines(
            x_start: float, x_end: float, y_centre: float, y_separation: float
        ) -> None:
            top_y = y_centre - y_separation / 2
            self._canvas.create_line(
                x_start, top_y, x_start + HORIZONTAL_LINE_LENGTH, top_y
            )
            bottom_y = y_centre + y_separation / 2
            self._canvas.create_line(
                x_start, bottom_y, x_start + HORIZONTAL_LINE_LENGTH, bottom_y
            )
            self._canvas.create_line(
                x_start + HORIZONTAL_LINE_LENGTH,
                top_y,
                x_start + HORIZONTAL_LINE_LENGTH,
                bottom_y,
            )
            self._canvas.create_line(
                x_start + HORIZONTAL_LINE_LENGTH, y_centre, x_end, y_centre
            )

        def draw_number(
            x: float, y: float, car: Car | None, prev_race: Race | None
        ) -> None:
            if car is None and prev_race is not None and prev_race.has_competitors():
                # Undecided, will be decided this round.
                current_var = tk.StringVar()
                values = (
                    [""]
                    + (
                        [f"{prev_race.left_car.car_id}"]
                        if prev_race.left_car is not None
                        else []
                    )
                    + (
                        [f"{prev_race.right_car.car_id}"]
                        if prev_race.right_car is not None
                        else []
                    )
                    + ["DNR"]
                )
                combobox = ttk.Combobox(
                    self._frame, textvariable=current_var, values=values
                )
                combobox["state"] = ttkc.READONLY
                self._canvas.create_window(
                    x,
                    y,
                    anchor=ttkc.W,
                    width=LABEL_WIDTH,
                    height=LABEL_HEIGHT,
                    window=combobox,
                )
            elif prev_race is not None and not prev_race.has_competitors():
                # Draw a placeholder box for now.
                self._canvas.create_rectangle(
                    x,
                    y - LABEL_HEIGHT / 2,
                    x + LABEL_WIDTH,
                    y + LABEL_HEIGHT / 2,
                    dash=5,
                )
            elif car is not None:
                # Car is specified. Print that.
                self._canvas.create_text(
                    x + LABEL_WIDTH,
                    y - TEXT_LINE_HEIGHT / 2,
                    anchor=ttkc.E,
                    width=LABEL_WIDTH,
                    text=car.car_id,
                    font=(FONT, FONT_NORMAL_SIZE),
                )
                self._canvas.create_text(
                    x + LABEL_WIDTH,
                    y + TEXT_LINE_HEIGHT / 2,
                    anchor=ttkc.E,
                    width=LABEL_WIDTH,
                    text=car.car_name,
                    font=(FONT, FONT_SMALL_SIZE, "italic"),
                )

        def draw_race(x: float, y_centre: float, y_spacing: float, race: Race) -> float:
            """Draws a race.

            Args:
                x (float): The x location of the left side of the race.
                y_centre (float): The centreline of the race.
                y_spacing (float): The spacing between the inputs of the race.
                race (Race): The race to draw.

            Returns:
                float: The x coordinate of the right side of the race.
            """
            line_x_start = x + LABEL_WIDTH + TEXT_MARGIN
            line_x_end = x + LABEL_WIDTH + TEXT_MARGIN + 2 * HORIZONTAL_LINE_LENGTH

            def draw_normal_race() -> None:
                top_y = y_centre - y_spacing / 2
                bottom_y = y_centre + y_spacing / 2
                assert not race.is_bye(), "Do not use draw_normal_race() for a bye."
                draw_number(x, top_y, cast(Car, race.left_car), race.left_prev_race)
                draw_number(
                    x, bottom_y, cast(Car, race.right_car), race.right_prev_race
                )
                draw_bracket_lines(
                    line_x_start,
                    line_x_end,
                    y_centre,
                    y_spacing,
                )

            def draw_bye() -> None:
                assert race.is_bye(), "Use draw_normal_race() for non-byes."
                draw_number(x, y_centre, race.bye_winner(), None)
                self._canvas.create_line(line_x_start, y_centre, line_x_end, y_centre)

            if race.is_bye():
                draw_bye()
            else:
                draw_normal_race()

            return line_x_end

        def draw_round(
            x: float, y_centre: float, y_spacing: float, round: List[Race]
        ) -> None:
            for i, race in enumerate(round):
                race_y_centre = (i + 0.5 - len(round) / 2) * y_spacing + y_centre
                draw_race(x, race_y_centre, y_spacing / 2, race)

        def draw_bracket(
            x: float,
            y_centre: float,
            y_spacing_initial: float,
            rounds: List[List[Race]],
        ) -> Tuple[float, float]:
            for i, round in enumerate(rounds):
                draw_round(
                    x + i * ROUND_WIDTH, y_centre, y_spacing_initial * (2**i), round
                )

            return x + len(rounds) * ROUND_WIDTH, y_centre

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
            offset = 0
            for i, round in enumerate(rounds):
                spacing = y_spacing_initial * (2 ** (i // 2))
                draw_round(x + i * ROUND_WIDTH, y_centre - offset, spacing, round)
                if i & 0x01 == 0x00:
                    offset += spacing / 4

            return x + len(rounds) * ROUND_WIDTH, y_centre - offset

        def draw_grand_final(
            winners_end: Tuple[float, float], losers_end: Tuple[float, float]
        ) -> None:
            """Draws the grand final and any extended lines from the previous rounds.

            Args:
                winners_end (Tuple[float, float]): The x and y coordinates of the end of the winners round.
                losers_end (Tuple[float, float]): The x and y coordinates of the end of the losers round.
            """
            # Main bracket.
            gf_y_centre = (winners_end[1] + losers_end[1]) / 2
            right_side = draw_race(
                max(winners_end[0], losers_end[0]),
                gf_y_centre,
                losers_end[1] - winners_end[1],
                event.grand_final,
            )

            # Extend the lines from the previous race if needed.
            if winners_end[0] < losers_end[0]:
                # We need to extend the winners' line (the usual?)
                self._canvas.create_line(
                    winners_end[0] - TEXT_MARGIN,
                    winners_end[1],
                    losers_end[0] - TEXT_MARGIN,
                    winners_end[1],
                )
            elif winners_end[0] > losers_end[0]:
                # We need to extend the losers' line (unheard of?)
                self._canvas.create_line(
                    losers_end[0] - TEXT_MARGIN,
                    losers_end[1],
                    winners_end[0] - TEXT_MARGIN,
                    losers_end[1],
                )

            # Add a results box.
            draw_number(
                right_side + TEXT_MARGIN, gf_y_centre, None, prev_race=event.grand_final
            )

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
                text="Winner's bracket",
                font=(FONT, FONT_TITLE_SIZE),
                anchor=ttkc.NW,
            )
        )
        winners_height = (len(event.winners_bracket[0]) - 1) * INITIAL_SPACING
        winners_centreline = (
            winners_title_bottom + TEXT_MARGIN + winners_height / 2 + LABEL_HEIGHT / 2
        )
        win_end = draw_bracket(
            LEFT_MARGIN, winners_centreline, INITIAL_SPACING, event.winners_bracket
        )

        # Losers' bracket
        winners_bottom = winners_centreline + winners_height / 2 + LABEL_HEIGHT
        _, _, _, losers_title_bottom = self._canvas.bbox(
            self._canvas.create_text(
                LEFT_MARGIN,
                winners_bottom + TEXT_MARGIN,
                text="Loser's bracket",
                font=(FONT, FONT_TITLE_SIZE),
                anchor=ttkc.NW,
            )
        )
        losers_height = (len(event.losers_bracket[0]) - 1) * INITIAL_SPACING
        losers_centreline = (
            losers_title_bottom + TEXT_MARGIN + losers_height / 2 + LABEL_HEIGHT / 2
        )
        lose_end = draw_losers_bracket(
            LEFT_MARGIN, losers_centreline, INITIAL_SPACING, event.losers_bracket
        )

        def mark_line(y: float) -> None:
            """Marks a y coordinate for debugging purposes."""
            self._canvas.create_line(0, y, self.width, y, fill="red")

        # Grand final
        draw_grand_final(win_end, lose_end)

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
            width=self.width,
            height=self.height,
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
