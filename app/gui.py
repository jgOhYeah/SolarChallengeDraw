"""A GUI for the application.
Written by Jotham Gates, 20/10/2025"""

import tkinter as tk
from typing import List, Self, cast
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
        SCALE = 7
        self.width = 210 * SCALE
        self.height = 297 * SCALE
        self._canvas = ttk.Canvas(self._frame, width=self.width, height=self.height)
        self._canvas.pack(fill=ttkc.BOTH, expand=True)

    def draw(self, event: KnockoutEvent) -> None:
        """Draws the knockout event on the canvas.

        Args:
            event (KnockoutEvent): The event to plot.
        """
        HORIZONTAL_LINE_LENGTH = 20
        LABEL_WIDTH = 80
        TEXT_MARGIN = 10
        ROUND_WIDTH = 2 * HORIZONTAL_LINE_LENGTH + LABEL_WIDTH + 2 * TEXT_MARGIN
        INITIAL_SPACING = 55
        TEXT_LINE_HEIGHT = 12

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

        def draw_race(x: float, y_centre: float, y_spacing: float, race: Race) -> None:
            def draw_number(y, car: Car, prev_race: Race | None) -> None:
                if car is None and prev_race.has_competitors():
                    # Undecided, will be decided this round.
                    # TODO: Populate with options from the previous race.
                    current_var = tk.StringVar()
                    values = (
                            [""]
                        +
                        (
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
                        x, y, anchor=ttkc.W, width=LABEL_WIDTH, window=combobox
                    )
                elif prev_race is not None and not prev_race.has_competitors():
                    # Draw a placeholder box for now.
                    PLACEHOLDER_HEIGHT = 30
                    self._canvas.create_rectangle(
                        x, y-PLACEHOLDER_HEIGHT/2, x+LABEL_WIDTH, y+PLACEHOLDER_HEIGHT/2,
                        dash=5
                    )
                elif car is not None:
                    # Car is specified. Print that.
                    self._canvas.create_text(
                        x + LABEL_WIDTH,
                        y - TEXT_LINE_HEIGHT / 2,
                        anchor=ttkc.E,
                        width=LABEL_WIDTH,
                        text=car.car_id,
                    )
                    self._canvas.create_text(
                        x + LABEL_WIDTH,
                        y + TEXT_LINE_HEIGHT / 2,
                        anchor=ttkc.E,
                        width=LABEL_WIDTH,
                        text=car.car_name,
                        font=("", 7, "italic"),
                    )

            line_x_start = x + LABEL_WIDTH + TEXT_MARGIN
            line_x_end = x + LABEL_WIDTH + TEXT_MARGIN + 2 * HORIZONTAL_LINE_LENGTH

            def draw_normal_race() -> None:
                top_y = y_centre - y_spacing / 2
                bottom_y = y_centre + y_spacing / 2
                assert not race.is_bye(), "Do not use draw_normal_race() for a bye."
                draw_number(top_y, cast(Car, race.left_car), race.left_prev_race)
                draw_number(bottom_y, cast(Car, race.right_car), race.right_prev_race)
                draw_bracket_lines(
                    line_x_start,
                    line_x_end,
                    y_centre,
                    y_spacing,
                )

            def draw_bye() -> None:
                assert race.is_bye(), "Use draw_normal_race() for non-byes."
                draw_number(y_centre, race.bye_winner(), None)
                self._canvas.create_line(line_x_start, y_centre, line_x_end, y_centre)

            if race.is_bye():
                draw_bye()
            else:
                draw_normal_race()

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
        ) -> None:
            for i, round in enumerate(rounds):
                draw_round(
                    x + i * ROUND_WIDTH, y_centre, y_spacing_initial * (2**i), round
                )

        draw_bracket(10, self.height / 3, INITIAL_SPACING, event.winners_bracket)
        # TODO: Sort out spacing between winner's and loser's brackets.
        # TODO: Handle drawing repecharge rounds.
        # draw_bracket(10, 2*self.height / 3, INITIAL_SPACING, event.losers_bracket)
    def export(self, output: str) -> None:
        """Exports the canvas as postscript to a file."""
        self._canvas.update()
        self._canvas.postscript(file=output)


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
