import numpy as np
from datetime import datetime, timedelta
import os

from openpyxl import Workbook
from openpyxl.utils import get_column_letter

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog

import matplotlib as mpl
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk
)
from matplotlib.figure import Figure
import matplotlib.dates as mdates

from typing import Any, Optional, List, Dict

from Buttons import MainButtons, TestButtons, SmallButtons
from Messages import Messages
import Formulas
from Settings import (
    DECIMAL, show_info, FONTS, COLORS, GAPS, ITC_COMPUTATION_VALUES,
    SPLITTER_MINSIZES, PLOT, CURSOR, TABLE, TIME_SHIFT,
    GROUP_COLORS, PLOT_STYLE, DRDH_HINTS, DRDH_ERROR, DRDH_PLOT,
    DRDC_WINDOW_SEC, ENTRY_WIDTH
)

mpl.rcParams['font.family'] = 'Times New Roman'


class DRDH_processing:

    def __init__(self, root: tk.Widget, main_app: Any):
        self.root: tk.Widget = root
        self.main_app: Any = main_app
        self.root.winfo_toplevel().iconbitmap("Icons/DRDH_icon.ico")
        self.DRDH_frame: Optional[tk.Frame] = None
        self.beta: float = self.main_app.main_app.beta
        self.Group_length = self.main_app.Group_length
        # Overlap of the control groups, %. 0 -> no overlap.
        self.overlap: float = float(getattr(self.main_app, "overlap", 0) or 0)

        # Movement type chosen in DRDH_module: 'Withdrawal', 'Insertion'
        # or None. Not used by the determination itself - the direction is
        # taken from the data - but kept for reference and further use.
        self.movement_type: Optional[str] = getattr(
            self.main_app, "movement_type", None
        )
        self.active_entry: Optional[ttk.Entry] = None
        self.plot_windows: List[Dict[str, Any]] = []
        self.extended_cursor_enabled: bool = False
        self.Time = getattr(self.main_app, "Time", None)
        self.Reactivity = getattr(self.main_app, "Reactivity", None)
        self.Groups = []
        self.Group_names = []
        for i in range(12, 0, -1):
            attr_name = f"H{i}_position"
            series = getattr(self.main_app, attr_name)

            if series is not None:
                self.Groups.append(series.values)
                self.Group_names.append(f"H{i}")

        self.DRDC: Optional[float] = (
            self.main_app.DRDC
            if hasattr(self.main_app, 'DRDC') else None
        )
        self.boric_acid_start: Optional[float] = (
            self.main_app.boric_acid_start
            if hasattr(self.main_app, 'boric_acid_start') else None
        )
        self.boric_acid_finish: Optional[float] = (
            self.main_app.boric_acid_finish
            if hasattr(self.main_app, 'boric_acid_finish') else None
        )

        # Boric acid concentration taken from the NFME file (optional).
        # Stored as a plain array, like the group positions, so that it can
        # safely be indexed by position.
        series = getattr(self.main_app, "boric_acid_NFME", None)
        self.boric_acid_NFME = (
            series.values if series is not None else None
        )

        # Indices needed by the "C from file" method of the DRDC:
        #   the very first click of the session and the last right click
        #   made before "Complete" was pressed.
        self.first_click_index: Optional[int] = None
        self.last_right_click_index: Optional[int] = None

        # Tree rows of the DRDC block, so that it can be rebuilt
        self.drdc_rows: List[str] = []

        # The initial row is compared with the first measured interval once
        self.initial_position_checked: bool = False

        self.DECIMAL_REACT: int = DECIMAL['DECIMAL_REACT']
        self.DECIMAL_GROUP: int = DECIMAL['DECIMAL_GROUP']
        self.DECIMAL_DRDH: int = DECIMAL['DECIMAL_DRDH']
        self.DECIMAL_DRDC: int = DECIMAL['DECIMAL_DRDC']
        self.DECIMAL_BORIC: int = DECIMAL['DECIMAL_BORIC']

        self.min_points: int = ITC_COMPUTATION_VALUES['MIN_POINTS']
        self.points_amount: int = ITC_COMPUTATION_VALUES['POINTS_AMOUNT']
        self.step_points: int = ITC_COMPUTATION_VALUES['STEP_POINTS']

        self.selection_state = {
            "interval1": {
                "left": None,
                "right": None,
                "fixed": False,
                "dots": False
            },
            "interval2": {
                "left": None,
                "right": None,
                "fixed": False,
                "dots": False
            }
        }

        self.active_interval = 1

        # Stage flags of the current measurement cycle:
        #   fix1_done    - "Fix 1" has been pressed for this cycle
        #   line1_locked - line 1 is inherited from the previous cycle
        #                  and can no longer be re-clicked
        self.fix1_done: bool = False
        self.line1_locked: bool = False

        # Every accepted DRDH measurement, for the "DRDH plot" window.
        self.drdh_points: List[Dict[str, Any]] = []

        # Groups that actually move, in order of their first movement
        self.moving_order: List[int] = self.get_moving_order()

        # Full stroke of a group as it appears in the data (may be > 100 %)
        self.position_max: float = float(
            max((g.max() for g in self.Groups), default=100.0)
        )

        # Geometry of every already measured (black) line.
        # Needed to redraw the history in a newly opened plot window.
        self.finished_lines: List[Dict[str, Any]] = []

        # Visibility flags, so that a new window repeats the old one exactly
        self.show_move_line: bool = False
        self.show_intersections: bool = False

    @staticmethod
    def group_number(name: str) -> int:
        """'H12' -> 12. Used to pick the reference group of a measurement."""
        digits = "".join(ch for ch in name if ch.isdigit())
        return int(digits) if digits else 0

    def get_moving_order(self) -> List[int]:
        """
        Indices of the groups that move during the experiment, ordered by the
        moment they start moving. Also caches the index of the first movement
        of every group.

        Everything is taken from the data, so the result is correct both for
        insertion and for withdrawal, and for any group numbering.
        """
        self.first_move_index: Dict[int, int] = {}

        for i, group in enumerate(self.Groups):
            for j in range(1, len(group)):
                if not np.isclose(group[j], group[0]):
                    self.first_move_index[i] = j
                    break

        return sorted(
            self.first_move_index,
            key=lambda i: self.first_move_index[i]
        )

    def get_group_offsets(self) -> Dict[int, float]:
        """
        Offset of every moving group on the common axis, so that the rulers
        of consecutive groups join exactly at the handover point:

            u = offset[group] + position[group]

        The offsets are derived from the data itself, not from the nominal
        overlap: at the moment a group starts moving, the previous group
        stands at a known position, and requiring the same `u` for both fixes
        the offset. This works for insertion and withdrawal, with and without
        overlap, and for any stroke length (the positions need not end at
        100 %).
        """
        offsets: Dict[int, float] = {}
        previous = None

        for gi in self.moving_order:
            if previous is None:
                offsets[gi] = 0.0
            else:
                # the sample right before `gi` started to move
                j = max(self.first_move_index[gi] - 1, 0)

                offsets[gi] = (
                    offsets[previous]
                    + self.Groups[previous][j]
                    - self.Groups[gi][j]
                )

            previous = gi

        if not offsets:
            return {}

        shift = min(offsets.values())
        return {gi: v - shift for gi, v in offsets.items()}

    def get_leading_group(self, idx1: int, idx2: int) -> Optional[int]:
        """
        The group whose displacement is used as the denominator of the DRDH.

        Only one group defines the step, even when two of them move at the
        same time: during a handover the worth is referred to the group that
        started moving first. For a handover 12 -> 11 that is group 12.

        Without overlap only one group moves anyway, so the choice is trivial.
        """
        moved = [
            gi for gi in self.moving_order
            if not np.isclose(self.Groups[gi][idx1], self.Groups[gi][idx2])
        ]

        if not moved:
            return None

        # self.moving_order is sorted by the first movement of every group,
        # so the first entry is the one that started moving earliest.
        return moved[0]

    def get_reference_group(self, idx1: int, idx2: int) -> Optional[int]:
        """
        The group whose position is used as the abscissa of a measurement.

        One group moved  -> that group.
        Several moved    -> the one with the highest number (e.g. H12 over H11).
        """
        moved = [
            gi for gi in self.moving_order
            if not np.isclose(self.Groups[gi][idx1], self.Groups[gi][idx2])
        ]

        if not moved:
            return None

        return max(
            moved,
            key=lambda gi: self.group_number(self.Group_names[gi])
        )

    def get_program_coordinate(self, idx1: int, idx2: int) -> Optional[float]:
        """
        Abscissa of a measured DRDH point: the mean position of the reference
        group between the start and the end of its movement, shifted onto the
        common axis.
        """
        ref = self.get_reference_group(idx1, idx2)

        if ref is None:
            return None

        group = self.Groups[ref]
        offsets = self.get_group_offsets()

        return float(offsets[ref] + (group[idx1] + group[idx2]) / 2.0)

    @staticmethod
    def get_drdh_sigma(delta_rho: float,
                       delta_H_cm: float,
                       DRDH: float) -> float:
        """
        Experimental uncertainty of the differential worth:

            sigma(dRho/dH) = 1/dH *
                             sqrt( sigma^2(dRho) + (dRho/dH)^2 * sigma^2(dH) )

        with sigma(dRho) relative and sigma(dH) absolute (cm).
        """
        if np.isclose(delta_H_cm, 0):
            return 0.0

        sigma_rho = DRDH_ERROR['REACTIVITY_REL'] * abs(delta_rho)
        sigma_H = DRDH_ERROR['POSITION_CM']

        return abs(1.0 / delta_H_cm) * float(
            np.sqrt(sigma_rho ** 2 + (DRDH ** 2) * (sigma_H ** 2))
        )

    @staticmethod
    def widget_alive(widget) -> bool:
        """True if the widget still exists (was not destroyed by the user)."""
        try:
            return bool(widget.winfo_exists())
        except Exception:
            return False

    def values_window_alive(self) -> bool:
        """True while the 'Current values' window is open."""
        return (
            hasattr(self, "values_window")
            and self.widget_alive(self.values_window)
        )

    def create_DRDH_processing_window(self) -> None:
        """Create the main DRDH processing window layout and initialize UI."""
        self.DRDH_processing_frame = tk.Frame(
            self.root, bg=COLORS['BACKGROUND_COLOR']
        )
        self.DRDH_processing_frame.place(x=0, y=0, relwidth=1, relheight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.DRDH_processing_frame.grid_rowconfigure(0, weight=0)
        self.DRDH_processing_frame.grid_rowconfigure(1, weight=1)
        self.DRDH_processing_frame.grid_rowconfigure(2, weight=0)
        self.DRDH_processing_frame.grid_rowconfigure(3, weight=0)
        self.DRDH_processing_frame.grid_rowconfigure(4, weight=0)
        self.DRDH_processing_frame.grid_rowconfigure(5, weight=0)

        self.DRDH_processing_frame.grid_columnconfigure(0, weight=4)
        self.DRDH_processing_frame.grid_columnconfigure(1, weight=4)
        self.DRDH_processing_frame.grid_columnconfigure(2, weight=2)
        self.DRDH_processing_frame.grid_columnconfigure(3, weight=2)

        self.create_menu()
        self.create_splitter_window()
        self.create_plot_frame()
        self.labels()
        self.checkbox()
        self.mean_position_checkbox()
        self.buttons()
        self.create_table()

        # Fill the first row
        self.results_table = []
        self.cumulative_R = 0.0
        initial_groups = {
            name: self.Groups[i][0] for i, name in enumerate(self.Group_names)
        }
        self.update_table(
            R=0.0, delta_R=0.0, DRDH=0.0, group_values=initial_groups
        )

        self.update_hint()

    def create_splitter_window(self) -> None:
        """Create a horizontal splitter separating plot and results table."""
        self.splitter_window = tk.PanedWindow(
            self.DRDH_processing_frame,
            orient=tk.HORIZONTAL,
            sashrelief=tk.RAISED,
            sashwidth=5,
            bg=COLORS['BACKGROUND_COLOR']
        )
        self.splitter_window.grid(
            row=1, column=0, columnspan=4,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_10_5'],
            sticky="nsew"
        )
        self.DRDH_processing_frame.grid_rowconfigure(1, weight=1)

    def labels(self):
        """
        Create and locate all labels in the UI.
        """
        self.main_window_label = tk.Label(
            self.DRDH_processing_frame, text='DRDH Module',
            font=FONTS['TITLE_FONT'], bg=COLORS['BACKGROUND_COLOR']
        ).grid(
            row=0, column=0, columnspan=4,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            )

        self.Reactivity_change_unit = tk.Label(
            self.DRDH_processing_frame,
            text='Reactivity is displayed as a: beta',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.Reactivity_change_unit.grid(
            row=2, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
        )

        self.mean_position_label = tk.Label(
            self.DRDH_processing_frame,
            text='Mean group position column: hidden',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.mean_position_label.grid(
            row=3, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
        )

        # Hint for the user: what is expected right now (right-bottom corner)
        self.status_label = tk.Label(
            self.DRDH_processing_frame,
            text="",
            font=FONTS['TEXT_FONT'],
            bg=COLORS['BACKGROUND_COLOR'],
            justify="center",
            anchor="center",
            wraplength=TABLE['CELL_WIDTH'] * 2
        )
        self.status_label.grid(
            row=5, column=3,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'],
            sticky="nsew"
        )

    def checkbox(self):
        """
        Create a checkbox changing reactivity units between:
        - Beta effective (Beff)
        - Percent (%)
        """
        self.checkbox_var = tk.IntVar(value=0)
        self.checkbox_text = tk.StringVar(value="beta")
        self.reactivity_checkbox = tk.Checkbutton(
            self.DRDH_processing_frame,
            variable=self.checkbox_var,
            textvariable=self.checkbox_text,
            command=self.change_checkbox_text,
            bg=COLORS['BACKGROUND_COLOR'],
            font=FONTS['TEXT_FONT']
        )
        self.reactivity_checkbox.grid(
            row=2, column=1,
            padx=GAPS['GAPS_X']['PAD_X_5'],
            sticky="w"
        )

    def mean_position_checkbox(self):
        """
        Create a checkbox showing or hiding the column with the mean position
        of the reference group - the abscissa the DRDH is plotted against.
        """
        self.mean_position_var = tk.IntVar(value=0)
        self.mean_position_text = tk.StringVar(value="hidden")
        self.mean_position_check = tk.Checkbutton(
            self.DRDH_processing_frame,
            variable=self.mean_position_var,
            textvariable=self.mean_position_text,
            command=self.change_mean_position_text,
            bg=COLORS['BACKGROUND_COLOR'],
            font=FONTS['TEXT_FONT']
        )
        self.mean_position_check.grid(
            row=3, column=1,
            padx=GAPS['GAPS_X']['PAD_X_5'],
            sticky="w"
        )

    def mean_position_shown(self) -> bool:
        """True while the mean position column is displayed."""
        return (
            hasattr(self, "mean_position_var")
            and self.mean_position_var.get() == 1
        )

    def change_mean_position_text(self):
        """Auxiliary method. Show or hide the mean position column."""
        name = "shown" if self.mean_position_shown() else "hidden"

        self.mean_position_text.set(name)
        self.mean_position_label.configure(
            text=f'Mean group position column: {name}'
        )

        self.tree.configure(displaycolumns=self.get_visible_columns())
        self.refresh_column_headings()

    def reactivity_in_percent(self) -> bool:
        """True while the reactivity is displayed in percent."""
        return (
            hasattr(self, "checkbox_var")
            and self.checkbox_var.get() == 1
        )

    def reactivity_unit(self) -> str:
        """Suffix of the currently selected reactivity unit."""
        return "%" if self.reactivity_in_percent() else "Beff"

    def to_display_reactivity(self, value: float) -> float:
        """
        Convert a reactivity from Beff (as stored) into the unit currently
        selected by the user.
        """
        return Formulas.beff_to_display(
            value, self.reactivity_in_percent(), self.beta
        )

    def change_checkbox_text(self):
        """
        Auxiliary method. Update labels when switching between beta and
        percent reactivity units.
        """
        name = "%" if self.reactivity_in_percent() else "beta"

        self.checkbox_text.set(name)
        self.Reactivity_change_unit.configure(
            text=f'Reactivity is displayed as a: {name}'
        )

        self.update_labels()

    def update_labels(self):
        """
        Refresh every displayed reactivity after the unit or the number of
        decimal places has been changed.
        """
        had_drdc_block = bool(self.drdc_rows)

        self.refresh_results_table()

        # refresh_results_table() drops the block, so rebuild it if it was
        # shown before the unit or the decimals were changed.
        if had_drdc_block:
            self.add_drdc_block(self.get_drdc_results())

        if self.values_window_alive():
            self.refresh_line_tables()

            if hasattr(self, "t"):
                self.update_drdh_table()

    def buttons(self):
        """
        Create buttons to:
        - Compute the DRDH
        - Save results
        - Back navigation
        - User guide
        """
        self.Proceed_button = TestButtons(
              self.DRDH_processing_frame,
              text='Proceed',
              command=self.proceed,
        )
        self.Proceed_button.grid(
            row=4, column=0,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10']
        )

        self.save_button = TestButtons(
              self.DRDH_processing_frame,
              text='Save',
              command=self.choose_save_format,
        )
        self.save_button.grid(
            row=4, column=1,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10']
        )

        self.BACK_button = MainButtons(
              self.DRDH_processing_frame,
              text='<< BACK',
              command=lambda: self.back(self.DRDH_processing_frame),
        )
        self.BACK_button.grid(
            row=5, column=0,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10']
        )

        self.INFO_button = MainButtons(
              self.DRDH_processing_frame,
              text='User guide',
              command=lambda: show_info(self.root, "DRDH/info_processing.txt"),
        )
        self.INFO_button.grid(
            row=5, column=1,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10']
        )

        self.fix1 = TestButtons(
            self.DRDH_processing_frame, text="Fix 1", command=self.fix_first
        )
        self.fix1.grid(row=4, column=2)

        self.fix2 = TestButtons(
            self.DRDH_processing_frame, text="Fix 2", command=self.fix_second
        )
        self.fix2.grid(row=4, column=3)

        self.delete_last_step_button = TestButtons(
            self.DRDH_processing_frame,
            text="Remove previous step",
            command=self.delete_last_step,
        )
        self.delete_last_step_button.grid(row=4, column=4)

        self.complete_button = TestButtons(
              self.DRDH_processing_frame,
              text='Complete',
              command=self.complete,
        )
        self.complete_button.grid(
            row=5, column=2,
            pady=GAPS['GAPS_Y']['PAD_Y_10']
        )

    def create_menu(self):
        """
        Create the top menu bar for ITC_module window.

        Includes:
        - Decimal precision settings
        - Info
        - Save results
        - Plot tools
        """
        root_window = self.root.winfo_toplevel()
        root_window.config(menu=None)

        self.menu_bar = tk.Menu(root_window)
        root_window.config(menu=self.menu_bar)

        Decimal = tk.Menu(self.menu_bar, tearoff=1)
        self.menu_bar.add_cascade(label="Decimal", menu=Decimal)

        for decimal_type in (
            "DRDC",
            "Reactivity",
            "Group position",
            "DRDH",
            "Boric acid concentration",
        ):
            Decimal.add_command(
                label=f"{decimal_type} decimal",
                font=FONTS['DATA_FONT'],
                command=lambda t=decimal_type: self.set_decimal(t)
            )

        info = tk.Menu(self.menu_bar, tearoff=1)
        self.menu_bar.add_cascade(label="INFO", menu=info)

        info.add_command(
            label="INFO",
            font=FONTS['DATA_FONT'],
            command=lambda: show_info(self.root, "DRDH/info_processing.txt")
        )

        save = tk.Menu(self.menu_bar, tearoff=1)
        self.menu_bar.add_cascade(label="Save", menu=save)

        save.add_command(
            label="Save to Excel",
            font=FONTS['DATA_FONT'],
            command=self.save_to_Excel
        )
        save.add_command(
            label="Save in '.txt'",
            font=FONTS['DATA_FONT'],
            command=self.save_to_txt
        )

        save = tk.Menu(self.menu_bar, tearoff=1)
        self.menu_bar.add_cascade(label="Plot", menu=save)

        save.add_command(
            label="Plot in new window",
            font=FONTS['DATA_FONT'],
            command=self.open_plot_in_new_window
        )
        save.add_command(
            label="Extended cursor",
            font=FONTS['DATA_FONT'],
            command=self.extended_cursor
        )
        experiment_parameters = tk.Menu(
            self.menu_bar,
            tearoff=1
        )
        self.menu_bar.add_cascade(
            label="Computed parameters",
            menu=experiment_parameters
        )

        experiment_parameters.add_command(
            label="Edit parameters",
            font=FONTS['DATA_FONT'],
            command=self.open_experiment_parameters
        )
        current_actions = tk.Menu(self.menu_bar, tearoff=1)
        self.menu_bar.add_cascade(
            label="Current_actions", menu=current_actions
        )

        current_actions.add_command(
            label="DRDH plot",
            font=FONTS['DATA_FONT'],
            command=self.create_drdh_plot
        )
        current_actions.add_command(
            label="Current values",
            font=FONTS['DATA_FONT'],
            command=self.display_current_values
        )

    def open_experiment_parameters(self) -> None:
        if (
                hasattr(self, "experiment_parameters_window")
                and self.experiment_parameters_window.winfo_exists()
        ):
            self.experiment_parameters_window.lift()
            self.experiment_parameters_window.focus_force()
            return

        window = tk.Toplevel(self.root)
        window.title("Computed parameters")
        window.resizable(False, False)
        window.config(bg=COLORS['PARAMETERS_BACKGROUND_COLOR'])
        self.experiment_parameters_window = window

        frame = tk.Frame(window, bg=COLORS['PARAMETERS_BACKGROUND_COLOR'])
        frame.grid(
            row=0, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_10']
        )

        parameters = [
            ("Group length:", "Group_length", self.Group_length),
            ("Overlap:", "overlap", self.overlap),
            ("DRDC:", "DRDC", self.DRDC),
            ("Boric acid start:", "boric_acid_start", self.boric_acid_start),
            ("Boric acid finish:", "boric_acid_finish", self.boric_acid_finish),
        ]

        self.experiment_parameter_vars = {}
        self.experiment_parameter_entries = {}

        for row, (label_text, parameter_name, value) in enumerate(parameters):
            tk.Label(
                frame,
                text=label_text,
                font=FONTS['DATA_FONT'],
                bg=COLORS['PARAMETERS_BACKGROUND_COLOR']
            ).grid(
                row=row,
                column=0,
                padx=GAPS['GAPS_X']['PAD_X_10'],
                pady=GAPS['GAPS_Y']['PAD_Y_5'],
                sticky="w"
            )

            var = tk.StringVar(
                value="" if value is None else str(value)
            )
            self.experiment_parameter_vars[parameter_name] = var

            entry = tk.Entry(
                frame,
                width=ENTRY_WIDTH,
                textvariable=var,
                font=FONTS['DATA_FONT']
            )
            self.experiment_parameter_entries[parameter_name] = entry
            entry.grid(
                row=row,
                column=1,
                padx=GAPS['GAPS_X']['PAD_X_10'],
                pady=GAPS['GAPS_Y']['PAD_Y_5']
            )

        button_frame = tk.Frame(frame, bg=COLORS['PARAMETERS_BACKGROUND_COLOR'])
        button_frame.grid(
            row=len(parameters),
            column=0,
            columnspan=2,
            pady=GAPS['GAPS_Y']['PAD_Y_10_20']
        )

        self.apply_parameters_button = TestButtons(
            button_frame,
            text="Apply",
            command=self.apply_experiment_parameters,
        )
        self.apply_parameters_button.grid(
            row=0, column=0,
            padx=GAPS['GAPS_X']['PAD_X_5']
        )

        self.cancel_parameters_button = MainButtons(
            button_frame,
            text="Cancel",
            command=self.close_experiment_parameters,
        )
        self.cancel_parameters_button.grid(
            row=0, column=1,
            padx=GAPS['GAPS_X']['PAD_X_5']
        )

        window.protocol(
            "WM_DELETE_WINDOW",
            self.close_experiment_parameters
        )
        window.bind(
            "<Return>",
            lambda event: self.apply_experiment_parameters()
        )
        window.bind(
            "<Escape>",
            lambda event: self.close_experiment_parameters()
        )

    def _format_parameter_value(self, value) -> str:
        """Convert a parameter value to text for the edit field."""

        if value is None:
            return ""

        try:
            return str(value)
        except Exception:
            return ""

    def apply_experiment_parameters(self) -> None:
        """
        Validate and apply edited experiment parameters.

        Changes are applied to the current DRDH_processing instance only.
        """

        values = {}

        required_parameters = {
            "Group_length",
            "overlap",
        }

        optional_parameters = {
            "DRDC",
            "boric_acid_start",
            "boric_acid_finish",
        }

        for parameter_name, var in self.experiment_parameter_vars.items():

            text = var.get().strip().replace(",", ".")

            # ---------------------------------------------------------
            # Empty value
            # ---------------------------------------------------------
            if not text:

                if parameter_name in required_parameters:
                    Messages.show(
                        "error",
                        "VALUE_ERROR",
                        value_name=parameter_name,
                        error="Value cannot be empty"
                    )

                    self.experiment_parameter_entries[
                        parameter_name
                    ].focus_set()

                    return

                # Optional parameter
                values[parameter_name] = None
                continue

            # ---------------------------------------------------------
            # Convert to float
            # ---------------------------------------------------------
            try:
                values[parameter_name] = float(text)

            except ValueError as error:
                Messages.show(
                    "error",
                    "VALUE_ERROR",
                    value_name=parameter_name,
                    error=error
                )

                self.experiment_parameter_entries[
                    parameter_name
                ].focus_set()

                return

        # ---------------------------------------------------------
        # Validation
        # ---------------------------------------------------------

        if values["Group_length"] <= 0:
            Messages.show(
                "error",
                "VALUE_POSTIVE",
                value="Group length",
                sign="positive"
            )
            return

        if values["overlap"] < 0:
            Messages.show(
                "error",
                "VALUE_POSTIVE",
                value="Overlap",
                sign="positive"
            )
            return

        if values["overlap"] > 100:
            Messages.show(
                "error",
                "VALUE_ERROR",
                value_name="Overlap",
                error="Overlap must not exceed 100 %"
            )
            return

        if values["DRDC"] is not None and values["DRDC"] > 0:
            Messages.show(
                "error",
                "VALUE_POSTIVE",
                value="DRDC",
                sign="negative"
            )
            return

        if (
                values["boric_acid_start"] is not None
                and values["boric_acid_start"] < 0
        ):
            Messages.show(
                "error",
                "VALUE_POSTIVE",
                value="C(H₃BO₃) initial",
                sign="positive"
            )
            return

        if (
                values["boric_acid_finish"] is not None
                and values["boric_acid_finish"] < 0
        ):
            Messages.show(
                "error",
                "VALUE_POSTIVE",
                value="C(H₃BO₃) final",
                sign="positive"
            )
            return

        # ---------------------------------------------------------
        # Apply
        # ---------------------------------------------------------

        self.Group_length = values["Group_length"]
        self.overlap = values["overlap"]
        self.DRDC = values["DRDC"]
        self.boric_acid_start = values["boric_acid_start"]
        self.boric_acid_finish = values["boric_acid_finish"]

        # Update temporary fields to normalized values.
        for parameter_name, value in values.items():
            self.experiment_parameter_vars[
                parameter_name
            ].set(str(value))

        self.close_experiment_parameters()

    def close_experiment_parameters(self) -> None:
        """Close the experiment parameters window."""

        if (
                hasattr(self, "experiment_parameters_window")
                and self.widget_alive(self.experiment_parameters_window)
        ):
            self.experiment_parameters_window.grab_release()
            self.experiment_parameters_window.destroy()

        for attr in (
                "experiment_parameters_window",
                "experiment_parameter_vars",
                "experiment_parameter_entries",
        ):
            if hasattr(self, attr):
                delattr(self, attr)

    def create_drdh_plot(self):
        """
        Open the "DRDH plot" window: differential worth against the group
        position. Every measurement made so far is drawn immediately, and
        every new one appears online.
        """
        if (
            hasattr(self, "drdh_plot_window")
            and self.widget_alive(self.drdh_plot_window)
        ):
            self.drdh_plot_window.lift()
            self.drdh_plot_window.focus_force()
            return

        win = tk.Toplevel(self.root)
        win.title("DRDH plot")
        win.geometry("900x700")
        self.drdh_plot_window = win
        win.protocol("WM_DELETE_WINDOW", self.close_drdh_plot_window)

        frame = tk.Frame(win, bg="white")
        frame.pack(fill=tk.BOTH, expand=True)

        fig = Figure(figsize=(9, 7))
        canvas = FigureCanvasTkAgg(fig, master=frame)

        # The toolbar has to be packed BEFORE the canvas: the canvas expands
        # over the whole frame and would otherwise squeeze the toolbar out.
        toolbar = NavigationToolbar2Tk(canvas, frame)
        toolbar.update()
        toolbar.pack(side=tk.TOP, fill=tk.X)

        buttons_frame = tk.Frame(frame, bg="white")
        buttons_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.save_drdh_plot_button = SmallButtons(
            buttons_frame,
            text="Save plot",
            command=self.save_drdh_plot,
        )
        self.save_drdh_plot_button.pack(
            side=tk.LEFT, padx=GAPS['GAPS_X']['PAD_X_10'], pady=5
        )

        self.save_drdh_data_button = SmallButtons(
            buttons_frame,
            text="Save data",
            command=self.save_drdh_data,
        )
        self.save_drdh_data_button.pack(
            side=tk.LEFT, padx=GAPS['GAPS_X']['PAD_X_10'], pady=5
        )

        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.drdh_plot = {"fig": fig, "canvas": canvas}

        # The window may be opened at any moment - show the whole history
        self.draw_drdh_plot()

    def save_drdh_plot(self):
        """
        Save the DRDH plot as an image.

        Vector format (PDF) keep the quality at any scale and ignore
        the DPI; PNG is rendered at 300 DPI, which is enough for printing.
        """
        if not getattr(self, "drdh_plot", None):
            return

        initial_dir = os.path.dirname(os.path.abspath(__file__))

        filename = filedialog.asksaveasfilename(
            initialdir=initial_dir,
            defaultextension=".png",
            filetypes=[
                ("PNG image", "*.png"),
                ("PDF document", "*.pdf"),
            ],
            title="Save DRDH plot"
        )

        if not filename:
            return

        self.drdh_plot["fig"].savefig(
            filename, dpi=300, bbox_inches="tight"
        )

    def save_drdh_data(self):
        """
        Save the points of the DRDH plot as a tab separated text file, so
        that the curve can be replotted in any other program.
        """
        points = [p for p in self.drdh_points if p["u"] is not None]

        if not points:
            Messages.show("warning", "NO_DRDH_RESULTS")
            return

        initial_dir = os.path.dirname(os.path.abspath(__file__))

        filename = filedialog.asksaveasfilename(
            initialdir=initial_dir,
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            title="Save DRDH plot data"
        )

        if not filename:
            return

        points = sorted(points, key=lambda p: p["u"])
        factor = DRDH_ERROR['SIGMA_FACTOR']

        with open(filename, "w", encoding="utf-8") as f:
            f.write(
                "\t".join([
                    "Position, %",
                    "DRDH, pcm/cm",
                    f"+/-{factor:g}sigma, pcm/cm",
                    "Reference group"
                ]) + "\n"
            )

            for p in points:
                f.write(
                    "\t".join([
                        f"{p['u']:.{self.DECIMAL_GROUP}f}",
                        f"{p['DRDH']:.{self.DECIMAL_DRDH}f}",
                        f"{p['sigma'] * factor:.{self.DECIMAL_DRDH}f}",
                        str(p["ref_group"] or "")
                    ]) + "\n"
                )

    def close_drdh_plot_window(self):
        """Drop the references when the user closes the DRDH plot window."""
        for attr in ("drdh_plot", "save_drdh_plot_button",
                     "save_drdh_data_button"):
            if hasattr(self, attr):
                delattr(self, attr)

        if hasattr(self, "drdh_plot_window"):
            win = self.drdh_plot_window
            del self.drdh_plot_window
            win.destroy()

    def draw_drdh_plot(self):
        """(Re)draw the DRDH plot. Silently does nothing if it is closed."""
        if not (
            hasattr(self, "drdh_plot")
            and hasattr(self, "drdh_plot_window")
            and self.widget_alive(self.drdh_plot_window)
        ):
            return

        fig = self.drdh_plot["fig"]

        # Rebuilding the axes also drops the group rulers of the previous draw
        fig.clear()
        ax = fig.add_subplot(111)

        n_rulers = max(len(self.moving_order), 1)
        fig.subplots_adjust(
            bottom=0.10 + DRDH_PLOT['RULER_GAP'] * n_rulers,
            left=0.11, right=0.97, top=0.95
        )

        offsets = self.get_group_offsets()

        points = [p for p in self.drdh_points if p["u"] is not None]
        points.sort(key=lambda p: p["u"])

        # The rulers stop at 100 %, but a group may physically go a bit
        # further (e.g. 103.66 %), so the axis still has to show such points.
        ruler_end = (
            (max(offsets.values()) if offsets else 0.0)
            + DRDH_PLOT['RULER_MAX']
        )
        u_min = min([0.0] + [p["u"] for p in points])
        u_max = max([ruler_end] + [p["u"] for p in points])

        if points:
            us = np.array([p["u"] for p in points])
            ys = np.array([p["DRDH"] for p in points])
            errs = np.array([
                p["sigma"] * DRDH_ERROR['SIGMA_FACTOR'] for p in points
            ])

            ax.plot(
                us, ys,
                color=DRDH_PLOT['LINE_COLOR'],
                linewidth=DRDH_PLOT['LINE_WIDTH'],
                zorder=4
            )
            ax.errorbar(
                us, ys, yerr=errs,
                fmt='o',
                color=DRDH_PLOT['POINT_COLOR'],
                markersize=DRDH_PLOT['POINT_SIZE'],
                ecolor=DRDH_PLOT['ERROR_COLOR'],
                elinewidth=DRDH_PLOT['ERROR_WIDTH'],
                capsize=DRDH_PLOT['ERROR_CAPSIZE'],
                capthick=DRDH_PLOT['ERROR_WIDTH'],
                linestyle='none',
                label="Experiment",
                zorder=5
            )
            ax.legend(frameon=True, loc="best")

            top = float(np.max(ys + errs))
            bottom = float(np.min(ys - errs))
            margin = 0.12 * max(top - bottom, 1e-9)
            ax.set_ylim(min(0.0, bottom - margin), top + margin)

        ax.set_ylabel(DRDH_PLOT['Y_LABEL'], fontsize=PLOT['PLOT_LABEL_SIZE'])
        ax.set_xlim(u_min - 3, u_max + 3)
        ax.grid(
            True,
            color=DRDH_PLOT['GRID_COLOR'],
            linewidth=DRDH_PLOT['GRID_WIDTH']
        )
        ax.set_axisbelow(True)

        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)

        # The common axis itself is meaningless for the user - only the
        # per-group rulers below it are.
        ax.xaxis.set_visible(False)

        self.draw_group_rulers(ax, offsets)

        self.drdh_plot["canvas"].draw_idle()

    def draw_group_rulers(self, ax, offsets):
        """
        One 0..100 % ruler per moving group, shifted by the overlap, so that
        the handover point of two groups falls on the same vertical line.
        """
        step = DRDH_PLOT['RULER_STEP']
        gap = DRDH_PLOT['RULER_GAP']

        top = DRDH_PLOT['RULER_MAX']

        for k, gi in enumerate(self.moving_order):
            off = offsets[gi]

            ruler = ax.secondary_xaxis(
                -gap * (k + 1),
                functions=(
                    lambda u, o=off: u - o,
                    lambda p, o=off: p + o
                )
            )
            ruler.set_xticks(np.arange(0, top + 1, step))
            ruler.spines["bottom"].set_bounds(0, top)
            ruler.tick_params(labelsize=7, length=3)
            ruler.set_xlabel(
                self.Group_names[gi],
                labelpad=-26,
                x=-0.02,
                ha="right",
                fontsize=8,
                fontweight="bold"
            )

    def close_values_window(self):
        """Drop references to the 'Current values' window on close."""
        for attr in ("first_line_table", "second_line_table", "drdh_table",
                     "first_line_frame", "second_line_frame", "bottom_frame"):
            if hasattr(self, attr):
                delattr(self, attr)

        if hasattr(self, "values_window"):
            win = self.values_window
            del self.values_window
            win.destroy()

    def display_current_values(self):

        # Only one window at a time
        if self.values_window_alive():
            self.values_window.lift()
            self.values_window.focus_force()
            return

        self.values_window = tk.Toplevel(self.root)
        self.values_window.title("Current DRDH values")
        self.values_window.geometry("900x600")
        self.values_window.configure(bg=COLORS['BACKGROUND_COLOR'])

        main_frame = tk.Frame(
            self.values_window, bg=COLORS['BACKGROUND_COLOR']
        )
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        title = tk.Label(
            main_frame,
            text="Current DRDH values",
            font=FONTS['TITLE_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
        )
        title.pack(anchor="center", pady=(0, 10))

        canvas_frame = tk.Frame(main_frame, bg=COLORS['BACKGROUND_COLOR'])
        canvas_frame.pack(fill="both", expand=True)

        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.rowconfigure(1, weight=1)
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.columnconfigure(1, weight=1)

        self.first_line_frame = tk.Frame(
            canvas_frame, bg=COLORS['BACKGROUND_COLOR']
        )
        self.first_line_frame.grid(
            row=0, column=0, sticky="nsew", padx=5, pady=5
        )

        self.second_line_frame = tk.Frame(
            canvas_frame, bg=COLORS['BACKGROUND_COLOR']
        )
        self.second_line_frame.grid(
            row=0, column=1, sticky="nsew", padx=5, pady=5
        )

        self.bottom_frame = tk.Frame(
            canvas_frame, bg=COLORS['BACKGROUND_COLOR']
        )
        self.bottom_frame.grid(
            row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5
        )

        self.values_window.protocol(
            "WM_DELETE_WINDOW", self.close_values_window
        )

        self.create_first_line_table()
        self.create_second_line_table()
        self.create_drdh_table()

        # The window may be opened AFTER the points were already clicked,
        # so it has to be filled from the current state, not left empty.
        self.refresh_line_tables()

        if hasattr(self, "t"):
            self.update_drdh_table()

    def refresh_line_tables(self):
        """
        Fill the 'First/Second line parameters' tables from the current
        selection state. Row layout of each table:
            row 0      - R of the left point
            row 1      - R of the right point
            row 2..N+1 - group positions at the left point
        """
        if not self.values_window_alive():
            return

        pairs = (
            ("interval1", self.first_line_table),
            ("interval2", self.second_line_table),
        )

        unit = self.reactivity_unit()

        for num, (key, table) in enumerate(pairs, start=1):
            state = self.selection_state[key]
            rows = table.get_children()

            # clear, and keep the unit of the two reactivity rows up to date
            for i, row in enumerate(rows):
                table.set(row, "value", "")

                if i < 2:
                    table.set(row, "param", f"R{num}_{i + 1}, {unit}")

            if state["left"]:
                R = self.to_display_reactivity(state["left"]["R"])
                table.set(rows[0], "value", f"{R:.{self.DECIMAL_REACT}f}")

                for i, val in enumerate(state["left"]["groups"]):
                    table.set(
                        rows[i + 2], "value",
                        f"{val:.{self.DECIMAL_GROUP}f}"
                    )

            if state["right"]:
                R = self.to_display_reactivity(state["right"]["R"])
                table.set(rows[1], "value", f"{R:.{self.DECIMAL_REACT}f}")

    def create_table(self):

        style = ttk.Style(self.root)
        style.configure("DRDH.Treeview", font=FONTS['DATA_FONT'])
        style.configure(
            "DRDH.Treeview.Heading", font=FONTS['HEADING_FONT']
        )

        self.right_frame = tk.Frame(
            self.splitter_window,
            bg=COLORS['PARAMETERS_BACKGROUND_COLOR'],
            highlightthickness=0,
        )
        self.splitter_window.add(
            self.right_frame,
            minsize=SPLITTER_MINSIZES['RIGHT'],
            stretch="always"
        )

        # Every group is followed by its own mean position column, so that
        # simultaneously moving groups both get an abscissa of their own.
        self.columns = ['dR', 'R', 'DRDH']

        for name in self.Group_names:
            self.columns += [name, f"{name}_mean"]

        self.tree = tk.ttk.Treeview(
            self.right_frame, columns=self.columns,
            show="headings", height=TABLE['CELL_HEIGHT'],
            style="DRDH.Treeview", selectmode="none"
        )

        for col in self.columns:
            self.tree.column(
                col, width=TABLE['CELL_WIDTH'], anchor="center"
            )

        self.tree.configure(displaycolumns=self.get_visible_columns())
        self.refresh_column_headings()

        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<Button-1>", self.on_tree_click)
        self.tree.bind("<Control-c>", self.copy_from_entry)
        self.tree.bind("<Control-C>", self.copy_from_entry)

    def on_tree_click(self, event):
        """
        Proceed with a click on table cell.

        Allows to copy cell contents.
        """
        self.close_active_entry()

        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return "break"

        row_id = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)

        if not row_id or not column:
            return "break"

        col_index = int(column.replace("#", "")) - 1
        bbox = self.tree.bbox(row_id, column)
        if not bbox:
            return "break"

        x, y, width, height = bbox
        value = self.tree.item(row_id, "values")[col_index]

        entry = ttk.Entry(self.tree)
        entry.insert(0, value)
        entry.state(["readonly"])
        entry.select_range(0, tk.END)
        entry.focus()

        entry.place(x=x, y=y, width=width, height=height)

        self.active_entry = entry

        return "break"

    def close_active_entry(self):
        """
        "Auxiliary method. 'Close' a cell of the result table."
        """
        if self.active_entry is not None:
            self.active_entry.destroy()
            self.active_entry = None

    def copy_from_entry(self, event=None):
        """Auxiliary method. Copy selected table cell content."""
        if self.active_entry is None:
            return "break"

        text = self.active_entry.get()
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

        return "break"

    def get_table_data(self):
        """
        Auxiliary method. Aimes at providing opportunity to save the result.
        Extract all table rows as a list of values.

        Returns:
            List[List[str]]: Table data rows.
        """
        indices = [
            self.columns.index(col) for col in self.get_visible_columns()
        ]

        data = []
        for item_id in self.tree.get_children():
            values = self.tree.item(item_id, "values")
            data.append([
                values[i] if i < len(values) else "" for i in indices
            ])
        return data

    def save_to_Excel(self):
        """
        Export the results table to an Excel file.

        Creates a formatted workbook with auto-sized columns.
        """
        initial_dir = os.path.dirname(os.path.abspath(__file__))

        filename = filedialog.asksaveasfilename(
            initialdir=initial_dir,
            defaultextension=".xlsx",
            filetypes=[
                ("Excel files", "*.xlsx"),
                ("Excel 97-2003", "*.xls")
            ],
            title="Save results"
        )

        if not filename:
            return

        wb = Workbook()
        ws = wb.active
        ws.title = "Results"

        ws.append(self.get_column_headings())
        for col in range(1, len(self.columns) + 1):
            cell = ws.cell(row=1, column=col)
            cell.font = FONTS['EXCEL_FONT']

        for row_idx, row in enumerate(self.get_table_data(), start=2):
            for col_idx, value in enumerate(row, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.font = FONTS['EXCEL_FONT']

        for col_idx, col_name in enumerate(self.get_column_headings(), start=1):
            max_length = len(str(col_name))

            for row in ws.iter_rows(min_col=col_idx, max_col=col_idx):
                for cell in row:
                    if cell.value is not None:
                        max_length = max(max_length, len(str(cell.value)))

            ws.column_dimensions[
                get_column_letter(col_idx)
            ].width = max_length + 2

        wb.save(filename)

    def save_to_txt(self):
        """
        Export the results table as a tab-separated text file.
        """
        initial_dir = os.path.dirname(os.path.abspath(__file__))

        filename = filedialog.asksaveasfilename(
            initialdir=initial_dir,
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            title="Save results"
        )

        if not filename:
            return

        with open(filename, "w", encoding="utf-8") as f:
            f.write("\t".join(self.get_column_headings()) + "\n")
            for row in self.get_table_data():
                f.write("\t".join(str(cell) for cell in row) + "\n")

    def choose_save_format(self):
        """Select the results export format (Excel or ".txt")."""
        save_window = tk.Toplevel(self.root)
        save_window.title("Save Format")
        save_window.geometry("300x120")
        save_window.config(bg=COLORS['BACKGROUND_COLOR'])
        save_window.grab_set()

        tk.Label(
            save_window, text="Please, choose file format:",
            font=FONTS['DATA_FONT'], bg=COLORS['BACKGROUND_COLOR']
        ).grid(
            row=0, column=0, columnspan=2,
            pady=(10, 20)
            )

        def save_excel():
            """Launch the saving process in the new Excel file."""
            save_window.destroy()
            self.save_to_Excel()

        def save_txt():
            """Launch the saving process in the ".txt" format."""
            save_window.destroy()
            self.save_to_txt()

        self.txt_button = SmallButtons(
              save_window,
              text='.txt',
              command=save_txt,
        )
        self.txt_button.grid(
            row=2, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_0_5']
        )

        self.xls_button = SmallButtons(
              save_window,
              text='Excel',
              command=save_excel,
        )
        self.xls_button.grid(
            row=2, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_0_5']
        )

    def extended_cursor(self):
        """
        Select the extended cursor mode on all open plots.

        If enabled, displays:
        - Crosshair lines
        - Live data parameters
        """
        self.extended_cursor_enabled = not self.extended_cursor_enabled

        for plot in self.plot_windows:

            if self.extended_cursor_enabled:

                cid = plot["canvas"].mpl_connect(
                    "motion_notify_event",
                    lambda event, p=plot: self.on_mouse_move(event, p)
                )
                plot["cursor_cid"] = cid

            else:

                if plot["cursor_cid"] is not None:
                    plot["canvas"].mpl_disconnect(plot["cursor_cid"])
                    plot["cursor_cid"] = None

                plot["cursor_vline"].set_visible(False)
                plot["cursor_hline_R"].set_visible(False)

                for line in plot["cursor_hlines_groups"]:
                    line.set_visible(False)
                plot["cursor_text"].set_visible(False)

                plot["canvas"].draw_idle()

    def on_mouse_move(self, event, plot):
        """
        Update extended cursor tabel parameters according to mouse position.

        Args:
            event: Matplotlib motion event.
            plot (dict): Plot container dictionary.
        """
        if not self.extended_cursor_enabled:
            return

        if plot["toolbar"].mode != '':
            return

        if event.inaxes not in (plot["ax1"], plot["ax2"]):
            return

        if event.xdata is None:
            return

        clicked_time = mdates.num2date(event.xdata).replace(tzinfo=None)

        nearest_index = min(
            range(len(self.times)),
            key=lambda i: abs(self.times[i] - clicked_time)
        )

        time_val = self.times[nearest_index]
        R = float(self.Reactivity[nearest_index])

        plot["cursor_vline"].set_xdata([time_val, time_val])
        plot["cursor_vline"].set_visible(True)

        plot["cursor_hline_R"].set_ydata([R, R])
        plot["cursor_hline_R"].set_visible(True)

        for i, group in enumerate(self.Groups):
            val = float(group[nearest_index])
            line = plot["cursor_hlines_groups"][i]
            line.set_ydata([val, val])
            line.set_visible(True)

        textstr = f"{time_val.strftime('%H:%M:%S')}\nR: {R:.{self.DECIMAL_REACT}f}"

        for i, name in enumerate(self.Group_names):
            val = self.Groups[i][nearest_index]
            textstr += f"\n{name}: {val:.{self.DECIMAL_GROUP}f}"

        plot["cursor_text"].set_text(textstr)
        plot["cursor_text"].set_position((time_val, R))
        plot["cursor_text"].set_visible(True)

        plot["cursor_text"].set_text(textstr)

        # Set the text position next to the current cursor position
        plot["cursor_text"].set_position((time_val, R))
        plot["cursor_text"].set_visible(True)

        plot["canvas"].draw_idle()

    def back(self, window):
        """
        Close DRDH_processing and return to DRDH_module.

        Results remain.

        Args:
            window (tk.Widget): DRDH frame to destroy.
        """
        root_window = self.root.winfo_toplevel()
        root_window.config(menu=None)
        self.root.config(menu=None)

        self.menu_bar.destroy()
        self.menu_bar = None
        window.destroy()
        root_window.config(menu=None)

        self.main_app.create_DRDH_window()

        root_window.title('DRDH')
        root_window.update_idletasks()

    def set_decimal(self, decimal_type):
        """
        Open a dialog to change decimal value for selected value type.

        Args:
            decimal_type (str):
                - Temperature
                - Reactivity
                - Group position
                - General
        """
        decimal_window = tk.Toplevel(self.root)
        decimal_window.title(f"Set {decimal_type} Decimal")
        decimal_window.geometry("230x150")
        decimal_window.config(bg=COLORS['BACKGROUND_COLOR'])

        tk.Label(
            decimal_window,
            text=f"Enter decimal places for {decimal_type}:",
            font=FONTS['DATA_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
        ).grid(
            row=0, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_10_5'],
            sticky='ew'
            )

        entry = ttk.Entry(decimal_window, font=FONTS['DATA_FONT'])
        entry.grid(
            row=1, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_0_5']
        )
        entry.focus_set()

        def save_decimal():
            """Save the Decimal value which was set by the user."""
            try:
                value = int(entry.get())

                attributes = {
                    "DRDC": "DECIMAL_DRDC",
                    "Reactivity": "DECIMAL_REACT",
                    "Group position": "DECIMAL_GROUP",
                    "DRDH": "DECIMAL_DRDH",
                    "Boric acid concentration": "DECIMAL_BORIC",
                }
                setattr(self, attributes[decimal_type], value)

                self.update_labels()

                Messages.show(
                    "info",
                    "DECIMAL_SET",
                    type=decimal_type,
                    value=value
                    )
                decimal_window.destroy()
            except ValueError:
                Messages.show("error", "INVALID_DECIMAL")

        self.decimal_button = SmallButtons(
              decimal_window,
              text='Save',
              command=save_decimal,
        )
        self.decimal_button.grid(
            row=2, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_0_5']
        )
        entry.bind('<Return>', lambda event: save_decimal())

    def mean_concentration_before(self, index: Optional[int]) -> Optional[float]:
        """
        Mean boric acid concentration over the averaging window that ends at
        `index`: from (t - WINDOW_SEC) to t.

        If less than WINDOW_SEC of data exists before the click, whatever is
        available is averaged instead.
        """
        if self.boric_acid_NFME is None or index is None:
            return None

        end_time = self.times[index]
        start_time = end_time - timedelta(seconds=DRDC_WINDOW_SEC)

        indices = [
            i for i in range(index + 1)
            if self.times[i] >= start_time
        ]

        if not indices:
            indices = [index]

        values = [float(self.boric_acid_NFME[i]) for i in indices]

        return float(np.mean(values))

    def get_total_delta_rho(self) -> Optional[float]:
        """
        Reactivity difference of the whole experiment, in Beff.

        It is the last cumulative value of the DRDH table. Everything is kept
        in Beff and converted only when displayed, so the DRDC follows the
        unit selected by the user.
        """
        if not getattr(self, "results_table", None):
            return None

        return self.cumulative_R

    @staticmethod
    def compute_drdc(delta_rho: Optional[float],
                     C_start: Optional[float],
                     C_finish: Optional[float]) -> Optional[float]:
        """DRDC = dRho / dC. Kept as a thin wrapper over Formulas."""
        return Formulas.compute_drdc(delta_rho, C_start, C_finish)

    def get_drdc_results(self) -> Dict[str, Dict[str, Optional[float]]]:
        """
        Both ways of determining the DRDC.

        A method whose concentrations are missing is simply left empty -
        it is not an error.
        """
        delta_rho = self.get_total_delta_rho()

        entered_start = self.boric_acid_start
        entered_finish = self.boric_acid_finish

        file_start = self.mean_concentration_before(self.first_click_index)
        file_finish = self.mean_concentration_before(
            self.last_right_click_index
        )

        results = {
            "entered": {
                "C_start": entered_start,
                "C_finish": entered_finish,
                "delta_rho": delta_rho,
                "DRDC": self.compute_drdc(
                    delta_rho, entered_start, entered_finish
                ),
            },
            "file": {
                "C_start": file_start,
                "C_finish": file_finish,
                "delta_rho": delta_rho,
                "DRDC": self.compute_drdc(
                    delta_rho, file_start, file_finish
                ),
            },
        }

        # The reference DRDC is entered in %/(g/kg), while everything here
        # is kept in Beff/(g/kg), so it has to be converted first.
        reference = None

        if self.DRDC is not None and not np.isclose(self.beta, 0):
            reference = self.DRDC / self.beta

        for data in results.values():
            data["reference"] = reference
            data["deviation"] = None
            data["deviation_pct"] = None

            if data["DRDC"] is not None and reference is not None:
                data["deviation"] = data["DRDC"] - reference

                # A ratio - the same number in either unit
                if not np.isclose(reference, 0):
                    data["deviation_pct"] = (
                        data["deviation"] / abs(reference) * 100.0
                    )

        return results

    def proceed(self):
        if self.current_stage() != "PROCEED":
            Messages.show(
                "error",
                "NOT_READY_TO_PROCEED"
            )
            self.update_hint()
            return

        # Remove yellow dots
        for plot in self.plot_windows:
            for key in ("interval1", "interval2"):
                art = plot["interval_artists"][key]

                if art["left"]:
                    art["left"].remove()
                    art["left"] = None

                if art["right"]:
                    art["right"].remove()
                    art["right"] = None

        for key in ("interval1", "interval2"):
            self.selection_state[key]["dots"] = False

        self.make_interval_lines_infinite()

        # Green intersection dots
        self.draw_intersection_points()

        # Compute DRDH
        # Time dots
        idx1 = self.selection_state["interval1"]["right"]["index"]
        idx2 = self.selection_state["interval2"]["right"]["index"]

        # R1/R2 - ординаты пересечения жёлтых прямых с красной вертикалью.
        # Они уже посчитаны в draw_intersection_points() выше (зелёные точки),
        # поэтому итоговый результат совпадает с онлайн-таблицей
        # в окне "Current values".
        R1 = self.p1_R
        R2 = self.p2_R

        delta_R = R2 - R1

        # The step is referred to a single group - the one that started
        # moving first - and not to the sum of every moving group.
        lead = self.get_leading_group(idx1, idx2)

        if lead is None:
            Messages.show("error", "NO_GROUP_MOVEMENT")
            self.update_hint()
            return

        delta_H = self.Groups[lead][idx2] - self.Groups[lead][idx1]
        delta_H_cm = delta_H * self.Group_length / 100

        # Stored in Beff/cm, like every other reactivity of the table, so
        # that it can be redrawn in the unit chosen by the user.
        DRDH = delta_R / delta_H_cm

        # The DRDH plot keeps the conventional pcm/cm
        delta_rho_pcm = delta_R * 1000 * self.beta
        DRDH_pcm = delta_rho_pcm / delta_H_cm

        self.cumulative_R += delta_R

        group_values = {
            name: self.Groups[i][idx2] for i, name in enumerate(self.Group_names)
        }

        # Point of the "DRDH plot" window. It is appended here and removed
        # again in reject_result(), exactly like the row of the results table.
        ref = self.get_reference_group(idx1, idx2)

        # Mean position of every group that moved - the abscissa the DRDH is
        # plotted against. Groups that stood still get nothing: that way the
        # table also shows which group (or groups) the measurement belongs to.
        mean_positions = {}

        for i, name in enumerate(self.Group_names):
            H1 = self.Groups[i][idx1]
            H2 = self.Groups[i][idx2]

            mean_positions[name] = (
                None if np.isclose(H1, H2) else (H1 + H2) / 2.0
            )

        self.drdh_points.append({
            "u": self.get_program_coordinate(idx1, idx2),
            "DRDH": DRDH_pcm,
            "sigma": self.get_drdh_sigma(
                delta_rho_pcm, delta_H_cm, DRDH_pcm
            ),
            "ref_group": self.Group_names[ref] if ref is not None else None,
            "groups": group_values
        })
        self.draw_drdh_plot()

        self.check_initial_position(idx1)

        self.update_table(
            R=self.cumulative_R, delta_R=delta_R,
            DRDH=DRDH, group_values=group_values,
            mean_positions=mean_positions
        )

        self.ask_result_confirmation()

    def check_initial_position(self, idx1):
        """
        The first row of the table holds the group positions of the very
        first sample of the record. If the determination starts later, those
        positions do not match the beginning of the first measured interval.

        Warn the user once and offer to rewrite that row.
        """
        if self.initial_position_checked:
            return

        if len(getattr(self, "results_table", [])) != 1:
            return

        self.initial_position_checked = True

        first_row = self.results_table[0]
        recorded_groups = first_row.get("groups")

        if not recorded_groups:
            return

        mismatched = []

        for i, name in enumerate(self.Group_names):
            recorded = recorded_groups[name]
            actual = float(self.Groups[i][idx1])

            if not np.isclose(recorded, actual):
                mismatched.append((name, recorded, actual))

        if not mismatched:
            return

        positions = "\n".join(
            f"{name}:  {rec:.{self.DECIMAL_GROUP}f}  ->  "
            f"{act:.{self.DECIMAL_GROUP}f}"
            for name, rec, act in mismatched
        )

        rewrite = Messages.show(
            "question",
            "INITIAL_POSITION_MISMATCH",
            positions=positions
        )

        if not rewrite:
            return

        for i, name in enumerate(self.Group_names):
            recorded_groups[name] = float(self.Groups[i][idx1])

        self.refresh_results_table()

    def ask_result_confirmation(self):
        result = Messages.show(
                "question",
                "SATISFACTORY_RESULT"
            )

        if result:
            self.accept_result()
        else:
            self.reject_result()
        if hasattr(self, "large_plot_window") and self.large_plot_window.winfo_exists():
            self.large_plot_window.lift()
            self.large_plot_window.focus_force()

    def accept_result(self):

        for plot in self.plot_windows:
            if "move_line" in plot and plot["move_line"]:
                plot["move_line"].remove()
                plot["move_line"] = None

            if "green_points" in plot:
                for p in plot["green_points"]:
                    p.remove()
                plot["green_points"] = []

        self.show_move_line = False
        self.show_intersections = False

        state1 = self.selection_state["interval1"]
        state2 = self.selection_state["interval2"]

        # Remember the geometry of the measured line, so that it can be
        # redrawn in a plot window opened later.
        if state1["left"] and state1["right"]:
            self.finished_lines.append({
                "left": state1["left"],
                "right": state1["right"]
            })

        # Artists: interval1 -> black (measured, kept forever),
        #          interval2 -> stays yellow and becomes the new interval1.
        for plot in self.plot_windows:
            art1 = plot["interval_artists"]["interval1"]
            art2 = plot["interval_artists"]["interval2"]

            if art1["line"]:
                self.apply_finished_style(art1["line"])
                plot["finished_lines"].append(art1["line"])

            plot["interval_artists"]["interval1"] = {
                "left": art2["left"],
                "right": art2["right"],
                "line": art2["line"]
            }
            plot["interval_artists"]["interval2"] = {
                "left": None,
                "right": None,
                "line": None
            }

        # State: interval2 -> interval1 (new cycle)
        self.selection_state["interval1"] = {
            "left": state2["left"],
            "right": state2["right"],
            "fixed": True,
            "dots": state2["dots"]
        }
        self.selection_state["interval2"] = {
            "left": None,
            "right": None,
            "fixed": False,
            "dots": False
        }

        # A new cycle starts: line 1 is inherited and locked,
        # the user has to confirm it with "Fix 1" before clicking again.
        self.fix1_done = False
        self.line1_locked = True
        self.active_interval = 1

        self.refresh_line_tables()
        self.draw_drdh_plot()
        self.update_hint()

        for plot in self.plot_windows:
            plot["canvas"].draw_idle()

    def reject_result(self):
        self.clear_drdc_block()

        children = self.tree.get_children()
        if children:
            last_item = children[-1]
            self.tree.delete(last_item)

        if hasattr(self, "results_table") and self.results_table:
            self.results_table.pop()

        if len(self.results_table) > 0:
            self.cumulative_R = self.results_table[-1]["R"]
        else:
            self.cumulative_R = 0.0

        for plot in self.plot_windows:

            if "move_line" in plot and plot["move_line"]:
                plot["move_line"].remove()
                plot["move_line"] = None

            if "green_points" in plot:
                for p in plot["green_points"]:
                    p.remove()
                plot["green_points"] = []

            art2 = plot["interval_artists"]["interval2"]

            for key in ("left", "right", "line"):
                if art2[key]:
                    art2[key].remove()

            plot["interval_artists"]["interval2"] = {
                "left": None,
                "right": None,
                "line": None
            }

        self.show_move_line = False
        self.show_intersections = False

        # interval1 is kept as it is (still yellow, still fixed),
        # only the second interval is dropped and has to be re-selected.
        self.selection_state["interval2"] = {
            "left": None,
            "right": None,
            "fixed": False,
            "dots": False
        }

        # The rejected measurement must disappear from the DRDH plot too
        if self.drdh_points:
            self.drdh_points.pop()
        self.draw_drdh_plot()

        # "Fix 1" stays valid for this cycle - only line 2 is re-selected
        self.active_interval = 2

        self.refresh_line_tables()
        self.update_hint()

        for plot in self.plot_windows:
            plot["canvas"].draw_idle()

    def delete_last_step(self):
        """
        Delete the last accepted DRDH step and return the processing
        to the state that existed immediately before that step.
        """

        # The first row of results_table is the initial state,
        # not a measured step.
        if len(getattr(self, "results_table", [])) <= 1:
            return

        # Remove the DRDC summary, if it is currently displayed.
        self.clear_drdc_block()

        # ---------------------------------------------------------
        # Save the state of the last step before modifying anything.
        # ---------------------------------------------------------
        last_step_line = None

        if self.finished_lines:
            last_step_line = self.finished_lines.pop()

        # The current interval1 is the second line of the last step.
        last_step_second_line = self.selection_state["interval1"]

        # ---------------------------------------------------------
        # Remove the last result from the results table.
        # ---------------------------------------------------------
        children = self.tree.get_children()

        if children:
            self.tree.delete(children[-1])

        self.results_table.pop()

        # Restore cumulative reactivity.
        self.cumulative_R = self.results_table[-1]["R"]

        # ---------------------------------------------------------
        # Remove the last accepted point from the DRDH plot.
        # ---------------------------------------------------------
        if self.drdh_points:
            self.drdh_points.pop()

        # ---------------------------------------------------------
        # Restore selection state.
        #
        # If there are previous accepted steps:
        #
        #     previous step's Fix 2 line
        #             ↓
        #         becomes Fix 1
        #
        # The user must press Fix 1 again before selecting
        # the next pair of points.
        # ---------------------------------------------------------
        if self.finished_lines:

            self.selection_state["interval1"] = {
                "left": last_step_line["left"],
                "right": last_step_line["right"],
                "fixed": True,
                "dots": True,
            }

            self.selection_state["interval2"] = {
                "left": None,
                "right": None,
                "fixed": False,
                "dots": False,
            }

            self.fix1_done = False
            self.line1_locked = True
            self.active_interval = 1

            self.last_right_click_index = (
                last_step_line["right"]["index"]
            )

        # ---------------------------------------------------------
        # If we deleted the very first step, restore the state
        # that existed immediately before its Proceed.
        #
        # In this case:
        #   last_step_line      = original Fix 1
        #   last_step_second_line = original Fix 2
        # ---------------------------------------------------------
        else:

            self.selection_state["interval1"] = {
                "left": last_step_line["left"],
                "right": last_step_line["right"],
                "fixed": True,
                "dots": True,
            }

            self.selection_state["interval2"] = {
                "left": last_step_second_line["left"],
                "right": last_step_second_line["right"],
                "fixed": True,
                "dots": True,
            }

            self.fix1_done = True
            self.line1_locked = False
            self.active_interval = 2

            self.last_right_click_index = (
                last_step_second_line["right"]["index"]
            )

        # ---------------------------------------------------------
        # Restore the plot.
        # ---------------------------------------------------------
        for plot in self.plot_windows:

            # Remove all currently drawn active elements.
            for key in ("interval1", "interval2"):
                art = plot["interval_artists"][key]

                for artist_key in ("left", "right", "line"):
                    artist = art[artist_key]

                    if artist is not None:
                        artist.remove()

                plot["interval_artists"][key] = {
                    "left": None,
                    "right": None,
                    "line": None,
                }

            # Remove the last finished line from this plot.
            if plot["finished_lines"]:
                line = plot["finished_lines"].pop()
                line.remove()

            # Remove temporary movement/intersection graphics.
            if plot.get("move_line"):
                plot["move_line"].remove()
                plot["move_line"] = None

            for point in plot.get("green_points", []):
                point.remove()

            plot["green_points"] = []

            # Redraw active intervals from the restored state.
            for key in ("interval1", "interval2"):
                state = self.selection_state[key]
                art = plot["interval_artists"][key]

                if state["dots"]:
                    if state["left"]:
                        art["left"] = self.draw_selection_point(
                            plot, state["left"]
                        )

                    if state["right"]:
                        art["right"] = self.draw_selection_point(
                            plot, state["right"]
                        )

                if state["left"] and state["right"]:
                    art["line"] = self.draw_interval_line(
                        plot, state
                    )

            plot["canvas"].draw_idle()

        self.show_move_line = False
        self.show_intersections = False

        # Remove the vertical line state.
        for attr in ("t", "t_move", "p1_R", "p2_R"):
            if hasattr(self, attr):
                delattr(self, attr)

        # Refresh all dependent UI.
        self.refresh_line_tables()
        self.refresh_results_table()
        self.draw_drdh_plot()
        self.update_hint()

        if self.values_window_alive():
            self.update_drdh_table()
    def complete(self):
        """
        Finish the processing and determine the DRDC.

        Both methods are attempted; the one whose concentrations are missing
        is left empty. The summary block is (re)built at the bottom of the
        results table, one blank row below the DRDH rows.
        """
        if not getattr(self, "results_table", None):
            Messages.show("warning", "NO_DRDH_RESULTS")
            return

        self.add_drdc_block(self.get_drdc_results())

    def clear_drdc_block(self):
        """Remove the DRDC summary block from the results table."""
        for row_id in self.drdc_rows:
            if self.tree.exists(row_id):
                self.tree.delete(row_id)

        self.drdc_rows = []

    def format_drdc_value(self, value: Optional[float],
                          decimals: Optional[int] = None) -> str:
        """
        Format a value of the DRDC block, or a dash if it is not available.

        Every line of the block has its own quantity, so the number of
        decimals is passed in rather than taken from a single setting.
        """
        if value is None:
            return "-"

        if decimals is None:
            decimals = self.DECIMAL_DRDC

        return f"{value:.{decimals}f}"

    def add_drdc_block(self, results):
        """
        Append the DRDC summary to the results table.

        The block always has the same shape, so the user sees what belongs
        where even when nothing could be computed - missing numbers are
        shown as dashes.
        """
        self.clear_drdc_block()

        entered = results["entered"]
        from_file = results["file"]
        width = len(self.columns)

        def row(*cells):
            """Insert one row, padded to the width of the table."""
            values = list(cells) + [""] * (width - len(cells))
            self.drdc_rows.append(
                self.tree.insert("", "end", values=values[:width])
            )

        fmt = self.format_drdc_value

        # One blank row separates the block from the DRDH results
        row("")

        row("DRDC", "Entered C", "C from file")

        unit = self.reactivity_unit()

        # Concentrations and the relative deviation do not depend on the
        # reactivity unit; everything else is converted.
        for label, key, convert, decimals in (
            ("C initial, g/kg", "C_start", False, self.DECIMAL_BORIC),
            ("C final, g/kg", "C_finish", False, self.DECIMAL_BORIC),
            (f"dR, {unit}", "delta_rho", True, self.DECIMAL_REACT),
            (f"DRDC, {unit}/(g/kg)", "DRDC", True, self.DECIMAL_DRDC),
            (f"DRDC ref., {unit}/(g/kg)", "reference", True, self.DECIMAL_DRDC),
            (f"Deviation, {unit}/(g/kg)", "deviation", True, self.DECIMAL_DRDC),
            ("Deviation, rel. %", "deviation_pct", False, self.DECIMAL_DRDC),
        ):
            values = []

            for data in (entered, from_file):
                value = data[key]

                if convert and value is not None:
                    value = self.to_display_reactivity(value)

                values.append(fmt(value, decimals))

            row(label, *values)

    def update_table(self, R, delta_R, DRDH, group_values,
                     mean_positions=None):
        """
        Add a new row to the results table.

        The reactivity is stored in Beff, as it is measured; the unit chosen
        by the user is applied only when the row is rendered, so the whole
        table can be redrawn on the fly.
        """
        new_row = {
            "R": R,
            "dR": delta_R,
            "DRDH": DRDH,
            "mean_positions": mean_positions or {},
            "groups": {
                name: group_values.get(name, 0.0)
                for name in self.Group_names
            },
        }

        if not hasattr(self, "results_table"):
            self.results_table = []
        self.results_table.append(new_row)

        # The DRDC block must always stay at the very bottom of the table
        self.clear_drdc_block()

        self.tree.insert("", "end", values=self.format_result_row(new_row))

    def format_result_row(self, row):
        """Render one stored result row in the currently selected unit."""
        delta_R = self.to_display_reactivity(row["dR"])
        R = self.to_display_reactivity(row["R"])
        DRDH = self.to_display_reactivity(row["DRDH"])

        cells = [
            f"{delta_R:.{self.DECIMAL_REACT}f}",
            f"{R:.{self.DECIMAL_REACT}f}",
            f"{DRDH:.{self.DECIMAL_DRDH}f}",
        ]

        means = row.get("mean_positions") or {}

        for name in self.Group_names:
            cells.append(
                f"{row['groups'][name]:.{self.DECIMAL_GROUP}f}"
            )

            mean = means.get(name)
            cells.append(
                "-" if mean is None
                else f"{mean:.{self.DECIMAL_GROUP}f}"
            )

        return cells

    def get_visible_columns(self):
        """
        Identifiers of the columns currently shown. The mean position column
        always exists and is only hidden, so no data is ever lost.
        """
        if self.mean_position_shown():
            return self.columns

        return [
            col for col in self.columns if not col.endswith("_mean")
        ]

    def get_column_headings(self):
        """Titles of the visible columns, with the current units."""
        unit = self.reactivity_unit()

        titles = {
            "dR": f"dR, {unit}",
            "R": f"R, {unit}",
            "DRDH": f"DRDH, {unit}/cm",
        }

        for name in self.Group_names:
            titles[name] = f"{name}, %"
            titles[f"{name}_mean"] = f"{name} mean, %"

        return [titles[col] for col in self.get_visible_columns()]

    def refresh_column_headings(self):
        """Apply the current titles to the visible columns."""
        for col, title in zip(
            self.get_visible_columns(), self.get_column_headings()
        ):
            self.tree.heading(col, text=title)

    def refresh_results_table(self):
        """
        Redraw the whole results table: after the reactivity unit or the
        number of decimal places has been changed.
        """
        self.clear_drdc_block()

        self.refresh_column_headings()

        for item_id in self.tree.get_children():
            self.tree.delete(item_id)

        for row in getattr(self, "results_table", []):
            self.tree.insert("", "end", values=self.format_result_row(row))

    def create_plot(self, parent, large=False):
        """
        Create a plot(s) with three axes:
        - Reactivity
        - Temperature
        - Group position

        Args:
            parent: Tkinter container.
            large (bool): If True, creates an enlarged plot.
        """

        if large:
            fig = Figure(figsize=(10, 6), constrained_layout=True)
        else:
            fig = Figure(figsize=(5, 3.5), constrained_layout=True)
        ax1 = fig.add_subplot(111)

        self.times = [
            datetime(1899, 12, 30) + timedelta(days=t) for t in self.Time
        ]

        ax1.plot(
            self.times, self.Reactivity,
            color=PLOT_STYLE['REACTIVITY_COLOR'],
            linewidth=PLOT_STYLE['REACTIVITY_WIDTH'],
            label="Reactivity, Beff"
        )
        ax1.set_ylabel("Reactivity, Beff", fontsize=PLOT['PLOT_LABEL_SIZE'])
        ax1.grid(
            True,
            color=PLOT_STYLE['GRID_COLOR'],
            linewidth=PLOT_STYLE['GRID_WIDTH'],
            zorder=0
        )
        ax1.set_axisbelow(True)

        for spine in ("top", "right"):
            ax1.spines[spine].set_visible(False)

        ax2 = ax1.twinx()
        ax1.set_autoscale_on(False)
        ax2.set_autoscale_on(False)

        for i, group in enumerate(self.Groups):
            name = self.Group_names[i]

            ax2.plot(
                self.times, group,
                linestyle='--',
                linewidth=PLOT_STYLE['GROUP_WIDTH'],
                alpha=PLOT_STYLE['GROUP_ALPHA'],
                color=GROUP_COLORS[name],
                label=name
            )

        ax2.set_ylabel("Group position, %")
        ax2.set_ylim(0, 110)

        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        fig.autofmt_xdate()
        ax1.set_xlabel("Time")

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.bind(
            "<Enter>", lambda e: canvas_widget.config(cursor="crosshair")
        )
        canvas_widget.bind(
            "<Leave>", lambda e: canvas_widget.config(cursor="arrow")
        )

        toolbar = NavigationToolbar2Tk(canvas, parent)
        toolbar.update()
        toolbar.pack(side=tk.TOP, fill=tk.X)
        canvas_widget.pack(fill=tk.BOTH, expand=True)

        cursor_vline = ax1.axvline(
            self.times[0], visible=False,
            color="black", linestyle="--",
            linewidth=CURSOR['CURSOR_LINEWIDTH']
        )

        cursor_hline_R = ax1.axhline(
            self.Reactivity[0], visible=False,
            color="black", linestyle="--",
            linewidth=CURSOR['CURSOR_LINEWIDTH']
        )

        cursor_hlines_groups = []
        for group in self.Groups:
            line = ax2.axhline(
                group[0],
                visible=False,
                color="black", linestyle="--",
                linewidth=CURSOR['CURSOR_LINEWIDTH']
            )
            cursor_hlines_groups.append(line)

        plot_obj = {
            "fig": fig,
            "ax1": ax1,
            "ax2": ax2,
            "canvas": canvas,
            "toolbar": toolbar,
            "vline_left": None,
            "vline_right": None,

            # Extended cursor elements
            "cursor_vline": cursor_vline,
            "cursor_hline_R": cursor_hline_R,
            "cursor_hlines_groups": cursor_hlines_groups,
            "cursor_text": ax1.text(
                0, 0, "",
                visible=False,
                fontsize=CURSOR['CURSOR_TEXT_SIZE'],
                bbox=dict(boxstyle="round", facecolor="white", alpha=0.8)
            ),
            "interval_artists": {
                "interval1": {"left": None, "right": None, "line": None},
                "interval2": {"left": None, "right": None, "line": None},
            },
            "finished_lines": [],
            "green_points": [],
            "move_line": None,
            "cursor_cid": None
        }

        canvas.mpl_connect(
            "button_press_event",
            lambda event, p=plot_obj: self.on_plot_click(event, p)
        )
        canvas.mpl_connect(
            "scroll_event",
            lambda event, p=plot_obj: self.on_plot_scroll(event, p)
        )
        canvas.get_tk_widget().bind("<Left>", self.move_line_left)
        canvas.get_tk_widget().bind("<Right>", self.move_line_right)
        canvas.get_tk_widget().focus_set()

        self.plot_windows.append(plot_obj)

        # A newly opened window must repeat everything the first one shows
        self.redraw_plot_from_state(plot_obj)

        canvas.draw_idle()

        if self.extended_cursor_enabled:
            cid = canvas.mpl_connect(
                "motion_notify_event",
                lambda event, p=plot_obj: self.on_mouse_move(event, p)
            )
            plot_obj["cursor_cid"] = cid

        return plot_obj

    def redraw_plot_from_state(self, plot):
        """
        Restore the whole drawing state in a freshly created plot window:
        measured (black) lines, the active (yellow) lines and their points,
        the red vertical line and the green intersection dots.
        """
        # Measured lines (black)
        for entry in self.finished_lines:
            plot["finished_lines"].append(
                self.draw_interval_line(plot, entry, finished=True)
            )

        # Active intervals: points and lines (yellow)
        for key in ("interval1", "interval2"):
            state = self.selection_state[key]
            art = plot["interval_artists"][key]

            if state["dots"]:
                if state["left"]:
                    art["left"] = self.draw_selection_point(
                        plot, state["left"]
                    )
                if state["right"]:
                    art["right"] = self.draw_selection_point(
                        plot, state["right"]
                    )

            if state["left"] and state["right"]:
                art["line"] = self.draw_interval_line(plot, state)

        # Red vertical line of the group movement
        if self.show_move_line and hasattr(self, "t"):
            plot["move_line"] = plot["ax1"].axvline(
                self.times[self.t],
                color=PLOT_STYLE['MOVE_LINE_COLOR'],
                linewidth=PLOT_STYLE['MOVE_LINE_WIDTH'],
                alpha=PLOT_STYLE['MOVE_LINE_ALPHA'],
                zorder=PLOT_STYLE['MOVE_LINE_ZORDER']
            )

        # Green intersection dots
        if self.show_intersections and hasattr(self, "t"):
            x_time = self.times[self.t]
            plot["green_points"] = [
                self.draw_intersection_point(plot, x_time, self.p1_R),
                self.draw_intersection_point(plot, x_time, self.p2_R)
            ]

        plot["canvas"].draw_idle()

    def close_large_plot_window(self):
        """
        Drop every reference to the large plot window when the user
        closes it, otherwise stale Tk widgets raise TclError later.
        """
        plot_obj = getattr(self, "large_plot_obj", None)

        if plot_obj in self.plot_windows:
            self.plot_windows.remove(plot_obj)

        for attr in ("large_plot_obj", "large_status_label",
                     "Proceed_button_large", "fix1_large", "fix2_large", "delete_last_step_button",
                     "complete_large"):
            if hasattr(self, attr):
                delattr(self, attr)

        if hasattr(self, "large_plot_window"):
            win = self.large_plot_window
            del self.large_plot_window
            win.destroy()

    def open_plot_in_new_window(self):
        """Create large plot in the window."""
        # Only one large window at a time
        if (
            hasattr(self, "large_plot_window")
            and self.widget_alive(self.large_plot_window)
        ):
            self.large_plot_window.lift()
            self.large_plot_window.focus_force()
            return

        win = tk.Toplevel(self.root)
        win.title("DRDH Plot – Extended view")
        win.geometry("1200x800")
        # To move large plon to the front position
        self.large_plot_window = win
        win.protocol("WM_DELETE_WINDOW", self.close_large_plot_window)

        frame = tk.Frame(win, bg="white")
        frame.pack(fill=tk.BOTH, expand=True)

        self.large_plot_obj = self.create_plot(frame, large=True)

        self.Proceed_button_large = TestButtons(
            frame,
            text='Proceed',
            command=self.proceed
        )
        self.Proceed_button_large.pack(side=tk.LEFT, padx=10, pady=10)

        self.fix1_large = TestButtons(
            frame,
            text="Fix 1",
            command=self.fix_first
        )
        self.fix1_large.pack(side=tk.LEFT, padx=10, pady=10)

        self.fix2_large = TestButtons(
            frame,
            text="Fix 2",
            command=self.fix_second
        )
        self.fix2_large.pack(side=tk.LEFT, padx=10, pady=10)

        self.delete_last_step_button = TestButtons(
            frame,
            text="Remove previous step",
            command=self.delete_last_step,
        )
        self.delete_last_step_button.pack(side=tk.LEFT, padx=10, pady=10)

        self.complete_large = TestButtons(
            frame,
            text="Complete",
            command=self.complete
        )
        self.complete_large.pack(side=tk.LEFT, padx=10, pady=10)

        self.large_status_label = tk.Label(
            frame,
            text="",
            font=FONTS['TEXT_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
        )
        self.large_status_label.pack(
            side=tk.RIGHT, padx=20, pady=10, anchor="se"
        )
        self.large_status_label.config(justify="right")

        # The window may be opened in the middle of a cycle
        self.update_hint()

    def current_stage(self) -> str:
        """
        Current stage of the measurement cycle. Derived from the state,
        so the hint can never get out of sync with the actual progress.

            LEFT_1 -> RIGHT_1 -> FIX_1 -> LEFT_2 -> RIGHT_2 -> FIX_2
                   -> PROCEED -> (next cycle starts at FIX_1)
        """
        state1 = self.selection_state["interval1"]
        state2 = self.selection_state["interval2"]

        if state2["fixed"]:
            return "PROCEED"

        if not self.fix1_done:
            if not state1["left"]:
                return "LEFT_1"
            if not state1["right"]:
                return "RIGHT_1"
            return "FIX_1"

        if not state2["left"]:
            return "LEFT_2"
        if not state2["right"]:
            return "RIGHT_2"
        return "FIX_2"

    def update_hint(self) -> None:
        """Show what is expected from the user right now."""
        stage = self.current_stage()

        # Line 1 of the 2nd (and every next) cycle is inherited,
        # so the wording differs.
        if stage == "FIX_1" and self.line1_locked:
            stage = "FIX_1_INHERITED"

        self.set_status_text(DRDH_HINTS[stage])

    def set_status_text(self, text):
        """
        Write the hint into the status label of the main window and,
        if it is open, of the large plot window.
        """
        for attr in ("status_label", "large_status_label"):
            label = getattr(self, attr, None)

            if label is not None and self.widget_alive(label):
                label.config(text=text)

    def create_plot_frame(self):
        """
        Create the field for the initial plot.
        """
        self.left_frame = tk.Frame(
            self.splitter_window,
            bg=COLORS['PARAMETERS_BACKGROUND_COLOR'],
            highlightthickness=0,
        )
        self.splitter_window.add(
            self.left_frame,
            minsize=SPLITTER_MINSIZES['LEFT'],
            stretch="always"
        )
        self.create_plot(self.left_frame, large=False)

    def get_click_data(self, event, plot):
        if event.xdata is None:
            return None

        clicked_time = mdates.num2date(event.xdata).replace(tzinfo=None)

        nearest_index = min(
            range(len(self.times)),
            key=lambda i: abs(self.times[i] - clicked_time)
        )

        time_val = self.times[nearest_index]
        R = float(self.Reactivity[nearest_index])

        group_values = []
        for group in self.Groups:
            group_values.append(float(group[nearest_index]))

        return {
            "index": nearest_index,
            "time": time_val,
            "R": R,
            "groups": group_values
        }

    def on_plot_scroll(self, event, plot):
        """
        Zoom the plot horizontally with the mouse wheel.

        Zoom is performed around the mouse cursor position.
        The X axis is shared by ax1 and ax2.
        The Y axes remain unchanged.
        """

        if event.inaxes not in (plot["ax1"], plot["ax2"]):
            return

        # Do not interfere with an explicitly selected toolbar mode.
        if plot["toolbar"].mode != '':
            return

        if event.xdata is None:
            return

        # Scroll up -> zoom in.
        # Scroll down -> zoom out.
        if event.button == "up":
            scale = 0.8
        elif event.button == "down":
            scale = 1.25
        else:
            return

        ax1 = plot["ax1"]
        ax2 = plot["ax2"]

        # ---------------------------------------------------------
        # X axis
        # ---------------------------------------------------------
        # Zoom around the mouse cursor position.
        x_min, x_max = ax1.get_xlim()
        x_center = event.xdata

        new_x_min = x_center + (x_min - x_center) * scale
        new_x_max = x_center + (x_max - x_center) * scale

        ax1.set_xlim(new_x_min, new_x_max)
        ax2.set_xlim(new_x_min, new_x_max)

        # Redraw all active/finished lines using the new limits.
        self.make_interval_lines_infinite()

        plot["canvas"].draw_idle()

    def on_plot_click(self, event, plot):
        # print("CLICK:", event.button, event.inaxes) <- debug

        # Moving the vertical line insread of creating points
        if self.selection_state["interval2"]["fixed"]:
            if event.button == 1:
                click_data = self.get_click_data(event, plot)
                if click_data:
                    idx = click_data["index"]

                    state1 = self.selection_state["interval1"]
                    state2 = self.selection_state["interval2"]

                    if state1["right"]["index"] <= idx <= state2["right"]["index"]:
                        self.t = idx
                        self.draw_vertical_line(self.times[self.t])
                return

        if plot["toolbar"].mode != '':
            return

        if event.inaxes not in (plot["ax1"], plot["ax2"]):
            return

        # Line 1 is inherited from the previous cycle: the user has to
        # confirm it with "Fix 1" before selecting the points of line 2.
        if self.line1_locked and not self.fix1_done:
            self.update_hint()
            return

        interval_key = "interval2" if self.fix1_done else "interval1"
        state = self.selection_state[interval_key]

        if state["fixed"]:
            return

        click_data = self.get_click_data(event, plot)
        if click_data is None:
            return

        # Needed by the "C from file" method of the DRDC
        if self.first_click_index is None:
            self.first_click_index = click_data["index"]

        if event.button == 3:
            self.last_right_click_index = click_data["index"]

        if event.button == 1:
            state["left"] = click_data

        elif event.button == 3:
            if state["left"] is None:
                return

            if click_data["index"] <= state["left"]["index"]:
                Messages.show(
                    "error",
                    "RIGHT_CLICK_BEFORE_LEFT"
                )
                return

            moved_groups = self.get_moved_groups(
                state["left"]["groups"],
                click_data["groups"]
            )
            if moved_groups:
                movement_lines = []

                for name, start, end in moved_groups:
                    movement_lines.append(
                        f"{name}: {start:.2f} → {end:.2f}"
                    )

                movement_text = "\n".join(movement_lines)

                Messages.show(
                    "error",
                    "GROUPS_MOVED",
                    movements=movement_text
                )
                return

            state["right"] = click_data

        self.refresh_line_tables()
        self.update_hint()

        state["dots"] = True

        # The dot is drawn in EVERY window (p), not only in the clicked one
        for p in self.plot_windows:
            art = p["interval_artists"][interval_key]

            if event.button == 1:
                if art["left"]:
                    art["left"].remove()
                art["left"] = self.draw_selection_point(p, click_data)

            elif event.button == 3:
                if art["right"]:
                    art["right"].remove()
                art["right"] = self.draw_selection_point(p, click_data)

        # Both points are set -> (re)draw the line in EVERY window
        if state["left"] and state["right"]:
            for p in self.plot_windows:
                art = p["interval_artists"][interval_key]

                if art["line"]:
                    art["line"].remove()

                art["line"] = self.draw_interval_line(p, state)

        for p in self.plot_windows:
            p["canvas"].draw_idle()

    def make_interval_lines_infinite(self):
        for plot in self.plot_windows:
            for key in ("interval1", "interval2"):
                state = self.selection_state[key]
                art = plot["interval_artists"][key]

                if state["left"] and state["right"]:
                    if art["line"]:
                        art["line"].remove()

                    art["line"] = self.draw_interval_line(plot, state)

            plot["canvas"].draw_idle()

    def draw_selection_point(self, plot, click_data):
        """Draw a single clicked point (left or right) in the given window."""
        return plot["ax1"].scatter(
            click_data["time"], click_data["R"],
            s=PLOT_STYLE['POINT_SIZE'],
            facecolor=PLOT_STYLE['POINT_COLOR'],
            edgecolor=PLOT_STYLE['POINT_EDGE'],
            linewidth=PLOT_STYLE['POINT_EDGE_WIDTH'],
            zorder=10
        )

    def draw_interval_line(self, plot, state, finished=False):
        """
        Draw the straight line through the two clicked points,
        extended over the whole time axis.

        Args:
            plot: target plot window (the line is drawn in THIS window).
            state: dict with "left" and "right" click data.
            finished (bool): True -> already measured line (black style).
        """
        ax = plot["ax1"]

        x1 = mdates.date2num(state["left"]["time"])
        x2 = mdates.date2num(state["right"]["time"])
        y1 = state["left"]["R"]
        y2 = state["right"]["R"]

        slope = (y2 - y1) / (x2 - x1)
        intercept = y1 - slope * x1

        x_vals = np.array(ax.get_xlim())
        y_vals = slope * x_vals + intercept

        if finished:
            color = PLOT_STYLE['FINISHED_LINE_COLOR']
            width = PLOT_STYLE['FINISHED_LINE_WIDTH']
            alpha = PLOT_STYLE['FINISHED_LINE_ALPHA']
            zorder = PLOT_STYLE['FINISHED_LINE_ZORDER']
        else:
            color = PLOT_STYLE['ACTIVE_LINE_COLOR']
            width = PLOT_STYLE['ACTIVE_LINE_WIDTH']
            alpha = PLOT_STYLE['ACTIVE_LINE_ALPHA']
            zorder = PLOT_STYLE['ACTIVE_LINE_ZORDER']

        return ax.plot(
            mdates.num2date(x_vals),
            y_vals,
            color=color,
            linewidth=width,
            alpha=alpha,
            solid_capstyle="round",
            zorder=zorder
        )[0]

    def apply_finished_style(self, line):
        """Recolor an active (yellow) line into a measured (black) one."""
        line.set_color(PLOT_STYLE['FINISHED_LINE_COLOR'])
        line.set_linewidth(PLOT_STYLE['FINISHED_LINE_WIDTH'])
        line.set_alpha(PLOT_STYLE['FINISHED_LINE_ALPHA'])
        line.set_zorder(PLOT_STYLE['FINISHED_LINE_ZORDER'])

    def fix_first(self):
        state1 = self.selection_state["interval1"]

        if not (state1["left"] and state1["right"]):
            Messages.show(
                "error",
                "LINE_NOT_DEFINED"
            )
            return

        state1["fixed"] = True
        self.fix1_done = True
        self.active_interval = 2

        self.update_hint()

    def fix_second(self):

        state1 = self.selection_state["interval1"]
        state2 = self.selection_state["interval2"]

        if not (state1["left"] and state1["right"]):
            Messages.show(
                "error",
                "LINE_NOT_DEFINED"
            )
            return

        if not (state2["left"] and state2["right"]):
            Messages.show(
                "error",
                "LINE_NOT_DEFINED"
            )
            return

        moved_between_lines = self.get_moved_groups(
            state1["right"]["groups"],   # first line
            state2["right"]["groups"]    # second line
        )

        if not moved_between_lines:
            Messages.show(
                "error",
                "NO_GROUP_MOVEMENT"
            )
            return

        self.selection_state["interval2"]["fixed"] = True

        # Create the vertical line
        idx_start = state1["right"]["index"]
        idx_end = state2["right"]["index"]

        self.t_move = self.get_move_start_index(idx_start, idx_end)

        if self.t_move is None:
            Messages.show(
                "error",
                "NO_GROUP_MOVEMENT"
            )
            self.selection_state["interval2"]["fixed"] = False
            self.update_hint()
            return

        # The red line must stay inside [idx_start, idx_end]
        self.t = min(self.t_move + TIME_SHIFT, idx_end)
        self.draw_vertical_line(self.times[self.t])

        if self.values_window_alive():
            self.update_drdh_table()

        self.update_hint()

    def get_moved_groups(self, groups_start, groups_end):
        """
        Returns list of moved groups with positions.

        Args:
            groups_start (list[float])
            groups_end (list[float])

        Returns:
            list[tuple[str, float, float]]
            -> (group_name, start_position, end_position)
        """
        moved = []

        for i, (g1, g2) in enumerate(zip(groups_start, groups_end)):
            if not np.isclose(g1, g2):
                moved.append((
                    self.Group_names[i],
                    g1,
                    g2
                ))

        return moved

    def get_move_start_index(self, idx_start, idx_end):
        """
        Returns first index where any group position changed.
        """
        for i in range(idx_start, idx_end + 1):
            for group in self.Groups:
                if not np.isclose(group[i], group[idx_start]):
                    return i

    def draw_vertical_line(self, time):
        self.show_move_line = True

        for plot in self.plot_windows:

            if "move_line" in plot and plot["move_line"]:
                plot["move_line"].remove()

            plot["move_line"] = plot["ax1"].axvline(
                time,
                color=PLOT_STYLE['MOVE_LINE_COLOR'],
                linewidth=PLOT_STYLE['MOVE_LINE_WIDTH'],
                alpha=PLOT_STYLE['MOVE_LINE_ALPHA'],
                zorder=PLOT_STYLE['MOVE_LINE_ZORDER']
            )
            plot["canvas"].draw_idle()

    def move_line_left(self, event=None):
        self.shift_vertical_line(-1)

    def move_line_right(self, event=None):
        self.shift_vertical_line(1)

    def shift_vertical_line(self, step):
        state1 = self.selection_state["interval1"]
        state2 = self.selection_state["interval2"]

        min_idx = state1["right"]["index"]
        max_idx = state2["right"]["index"]

        new_index = self.t + step

        if new_index < min_idx or new_index > max_idx:
            return

        self.t = new_index
        self.draw_vertical_line(self.times[self.t])
        if self.values_window_alive():
            self.update_drdh_table()

    def get_line_intersection(self, state):
        """
        Возвращает R в точке пересечения жёлтой линии
        с текущей красной вертикалью (координату У)
        """
        x = mdates.date2num(self.times[self.t])

        x1 = mdates.date2num(state["left"]["time"])
        x2 = mdates.date2num(state["right"]["time"])
        y1 = state["left"]["R"]
        y2 = state["right"]["R"]

        slope = (y2 - y1) / (x2 - x1)
        intercept = y1 - slope * x1

        return slope * x + intercept

    def draw_intersection_points(self):
        x_time = self.times[self.t]

        # remove previous green dots
        for plot in self.plot_windows:
            if "green_points" in plot:
                for p in plot["green_points"]:
                    p.remove()

            plot["green_points"] = []

        y1 = self.get_line_intersection(self.selection_state["interval1"])
        y2 = self.get_line_intersection(self.selection_state["interval2"])

        for plot in self.plot_windows:
            plot["green_points"] = [
                self.draw_intersection_point(plot, x_time, y1),
                self.draw_intersection_point(plot, x_time, y2)
            ]
            plot["canvas"].draw_idle()

        self.p1_R = y1
        self.p2_R = y2
        self.show_intersections = True

    def draw_intersection_point(self, plot, x_time, y):
        """Draw one green intersection dot in the given window."""
        return plot["ax1"].scatter(
            x_time, y,
            s=PLOT_STYLE['INTERSECTION_SIZE'],
            facecolor=PLOT_STYLE['INTERSECTION_COLOR'],
            edgecolor=PLOT_STYLE['INTERSECTION_EDGE'],
            linewidth=PLOT_STYLE['INTERSECTION_EDGE_WIDTH'],
            zorder=PLOT_STYLE['INTERSECTION_ZORDER']
        )

    def get_values_at_index(self, idx):
        result = {
            "time": self.times[idx],
            "reactivity": float(self.Reactivity[idx])
        }

        for i, name in enumerate(self.Group_names):
            result[name] = float(self.Groups[i][idx])

        return result

    def create_first_line_table(self):
        """Create small window with a current parameters, left table"""
        tk.Label(
            self.first_line_frame,
            text="First line parameters:",
            font=FONTS['HEADING_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
        ).pack(anchor="w")

        unit = self.reactivity_unit()
        rows = [f"R1_1, {unit}", f"R1_2, {unit}"]

        for name in self.Group_names:
            rows.append(f"{name}_1, cm")

        self.first_line_table = ttk.Treeview(
            self.first_line_frame,
            columns=("param", "value"),
            show="headings",
            height=len(rows)
        )

        self.first_line_table.heading("param", text="Parameter")
        self.first_line_table.heading("value", text="Value")

        self.first_line_table.column("param", width=150, anchor="center")
        self.first_line_table.column("value", width=120, anchor="center")

        for r in rows:
            self.first_line_table.insert("", "end", values=(r, ""))

        self.first_line_table.pack(fill="both", expand=True)

    def create_second_line_table(self):
        """Small window with a current parameters, right table"""
        tk.Label(
            self.second_line_frame,
            text="Second line parameters:",
            font=FONTS['HEADING_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
        ).pack(anchor="w")

        unit = self.reactivity_unit()
        rows = [f"R2_1, {unit}", f"R2_2, {unit}"]

        for name in self.Group_names:
            rows.append(f"{name}_2, cm")

        self.second_line_table = ttk.Treeview(
            self.second_line_frame,
            columns=("param", "value"),
            show="headings",
            height=len(rows)
        )

        self.second_line_table.heading("param", text="Parameter")
        self.second_line_table.heading("value", text="Value")

        self.second_line_table.column("param", width=150, anchor="center")
        self.second_line_table.column("value", width=120, anchor="center")

        for r in rows:
            self.second_line_table.insert("", "end", values=(r, ""))

        self.second_line_table.pack(fill="both", expand=True)

    def create_drdh_table(self):
        """Small window with a current parameters, footer table"""
        columns = [
            "", "", "", "", "", "", "", ""
        ]

        self.drdh_table = ttk.Treeview(
            self.bottom_frame,
            columns=columns,
            show="headings",
            height=4
        )

        for c in columns:
            self.drdh_table.heading(c, text=c)
            self.drdh_table.column(c, width=90, anchor="center")

        unit = self.reactivity_unit()

        self.drdh_table.insert("", "end",
                               values=(
                                   f"R1, {unit}", "", "",
                                   f"R2, {unit}", "", "",
                                   f"ΔR, {unit}", ""
                                )
                               )

        self.drdh_table.insert("", "end",
                               values=(
                                   "H1, %", "", "",
                                   "H2, %", "", "",
                                   "ΔH, %", ""
                                )
                               )

        self.drdh_table.insert("", "end",
                               values=("DRDH =", "", "", "", "", "", "", "")
                               )

        self.drdh_table.pack(fill="both", expand=True)

    def update_drdh_table(self):
        """
        Renew footer table according to the red time line movements
        """
        if not self.values_window_alive():
            return

        state1 = self.selection_state["interval1"]
        state2 = self.selection_state["interval2"]

        # значения R на пересечении желтых линий с красной
        R1 = self.get_line_intersection(state1) if state1["left"] and state1["right"] else 0
        R2 = self.get_line_intersection(state2) if state2["left"] and state2["right"] else 0
        delta_R = R2 - R1

        # значения групп для ΔH
        H1_vals = [g[state1["right"]["index"]] if state1["right"] else 0 for g in self.Groups]
        H2_vals = [g[state2["right"]["index"]] if state2["right"] else 0 for g in self.Groups]
        delta_H_vals = [h2 - h1 for h1, h2 in zip(H1_vals, H2_vals)]

        # Обновление первой строки (R1, R2, ΔR)
        unit = self.reactivity_unit()
        R1_disp = self.to_display_reactivity(R1)
        R2_disp = self.to_display_reactivity(R2)
        delta_R_disp = self.to_display_reactivity(delta_R)

        values = [f"R1, {unit}", f"{R1_disp:.{self.DECIMAL_REACT}f}", "",
                  f"R2, {unit}", f"{R2_disp:.{self.DECIMAL_REACT}f}", "",
                  f"ΔR, {unit}", f"{delta_R_disp:.{self.DECIMAL_REACT}f}"]
        self.drdh_table.item(self.drdh_table.get_children()[0], values=values)

        # Обновление второй строки (H1, H2, ΔH)
        values = ["H1, %"] + [f"{v:.{self.DECIMAL_GROUP}f}" for v in H1_vals[:3]] + \
                ["H2, %"] + [f"{v:.{self.DECIMAL_GROUP}f}" for v in H2_vals[:3]] + \
                ["ΔH, %"] + [f"{v:.{self.DECIMAL_GROUP}f}" for v in delta_H_vals[:3]]
        self.drdh_table.item(self.drdh_table.get_children()[1], values=values)

        # DRDH вычисляется при наличии ΔH.
        # Знаменатель - перемещение ведущей группы, как и в proceed().
        DRDH = 0

        if delta_H_vals and state1["right"] and state2["right"]:
            lead = self.get_leading_group(
                state1["right"]["index"], state2["right"]["index"]
            )

            if lead is not None:
                delta_H = (
                    self.Groups[lead][state2["right"]["index"]]
                    - self.Groups[lead][state1["right"]["index"]]
                )
                DRDH = delta_R / (delta_H * self.Group_length / 100)

        DRDH = self.to_display_reactivity(DRDH)
        values = [
            f"DRDH, {unit}/cm =", f"{DRDH:.{self.DECIMAL_DRDH}f}"
        ] + [""] * 6
        self.drdh_table.item(self.drdh_table.get_children()[2], values=values)
