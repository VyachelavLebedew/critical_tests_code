import sys
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from tkinter import font as tkfont
from typing import Any, Optional, List
import pandas as pd

from .DRDH_processing import DRDH_processing
from Buttons import MainButtons, TestButtons, SmallButtons
from Messages import Messages
from Settings import (
    show_info, FONTS, COLORS, GAPS, ENTRY_WIDTH, RANGES_EXPECTED,
    HEADER_FRAME_HEIGHT, MOUSE_WHEEL_DELTA, NFME_BUTTONS, MINSIZE_RIGHT_FRAME,
    MINSIZE_RIGHT_HEADER, LEFT_CANVAS_WIDTH, GROUP_MAP
)


# Combobox item that adds an auxiliary (not used in the DRDH computation)
# parameter, which is only shown on the DRDH_processing plot.
ADD_PARAMETER = "Add new parameter"

# Prefix of auxiliary parameters in the NFME_parameters list
EXTRA_PREFIX = "Added: "

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

_SUBSCRIPTS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

# NFME parameters: attribute of DRDH_module that stores the data, label in
# the "Required Parameters" column and its default (not obtained) text.
DRDH_NFME_PARAMS: dict[str, dict[str, str]] = {
    "Time": {
        "attr": "Time",
        "label": "time_required_label",
        "text": "⏱ Time :1",
    },
    "Reactivity": {
        "attr": "Reactivity",
        "label": "reactivity_required_label",
        "text": "⏱ Reactivity :2",
    },
    "Boric acid concentration": {
        "attr": "boric_acid_NFME",
        "label": "boric_acid_NFME_required_label",
        "text": "⏱ Boric acid :2",
    },
}
for _n in range(12, 0, -1):
    DRDH_NFME_PARAMS[f"{_n} Group position"] = {
        "attr": f"H{_n}_position",
        "label": f"H{_n}_position_required_label",
        "text": f"⏱ H{str(_n).translate(_SUBSCRIPTS)} :1",
    }

# Computed parameters (entered by the operator): attribute, entry field,
# label (default / obtained text), default value of the entry and the title
# shown in the "computed parameters" window.
DRDH_COMPUTED_PARAMS: dict[str, dict[str, Any]] = {
    "Group_length": {
        "attr": "Group_length",
        "entry": "Group_length_entry",
        "label": "Group_length_required_label",
        "text": "  Group length",
        "ok": "✓ Group length",
        "default": 388.73,
        "title": "Group length, cm",
    },
    "Overlap": {
        "attr": "overlap",
        "entry": "overlap_entry",
        "label": "overlap_required_label",
        "text": "  Overlap",
        "ok": "✓ Overlap",
        "default": 50.0,
        "title": "Overlap, %",
    },
    "DRDC": {
        "attr": "DRDC",
        "entry": "DRDC_entry",
        "label": "DRDC_required_label",
        "text": "⏱ DRDC",
        "ok": "✓ DRDC",
        "default": None,
        "title": "DRDC, %/(g/kg)",
    },
    "boric_acid_start": {
        "attr": "boric_acid_start",
        "entry": "boric_acid_start_entry",
        "label": "boric_acid_start_required_label",
        "text": "⏱ С(H₃BO₃) initial",
        "ok": "✓ Boric acid concentration (initial)",
        "default": None,
        "title": "С(H₃BO₃) initial, g/kg",
    },
    "boric_acid_finish": {
        "attr": "boric_acid_finish",
        "entry": "boric_acid_finish_entry",
        "label": "boric_acid_finish_required_label",
        "text": "⏱ С(H₃BO₃) final",
        "ok": "✓ Boric acid concentration (final)",
        "default": None,
        "title": "С(H₃BO₃) final, g/kg",
    },
}


class DRDH_module:
    """
    Class allows to obtain all parameters required to compute DRDH.

    Provides the possibility to choose any parameter directly from
    NFME data file and add full set of parameters

    Attributes:
        listed in "__init__"

    Methods:
        create_DRDH_window: Create the DRDH_module window interface.
        labels: Create and locate all labels and entry fields.
        buttons: Create all buttons in the DRDH_module interface.
        combobox: Create a combobox to select one of the parameters required.
        create_menu: Create the top menu bar for DRDH_module window.
        show_parameters: Window with the NFME / computed parameters
        (clickable rows, Clear / Clear all).
        clear_parameters: Clear chosen (or all) NFME / computed parameters.
        refresh_ui: Redraw buttons, labels and entries from the state.
        undo / redo: Ctrl+Z / Ctrl+Y.
        start_DRDH: Launch DRDH computation process.
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
        """Initialize DRDH module attributes.

        Args:
            root (tk.Widget): Parent Tkinter widget.
            main_app (Any): Main application instance providing data
            and settings.

        Attributes:
            root (tk.Widget): Parent Tkinter widget.
            main_app (Any): Reference to main application instance.
            df (pd.DataFrame): Loaded data from main application.
            DRDH_frame (Optional[tk.Frame]): Main frame of the DRDH module.
            menu_bar (Optional[tk.Menu]): Top menu bar for DRDH window.
            DRDC (Optional[float]): Value for DTC parameter.
            boric_acid_start (Optional[float]): Initial boric acid
            concentration.
            boric_acid_finish (Optional[float]): Boric acid concentration
            arter the groups movement.
            Reactivity (Optional[pd.Series]): Reactivity (data series).
            Time (Optional[pd.Series]): Time (data series).
            1-12(10) Group_position (Optional[pd.Series]): Group positions
            (data series).
            selected_columns (List[str]): Columns selected by user for
            processing.
            NFME_parameters (List[str]): Selected NFME parameters.
            computed_parameters (List[str]): Selected computed parameters.
        """
        self.root: tk.Widget = root
        self.main_app: Any = main_app
        self.root.iconbitmap("Icons/DRDH_icon.ico")
        self.df: pd.DataFrame = self.main_app.df
        self.DRDH_frame: Optional[tk.Frame] = None
        self.menu_bar: Optional[tk.Menu] = None
        self.Group_length: float = 388.73
        self.overlap: float = 50.0
        self.DRDC: Optional[float] = None
        self.boric_acid_start: Optional[float] = None
        self.boric_acid_finish: Optional[float] = None
        self.Reactivity: Optional[pd.Series] = None
        self.Time: Optional[pd.Series] = None
        self.boric_acid_NFME: Optional[pd.Series] = None

        # Movement type of the control groups: 'Withdrawal', 'Insertion'
        # or None while the user has not specified it. Passed on to
        # DRDH_processing; the determination itself does not need it.
        self.movement_type: Optional[str] = None

        self.groups_count: int = 12
        self.H12_position: Optional[pd.Series] = None
        self.H11_position: Optional[pd.Series] = None
        self.H10_position: Optional[pd.Series] = None
        self.H9_position: Optional[pd.Series] = None
        self.H8_position: Optional[pd.Series] = None
        self.H7_position: Optional[pd.Series] = None
        self.H6_position: Optional[pd.Series] = None
        self.H5_position: Optional[pd.Series] = None
        self.H4_position: Optional[pd.Series] = None
        self.H3_position: Optional[pd.Series] = None
        self.H2_position: Optional[pd.Series] = None
        self.H1_position: Optional[pd.Series] = None
        self.selected_columns: List[str] = []
        self.NFME_parameters: List[str] = []
        self.computed_parameters: List[str] = []
        self.selected_column_buttons: dict[str, tk.Button] = {}
        self.parameter_columns: dict[str, list[str]] = {}

        # Computed parameters entered by the operator: {name: value}
        self.computed_values: dict[str, float] = {}

        # Undo / redo (snapshots of the whole parameters state)
        self._undo_stack: list[dict[str, Any]] = []
        self._redo_stack: list[dict[str, Any]] = []

        # Open "parameters" windows: {kind: {"window", "tree"}}
        self._param_windows: dict[str, dict[str, Any]] = {}
        self._ctrl_bind_id: Optional[str] = None

        # Auxiliary parameters: {"name": str, "values": pd.Series,
        # "columns": list[str]}. They do not take part in the computation,
        # DRDH_processing draws each of them on its own scale.
        self.extra_parameters: list[dict[str, Any]] = []

    def create_DRDH_window(self) -> None:
        """
        Create the DRDH_module window interface.

        Initializes the frame, menu, NFME buttons, labels, entries,
        buttons, and combobox as well for selecting and obtainind parameters.

        The window is also re-created when the operator returns from
        DRDH_processing (BACK), so everything chosen before is restored
        from the stored state: pressed buttons, labels, entered values,
        groups mode and movement type.
        """
        root_window = self.root.winfo_toplevel()
        root_window.config(menu=None)
        if self.DRDH_frame:
            self.DRDH_frame.destroy()

        self.DRDH_frame = tk.Frame(self.root, bg=COLORS['BACKGROUND_COLOR'])
        self.DRDH_frame.place(x=0, y=0, relwidth=1, relheight=1)
        self.root.title('DRDH')
        self.create_menu()
        self.create_NFME_buttons_frame()
        self.labels()
        self.buttons()
        self.combobox()
        self.DRDH_frame.update_idletasks()

        # Restore the state into the freshly created widgets
        self.apply_groups_mode()
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

        self.reactivity_required_label = tk.Label(
            self.right_frame, text='⏱ Reactivity :2',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.reactivity_required_label.grid(
            row=2, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )

        self.H12_position_required_label = tk.Label(
            self.right_frame, text='⏱ H₁₂ :1',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.H12_position_required_label.grid(
            row=3, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )

        self.groups_mode_label = tk.Label(
            self.right_frame,
            text='12 groups mode',
            font=FONTS['INFO_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
        )
        self.groups_mode_label.grid(
            row=4, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )

        self.Group_length_required_label = tk.Label(
            self.right_frame, text='  Group length',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.Group_length_required_label.grid(
            row=1, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )

        self.overlap_required_label = tk.Label(
            self.right_frame, text='  Overlap',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.overlap_required_label.grid(
            row=2, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )

        self.boric_acid_NFME_required_label = tk.Label(
            self.right_frame, text='⏱ Boric acid :2',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.boric_acid_NFME_required_label.grid(
            row=3, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )

        self.DRDC_required_label = tk.Label(
            self.right_frame, text='⏱ DRDC',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.DRDC_required_label.grid(
            row=4, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )

        self.boric_acid_start_required_label = tk.Label(
            self.right_frame, text='⏱ С(H₃BO₃) initial',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.boric_acid_start_required_label.grid(
            row=5, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )

        self.boric_acid_finish_required_label = tk.Label(
            self.right_frame, text='⏱ С(H₃BO₃) final',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.boric_acid_finish_required_label.grid(
            row=6, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )

        self.H11_position_required_label = tk.Label(
            self.right_frame, text='⏱ H₁₁ :1',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.H11_position_required_label.grid(
            row=7, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )

        self.H10_position_required_label = tk.Label(
            self.right_frame, text='⏱ H₁₀ :1',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.H10_position_required_label.grid(
            row=7, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="e"
        )

        self.H9_position_required_label = tk.Label(
            self.right_frame, text='⏱ H₉ :1',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.H9_position_required_label.grid(
            row=8, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )

        self.H8_position_required_label = tk.Label(
            self.right_frame, text='⏱ H₈ :1',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.H8_position_required_label.grid(
            row=8, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="e"
        )

        self.H7_position_required_label = tk.Label(
            self.right_frame, text='⏱ H₇ :1',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.H7_position_required_label.grid(
            row=9, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )

        self.H6_position_required_label = tk.Label(
            self.right_frame, text='⏱ H₆ :1',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.H6_position_required_label.grid(
            row=9, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="e"
        )

        self.H5_position_required_label = tk.Label(
            self.right_frame, text='⏱ H₅ :1',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.H5_position_required_label.grid(
            row=10, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )

        self.H4_position_required_label = tk.Label(
            self.right_frame, text='⏱ H₄ :1',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.H4_position_required_label.grid(
            row=10, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="e"
        )

        self.H3_position_required_label = tk.Label(
            self.right_frame, text='⏱ H₃ :1',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.H3_position_required_label.grid(
            row=11, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )

        self.H2_position_required_label = tk.Label(
            self.right_frame, text='⏱ H₂ :1',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.H2_position_required_label.grid(
            row=11, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="e"
        )

        self.H1_position_required_label = tk.Label(
            self.right_frame, text='⏱ H₁ :1',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.H1_position_required_label.grid(
            row=12, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )

        self.splitter_label_1 = tk.Label(
            self.right_frame,
            text='Enter the computed and experimental values:',
            font=FONTS['SPLITTER_FONT'], bg=COLORS['BACKGROUND_COLOR']
            ).grid(
                row=13, column=0, columnspan=2, sticky="w"
                )

        self.Group_length_label = tk.Label(
            self.right_frame, text='Group length, cm:',
            font=FONTS['INFO_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
            ).grid(row=15, column=0, sticky="w")
        self.Group_length_entry = ttk.Entry(
            self.right_frame, font=FONTS['DATA_FONT'], width=ENTRY_WIDTH
        )
        self.Group_length_entry.grid(
            row=15, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            sticky="e"
        )
        self.Group_length_entry.insert(0, "388.73")
        self.Group_length_entry.focus_set()
        self.Group_length_entry.bind(
            '<Return>', lambda event: self.get_entry(
                self.Group_length_entry, 'Group_length'
            )
        )

        self.overlap_label = tk.Label(
            self.right_frame, text='Overlap, %:',
            font=FONTS['INFO_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
            ).grid(row=16, column=0, sticky="w")
        self.overlap_entry = ttk.Entry(
            self.right_frame, font=FONTS['DATA_FONT'], width=ENTRY_WIDTH
        )
        self.overlap_entry.grid(
            row=16, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            sticky="e"
        )
        self.overlap_entry.insert(0, "50.0")
        self.overlap_entry.bind(
            '<Return>', lambda event: self.get_entry(
                self.overlap_entry, 'Overlap'
            )
        )

        self.DRDC_label = tk.Label(
            self.right_frame, text='DRDC, %/(g/kg):',
            font=FONTS['INFO_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
            ).grid(row=17, column=0, sticky="w")
        self.DRDC_entry = ttk.Entry(
            self.right_frame, font=FONTS['DATA_FONT'], width=ENTRY_WIDTH
        )
        self.DRDC_entry.grid(
            row=17, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            sticky="e"
        )
        self.DRDC_entry.bind(
            '<Return>', lambda event: self.get_entry(self.DRDC_entry, 'DRDC')
        )

        self.boric_acid_start_label = tk.Label(
            self.right_frame,
            text='С(H₃BO₃) (initial), g/kg:',
            font=FONTS['INFO_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
            ).grid(row=18, column=0, sticky="w")
        self.boric_acid_start_entry = ttk.Entry(
            self.right_frame, font=FONTS['DATA_FONT'], width=ENTRY_WIDTH
        )
        self.boric_acid_start_entry.grid(
            row=18, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            sticky="e"
        )
        self.boric_acid_start_entry.bind(
            '<Return>',
            lambda event: self.get_entry(
                self.boric_acid_start_entry, 'boric_acid_start'
            )
        )

        self.boric_acid_finish_label = tk.Label(
            self.right_frame,
            text='С(H₃BO₃) (final), g/kg:',
            font=FONTS['INFO_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
            ).grid(row=19, column=0, sticky="w")
        self.boric_acid_finish_entry = ttk.Entry(
            self.right_frame, font=FONTS['DATA_FONT'], width=ENTRY_WIDTH
        )
        self.boric_acid_finish_entry.grid(
            row=19, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            sticky="e"
        )
        self.boric_acid_finish_entry.bind(
            '<Return>',
            lambda event: self.get_entry(
                self.boric_acid_finish_entry, 'boric_acid_finish'
            )
        )

    def buttons(self) -> None:
        """
        Create buttons for obtaining parameters and program buttons.

        Includes buttons for DRDC, boric acid concentrations values, START
        button, BACK button, INFO button and NFME parameters buttons as well.
        """
        self.get_Group_length_button = TestButtons(
              self.right_frame,
              text='Get group length',
              command=lambda: self.get_entry(
                  self.Group_length_entry, 'Group_length'
                ),
        )
        self.get_Group_length_button.grid(
            row=15, column=1,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'],
            sticky="w"
        )

        self.get_overlap_button = TestButtons(
              self.right_frame,
              text='Get overlap value',
              command=lambda: self.get_entry(
                  self.overlap_entry, 'Overlap'
                ),
        )
        self.get_overlap_button.grid(
            row=16, column=1,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'],
            sticky="w"
        )

        self.get_DRDC_button = TestButtons(
              self.right_frame,
              text='Get the DRDC',
              command=lambda: self.get_entry(self.DRDC_entry, 'DRDC'),
        )
        self.get_DRDC_button.grid(
            row=17, column=1,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'],
            sticky="w"
        )

        self.boric_acid_start_button = TestButtons(
              self.right_frame,
              text='Get С(H₃BO₃) (initial)',
              command=lambda: self.get_entry(
                  self.boric_acid_start_entry, 'boric_acid_start'
                ),
        )
        self.boric_acid_start_button.grid(
            row=18, column=1,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'],
            sticky="w"
        )

        self.boric_acid_finish_button = TestButtons(
              self.right_frame,
              text='Get С(H₃BO₃) (final)',
              command=lambda: self.get_entry(
                  self.boric_acid_finish_entry, 'boric_acid_finish'
                ),
        )
        self.boric_acid_finish_button.grid(
            row=19, column=1,
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
              command=self.start_DRDH,
        )
        self.START_button.grid(
            row=20, column=0,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'],
            sticky="w"
        )
        self.BACK_button = MainButtons(
              self.right_frame,
              text='<< BACK',
              command=lambda: self.back(self.DRDH_frame),
        )
        self.BACK_button.grid(
            row=20, column=1,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'],
            sticky="w"
        )
        self.INFO_button = MainButtons(
              self.right_frame,
              text='User guide',
              command=lambda: show_info(self.root, "DRDH/info_module.txt"),
        )
        self.INFO_button.grid(
            row=21, column=1,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'],
            sticky="w"
        )

    def _combobox_values(self) -> list[str]:
        """Items of the parameter combobox for the current groups mode."""
        values = [
            "Not selected",
            "Time",
            "Reactivity",
            "Boric acid concentration",
            "12 Group position",
            "11 Group position",
            "10 Group position",
            "9 Group position",
            "8 Group position",
            "7 Group position",
            "6 Group position",
            "5 Group position",
            "4 Group position",
            "3 Group position",
            "2 Group position",
            "1 Group position",
            ADD_PARAMETER,
        ]
        if self.groups_count == 10:
            values = [
                v for v in values
                if v not in ("12 Group position", "11 Group position")
            ]
        return values

    def combobox(self) -> None:
        """
        Create a combobox to select one of the parameters required
        directly for NFME file via buttons.
        """
        self.selected_param: tk.StringVar = tk.StringVar(value="Not selected")
        self.parameter_combobox = ttk.Combobox(
            self.right_frame,
            textvariable=self.selected_param,
            values=self._combobox_values(),
            state="readonly",
            width=20,
            font=FONTS['TEXT_FONT']
        )
        self.parameter_combobox.grid(
            row=14, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            sticky="w"
        )

    def set_movement_type(self) -> None:
        """Store the movement type chosen in the menu."""
        self.movement_type = self.movement_type_var.get() or None

    def clear_movement_type(self) -> None:
        """Drop the movement type: it is an optional setting."""
        self.movement_type_var.set("")
        self.movement_type = None

    def switch_groups_amount(self) -> None:
        """Switch between 12 and 10 control groups."""
        self.groups_count = 10 if self.groups_count == 12 else 12
        self.apply_groups_mode()

    def apply_groups_mode(self) -> None:
        """
        Show the current groups mode (12 or 10) in the widgets.

        Called on a switch and every time the window is re-created, since
        the new widgets are always built in the 12 groups mode.
        """
        values = self._combobox_values()
        self.parameter_combobox["values"] = values
        if self.selected_param.get() not in values:
            self.selected_param.set("Not selected")

        if self.groups_count == 10:
            # H12 label binds H10 group (see refresh_ui)
            self.H11_position_required_label.config(text='')
            self.H10_position_required_label.config(text='')
            self.groups_mode_label.config(text="10 groups mode")
        else:
            self.groups_mode_label.config(text="12 groups mode")

        self.refresh_ui()

    def create_menu(self) -> None:
        """
        Create the top menu bar for DRDH_module window.

        Menu includes:
            - Parameters (show NFME parameters, show computed parameters)
            - INFO
            - Mode settings (groups amount, movement type)
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
            command=lambda: show_info(self.root, "DRDH/info_module.txt")
        )

        mode_settings = tk.Menu(self.menu_bar, tearoff=1)
        self.menu_bar.add_cascade(label="Mode settings", menu=mode_settings)

        mode_settings.add_command(
            label="Switch 12 <-> 10",
            font=FONTS['DATA_FONT'],
            command=self.switch_groups_amount
        )

        # Side submenu: opens on hover, like any nested Tk menu
        movement_menu = tk.Menu(mode_settings, tearoff=0)
        mode_settings.add_cascade(
            label="Movement type",
            font=FONTS['DATA_FONT'],
            menu=movement_menu
        )

        # Empty until the user chooses (restored after BACK from processing)
        self.movement_type_var = tk.StringVar(value=self.movement_type or "")

        for option in ("Withdrawal", "Insertion"):
            movement_menu.add_radiobutton(
                label=option,
                font=FONTS['DATA_FONT'],
                value=option,
                variable=self.movement_type_var,
                command=self.set_movement_type
            )

        movement_menu.add_separator()
        movement_menu.add_command(
            label="Not specified",
            font=FONTS['DATA_FONT'],
            command=self.clear_movement_type
        )

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
            (name, DRDH_COMPUTED_PARAMS[name]["title"],
             str(self.computed_values[name]))
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
        """Close all open \"parameters\" windows."""
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

    def _remove_nfme_parameter(self, key: str) -> None:
        self.parameter_columns.pop(key, None)
        if key.startswith(EXTRA_PREFIX):
            extra_name = key[len(EXTRA_PREFIX):]
            self.extra_parameters = [
                p for p in self.extra_parameters if p["name"] != extra_name
            ]
        elif key in DRDH_NFME_PARAMS:
            setattr(self, DRDH_NFME_PARAMS[key]["attr"], None)
        if key in self.NFME_parameters:
            self.NFME_parameters.remove(key)

    def _set_computed(self, name: str, value: float) -> None:
        setattr(self, DRDH_COMPUTED_PARAMS[name]["attr"], value)
        self.computed_values[name] = value
        if name not in self.computed_parameters:
            self.computed_parameters.append(name)

    def _remove_computed_parameter(self, name: str) -> None:
        self.computed_values.pop(name, None)
        # Group length and overlap go back to their defaults
        setattr(
            self, DRDH_COMPUTED_PARAMS[name]["attr"],
            DRDH_COMPUTED_PARAMS[name]["default"]
        )
        if name in self.computed_parameters:
            self.computed_parameters.remove(name)

    # ------------------------------------------------------------------
    # State: snapshot / undo / redo
    # ------------------------------------------------------------------
    def _snapshot(self) -> dict[str, Any]:
        """Copy of everything the operator has chosen so far."""
        params = {
            key: (list(cols), getattr(self, DRDH_NFME_PARAMS[key]["attr"]))
            for key, cols in self.parameter_columns.items()
            if key in DRDH_NFME_PARAMS
        }
        return {
            "order": list(self.NFME_parameters),
            "params": params,
            "extras": [
                dict(p, columns=list(p["columns"]))
                for p in self.extra_parameters
            ],
            "computed": dict(self.computed_values),
            "selected": list(self.selected_columns),
        }

    def _apply_state(self, state: dict[str, Any]) -> None:
        """Make the given snapshot current and redraw the UI."""
        self.reset_parameters('NFME', 'computed')
        self.parameter_columns.clear()
        self.NFME_parameters = []
        self.computed_values = {}
        self.computed_parameters = []

        extras = {p["name"]: p for p in state["extras"]}
        for key in state["order"]:
            if key.startswith(EXTRA_PREFIX):
                extra = extras[key[len(EXTRA_PREFIX):]]
                self.extra_parameters.append(
                    dict(extra, columns=list(extra["columns"]))
                )
                self.parameter_columns[key] = list(extra["columns"])
            else:
                cols, series = state["params"][key]
                setattr(self, DRDH_NFME_PARAMS[key]["attr"], series)
                self.parameter_columns[key] = list(cols)
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
        """Label of an NFME parameter (None if it is not shown)."""
        if self.groups_count == 10:
            if param in ("12 Group position", "11 Group position"):
                return None
            if param == "10 Group position":
                return self.H12_position_required_label
        return getattr(self, DRDH_NFME_PARAMS[param]["label"], None)

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
        if self.DRDH_frame is None or not self.DRDH_frame.winfo_exists():
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

        for param, info in DRDH_NFME_PARAMS.items():
            label = self._nfme_label(param)
            if label is None:
                continue
            text = info["text"]
            if param in self.parameter_columns:
                text = "✓" + text[1:]
            label.config(text=text)

        for name, info in DRDH_COMPUTED_PARAMS.items():
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

    def start_DRDH(self) -> None:
        """
        Launch DRDH computation process.

        Checks that required parameters are set; if missing, shows a warning.
        Checks wheather the parameters comply with the requirements and the order.
        Initializes DRDH_processing window.
        """
        missing_parameters = []

        if self.Time is None:
            missing_parameters.append("Time")
        if self.Reactivity is None:
            missing_parameters.append("Reactivity")
        if self.groups_count == 12:
            if self.H12_position is None:
                missing_parameters.append("12 group position")
        else:
            if self.H10_position is None:
                missing_parameters.append("10 group position")

        if missing_parameters:
            if len(missing_parameters) == 1:
                Messages.show(
                    "warning", "MISSING_PARAMS",
                    param=missing_parameters[0], test='DRDH'
                )
            else:
                params = "\n".join(f"• {p}" for p in missing_parameters)
                Messages.show(
                    "warning", "MISSING_PARAMS",
                    params=params, test='DRDH'
                )
            return

        # Check the groups chosen order
        selected_groups = []

        for num, attr_name in GROUP_MAP.items():
            if getattr(self, attr_name) is not None:
                selected_groups.append(num)

        sorted_groups = sorted(selected_groups)
        expected_range = list(range(min(sorted_groups), max(sorted_groups) + 1))

        if sorted_groups != expected_range:
            groups_str = ", ".join(f"H{g}" for g in sorted(selected_groups, reverse=True))
            Messages.show(
                "warning",
                "GROUP_ORDER_ERROR",
                groups=groups_str
            )
            selected_groups = []
            groups_str = None
            return

        # Shortcuts and parameter windows must not touch the state while
        # the processing window is open
        self.unbind_undo_redo()
        self.close_parameter_windows()

        self.DRDH_processing_interface = DRDH_processing(self.DRDH_frame, self)
        self.DRDH_processing_interface.create_DRDH_processing_window()

    def _parameter_rules(self, param: str) -> tuple[int, tuple]:
        """Expected number of columns and the allowed range of a parameter."""
        if param == "Time":
            return 1, RANGES_EXPECTED['TIME_RANGE']
        if param == "Reactivity":
            return 2, RANGES_EXPECTED['REACTIVITY_RANGE']
        if param == "Boric acid concentration":
            return 2, RANGES_EXPECTED['BORIC_ACID_RANGE']
        return 1, RANGES_EXPECTED['GROUP_POSITION_RANGE']

    def get_parameter(self) -> None:
        """
        Obtain NFME parameter via buttons.

        Check whether the parameter complies with the requirements.
        Updates corresponding attribute and UI (labels, locked buttons).
        """
        selected_param: str = self.selected_param.get()

        if selected_param == "Not selected":
            Messages.show("warning", "PARAM_NOT_SELECTED")
            return

        if not self.selected_columns:
            Messages.show("warning", "NO_COLUMNS")
            return

        if selected_param == ADD_PARAMETER:
            self.add_extra_parameter()
            return

        expected_columns, value_range = self._parameter_rules(selected_param)

        if len(self.selected_columns) > expected_columns:
            response = Messages.show(
                "question",
                "COLUMNS_COUNT",
                param=selected_param,
                expected=expected_columns,
                selected=len(self.selected_columns)
                )
            if not response:
                self.clear_selected_column_buttons()
                return

        data: pd.DataFrame = self.df[self.selected_columns]

        min_val, max_val = value_range
        allow_exp = False

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
        setattr(self, DRDH_NFME_PARAMS[selected_param]["attr"], result)

        # Remember which NFME columns were assigned to this parameter. If
        # the parameter was already obtained, its old columns are released.
        self.parameter_columns[selected_param] = self.selected_columns.copy()
        if selected_param not in self.NFME_parameters:
            self.NFME_parameters.append(selected_param)

        self.selected_columns.clear()
        self.refresh_ui()

    def ask_extra_parameter_name(self) -> Optional[str]:
        """
        Ask the user for the name of a new auxiliary parameter.

        The name is used for the scale and for the legend, so it has to be
        non-empty and unique. Returns None if the dialog is cancelled.
        """
        existing = {p["name"].casefold() for p in self.extra_parameters}
        initial = ""

        while True:
            name = simpledialog.askstring(
                "Add new parameter",
                "Enter the parameter name\n"
                "(it will be shown on its scale and in the legend):",
                initialvalue=initial,
                parent=self.root
            )
            if name is None:
                return None

            name = name.strip()
            if not name:
                messagebox.showwarning(
                    "Add new parameter",
                    "The name must not be empty.",
                    parent=self.root
                )
                continue

            if name.casefold() in existing:
                messagebox.showwarning(
                    "Add new parameter",
                    f"The parameter '{name}' already exists. "
                    "Enter another name.",
                    parent=self.root
                )
                initial = name
                continue

            return name

    def add_extra_parameter(self) -> None:
        """
        Add an auxiliary parameter from the currently selected columns.

        The parameter is not used in the computation: it is only drawn in
        DRDH_processing on its own scale. Any number of them can be added;
        the combobox keeps "Add new parameter" selected for the next one.
        """
        columns = self.selected_columns.copy()
        raw = self.df[columns]

        # Numbers may use a decimal comma
        text = raw.astype(str).apply(
            lambda s: s.str.strip().str.replace(',', '.', regex=False)
        )
        data = text.apply(pd.to_numeric, errors='coerce')
        blank = text.isin(['', 'nan', 'None'])

        bad = data.isna() & ~blank
        if bad.any().any():
            col = next(c for c in columns if bad[c].any())
            value = text[col][bad[col]].iloc[0]
            Messages.show("error", "DATA_FORMAT", col=col, value=value)
            self.clear_selected_column_buttons()
            return

        if data.isna().all().all():
            messagebox.showerror(
                "Add new parameter",
                "The selected columns contain no numeric data.",
                parent=self.root
            )
            self.clear_selected_column_buttons()
            return

        if len(columns) > 1:
            proceed = messagebox.askyesno(
                "Add new parameter",
                f"{len(columns)} columns are selected. Their mean will be "
                "shown as ONE parameter on a single scale.\n\nContinue?",
                parent=self.root
            )
            if not proceed:
                self.clear_selected_column_buttons()
                return

        name = self.ask_extra_parameter_name()
        if name is None:
            # Cancelled: the columns stay selected so it can be repeated
            return

        result: pd.Series = (
            data.mean(axis=1) if len(columns) > 1 else data.iloc[:, 0]
        )

        key = f"{EXTRA_PREFIX}{name}"
        self._push_undo()
        self.extra_parameters.append(
            {"name": name, "values": result, "columns": columns}
        )
        self.parameter_columns[key] = columns
        self.NFME_parameters.append(key)

        # Like for the other parameters, the columns become locked
        self.selected_columns.clear()
        self.refresh_ui()

    def get_entry(self, entry, value_name: str) -> None:
        """
        Obtain a computed parameter via entry field.

        Args:
            entry (ttk.Entry): Entry widget contains user input value.
            value_name (str): Name of the parameter ('DRDC', and
            'Boric_acid_concentrations').

        Check whether the parameter complies with the requirements.
        Updates corresponding attribute and UI label.
        """
        VALUES_RULES: dict[str, dict[str, Any]] = {
            "Overlap": {
                "attr": "overlap",
                "label": lambda self: self.overlap_required_label,
                "label_text": "✓ Overlap",
                "sign": "positive"
            },

            "Group_length": {
                "attr": "Group_length",
                "label": lambda self: self.Group_length_required_label,
                "label_text": "✓ Group length",
                "sign": "positive"
            },
            "DRDC": {
                "attr": "DRDC",
                "label": lambda self: self.DRDC_required_label,
                "label_text": "✓ DRDC",
                "sign": "negative"
            },
            "boric_acid_start": {
                "attr": "boric_acid_start",
                "label": lambda self: self.boric_acid_start_required_label,
                "label_text": "✓ Boric acid concentration (initial)",
                "sign": "positive"
            },
            "boric_acid_finish": {
                "attr": "boric_acid_finish",
                "label": lambda self: self.boric_acid_finish_required_label,
                "label_text": "✓ Boric acid concentration (final)",
                "sign": "positive"
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
            self.Reactivity = None
            self.Time = None
            self.boric_acid_NFME = None
            self.H12_position = None
            self.H11_position = None
            self.H10_position = None
            self.H9_position = None
            self.H8_position = None
            self.H7_position = None
            self.H6_position = None
            self.H5_position = None
            self.H4_position = None
            self.H3_position = None
            self.H2_position = None
            self.H1_position = None
            self.extra_parameters = []
        if 'computed' in args:
            self.DRDC = None
            self.boric_acid_start = None
            self.boric_acid_finish = None
            self.Group_length = DRDH_COMPUTED_PARAMS["Group_length"]["default"]
            self.overlap = DRDH_COMPUTED_PARAMS["Overlap"]["default"]

    def reset_entry(self, entry: ttk.Entry) -> None:
        """
        Auxiliary method to clear an entry field and set focus.

        Args:
            entry (ttk.Entry): Entry widget to reset.
        """
        entry.delete(0, tk.END)
        entry.focus_set()

    def back(self, window: tk.Widget) -> None:
        """
        Close DRDH_module and return to main application window.

        Resets parameters.

        Args:
            window (tk.Widget): DRDH frame to destroy.
        """
        self.unbind_undo_redo()
        self.close_parameter_windows()

        self.reset_parameters('NFME', 'computed')
        self.selected_columns = []
        self.NFME_parameters = []
        self.computed_parameters = []
        self.computed_values = {}
        self.parameter_columns.clear()
        self._undo_stack.clear()
        self._redo_stack.clear()
        self.groups_count = 12
        self.movement_type = None

        if hasattr(self, 'root_window'):
            self.root_window.config(menu=None)

        self.menu_bar.destroy()
        self.menu_bar = None

        window.destroy()
        self.root.title('3 in 1 v2')

        if hasattr(self, 'root_window'):
            self.root_window.update_idletasks()

    def create_NFME_buttons_frame(self) -> None:
        """
        Create the NFME buttons field in the DRDH frame.

        Adds scrollbars for both fields.
        """
        self.selected_column_buttons.clear()
        self.header_frame = tk.Frame(
            self.DRDH_frame,
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
            text="DRDH Module",
            font=FONTS['TITLE_FONT'],
            bg=COLORS['BACKGROUND_COLOR'],
            anchor='center'
        )
        self.header_label.grid(row=0, column=0)

        self.left_header = tk.Frame(
            self.DRDH_frame,
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
            self.DRDH_frame,
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
            self.DRDH_frame,
            bg=COLORS['PARAMETERS_BACKGROUND_COLOR'],
            highlightthickness=0,
            width=LEFT_CANVAS_WIDTH
        )

        self.right_canvas = tk.Canvas(
            self.DRDH_frame,
            bg=COLORS['BACKGROUND_COLOR'],
            highlightthickness=0
        )

        right_scrollbar = ttk.Scrollbar(
            self.DRDH_frame,
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
            self.DRDH_frame,
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
                font=FONTS['DATA_FONT'],
                relief=tk.RAISED,
                bd=2
            )

            self.selected_column_buttons[column_name] = button

            button.pack(
                padx=GAPS['GAPS_X']['PAD_X_5'],
                pady=GAPS['GAPS_Y']['PAD_Y_2']
            )
            button.pack(
                padx=GAPS['GAPS_X']['PAD_X_5'], pady=GAPS['GAPS_Y']['PAD_Y_2']
            )

        # Updating the scrolling area after adding all buttons
        buttons_frame.update_idletasks()
        self.left_canvas.config(scrollregion=self.left_canvas.bbox("all"))

        self.DRDH_frame.grid_rowconfigure(2, weight=1)
        self.DRDH_frame.grid_columnconfigure(0, weight=0)
        self.DRDH_frame.grid_columnconfigure(1, weight=1)

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