"""knockout_sheet.py
Classes and tools to render a knockout event and export it as a PDF.
Written by Jotham Gates, 09/11/2025"""

from __future__ import annotations
import os
import subprocess
from typing import List, Literal, Tuple, cast
import numpy as np
import ttkbootstrap as ttk
import ttkbootstrap.constants as ttkc
from knockout_race import (
    RaceBranch,
    BranchResult,
    Podium,
    Race,
)
from knockout import (
    KnockoutEvent,
)
from knockout_sheet_elements import (
    ARROW_HEIGHT,
    ARROW_WIDTH,
    AUX_RACES_SECTION_WIDTH,
    BOTTOM_MARGIN,
    BRACKET_VERTICAL_SEPARATION,
    FIRST_COLUMN_HINT_WIDTH,
    FONT,
    FONT_NORMAL_SIZE,
    FONT_SMALL_SIZE,
    FONT_SUPTITLE_SIZE,
    FONT_TITLE_SIZE,
    HORIZONTAL_LINE_LENGTH,
    LABEL_HEIGHT,
    LABEL_WIDTH,
    LEFT_MARGIN,
    LOSERS_INITIAL_SPACING,
    RIGHT_MARGIN,
    SHORT_TEXT_MARGIN,
    TEXT_MARGIN,
    TOP_MARGIN,
    WINNERS_INITIAL_SPACING,
    AuxilliaryRaceSheet,
    BracketLineSet,
    BracketLineSetBye,
    BracketLineSetNormal,
    NotesBox,
    NumberBox,
    NumberBoxFactory,
    RaceDrawing,
    COLUMN_WIDTH,
)


class KnockoutSheet:
    """Class that draws and manages the knockout tree structure."""

    def __init__(
        self,
        frame: ttk.Frame | ttk.Window,
        start_row: int | None,
        start_column: int | None,
    ) -> None:
        self._frame = frame

        # Canvas to draw the draw on.
        SCALE = 1
        self._width = 297 * SCALE
        self._height = 210 * SCALE
        self.canvas = ttk.Canvas(self._frame, width=self._width, height=self._height)
        self._races: List[RaceDrawing] = []
        self._aux_races: AuxilliaryRaceSheet

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
        self.canvas.bind(
            "<ButtonPress-1>", lambda event: self.canvas.scan_mark(event.x, event.y)
        )
        self.canvas.bind(
            "<B1-Motion>",
            lambda event: self.canvas.scan_dragto(event.x, event.y, gain=1),
        )

        # Linux scrolling using the mousewheel and trackpad.
        # Based on https://stackoverflow.com/questions/17355902/tkinter-binding-mousewheel-to-scrollbar
        # Scrolling up and down.
        self.canvas.bind("<4>", lambda event: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<5>", lambda event: self.canvas.yview_scroll(1, "units"))

        # Scrolling left and right.
        self.canvas.bind(
            "<Shift-4>", lambda event: self.canvas.xview_scroll(-1, "units")
        )
        self.canvas.bind(
            "<Shift-5>", lambda event: self.canvas.xview_scroll(1, "units")
        )

        # Windows scrolling using the mousewheel and trackpad. # TODO: Test
        self.canvas.bind(
            "<MouseWheel>",
            lambda event: self.canvas.yview_scroll(
                int(-1 * (event.delta / 120)), "units"
            ),
        )
        self.canvas.bind(
            "<Shift-MouseWheel>",
            lambda event: self.canvas.yview_scroll(
                int(-1 * (event.delta / 120)), "units"
            ),
        )

        # Scroll bars.
        # Based on https://stackoverflow.com/a/68723221
        self._x_scroll_bar = ttk.Scrollbar(
            self._frame, orient="horizontal", command=self.canvas.xview
        )
        self._y_scroll_bar = ttk.Scrollbar(
            self._frame, orient="vertical", command=self.canvas.yview
        )
        self.canvas.configure(
            yscrollcommand=self._y_scroll_bar.set, xscrollcommand=self._x_scroll_bar.set
        )
        self.canvas.configure(scrollregion=(0, 0, self._width, self._height))

        self._x_scroll_bar.grid(row=start_row + 1, column=start_column, sticky="ew")
        self._y_scroll_bar.grid(row=start_row, column=start_column + 1, sticky="ns")
        self.canvas.grid(row=start_row, column=start_column, sticky="nsew")
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
        suptitle_bottom = self.draw_title(event)
        self.draw_tree(
            event=event,
            numbers=numbers,
            show_seed=show_seed,
            x_offset=AUX_RACES_SECTION_WIDTH + LEFT_MARGIN + TEXT_MARGIN,
            y_offset=suptitle_bottom,
        )
        self.draw_notes(event, self._width - RIGHT_MARGIN, self._height - BOTTOM_MARGIN)
        self.draw_aux_races(event, numbers, suptitle_bottom)

    def draw_notes(self, event: KnockoutEvent, x: float, y: float) -> None:
        notes_box = NotesBox(self.canvas, (x - 450, y - 300), (x, y))
        src_filename = os.path.join(os.path.dirname(__file__), "notes.md")
        notes_box.read_markdown(src_filename)
        notes_box.add_text(
            f"Rounds will be run in the following order:\n{event.calculate_play_order()}",
            bullet_point=True,
        )

    def draw_aux_races(
        self, event: KnockoutEvent, numbers: NumberBoxFactory, y_offset: float
    ) -> None:
        top_left = (LEFT_MARGIN, y_offset)
        bottom_right = (
            LEFT_MARGIN + AUX_RACES_SECTION_WIDTH,
            self._height - BOTTOM_MARGIN,
        )
        self._aux_races = AuxilliaryRaceSheet(
            self, event, numbers, top_left, bottom_right
        )

    def draw_title(
        self,
        event: KnockoutEvent,
    ) -> float:
        """Draws the main title."""
        # Titles
        _, _, _, suptitle_bottom = self.canvas.bbox(
            self.canvas.create_text(
                LEFT_MARGIN,
                TOP_MARGIN,
                text=event.name,
                font=(FONT, FONT_SUPTITLE_SIZE),
                anchor=ttkc.NW,
            )
        )
        return suptitle_bottom

    def draw_tree(
        self,
        event: KnockoutEvent,
        numbers: NumberBoxFactory,
        show_seed: bool,
        x_offset: float,
        y_offset: float,
    ) -> None:
        """Draws the tree of the knockout event on the canvas."""

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
            BOX_FILL = "#CFF9F3"
            TEXT_FILL = "#1E7B6D"
            box_centre = x_end - HORIZONTAL_LINE_LENGTH - TEXT_MARGIN
            box_half_width = HORIZONTAL_LINE_LENGTH + TEXT_MARGIN + BOX_PADDING
            next_round_top = y_centre - next_round_height / 2 - next_round_offset
            preferred_text_location = y_centre - (height / 2) - offset
            text_y_bottom = min(next_round_top, preferred_text_location) - TEXT_MARGIN

            _, text_y_top, _, _ = self.canvas.bbox(
                self.canvas.create_text(
                    box_centre,
                    text_y_bottom,
                    anchor=ttkc.S,
                    text=round_name,
                    width=2 * box_half_width - 2 * TEXT_MARGIN,
                    font=(FONT, FONT_NORMAL_SIZE, "bold"),
                    fill=TEXT_FILL,
                )
            )
            rect = self.canvas.create_rectangle(
                box_centre - box_half_width,
                text_y_top - TEXT_MARGIN,
                box_centre + box_half_width,
                y_centre - offset + (height / 2) + BOX_PADDING,
                width=0,
                fill=BOX_FILL,
                outline=BOX_FILL,
            )
            self.canvas.tag_lower(rect)

        def draw_round(
            x: float,
            y_centre: float,
            y_spacing: float,
            round: List[Race],
            columns_wide: int,
            show_result_box: bool,
        ) -> float:
            """Draws a round in either the winners' or losers' brackets.

            Args:
                x (float): The left coordinate of the races in the round.
                y_centre (float): The y coordinate of the centreline of the round.
                y_spacing (float): The y spacing between branches in the round.
                round (List[Race]): The round itself.
                columns_wide (int): The number of columns wide to draw the round to make it line up correctly.
                show_result_box (bool): When True, draws the result of the race
                    next to it (only enable for the grand final and auxilliary races).

            Returns:
                float: The x coordinate of the right side of the races in the round.
            """
            # Draw the races
            x_end = -1.0
            for i, race in enumerate(round):
                race_y_centre = (i + 0.5 - len(round) / 2) * y_spacing + y_centre
                race_drawing = RaceDrawing(self, event, numbers, show_seed)
                self._races.append(race_drawing)
                x_end = race_drawing.draw_race(
                    x, race_y_centre, y_spacing / 2, columns_wide, race, show_result_box
                )

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
                    x=next_x,
                    y_centre=y_centre,
                    y_spacing=y_spacing(i),
                    round=round,
                    columns_wide=cols_wide,
                    show_result_box=False,
                )
                draw_round_box(
                    x_end=next_x,
                    y_centre=y_centre,
                    height=round_height(round, y_spacing(i)),
                    offset=0,
                    next_round_height=(
                        0
                        if i + 1 == len(rounds)
                        else round_height(rounds[i + 1], y_spacing(i + 1))
                    ),
                    next_round_offset=0,
                    round_name=f"P{i+1}",
                )

            return x + len(rounds) * COLUMN_WIDTH, y_centre

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
                    x=next_x,
                    y_centre=y_centre - y_offset(i),
                    y_spacing=y_spacing(i),
                    round=round,
                    columns_wide=1,
                    show_result_box=False,
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

            return x + len(rounds) * COLUMN_WIDTH, y_centre - y_offset(len(rounds))

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
                x=max(winners_end[0], losers_end[0]),
                y_centre=gf_y_centre,
                y_spacing=gf_y_spacing,
                round=[event.grand_final],
                columns_wide=1,
                show_result_box=True,
            )
            draw_round_box(
                x_end=right_side - LABEL_WIDTH,
                y_centre=gf_y_centre,
                height=round_height([event.grand_final], gf_y_spacing),
                offset=0,
                next_round_height=0,
                next_round_offset=0,
                round_name=f"Grand final",
            )

            # Check the results box.
            assert isinstance(
                event.grand_final.winner_next_race, Podium
            ), "The winner of the grand final must end up with a podium."

            return right_side + TEXT_MARGIN + LABEL_WIDTH

        # Winners' bracket.
        _, _, _, winners_title_bottom = self.canvas.bbox(
            self.canvas.create_text(
                x_offset,
                y_offset + TEXT_MARGIN,
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
            x_offset + FIRST_COLUMN_HINT_WIDTH,
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
        _, _, _, losers_title_bottom = self.canvas.bbox(
            self.canvas.create_text(
                x_offset,
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
            x_offset + FIRST_COLUMN_HINT_WIDTH,
            losers_centreline,
            LOSERS_INITIAL_SPACING,
            event.losers_bracket,
        )

        def mark_line(y: float) -> None:
            """Marks a y coordinate for debugging purposes."""
            self.canvas.create_line(0, y, self._width, y, fill="red")

        # Grand final
        drawing_width = draw_grand_final(win_end, lose_end) + RIGHT_MARGIN
        drawing_height = (
            losers_centreline + losers_height / 2 + LABEL_HEIGHT + BOTTOM_MARGIN
        )
        self.set_size(self.a_paper_scale((drawing_width, drawing_height)))
        # self.manual_update()

    def update(self) -> None:
        """Updates each item on the sheet."""
        # print("Not updating here.")

        # def manual_update(self) -> None:
        for drawing in self._races:
            drawing.update()

        self._aux_races.update()

        # self._frame.after(2000, self.manual_update)

    def _clear(self) -> None:
        """Clears everything from the canvas.
        This may not be 100% memory leak free, so minimise the use of this."""
        self.canvas.delete("all")
        self._races = []

    def a_paper_scale(self, min_dimensions: Tuple[float, float]) -> Tuple[float, float]:
        """Calculates the minimum size in the A paper ratio."""
        min_width, min_height = min_dimensions
        height = max(min_height, min_width / np.sqrt(2))
        width = height * np.sqrt(2)
        return width, height

    def set_size(self, dimensions: Tuple[float, float]) -> None:
        """Sets the size of the canvas."""
        width, height = dimensions
        self.canvas.config(width=width, height=height)
        self.canvas.config(scrollregion=(0, 0, width, height))
        self._width = width
        self._height = height

    def export(
        self,
        ghostscript_path: str,
        output: str,
        pdf_width_mm: float,
        pdf_height_mm: float,
        save_ps: bool = False,
        generate_pdf: bool = True,
        surpress_output: bool = False,
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
        self.canvas.update()
        postscript = cast(
            str,
            self.canvas.postscript(
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
            if not surpress_output:
                print(" ".join(args))
                
            process = subprocess.Popen(
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL if surpress_output else None,
            )
            process.communicate(postscript, timeout=30)
            process.wait()
