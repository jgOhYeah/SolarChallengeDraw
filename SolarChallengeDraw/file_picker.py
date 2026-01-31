"""file_picker.py
Class that adds memory to file picking.
Written by Jotham Gates, 11/11/2025"""

import os
import tkinter as tk
import tkinter.filedialog as filedialog
from typing import Iterable, List, Tuple
import ttkbootstrap.constants as ttkc

class FilePickerException(Exception):
    """Exceptions that relate to file picking."""
    pass

class FilePicker:
    """Class that remembers the last file path selected."""

    def __init__(
        self,
        default_extension: str,
        filetypes: Iterable[tuple[str, str | list[str] | tuple[str, ...]]] | None,
        initial_dir: str,
        initial_file: str,
        title: str,
        initial_path: str | None = None,
        read_only: bool = True
    ) -> None:
        """Initialises the file picker with settings and an initial path.

        Args:
            default_extension (str): The default extension to load and save.
            filetypes (Iterable[tuple[str, str  |  list[str]  |  tuple[str, ...]]] | None): The types of files to look for.
            initial_dir (str): The initial directory to search in.
            initial_file (str): The initial filename to show by default.
            title (str): The title of the window. This will be concatenated on to "Select a location to [load/save] ".
            initial_path (str | None, optional): An initial path. If provided, overrides initial_dir and initial_file and treats this as an ok path to save to. Defaults to None.
        """
        self._default_extension = default_extension
        # Add on all files to the filetypes options.
        self._filetypes = list(filetypes) if filetypes is not None else []
        self._filetypes.append(
            ("All files", "*"),
        )
        if initial_path is None:
            # Normal.
            self._initial_dir = initial_dir
            self._initial_file = initial_file
            self._ok_to_save = False
        else:
            # Override and use the initial path.
            self._initial_dir, self._initial_file = self._split_path(initial_path)
            self._ok_to_save = True

        self._title = title
        self._read_only = read_only

    def _split_path(self, path: str) -> Tuple[str, str]:
        """Splits a path into a directory and base name."""
        return os.path.dirname(path), os.path.basename(path)

    def request(self, saveas: bool = True) -> str | None:
        """Opens the dialog.

        Args:
            saveas (bool, optional): Opens a saveas dialogue if True, otherwise dialogue to read the file. Defaults to True.
        Returns:
            str | None: The string to save as or None if the operation was cancelled.
        """
        if saveas:
            if self._read_only:
                raise FilePickerException("This picker is for read-only files. Therefore save as should not be called.")
            path = filedialog.asksaveasfilename(
                defaultextension=self._default_extension,
                filetypes=self._filetypes,
                initialdir=self._initial_dir,
                initialfile=self._initial_file,
                title=f"Select a location to save {self._title}",
            )
        else:
            path = filedialog.askopenfilename(
                defaultextension=self._default_extension,
                filetypes=self._filetypes,
                initialdir=self._initial_dir,
                initialfile=self._initial_file,
                title=f"Select a location to load {self._title}",
            )
        if path:
            # Valid
            print(f"'{path}' selected as path.")
            self._initial_dir, self._initial_file = self._split_path(path)
            self._ok_to_save = True
            return path
        else:
            # Cancelled.
            print("Cancelled")
            return None

    @property
    def ok_to_save(self) -> bool:
        """Checks if it is ok to save to this filename (i.e. the path is not the default that could accidentally overwrite something)."""
        return self._ok_to_save
    
    @ok_to_save.setter
    def ok_to_save(self, save_allowed) -> None:
        """External control over whether it is ok to write to the current path."""
        if save_allowed and self._read_only:
            raise FilePickerException("This picker is read only - setting ok_to_save to True is not allowed!")
        
        self._ok_to_save = save_allowed