import numpy as np
import pandas as pd
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
    DECIMAL, show_info, FONTS, COLORS, GAPS,
    SPLITTER_MINSIZES, PLOT, TABLE, PCR_SIGMA, CURSOR, ENCODINGS
)

mpl.rcParams['font.family'] = 'Times New Roman'


class PCR_processing:
    """
    Determination of the power reactivity coefficient (PCR).

    The coefficient is measured in two procedures - with and without steam
    extraction. For every procedure the user picks points on the plot:

      * without steam extraction: one click before the reactivity is added
        (its heating rate, averaged over the `base` window, gives v_RCPS),
        then "Get DTDt RCPS", then two clicks after the reactivity is added (tau0
        and tau1 - the bounds of the power rise);
      * with steam extraction: v_RCPS = 0, "Get DTDt RCPS" is disabled, only the two
        clicks tau0 and tau1 are made.

    For each procedure:

        N(t1) = MC * (v_T(t1) - v_RCPS)          , N(t0) = 0
        dR_N  = -[ R(t0) - R(t1)
                   + ITC*(T(t1) - T(t0))
                   + PrCR*(P(t1) - P(t0)) ]
        PCR_exp = dR_N / N(t1)

    with alpha_T = ITC and alpha_P = PrCR entered in PCR_module. The final
    PCR is the inverse-variance weighted mean of the two procedures.
    """

    def __init__(self, root: tk.Widget, main_app: Any):
        self.root: tk.Widget = root
        self.main_app: Any = main_app
        try:
            self.root.winfo_toplevel().iconbitmap("Icons/PCR_icon.ico")
        except Exception:
            pass

        self.PCR_frame: Optional[tk.Frame] = None
        self.plot_windows: List[Dict[str, Any]] = []
        self.active_entry: Optional[ttk.Entry] = None
        self.extended_cursor_enabled: bool = False

        # beta_eff, entered in the main window in percent
        self.beta: float = self.main_app.main_app.beta

        # Entered values from PCR_module
        self.alpha_T: float = self.main_app.ITC          # ITC, pcm/degC
        self.alpha_P: float = self.main_app.PrCR         # PrCR
        self.MC: float = self.main_app.MC                # heat capacity
        self.sigma_DRDY = getattr(self.main_app, "sigma_DRDY", None)
        self.PCR_reference: Optional[float] = getattr(
            self.main_app, "PCR_reference", None
        )
        self.base: int = int(getattr(self.main_app, "base", 60))

        # Steam mode chosen in PCR_module: mandatory, so it is set
        self.steam_mode: str = self.main_app.steam_mode

        # NFME columns
        self.Reactivity = getattr(self.main_app, "Reactivity", None)
        self.Temperature = getattr(self.main_app, "Temperature", None)
        self.Pressure = getattr(self.main_app, "Pressure", None)
        self.Time = getattr(self.main_app, "Time", None)
        self.Group_position = getattr(self.main_app, "Group_position", None)

        # File headers used for every NFME parameter, so a new file can be
        # re-resolved by column name rather than by position.
        self.column_headers: Dict[str, List[str]] = dict(
            getattr(self.main_app, "column_headers", {})
        )

        self.DECIMAL_REACT: int = DECIMAL['DECIMAL_REACT']
        self.DECIMAL_TEMP: int = DECIMAL['DECIMAL_TEMP']
        self.DECIMAL_GROUP: int = DECIMAL['DECIMAL_GROUP']
        self.DECIMAL_PRESSURE: int = 3
        self.DECIMAL_GENERAL: int = 2

        # Reactivity display unit: "%" (default) or "Beff"
        self.react_unit: str = "%"
        # Plot legend visibility
        self.legend_visible: bool = True

        # Uncertainty constants (methodology)
        self.sigma_alpha_T: float = PCR_SIGMA['SIGMA_ALPHA_T']
        self.sigma_dT: float = PCR_SIGMA['SIGMA_DT']
        self.sigma_dP: float = PCR_SIGMA['SIGMA_DP']
        self.sigma_MC_rel: float = PCR_SIGMA['SIGMA_MC_REL']
        self.sigma_v_rel: float = PCR_SIGMA['SIGMA_V_REL']
        self.sigma_rho_rel: float = PCR_SIGMA['SIGMA_RHO_REL']

        # Per-procedure results, keyed by the steam mode
        self.results: Dict[str, Dict[str, Any]] = {}

        # Selection state of the current procedure
        self.reset_selection()

    # ------------------------------------------------------------------ #
    #  Selection state                                                   #
    # ------------------------------------------------------------------ #
    def reset_selection(self) -> None:
        """Drop the clicks of the procedure currently being measured."""
        self.base_index: Optional[int] = None     # click before reactivity
        self.v_RCPS: Optional[float] = None        # base heating rate
        self.base_fixed: bool = False              # "Get DTDt_RCPS" pressed
        self.tau0_index: Optional[int] = None      # start of the rise
        self.tau1_index: Optional[int] = None      # end of the rise

    def with_steam(self) -> bool:
        """True while the current mode is 'with steam extraction'."""
        return self.steam_mode == "With steam extraction"

    @staticmethod
    def widget_alive(widget) -> bool:
        """True if the widget still exists (was not destroyed by the user)."""
        try:
            return bool(widget.winfo_exists())
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    #  Window                                                            #
    # ------------------------------------------------------------------ #
    def create_PCR_processing_window(self) -> None:
        """Create the main PCR processing window layout."""
        self.PCR_processing_frame = tk.Frame(
            self.root, bg=COLORS['BACKGROUND_COLOR']
        )
        self.PCR_processing_frame.place(x=0, y=0, relwidth=1, relheight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        for r, w in ((0, 0), (1, 1), (2, 0), (3, 0), (4, 0)):
            self.PCR_processing_frame.grid_rowconfigure(r, weight=w)
        for c, w in ((0, 4), (1, 4), (2, 2), (3, 2)):
            self.PCR_processing_frame.grid_columnconfigure(c, weight=w)

        self.create_menu()
        self.create_splitter_window()
        self.create_plot_frame()
        self.labels()
        self.buttons()
        self.create_table()
        self.update_mode_label()
        self.update_status_labels()

    def create_splitter_window(self) -> None:
        """Horizontal splitter separating plot and results table."""
        self.splitter_window = tk.PanedWindow(
            self.PCR_processing_frame,
            orient=tk.HORIZONTAL,
            sashrelief=tk.RAISED, sashwidth=5,
            bg=COLORS['BACKGROUND_COLOR']
        )
        self.splitter_window.grid(
            row=1, column=0, columnspan=4,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_10_5'],
            sticky="nsew"
        )

    def create_plot_frame(self) -> None:
        """Left pane with the plot."""
        self.plot_frame = tk.Frame(
            self.splitter_window, bg=COLORS['BACKGROUND_COLOR']
        )
        self.splitter_window.add(
            self.plot_frame, minsize=SPLITTER_MINSIZES['LEFT']
        )
        self.create_plot(self.plot_frame, is_main=True)

    # ------------------------------------------------------------------ #
    #  Menu                                                              #
    # ------------------------------------------------------------------ #
    def create_menu(self) -> None:
        """Menu bar: Options (switch mode, load file), Plot, Save, INFO."""
        self.menu_bar = tk.Menu(self.root.winfo_toplevel())
        self.root.winfo_toplevel().config(menu=self.menu_bar)

        options = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Options", menu=options)
        options.add_command(
            label="Switch mode",
            font=FONTS['DATA_FONT'],
            command=self.switch_mode
        )
        options.add_command(
            label="Load a new file",
            font=FONTS['DATA_FONT'],
            command=self.load_new_file
        )

        plot_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Plot", menu=plot_menu)
        plot_menu.add_command(
            label="Plot in new window",
            font=FONTS['DATA_FONT'],
            command=self.open_plot_in_new_window
        )
        plot_menu.add_command(
            label="Extended cursor",
            font=FONTS['DATA_FONT'],
            command=self.extended_cursor
        )
        plot_menu.add_command(
            label="Show / hide legend",
            font=FONTS['DATA_FONT'],
            command=self.toggle_legend
        )

        parameters_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(
            label="Computed parameters", menu=parameters_menu
        )
        parameters_menu.add_command(
            label="Edit parameters",
            font=FONTS['DATA_FONT'],
            command=self.open_experiment_parameters
        )

        units = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Units", menu=units)
        units.add_command(
            label="Reactivity in %", font=FONTS['DATA_FONT'],
            command=lambda: self.set_reactivity_unit("%")
        )
        units.add_command(
            label="Reactivity in Beff", font=FONTS['DATA_FONT'],
            command=lambda: self.set_reactivity_unit("Beff")
        )

        decimal = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Decimal", menu=decimal)
        decimal.add_command(
            label="Reactivity decimal", font=FONTS['DATA_FONT'],
            command=lambda: self.set_decimal("Reactivity")
        )
        decimal.add_command(
            label="Temperature decimal", font=FONTS['DATA_FONT'],
            command=lambda: self.set_decimal("Temperature")
        )
        decimal.add_command(
            label="Pressure decimal", font=FONTS['DATA_FONT'],
            command=lambda: self.set_decimal("Pressure")
        )
        decimal.add_command(
            label="General decimal", font=FONTS['DATA_FONT'],
            command=lambda: self.set_decimal("General")
        )

        save_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Save", menu=save_menu)
        save_menu.add_command(
            label="Save to Excel", font=FONTS['DATA_FONT'],
            command=self.save_to_Excel
        )
        save_menu.add_command(
            label="Save to txt", font=FONTS['DATA_FONT'],
            command=self.save_to_txt
        )

        info = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="INFO", menu=info)
        info.add_command(
            label="INFO", font=FONTS['DATA_FONT'],
            command=lambda: show_info(self.root, "PCR/info_processing.txt")
        )

    # ------------------------------------------------------------------ #
    #  Labels: mode indicator and per-procedure status                   #
    # ------------------------------------------------------------------ #
    def labels(self) -> None:
        """On-screen mode indicator and the two status lines."""
        self.mode_label = tk.Label(
            self.PCR_processing_frame,
            text="Mode: -",
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.mode_label.grid(
            row=2, column=0, columnspan=2,
            padx=GAPS['GAPS_X']['PAD_X_10'], sticky="w"
        )

        # Two clock/tick lines: PCR with and without steam extraction
        self.status_with = tk.Label(
            self.PCR_processing_frame,
            text="⏱ PCR with steam extraction",
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.status_with.grid(
            row=3, column=0, columnspan=2,
            padx=GAPS['GAPS_X']['PAD_X_10'], sticky="w"
        )
        self.status_without = tk.Label(
            self.PCR_processing_frame,
            text="⏱ PCR without steam extraction",
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.status_without.grid(
            row=4, column=0, columnspan=2,
            padx=GAPS['GAPS_X']['PAD_X_10'], sticky="w"
        )

        # Hint in the lower right corner
        self.hint_label = tk.Label(
            self.PCR_processing_frame, text="",
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR'],
            fg="#555555"
        )
        self.hint_label.grid(
            row=4, column=2, columnspan=2,
            padx=GAPS['GAPS_X']['PAD_X_10'], sticky="e"
        )

    def update_mode_label(self) -> None:
        """Reflect the current steam mode on screen."""
        self.mode_label.config(text=f"Mode: {self.steam_mode}")

    def update_status_labels(self) -> None:
        """Turn a clock into a tick once the matching procedure is done."""
        done_with = "With steam extraction" in self.results
        done_without = "Without steam extraction" in self.results

        self.status_with.config(
            text=("✓" if done_with else "⏱") + " PCR with steam extraction"
        )
        self.status_without.config(
            text=("✓" if done_without else "⏱")
            + " PCR without steam extraction"
        )

    def update_hint(self) -> None:
        """Show what click is expected next for the current procedure."""
        if not self.with_steam() and self.base_index is None:
            msg = "Click on the steady section before the reactivity is added"
        elif not self.with_steam() and not self.base_fixed:
            msg = "Press 'Get DTDt RCPS' to confirm the base"
        elif self.tau0_index is None:
            msg = "Click the start of the power rise (t₀)"
        elif self.tau1_index is None:
            msg = "Click the end of the power rise (t₁)"
        else:
            msg = "Press 'Proceed' to compute"
        self.hint_label.config(text=msg)

    # ------------------------------------------------------------------ #
    #  Buttons section                                                   #
    # ------------------------------------------------------------------ #
    def buttons(self) -> None:
        """Get DTDt RCPS, Proceed, BACK, INFO."""
        self.fix1_button = TestButtons(
            self.PCR_processing_frame, text="Get DTDt RCPS",
            command=self.fix_base
        )
        self.fix1_button.grid(
            row=2, column=2,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'], sticky="w"
        )

        self.proceed_button = TestButtons(
            self.PCR_processing_frame, text="Proceed",
            command=self.proceed
        )
        self.proceed_button.grid(
            row=2, column=3,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'], sticky="w"
        )

        self.BACK_button = MainButtons(
            self.PCR_processing_frame, text="<< BACK",
            command=lambda: self.back(self.PCR_frame)
        )
        self.BACK_button.grid(
            row=3, column=2,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'], sticky="w"
        )

        self.INFO_button = MainButtons(
            self.PCR_processing_frame, text="User guide",
            command=lambda: show_info(self.root, "PCR/info_processing.txt")
        )
        self.INFO_button.grid(
            row=3, column=3,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'], sticky="w"
        )

        if self.with_steam():
            self.fix1_button.configure(state="disabled")

    # ------------------------------------------------------------------ #
    #  Results table                                                     #
    # ------------------------------------------------------------------ #
    def set_reactivity_unit(self, unit):
        """Set the reactivity display unit ('%' or 'Beff') and redraw."""
        self.react_unit = unit
        self.refresh_table()
        Messages.show("info", "PCR_REACT_UNIT", unit=unit)

    def toggle_legend(self):
        """Show or hide the legend on every open plot."""
        self.legend_visible = not self.legend_visible
        for p in self.plot_windows:
            legend = p.get("legend")
            if legend is not None:
                legend.set_visible(self.legend_visible)
            try:
                p["canvas"].draw_idle()
            except Exception:
                pass

    def set_decimal(self, decimal_type):
        """Dialog to change the number of decimals for a value type."""
        win = tk.Toplevel(self.root)
        win.title(f"Set {decimal_type} decimal")
        win.geometry("240x150")
        win.config(bg=COLORS['BACKGROUND_COLOR'])

        tk.Label(
            win, text=f"Enter decimal places for {decimal_type}:",
            font=FONTS['DATA_FONT'], bg=COLORS['BACKGROUND_COLOR']
        ).grid(row=0, column=0, padx=GAPS['GAPS_X']['PAD_X_10'],
               pady=GAPS['GAPS_Y']['PAD_Y_10'], sticky="ew")

        entry = ttk.Entry(win, font=FONTS['DATA_FONT'])
        entry.grid(row=1, column=0, padx=GAPS['GAPS_X']['PAD_X_10'])
        entry.focus_set()

        def save():
            try:
                value = int(entry.get())
            except ValueError:
                Messages.show("error", "INVALID_DECIMAL")
                return
            if decimal_type == "Temperature":
                self.DECIMAL_TEMP = value
            elif decimal_type == "Reactivity":
                self.DECIMAL_REACT = value
            elif decimal_type == "Pressure":
                self.DECIMAL_PRESSURE = value
            else:
                self.DECIMAL_GENERAL = value
            self.refresh_table()
            Messages.show("info", "DECIMAL_SET",
                          type=decimal_type, value=value)
            win.destroy()

        SmallButtons(win, text="Save", command=save).grid(
            row=2, column=0, pady=GAPS['GAPS_Y']['PAD_Y_10']
        )
        entry.bind("<Return>", lambda e: save())

    # ------------------------------------------------------------------ #
    #  Computed parameters (menu: Computed parameters -> Edit parameters)#
    # ------------------------------------------------------------------ #
    def open_experiment_parameters(self) -> None:
        """
        Open the "Computed parameters" window, letting ITC, PrCR, MC,
        beta, sigma(DRDY), the PCR reference and the base window be
        edited after the module has been entered, the same as
        "Computed parameters -> Edit parameters" in DRDH_processing.
        """
        if (
            hasattr(self, "experiment_parameters_window")
            and self.widget_alive(self.experiment_parameters_window)
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
            ("ITC (α_T), pcm/°C:", "alpha_T", self.alpha_T),
            ("PrCR (α_P), pcm/MPa:", "alpha_P", self.alpha_P),
            ("MC, MJ/°C:", "MC", self.MC),
            ("β_eff, %:", "beta", self.beta),
            ("σ(DRDY), %:", "sigma_DRDY", self.sigma_DRDY),
            ("PCR reference, pcm/MWt:", "PCR_reference", self.PCR_reference),
            ("Base window, s:", "base", self.base),
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
                width=15,
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

    def apply_experiment_parameters(self) -> None:
        """
        Validate and apply the edited computed parameters.

        Changes are applied to the current PCR_processing instance only,
        and take effect the next time "Proceed" is pressed.
        """
        values = {}

        required_parameters = {"alpha_T", "alpha_P", "MC", "beta", "base"}
        optional_parameters = {"sigma_DRDY", "PCR_reference"}

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
        if values["MC"] <= 0:
            Messages.show(
                "error", "VALUE_POSTIVE", value="MC", sign="positive"
            )
            return

        if values["beta"] <= 0:
            Messages.show(
                "error", "VALUE_POSTIVE", value="β_eff", sign="positive"
            )
            return

        if values["base"] <= 0:
            Messages.show(
                "error", "VALUE_POSTIVE",
                value="Base window", sign="positive"
            )
            return

        if values["sigma_DRDY"] is not None and values["sigma_DRDY"] < 0:
            Messages.show(
                "error", "VALUE_POSTIVE", value="σ(DRDY)", sign="positive"
            )
            return

        # ---------------------------------------------------------
        # Apply
        # ---------------------------------------------------------
        self.alpha_T = values["alpha_T"]
        self.alpha_P = values["alpha_P"]
        self.MC = values["MC"]
        self.beta = values["beta"]
        self.sigma_DRDY = values["sigma_DRDY"]
        self.PCR_reference = values["PCR_reference"]
        self.base = int(values["base"])

        # Update temporary fields to normalized values.
        for parameter_name, value in values.items():
            self.experiment_parameter_vars[parameter_name].set(
                "" if value is None else str(value)
            )

        # The reference and beta may affect already computed results.
        self.compute_mean()
        self.refresh_table()

        self.close_experiment_parameters()

    def close_experiment_parameters(self) -> None:
        """Close the "Computed parameters" window."""
        if (
            hasattr(self, "experiment_parameters_window")
            and self.widget_alive(self.experiment_parameters_window)
        ):
            self.experiment_parameters_window.destroy()

        for attr in (
            "experiment_parameters_window",
            "experiment_parameter_vars",
            "experiment_parameter_entries",
        ):
            if hasattr(self, attr):
                delattr(self, attr)

    def create_table(self) -> None:
        """Right pane: one column per procedure plus the weighted mean."""
        style = ttk.Style(self.root)
        style.configure("PCR.Treeview", font=FONTS['DATA_FONT'])
        style.configure("PCR.Treeview.Heading", font=FONTS['HEADING_FONT'])

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

        self.columns = ['param', 'with', 'without', 'mean']
        headings = {
            'param': '',
            'with': 'With steam',
            'without': 'Without steam',
            'mean': 'Mean',
        }
        self.tree = tk.ttk.Treeview(
            self.right_frame, columns=self.columns,
            show="headings", height=TABLE['CELL_HEIGHT'],
            style="PCR.Treeview", selectmode="none"
        )
        for col in self.columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=TABLE['CELL_WIDTH'], anchor="center")

        # Row labels of the table
        self.row_labels = [
            ("R0", "R(t₀), %"),
            ("R1", "R(t₁), %"),
            ("T0", "T(t₀), °C"),
            ("T1", "T(t₁), °C"),
            ("dT", "ΔT, °C"),
            ("P0", "P(t₀), MPa"),
            ("P1", "P(t₁), MPa"),
            ("dP", "ΔP, MPa"),
            ("vT", "v_T(t₁), °C/h"),
            ("vG", "v_RCPS, °C/h"),
            ("N", "N(t₁), MWt"),
            ("dR_N", "ΔR_N, %"),
            ("PCR_exp", "PCR_exp, pcm/MWt"),
            ("delta", "δ(PCR_exp), %"),
            ("reference", "PCR ref., pcm/MWt"),
            ("deviation", "Deviation, %"),
        ]
        for key, label in self.row_labels:
            self.tree.insert(
                "", "end", iid=key,
                values=[label, "", "", ""]
            )

        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<Button-1>", self.on_tree_click)
        self.tree.bind("<Control-c>", self.copy_from_entry)
        self.tree.bind("<Control-C>", self.copy_from_entry)

    def on_tree_click(self, event):
        """
        Handle a click on a results-table cell.

        Shows the cell content in a small read-only entry, so that the
        computed parameter can be selected and copied (Ctrl+C) - the same
        behaviour as in DRDH_processing.
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
        """Close (destroy) the cell-copy entry, if any is open."""
        if self.active_entry is not None:
            self.active_entry.destroy()
            self.active_entry = None

    def copy_from_entry(self, event=None):
        """Copy the content of the currently open cell entry."""
        if self.active_entry is None:
            return "break"

        text = self.active_entry.get()
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

        return "break"

    def _react_from_pcm(self, pcm):
        """Convert a pcm value to the current display unit."""
        return Formulas.pcm_to_unit(pcm, self.react_unit, self.beta)

    def _react_unit_label(self):
        """Unit suffix used in the row labels."""
        return "%" if self.react_unit == "%" else "Beff"

    def _react_rows(self):
        """Row labels for the reactivity rows, with the current unit."""
        u = self._react_unit_label()
        return {
            "R0": f"R(t₀), {u}",
            "R1": f"R(t₁), {u}",
            "dR_N": f"ΔR_N, {u}",
        }

    def refresh_table(self) -> None:
        """Redraw the table from stored per-procedure results."""
        col_of = {
            "With steam extraction": "with",
            "Without steam extraction": "without",
        }
        react_labels = self._react_rows()
        react_raw = {"R0": "_R0_pcm", "R1": "_R1_pcm", "dR_N": "_dR_N_pcm"}
        r = self.DECIMAL_REACT

        # clear data columns; reactivity rows get the current-unit label
        for key, label in self.row_labels:
            shown = react_labels.get(key, label)
            self.tree.item(key, values=[shown, "", "", ""])

        for mode, res in self.results.items():
            col = self.columns.index(col_of[mode])
            for key, _ in self.row_labels:
                if key not in res:
                    continue
                vals = list(self.tree.item(key, "values"))
                if key in react_raw and react_raw[key] in res:
                    value = self._react_from_pcm(res[react_raw[key]])
                    vals[col] = f"{value:.{r}f}"
                else:
                    vals[col] = res[key]
                self.tree.item(key, values=vals)

        # Mean column, filled by compute_mean()
        mean = getattr(self, "mean_result", None)
        if mean:
            mcol = self.columns.index("mean")
            for key in ("PCR_exp", "reference", "deviation"):
                if key in mean:
                    vals = list(self.tree.item(key, "values"))
                    vals[mcol] = mean[key]
                    self.tree.item(key, values=vals)

    # ------------------------------------------------------------------ #
    #  Plot                                                              #
    # ------------------------------------------------------------------ #
    def create_plot(self, parent, large=False, is_main=False):
        """
        Plot with three axes: reactivity, temperature, pressure.

        The canvas and toolbar are packed into `parent`; `parent` itself is
        never destroyed, so the plot can be rebuilt in place (e.g. after a
        new file is loaded) without invalidating the frame.
        """
        for child in parent.winfo_children():
            child.destroy()

        if large:
            fig = Figure(figsize=(10, 6), constrained_layout=True)
        else:
            fig = Figure(figsize=(5, 3.5), constrained_layout=True)
        ax1 = fig.add_subplot(111)

        self.times = [
            datetime(1899, 12, 30) + timedelta(days=float(t))
            for t in self.Time
        ]

        ax1.plot(self.times, self.Reactivity, 'b-', label="R, Beff")
        ax1.set_ylabel("R, Beff", fontsize=PLOT['PLOT_LABEL_SIZE'])

        ax2 = ax1.twinx()
        ax2.plot(self.times, self.Temperature, 'r--', label="Temperature, °C")
        ax2.set_ylabel("Temperature, °C", fontsize=8)

        ax3 = ax1.twinx()
        ax3.plot(self.times, self.Pressure, 'g--', label="Pressure")
        ax3.spines['right'].set_position(('outward', PLOT['AXIS_SHIFT']))
        ax3.set_ylabel("Pressure", fontsize=8)

        # Group position, if available, on a fourth axis
        gp_series = self._group_position_series()
        if gp_series is not None:
            ax4 = ax1.twinx()
            ax4.plot(self.times, gp_series, color="purple",
                     linestyle=":", label="Group position")
            ax4.spines['right'].set_position(
                ('outward', 2 * PLOT['AXIS_SHIFT'])
            )
            ax4.set_ylabel("Group position, cm", fontsize=8)
        else:
            ax4 = None

        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        fig.autofmt_xdate()
        ax1.set_xlabel("Time")

        # Combined legend across all axes (R, T, P, group position)
        axes_for_legend = [ax1, ax2, ax3]
        if ax4 is not None:
            axes_for_legend.append(ax4)
        handles, labels = [], []
        for a in axes_for_legend:
            h, ls = a.get_legend_handles_labels()
            handles += h
            labels += ls
        legend = ax1.legend(handles, labels, fontsize=7, loc="best")
        if legend is not None:
            legend.set_visible(self.legend_visible)

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
        canvas.mpl_connect(
            "button_press_event",
            lambda e: self.on_plot_click(e, ax1)
        )
        canvas.draw()

        plot_obj = {
            "fig": fig, "ax1": ax1, "ax2": ax2, "ax3": ax3, "ax4": ax4,
            "canvas": canvas, "toolbar": toolbar,
            "base_line": None, "tau0_line": None, "tau1_line": None,
            "is_main": is_main,
            "legend": legend,

            # Extended cursor elements: crosshair over R, T, P
            "cursor_vline": ax1.axvline(
                self.times[0], visible=False,
                color="black", linestyle="--",
                linewidth=CURSOR['CURSOR_LINEWIDTH']
            ),
            "cursor_hline1": ax1.axhline(
                float(self.Reactivity[0]), visible=False,
                color="black", linestyle="--",
                linewidth=CURSOR['CURSOR_LINEWIDTH']
            ),
            "cursor_hline2": ax2.axhline(
                float(self.Temperature[0]), visible=False,
                color="black", linestyle="--",
                linewidth=CURSOR['CURSOR_LINEWIDTH']
            ),
            "cursor_hline3": ax3.axhline(
                float(self.Pressure[0]), visible=False,
                color="black", linestyle="--",
                linewidth=CURSOR['CURSOR_LINEWIDTH']
            ),
            "cursor_text": ax1.text(
                0, 0, "", visible=False,
                fontsize=CURSOR['CURSOR_TEXT_SIZE'],
                bbox=dict(boxstyle="round", facecolor="white", alpha=0.8)
            ),
            "cursor_cid": None,
        }
        canvas.mpl_connect(
            "scroll_event",
            lambda event, p=plot_obj: self.on_plot_scroll(event, p)
        )

        self.plot_windows.append(plot_obj)
        self.redraw_markers()

        # If the extended cursor is on, connect this new plot too
        if self.extended_cursor_enabled:
            plot_obj["cursor_cid"] = canvas.mpl_connect(
                "motion_notify_event",
                lambda event, p=plot_obj: self.on_mouse_move(event, p)
            )
        return plot_obj

    def create_plot_frame_large(self):
        """Container for the enlarged plot."""
        self.large_window = tk.Toplevel(self.root)
        self.large_window.title("PCR plot")
        frame = tk.Frame(self.large_window, bg="white")
        frame.pack(fill=tk.BOTH, expand=True)
        return frame

    def open_plot_in_new_window(self):
        """Open an enlarged copy of the plot."""
        frame = self.create_plot_frame_large()
        self.create_plot(frame, large=True)

    # ------------------------------------------------------------------ #
    #  Clicks and selection                                              #
    # ------------------------------------------------------------------ #
    def get_nearest_index(self, xdata) -> int:
        """Index of the sample nearest to the clicked time."""
        clicked = mdates.num2date(xdata).replace(tzinfo=None)
        target = mdates.date2num(clicked)
        nums = mdates.date2num(self.times)
        return int(np.argmin(np.abs(nums - target)))

    def on_plot_scroll(self, event, plot):
        """
        Zoom the plot horizontally with the mouse wheel, around the cursor.

        The X axis is shared by ax1, ax2, ax3 (and ax4, if present - the
        group-position axis). The Y axes remain unchanged. Same behaviour
        as in DRDH_processing.
        """
        axes = [plot["ax1"], plot["ax2"], plot["ax3"]]
        if plot.get("ax4") is not None:
            axes.append(plot["ax4"])

        if event.inaxes not in axes:
            return

        # Do not interfere with an explicitly selected toolbar mode.
        if plot["toolbar"].mode != '':
            return

        if event.xdata is None:
            return

        # Scroll up -> zoom in. Scroll down -> zoom out.
        if event.button == "up":
            scale = 0.8
        elif event.button == "down":
            scale = 1.25
        else:
            return

        ax1 = plot["ax1"]
        x_min, x_max = ax1.get_xlim()
        x_center = event.xdata

        new_x_min = x_center + (x_min - x_center) * scale
        new_x_max = x_center + (x_max - x_center) * scale

        for ax in axes:
            ax.set_xlim(new_x_min, new_x_max)

        plot["canvas"].draw_idle()

    def heating_rate(self, index: int) -> float:
        """
        Local heating rate at `index`, degC/h, by a linear fit of the
        temperature over the `base` window (seconds) centred on the point.
        """
        tsec = np.array(self.Time) * 86400.0
        t0 = tsec[index]
        mask = np.abs(tsec - t0) <= self.base / 2.0
        if mask.sum() < 3:
            # widen minimally if the window is too small
            lo = max(0, index - 3)
            hi = min(len(tsec), index + 4)
            sl = slice(lo, hi)
            slope = np.polyfit(tsec[sl], np.asarray(self.Temperature)[sl], 1)[0]
        else:
            slope = np.polyfit(
                tsec[mask], np.asarray(self.Temperature)[mask], 1
            )[0]
        return slope * 3600.0

    def redraw_markers(self):
        """
        Draw the current clicks (base, tau0, tau1) on every open plot.

        Lines are rebuilt from the stored indices, so all windows stay in
        sync and a re-clicked point simply moves. The base line is a solid
        black one; tau0/tau1 are the dashed brown lines used in ITC.
        """
        specs = [
            ("base_line", self.base_index, "#000000", "-"),
            ("tau0_line", self.tau0_index, "brown", "--"),
            ("tau1_line", self.tau1_index, "brown", "--"),
        ]
        for po in self.plot_windows:
            for key, index, colour, ls in specs:
                if po.get(key) is not None:
                    try:
                        po[key].remove()
                    except Exception:
                        pass
                    po[key] = None
                if index is not None:
                    po[key] = po["ax1"].axvline(
                        self.times[index], color=colour, lw=1.2, ls=ls
                    )
            po["canvas"].draw_idle()

    def clear_markers(self):
        """Remove every click line from every plot (indices stay intact)."""
        for po in self.plot_windows:
            for key in ("base_line", "tau0_line", "tau1_line"):
                if po.get(key) is not None:
                    try:
                        po[key].remove()
                    except Exception:
                        pass
                    po[key] = None
            po["canvas"].draw_idle()

    def on_plot_click(self, event, ax1):
        """
        Route a click depending on the stage of the current procedure.

        While points are still being placed, clicks fill them in order:
          without steam: base -> Get DTDt RCPS -> t0 -> t1
          with steam:    t0 -> t1
        Once every point is placed, a further click moves the nearest one,
        so any line can be re-clicked, both before and after "Proceed".
        """
        if event.inaxes is None or event.xdata is None:
            return
        idx = self.get_nearest_index(event.xdata)

        if not self.with_steam() and not self.base_fixed:
            self.base_index = idx
            self.v_RCPS = self.heating_rate(idx)
            self.redraw_markers()
            self.update_hint()
            return

        if self.tau0_index is None:
            self.tau0_index = idx
            self.redraw_markers()
            self.update_hint()
            return

        if self.tau1_index is None:
            self.tau1_index = idx
            self.redraw_markers()
            self.update_hint()
            return

        self.reclick_nearest(idx)

    def reclick_nearest(self, idx):
        """
        Move whichever placed point is closest to a new click.

        Lets the user correct a line after all points are set, including
        after "Proceed" if the result was not satisfactory.
        """
        candidates = []
        if not self.with_steam() and not self.base_fixed \
                and self.base_index is not None:
            candidates.append(("base", self.base_index))
        if self.tau0_index is not None:
            candidates.append(("tau0", self.tau0_index))
        if self.tau1_index is not None:
            candidates.append(("tau1", self.tau1_index))
        if not candidates:
            return

        which = min(candidates, key=lambda c: abs(c[1] - idx))[0]
        if which == "base":
            self.base_index = idx
            self.v_RCPS = self.heating_rate(idx)
        elif which == "tau0":
            self.tau0_index = idx
        else:
            self.tau1_index = idx
        self.redraw_markers()
        self.update_hint()

    def fix_base(self):
        """Confirm the base heating rate (without steam extraction)."""
        if self.with_steam():
            return
        if self.base_index is None:
            Messages.show("warning", "PCR_NO_BASE")
            return
        self.base_fixed = True
        self.update_hint()

    # ------------------------------------------------------------------ #
    #  Computation (methodology)                                         #
    # ------------------------------------------------------------------ #
    def _group_position_series(self):
        """
        A 1-D group-position series for the plot, or None. If several group
        columns exist, the first one is used.
        """
        gp = getattr(self, "Group_position", None)
        if gp is None:
            return None
        try:
            arr = np.asarray(gp, dtype=float)
        except Exception:
            return None
        if arr.ndim == 1:
            return arr
        if arr.ndim == 2 and arr.shape[1] >= 1:
            return arr[:, 0]
        return None

    def group_position_at(self, index):
        """
        Group position(s) at a sample, as a tuple so several columns are
        compared element-wise. Returns None if unavailable.
        """
        if getattr(self, "Group_position", None) is None:
            return None
        gp = np.asarray(self.Group_position)
        if gp.ndim == 1:
            return (round(float(gp[index]), 2),)
        return tuple(round(float(v), 2) for v in gp[index])

    def positions_differ(self) -> bool:
        """
        True if the group stood at a different position for the base than
        for the clicks after the reactivity was added.

        Only meaningful without steam extraction, where a base click exists.
        With steam extraction there is nothing to compare, so True.
        """
        if self.with_steam() or self.base_index is None:
            return True
        base_pos = self.group_position_at(self.base_index)
        if base_pos is None:
            return True
        for idx in (self.tau0_index, self.tau1_index):
            if idx is None:
                continue
            if self.group_position_at(idx) == base_pos:
                return False
        return True

    def proceed(self):
        """Compute the PCR of the current procedure and fill the table."""
        if self.tau0_index is None or self.tau1_index is None:
            Messages.show("warning", "PCR_NO_POINTS")
            return

        # Guard against missing entered values (should be caught in the
        # module, but a clear message beats a raw TypeError here).
        # ITC, PrCR, MC are needed for the value itself; sigma_DRDY only
        # affects the uncertainty, so it is not required here.
        if None in (self.alpha_T, self.alpha_P, self.MC):
            Messages.show("error", "PCR_MISSING_VALUES")
            return

        # Without steam extraction the group must have moved between the
        # base and the clicks. Equal positions mean the base was taken at
        # the same rod position - warn and let the user re-click everything.
        if not self.positions_differ():
            keep = Messages.show("question", "PCR_SAME_POSITION")
            if not keep:
                self.reset_selection()
                self.clear_markers()
                self.update_hint()
                return

        i0, i1 = self.tau0_index, self.tau1_index

        # v_Pumps: 0 with steam, else from the base click
        v_G = 0.0 if self.with_steam() else (self.v_RCPS or 0.0)
        v_T1 = self.heating_rate(i1)

        # Criterion: at tau1 the net rate must exceed 10 degC/h
        if (v_T1 - v_G) <= 10.0:
            proceed_anyway = Messages.show(
                "question", "PCR_RATE_LOW",
                rate=f"{v_T1 - v_G:.1f}"
            )
            if not proceed_anyway:
                return

        # Reactivity in pcm for the computation (stored in Beff, beta in
        # percent). The table converts pcm to the chosen display unit.
        rho0 = Formulas.reactivity_pcm(float(self.Reactivity[i0]), self.beta)
        rho1 = Formulas.reactivity_pcm(float(self.Reactivity[i1]), self.beta)
        T0 = float(self.Temperature[i0])
        T1 = float(self.Temperature[i1])
        P0 = float(self.Pressure[i0])
        P1 = float(self.Pressure[i1])

        dT = T1 - T0
        dP = P1 - P0

        # Power (N(tau0) = 0)
        N1 = self.MC * (v_T1 - v_G)

        # Power reactivity effect
        drho_N = -(
            (rho0 - rho1)
            + self.alpha_T * dT
            + self.alpha_P * dP
        )

        if N1 == 0:
            Messages.show("warning", "PCR_ZERO_POWER")
            return

        alpha_N = drho_N / N1

        # ---- uncertainties ----
        s_rho = self.sigma_rho_rel * abs(rho1 - rho0)
        s_rho_T = np.sqrt(
            self.sigma_alpha_T**2 * dT**2
            + self.alpha_T**2 * self.sigma_dT**2
        )
        # sigma(alpha_P) = sigma(DRDY) * PrCR. If sigma(DRDY) was not
        # entered, this term drops out and only sigma(dP) remains.
        if self.sigma_DRDY is None:
            sigma_alpha_P = 0.0
        else:
            sigma_alpha_P = (self.sigma_DRDY / 100.0) * self.alpha_P
        s_rho_P = np.sqrt(
            sigma_alpha_P**2 * dP**2
            + self.alpha_P**2 * self.sigma_dP**2
        )
        s_drho_N = np.sqrt(s_rho**2 + s_rho_T**2 + s_rho_P**2)
        d_drho_N = s_drho_N / abs(drho_N) if drho_N else 0.0

        s_N = np.sqrt(
            (v_T1 + v_G)**2 * self.sigma_MC_rel**2
            + self.MC**2 * (
                (self.sigma_v_rel * v_T1)**2
                + (self.sigma_v_rel * v_G)**2
            )
        )
        d_N = s_N / abs(N1)

        delta_alpha = np.sqrt(d_drho_N**2 + d_N**2)   # relative

        # ---- store, formatted ----
        r = self.DECIMAL_REACT
        res = {
            "R0": f"{rho0:.1f}",
            "R1": f"{rho1:.1f}",
            "T0": f"{T0:.{self.DECIMAL_TEMP}f}",
            "T1": f"{T1:.{self.DECIMAL_TEMP}f}",
            "dT": f"{dT:.{self.DECIMAL_TEMP}f}",
            "P0": f"{P0:.3f}",
            "P1": f"{P1:.3f}",
            "dP": f"{dP:.3f}",
            "vT": f"{v_T1:.2f}",
            "vG": f"{v_G:.2f}",
            "N": f"{N1:.2f}",
            "dR_N": f"{drho_N:.1f}",
            "PCR_exp": f"{alpha_N:.3f}",
            "delta": f"{100 * delta_alpha:.1f}",
            "reference": (
                "-" if self.PCR_reference is None
                else f"{self.PCR_reference:.3f}"
            ),
            "deviation": "-",
            # raw reactivity values in pcm, for unit switching
            "_R0_pcm": rho0,
            "_R1_pcm": rho1,
            "_dR_N_pcm": drho_N,
            # raw values for the weighted mean
            "_alpha_N": alpha_N,
            "_sigma_abs": abs(alpha_N) * delta_alpha,
        }

        # per-procedure deviation from the reference, if given
        if self.PCR_reference is not None and self.PCR_reference != 0:
            dev = (alpha_N - self.PCR_reference) / abs(self.PCR_reference)
            res["deviation"] = f"{100 * dev:.1f}"

        self.results[self.steam_mode] = res
        self.compute_mean()
        self.refresh_table()
        self.update_status_labels()
        self.update_hint()

    def compute_mean(self):
        """Inverse-variance weighted mean of the two procedures."""
        both = [
            r for r in self.results.values()
            if r.get("_sigma_abs", 0) > 0
        ]
        if len(both) < 2:
            # with a single procedure the mean equals it
            if len(self.results) == 1:
                only = next(iter(self.results.values()))
                self.mean_result = {"PCR_exp": only["PCR_exp"]}
                self._apply_mean_reference(only["_alpha_N"])
            return

        alpha_mean, _ = Formulas.weighted_mean(
            [r["_alpha_N"] for r in both],
            [r["_sigma_abs"] for r in both]
        )

        self.mean_result = {"PCR_exp": f"{alpha_mean:.3f}"}
        self._apply_mean_reference(alpha_mean)

    def _apply_mean_reference(self, alpha_mean):
        """Reference and deviation of the mean, if a reference is given."""
        if self.PCR_reference is None:
            self.mean_result["reference"] = "-"
            self.mean_result["deviation"] = "-"
            return
        self.mean_result["reference"] = f"{self.PCR_reference:.3f}"
        if self.PCR_reference != 0:
            dev = (alpha_mean - self.PCR_reference) / abs(self.PCR_reference)
            self.mean_result["deviation"] = f"{100 * dev:.1f}"
        else:
            self.mean_result["deviation"] = "-"

    # ------------------------------------------------------------------ #
    #  Mode switching and file loading                                   #
    # ------------------------------------------------------------------ #
    def switch_mode(self):
        """
        Switch to the other steam mode to measure the second procedure.

        The result of the current procedure is kept: it stays in the table
        and is used for the weighted mean once both are done.
        """
        if self.steam_mode == "With steam extraction":
            self.steam_mode = "Without steam extraction"
        else:
            self.steam_mode = "With steam extraction"

        # Fresh selection for the new procedure; results are preserved
        self.reset_selection()
        self.clear_markers()

        state = "disabled" if self.with_steam() else "normal"
        self.fix1_button.configure(state=state)

        self.update_mode_label()
        self.update_hint()

    def load_new_file(self):
        """
        Load a new NFME file, in case the second procedure was recorded
        separately. The same columns are resolved by their header names, so
        a differently ordered export still works as long as the headers
        match. A missing header is reported.
        """
        filename = filedialog.askopenfilename(
            title="Load a new NFME file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not filename:
            return

        df = self._read_file(filename)
        if df is None:
            Messages.show("error", "PCR_FILE_ERROR")
            return

        # Resolve every NFME parameter by the header(s) used before
        missing = []
        resolved = {}
        for attr, headers in self.column_headers.items():
            absent = [h for h in headers if h not in df.columns]
            if absent:
                missing.extend(absent)
                continue
            cols = df[headers]
            series = (
                cols.mean(axis=1) if len(headers) > 1 else cols.iloc[:, 0]
            )
            resolved[attr] = series.to_numpy(dtype=float)

        if missing:
            Messages.show(
                "error", "PCR_HEADER_NOT_FOUND",
                headers="\n".join(f"• {h}" for h in missing)
            )
            return

        # Apply the resolved arrays
        self.Reactivity = resolved.get("Reactivity", self.Reactivity)
        self.Temperature = resolved.get("Temperature", self.Temperature)
        self.Pressure = resolved.get("Pressure", self.Pressure)
        self.Time = resolved.get("Time", self.Time)
        self.Group_position = resolved.get(
            "Group_position", self.Group_position
        )

        # Fresh selection; results stay in the table. Rebuild the plot in
        # place - the plot_frame itself must NOT be destroyed, or its path
        # becomes invalid. create_plot clears the frame's children first.
        self.reset_selection()
        self.plot_windows = [
            po for po in self.plot_windows if not po.get("is_main")
        ]
        self.create_plot(self.plot_frame, is_main=True)
        self.update_hint()

    def _read_file(self, filename):
        """
        Read an NFME file the same way the main window does: tab-separated,
        trying the usual encodings. Returns a DataFrame or None on failure.
        """
        for encoding in ENCODINGS:
            try:
                return pd.read_csv(filename, sep="\t", encoding=encoding)
            except Exception:
                continue
        return None

    # ------------------------------------------------------------------ #
    #  Navigation                                                        #
    # ------------------------------------------------------------------ #
    def extended_cursor(self):
        """
        Toggle the extended cursor mode on every open plot.

        When enabled, a crosshair follows the mouse and a small box shows
        the reactivity, temperature and pressure at the nearest sample.
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
                if plot.get("cursor_cid") is not None:
                    plot["canvas"].mpl_disconnect(plot["cursor_cid"])
                    plot["cursor_cid"] = None
                for key in ("cursor_vline", "cursor_hline1",
                            "cursor_hline2", "cursor_hline3", "cursor_text"):
                    if plot.get(key) is not None:
                        plot[key].set_visible(False)
                plot["canvas"].draw_idle()

    def on_mouse_move(self, event, plot):
        """Update the crosshair and the R/T/P read-out at the cursor."""
        if not self.extended_cursor_enabled:
            return
        if plot["toolbar"].mode != '':
            return
        if event.inaxes not in (plot["ax1"], plot["ax2"], plot["ax3"]):
            return
        if event.xdata is None:
            return

        clicked_time = mdates.num2date(event.xdata).replace(tzinfo=None)
        idx = min(
            range(len(self.times)),
            key=lambda i: abs(self.times[i] - clicked_time)
        )

        time_val = self.times[idx]
        R = float(self.Reactivity[idx])
        T = float(self.Temperature[idx])
        P = float(self.Pressure[idx])

        plot["cursor_vline"].set_xdata([time_val, time_val])
        plot["cursor_hline1"].set_ydata([R, R])
        plot["cursor_hline2"].set_ydata([T, T])
        plot["cursor_hline3"].set_ydata([P, P])
        for key in ("cursor_vline", "cursor_hline1",
                    "cursor_hline2", "cursor_hline3"):
            plot[key].set_visible(True)

        textstr = (
            f"{time_val.strftime('%H:%M:%S')}\n"
            f"R: {R:.{self.DECIMAL_REACT}f}\n"
            f"T: {T:.{self.DECIMAL_TEMP}f}\n"
            f"P: {P:.3f}"
        )
        plot["cursor_text"].set_text(textstr)
        plot["cursor_text"].set_position((time_val, R))
        plot["cursor_text"].set_visible(True)

        plot["canvas"].draw_idle()

    def back(self, window):
        """Return to the parameter-selection window."""
        try:
            self.root.winfo_toplevel().config(menu="")
        except Exception:
            pass
        if window is not None:
            window.destroy()
        self.main_app.create_PCR_window()

    # ------------------------------------------------------------------ #
    #  Export                                                            #
    # ------------------------------------------------------------------ #
    def get_table_data(self):
        """Rows of the results table as plain lists."""
        data = []
        for key, _ in self.row_labels:
            data.append(list(self.tree.item(key, "values")))
        return data

    def save_to_Excel(self):
        """Export the results table to Excel."""
        initial_dir = os.path.dirname(os.path.abspath(__file__))
        filename = filedialog.asksaveasfilename(
            initialdir=initial_dir, defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("Excel 97-2003", "*.xls")],
            title="Save results"
        )
        if not filename:
            return

        wb = Workbook()
        ws = wb.active
        ws.title = "PCR"

        headers = ['', 'With steam', 'Without steam', 'Mean']
        ws.append(headers)
        for row in self.get_table_data():
            ws.append(row)

        for col_idx in range(1, len(headers) + 1):
            max_len = len(str(headers[col_idx - 1]))
            for row in ws.iter_rows(min_col=col_idx, max_col=col_idx):
                for cell in row:
                    if cell.value is not None:
                        max_len = max(max_len, len(str(cell.value)))
            ws.column_dimensions[get_column_letter(col_idx)].width = (
                max_len + 2
            )

        wb.save(filename)

    def save_to_txt(self):
        """Export the results table as a tab-separated text file."""
        initial_dir = os.path.dirname(os.path.abspath(__file__))
        filename = filedialog.asksaveasfilename(
            initialdir=initial_dir, defaultextension=".txt",
            filetypes=[("Text files", "*.txt")], title="Save results"
        )
        if not filename:
            return

        headers = ['', 'With steam', 'Without steam', 'Mean']
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\t".join(headers) + "\n")
            for row in self.get_table_data():
                f.write("\t".join(str(c) for c in row) + "\n")