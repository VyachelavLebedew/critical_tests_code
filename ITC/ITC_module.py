import sys
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import font as tkfont
from typing import Any, Optional, List
import pandas as pd

from .ITC_processing import ITC_processing
from Buttons import MainButtons, TestButtons, SmallButtons
from Messages import Messages
from Settings import (
    show_info, FONTS, COLORS, GAPS, ENTRY_WIDTH, RANGES_EXPECTED,
    HEADER_FRAME_HEIGHT, MOUSE_WHEEL_DELTA, NFME_BUTTONS, MINSIZE_RIGHT_FRAME,
    MINSIZE_RIGHT_HEADER, LEFT_CANVAS_WIDTH
)


# ---------------------------------------------------------------------
# New constants (the same in DRDH / ITC / PCR / Imax modules).
# Move them to Settings if needed.
# ---------------------------------------------------------------------

# Ctrl+Z / Ctrl+Y
UNDO_LIMIT = 200                       # how many steps can be reverted
UNDO_KEYSYMS = ("z", "cyrillic_ya")    # works with the Russian layout too
REDO_KEYSYMS = ("y", "cyrillic_en")
UNDO_KEYCODE_WIN = 90                  # Windows virtual key codes of Z and Y
REDO_KEYCODE_WIN = 89
SHIFT_STATE_MASK = 0x1                 # Ctrl+Shift+Z is redo as well

# "Parameters" menu
MENU_PARAMETERS = "Parameters"
MENU_SHOW_NFME = "Show NFME parameters"
MENU_SHOW_COMPUTED = "Show computed parameters"

# "Parameters" windows (NFME / computed)
PARAMS_WINDOW_TITLE_NFME = "NFME parameters"
PARAMS_WINDOW_TITLE_COMPUTED = "Computed parameters"
PARAMS_WINDOW_GEOMETRY = "460x320"
PARAMS_TREE_STYLE = "Params.Treeview"
PARAMS_ROW_PADDING = 6                 # added to the font height of a row
PARAMS_COLUMN_WIDTH = {"parameter": 190, "value": 230}
PARAMS_HEADINGS = {
    "parameter": "Parameter",
    "NFME": "Column(s)",
    "computed": "Value",
}
PARAMS_BUTTON_CLEAR = "Clear"
PARAMS_BUTTON_CLEAR_ALL = "Clear all"
PARAMS_HINT_SELECT = "Click a parameter in the list first."

# Default DYDT of the ITC module
ITC_DYDT_DEFAULT = -1.73

# NFME parameters: attribute(s) of the module that store the data, label
# in the "Required Parameters" column and its default (not obtained) text.
ITC_NFME_PARAMS: dict[str, dict[str, Any]] = {
    'Time': {
        'attr': 'Time',
        'label': 'time_required_label',
        'text': '⏱ Time :1',
    },
    'Temperature': {
        'attr': 'Temperature',
        'label': 'temparature_required_label',
        'text': '⏱ Temperature',
    },
    'Reactivity': {
        'attr': 'Reactivity',
        'label': 'reactivity_required_label',
        'text': '⏱ Reactivity :2',
    },
    'Group position': {
        'attr': 'Group_position',
        'label': 'group_position_required_label',
        'text': '⏱ Group position :1',
    },
}

# Computed parameters (entered by the operator): attribute, entry field,
# label (default / obtained text), default value and the title shown in
# the "computed parameters" window.
ITC_COMPUTED_PARAMS: dict[str, dict[str, Any]] = {
    'DTC': {
        'attr': 'DTC',
        'entry': 'DTC_entry',
        'label': 'DTC_required_label',
        'text': '⏱ DTC',
        'ok': '✓ DTC',
        'default': None,
        'title': 'DTC, ×10³ %/°С',
    },
    'MTC_computed': {
        'attr': 'MTC_computed',
        'entry': 'MTC_entry',
        'label': 'MTC_required_label',
        'text': '⏱ MTC',
        'ok': '✓ MTC',
        'default': None,
        'title': 'MTC, ×10³ %/°С',
    },
    'ITC_computed': {
        'attr': 'ITC_computed',
        'entry': 'ITC_entry',
        'label': 'ITC_required_label',
        'text': '⏱ ITC',
        'ok': '✓ ITC',
        'default': None,
        'title': 'ITC, ×10³ %/°С',
    },
    'DRDY_computed': {
        'attr': 'DRDY_computed',
        'entry': 'DRDY_entry',
        'label': 'DRDY_required_label',
        'text': '⏱ DRDY',
        'ok': '✓ DRDY',
        'default': None,
        'title': 'DRDY, ×10³ %/(g/cm³)',
    },
    'Boric_acid_concentration': {
        'attr': 'boric_acid',
        'entry': 'boric_acid_entry',
        'label': 'boric_acid_required_label',
        'text': '⏱ Boric acid concentration',
        'ok': '✓ Boric acid concentration',
        'default': None,
        'title': 'С(H₃BO₃), g/kg',
    },
    'DYDT': {
        'attr': 'DYDT',
        'entry': 'DYDT_entry',
        'label': 'DYDT_required_label',
        'text': '       DYDT',
        'ok': '✓ DYDT',
        'default': ITC_DYDT_DEFAULT,
        'title': 'DYDT, (g/cm³)/°С',
    },
}


class ITC_module:
    """
    Class allows to obtain all parameters required to compute an ITC.

    Provides the possibility to choose any parameter directly from
    NFME data file and add full set of parameters

    Attributes:
        listed in "__init__"

    Methods:
        create_ITC_window: Create the ITC_module window interface.
        labels: Create and locate all labels and entry fields.
        buttons: Create all buttons in the ITC_module interface.
        combobox: Create a combobox to select one of the parameters required.
        create_menu: Create the top menu bar for ITC_module window.
        show_parameters: Window with the NFME / computed parameters
        (clickable rows, Clear / Clear all).
        clear_parameters: Clear chosen (or all) NFME / computed parameters.
        refresh_ui: Redraw buttons, labels and entries from the state.
        undo / redo: Ctrl+Z / Ctrl+Y.
        start_ITC: Launch ITC computation process.
        get_parameter: Obtain NFME parameter via buttons.
        get_entry: Obtain a computed parameter via entry field.
        get_button_name: Bind NFME file and the button pressed.
        reset_parameters: Auxiliary method to clear some attributes.
        reset_entry: Auxiliary method to clear an entry field and set focus.
        back: Return to main window and reset parameters.
        create_NFME_buttons_frame: Create the NFME buttons field.
        _update_right_scrollregion: Update scrollregion when right frame
        changes size.
    """

    def __init__(self, root, main_app: Any) -> None:
        """Initialize ITC module attributes.

        Args:
            root (tk.Widget): Parent Tkinter widget.
            main_app (Any): Main application instance providing data
            and settings.

        Attributes:
            root (tk.Widget): Parent Tkinter widget.
            main_app (Any): Reference to main application instance.
            df (pd.DataFrame): Loaded data from main application.
            ITC_frame (Optional[tk.Frame]): Main frame of the ITC module.
            menu_bar (Optional[tk.Menu]): Top menu bar for ITC window.
            DTC (Optional[float]): Value for DTC parameter.
            ITC_computed (Optional[float]): Computed ITC value.
            MTC_computed (Optional[float]): Computed MTC value.
            DRDY_computed (Optional[float]): Computed DRDY value.
            boric_acid (Optional[float]): Boric acid concentration.
            DYDT (float): DYDT value, default -1.73.
            Temperature (Optional[pd.Series]): Temperature (data series).
            Reactivity (Optional[pd.Series]): Reactivity (data series).
            Time (Optional[pd.Series]): Time (data series).
            Group_position (Optional[pd.Series]): Group position (data series).
            selected_columns (List[str]): Columns selected by user for
            processing.
            NFME_parameters (List[str]): Selected NFME parameters.
            computed_parameters (List[str]): Selected computed parameters.
        """
        self.root: tk.Widget = root
        self.main_app: Any = main_app
        self.root.iconbitmap("Icons/ITC_icon.ico")
        self.df: pd.DataFrame = self.main_app.df
        self.ITC_frame: Optional[tk.Frame] = None
        self.menu_bar: Optional[tk.Menu] = None
        self.DTC: Optional[float] = None
        self.ITC_computed: Optional[float] = None
        self.MTC_computed: Optional[float] = None
        self.DRDY_computed: Optional[float] = None
        self.boric_acid: Optional[float] = None
        self.DYDT = ITC_DYDT_DEFAULT
        self.Temperature: Optional[pd.Series] = None
        self.Reactivity: Optional[pd.Series] = None
        self.Time: Optional[pd.Series] = None
        self.Group_position: Optional[pd.Series] = None
        self.selected_columns: List[str] = []
        self.NFME_parameters: List[str] = []
        self.computed_parameters: List[str] = []

        # Computed parameters entered by the operator: {name: value}
        self.computed_values: dict[str, float] = {}

        # Undo / redo (snapshots of the whole parameters state)
        self._undo_stack: list[dict[str, Any]] = []
        self._redo_stack: list[dict[str, Any]] = []

        # Open "parameters" windows: {kind: {"window", "tree"}}
        self._param_windows: dict[str, dict[str, Any]] = {}
        self._ctrl_bind_id: Optional[str] = None
        self.selected_column_buttons: dict[str, tk.Button] = {}
        self.parameter_columns: dict[str, List[str]] = {}

    def create_ITC_window(self) -> None:
        """
        Create the ITC_module window interface.

        Initializes the frame, menu, NFME buttons, labels, entries,
        buttons, and combobox as well for selecting and obtainind parameters.
        """
        root_window = self.root.winfo_toplevel()
        root_window.config(menu=None)
        if self.ITC_frame:
            self.ITC_frame.destroy()

        self.ITC_frame = tk.Frame(self.root, bg=COLORS['BACKGROUND_COLOR'])
        self.ITC_frame.place(x=0, y=0, relwidth=1, relheight=1)
        self.root.title('ITC')
        self.create_menu()
        self.create_NFME_buttons_frame()
        self.labels()
        self.buttons()
        self.combobox()
        self.ITC_frame.update_idletasks()

        # Restore the state into the freshly created widgets (the
        # window is re-created when returning from ITC_processing)
        self.refresh_ui(sync_entries=True)
        self.bind_undo_redo()

    def labels(self) -> None:
        """
        Create and locate all labels and entry fields in the right frame.

        Includes labels for required parameters and additional parameters.
        """
        self.time_required_label = tk.Label(
            self.right_frame, text='⏱ Time :1',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.time_required_label.grid(
            row=1, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )
        self.temparature_required_label = tk.Label(
            self.right_frame, text='⏱ Temperature',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.temparature_required_label.grid(
            row=2, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )
        self.reactivity_required_label = tk.Label(
            self.right_frame, text='⏱ Reactivity :2',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.reactivity_required_label.grid(
            row=3, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )
        self.group_position_required_label = tk.Label(
            self.right_frame, text='⏱ Group position :1',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.group_position_required_label.grid(
            row=4, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )
        self.DTC_required_label = tk.Label(
            self.right_frame, text='⏱ DTC',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
            )
        self.DTC_required_label.grid(
            row=5, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )
        self.MTC_required_label = tk.Label(
            self.right_frame, text='⏱ MTC',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.MTC_required_label.grid(
            row=1, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )
        self.ITC_required_label = tk.Label(
            self.right_frame, text='⏱ ITC',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.ITC_required_label.grid(
            row=2, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )
        self.DRDY_required_label = tk.Label(
            self.right_frame, text='⏱ DRDY',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.DRDY_required_label.grid(
            row=3, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )
        self.boric_acid_required_label = tk.Label(
            self.right_frame, text='⏱ Boric acid concentration',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.boric_acid_required_label.grid(
            row=4, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )
        self.DYDT_required_label = tk.Label(
            self.right_frame, text='       DYDT',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.DYDT_required_label.grid(
            row=5, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )
        self.splitter_label_1 = tk.Label(
            self.right_frame, text='Enter the computed values:',
            font=FONTS['SPLITTER_FONT'], bg=COLORS['BACKGROUND_COLOR']
            ).grid(
                row=6, column=0, columnspan=2, sticky="w"
                )

        self.DTC_label = tk.Label(
            self.right_frame, text='DTC, ×10³ %/°С:',
            font=FONTS['INFO_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
            ).grid(row=7, column=0, sticky="w")
        self.DTC_entry = ttk.Entry(
            self.right_frame, font=FONTS['DATA_FONT'], width=ENTRY_WIDTH
        )
        self.DTC_entry.grid(
            row=7, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            sticky="e"
        )
        self.DTC_entry.focus_set()
        self.DTC_entry.bind(
            '<Return>', lambda event: self.get_entry(self.DTC_entry, 'DTC')
        )

        self.MTC_label = tk.Label(
            self.right_frame,
            text='MTC, ×10³ %/°С:',
            font=FONTS['INFO_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
            ).grid(row=8, column=0, sticky="w")
        self.MTC_entry = ttk.Entry(
            self.right_frame, font=FONTS['DATA_FONT'], width=ENTRY_WIDTH
        )
        self.MTC_entry.grid(
            row=8, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            sticky="e"
        )
        self.MTC_entry.bind(
            '<Return>',
            lambda event: self.get_entry(self.MTC_entry, 'MTC_computed')
        )

        self.ITC_label = tk.Label(
            self.right_frame,
            text='ITC, ×10³ %/°С:',
            font=FONTS['INFO_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
            ).grid(row=9, column=0, sticky="w")
        self.ITC_entry = ttk.Entry(
            self.right_frame, font=FONTS['DATA_FONT'], width=ENTRY_WIDTH
        )
        self.ITC_entry.grid(
            row=9, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            sticky="e"
        )
        self.ITC_entry.bind(
            '<Return>',
            lambda event: self.get_entry(self.ITC_entry, 'ITC_computed')
        )
        self.DRDY_label = tk.Label(
            self.right_frame,
            text='DRDY, ×10³ %/(g/cm³):',
            font=FONTS['INFO_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
            ).grid(row=10, column=0, sticky="w")
        self.DRDY_entry = ttk.Entry(
            self.right_frame, font=FONTS['DATA_FONT'], width=ENTRY_WIDTH
        )
        self.DRDY_entry.grid(
            row=10, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            sticky="e"
        )
        self.DRDY_entry.bind(
            '<Return>',
            lambda event: self.get_entry(self.DRDY_entry, 'DRDY_computed')
        )
        self.boric_acid_label = tk.Label(
            self.right_frame,
            text='С(H₃BO₃)*, g/kg:',
            font=FONTS['INFO_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
            ).grid(row=11, column=0, sticky="w")
        self.boric_acid_entry = ttk.Entry(
            self.right_frame, font=FONTS['DATA_FONT'], width=ENTRY_WIDTH
        )
        self.boric_acid_entry.grid(
            row=11, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            sticky="e"
        )
        self.boric_acid_entry.bind(
            '<Return>',
            lambda event: self.get_entry(
                self.boric_acid_entry, 'Boric_acid_concentration'
            )
        )
        self.DYDT_label = tk.Label(
            self.right_frame,
            text='DYDT, (g/cm³)/°С:',
            font=FONTS['INFO_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
        ).grid(row=12, column=0, sticky="w")
        self.DYDT_entry = ttk.Entry(
            self.right_frame, font=FONTS['DATA_FONT'], width=ENTRY_WIDTH
        )
        self.DYDT_entry.grid(
            row=12, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            sticky="e"
        )
        self.DYDT_entry.insert(0, str(ITC_DYDT_DEFAULT))
        self.DYDT_entry.bind(
            '<Return>', lambda event: self.get_entry(self.DYDT_entry, 'DYDT')
        )

        self.splitter_label_2 = tk.Label(
            self.right_frame,
            text=(
                '* - experimental critical boric acid '
                'concentration is expected'
            ),
            font=FONTS['SPLITTER_FONT'], bg=COLORS['BACKGROUND_COLOR'],
            justify="left", anchor="w"
        ).grid(row=13, column=0, columnspan=2, sticky="w")

    def buttons(self) -> None:
        """
        Create buttons for obtaining parameters and program buttons.

        Includes buttons for DTC, MTC, ITC, DRDY, boric acid, DYDT,
        START button, BACK button, INFO button and NFME parameters
        buttons as well.
        """
        self.get_DTC_button = TestButtons(
              self.right_frame,
              text='Get the DTC',
              command=lambda: self.get_entry(self.DTC_entry, 'DTC'),
        )
        self.get_DTC_button.grid(
            row=7, column=1,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'],
            sticky="w"
        )
        self.get_MTC_computed_button = TestButtons(
              self.right_frame,
              text='Get the MTC',
              command=lambda: self.get_entry(self.MTC_entry, 'MTC_computed'),
        )
        self.get_MTC_computed_button.grid(
            row=8, column=1,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'],
            sticky="w"
        )
        self.get_ITC_computed_button = TestButtons(
              self.right_frame,
              text='Get the ITC',
              command=lambda: self.get_entry(self.ITC_entry, 'ITC_computed'),
        )
        self.get_ITC_computed_button.grid(
            row=9, column=1,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'],
            sticky="w"
        )
        self.get_DRDY_computed_button = TestButtons(
              self.right_frame,
              text='Get the DRDY',
              command=lambda: self.get_entry(self.DRDY_entry, 'DRDY_computed'),
        )
        self.get_DRDY_computed_button.grid(
            row=10, column=1,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'],
            sticky="w"
        )
        self.get_boric_acid_button = TestButtons(
              self.right_frame,
              text='Get the С(H₃BO₃)',
              command=lambda: self.get_entry(
                  self.boric_acid_entry, 'Boric_acid_concentration'
                ),
        )
        self.get_boric_acid_button.grid(
            row=11, column=1,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'],
            sticky="w"
        )
        self.get_DYDT_button = TestButtons(
              self.right_frame,
              text='Get the DYDT',
              command=lambda: self.get_entry(self.DYDT_entry, 'DYDT'),
        )
        self.get_DYDT_button.grid(
            row=12, column=1,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'],
            sticky="w"
        )
        self.get_parameter_button = TestButtons(
              self.right_frame,
              text='Get a parameter',
              command=self.get_parameter,
        )
        self.get_parameter_button.grid(
            row=14, column=0,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'],
            sticky="w"
        )
        self.START_button = TestButtons(
              self.right_frame,
              text='START',
              command=self.start_ITC,
        )
        self.START_button.grid(
            row=15, column=0,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'],
            sticky="w"
        )
        self.BACK_button = MainButtons(
              self.right_frame,
              text='<< BACK',
              command=lambda: self.back(self.ITC_frame),
        )
        self.BACK_button.grid(
            row=15, column=1,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'],
            sticky="w"
        )
        self.INFO_button = MainButtons(
              self.right_frame,
              text='User guide',
              command=lambda: show_info(self.root, "ITC/info_module.txt"),
        )
        self.INFO_button.grid(
            row=16, column=1,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'],
            sticky="w"
        )

    def combobox(self) -> None:
        """
        Create a combobox to select one of the parameters required
        directly for NFME file via buttons.
        """
        self.selected_param: tk.StringVar = tk.StringVar(value="Not selected")
        self.parameter_combobox = ttk.Combobox(
            self.right_frame,
            textvariable=self.selected_param,
            values=[
                "Not selected",
                "Time",
                "Temperature",
                "Reactivity",
                "Group position"
                ],
            state="readonly",
            width=20,
            font=FONTS['TEXT_FONT']
        )
        self.parameter_combobox.grid(
            row=14, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            sticky="w"
        )

    def create_menu(self) -> None:
        """
        Create the top menu bar for ITC_module window.

        Menu includes:
            - Parameters (show NFME / computed parameters)
            - INFO
        """
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)

        parameters_menu = tk.Menu(self.menu_bar, tearoff=1)
        self.menu_bar.add_cascade(label=MENU_PARAMETERS, menu=parameters_menu)

        parameters_menu.add_command(
            label=MENU_SHOW_NFME,
            font=FONTS['DATA_FONT'],
            command=lambda: self.show_parameters("NFME")
        )
        parameters_menu.add_command(
            label=MENU_SHOW_COMPUTED,
            font=FONTS['DATA_FONT'],
            command=lambda: self.show_parameters("computed")
        )

        info = tk.Menu(self.menu_bar, tearoff=1)
        self.menu_bar.add_cascade(label="INFO", menu=info)

        info.add_command(
            label="INFO",
            font=FONTS['DATA_FONT'],
            command=lambda: show_info(self.root, "ITC/info_module.txt")
        )

    def start_ITC(self) -> None:
        """
        Launch ITC computation process.

        Checks that required parameters are set; if missing, shows a warning.
        Initializes ITC_processing window.
        """
        missing_parameters = []

        if self.Time is None:
            missing_parameters.append("Time")
        if self.Temperature is None:
            missing_parameters.append("Temperature")
        if self.Reactivity is None:
            missing_parameters.append("Reactivity")
        if self.Group_position is None:
            missing_parameters.append("Group position")
        if self.DTC is None:
            missing_parameters.append("DTC")

        if missing_parameters:
            if len(missing_parameters) == 1:
                Messages.show(
                    "warning", "MISSING_PARAMS",
                    param=missing_parameters[0], test='ITC'
                )
            else:
                params = "\n".join(f"• {p}" for p in missing_parameters)
                Messages.show(
                    "warning", "MISSING_PARAMS",
                    params=params, test='ITC'
                )
            return
        # Shortcuts and parameter windows must not touch the state while
        # the processing window is open
        self.unbind_undo_redo()
        self.close_parameter_windows()

        self.ITC_processing_interface = ITC_processing(self.ITC_frame, self)
        self.ITC_processing_interface.create_ITC_processing_window()

    def get_parameter(self) -> None:
        """
        Obtain NFME parameter via buttons.

        Check whether the parameter complies with the requirements.
        Updates corresponding attribute and UI label.
        """
        PARAMETER_RULES: dict[str, dict[str, Any]] = {
            "Time": {
                "columns": 1,
                "range": RANGES_EXPECTED['TIME_RANGE'],
                "allow_exp": False,
                "attr": "Time",
            },
            "Reactivity": {
                "columns": 2,
                "range": RANGES_EXPECTED['REACTIVITY_RANGE'],
                "allow_exp": False,
                "attr": "Reactivity",
            },
            "Group position": {
                "columns": 1,
                "range": RANGES_EXPECTED['GROUP_POSITION_RANGE'],
                "allow_exp": False,
                "attr": "Group_position",
            },
            "Temperature": {
                "columns": None,
                "range": RANGES_EXPECTED['TEMPERATURE_RANGE'],
                "allow_exp": False,
                "attr": "Temperature",
            }
        }

        selected_param: str = self.selected_param.get()

        if selected_param == "Not selected":
            Messages.show("warning", "PARAM_NOT_SELECTED")
            return

        if not self.selected_columns:
            Messages.show("warning", "NO_COLUMNS")
            return

        rules = PARAMETER_RULES[selected_param]

        if rules["columns"] is not None:
            if len(self.selected_columns) > rules["columns"]:
                response = Messages.show(
                    "question",
                    "COLUMNS_COUNT",
                    param=selected_param,
                    expected=rules["columns"],
                    selected=len(self.selected_columns)
                    )
                if not response:
                    self.clear_selected_column_buttons()
                    return

        data: pd.DataFrame = self.df[self.selected_columns]

        min_val, max_val = rules["range"]
        allow_exp = rules["allow_exp"]

        for col in data.columns:
            series = data[col]

            for raw_value in series:
                s = str(raw_value).strip()
                if ('e' in s.lower()) and not allow_exp:
                    response = Messages.show(
                        "question",
                        "EXPONENTIAL_FORMAT",
                        col=col,
                        example=s
                        )

                    if not response:
                        self.clear_selected_column_buttons()
                        return
                    break

                try:
                    float(s)
                except ValueError:
                    try:
                        float(s.replace(',', '.'))
                    except ValueError:
                        Messages.show("error",
                                      "DATA_FORMAT",
                                      col=col,
                                      value=s
                                      )
                        self.clear_selected_column_buttons()
                        return

            invalid_values = series[~series.between(min_val, max_val)]
            if not invalid_values.empty:
                example_value = invalid_values.iloc[0]
                response = Messages.show(
                    "question",
                    "OUT_OF_RANGE",
                    example=example_value,
                    col=col
                    )
                if not response:
                    self.clear_selected_column_buttons()
                    return

        result: pd.Series = (
            data.mean(axis=1) if len(data.columns) > 1
            else data.iloc[:, 0]
        )

        self._push_undo()
        setattr(self, rules["attr"], result)

        # Remember which NFME columns were assigned to this parameter. If
        # the parameter was already obtained, its old columns are released.
        self.parameter_columns[selected_param] = list(self.selected_columns)
        if selected_param not in self.NFME_parameters:
            self.NFME_parameters.append(selected_param)

        self.selected_columns.clear()
        self.refresh_ui()

    def get_entry(self, entry, value_name: str) -> None:
        """
        Obtain a computed parameter via entry field.

        Args:
            entry (ttk.Entry): Entry widget contains user input value.
            value_name (str): Name of the parameter ('DTC', 'MTC_computed',
                              'ITC_computed', 'Boric_acid_concentration',
                              'DRDY_computed', or 'DYDT').

        Check whether the parameter complies with the requirements.
        Updates corresponding attribute and UI label.
        """
        VALUES_RULES: dict[str, dict[str, Any]] = {
            "DTC": {
                "attr": "DTC",
                "label": lambda self: self.DTC_required_label,
                "label_text": "✓ DTC",
                "sign": "negative"
            },
            "MTC_computed": {
                "attr": "MTC_computed",
                "label": lambda self: self.MTC_required_label,
                "label_text": "✓ MTC",
                "sign": "negative"
            },
            "ITC_computed": {
                "attr": "ITC_computed",
                "label": lambda self: self.ITC_required_label,
                "label_text": "✓ ITC",
                "sign": "negative"
            },
            "Boric_acid_concentration": {
                "attr": "boric_acid",
                "label": lambda self: self.boric_acid_required_label,
                "label_text": "✓ Boric acid concentration",
                "sign": "positive"
            },
            "DRDY_computed": {
                "attr": "DRDY_computed",
                "label": lambda self: self.DRDY_required_label,
                "label_text": "✓ DRDY",
                "sign": "positive"
            },
            "DYDT": {
                "attr": "DYDT",
                "label": lambda self: self.DYDT_required_label,
                "label_text": "✓ DYDT",
                "sign": "nonzero"
                }
        }
        rules: dict[str, Any] = VALUES_RULES[value_name]
        value: str = entry.get().strip().replace(',', '.')
        try:
            numeric_value: float = float(value)
        except Exception as e:
            Messages.show(
                "error", "VALUE_ERROR",
                value_name=value_name,
                error=e
                )
            self.reset_entry(entry)
            return

        if rules["sign"] == "positive" and numeric_value < 0:
            Messages.show(
                "error", "VALUE_POSTIVE",
                value=value_name,
                sign='positive'
                )
            self.reset_entry(entry)
            return

        if rules["sign"] == "negative" and numeric_value > 0:
            Messages.show(
                "error", "VALUE_POSTIVE",
                value=value_name,
                sign='negatve'
                )
            self.reset_entry(entry)
            return

        if rules["sign"] == "nonzero" and numeric_value == 0:
            Messages.show(
                "error", "VALUE_POSTIVE",
                value=value_name,
                sign='nonzero'
                )
            self.reset_entry(entry)
            return

        if self.computed_values.get(value_name) != numeric_value:
            self._push_undo()
        self._set_computed(value_name, numeric_value)
        self.refresh_ui()

    def get_button_name(self, button_name: str) -> None:
        """
        Toggle selection of an NFME data column.

        Selected columns remain visually pressed until the parameter
        is assigned or the selection is cleared.
        """
        locked = {
            col for cols in self.parameter_columns.values() for col in cols
        }
        if button_name in locked:
            return

        self._push_undo()
        if button_name in self.selected_columns:
            self.selected_columns.remove(button_name)
        else:
            self.selected_columns.append(button_name)
        self.refresh_ui()

    def clear_selected_column_buttons(self) -> None:
        """
        Reset the selection of NFME column buttons.

        Only touches columns picked but not yet assigned to a parameter
        (self.selected_columns); buttons locked to a parameter stay as
        they are.
        """
        if self.selected_columns:
            self._push_undo()
            self.selected_columns.clear()
        self.refresh_ui()

    def reset_parameters(self, *args: str) -> None:
        """
        Auxiliary method aimes at reset either NFME or computed parameters
        in cases "BACK" or "clear" some parameters.

        Args:
            *args (str): 'NFME' to reset required parameters, 'computed'
                         to reset computed data. Both may be given at once.
        """
        if 'NFME' in args:
            self.Temperature = None
            self.Reactivity = None
            self.Time = None
            self.Group_position = None
        if 'computed' in args:
            self.DTC = None
            self.ITC_computed = None
            self.MTC_computed = None
            self.DRDY_computed = None
            self.boric_acid = None
            self.DYDT = ITC_DYDT_DEFAULT

    def reset_entry(self, *args) -> None:
        """
        Auxiliary method to clear an entry field and set focus.

        Args:
            entries (ttk.Entry): Entry widget to reset.
        """
        for entry in args:
            entry.delete(0, tk.END)
            entry.focus_set()

    def back(self, window: tk.Widget) -> None:
        """
        Close ITC_module and return to main application window.

        Resets parameters.

        Args:
            window (tk.Widget): ITC frame to destroy.
        """
        self.unbind_undo_redo()
        self.close_parameter_windows()

        self.reset_parameters('NFME', 'computed')
        self.selected_columns = []
        self.parameter_columns.clear()
        self.NFME_parameters = []
        self.computed_parameters = []
        self.computed_values = {}
        self._undo_stack.clear()
        self._redo_stack.clear()

        if hasattr(self, 'root_window'):
            self.root_window.config(menu=None)

        self.menu_bar.destroy()
        self.menu_bar = None

        window.destroy()
        self.root.title('3 in 1 v2')

        if hasattr(self, 'root_window'):
            self.root_window.update_idletasks()

    # ------------------------------------------------------------------
    # "Parameters" windows
    # ------------------------------------------------------------------
    def _parameter_rows(self, kind: str) -> list[tuple[str, str, str]]:
        """Rows (iid, parameter, columns / value) of a parameters window."""
        if kind == "NFME":
            return [
                (key, key, ", ".join(self.parameter_columns.get(key, [])))
                for key in self.NFME_parameters
            ]
        return [
            (name, ITC_COMPUTED_PARAMS[name]["title"], str(self.computed_values[name]))
            for name in self.computed_parameters
            if name in self.computed_values
        ]

    def show_parameters(self, kind: str) -> None:
        """
        Open a window with the parameters already obtained.

        Args:
            kind (str): 'NFME' - parameter and the NFME column(s) assigned
                to it; 'computed' - parameter and the value entered.

        Rows are clickable. "Clear" removes the clicked parameter(s),
        "Clear all" removes all of them. The window follows every change
        of the state (including Ctrl+Z / Ctrl+Y).
        """
        opened = self._param_windows.get(kind)
        if opened and opened["window"].winfo_exists():
            opened["window"].deiconify()
            opened["window"].lift()
            self._refresh_param_window(kind)
            return

        is_nfme = kind == "NFME"
        window = tk.Toplevel(self.root)
        window.title(
            PARAMS_WINDOW_TITLE_NFME if is_nfme
            else PARAMS_WINDOW_TITLE_COMPUTED
        )
        window.geometry(PARAMS_WINDOW_GEOMETRY)
        window.config(bg=COLORS['BACKGROUND_COLOR'])

        style = ttk.Style(window)
        row_font = tkfont.Font(root=window, font=FONTS['DATA_FONT'])
        style.configure(
            PARAMS_TREE_STYLE,
            font=FONTS['DATA_FONT'],
            rowheight=row_font.metrics("linespace") + PARAMS_ROW_PADDING
        )
        style.configure(f"{PARAMS_TREE_STYLE}.Heading", font=FONTS['DATA_FONT'])

        frame = tk.Frame(window, bg=COLORS['BACKGROUND_COLOR'])
        frame.pack(
            fill=tk.BOTH, expand=True,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'],
        )
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        tree = ttk.Treeview(
            frame,
            columns=("parameter", "value"),
            show="headings",
            selectmode="extended",
            style=PARAMS_TREE_STYLE
        )
        tree.heading("parameter", text=PARAMS_HEADINGS["parameter"])
        tree.heading("value", text=PARAMS_HEADINGS[kind])
        tree.column(
            "parameter", width=PARAMS_COLUMN_WIDTH["parameter"], anchor="w"
        )
        tree.column(
            "value", width=PARAMS_COLUMN_WIDTH["value"], anchor="w"
        )

        scrollbar = ttk.Scrollbar(
            frame, orient="vertical", command=tree.yview
        )
        tree.configure(yscrollcommand=scrollbar.set)
        tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        button_frame = tk.Frame(window, bg=COLORS['BACKGROUND_COLOR'])
        button_frame.pack(pady=5)

        def clear_clicked() -> None:
            chosen = list(tree.selection())
            if not chosen:
                messagebox.showinfo(
                    window.title(), PARAMS_HINT_SELECT, parent=window
                )
                return
            self.clear_parameters(kind, chosen)

        SmallButtons(
            button_frame,
            text=PARAMS_BUTTON_CLEAR,
            command=clear_clicked,
        ).grid(
            row=0, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_0_5']
        )
        SmallButtons(
            button_frame,
            text=PARAMS_BUTTON_CLEAR_ALL,
            command=lambda: self.clear_parameters(kind),
        ).grid(
            row=0, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_0_5']
        )

        window.bind("<Control-KeyPress>", self._on_ctrl_key)
        window.protocol(
            "WM_DELETE_WINDOW", lambda: self._close_param_window(kind)
        )

        self._param_windows[kind] = {"window": window, "tree": tree}
        self._refresh_param_window(kind)

    def _refresh_param_window(self, kind: str) -> None:
        """Redraw the rows of an open parameters window."""
        opened = self._param_windows.get(kind)
        if not opened:
            return
        if not opened["window"].winfo_exists():
            self._param_windows.pop(kind, None)
            return

        tree: ttk.Treeview = opened["tree"]
        previously_selected = set(tree.selection())
        tree.delete(*tree.get_children())
        for iid, parameter, value in self._parameter_rows(kind):
            tree.insert("", "end", iid=iid, values=(parameter, value))

        keep = [i for i in previously_selected if tree.exists(i)]
        if keep:
            tree.selection_set(keep)

    def _close_param_window(self, kind: str) -> None:
        opened = self._param_windows.pop(kind, None)
        if opened and opened["window"].winfo_exists():
            opened["window"].destroy()

    def close_parameter_windows(self) -> None:
        """Close all open "parameters" windows."""
        for kind in list(self._param_windows):
            self._close_param_window(kind)

    # ------------------------------------------------------------------
    # Clearing
    # ------------------------------------------------------------------
    def clear_parameters(
            self,
            kind: str,
            keys: Optional[list[str]] = None
    ) -> None:
        """
        Clear obtained parameters and roll the UI back.

        Args:
            kind (str): 'NFME' or 'computed'.
            keys (list[str], optional): Parameters to clear; all of this
                kind if omitted.

        NFME: the columns of the parameter are released (buttons are
        unpressed and enabled again) and the label is reset.
        Computed: the value is dropped, the entry gets its default again.
        """
        existing = (
            list(self.NFME_parameters) if kind == "NFME"
            else list(self.computed_parameters)
        )
        keys = existing if keys is None else [k for k in keys if k in existing]
        if not keys:
            return

        self._push_undo()
        for key in keys:
            if kind == "NFME":
                self._remove_nfme_parameter(key)
            else:
                self._remove_computed_parameter(key)
        self.refresh_ui(sync_entries=True)

    @staticmethod
    def _copy_value(value: Any) -> Any:
        return list(value) if isinstance(value, list) else value

    @staticmethod
    def _nfme_attrs(key: str) -> dict[str, Any]:
        """Attributes of the module that store an NFME parameter."""
        info = ITC_NFME_PARAMS[key]
        attrs: dict[str, Any] = {info["attr"]: None}
        attrs.update(info.get("extra_attrs", {}))
        return attrs

    def _remove_nfme_parameter(self, key: str) -> None:
        self.parameter_columns.pop(key, None)
        if key in ITC_NFME_PARAMS:
            for attr, default in self._nfme_attrs(key).items():
                setattr(self, attr, self._copy_value(default))
            if ITC_NFME_PARAMS[key].get("headers") and hasattr(self, "column_headers"):
                self.column_headers.pop(ITC_NFME_PARAMS[key]["attr"], None)
        if key in self.NFME_parameters:
            self.NFME_parameters.remove(key)

    def _set_computed(self, name: str, value: float) -> None:
        setattr(self, ITC_COMPUTED_PARAMS[name]["attr"], value)
        self.computed_values[name] = value
        if name not in self.computed_parameters:
            self.computed_parameters.append(name)

    def _remove_computed_parameter(self, name: str) -> None:
        self.computed_values.pop(name, None)
        # The value goes back to its default
        setattr(self, ITC_COMPUTED_PARAMS[name]["attr"], ITC_COMPUTED_PARAMS[name]["default"])
        if name in self.computed_parameters:
            self.computed_parameters.remove(name)

    # ------------------------------------------------------------------
    # State: snapshot / undo / redo
    # ------------------------------------------------------------------
    def _snapshot(self) -> dict[str, Any]:
        """Copy of everything the operator has chosen so far."""
        params = {
            key: (
                list(cols),
                {
                    attr: self._copy_value(getattr(self, attr, None))
                    for attr in self._nfme_attrs(key)
                }
            )
            for key, cols in self.parameter_columns.items()
            if key in ITC_NFME_PARAMS
        }
        return {
            "order": list(self.NFME_parameters),
            "params": params,
            "computed": dict(self.computed_values),
            "selected": list(self.selected_columns),
        }

    def _reset_state_attrs(self) -> None:
        """Put all attributes of the parameters to the initial values."""
        for key in ITC_NFME_PARAMS:
            for attr, default in self._nfme_attrs(key).items():
                setattr(self, attr, self._copy_value(default))
        if hasattr(self, "column_headers"):
            self.column_headers = {}
        for info in ITC_COMPUTED_PARAMS.values():
            setattr(self, info["attr"], info["default"])

    def _apply_state(self, state: dict[str, Any]) -> None:
        """Make the given snapshot current and redraw the UI."""
        self._reset_state_attrs()
        self.parameter_columns.clear()
        self.NFME_parameters = []
        self.computed_values = {}
        self.computed_parameters = []

        for key in state["order"]:
            cols, values = state["params"][key]
            for attr, value in values.items():
                setattr(self, attr, self._copy_value(value))
            self.parameter_columns[key] = list(cols)
            if ITC_NFME_PARAMS[key].get("headers"):
                self.column_headers[ITC_NFME_PARAMS[key]["attr"]] = list(cols)
            self.NFME_parameters.append(key)

        for name, value in state["computed"].items():
            self._set_computed(name, value)

        self.selected_columns = list(state["selected"])
        self.refresh_ui(sync_entries=True)

    def _push_undo(self) -> None:
        """Remember the current state; call right BEFORE changing it."""
        self._undo_stack.append(self._snapshot())
        if len(self._undo_stack) > UNDO_LIMIT:
            del self._undo_stack[0]
        self._redo_stack.clear()

    def undo(self) -> None:
        """Ctrl+Z: revert the last change of the parameters."""
        if not self._undo_stack:
            return
        self._redo_stack.append(self._snapshot())
        self._apply_state(self._undo_stack.pop())

    def redo(self) -> None:
        """Ctrl+Y: return the change reverted by Ctrl+Z."""
        if not self._redo_stack:
            return
        self._undo_stack.append(self._snapshot())
        self._apply_state(self._redo_stack.pop())

    def _on_ctrl_key(self, event: tk.Event) -> Optional[str]:
        """
        Ctrl+Z / Ctrl+Y (Ctrl+Shift+Z too) for any keyboard layout.

        On Windows the virtual key code is checked, so the shortcuts also
        work with the Russian layout.
        """
        key = (event.keysym or "").lower()
        code = event.keycode if sys.platform.startswith("win") else None
        shift = bool(event.state & SHIFT_STATE_MASK)

        if key in UNDO_KEYSYMS or code == UNDO_KEYCODE_WIN:
            self.redo() if shift else self.undo()
            return "break"
        if key in REDO_KEYSYMS or code == REDO_KEYCODE_WIN:
            self.redo()
            return "break"
        return None

    def bind_undo_redo(self) -> None:
        """Bind Ctrl+Z / Ctrl+Y to the window of the module."""
        self.unbind_undo_redo()
        self._ctrl_bind_id = self.root.winfo_toplevel().bind(
            "<Control-KeyPress>", self._on_ctrl_key, add="+"
        )

    def unbind_undo_redo(self) -> None:
        """Release the shortcuts (processing window, leaving the module)."""
        if self._ctrl_bind_id:
            try:
                self.root.winfo_toplevel().unbind(
                    "<Control-KeyPress>", self._ctrl_bind_id
                )
            except tk.TclError:
                pass
            self._ctrl_bind_id = None

    # ------------------------------------------------------------------
    # Drawing the state
    # ------------------------------------------------------------------
    def _nfme_label(self, param: str) -> Optional[tk.Label]:
        """Label of an NFME parameter."""
        return getattr(self, ITC_NFME_PARAMS[param]["label"], None)

    def refresh_ui(self, sync_entries: bool = False) -> None:
        """
        Redraw the widgets from the stored state.

        - column buttons: locked (pressed, disabled) when assigned to a
          parameter, pressed when just selected, raised otherwise;
        - labels of required parameters and of computed parameters;
        - open "parameters" windows;
        - entry fields (only if sync_entries, so that a value the operator
          is typing is not overwritten by ordinary actions).
        """
        if self.ITC_frame is None or not self.ITC_frame.winfo_exists():
            return

        locked = {
            col for cols in self.parameter_columns.values() for col in cols
        }
        for column_name, button in self.selected_column_buttons.items():
            if not button.winfo_exists():
                continue
            if column_name in locked:
                button.config(state=tk.DISABLED, relief=tk.SUNKEN, bd=2)
            elif column_name in self.selected_columns:
                button.config(state=tk.NORMAL, relief=tk.SUNKEN, bd=2)
            else:
                button.config(state=tk.NORMAL, relief=tk.RAISED, bd=2)

        for param, info in ITC_NFME_PARAMS.items():
            label = self._nfme_label(param)
            if label is None:
                continue
            text = info["text"]
            if param in self.parameter_columns:
                text = "✓" + text[1:]
            label.config(text=text)

        for name, info in ITC_COMPUTED_PARAMS.items():
            done = name in self.computed_values
            getattr(self, info["label"]).config(
                text=info["ok"] if done else info["text"]
            )
            if sync_entries:
                entry = getattr(self, info["entry"])
                entry.delete(0, tk.END)
                if done:
                    entry.insert(0, str(self.computed_values[name]))
                elif info["default"] is not None:
                    entry.insert(0, str(info["default"]))

        for kind in list(self._param_windows):
            self._refresh_param_window(kind)

    def create_NFME_buttons_frame(self) -> None:
        """
        Create the NFME buttons field in the ITC frame.

        Adds scrollbars for both fields.
        """
        self.selected_column_buttons.clear()
        self.header_frame = tk.Frame(
            self.ITC_frame,
            bg=COLORS['BACKGROUND_COLOR'],
            height=HEADER_FRAME_HEIGHT,
            width=self.root.winfo_width()
        )
        self.header_frame.grid(
            row=0,
            column=0,
            columnspan=3,
            sticky="ew"
        )

        self.header_frame.grid_propagate(False)
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.header_label = tk.Label(
            self.header_frame,
            text="ITC Module",
            font=FONTS['TITLE_FONT'],
            bg=COLORS['BACKGROUND_COLOR'],
            anchor='center'
        )
        self.header_label.grid(row=0, column=0)

        self.left_header = tk.Frame(
            self.ITC_frame,
            bg=COLORS['BACKGROUND_COLOR'],
            highlightbackground="black",
            highlightthickness=1
            )
        self.left_header.grid(
            row=1, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_5_0'],
            sticky="ew"
        )

        self.parameters_label = tk.Label(
            self.left_header, text='Parameters:',
            font=FONTS['PARAMETER_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.parameters_label.grid(
            row=0, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_0_5'],
            sticky="ew"
        )
        self.left_header.grid_columnconfigure(0, weight=1)

        self.right_header = tk.Frame(
            self.ITC_frame,
            bg=COLORS['BACKGROUND_COLOR']
            )
        self.right_header.grid(
            row=1, column=1, columnspan=2,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_5_0'],
            sticky='w'
        )
        self.right_header.grid_columnconfigure(1, minsize=MINSIZE_RIGHT_HEADER)

        self.required_parameters_label = tk.Label(
            self.right_header,
            text='Required Parameters:',
            font=FONTS['PARAMETER_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
            )
        self.required_parameters_label.grid(
            row=0, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10_30'],
            sticky="w"
            )

        self.additional_parameters_label = tk.Label(
            self.right_header,
            text='Additional Parameters:',
            font=FONTS['PARAMETER_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
            )
        self.additional_parameters_label.grid(
            row=0, column=1, sticky="e"
            )

        self.left_canvas = tk.Canvas(
            self.ITC_frame,
            bg=COLORS['PARAMETERS_BACKGROUND_COLOR'],
            highlightthickness=0,
            width=LEFT_CANVAS_WIDTH
        )

        self.right_canvas = tk.Canvas(
            self.ITC_frame,
            bg=COLORS['BACKGROUND_COLOR'],
            highlightthickness=0
        )

        right_scrollbar = ttk.Scrollbar(
            self.ITC_frame,
            orient="vertical",
            command=self.right_canvas.yview
            )

        right_scrollbar.grid(row=2, column=2, rowspan=12, sticky="ns")

        self.left_canvas.grid(
            row=2, column=0, rowspan=12,
            padx=GAPS['GAPS_X']['PAD_X_10_15'],
            pady=GAPS['GAPS_Y']['PAD_Y_0_5'],
            sticky="ns"
        )
        self.right_canvas.grid(
            row=2, column=1, rowspan=12,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_10_5'],
            sticky="nsew"
        )

        scrollbar = ttk.Scrollbar(
            self.ITC_frame,
            orient="vertical",
            command=self.left_canvas.yview
        )
        scrollbar.grid(
            row=2, column=0, rowspan=12,
            padx=GAPS['GAPS_X']['PAD_X_0_10'],
            sticky="nse"
        )

        buttons_frame = tk.Frame(
            self.left_canvas,
            bg=COLORS['PARAMETERS_BACKGROUND_COLOR']
        )

        self.right_frame = tk.Frame(
            self.right_canvas,
            bg=COLORS['BACKGROUND_COLOR']
        )
        self.right_frame.grid_columnconfigure(0, minsize=MINSIZE_RIGHT_FRAME)

        # Bind the canvas with the frame and with scrollbar
        self.right_canvas.create_window(
            (0, 0),
            window=self.right_frame,
            anchor="nw"
        )

        def _update_right_scrollregion(event) -> None:
            """Update scrollregion when right frame changes size"""
            self.right_canvas.configure(
                scrollregion=self.right_canvas.bbox("all")
            )

        self.right_frame.bind("<Configure>", _update_right_scrollregion)

        self.right_canvas.configure(yscrollcommand=right_scrollbar.set)
        self.left_canvas.create_window(
            (0, 0),
            window=buttons_frame,
            anchor="nw",
            width=NFME_BUTTONS['BUTTONS_FRAME_WIDTH']
        )
        self.left_canvas.configure(yscrollcommand=scrollbar.set)

        columns = self.main_app.df.columns.tolist()
        for column_name in columns:
            button = tk.Button(
                buttons_frame,
                text=column_name,
                command=lambda name=column_name: self.get_button_name(name),
                width=NFME_BUTTONS['BUTTONS_WIDTH'],
                font=FONTS['DATA_FONT']
            )

            self.selected_column_buttons[column_name] = button

            button.pack(
                padx=GAPS['GAPS_X']['PAD_X_5'],
                pady=GAPS['GAPS_Y']['PAD_Y_2']
            )

        # Updating the scrolling area after adding all buttons
        buttons_frame.update_idletasks()
        self.left_canvas.config(scrollregion=self.left_canvas.bbox("all"))

        self.ITC_frame.grid_rowconfigure(2, weight=1)
        self.ITC_frame.grid_columnconfigure(0, weight=0)
        self.ITC_frame.grid_columnconfigure(1, weight=1)

        def _on_mousewheel_left(event) -> None:
            self.left_canvas.yview_scroll(
                int(-1 * (event.delta / MOUSE_WHEEL_DELTA)), "units"
            )

        def _on_mousewheel_right(event) -> None:
            self.right_canvas.yview_scroll(
                int(-1 * (event.delta / MOUSE_WHEEL_DELTA)), "units"
            )

        self.left_canvas.bind(
            "<Enter>",
            lambda e: self.root.bind_all("<MouseWheel>", _on_mousewheel_left)
        )
        self.left_canvas.bind(
            "<Leave>",
            lambda e: self.root.unbind_all("<MouseWheel>")
        )

        self.right_canvas.bind(
            "<Enter>",
            lambda e: self.root.bind_all("<MouseWheel>", _on_mousewheel_right)
        )
        self.right_canvas.bind(
            "<Leave>",
            lambda e: self.root.unbind_all("<MouseWheel>")
        )