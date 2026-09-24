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
SPLITTER_MINSIZES, PLOT, CURSOR, TABLE, ENTRY_WIDTH
)

mpl.rcParams['font.family'] = 'Times New Roman'


class ITC_processing:
    """
    ITC_processing module to determine ITC.

    This class provides a Tkinter-based GUI for:
    - Computing ITC/MTC using a variety of techniques
    - Computing DRDY
    - Computing the deviation between experimental obtained value and
    the relevant computed value
    - Exporting results to Excel or in .txt format

    Attributes:
        listed in "__init__"

    Methods:
        create_ITC_processing_window: Create the main ITC processing window.
        create_splitter_window: Create a horizontal splitter.
        labels: Create and locate all labels.
        checkbox: Create a checkbox changing reactivity units
        change_checkbox_text: Auxiliary method. Update labels when switching
        reactivity units.
        buttons: Create all buttons in the ITC_processing interface.
        create_menu: Create the top menu bar for ITC_processing window.
        set_decimal: Change decimal value.
        create_table: Create a table comprises the results.
        on_tree_click: Proceed with a click on table cell, Allows to copy
        cell contents.
        close_active_entry: Auxiliary method. "Close" a cell of the table.
        copy_from_entry: Auxiliary method. Copy selected table cell content.
        get_table_data: Auxiliary method. Aimes at providing opportunity to
        save the result.
        save_to_Excel: Save the results in the new Excel file.
        save_to_txt: Save the results in the ".txt" format.
        choose_save_format: Select the results export format.
        save_excel: Launch the saving process in the new Excel file.
        save_txt: Launch the saving process in the ".txt" format.
        extended_cursor: Set the extended cursor mode.
        on_mouse_move: Update extended cursor tabel parameters.
        back: Close ITC_processing and return to ITC_module.
        proceed: Launch the computation.
        update_table: Fill the result table.
        save_decimal: Save the Decimal value which was set by the user.
        create_plot: Create a plot(s).
        open_plot_in_new_window: Create large plot in the window.
        create_plot_frame: Create the field for the initial plot.
        draw_vertical_line: Draw a vertical line on all plots.
        on_plot_click: Proceed with mouse clicks on the plot.
        techniques 1-3: compute the ITC ect.
        DRDY: Compute DRDY.
        error: Compute the error values for ITC and DRDY.
        update_labels: Refresh label values after Decimal or unit changes.
    """

    def __init__(self, root: tk.Widget, main_app: Any):
        """
        Attributes:
            root: Parent Tkinter widget.
            main_app: Reference to main application controller.
            plot_windows: List of active matplotlib plot objects.
            extended_cursor_enabled: Enables interactive multi-axis cursor.
            beta (Optional[float]): beta value.
            DTC (Optional[float]): Value for DTC parameter.
            ITC_computed (Optional[float]): Computed ITC value.
            MTC_computed (Optional[float]): Computed MTC value.
            DRDY_computed (Optional[float]): Computed DRDY value.
            boric_acid (Optional[float]): Boric acid concentration.
            DYDT (float): DYDT value, default -1.73.
            Other necessary attributes imported.
        """
        self.root: tk.Widget = root
        self.main_app: Any = main_app
        self.root.winfo_toplevel().iconbitmap("Icons/ITC_icon.ico")
        self.ITC_frame: Optional[tk.Frame] = None
        self.beta: float = self.main_app.main_app.beta
        self.DTC: float = self.main_app.DTC
        self.active_entry: Optional[ttk.Entry] = None
        self.plot_windows: List[Dict[str, Any]] = []
        self.extended_cursor_enabled: bool = False

        # Obtain values from ITC_module
        self.ITC_computed: Optional[float] = getattr(
            self.main_app, "ITC_computed", None
        )
        self.MTC_computed: Optional[float] = getattr(
            self.main_app, "MTC_computed", None
        )

        # If merely MTC was set
        if self.ITC_computed is None and self.MTC_computed is not None:
            self.ITC_computed = self.DTC + self.MTC_computed

        # If merely ITC was set
        elif self.MTC_computed is None and self.ITC_computed is not None:
            self.MTC_computed = self.ITC_computed - self.DTC

        self.DRDY_computed: Optional[float] = (
            self.main_app.DRDY_computed
            if hasattr(self.main_app, 'DRDY_computed') else None
        )
        self.boric_acid: Optional[float] = (
            self.main_app.boric_acid
            if hasattr(self.main_app, 'boric_acid') else None
        )
        self.DYDT: float = (
            self.main_app.DYDT
            if hasattr(self.main_app, 'DYDT') else -1.73
        )

        self.DECIMAL: int = DECIMAL['DECIMAL']
        self.DECIMAL_REACT: int = DECIMAL['DECIMAL_REACT']
        self.DECIMAL_TEMP: int = DECIMAL['DECIMAL_TEMP']
        self.DECIMAL_GROUP: int = DECIMAL['DECIMAL_GROUP']

        self.min_points: int = ITC_COMPUTATION_VALUES['MIN_POINTS']
        self.points_amount: int = ITC_COMPUTATION_VALUES['POINTS_AMOUNT']
        self.step_points: int = ITC_COMPUTATION_VALUES['STEP_POINTS']

    def create_ITC_processing_window(self) -> None:
        """Create the main ITC processing window layout and initialize UI."""
        self.ITC_processing_frame = tk.Frame(
            self.root, bg=COLORS['BACKGROUND_COLOR']
        )
        self.ITC_processing_frame.place(x=0, y=0, relwidth=1, relheight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.ITC_processing_frame.grid_rowconfigure(0, weight=0)
        self.ITC_processing_frame.grid_rowconfigure(1, weight=1)
        self.ITC_processing_frame.grid_rowconfigure(2, weight=0)
        self.ITC_processing_frame.grid_rowconfigure(3, weight=0)
        self.ITC_processing_frame.grid_rowconfigure(4, weight=0)

        self.ITC_processing_frame.grid_columnconfigure(0, weight=4)
        self.ITC_processing_frame.grid_columnconfigure(1, weight=4)
        self.ITC_processing_frame.grid_columnconfigure(2, weight=2)
        self.ITC_processing_frame.grid_columnconfigure(3, weight=2)

        self.create_menu()
        self.create_splitter_window()
        self.create_plot_frame()
        self.labels()
        self.buttons()
        self.checkbox()
        self.create_table()

    def create_splitter_window(self) -> None:
        """Create a horizontal splitter separating plot and results table."""
        self.splitter_window = tk.PanedWindow(
            self.ITC_processing_frame,
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
        self.ITC_processing_frame.grid_rowconfigure(1, weight=1)

    def labels(self):
        """
        Create and locate all labels in the UI.
        """
        self.main_window_label = tk.Label(
            self.ITC_processing_frame, text='ITC Module',
            font=FONTS['TITLE_FONT'], bg=COLORS['BACKGROUND_COLOR']
        ).grid(
            row=0, column=0, columnspan=4,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            )

        self.R1_label = tk.Label(
            self.ITC_processing_frame, text='R₁ = _.____ Beff',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.R1_label.grid(
            row=2, column=2,
            padx=GAPS['GAPS_X']['PAD_X_10'],
        )
        self.R2_label = tk.Label(
            self.ITC_processing_frame, text='R₂ = _.____ Beff',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.R2_label.grid(
            row=3, column=2,
            padx=GAPS['GAPS_X']['PAD_X_10'],
        )
        self.delta_R_label = tk.Label(
            self.ITC_processing_frame, text='dR = _.____ Beff',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.delta_R_label.grid(
            row=4, column=2,
            padx=GAPS['GAPS_X']['PAD_X_10'],
        )
        self.T1_label = tk.Label(
            self.ITC_processing_frame, text='T₁ = ___._ °C',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.T1_label.grid(
            row=2, column=3,
            padx=GAPS['GAPS_X']['PAD_X_10'],
        )
        self.T2_label = tk.Label(
            self.ITC_processing_frame, text='T₂ = ___._ °C',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.T2_label.grid(
            row=3, column=3,
            padx=GAPS['GAPS_X']['PAD_X_10'],
        )
        self.delta_T_label = tk.Label(
            self.ITC_processing_frame, text='dT = ___._ °C',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.delta_T_label.grid(
            row=4, column=3,
            padx=GAPS['GAPS_X']['PAD_X_10'],
        )
        self.Reactivity_change_unit = tk.Label(
            self.ITC_processing_frame,
            text='Reactivity is displayed as a: beta',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.Reactivity_change_unit.grid(
            row=2, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
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
            self.ITC_processing_frame,
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

    def change_checkbox_text(self):
        """
        Auxiliary method. Update labels when switching between beta and
        percent reactivity units.
        """
        if self.checkbox_var.get() == 1:
            self.checkbox_text.set("%")
            self.Reactivity_change_unit.configure(
                text='Reactivity is displayed as a: %'
            )
            self.R1_label.config(
                text=f'R₁ = {self.R1_percent:.{self.DECIMAL_REACT}f} %'
            )
            self.R2_label.config(
                text=f'R₂ = {self.R2_percent:.{self.DECIMAL_REACT}f} %'
            )
            self.delta_R_label.config(
                text=f'ΔR = {self.delta_R_percent:.{self.DECIMAL_REACT}f} %'
            )
        else:
            self.checkbox_text.set("beta")
            self.Reactivity_change_unit.configure(
                text='Reactivity is displayed as a: beta'
            )
            self.R1_label.config(
                text=f'R₁ = {self.R1_beta:.{self.DECIMAL_REACT}f} Beff'
            )
            self.R2_label.config(
                text=f'R₂ = {self.R2_beta:.{self.DECIMAL_REACT}f} Beff'
            )
            self.delta_R_label.config(
                text=f'ΔR = {self.delta_R_beta:.{self.DECIMAL_REACT}f} Beff'
            )

    def buttons(self):
        """
        Create buttons to:
        - Compute the ITC
        - Save results
        - Back navigation
        - User guide
        """
        self.Proceed_button = TestButtons(
              self.ITC_processing_frame,
              text='Proceed',
              command=self.proceed,
        )
        self.Proceed_button.grid(
            row=3, column=0,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10']
        )
        self.Proceed_button.config(state="disabled")

        self.save_button = TestButtons(
              self.ITC_processing_frame,
              text='Save',
              command=self.choose_save_format,
        )
        self.save_button.grid(
            row=3, column=1,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10']
        )

        self.BACK_button = MainButtons(
              self.ITC_processing_frame,
              text='<< BACK',
              command=lambda: self.back(self.ITC_processing_frame),
        )
        self.BACK_button.grid(
            row=4, column=0,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10']
        )

        self.INFO_button = MainButtons(
              self.ITC_processing_frame,
              text='User guide',
              command=lambda: show_info(self.root, "ITC/info_processing.txt"),
        )
        self.INFO_button.grid(
            row=4, column=1,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
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

        Decimal.add_command(
            label="Temperature decimal",
            font=FONTS['DATA_FONT'],
            command=lambda: self.set_decimal("Temperature")
        )
        Decimal.add_command(
            label="Reactivity decimal",
            font=FONTS['DATA_FONT'],
            command=lambda: self.set_decimal("Reactivity")
        )
        Decimal.add_command(
            label="Group position decimal",
            font=FONTS['DATA_FONT'],
            command=lambda: self.set_decimal("Group position")
        )
        Decimal.add_command(
            label="General decimal",
            font=FONTS['DATA_FONT'],
            command=lambda: self.set_decimal("General")
        )

        info = tk.Menu(self.menu_bar, tearoff=1)
        self.menu_bar.add_cascade(label="INFO", menu=info)

        info.add_command(
            label="INFO",
            font=FONTS['DATA_FONT'],
            command=lambda: show_info(self.root, "ITC/info_processing.txt")
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
        computed_parameters = tk.Menu(
            self.menu_bar,
            tearoff=1
        )

        self.menu_bar.add_cascade(
            label="Computed parameters",
            menu=computed_parameters
        )

        computed_parameters.add_command(
            label="Edit parameters",
            font=FONTS['DATA_FONT'],
            command=self.open_computed_parameters
        )
    def open_computed_parameters(self) -> None:
        """
        Open a window for editing computed/reference ITC parameters.
        Changes are applied only to the current ITC_processing instance.
        """

        if (
            hasattr(self, "computed_parameters_window")
            and self.computed_parameters_window.winfo_exists()
        ):
            self.computed_parameters_window.lift()
            self.computed_parameters_window.focus_force()
            return

        window = tk.Toplevel(self.root)
        window.title("Computed parameters")
        window.resizable(False, False)

        self.computed_parameters_window = window

        frame = tk.Frame(
            window,
            bg=COLORS['PARAMETERS_BACKGROUND_COLOR']
        )
        frame.grid(
            row=0,
            column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_10']
        )

        parameters = [
            ("DTC:", "DTC", self.DTC),
            ("ITC:", "ITC_computed", self.ITC_computed),
            ("MTC:", "MTC_computed", self.MTC_computed),
            ("DRDY:", "DRDY_computed", self.DRDY_computed),
            ("Boric acid concentration:", "boric_acid", self.boric_acid),
            ("DYDT:", "DYDT", self.DYDT),
        ]

        self.computed_parameter_vars = {}
        self.computed_parameter_entries = {}

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

            self.computed_parameter_vars[parameter_name] = var

            entry = tk.Entry(
                frame,
                width=ENTRY_WIDTH,
                textvariable=var,
                font=FONTS['DATA_FONT']
            )

            self.computed_parameter_entries[parameter_name] = entry

            entry.grid(
                row=row,
                column=1,
                padx=GAPS['GAPS_X']['PAD_X_10'],
                pady=GAPS['GAPS_Y']['PAD_Y_5']
            )

        button_frame = tk.Frame(
            frame,
            bg=COLORS['PARAMETERS_BACKGROUND_COLOR']
        )

        button_frame.grid(
            row=len(parameters),
            column=0,
            columnspan=2,
            pady=GAPS['GAPS_Y']['PAD_Y_10_20']
        )

        self.apply_parameters_button = TestButtons(
            button_frame,
            text="Apply",
            command=self.apply_computed_parameters,
        )

        self.apply_parameters_button.grid(
            row=0,
            column=0,
            padx=GAPS['GAPS_X']['PAD_X_5']
        )

        self.cancel_parameters_button = MainButtons(
            button_frame,
            text="Cancel",
            command=self.close_computed_parameters,
        )

        self.cancel_parameters_button.grid(
            row=0,
            column=1,
            padx=GAPS['GAPS_X']['PAD_X_5']
        )

        window.protocol(
            "WM_DELETE_WINDOW",
            self.close_computed_parameters
        )

        window.bind(
            "<Return>",
            lambda event: self.apply_computed_parameters()
        )

        window.bind(
            "<Escape>",
            lambda event: self.close_computed_parameters()
        )


    def apply_computed_parameters(self) -> None:
        """
        Validate and apply edited computed/reference parameters.
        Changes affect only the current ITC_processing instance.
        """

        values = {}

        for parameter_name, var in self.computed_parameter_vars.items():
            text = var.get().strip().replace(",", ".")

            if not text:
                # Пустое поле означает: оставить текущее значение без изменений
                values[parameter_name] = getattr(self, parameter_name)
                continue

            try:
                values[parameter_name] = float(text)

            except ValueError as error:
                Messages.show(
                    "error",
                    "VALUE_ERROR",
                    value_name=parameter_name,
                    error=error
                )

                self.computed_parameter_entries[
                    parameter_name
                ].focus_set()

                return

        # ---------------------------------------------------------
        # Validation
        # ---------------------------------------------------------

        if values["DTC"] > 0:
            Messages.show(
                "error",
                "VALUE_POSTIVE",
                value="DTC",
                sign="negative"
            )
            return

        if values["DYDT"] == 0:
            Messages.show(
                "error",
                "VALUE_ERROR",
                value_name="DYDT",
                error="DYDT cannot be zero"
            )
            return

        if (
            values["boric_acid"] is not None
            and values["boric_acid"] < 0
        ):
            Messages.show(
                "error",
                "VALUE_POSTIVE",
                value="Boric acid concentration",
                sign="positive"
            )
            return

        # ---------------------------------------------------------
        # Apply
        # ---------------------------------------------------------

        self.DTC = values["DTC"]
        self.ITC_computed = values["ITC_computed"]
        self.MTC_computed = values["MTC_computed"]
        self.DRDY_computed = values["DRDY_computed"]
        self.boric_acid = values["boric_acid"]
        self.DYDT = values["DYDT"]

        # Synchronize values used by the parent application.
        self.main_app.DTC = self.DTC
        self.main_app.ITC_computed = self.ITC_computed
        self.main_app.MTC_computed = self.MTC_computed
        self.main_app.DRDY_computed = self.DRDY_computed
        self.main_app.boric_acid = self.boric_acid
        self.main_app.DYDT = self.DYDT

        self.update_table()

        if hasattr(self, "canvas"):
            self.canvas.draw_idle()

        self.close_computed_parameters()
    def close_computed_parameters(self) -> None:
        """Close the computed parameters window."""

        if (
            hasattr(self, "computed_parameters_window")
            and self.computed_parameters_window.winfo_exists()
        ):
            self.computed_parameters_window.destroy()
    def create_table(self):
        """
        Create a table comprises the results:
        - ITC
        - MTC
        - DRDY
        - Deviations
        - Errors
        - Parameters under which the test was carried out
        """

        style = ttk.Style(self.root)
        style.configure("ITC.Treeview", font=FONTS['DATA_FONT'])
        style.configure(
            "ITC.Treeview.Heading", font=FONTS['HEADING_FONT']
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

        self.columns = [
            '',
            'MTC',
            'ITC',
            'Deviation_ITC',
            "DRDY",
            "Deviation_DRDY"
        ]
        self.tree = tk.ttk.Treeview(
            self.right_frame, columns=self.columns,
            show="headings", height=TABLE['CELL_HEIGHT'],
            style="ITC.Treeview", selectmode="none"
        )

        for col in self.columns:
            self.tree.heading(col, text=col)
            self.tree.column(
                col, width=TABLE['CELL_WIDTH'], anchor="center"
            )

        rows = [
            "Technique 1",
            "Technique 2",
            "Technique 3",
            "Result",
            "Computed values",
            "2sigma_ITC",
            "2sigma_DRDY",
            "Units:",
            "Group_position:"
        ]
        for row in rows:
            self.tree.insert(
                "", "end", iid=row, values=["" for _ in self.columns]
            )

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
        data = []
        for item_id in self.tree.get_children():
            values = self.tree.item(item_id, "values")
            data.append(values)
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

        ws.append(self.columns)
        for col in range(1, len(self.columns) + 1):
            cell = ws.cell(row=1, column=col)
            cell.font = FONTS['EXCEL_FONT']

        for row_idx, row in enumerate(self.get_table_data(), start=2):
            for col_idx, value in enumerate(row, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.font = FONTS['EXCEL_FONT']

        for col_idx, col_name in enumerate(self.columns, start=1):
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
            f.write("\t".join(self.columns) + "\n")
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
        - Interval distance indicator betweel left and right mouse clicks
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
                plot["cursor_hline1"].set_visible(False)
                plot["cursor_hline2"].set_visible(False)
                plot["cursor_hline3"].set_visible(False)
                plot["cursor_text"].set_visible(False)

                plot["distance_label"].set_text("")

                plot["canvas"].draw_idle()

    def on_mouse_move(self, event, plot):
        """
        Update extended cursor tabel parameters according to mouse position.
        Displays the interval distance.

        Args:
            event: Matplotlib motion event.
            plot (dict): Plot container dictionary.
        """
        if not self.extended_cursor_enabled:
            return

        if plot["toolbar"].mode != '':
            return

        if event.inaxes not in (plot["ax1"], plot["ax2"], plot["ax3"]):
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
        T = float(self.Temperature[nearest_index])
        H = float(self.Group_position[nearest_index])

        plot["cursor_vline"].set_xdata([time_val, time_val])
        plot["cursor_hline1"].set_ydata([R, R])
        plot["cursor_hline2"].set_ydata([T, T])
        plot["cursor_hline3"].set_ydata([H, H])

        plot["cursor_vline"].set_visible(True)
        plot["cursor_hline1"].set_visible(True)
        plot["cursor_hline2"].set_visible(True)
        plot["cursor_hline3"].set_visible(True)

        textstr = (
            f"{time_val.strftime('%H:%M:%S')}\n"
            f"R: {R:.{self.DECIMAL_REACT}f}\n"
            f"T: {T:.{self.DECIMAL_TEMP}f}\n"
            f"H: {H:.{self.DECIMAL_GROUP}f}"
        )

        plot["cursor_text"].set_text(textstr)
        plot["cursor_text"].set_position((time_val, R))
        plot["cursor_text"].set_visible(True)

        distance = self.distance_to_lines(nearest_index)

        if distance is None:
            plot["distance_label"].set_text("")
        else:

            plot["distance_label"].set_text(f"Time gap: {distance}")

            if distance < self.min_points:
                plot["distance_label"].set_color("red")
            else:
                plot["distance_label"].set_color("green")

        plot["cursor_text"].set_text(textstr)

        # Set the text position next to the current cursor position
        plot["cursor_text"].set_position((time_val, R))
        plot["cursor_text"].set_visible(True)

        plot["canvas"].draw_idle()

    def distance_to_lines(self, idx):
        distances = []

        if hasattr(self, "start_index"):
            distances.append(abs(idx - self.start_index))

        if hasattr(self, "finish_index"):
            distances.append(abs(idx - self.finish_index))

        if not distances:
            return None

        return min(distances)

    def back(self, window):
        """
        Close ITC_processing and return to ITC_module.

        Results remain.

        Args:
            window (tk.Widget): ITC frame to destroy.
        """
        root_window = self.root.winfo_toplevel()
        root_window.config(menu=None)
        self.root.config(menu=None)

        self.menu_bar.destroy()
        self.menu_bar = None
        window.destroy()
        root_window.config(menu=None)

        self.main_app.create_ITC_window()

        root_window.title('ITC')
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
                if decimal_type == "Temperature":
                    self.DECIMAL_TEMP = value
                elif decimal_type == "Reactivity":
                    self.DECIMAL_REACT = value
                elif decimal_type == "Group position":
                    self.DECIMAL_GROUP = value
                else:
                    self.DECIMAL = value

                self.update_labels()
                if hasattr(self, 'itc1'):
                    self.update_table()

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

    def proceed(self):
        """Launch the computation."""
        (
            self.itc1,
            self.mtc1,
            self.dev1_itc,
            self.drdy1,
            self.dev1_drdy
        ) = self.technique_1()
        (
            self.itc2,
            self.mtc2,
            self.dev2_itc,
            self.drdy2,
            self.dev2_drdy
        ) = self.technique_2()
        (
            self.itc3,
            self.mtc3,
            self.dev3_itc,
            self.drdy3,
            self.dev3_drdy
        ) = self.technique_3()
        self.itc_err = self.error()[0]
        self.drdy_err = self.error()[1]

        self.update_table()

        if hasattr(self, "canvas"):
            self.canvas.draw_idle()

    def update_table(self):
        """
        Fill the result table. Refill the table if the Decimal has
        been reset or reactivity unit has been changed.
        """
        if not hasattr(self, 'itc1'):
            return

        self.tree.item(
            "Technique 1",
            values=[
                "Technique 1",
                f'{self.mtc1:.{self.DECIMAL}f}',
                f'{self.itc1:.{self.DECIMAL}f}',
                (
                    f'{self.dev1_itc:.{self.DECIMAL}f}'
                    if self.dev1_itc is not None else "None"
                ),
                (
                    f'{self.drdy1:.{self.DECIMAL}f}'
                    if self.drdy1 is not None else "None"
                ),
                (
                    f'{self.dev1_drdy:.{self.DECIMAL}f}'
                    if self.dev1_drdy is not None else "None"
                )
            ]
        )

        self.tree.item(
            "Technique 2",
            values=[
                "Technique 2",
                f'{self.mtc2:.{self.DECIMAL}f}',
                f'{self.itc2:.{self.DECIMAL}f}',
                (
                    f'{self.dev2_itc:.{self.DECIMAL}f}'
                    if self.dev2_itc is not None else "None"
                ),
                (
                    f'{self.drdy2:.{self.DECIMAL}f}'
                    if self.drdy2 is not None else "None"
                ),
                (
                    f'{self.dev2_drdy:.{self.DECIMAL}f}'
                    if self.dev2_drdy is not None else "None"
                )
            ]
        )

        self.tree.item(
            "Technique 3",
            values=[
                "Technique 3",
                f'{self.mtc3:.{self.DECIMAL}f}',
                f'{self.itc3:.{self.DECIMAL}f}',
                (
                    f'{self.dev3_itc:.{self.DECIMAL}f}'
                    if self.dev3_itc is not None else "None"
                ),
                (
                    f'{self.drdy3:.{self.DECIMAL}f}'
                    if self.drdy3 is not None else "None"
                ),
                (
                    f'{self.dev3_drdy:.{self.DECIMAL}f}'
                    if self.dev3_drdy is not None else "None"
                )
            ]
        )

        itc_res = np.mean([self.itc1, self.itc2, self.itc3])
        drdy_res = (
            np.mean([self.drdy1, self.drdy2, self.drdy3])
            if self.drdy1 is not None else None
        )
        mtc_res = itc_res - self.DTC
        dev_itc = (
            itc_res - self.ITC_computed
            if self.ITC_computed is not None else None
        )
        dev_drdy = (
            drdy_res - self.DRDY_computed
            if self.DRDY_computed is not None
            and drdy_res is not None else None
        )

        self.tree.item(
            "Result",
            values=[
                "Result",
                f'{mtc_res:.{self.DECIMAL}f}', f'{itc_res:.{self.DECIMAL}f}',
                (
                    f'{dev_itc:.{self.DECIMAL}f}'
                    if dev_itc is not None else "None"
                ),
                (
                    f'{drdy_res:.{self.DECIMAL}f}'
                    if drdy_res is not None else "None"
                ),
                (
                    f'{dev_drdy:.{self.DECIMAL}f}'
                    if dev_drdy is not None else "None"
                )
            ]
        )

        self.tree.item(
            "Computed values",
            values=[
                "Computed values",
                f'DTC = {self.DTC:.{self.DECIMAL}f}',
                (
                    f'ITC = {self.ITC_computed:.{self.DECIMAL}f}'
                    if self.ITC_computed is not None else ''
                ),
                (
                    f'MTC = {self.MTC_computed:.{self.DECIMAL}f}'
                    if self.MTC_computed is not None else ''
                ),
                (
                    f'DRDY = {self.DRDY_computed:.{self.DECIMAL}f}'
                    if self.DRDY_computed is not None else ''
                ),
                (
                    f'Boric acid concentration = '
                    f'{self.boric_acid:.{self.DECIMAL}f}'
                    if self.boric_acid is not None else ''
                ),
            ]
        )

        self.tree.item(
            "2sigma_ITC",
            values=[
                "2σ(ITC):",
                f'{self.itc_err:.{self.DECIMAL}f} pcm/°C',
                # "pcm/°C"
            ]
        )

        self.tree.item(
            "2sigma_DRDY",
            values=[
                "2σ(DRDY):",
                (
                    f'{self.drdy_err:.{self.DECIMAL}f} %/(g/cm³)'
                    if self.drdy_err is not None else "None"
                ),
                # "%/(g/cm³)" if self.drdy_err is not None else ""
            ]
        )

        self.tree.item(
            "Units:",
            values=[
                "Units:",
                "pcm/°C",
                "pcm/°C",
                "pcm/°C",
                "%/(g/cm³)",
                "%/(g/cm³)"
            ]
        )

        self.tree.item(
            "Group_position:",
            values=[
                "Group position:",
                f'{self.H1:.{self.DECIMAL_GROUP}f} %'
            ]
        )

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

        self.Time = getattr(self.main_app, "Time", None)
        self.Reactivity = getattr(self.main_app, "Reactivity", None)
        self.Temperature = getattr(self.main_app, "Temperature", None)
        self.Group_position = getattr(self.main_app, "Group_position", None)
        self.times = [
            datetime(1899, 12, 30) + timedelta(days=t) for t in self.Time
        ]

        ax1.plot(self.times, self.Reactivity, 'b-', label="Reactivity, Beff")
        ax1.set_ylabel("Reactivity, Beff", fontsize=PLOT['PLOT_LABEL_SIZE'])

        ax2 = ax1.twinx()
        ax2.plot(self.times, self.Temperature, 'r--', label="Temperature, °C")
        ax2.set_ylabel("Temperature, °C", fontsize=8)

        ax3 = ax1.twinx()
        ax3.plot(
            self.times, self.Group_position,
            'g--', label="Group position, %"
        )
        ax3.spines['right'].set_position(('outward', PLOT['AXIS_SHIFT']))
        ax3.set_ylabel("Group position, %", fontsize=8)

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

        self.toolbar = toolbar
        self.canvas = canvas

        toolbar.pack(side=tk.TOP, fill=tk.X)
        canvas_widget.pack(fill=tk.BOTH, expand=True)
        toolbar.update()
        toolbar.pack(side=tk.TOP, fill=tk.X)
        canvas_widget.pack(fill=tk.BOTH, expand=True)

        canvas.mpl_connect(
            "button_press_event",
            lambda event: self.on_plot_click(event, ax1)
        )
        canvas.mpl_connect(
            "scroll_event",
            lambda event: self.on_plot_scroll(
                event,
                ax1,
                ax2,
                ax3,
                canvas
            )
        )

        plot_obj = {
            "fig": fig,
            "ax1": ax1,
            "ax2": ax2,
            "ax3": ax3,
            "canvas": canvas,
            "toolbar": toolbar,
            "vline_left": None,
            "vline_right": None,

            # Extended cursor elements
            "cursor_vline": ax1.axvline(
                self.times[0], visible=False,
                color="black", linestyle="--",
                linewidth=CURSOR['CURSOR_LINEWIDTH']
            ),
            "cursor_hline1": ax1.axhline(
                self.Reactivity[0], visible=False,
                color="black", linestyle="--",
                linewidth=CURSOR['CURSOR_LINEWIDTH']
            ),
            "cursor_hline2": ax2.axhline(
                self.Temperature[0], visible=False,
                color="black", linestyle="--",
                linewidth=CURSOR['CURSOR_LINEWIDTH']
            ),
            "cursor_hline3": ax3.axhline(
                self.Group_position[0], visible=False,
                color="black", linestyle="--",
                linewidth=CURSOR['CURSOR_LINEWIDTH']
            ),
            "cursor_text": ax1.text(
                0, 0, "",
                visible=False,
                fontsize=CURSOR['CURSOR_TEXT_SIZE'],
                bbox=dict(boxstyle="round", facecolor="white", alpha=0.8)
            ),
            "distance_label": ax1.text(
                0.01, 0.01, "",
                transform=ax1.transAxes,
                fontsize=CURSOR['DISTANCE_LABEL_SIZE'],
                verticalalignment='bottom',
                horizontalalignment='left'
            ),
            "cursor_cid": None
        }

        self.plot_windows.append(plot_obj)
        canvas.draw_idle()

        if self.extended_cursor_enabled:
            cid = canvas.mpl_connect(
                "motion_notify_event",
                lambda event, p=plot_obj: self.on_mouse_move(event, p)
            )
            plot_obj["cursor_cid"] = cid
    def on_plot_scroll(
        self,
        event,
        ax1,
        ax2,
        ax3,
        canvas
    ):
        """
        Zoom the plot along the X axis around the mouse cursor.
        """

        if event.inaxes not in (ax1, ax2, ax3):
            return

        if hasattr(self, "toolbar") and self.toolbar.mode:
            return

        if event.xdata is None:
            return

        current_xlim = ax1.get_xlim()

        left, right = current_xlim
        cursor_x = event.xdata

        if event.button == "up":
            scale = 0.8
        elif event.button == "down":
            scale = 1.25
        else:
            return

        new_left = cursor_x - (cursor_x - left) * scale
        new_right = cursor_x + (right - cursor_x) * scale

        ax1.set_xlim(new_left, new_right)
        ax2.set_xlim(new_left, new_right)
        ax3.set_xlim(new_left, new_right)

        canvas.draw_idle()
    def open_plot_in_new_window(self):
        """Create large plot in the window."""
        win = tk.Toplevel(self.root)
        win.title("ITC Plot – Extended view")
        win.geometry("1200x800")

        frame = tk.Frame(win, bg="white")
        frame.pack(fill=tk.BOTH, expand=True)

        self.create_plot(frame, large=True)

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

    def draw_vertical_line(self, x, button):
        """
        Draw a vertical line on all plots.

        Args:
            x (datetime): X-coordinate.
            button (int): Mouse button (1 = left, 3 = right).
        """
        for plot in self.plot_windows:
            ax = plot["ax1"]

            if button == 1:
                if plot["vline_left"] is not None:
                    plot["vline_left"].remove()
                plot["vline_left"] = ax.axvline(
                    x, color="brown",
                    linestyle="--",
                    linewidth=1.2
                )

            elif button == 3:
                if plot["vline_right"] is not None:
                    plot["vline_right"].remove()
                plot["vline_right"] = ax.axvline(
                    x, color="brown",
                    linestyle="--",
                    linewidth=1.2
                )

            plot["canvas"].draw_idle()

    def get_nearest_index(self, xdata):
        """aux"""
        clicked_time = mdates.num2date(xdata).replace(tzinfo=None)

        nearest_index = min(
            range(len(self.times)),
            key=lambda i: abs(self.times[i] - clicked_time)
        )

        return nearest_index

    def set_first_point(self, idx):

        R = float(self.Reactivity[idx])
        T = float(self.Temperature[idx])
        H = float(self.Group_position[idx])

        self.start_index = idx
        self.point1 = (R, T, H, self.times[idx])

        self.R1_beta = R
        self.R1_percent = self.R1_beta * self.beta
        self.T1 = T
        self.H1 = H

        self.R1_label.config(
            text=f'R₁ = {self.R1_beta:.{self.DECIMAL_REACT}f} Beff'
        )
        self.T1_label.config(
            text=f'T₁ = {self.T1:.{self.DECIMAL_TEMP}f} °C'
        )

    def set_second_point(self, idx):

        R = float(self.Reactivity[idx])
        T = float(self.Temperature[idx])
        H = float(self.Group_position[idx])

        self.finish_index = idx
        self.point2 = (R, T, H, self.times[idx])

        self.R2_beta = R
        self.R2_percent = self.R2_beta * self.beta
        self.T2 = T
        self.H2 = H

        self.delta_R_beta = self.R2_beta - self.R1_beta
        self.delta_R_percent = self.delta_R_beta * self.beta
        self.delta_T = self.T2 - self.T1

        self.R2_label.config(
            text=f'R₂ = {self.R2_beta:.{self.DECIMAL_REACT}f} Beff'
        )
        self.T2_label.config(
            text=f'T₂ = {self.T2:.{self.DECIMAL_TEMP}f} °C'
        )
        self.delta_R_label.config(
            text=f'ΔR = {self.delta_R_beta:.{self.DECIMAL_REACT}f} Beff'
        )
        self.delta_T_label.config(
            text=f'ΔT = {self.delta_T:.{self.DECIMAL_TEMP}f} °C'
        )

        self.Proceed_button.config(state="normal")

    def on_plot_click(self, event, ax1):
        """
        Proceed with mouse clicks on the plot.

        Left click:
            Select start point.

        Right click:
            Select end point.
        """
        if event.inaxes is None:
            return

        for plot in self.plot_windows:
            if plot["ax1"] == ax1 and plot["toolbar"].mode != '':
                return

        idx = self.get_nearest_index(event.xdata)
        time_moment = self.times[idx]
        H = float(self.Group_position[idx])

        if event.button == 1:

            if hasattr(self, "point2"):

                if time_moment >= self.point2[3]:
                    Messages.show("warning", "SECOND_EARLIER")
                    return

                if H != self.H2:
                    Messages.show("warning", "GROUP_MOVEMENT")
                    return

                if (self.finish_index - idx) < self.min_points:
                    if not Messages.show("question", "NARROW_INTERVAL"):
                        return

            self.set_first_point(idx)
            self.draw_vertical_line(time_moment, 1)

            if hasattr(self, "point2"):

                self.delta_R_beta = self.R2_beta - self.R1_beta
                self.delta_R_percent = self.delta_R_beta * self.beta
                self.delta_T = self.T2 - self.T1

                self.delta_R_label.config(
                    text=f'ΔR = {self.delta_R_beta:.{self.DECIMAL_REACT}f} Beff'
                )

                self.delta_T_label.config(
                    text=f'ΔT = {self.delta_T:.{self.DECIMAL_TEMP}f} °C'
                )

        elif event.button == 3:

            if not hasattr(self, "point1"):
                Messages.show("warning", "SELECT_FIRST")
                return

            if time_moment <= self.point1[3]:
                Messages.show("warning", "SECOND_EARLIER")
                return

            if H != self.H1:
                Messages.show("warning", "GROUP_MOVEMENT")
                return

            if (idx - self.start_index) < self.min_points:
                if not Messages.show("question", "NARROW_INTERVAL"):
                    return

            self.set_second_point(idx)
            self.draw_vertical_line(time_moment, 3)

    def technique_1(self):
        """
        Compute ITC using averaged start and end points.
        The technique is thoroughly described in the User guide file.

        Returns:
            Tuple[float, float, Optional[float], Optional[float],
            Optional[float]]:
            ITC, MTC, ITC deviation, DRDY, DRDY deviation
        """
        index_start = self.start_index
        index_finish = self.finish_index

        ITC, d_reactivity, d_temperature = Formulas.itc_two_point(
            self.Reactivity, self.Temperature, index_start, index_finish,
            self.points_amount, self.beta
        )
        MTC = ITC - self.DTC
        deviation_ITC = (
            ITC - self.ITC_computed if self.ITC_computed is not None else None
        )
        DRDY, deviation_DRDY = self.DRDY(ITC)

        return ITC, MTC, deviation_ITC, DRDY, deviation_DRDY

    def technique_2(self):
        """
        Compute ITC using linear regression of reactivity vs temperature.
        The technique is thoroughly described in the User guide file.

        Returns:
            Tuple[float, float, Optional[float], Optional[float],
            Optional[float]]:
            ITC, MTC, ITC deviation, DRDY, DRDY deviation
        """
        index_start = self.start_index
        index_finish = self.finish_index

        ITC = Formulas.itc_linear_fit(
            self.Reactivity, self.Temperature, index_start, index_finish,
            self.beta
        )
        MTC = ITC - self.DTC
        deviation_ITC = (
            ITC - self.ITC_computed if self.ITC_computed is not None else None
        )
        DRDY, deviation_DRDY = self.DRDY(ITC)

        return ITC, MTC, deviation_ITC, DRDY, deviation_DRDY

    def technique_3(self):
        """
        Compute ITC using sliding window regression over time.
        The technique is thoroughly described in the User guide file.

        Returns:
            Tuple[float, float, Optional[float], Optional[float],
            Optional[float]]:
            ITC, MTC, ITC deviation, DRDY, DRDY deviation
        """
        index_start = self.start_index
        index_finish = self.finish_index

        times = mdates.date2num(self.times)
        ITC = Formulas.itc_sliding_window(
            self.Reactivity, self.Temperature, times, index_start,
            index_finish, self.step_points, self.beta
        )
        MTC = ITC - self.DTC
        deviation_ITC = (
            ITC - self.ITC_computed if self.ITC_computed is not None else None
        )
        DRDY, deviation_DRDY = self.DRDY(ITC)

        return ITC, MTC, deviation_ITC, DRDY, deviation_DRDY

    def DRDY(self, ITC):
        """
        Compute DRDY.

        Args:
            - ITC (float): Calculated ITC value.
            - Boric acid concentration (float)
            - DTC(float): Calculated DTC value.

        Returns:
            Tuple[Optional[float], Optional[float]]:
                DRDY value and deviation from reference.
        """
        DRDY = Formulas.drdy_value(ITC, self.DTC, self.DYDT, self.boric_acid)
        deviation_DRDY = None
        if DRDY is not None and self.DRDY_computed is not None:
            deviation_DRDY = DRDY - self.DRDY_computed
        return DRDY, deviation_DRDY

    def error(self):
        """
        Compute the error values for ITC and DRDY.

        Returns:
            Tuple[float, Optional[float]]:
                ITC error and DRDY error.
        """
        ITC_error = Formulas.itc_error(self.delta_R_percent, self.delta_T)
        DRDY_error = Formulas.drdy_error(
            ITC_error, self.DTC, self.boric_acid
        )
        return ITC_error, DRDY_error

    def update_labels(self):
        """Refresh label values after Decimal or unit changes."""
        if self.checkbox_var.get() == 1:
            if hasattr(self, 'R1_percent'):
                self.R1_label.config(
                    text=f'R₁ = {self.R1_percent:.{self.DECIMAL_REACT}f} %'
                )
            if hasattr(self, 'R2_percent'):
                self.R2_label.config(
                    text=f'R₂ = {self.R2_percent:.{self.DECIMAL_REACT}f} %'
                )
            if hasattr(self, 'delta_R_percent'):
                self.delta_R_label.config(
                    text=(
                        f'ΔR = {self.delta_R_percent:.{self.DECIMAL_REACT}f} %'
                    )
                )
        else:
            if hasattr(self, 'R1_beta'):
                self.R1_label.config(
                    text=f'R₁ = {self.R1_beta:.{self.DECIMAL_REACT}f} Beff'
                )
            if hasattr(self, 'R2_beta'):
                self.R2_label.config(
                    text=f'R₂ = {self.R2_beta:.{self.DECIMAL_REACT}f} Beff'
                )
            if hasattr(self, 'delta_R_beta'):
                self.delta_R_label.config(
                    text=(
                        f'ΔR = {self.delta_R_beta:.{self.DECIMAL_REACT}f} Beff'
                    )
                )

        if hasattr(self, 'T1'):
            self.T1_label.config(
                text=f'T₁ = {self.T1:.{self.DECIMAL_TEMP}f} °C'
            )
        if hasattr(self, 'T2'):
            self.T2_label.config(
                text=f'T₂ = {self.T2:.{self.DECIMAL_TEMP}f} °C'
            )
        if hasattr(self, 'delta_T'):
            self.delta_T_label.config(
                text=f'ΔT = {self.delta_T:.{self.DECIMAL_TEMP}f} °C'
            )
