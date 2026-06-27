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
from tkinter import messagebox as mb

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
from save_load import CarCSVLoader, JSONLoader, Loader

PAD_FULL = 10
PAD_HALF = 5


class AppTab(ABC):
    """Base class for tabs."""

    def __init__(self, root: ttk.Notebook, tab_name: str) -> None:
        """Creates a frame and adds it to the notebook with the provided name."""
        self._frame = ttk.Frame(root)
        root.add(self._frame, text=tab_name)
        self._tab_id = root.index("end") - 1
        self._root = root

    def _set_enable(self, enabled: bool) -> None:
        """Enables or disables the tab."""
        self._root.tab(self._tab_id, state=ttkc.NORMAL if enabled else ttkc.DISABLED)

    def _select_me(self) -> None:
        """Selects this tab."""
        self._root.select(self._tab_id)


class EventsTab(AppTab):
    """Class to handle the events tab."""

    def __init__(self, root: ttk.Notebook, gui: Gui) -> None:
        super().__init__(root, "Event")
        self._gui = gui
        ttk.Button(
            self._frame, text="Create new event from CSV", command=self._load_csv
        ).grid(
            row=0, column=0, sticky=ttkc.NSEW, padx=PAD_FULL, pady=(PAD_FULL, PAD_HALF)
        )
        ttk.Button(
            self._frame, text="Load existing event from JSON", command=self._load_json
        ).grid(
            row=1, column=0, sticky=ttkc.NSEW, padx=PAD_FULL, pady=(PAD_HALF, PAD_FULL)
        )
        self._frame.columnconfigure(0, weight=1)

    def _load_csv(self) -> None:
        if not self._gui.loaded or self._check_overwrite("list of cars"):
            filename = self._gui.csv_path.request(False)
            if filename is not None:
                self._gui.load_csv_from_path(filename)

    def _load_json(self) -> None:
        if not self._gui.loaded or self._check_overwrite("event"):
            filename = self._gui.json_path.request(False)
            if filename is not None:
                self._gui.load_json_from_path(filename)

    def _check_overwrite(self, new_item_name: str) -> bool:
        return mb.askyesno(
            title="Confirm load new event",
            message=f"An event is already loaded and there are potentially unsaved changes. Are you sure you wish to load a new {new_item_name}?",
        )


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

    def __init__(self, root: ttk.Notebook, ghostscript_path: str, gui: Gui) -> None:
        super().__init__(root, "Knockout")
        self._set_enable(False)
        self._ghostscript_path = ghostscript_path
        self._export_pdf_filename = FilePicker(
            default_extension=".pdf",
            filetypes=(("PDF files", "*.pdf"),),
            initial_dir="./",
            initial_file="knockout_draw.pdf",
            title="the knockout draw in PDF fomat.",
            read_only=False,
        )
        self._gui = gui
        self.create_title_bar()
        # Create one canvas for display and another for printing with the different number entry boxes.
        self._gui_sheet = KnockoutSheet(self._frame, 1, 0)
        self._print_sheet = KnockoutSheet(self._frame, None, None)

    def draw_event(self, event: KnockoutEvent, cars: List[Car]) -> None:
        """Draws the event on screen and in the print canvas."""
        self._gui_sheet.draw_canvas(event, InteractiveNumberBoxFactory())
        self._print_sheet.draw_canvas(event, PrintNumberBoxFactory())
        self._set_enable(True)
        self._select_me()

    class PaperSizes(Enum):
        """List of paper sizes in mm. Note that the aspect ration is currently always set for ISO A paper."""

        A4 = (297, 210)
        A3 = (420, 297)

    def create_title_bar(self) -> None:
        """Draws the title bar."""
        self._title_bar = ttk.Frame(self._frame)
        self._title_bar.grid(row=0, column=0, columnspan=2, sticky=ttkc.NSEW)
        self._title_bar.columnconfigure((0, 1), weight=1)
        ttk.Button(
            self._title_bar, text="Save as JSON", command=self._gui.save_event_as
        ).grid(
            row=0, column=0, sticky=ttkc.NSEW, padx=(PAD_FULL, PAD_HALF), pady=PAD_FULL
        )
        ttk.Button(self._title_bar, text="Save PDF", command=self._export_pdf).grid(
            row=0, column=1, sticky=ttkc.NSEW, padx=(PAD_HALF, PAD_FULL), pady=PAD_FULL
        )

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
    def __init__(
        self,
        ghostscript_path: str,
        initial_csv: str | None,
        initial_json: str | None,
    ) -> None:
        self._root = ttk.Window(title="Solar car draw generator", themename="cosmo")
        self.json_path = FilePicker(
            default_extension=".json",
            filetypes=(("JSON docs", "*.json"),),
            initial_dir="./",
            initial_file="knockout_draw.json",
            title="the knockout draw in JSON format.",
            initial_path=initial_json,
            read_only=False,
        )
        self._json_loader = JSONLoader()
        self.csv_path = FilePicker(
            default_extension=".csv",
            filetypes=(("CSV file", "*.csv"),),
            initial_dir="./",
            initial_file="",
            title="the cars to create a new event.",
            initial_path=initial_csv,
            read_only=True,
        )
        self._csv_loader = CarCSVLoader()
        self.loaded: bool = False  # Indicates whether an event is currently loaded.

        # Hotkey to save current file
        self._root.bind("<Control-s>", self.save_event)
        notebook = ttk.Notebook(self._root)
        self._events = EventsTab(notebook, gui=self)
        # self._cars = CarsTab(notebook)
        # self._round_robin = RoundRobinTab(notebook)
        self.knockout = KnockoutTab(notebook, ghostscript_path, self)
        notebook.pack(expand=True, fill=ttkc.BOTH)

        # Load the initial items if requested.
        if initial_csv is not None:
            print(f"Loading initial CSV: '{initial_csv}'.")
            self.load_csv_from_path(initial_csv)
        elif initial_json is not None:
            print(f"Loading initial JSON: '{initial_json}'.")
            self.load_json_from_path(initial_json)

    def load_csv_from_path(self, filename: str) -> None:
        self._csv_loader.filename = filename
        self._csv_loader.load()
        self.json_path.ok_to_save = False  # Invalidate the previous json file path.
        self.load_and_draw(self._csv_loader)

    def load_json_from_path(self, filename: str) -> None:
        self._json_loader.filename = filename
        self._json_loader.load()
        self.load_and_draw(self._json_loader)

    def load_and_draw(self, loader: Loader) -> None:
        self.loaded = True
        self.knockout.draw_event(loader.knockout, loader.cars)
        self._json_loader.copy_from(loader)

    def save_event(self, _) -> None:
        if self.loaded:
            # Ignore if nothing is loaded.
            if self.json_path.ok_to_save:
                # We can directly save.
                self._json_loader.save()
            else:
                # Need to perform a save as.
                self.save_event_as()

    def save_event_as(self) -> None:
        """Exports the event to a JSON file, asking for a new path first."""
        filename = self.json_path.request()
        if filename is not None:
            # Writing to filename first avoids wiping the saved filename if the request is cancelled or fails.
            self._json_loader.filename = filename
            self._json_loader.save()

    def run(self) -> None:
        self._root.mainloop()
        # pass
