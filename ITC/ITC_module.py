import tkinter as tk
from tkinter import ttk
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
        show_selected_parameters: Represent parameters (current, NFME,
        computed) chosen.
        clear_all_parameters: Clear all parameters from a given attribute list.
        clear_last_parameter: Remove the last item from currently chosen
        NFME parameters.
        clear_selected_parameters: Clear selected parameters from a listbox.
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
        self.DYDT = -1.73
        self.Temperature: Optional[pd.Series] = None
        self.Reactivity: Optional[pd.Series] = None
        self.Time: Optional[pd.Series] = None
        self.Group_position: Optional[pd.Series] = None
        self.selected_columns: List[str] = []
        self.NFME_parameters: List[str] = []
        self.computed_parameters: List[str] = []
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
        self.DYDT_entry.insert(0, "-1.73")
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
            - Currently chosen buttons
            - NFME parameters (chosen)
            - Computed parameters (entered)
            - INFO
        """
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)

        currently_choosen_parameters = tk.Menu(self.menu_bar, tearoff=1)
        self.menu_bar.add_cascade(
            label="Currently chosen buttons",
            menu=currently_choosen_parameters
        )

        currently_choosen_parameters.add_command(
            label="Show selected buttons",
            font=FONTS['DATA_FONT'],
            command=lambda: self.show_selected_parameters("selected_columns")
        )
        currently_choosen_parameters.add_command(
            label="Clear all parameters",
            font=FONTS['DATA_FONT'],
            command=lambda: self.clear_all_parameters("selected_columns")
        )
        currently_choosen_parameters.add_command(
            label="Clear last parameter",
            font=FONTS['DATA_FONT'],
            command=self.clear_last_parameter
        )

        NFME_parameters = tk.Menu(self.menu_bar, tearoff=1)
        self.menu_bar.add_cascade(
            label="NFME parameters", menu=NFME_parameters
        )

        NFME_parameters.add_command(
            label="Show selected parameters",
            font=FONTS['DATA_FONT'],
            command=lambda: self.show_selected_parameters("NFME_parameters")
        )
        NFME_parameters.add_command(
            label="Clear all parameters",
            font=FONTS['DATA_FONT'],
            command=lambda: self.clear_all_parameters("NFME_parameters")
        )

        computed_parameters = tk.Menu(self.menu_bar, tearoff=1)
        self.menu_bar.add_cascade(
            label="Computed parameters", menu=computed_parameters
        )

        computed_parameters.add_command(
            label="Show selected parameters",
            font=FONTS['DATA_FONT'],
            command=lambda: self.show_selected_parameters(
                "computed_parameters"
            )
        )
        computed_parameters.add_command(
            label="Clear all parameters",
            font=FONTS['DATA_FONT'],
            command=lambda: self.clear_all_parameters("computed_parameters")
        )

        info = tk.Menu(self.menu_bar, tearoff=1)
        self.menu_bar.add_cascade(label="INFO", menu=info)

        info.add_command(
            label="INFO",
            font=FONTS['DATA_FONT'],
            command=lambda: show_info(self.root, "ITC/info_module.txt")
        )

    def show_selected_parameters(self, attr_name: str) -> None:
        """
        Open a new window represents selected parameters for a given attribute.

        Args (given attributes):
            attr_name (str): Name of attribute contains a set of selected
            parameters. Among them: ('selected_columns', 'NFME_parameters',
                             or 'computed_parameters').

            'selected_columns' means paremeters from NFME file currenlty
            selected from one combobox parameter, "Get parameter" button
            has not pressed yet.

            'NFME_parameters' means the list of parameters, which has
            already fixed via "Get parameter" button.

            'computed_parameters' means parameters, entered via entry
            fields
        """
        params = getattr(self, attr_name)

        data_window = tk.Toplevel(self.root)
        data_window.title('NFME parameters')
        data_window.geometry("340x250")
        data_window.config(bg=COLORS['BACKGROUND_COLOR'])

        frame = tk.Frame(data_window)
        frame.pack(
            fill=tk.BOTH, expand=True,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'],
        )

        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)

        listbox = tk.Listbox(
            frame,
            selectmode=tk.MULTIPLE,
            font=FONTS['DATA_FONT'],
            bg=COLORS['PARAMETERS_BACKGROUND_COLOR']
        )

        for i, param in enumerate(params):
            listbox.insert(i, param)

        listbox.grid(row=0, column=0, columnspan=2, sticky='nswe')

        button_frame = tk.Frame(data_window, bg=COLORS['BACKGROUND_COLOR'])
        button_frame.pack(pady=5)

        clear_all_parameters_button = SmallButtons(
              button_frame,
              text='Clear all parameters',
              command=lambda: self.clear_all_parameters(attr_name, listbox),
        )
        clear_all_parameters_button.grid(
            row=1, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_0_5']
        )

        clear_selected_parameters_button = SmallButtons(
              button_frame,
              text='Clear selected parameters',
              command=lambda: self.clear_selected_parameters(
                  attr_name, listbox
                ),
        )
        clear_selected_parameters_button.grid(
            row=1, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_0_5']
        )

    def clear_all_parameters(
            self,
            attr_name: str,
            listbox: tk.Listbox = None
    ) -> None:
        """
        Clear all parameters from a given attribute list and reset UI.

        Args:
            attr_name (str): Attribute name to clear.
            listbox (tk.Listbox, optional): Related listbox to clear.
        """
        if attr_name == 'selected_columns':
            self.clear_selected_column_buttons()

        else:
            getattr(self, attr_name).clear()

            if attr_name == 'NFME_parameters':
                self.reset_parameters('NFME')
                self.parameter_columns.clear()

                self.time_required_label.config(text="⏱ Time :1")
                self.temparature_required_label.config(text="⏱ Temperature")
                self.reactivity_required_label.config(text="⏱ Reactivity :2")
                self.group_position_required_label.config(
                    text="⏱ Group position :1"
                )

            elif attr_name == 'computed_parameters':
                self.reset_parameters('computed')
                self.reset_entry(
                    self.DTC_entry,
                    self.MTC_entry,
                    self.ITC_entry,
                    self.DRDY_entry,
                    self.boric_acid_entry,
                    self.DYDT_entry
                )
                self.DTC_entry.focus_set()
                self.DYDT_entry.insert(0, "-1.73")

                self.DTC_required_label.config(text='⏱ DTC')
                self.MTC_required_label.config(text='⏱ MTC')
                self.ITC_required_label.config(text='⏱ ITC')
                self.boric_acid_required_label.config(
                    text='⏱ Boric acid concentration '
                )
                self.DRDY_required_label.config(text='⏱ DRDY')

        if listbox is not None:
            listbox.delete(0, tk.END)

    def clear_last_parameter(self) -> None:
        """
        Remove the last selected NFME column and reset its button.
        """
        if self.selected_columns:
            button_name = self.selected_columns.pop()

            button = self.selected_column_buttons.get(button_name)
            if button:
                button.config(
                    relief=tk.RAISED,
                    bd=2
                )

    def clear_selected_parameters(
            self,
            attr_name: str,
            listbox: tk.Listbox
    ) -> None:
        """
        Clear selected parameters from a listbox and update UI.

        Args:
            attr_name (str): Attribute contains parameters.
            listbox (tk.Listbox): Listbox widget contains selected items.
        """
        params = getattr(self, attr_name)
        selected = listbox.curselection()

        removed_params = []
        for index in reversed(selected):
            removed_params += [params[index]]
            if attr_name == 'NFME_parameters':
                self.parameter_columns.pop(params[index], None)
            del params[index]
            listbox.delete(index)

        if attr_name == 'NFME_parameters':
            remaining_params = params
            if 'Time' not in remaining_params:
                self.time_required_label.config(text="⏱ Time :1")

            if 'Temperature' not in remaining_params:
                self.temparature_required_label.config(
                    text="⏱ Temperature"
                )

            if 'Reactivity' not in remaining_params:
                self.reactivity_required_label.config(text="⏱ Reactivity :2")

            if 'Group position' not in remaining_params:
                self.group_position_required_label.config(
                    text="⏱ Group position :1"
                )

        elif attr_name == 'computed_parameters':

            for param in removed_params:
                if param == 'DTC':
                    self.DTC = None
                    self.DTC_required_label.config(text='⏱ DTC')
                    self.DTC_entry.delete(0, tk.END)
                elif param == 'MTC':
                    self.MTC_computed = None
                    self.MTC_required_label.config(text='⏱ MTC')
                    self.MTC_entry.delete(0, tk.END)
                elif param == 'ITC':
                    self.ITC_computed = None
                    self.ITC_required_label.config(text='⏱ ITC')
                    self.ITC_entry.delete(0, tk.END)
                elif param == 'DRDY':
                    self.DRDY_computed = None
                    self.DRDY_required_label.config(text='⏱ DRDY')
                    self.DRDY_entry.delete(0, tk.END)
                elif param == 'Boric acid concentration':
                    self.boric_acid = None
                    self.DRDY_required_label.config(
                        text='⏱ Boric acid concentration'
                    )
                    self.boric_acid_entry.delete(0, tk.END)
                elif param == 'DYDT':
                    self.DYDT = -1.73
                    self.DYDT_entry.delete(0, tk.END)
                    self.DYDT_entry.insert(0, "-1.73")

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
                "label": lambda self: self.time_required_label,
                "label_text": "✓ Time: 1"
            },
            "Reactivity": {
                "columns": 2,
                "range": RANGES_EXPECTED['REACTIVITY_RANGE'],
                "allow_exp": False,
                "attr": "Reactivity",
                "label": lambda self: self.reactivity_required_label,
                "label_text": "✓ Reactivity :2"
            },
            "Group position": {
                "columns": 1,
                "range": RANGES_EXPECTED['GROUP_POSITION_RANGE'],
                "allow_exp": False,
                "attr": "Group_position",
                "label": lambda self: self.group_position_required_label,
                "label_text": "✓ Group position"
            },
            "Temperature": {
                "columns": None,
                "range": RANGES_EXPECTED['TEMPERATURE_RANGE'],
                "allow_exp": False,
                "attr": "Temperature",
                "label": lambda self: self.temparature_required_label,
                "label_text": "✓ Temperature"
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

        setattr(self, rules["attr"], result)

        # Save column names assigned to the parameter
        self.parameter_columns[selected_param] = self.selected_columns.copy()

        label = rules["label"](self)

        column_names = ", ".join(self.parameter_columns[selected_param])
        label.config(
            text=f"{rules['label_text']} [{column_names}]"
        )

        if selected_param not in self.NFME_parameters:
            self.NFME_parameters.append(selected_param)

        self.clear_selected_column_buttons()

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

        setattr(self, rules["attr"], numeric_value)
        self.computed_parameters += [value_name]
        label: tk.Label = rules["label"](self)
        label.config(text=rules["label_text"])

    def get_button_name(self, button_name: str) -> None:
        """
        Toggle selection of an NFME data column.

        Selected columns remain visually pressed until the parameter
        is assigned or the selection is cleared.
        """
        if button_name in self.selected_columns:
            self.selected_columns.remove(button_name)

            button = self.selected_column_buttons.get(button_name)
            if button:
                button.config(
                    relief=tk.RAISED,
                    bd=2
                )
        else:
            self.selected_columns.append(button_name)

            button = self.selected_column_buttons.get(button_name)
            if button:
                button.config(
                    relief=tk.SUNKEN,
                    bd=2
                )

    def clear_selected_column_buttons(self) -> None:
        """Reset visual selection of all NFME column buttons."""
        for button in self.selected_column_buttons.values():
            button.config(
                relief=tk.RAISED,
                bd=2
            )

        self.selected_columns.clear()

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
            self.DYDT = -1.73

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
        self.reset_parameters('NFME', 'computed')
        self.clear_selected_column_buttons()
        self.parameter_columns.clear()
        self.NFME_parameters = []
        self.computed_parameters = []

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
        Create the NFME buttons field in the ITC frame.

        Adds scrollbars for both fields.
        """
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
