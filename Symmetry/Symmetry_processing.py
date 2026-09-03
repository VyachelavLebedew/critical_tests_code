import os
import re
from typing import Any, Optional, List, Dict

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog

import matplotlib as mpl
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk
)
from matplotlib.figure import Figure
import matplotlib.dates as mdates

from Buttons import MainButtons, TestButtons
from Messages import Messages
from Settings import show_info, FONTS, COLORS, GAPS, ENCODINGS, PLOT

mpl.rcParams['font.family'] = 'Times New Roman'


class Symmetry_processing:
    """
    Symmetry plotting window.

    Opens empty. Through the top menu the user loads an .s17-style file and
    then points at the columns to plot: the CR (rod) columns and the two
    current channels. Two plots can then be drawn - one for the CRs, one
    for the currents - each versus time, with a horizontal scrollbar since
    the experiment is long. A whole plot or a clicked-out fragment can be
    saved, always with rescaled axes.
    """

    def __init__(self, parent, main_app: Any) -> None:
        self.parent = parent
        self.main_app: Any = main_app
        self.root = main_app.root
        self.frame: Optional[tk.Frame] = None
        self.menu_bar: Optional[tk.Menu] = None

        self.df: Optional[pd.DataFrame] = None
        self.times: Optional[List[datetime]] = None

        # Chosen column indices (0-based into the file)
        self.cr_columns: List[int] = []
        self.current_columns: List[int] = []

        # The plot currently shown: "cr", "currents" or None
        self.current_plot: Optional[str] = None
        self.fig = None
        self.ax = None
        self.canvas = None
        self.hint = None
        self.legend_visible = True

        # Fragment selection: two dashed lines and their x-positions
        self._span_x: List[float] = []
        self._span_lines: List[Any] = []

    # ------------------------------------------------------------------ #
    #  Window                                                             #
    # ------------------------------------------------------------------ #
    def create_Symmetry_processing_window(self) -> None:
        """Build the (initially empty) plotting window."""
        if self.parent is not None:
            self.parent.destroy()

        self.frame = tk.Frame(self.root, bg=COLORS['BACKGROUND_COLOR'])
        self.frame.place(x=0, y=0, relwidth=1, relheight=1)
        self.root.title('Symmetry - plots')

        self.create_menu()

        # Area that will hold the plot; empty at first
        self.plot_area = tk.Frame(self.frame, bg=COLORS['BACKGROUND_COLOR'])
        self.plot_area.pack(side=tk.TOP, fill=tk.BOTH, expand=True,
                            padx=GAPS['GAPS_X']['PAD_X_10'],
                            pady=GAPS['GAPS_Y']['PAD_Y_10'])

        self.hint = tk.Label(
            self.plot_area,
            text="Please load an experiment file from the File menu to begin.",
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.hint.pack(pady=GAPS['GAPS_Y']['PAD_Y_10'])

        bar = tk.Frame(self.frame, bg=COLORS['BACKGROUND_COLOR'])
        bar.pack(side=tk.BOTTOM, fill=tk.X,
                 padx=GAPS['GAPS_X']['PAD_X_10'],
                 pady=GAPS['GAPS_Y']['PAD_Y_10'])
        MainButtons(
            bar, text="<< BACK", command=self.back
        ).pack(side=tk.LEFT)

        MainButtons(
            bar, text="User guide",
            command=lambda: show_info(
                self.root, "Symmetry/info_processing.txt"
            )
        ).pack(side=tk.LEFT, padx=GAPS['GAPS_X']['PAD_X_10'])

    # ------------------------------------------------------------------ #
    #  Menu                                                               #
    # ------------------------------------------------------------------ #
    def create_menu(self) -> None:
        """File / Plots / Save / INFO menus."""
        self.menu_bar = tk.Menu(self.root.winfo_toplevel())
        self.root.winfo_toplevel().config(menu=self.menu_bar)

        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(
            label="Load file", font=FONTS['DATA_FONT'],
            command=self.load_file
        )
        file_menu.add_command(
            label="Select columns", font=FONTS['DATA_FONT'],
            command=self.select_columns
        )

        plots_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Plots", menu=plots_menu)
        plots_menu.add_command(
            label="CR positions", font=FONTS['DATA_FONT'],
            command=lambda: self.draw_plot("cr")
        )
        plots_menu.add_command(
            label="Currents", font=FONTS['DATA_FONT'],
            command=lambda: self.draw_plot("currents")
        )
        plots_menu.add_separator()
        plots_menu.add_command(
            label="Show / hide legend", font=FONTS['DATA_FONT'],
            command=self.toggle_legend
        )

        save_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Save", menu=save_menu)
        save_menu.add_command(
            label="Save whole plot", font=FONTS['DATA_FONT'],
            command=self.save_whole
        )
        save_menu.add_command(
            label="Save a fragment", font=FONTS['DATA_FONT'],
            command=self.save_fragment_mode
        )

        info = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="INFO", menu=info)
        info.add_command(
            label="INFO", font=FONTS['DATA_FONT'],
            command=lambda: show_info(
                self.root, "Symmetry/info_processing.txt"
            )
        )

    # ------------------------------------------------------------------ #
    #  File loading and column parsing                                    #
    # ------------------------------------------------------------------ #
    def load_file(self) -> None:
        """Load an .s17-style tab-separated file."""
        filename = filedialog.askopenfilename(
            title="Load an experiment file",
            filetypes=[("Experiment files", "*.s17 *.txt"),
                       ("All files", "*.*")]
        )
        if not filename:
            return
        df = None
        for enc in ENCODINGS:
            try:
                df = pd.read_csv(filename, sep="\t", encoding=enc)
                break
            except Exception:
                continue
        if df is None:
            Messages.show("error", "SYM_FILE_ERROR")
            return

        self.df = df
        # Excel-serial time in the second column (index 1)
        try:
            serial = pd.to_numeric(
                df.iloc[:, 1].astype(str).str.replace(",", "."),
                errors="coerce"
            )
            self.times = [
                datetime(1899, 12, 30) + timedelta(days=float(t))
                for t in serial
            ]
        except Exception:
            self.times = list(range(len(df)))

        self.hint.config(
            text="File loaded. Please select the columns from the File menu."
        )

    def _column_series(self, index: int):
        """Numeric series of a file column by 0-based index."""
        return pd.to_numeric(
            self.df.iloc[:, index].astype(str).str.replace(",", "."),
            errors="coerce"
        )

    def parse_columns(self, text: str) -> List[int]:
        """
        Parse a column spec like '10-110' or '10-12, 17, 20, 100-210'
        into a sorted list of 0-based column indices.

        The numbers are the 1-based column numbers shown in the file
        header, so 1 is subtracted.
        """
        result: List[int] = []
        for part in text.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                a, b = part.split("-", 1)
                lo, hi = int(a), int(b)
                if lo > hi:
                    lo, hi = hi, lo
                result.extend(range(lo, hi + 1))
            else:
                result.append(int(part))
        # to 0-based, unique, in range
        n = self.df.shape[1]
        cols = sorted({c - 1 for c in result if 1 <= c <= n})
        return cols

    # ------------------------------------------------------------------ #
    #  Column selection dialog                                            #
    # ------------------------------------------------------------------ #
    def _announce_selection(self) -> None:
        """Tell the user what was selected and which plots are available."""
        if self.hint is None or not self.hint.winfo_exists():
            return
        parts = []
        if self.cr_columns:
            parts.append(f"{len(self.cr_columns)} CRs column(s)")
        if self.current_columns:
            parts.append(f"{len(self.current_columns)} current column(s)")

        if not parts:
            self.hint.config(
                text="No columns selected yet. Please select the columns "
                     "from the File menu."
            )
            return

        available = []
        if self.cr_columns:
            available.append("CR positions")
        if self.current_columns:
            available.append("Currents")
        self.hint.config(
            text="Selected: " + ", ".join(parts) + ".  Available plots: "
                 + ", ".join(available) + ".  Open them from the Plots menu."
        )

    def select_columns(self) -> None:
        """Open the two-row column selection dialog."""
        if self.df is None:
            Messages.show("warning", "SYM_NO_FILE")
            return

        win = tk.Toplevel(self.root)
        win.title("Select columns")
        win.configure(bg=COLORS['BACKGROUND_COLOR'])
        win.grab_set()

        tk.Label(
            win, text="CRs columns, e.g. 10-12, 17, 20:",
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        ).grid(row=0, column=0, sticky="w",
               padx=GAPS['GAPS_X']['PAD_X_10'],
               pady=GAPS['GAPS_Y']['PAD_Y_10'])
        cr_entry = ttk.Entry(win, font=FONTS['DATA_FONT'], width=40)
        cr_entry.grid(row=0, column=1,
                      padx=GAPS['GAPS_X']['PAD_X_10'],
                      pady=GAPS['GAPS_Y']['PAD_Y_10'])
        if self.cr_columns:
            cr_entry.insert(0, ", ".join(str(c + 1) for c in self.cr_columns))

        tk.Label(
            win, text="Current columns (two channels expected):",
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        ).grid(row=1, column=0, sticky="w",
               padx=GAPS['GAPS_X']['PAD_X_10'],
               pady=GAPS['GAPS_Y']['PAD_Y_10'])
        cur_entry = ttk.Entry(win, font=FONTS['DATA_FONT'], width=40)
        cur_entry.grid(row=1, column=1,
                       padx=GAPS['GAPS_X']['PAD_X_10'],
                       pady=GAPS['GAPS_Y']['PAD_Y_10'])
        if self.current_columns:
            cur_entry.insert(
                0, ", ".join(str(c + 1) for c in self.current_columns)
            )

        def confirm():
            cr_text = cr_entry.get().strip()
            cur_text = cur_entry.get().strip()
            try:
                cr_cols = self.parse_columns(cr_text) if cr_text else []
                cur_cols = self.parse_columns(cur_text) if cur_text else []
            except ValueError:
                Messages.show("error", "SYM_BAD_COLUMNS")
                return

            # Two current channels are expected; one -> ask, none -> fine
            if len(cur_cols) == 1:
                keep = Messages.show("question", "SYM_ONE_CURRENT")
                if not keep:
                    return

            self.cr_columns = cr_cols
            self.current_columns = cur_cols
            win.destroy()
            self._announce_selection()

        TestButtons(
            win, text="OK", command=confirm
        ).grid(row=2, column=1, sticky="e",
               padx=GAPS['GAPS_X']['PAD_X_10'],
               pady=GAPS['GAPS_Y']['PAD_Y_10'])

        # Enter in either field confirms the selection
        cr_entry.bind("<Return>", lambda e: confirm())
        cur_entry.bind("<Return>", lambda e: confirm())
        cr_entry.focus_set()

    # ------------------------------------------------------------------ #
    #  Plotting                                                           #
    # ------------------------------------------------------------------ #
    def draw_plot(self, kind: str) -> None:
        """Draw the CR plot or the currents plot with a horizontal scroll."""
        if self.df is None:
            Messages.show("warning", "SYM_NO_FILE")
            return
        columns = (self.cr_columns if kind == "cr"
                   else self.current_columns)
        if not columns:
            Messages.show("warning", "SYM_NO_COLUMNS")
            return

        # Clear the plot area
        for child in self.plot_area.winfo_children():
            child.destroy()
        self._span_x = []
        self._span_lines = []

        # A wide figure inside a horizontally scrollable canvas. The width
        # grows with the number of samples so a long run stays readable.
        n = len(self.df)
        width_in = max(12, n / 400.0)
        self.fig = Figure(figsize=(width_in, 5), constrained_layout=True)
        self.ax = self.fig.add_subplot(111)

        family = FONTS['PLOT_FONT'][0]
        fsize = FONTS['PLOT_FONT'][1]

        # Bright, cheerful palette that cycles if there are many columns
        bright = [
            "#E6194B", "#3CB44B", "#4363D8", "#F58231", "#911EB4",
            "#42D4F4", "#F032E6", "#BFEF45", "#FABED4", "#469990",
            "#9A6324", "#800000", "#808000", "#000075", "#E6BEFF",
        ]
        for i, idx in enumerate(columns):
            y = self._column_series(idx)
            label = str(self.df.columns[idx]).strip()[:24]
            self.ax.plot(
                self.times, y, linewidth=1.6,
                color=bright[i % len(bright)], label=label
            )

        if kind == "cr":
            self.ax.set_ylabel("CR position, cm", fontname=family,
                               fontsize=fsize)
            title = "CR positions"
        else:
            self.ax.set_ylabel("Current, A", fontname=family, fontsize=fsize)
            title = "Currents"
        self.ax.set_xlabel("Time", fontname=family, fontsize=fsize)
        self.ax.set_title(title, fontname=family, fontsize=fsize + 1)
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        # All tick labels in the plot font too
        for tick in self.ax.get_xticklabels() + self.ax.get_yticklabels():
            tick.set_fontname(family)
            tick.set_fontsize(fsize - 1)

        # Legend: column names from the file, in the plot font. Kept for
        # any number of columns and always exported with the figure.
        ncol = 2 if len(columns) <= 12 else 3
        self.legend = self.ax.legend(
            prop={"family": family, "size": max(6, fsize - 3)},
            ncol=ncol, framealpha=0.9
        )
        self.legend.set_visible(self.legend_visible)
        self.ax.grid(True, linewidth=0.3, alpha=0.5)

        self.current_plot = kind
        self._embed_scrollable_canvas(width_in)

    def _embed_scrollable_canvas(self, width_in: float) -> None:
        """Put the figure on a canvas that scrolls horizontally."""
        outer = tk.Frame(self.plot_area, bg=COLORS['BACKGROUND_COLOR'])
        outer.pack(fill=tk.BOTH, expand=True)

        hbar = tk.Scrollbar(outer, orient=tk.HORIZONTAL)
        hbar.pack(side=tk.BOTTOM, fill=tk.X)

        holder = tk.Canvas(
            outer, bg=COLORS['BACKGROUND_COLOR'],
            xscrollcommand=hbar.set, highlightthickness=0
        )
        holder.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        hbar.config(command=holder.xview)

        inner = tk.Frame(holder, bg=COLORS['BACKGROUND_COLOR'])
        holder.create_window((0, 0), window=inner, anchor="nw")

        self.canvas = FigureCanvasTkAgg(self.fig, master=inner)
        toolbar = NavigationToolbar2Tk(self.canvas, inner)
        toolbar.update()
        toolbar.pack(side=tk.TOP, fill=tk.X)
        widget = self.canvas.get_tk_widget()

        # Fix the pixel width so the canvas scrolls instead of shrinking
        px = int(width_in * self.fig.dpi)
        widget.configure(width=px, height=int(5 * self.fig.dpi))
        widget.pack(side=tk.TOP)
        self.canvas.draw()
        self.canvas.mpl_connect("button_press_event", self.on_click)

        inner.update_idletasks()
        holder.config(scrollregion=holder.bbox("all"))

    # ------------------------------------------------------------------ #
    #  Saving                                                             #
    # ------------------------------------------------------------------ #
    def _ask_save_path(self):
        """Ask for a destination file with the offered vector/raster set."""
        return filedialog.asksaveasfilename(
            title="Save the plot",
            defaultextension=".png",
            filetypes=[
                ("PNG image", "*.png"),
                ("PDF document", "*.pdf"),
                ("SVG image", "*.svg"),
                ("JPEG image", "*.jpg"),
            ]
        )

    def toggle_legend(self) -> None:
        """Show or hide the legend on the current plot."""
        self.legend_visible = not self.legend_visible
        if getattr(self, "legend", None) is not None:
            self.legend.set_visible(self.legend_visible)
            if self.canvas is not None:
                self.canvas.draw_idle()

    def save_whole(self) -> None:
        """Save the whole plot as it is now."""
        if self.fig is None or self.current_plot is None:
            Messages.show("warning", "SYM_NO_PLOT")
            return
        path = self._ask_save_path()
        if not path:
            return
        # Full time span, axes rebuilt to it
        self.ax.set_xlim(self.times[0], self.times[-1])
        self.ax.figure.canvas.draw()
        self.fig.savefig(path, dpi=200, bbox_inches="tight")

    def save_fragment_mode(self) -> None:
        """
        Save the fragment bounded by the two dashed lines on the plot.

        The bounds are placed by clicking the plot (see on_click); this
        command just exports whatever is currently selected.
        """
        if self.fig is None or self.current_plot is None:
            Messages.show("warning", "SYM_NO_PLOT")
            return
        if len(self._span_x) < 2:
            Messages.show("warning", "SYM_NO_FRAGMENT")
            return

        path = self._ask_save_path()
        if not path:
            return

        x0, x1 = sorted(self._span_x[:2])

        # Hide the selection lines so they are not saved, rescale the axes
        # to the fragment and rebuild the time ticks, then export.
        self._set_lines_visible(False)
        old_xlim = self.ax.get_xlim()
        self.ax.set_xlim(x0, x1)
        self.ax.relim()
        self.ax.autoscale_view(scalex=False, scaley=True)
        self.ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
        self.ax.figure.canvas.draw()

        self.fig.savefig(path, dpi=200, bbox_inches="tight")

        # Restore the full view and the selection lines on screen
        self.ax.set_xlim(old_xlim)
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        self._set_lines_visible(True)
        self.ax.figure.canvas.draw()

    def _set_lines_visible(self, visible: bool) -> None:
        """Show or hide the two selection lines."""
        for line in self._span_lines:
            line.set_visible(visible)

    def on_click(self, event) -> None:
        """
        Place or move the two dashed lines that bound the save fragment.

        First click sets the left bound, second the right. Once both are
        set, a further click moves whichever line is nearest - so the
        selection can be re-clicked freely.
        """
        if event.inaxes is None or event.xdata is None:
            return
        x = event.xdata

        if len(self._span_x) < 2:
            self._span_x.append(x)
            colour = "green" if len(self._span_x) == 1 else "red"
            line = self.ax.axvline(
                x, color=colour, linestyle="--", linewidth=1.2
            )
            self._span_lines.append(line)
        else:
            # move the nearest bound (re-click)
            i = min(range(2), key=lambda k: abs(self._span_x[k] - x))
            self._span_x[i] = x
            self._span_lines[i].set_xdata([x, x])

        self.ax.figure.canvas.draw_idle()

    # ------------------------------------------------------------------ #
    #  Navigation                                                         #
    # ------------------------------------------------------------------ #
    def back(self) -> None:
        """Return to the Symmetry table window."""
        try:
            self.root.winfo_toplevel().config(menu="")
        except Exception:
            pass
        if self.frame is not None:
            self.frame.destroy()
        self.main_app.create_Symmetry_window()
