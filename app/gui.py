"""A GUI for the application.
Written by Jotham Gates, 20/10/2025"""
import tkinter as tk
from typing import Self
import ttkbootstrap as ttk
import ttkbootstrap.constants as ttkc
import ttkbootstrap.tableview as tableview
from abc import ABC, abstractmethod
import datetime
class AppTab(ABC):
    """Base class for tabs."""
    def __init__(self, root:ttk.Notebook, tab_name:str) -> None:
        """Creates a frame and adds it to the notebook with the provided name."""
        self._frame = ttk.Frame(root)
        root.add(self._frame, text=tab_name)

class EventsTab(AppTab):
    """Class to handle the events tab."""
    def __init__(self, root:ttk.Notebook) -> None:
        super().__init__(root, "Events")

        # Select event dropdown.
        ttk.Label(self._frame, text="Selected event").grid(row=0, column=0)
        event_list = ["2024 Test", "2025 Test", "2026 Test"]
        selected_event_str = tk.StringVar(self._frame, "")
        event_dropdown = ttk.OptionMenu(self._frame, selected_event_str, event_list[0], *event_list)
        event_dropdown.grid(row=0, column=1)

        # Add new event button.
        ttk.Button(self._frame, text="Add new event").grid(row=0, column=3)

        # Draw the table.
        columns = [
            {"text":"Event ID", "anchor":ttkc.CENTER},
            {"text":"Event name"},
            {"text":"Date"},
            {"text":"# cars"}
        ]

        rows = [
            (123, "2024 Test", datetime.date(2024, 10, 1)),
            (124, "2025 Test", datetime.date(2025, 10, 19)),
            (125, "2026 Test", datetime.date(2026, 10, 1)),
        ]

        dt = tableview.Tableview(self._frame, coldata=columns, rowdata=rows, paginated=True, searchable=True)
        dt.grid(row=1, column=0, columnspan=4)

        self._frame.columnconfigure(2, weight=1)
        self._frame.rowconfigure(1, weight=1)

class CarsTab(AppTab):
    """Class to handle the cars tab."""
    def __init__(self, root:ttk.Notebook) -> None:
        super().__init__(root, "Cars")

class RoundRobinTab(AppTab):
    """Class to handle the round robin tab."""
    def __init__(self, root:ttk.Notebook) -> None:
        super().__init__(root, "Round robin")

class KnockoutTab(AppTab):
    """Class to handle the knockout round tab."""
    def __init__(self, root:ttk.Notebook) -> None:
        super().__init__(root, "Knockout")

class Gui:
    def __init__(self) -> None:
        self._root = ttk.Window(title="Solar car draw generator", themename="cosmo")
        # self._root = tk.Tk()
        notebook = ttk.Notebook(self._root)
        self._events = EventsTab(notebook)
        self._cars = CarsTab(notebook)
        self._round_robin = RoundRobinTab(notebook)
        self._knockout = KnockoutTab(notebook)
        notebook.pack(expand=True, fill=ttkc.BOTH)

    def run(self) -> None:
        self._root.mainloop()