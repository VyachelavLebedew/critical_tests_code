import sys
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from tkinter import font as tkfont
from typing import Any, Optional, List
import pandas as pd

from .Imax_processing import Imax_processing
from Buttons import MainButtons, TestButtons, SmallButtons
from Messages import Messages
from Settings import (
    show_info, FONTS, COLORS, GAPS, ENTRY_WIDTH,
    HEADER_FRAME_HEIGHT, MOUSE_WHEEL_DELTA, NFME_BUTTONS,
    MINSIZE_RIGHT_FRAME, MINSIZE_RIGHT_HEADER, LEFT_CANVAS_WIDTH,
    IMAX_BASE_DEFAULT, IMAX_BASE_RANGE
)


# ---------------------------------------------------------------------
# New constants (the same in DRDH / ITC / PCR / Imax modules).
# Move them to Settings if needed.
# ---------------------------------------------------------------------

# Combobox item that adds an auxiliary (not used in the computation)
# parameter, which is only shown on the plot of the processing window.
ADD_PARAMETER = "Add new parameter"
EXTRA_PREFIX = "Added: "       # prefix of auxiliary parameters in the lists
EXTRA_DIALOG_TITLE = "Add new parameter"

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

# NFME parameters: attribute(s) of the module that store the data, label
# in the "Required Parameters" column and its default (not obtained) text.
IMAX_NFME_PARAMS: dict[str, dict[str, Any]] = {
    'Time': {
        'attr': 'Time',
        'label': 'time_required_label',
        'text': '⏱ Time :1',
    },
    'Temperature': {
        'attr': 'Temperature',
        'label': 'temperature_required_label',
        'text': '⏱ Temperature :1+',
    },
    'Current': {
        'attr': 'Current',
        'label': 'current_required_label',
        'text': '⏱ Current :2',
        'extra_attrs': {"Current_columns": []},
    },
}

# Computed parameters (entered by the operator): attribute, entry field,
# label (default / obtained text), default value and the title shown in
# the "computed parameters" window.
IMAX_COMPUTED_PARAMS: dict[str, dict[str, Any]] = {
    'MC': {
        'attr': 'MC',
        'entry': 'MC_entry',
        'label': 'MC_required_label',
        'text': '  MC',
        'ok': '✓ MC',
        'default': None,
        'title': 'MC, MWt/(°C/h)',
    },
    'base': {
        'attr': 'base',
        'entry': 'base_entry',
        'label': 'base_required_label',
        'text': '  Base',
        'ok': '✓ Base',
        'default': IMAX_BASE_DEFAULT,
        'title': 'base, s',
    },
}


class Imax_module:
    """Collect the columns required by the Imax determination."""

    def __init__(self, root: tk.Widget, main_app: Any) -> None:
        self.root = root
        self.main_app = main_app
        self.df: Optional[pd.DataFrame] = self.main_app.df
        self.Imax_frame: Optional[tk.Frame] = None
        self.menu_bar: Optional[tk.Menu] = None

        self.Time: Optional[pd.Series] = None
        self.Temperature: Optional[pd.Series] = None
        self.Current_columns: List[str] = []
        self.Current: Optional[pd.DataFrame] = None

        self.selected_columns: List[str] = []
        self.parameter_columns: dict[str, list[str]] = {}
        self.selected_column_buttons: dict[str, tk.Button] = {}

        # Entered values
        self.MC: Optional[float] = None            # heat capacity, optional
        self.base: int = IMAX_BASE_DEFAULT         # heating-rate window, s
        self.computed_parameters: List[str] = []
        self.NFME_parameters: List[str] = []

        # Computed parameters entered by the operator: {name: value}
        self.computed_values: dict[str, float] = {}

        # Auxiliary parameters (drawn only in the processing window):
        # [{"name", "values" (Series), "columns"}]
        self.extra_parameters: list[dict[str, Any]] = []

        # Undo / redo (snapshots of the whole parameters state)
        self._undo_stack: list[dict[str, Any]] = []
        self._redo_stack: list[dict[str, Any]] = []

        # Open "parameters" windows: {kind: {"window", "tree"}}
        self._param_windows: dict[str, dict[str, Any]] = {}
        self._ctrl_bind_id: Optional[str] = None

    def create_Imax_window(self) -> None:
        if self.df is None or self.df.empty:
            Messages.show('warning', 'NO_FILE')
            return

        root_window = self.root.winfo_toplevel()
        root_window.config(menu=None)
        if self.Imax_frame is not None:
            self.Imax_frame.destroy()

        self.Imax_frame = tk.Frame(
            self.root, bg=COLORS['BACKGROUND_COLOR']
        )
        self.Imax_frame.place(x=0, y=0, relwidth=1, relheight=1)
        root_window.title('Imax')

        self.create_menu()
        self.create_parameter_frames()
        self.labels()
        self.buttons()
        self.combobox()
        self.Imax_frame.update_idletasks()

        # Restore the state into the freshly created widgets (the
        # window is re-created when returning from Imax_processing)
        self.refresh_ui(sync_entries=True)
        self.bind_undo_redo()

    def create_menu(self) -> None:
        root_window = self.root.winfo_toplevel()
        root_window.config(menu=None)
        self.menu_bar = tk.Menu(root_window)
        root_window.config(menu=self.menu_bar)

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
        self.menu_bar.add_cascade(label='INFO', menu=info)
        info.add_command(
            label='INFO', font=FONTS['DATA_FONT'],
            command=lambda: show_info(self.root, 'Imax/info_module.txt')
        )

    def create_parameter_frames(self) -> None:
        self.selected_column_buttons.clear()
        frame = self.Imax_frame
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=0)
        frame.grid_columnconfigure(1, weight=1)

        header = tk.Frame(frame, bg=COLORS['BACKGROUND_COLOR'], height=HEADER_FRAME_HEIGHT)
        header.grid(row=0, column=0, columnspan=3, sticky='ew')
        header.grid_propagate(False)
        header.grid_columnconfigure(0, weight=1)
        tk.Label(
            header, text='Imax Module', font=FONTS['TITLE_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
        ).grid(row=0, column=0)

        left_header = tk.Frame(
            frame, bg=COLORS['BACKGROUND_COLOR'],
            highlightbackground='black', highlightthickness=1
        )
        left_header.grid(
            row=1, column=0, padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_5_0'], sticky='ew'
        )
        tk.Label(
            left_header, text='Parameters:', font=FONTS['PARAMETER_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
        ).pack(padx=GAPS['GAPS_X']['PAD_X_10'], pady=GAPS['GAPS_Y']['PAD_Y_0_5'])

        right_header = tk.Frame(frame, bg=COLORS['BACKGROUND_COLOR'])
        right_header.grid(
            row=1, column=1, columnspan=2,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_5_0'], sticky='w'
        )
        right_header.grid_columnconfigure(1, minsize=MINSIZE_RIGHT_HEADER)
        tk.Label(
            right_header, text='Required Parameters:',
            font=FONTS['PARAMETER_FONT'], bg=COLORS['BACKGROUND_COLOR']
        ).grid(row=0, column=0, padx=GAPS['GAPS_X']['PAD_X_10_30'], sticky='w')
        tk.Label(
            right_header, text='Additional Parameters:',
            font=FONTS['PARAMETER_FONT'], bg=COLORS['BACKGROUND_COLOR']
        ).grid(row=0, column=1, sticky='e')

        self.left_canvas = tk.Canvas(
            frame, bg=COLORS['PARAMETERS_BACKGROUND_COLOR'],
            highlightthickness=0, width=LEFT_CANVAS_WIDTH
        )
        self.left_canvas.grid(
            row=2, column=0, padx=GAPS['GAPS_X']['PAD_X_10_15'],
            pady=GAPS['GAPS_Y']['PAD_Y_0_5'], sticky='ns'
        )
        left_scroll = ttk.Scrollbar(frame, orient='vertical', command=self.left_canvas.yview)
        left_scroll.grid(row=2, column=0, padx=GAPS['GAPS_X']['PAD_X_0_10'], sticky='nse')
        self.left_canvas.configure(yscrollcommand=left_scroll.set)

        self.right_canvas = tk.Canvas(
            frame, bg=COLORS['BACKGROUND_COLOR'], highlightthickness=0
        )
        self.right_canvas.grid(
            row=2, column=1, padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_10_5'], sticky='nsew'
        )
        right_scroll = ttk.Scrollbar(frame, orient='vertical', command=self.right_canvas.yview)
        right_scroll.grid(row=2, column=2, sticky='ns')
        self.right_canvas.configure(yscrollcommand=right_scroll.set)

        buttons_frame = tk.Frame(self.left_canvas, bg=COLORS['PARAMETERS_BACKGROUND_COLOR'])
        self.right_frame = tk.Frame(self.right_canvas, bg=COLORS['BACKGROUND_COLOR'])
        self.right_frame.grid_columnconfigure(0, minsize=MINSIZE_RIGHT_FRAME)
        self.left_canvas.create_window(
            (0, 0), window=buttons_frame, anchor='nw',
            width=NFME_BUTTONS['BUTTONS_FRAME_WIDTH']
        )
        self.right_canvas.create_window((0, 0), window=self.right_frame, anchor='nw')

        self.right_frame.bind(
            '<Configure>',
            lambda e: self.right_canvas.configure(scrollregion=self.right_canvas.bbox('all'))
        )

        for column_name in self.df.columns.tolist():
            button = tk.Button(
                buttons_frame, text=column_name,
                command=lambda name=column_name: self.get_button_name(name),
                width=NFME_BUTTONS['BUTTONS_WIDTH'], font=FONTS['DATA_FONT'],
                relief=tk.RAISED, bd=2
            )
            self.selected_column_buttons[column_name] = button
            button.pack(
                padx=GAPS['GAPS_X']['PAD_X_5'], pady=GAPS['GAPS_Y']['PAD_Y_2']
            )

        buttons_frame.update_idletasks()
        self.left_canvas.configure(scrollregion=self.left_canvas.bbox('all'))

        def wheel_left(event):
            self.left_canvas.yview_scroll(
                int(-event.delta / MOUSE_WHEEL_DELTA), 'units'
            )

        def wheel_right(event):
            self.right_canvas.yview_scroll(
                int(-event.delta / MOUSE_WHEEL_DELTA), 'units'
            )

        self.left_canvas.bind('<Enter>', lambda e: self.root.bind_all('<MouseWheel>', wheel_left))
        self.left_canvas.bind('<Leave>', lambda e: self.root.unbind_all('<MouseWheel>'))
        self.right_canvas.bind('<Enter>', lambda e: self.root.bind_all('<MouseWheel>', wheel_right))
        self.right_canvas.bind('<Leave>', lambda e: self.root.unbind_all('<MouseWheel>'))

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
            (name, IMAX_COMPUTED_PARAMS[name]["title"], str(self.computed_values[name]))
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
    # Auxiliary parameters
    # ------------------------------------------------------------------
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
                EXTRA_DIALOG_TITLE,
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
                    EXTRA_DIALOG_TITLE,
                    "The name must not be empty.",
                    parent=self.root
                )
                continue

            if name.casefold() in existing:
                messagebox.showwarning(
                    EXTRA_DIALOG_TITLE,
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
        the processing window on its own scale. Any number of them can be
        added; the combobox keeps "Add new parameter" selected for the
        next one.
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
                EXTRA_DIALOG_TITLE,
                "The selected columns contain no numeric data.",
                parent=self.root
            )
            self.clear_selected_column_buttons()
            return

        if len(columns) > 1:
            proceed = messagebox.askyesno(
                EXTRA_DIALOG_TITLE,
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
        info = IMAX_NFME_PARAMS[key]
        attrs: dict[str, Any] = {info["attr"]: None}
        attrs.update(info.get("extra_attrs", {}))
        return attrs

    def _remove_nfme_parameter(self, key: str) -> None:
        self.parameter_columns.pop(key, None)
        if key.startswith(EXTRA_PREFIX):
            extra_name = key[len(EXTRA_PREFIX):]
            self.extra_parameters = [
                p for p in self.extra_parameters if p["name"] != extra_name
            ]
        elif key in IMAX_NFME_PARAMS:
            for attr, default in self._nfme_attrs(key).items():
                setattr(self, attr, self._copy_value(default))
            if IMAX_NFME_PARAMS[key].get("headers") and hasattr(self, "column_headers"):
                self.column_headers.pop(IMAX_NFME_PARAMS[key]["attr"], None)
        if key in self.NFME_parameters:
            self.NFME_parameters.remove(key)

    def _set_computed(self, name: str, value: float) -> None:
        setattr(self, IMAX_COMPUTED_PARAMS[name]["attr"], value)
        self.computed_values[name] = value
        if name not in self.computed_parameters:
            self.computed_parameters.append(name)

    def _remove_computed_parameter(self, name: str) -> None:
        self.computed_values.pop(name, None)
        # The value goes back to its default
        setattr(self, IMAX_COMPUTED_PARAMS[name]["attr"], IMAX_COMPUTED_PARAMS[name]["default"])
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
            if key in IMAX_NFME_PARAMS
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

    def _reset_state_attrs(self) -> None:
        """Put all attributes of the parameters to the initial values."""
        for key in IMAX_NFME_PARAMS:
            for attr, default in self._nfme_attrs(key).items():
                setattr(self, attr, self._copy_value(default))
        if hasattr(self, "column_headers"):
            self.column_headers = {}
        self.extra_parameters = []
        for info in IMAX_COMPUTED_PARAMS.values():
            setattr(self, info["attr"], info["default"])

    def _apply_state(self, state: dict[str, Any]) -> None:
        """Make the given snapshot current and redraw the UI."""
        self._reset_state_attrs()
        self.parameter_columns.clear()
        self.NFME_parameters = []
        self.computed_values = {}
        self.extra_parameters = []
        self.computed_parameters = []

        extras = {p["name"]: p for p in state["extras"]}
        for key in state["order"]:
            if key.startswith(EXTRA_PREFIX):
                extra = extras[key[len(EXTRA_PREFIX):]]
                self.extra_parameters.append(
                    dict(extra, columns=list(extra["columns"]))
                )
                self.parameter_columns[key] = list(extra["columns"])
                self.NFME_parameters.append(key)
                continue
            cols, values = state["params"][key]
            for attr, value in values.items():
                setattr(self, attr, self._copy_value(value))
            self.parameter_columns[key] = list(cols)
            if IMAX_NFME_PARAMS[key].get("headers"):
                self.column_headers[IMAX_NFME_PARAMS[key]["attr"]] = list(cols)
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
        return getattr(self, IMAX_NFME_PARAMS[param]["label"], None)

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
        if self.Imax_frame is None or not self.Imax_frame.winfo_exists():
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

        for param, info in IMAX_NFME_PARAMS.items():
            label = self._nfme_label(param)
            if label is None:
                continue
            text = info["text"]
            if param in self.parameter_columns:
                text = "✓" + text[1:]
            label.config(text=text)

        for name, info in IMAX_COMPUTED_PARAMS.items():
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

    def _required_label(self, text: str, row: int, column: int) -> tk.Label:
        label = tk.Label(
            self.right_frame, text=text,
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        label.grid(
            row=row, column=column,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'], sticky='w'
        )
        return label

    def _entry_row(self, text: str, row: int, value_name: str) -> ttk.Entry:
        """Label on the left, entry at the right edge of the same cell."""
        tk.Label(
            self.right_frame, text=text, font=FONTS['INFO_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
        ).grid(row=row, column=0, sticky='w')
        entry = ttk.Entry(
            self.right_frame, font=FONTS['DATA_FONT'], width=ENTRY_WIDTH
        )
        entry.grid(
            row=row, column=0, padx=GAPS['GAPS_X']['PAD_X_10'], sticky='e'
        )
        entry.bind(
            '<Return>', lambda event: self.get_entry(entry, value_name)
        )
        return entry

    def labels(self) -> None:
        self.time_required_label = self._required_label('⏱ Time :1', 1, 0)
        self.temperature_required_label = self._required_label(
            '⏱ Temperature :1+', 2, 0
        )
        self.current_required_label = self._required_label(
            '⏱ Current :2', 3, 0
        )
        # Optional values: no clock, they have defaults / may stay empty
        self.base_required_label = self._required_label('  Base', 1, 1)
        self.MC_required_label = self._required_label('  MC', 2, 1)

        tk.Label(
            self.right_frame, text='Enter the additional parameters:',
            font=FONTS['SPLITTER_FONT'], bg=COLORS['BACKGROUND_COLOR']
        ).grid(row=4, column=0, columnspan=2, sticky='w')

        self.MC_entry = self._entry_row('MC, MWt/(°C/h):', 5, 'MC')
        self.MC_entry.focus_set()
        self.base_entry = self._entry_row('base, s:', 6, 'base')
        self.base_entry.insert(0, str(IMAX_BASE_DEFAULT))

    def buttons(self) -> None:
        def place(button, row: int, column: int) -> None:
            button.grid(
                row=row, column=column,
                padx=GAPS['GAPS_X']['PAD_X_40_20'],
                pady=GAPS['GAPS_Y']['PAD_Y_10'], sticky='w'
            )

        self.get_MC_button = TestButtons(
            self.right_frame, text='Get the MC',
            command=lambda: self.get_entry(self.MC_entry, 'MC')
        )
        place(self.get_MC_button, 5, 1)

        self.get_base_button = TestButtons(
            self.right_frame, text='Get the base',
            command=lambda: self.get_entry(self.base_entry, 'base')
        )
        place(self.get_base_button, 6, 1)

        self.get_parameter_button = TestButtons(
            self.right_frame, text='Get a parameter', command=self.get_parameter
        )
        place(self.get_parameter_button, 7, 1)

        self.START_button = TestButtons(
            self.right_frame, text='START', command=self.start_Imax
        )
        place(self.START_button, 8, 0)

        self.BACK_button = MainButtons(
            self.right_frame, text='<< BACK',
            command=lambda: self.back(self.Imax_frame)
        )
        place(self.BACK_button, 8, 1)

        self.INFO_button = MainButtons(
            self.right_frame, text='User guide',
            command=lambda: show_info(self.root, 'Imax/info_module.txt')
        )
        place(self.INFO_button, 9, 1)

    def combobox(self) -> None:
        self.selected_param = tk.StringVar(value='Not selected')
        self.parameter_combobox = ttk.Combobox(
            self.right_frame, textvariable=self.selected_param,
            values=['Not selected', 'Time', 'Temperature', 'Current', ADD_PARAMETER],
            state='readonly', width=20, font=FONTS['TEXT_FONT']
        )
        self.parameter_combobox.grid(
            row=7, column=0, padx=GAPS['GAPS_X']['PAD_X_10'], sticky='w'
        )

    def get_entry(self, entry: ttk.Entry, value_name: str) -> bool:
        """Obtain MC or base from its entry field.

        Checks the value, stores it and ticks the label. Returns True if the
        value was accepted.
        """
        rules: dict[str, dict[str, Any]] = {
            'MC': {
                'attr': 'MC', 'label': self.MC_required_label,
                'label_text': '✓ MC', 'sign': 'strictly_positive'
            },
            'base': {
                'attr': 'base', 'label': self.base_required_label,
                'label_text': '✓ Base', 'sign': 'range',
                'range': IMAX_BASE_RANGE
            },
        }[value_name]

        value = entry.get().strip().replace(',', '.')
        try:
            numeric_value = float(value)
        except Exception as e:
            Messages.show('error', 'VALUE_ERROR', value_name=value_name, error=e)
            self.reset_entry(entry)
            return False

        if rules['sign'] == 'strictly_positive' and numeric_value <= 0:
            Messages.show(
                'error', 'VALUE_POSTIVE', value=value_name, sign='positive'
            )
            self.reset_entry(entry)
            return False

        if rules['sign'] == 'range':
            low, high = rules['range']
            if not (low <= numeric_value <= high):
                Messages.show(
                    'warning', 'BASE_OUT_OF_RANGE',
                    value=value_name, low=low, high=high
                )
                self.reset_entry(entry)
                return False
            numeric_value = int(round(numeric_value))

        if self.computed_values.get(value_name) != numeric_value:
            self._push_undo()
        self._set_computed(value_name, numeric_value)
        self.refresh_ui()
        return True

    def reset_entry(self, *entries) -> None:
        for entry in entries:
            entry.delete(0, tk.END)
            entry.focus_set()

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

    def get_parameter(self) -> None:
        parameter = self.selected_param.get()
        if parameter == 'Not selected':
            Messages.show('warning', 'PARAM_NOT_SELECTED')
            return
        if not self.selected_columns:
            Messages.show('warning', 'NO_COLUMNS')
            return
        if parameter == ADD_PARAMETER:
            self.add_extra_parameter()
            return

        columns = self.selected_columns.copy()
        try:
            data = self.df[columns].apply(pd.to_numeric, errors='coerce')
            if data.isna().any().any():
                bad_col = data.columns[data.isna().any()][0]
                Messages.show('error', 'DATA_FORMAT', col=bad_col, value='non-numeric value')
                self.clear_selected_column_buttons()
                return

            if parameter == 'Time':
                if len(columns) != 1:
                    Messages.show('warning', 'COLUMNS_COUNT', param='Time', expected=1, selected=len(columns))
                    self.clear_selected_column_buttons()
                    return
                new_values = {'Time': self.df[columns[0]].copy()}
            elif parameter == 'Temperature':
                new_values = {
                    'Temperature': (
                        data.mean(axis=1) if len(columns) > 1
                        else data.iloc[:, 0]
                    )
                }
            else:  # Current
                new_values = {
                    'Current_columns': list(columns),
                    'Current': data.copy(),
                }
        except Exception as exc:
            Messages.show('error', 'VALUE_ERROR', value_name=parameter, error=exc)
            self.clear_selected_column_buttons()
            return

        self._push_undo()
        for attr, value in new_values.items():
            setattr(self, attr, value)

        # If the parameter was already obtained, its old columns are released
        self.parameter_columns[parameter] = columns
        if parameter not in self.NFME_parameters:
            self.NFME_parameters.append(parameter)

        self.selected_columns.clear()
        self.refresh_ui()

    def apply_pending_entries(self) -> bool:
        """Take base and MC as they are typed, even if 'Get' was not pressed."""
        if not self.get_entry(self.base_entry, 'base'):
            return False
        if self.MC_entry.get().strip():
            return self.get_entry(self.MC_entry, 'MC')
        if 'MC' in self.computed_values:  # the entry was cleared by the user
            self._push_undo()
            self._remove_computed_parameter('MC')
            self.refresh_ui(sync_entries=True)
        return True

    def start_Imax(self) -> None:
        missing = []
        if self.Time is None:
            missing.append('Time')
        if self.Temperature is None:
            missing.append('Temperature')
        if self.Current is None or not self.Current_columns:
            missing.append('Current')
        if missing:
            if len(missing) == 1:
                Messages.show('warning', 'MISSING_PARAMS', param=missing[0], test='Imax')
            else:
                Messages.show(
                    'warning', 'MISSING_PARAMS',
                    params='\n'.join(f'• {p}' for p in missing), test='Imax'
                )
            return

        if not self.apply_pending_entries():
            return

        # Shortcuts and parameter windows must not touch the state while
        # the processing window is open
        self.unbind_undo_redo()
        self.close_parameter_windows()

        self.Imax_processing_interface = Imax_processing(self.Imax_frame, self)
        self.Imax_processing_interface.create_Imax_processing_window()

    def reset_parameters(self) -> None:
        self.Time = None
        self.Temperature = None
        self.Current = None
        self.Current_columns = []
        self.selected_columns = []
        self.parameter_columns.clear()
        self.NFME_parameters = []
        self.MC = None
        self.base = IMAX_BASE_DEFAULT
        self.computed_parameters = []
        self.computed_values = {}
        self.extra_parameters = []
        self._undo_stack.clear()
        self._redo_stack.clear()

    def back(self, window: tk.Widget) -> None:
        self.unbind_undo_redo()
        self.close_parameter_windows()
        self.reset_parameters()
        if self.menu_bar is not None:
            self.root.winfo_toplevel().config(menu=None)
            self.menu_bar.destroy()
            self.menu_bar = None
        window.destroy()
        self.root.title('3 in 1 v2')