"""A GUI for the application.
Written by Jotham Gates, 20/10/2025"""

import tkinter as tk
from typing import List, Self
import ttkbootstrap as ttk
import ttkbootstrap.constants as ttkc
import ttkbootstrap.tableview as tableview
from abc import ABC, abstractmethod
import datetime
from knockout import KnockoutEvent, Race


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
        scale = 2.5
        self.width = 297 * scale
        self.height = 210 * scale
        self._canvas = ttk.Canvas(self._frame, width=self.width, height=self.height)
        self._canvas.pack(fill=ttkc.BOTH, expand=True)

    def draw(self, event: KnockoutEvent) -> None:
        """Draws the knockout event on the canvas.

        Args:
            event (KnockoutEvent): The event to plot.
        """
        HORIZONTAL_LINE_LENGTH = 20
        LABEL_WIDTH = 20
        TEXT_WEST_MARGIN = 10
        ROUND_WIDTH = 2*HORIZONTAL_LINE_LENGTH+LABEL_WIDTH+TEXT_WEST_MARGIN
        INITIAL_SPACING = 50
        def draw_bracket_lines(
            x_start: float, x_end: float, y_centre: float, y_separation: float
        ) -> None:
            top_y = y_centre - y_separation / 2
            self._canvas.create_line(x_start, top_y, x_start + HORIZONTAL_LINE_LENGTH, top_y)
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
            top_y = y_centre - y_spacing / 2
            bottom_y = y_centre + y_spacing / 2
            self._canvas.create_text(
                x, top_y, anchor=ttkc.W, width=LABEL_WIDTH, text=race.left_seed
            )
            self._canvas.create_text(
                x, bottom_y, anchor=ttkc.W, width=LABEL_WIDTH, text=race.right_seed
            )
            draw_bracket_lines(x + LABEL_WIDTH, x + LABEL_WIDTH + 2*HORIZONTAL_LINE_LENGTH, y_centre, y_spacing)

        def draw_round(
            x: float, y_centre: float, y_spacing: float, round: List[Race]
        ) -> None:
            for i, race in enumerate(round):
                race_y_centre = (i + 0.5 - len(round) / 2) * y_spacing + y_centre
                draw_race(x, race_y_centre, y_spacing/2, race)

        def draw_bracket(
                x:float, y_centre: float, y_spacing_initial: float, rounds: List[List[Race]]
        ) -> None:
            for i, round in enumerate(rounds):
                draw_round(x+i*ROUND_WIDTH, y_centre, y_spacing_initial*(2**i), round)
        # draw_bracket(10, 200, self._canvas.winfo_reqheight() / 3, 100)
        # draw_race(10, 300, 150, event.grand_final)
        # draw_round(10, self.height/2, 50, event.winners_bracket[0])
        draw_bracket(10, self.height/2, INITIAL_SPACING, event.winners_bracket)

    def export(self, output:str) -> None:
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
