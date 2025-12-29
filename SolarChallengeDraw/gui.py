"""gui.py
A GUI for the application.
Written by Jotham Gates, 20/10/2025"""

from __future__ import annotations
from enum import Enum
import tkinter as tk
from typing import List
import ttkbootstrap as ttk
import ttkbootstrap.constants as ttkc
import ttkbootstrap.tableview as tableview
from abc import ABC, abstractmethod
import datetime
from car import Car
from knockout import KnockoutEvent
from knockout_sheet_elements import (
    InteractiveNumberBoxFactory,
    PrintNumberBoxFactory,
)
from knockout_sheet import KnockoutSheet
from file_picker import FilePicker
from save_load import JSONLoader


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

    def __init__(self, root: ttk.Notebook, ghostscript_path: str) -> None:
        super().__init__(root, "Knockout")
        self._ghostscript_path = ghostscript_path
        self.create_title_bar()
        self._export_pdf_filename = FilePicker(
            default_extension=".pdf",
            filetypes=(("PDF files", "*.pdf"),),
            initial_dir="./",
            initial_file="knockout_draw.pdf",
            title="Select a location to save the knockout draw in PDF fomat.",
        )
        self._json_loader = JSONLoader(filename="")
        self._export_json_filename = FilePicker(
            default_extension=".json",
            filetypes=(("JSON docs", "*.json"),),
            initial_dir="./",
            initial_file="knockout_draw.json",
            title="Select a location to save the knockout draw in JSON format."
        )
        # Create one canvas for display and another for printing with the different number entry boxes.
        self._gui_sheet = KnockoutSheet(self._frame, 1, 0)
        self._print_sheet = KnockoutSheet(self._frame, None, None)

    def draw_event(self, event: KnockoutEvent, cars:List[Car]) -> None:
        """Draws the event on screen and in the print canvas."""
        self._gui_sheet.draw_canvas(event, InteractiveNumberBoxFactory())
        self._print_sheet.draw_canvas(event, PrintNumberBoxFactory())
        self._json_loader.knockout = event
        self._json_loader.cars = cars

    class PaperSizes(Enum):
        """List of paper sizes in mm. Note that the aspect ration is currently always set for ISO A paper."""

        A4 = (297, 210)
        A3 = (420, 297)

    def create_title_bar(self) -> None:
        """Draws the title bar."""
        self._title_bar = ttk.Frame(self._frame)
        self._title_bar.grid(row=0, column=0, columnspan=2, sticky=ttkc.NSEW)
        self._title_bar.columnconfigure((0, 1), weight=1)
        ttk.Button(self._title_bar, text="Save as JSON", command=self._save_json).grid(
            row=0, column=0, sticky=ttkc.NSEW
        )
        ttk.Button(self._title_bar, text="Save PDF", command=self._export_pdf).grid(
            row=0, column=1, sticky=ttkc.NSEW
        )

    def _save_json(self) -> None:
        """Exports the event to a JSON file."""
        filename = self._export_json_filename.request()
        if filename is not None:
            # Writing to filename first avoids wiping the saved filename if the request is cancelled or fails.
            self._json_loader.filename = filename
            self._json_loader.save()

    def _export_pdf(self) -> None:
        """Exports the sheet."""
        filename = self._export_pdf_filename.request()
        if filename is not None:
            paper_size = KnockoutTab.PaperSizes.A3
            self._print_sheet.update()  # We only need to update the print sheet right before printing.
            self._print_sheet.export(
                ghostscript_path=self._ghostscript_path,
                output=filename,
                pdf_width_mm=paper_size.value[0],
                pdf_height_mm=paper_size.value[1],
                save_ps=False,
                generate_pdf=True,
            )


class Gui:
    def __init__(self, ghostscript_path: str) -> None:
        self._root = ttk.Window(title="Solar car draw generator", themename="cosmo")
        # self._root = tk.Tk()
        notebook = ttk.Notebook(self._root)
        # self._events = EventsTab(notebook)
        # self._cars = CarsTab(notebook)
        # self._round_robin = RoundRobinTab(notebook)
        self.knockout = KnockoutTab(notebook, ghostscript_path)
        notebook.pack(expand=True, fill=ttkc.BOTH)

    def run(self) -> None:
        self._root.mainloop()
        # pass
