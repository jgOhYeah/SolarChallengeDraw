"""file_picker.py
Class that adds memory to file picking.
Written by Jotham Gates, 11/11/2025"""

import os
import tkinter as tk
import tkinter.filedialog as filedialog
from typing import Iterable, List
import ttkbootstrap.constants as ttkc


class FilePicker:
    """Class that remembers the last file path selected."""

    def __init__(
        self,
        default_extension: str,
        filetypes: Iterable[tuple[str, str | list[str] | tuple[str, ...]]] | None,
        initial_dir: str,
        initial_file: str,
        title: str,
    ) -> None:
        self._default_extension = default_extension
        self._filetypes = filetypes
        self._initial_dir = initial_dir
        self._initial_file = initial_file
        self._title = title

    def request(self) -> str | None:
        """Opens the dialog.

        Returns:
            str: The string to save as.
        """
        path = filedialog.asksaveasfilename(
            defaultextension=self._default_extension,
            filetypes=self._filetypes,
            initialdir=self._initial_dir,
            initialfile=self._initial_file,
            title=self._title,
        )
        if path:
            # Valid
            print(f"'{path}' selected as path.")
            self._initial_dir = os.path.dirname(path)
            self._initial_file = os.path.basename(path)
            return path
        else:
            # Cancelled.
            print("Cancelled")
            return None
