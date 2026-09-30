import tkinter as tk
from tkinter import ttk
from typing import Any, Optional, List
import pandas as pd

from .Imax_processing import Imax_processing
from Buttons import MainButtons, TestButtons, SmallButtons
from Messages import Messages
from Settings import (
    show_info, FONTS, COLORS, GAPS, ENTRY_WIDTH,
    HEADER_FRAME_HEIGHT, MOUSE_WHEEL_DELTA, NFME_BUTTONS,
    MINSIZE_RIGHT_FRAME, MINSIZE_RIGHT_HEADER, LEFT_CANVAS_WIDTH,
)


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

    def create_menu(self) -> None:
        root_window = self.root.winfo_toplevel()
        root_window.config(menu=None)
        self.menu_bar = tk.Menu(root_window)
        root_window.config(menu=self.menu_bar)

        chosen = tk.Menu(self.menu_bar, tearoff=1)
        self.menu_bar.add_cascade(label='Currently chosen buttons', menu=chosen)
        chosen.add_command(
            label='Show selected buttons', font=FONTS['DATA_FONT'],
            command=lambda: self.show_selected_parameters('selected_columns')
        )
        chosen.add_command(
            label='Clear all parameters', font=FONTS['DATA_FONT'],
            command=self.clear_all_selection
        )
        chosen.add_command(
            label='Clear last parameter', font=FONTS['DATA_FONT'],
            command=self.clear_last_parameter
        )

        parameters = tk.Menu(self.menu_bar, tearoff=1)
        self.menu_bar.add_cascade(label='Parameters', menu=parameters)
        parameters.add_command(
            label='Show selected parameters', font=FONTS['DATA_FONT'],
            command=lambda: self.show_selected_parameters('parameter_columns')
        )
        parameters.add_command(
            label='Clear all parameters', font=FONTS['DATA_FONT'],
            command=self.clear_all_parameters
        )

        info = tk.Menu(self.menu_bar, tearoff=1)
        self.menu_bar.add_cascade(label='INFO', menu=info)
        info.add_command(
            label='INFO', font=FONTS['DATA_FONT'],
            command=lambda: show_info(self.root, 'Imax/info_module.txt')
        )

    def create_parameter_frames(self) -> None:
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

    def labels(self) -> None:
        self.time_required_label = tk.Label(
            self.right_frame, text='⏱ Time :1', font=FONTS['TEXT_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
        )
        self.time_required_label.grid(row=1, column=0, padx=10, pady=2, sticky='w')

        self.temperature_required_label = tk.Label(
            self.right_frame, text='⏱ Temperature :1+', font=FONTS['TEXT_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
        )
        self.temperature_required_label.grid(row=2, column=0, padx=10, pady=2, sticky='w')

        self.current_required_label = tk.Label(
            self.right_frame, text='⏱ Current :1+', font=FONTS['TEXT_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
        )
        self.current_required_label.grid(row=3, column=0, padx=10, pady=2, sticky='w')

        tk.Label(
            self.right_frame, text='Enter the additional parameters:',
            font=FONTS['SPLITTER_FONT'], bg=COLORS['BACKGROUND_COLOR']
        ).grid(row=5, column=0, columnspan=2, sticky='w', pady=(15, 5))

        self.additional_placeholder = tk.Label(
            self.right_frame, text='No additional parameters yet.',
            font=FONTS['INFO_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.additional_placeholder.grid(row=6, column=0, sticky='w')

    def buttons(self) -> None:
        self.get_parameter_button = TestButtons(
            self.right_frame, text='Get a parameter', command=self.get_parameter
        )
        self.get_parameter_button.grid(
            row=4, column=0, padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'], sticky='w'
        )

        self.START_button = TestButtons(
            self.right_frame, text='START', command=self.start_Imax
        )
        self.START_button.grid(
            row=7, column=0, padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'], sticky='w'
        )
        self.BACK_button = MainButtons(
            self.right_frame, text='<< BACK',
            command=lambda: self.back(self.Imax_frame)
        )
        self.BACK_button.grid(
            row=7, column=1, padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'], sticky='w'
        )
        self.INFO_button = MainButtons(
            self.right_frame, text='User guide',
            command=lambda: show_info(self.root, 'Imax/info_module.txt')
        )
        self.INFO_button.grid(
            row=8, column=1, padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'], sticky='w'
        )

    def combobox(self) -> None:
        self.selected_param = tk.StringVar(value='Not selected')
        self.parameter_combobox = ttk.Combobox(
            self.right_frame, textvariable=self.selected_param,
            values=['Not selected', 'Time', 'Temperature', 'Current'],
            state='readonly', width=20, font=FONTS['TEXT_FONT']
        )
        self.parameter_combobox.grid(
            row=4, column=1, padx=GAPS['GAPS_X']['PAD_X_10'], sticky='w'
        )

    def get_button_name(self, button_name: str) -> None:
        if button_name in self.selected_columns:
            self.selected_columns.remove(button_name)
            self.selected_column_buttons[button_name].config(relief=tk.RAISED, bd=2)
        else:
            self.selected_columns.append(button_name)
            self.selected_column_buttons[button_name].config(relief=tk.SUNKEN, bd=2)

    def clear_selected_column_buttons(self) -> None:
        for name in self.selected_columns:
            if name in self.selected_column_buttons:
                self.selected_column_buttons[name].config(relief=tk.RAISED, bd=2)
        self.selected_columns.clear()

    def set_column_buttons_state(self, columns: list[str], disabled: bool) -> None:
        for name in columns:
            button = self.selected_column_buttons.get(name)
            if button is None:
                continue
            button.config(
                state=tk.DISABLED if disabled else tk.NORMAL,
                relief=tk.SUNKEN if disabled else tk.RAISED, bd=2
            )

    def get_parameter(self) -> None:
        parameter = self.selected_param.get()
        if parameter == 'Not selected':
            Messages.show('warning', 'PARAM_NOT_SELECTED')
            return
        if not self.selected_columns:
            Messages.show('warning', 'NO_COLUMNS')
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
                self.Time = self.df[columns[0]].copy()
                self.parameter_columns['Time'] = columns
                self.time_required_label.config(text='✓ Time :1')

            elif parameter == 'Temperature':
                self.Temperature = data.mean(axis=1) if len(columns) > 1 else data.iloc[:, 0]
                self.parameter_columns['Temperature'] = columns
                self.temperature_required_label.config(text='✓ Temperature :1+')

            elif parameter == 'Current':
                self.Current_columns = columns
                self.Current = data.copy()
                self.parameter_columns['Current'] = columns
                self.current_required_label.config(text='✓ Current :1+')

            self.set_column_buttons_state(columns, disabled=True)
            if parameter not in ('Time', 'Temperature', 'Current'):
                return
            self.selected_columns.clear()
        except Exception as exc:
            Messages.show('error', 'VALUE_ERROR', value_name=parameter, error=exc)
            self.clear_selected_column_buttons()

    def clear_last_parameter(self) -> None:
        if self.selected_columns:
            name = self.selected_columns.pop()
            self.selected_column_buttons[name].config(relief=tk.RAISED, bd=2)

    def clear_all_selection(self) -> None:
        self.selected_columns.clear()
        for button in self.selected_column_buttons.values():
            button.config(state=tk.NORMAL, relief=tk.RAISED, bd=2)

    def clear_all_parameters(self) -> None:
        self.Time = None
        self.Temperature = None
        self.Current = None
        self.Current_columns = []
        self.parameter_columns.clear()
        self.time_required_label.config(text='⏱ Time :1')
        self.temperature_required_label.config(text='⏱ Temperature :1+')
        self.current_required_label.config(text='⏱ Current :1+')
        self.clear_all_selection()

    def show_selected_parameters(self, attr_name: str) -> None:
        if attr_name == 'selected_columns':
            values = self.selected_columns.copy()
        else:
            values = [f'{k}: {v}' for k, v in self.parameter_columns.items()]
        win = tk.Toplevel(self.root)
        win.title('Selected parameters')
        win.geometry('500x350')
        win.config(bg=COLORS['BACKGROUND_COLOR'])
        frame = tk.Frame(win, bg=COLORS['BACKGROUND_COLOR'])
        frame.pack(fill='both', expand=True, padx=10, pady=10)
        listbox = tk.Listbox(
            frame, font=FONTS['DATA_FONT'],
            bg=COLORS['PARAMETERS_BACKGROUND_COLOR']
        )
        listbox.pack(fill='both', expand=True)
        for value in values:
            listbox.insert(tk.END, value)
        SmallButtons(win, text='Close', command=win.destroy).pack(pady=5)

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

        self.Imax_processing_interface = Imax_processing(self.Imax_frame, self)
        self.Imax_processing_interface.create_Imax_processing_window()

    def reset_parameters(self) -> None:
        self.Time = None
        self.Temperature = None
        self.Current = None
        self.Current_columns = []
        self.selected_columns = []
        self.parameter_columns.clear()

    def back(self, window: tk.Widget) -> None:
        self.reset_parameters()
        if self.menu_bar is not None:
            self.root.winfo_toplevel().config(menu=None)
            self.menu_bar.destroy()
            self.menu_bar = None
        window.destroy()
        self.root.title('3 in 1 v2')
