import tkinter as tk
from tkinter import ttk
from typing import Any, Optional, List, Dict
import pandas as pd

from .PCR_processing import PCR_processing
from Buttons import MainButtons, TestButtons, SmallButtons
from Messages import Messages
from Settings import (
    show_info, FONTS, COLORS, GAPS, ENTRY_WIDTH, RANGES_EXPECTED,
    HEADER_FRAME_HEIGHT, MOUSE_WHEEL_DELTA, NFME_BUTTONS, MINSIZE_RIGHT_FRAME,
    MINSIZE_RIGHT_HEADER, LEFT_CANVAS_WIDTH, PCR_BASE_RANGE, PCR_BASE_DEFAULT
)


class PCR_module:
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
        """Initialize PCR module attributes.

        Args:
            root (tk.Widget): Parent Tkinter widget.
            main_app (Any): Main application instance providing data
            and settings.

        Attributes:
            root (tk.Widget): Parent Tkinter widget.
            main_app (Any): Reference to main application instance.
            df (pd.DataFrame): Loaded data from main application.
            PCR_frame (Optional[tk.Frame]): Main frame of the PCR module.
            menu_bar (Optional[tk.Menu]): Top menu bar for PCR window.
            PCR_computed (Optional[float]): Computed PCR value.
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
        self.root.iconbitmap("Icons/PCR_icon.ico")
        self.df: pd.DataFrame = self.main_app.df
        self.PCR_frame: Optional[tk.Frame] = None
        self.menu_bar: Optional[tk.Menu] = None

        # Entered values
        self.ITC: Optional[float] = None          # experimental ITC
        self.PrCR: Optional[float] = None         # barometric coefficient
        self.MC: Optional[float] = None           # heat capacity
        self.PCR_reference: Optional[float] = None  # reference PCR, optional
        self.sigma_DRDY: Optional[float] = None   # sigma of DRDY, percent
        self.base: int = PCR_BASE_DEFAULT         # heating-rate window, s

        # Steam mode, chosen in the "Mode settings" menu. Mandatory:
        # 'With steam extraction' or 'Without steam extraction'.
        self.steam_mode: Optional[str] = None

        # NFME columns
        self.Temperature: Optional[pd.Series] = None
        self.Reactivity: Optional[pd.Series] = None
        self.Time: Optional[pd.Series] = None
        self.Pressure: Optional[pd.Series] = None
        self.Group_position: Optional[pd.Series] = None

        self.selected_columns: List[str] = []
        self.NFME_parameters: List[str] = []
        self.selected_column_buttons: Dict[str, tk.Button] = {}

        # Columns assigned to each NFME parameter (keyed by the same
        # names as NFME_parameters, e.g. "Time", "Group position").
        # Used to lock/unlock the corresponding column buttons.
        self.parameter_columns: Dict[str, List[str]] = {}

        # File headers used for every NFME parameter, keyed by attribute
        # name ('Time', 'Temperature', 'Reactivity', 'Pressure'). Lets
        # PCR_processing re-resolve the same columns by name in a new file.
        self.column_headers: Dict[str, List[str]] = {}
        self.computed_parameters: List[str] = []

    def create_PCR_window(self) -> None:
        """
        Create the PCR_module window interface.

        Initializes the frame, menu, NFME buttons, labels, entries,
        buttons, and combobox as well for selecting and obtainind parameters.
        """
        root_window = self.root.winfo_toplevel()
        root_window.config(menu=None)
        if self.PCR_frame:
            self.PCR_frame.destroy()

        self.PCR_frame = tk.Frame(self.root, bg=COLORS['BACKGROUND_COLOR'])
        self.PCR_frame.place(x=0, y=0, relwidth=1, relheight=1)
        self.root.title('PCR')
        self.create_menu()
        self.create_NFME_buttons_frame()
        self.labels()
        self.buttons()
        self.combobox()
        self.PCR_frame.update_idletasks()

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
        self.preasure_required_label = tk.Label(
            self.right_frame, text='⏱ Preasure :1',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.preasure_required_label.grid(
            row=4, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )
        self.group_position_required_label = tk.Label(
            self.right_frame, text='⏱ Group position :1',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.group_position_required_label.grid(
            row=5, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )
        self.ITC_required_label = tk.Label(
            self.right_frame, text='⏱ ITC*',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
            )
        self.ITC_required_label.grid(
            row=6, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )
        self.PrCR_required_label = tk.Label(
            self.right_frame, text='⏱ PrCR',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.PrCR_required_label.grid(
            row=7, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )
        self.MC_required_label = tk.Label(
            self.right_frame, text='⏱ MC',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.MC_required_label.grid(
            row=8, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )
        self.PCR_required_label = tk.Label(
            self.right_frame, text='⏱ PCR',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.PCR_required_label.grid(
            row=1, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )
        self.sigma_DRDY_required_label = tk.Label(
            self.right_frame, text='⏱ σ(DRDY)*',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.sigma_DRDY_required_label.grid(
            row=2, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )
        self.base_required_label = tk.Label(
            self.right_frame, text='  Base',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.base_required_label.grid(
            row=3, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )
        self.splitter_label_1 = tk.Label(
            self.right_frame, text='Enter the values:',
            font=FONTS['SPLITTER_FONT'], bg=COLORS['BACKGROUND_COLOR']
            ).grid(
                row=9, column=0, columnspan=2, sticky="w"
                )
        self.ITC_label = tk.Label(
            self.right_frame,
            text='ITC, ×10³ %/°С:',
            font=FONTS['INFO_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
            ).grid(row=10, column=0, sticky="w")
        self.ITC_entry = ttk.Entry(
            self.right_frame, font=FONTS['DATA_FONT'], width=ENTRY_WIDTH
        )
        self.ITC_entry.grid(
            row=10, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            sticky="e"
        )
        self.ITC_entry.bind(
            '<Return>',
            lambda event: self.get_entry(self.ITC_entry, 'ITC')
        )
        self.ITC_entry.focus_set()

        self.PrCR_label = tk.Label(
            self.right_frame, text='PrCR, ×10³ %/bar:',
            font=FONTS['INFO_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
            ).grid(row=11, column=0, sticky="w")
        self.PrCR_entry = ttk.Entry(
            self.right_frame, font=FONTS['DATA_FONT'], width=ENTRY_WIDTH
        )
        self.PrCR_entry.grid(
            row=11, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            sticky="e"
        )
        self.PrCR_entry.bind(
            '<Return>', lambda event: self.get_entry(self.PrCR_entry, 'PrCR')
        )

        self.MC_label = tk.Label(
            self.right_frame,
            text='MC, MWt/(°C/h):',
            font=FONTS['INFO_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
            ).grid(row=12, column=0, sticky="w")
        self.MC_entry = ttk.Entry(
            self.right_frame, font=FONTS['DATA_FONT'], width=ENTRY_WIDTH
        )
        self.MC_entry.grid(
            row=12, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            sticky="e"
        )
        self.MC_entry.bind(
            '<Return>',
            lambda event: self.get_entry(self.MC_entry, 'MC_computed')
        )

        self.PCR_computed_label = tk.Label(
            self.right_frame,
            text='PCR, ×10³ %/MWt:',
            font=FONTS['INFO_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
            ).grid(row=13, column=0, sticky="w")
        self.PCR_computed_entry = ttk.Entry(
            self.right_frame, font=FONTS['DATA_FONT'], width=ENTRY_WIDTH
        )
        self.PCR_computed_entry.grid(
            row=13, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            sticky="e"
        )
        self.PCR_computed_entry.bind(
            '<Return>',
            lambda event: self.get_entry(self.PCR_computed_entry, 'PCR_computed')
        )

        self.sigma_DRDY_label = tk.Label(
            self.right_frame,
            text='σ(DRDY)*, %:',
            font=FONTS['INFO_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
            ).grid(row=14, column=0, sticky="w")
        self.sigma_DRDY_entry = ttk.Entry(
            self.right_frame, font=FONTS['DATA_FONT'], width=ENTRY_WIDTH
        )
        self.sigma_DRDY_entry.grid(
            row=14, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            sticky="e"
        )
        self.sigma_DRDY_entry.bind(
            '<Return>',
            lambda event: self.get_entry(self.sigma_DRDY_entry, 'sigma_DRDY')
        )
        self.base_label = tk.Label(
            self.right_frame,
            text='base, s:',
            font=FONTS['INFO_FONT'],
            bg=COLORS['BACKGROUND_COLOR']
            ).grid(row=15, column=0, sticky="w")
        self.base_entry = ttk.Entry(
            self.right_frame, font=FONTS['DATA_FONT'], width=ENTRY_WIDTH
        )
        self.base_entry.grid(
            row=15, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            sticky="e"
        )
        self.base_entry.insert(0, str(PCR_BASE_DEFAULT))
        self.base_entry.bind(
            '<Return>',
            lambda event: self.get_entry(self.base_entry, 'base')
        )

        # Steam mode indicator, a couple of rows below the optional
        # parameters. Starts as a clock; turns into a tick once chosen.
        self.steam_mode_label = tk.Label(
            self.right_frame,
            text='⏱ Mode:',
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.steam_mode_label.grid(
            row=6, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_2'],
            sticky="w"
        )

        self.splitter_label_2 = tk.Label(
            self.right_frame,
            text='* - experimental ITC and σ(DRDY) values are expected',
            font=FONTS['SPLITTER_FONT'], bg=COLORS['BACKGROUND_COLOR'],
            justify="left", anchor="w"
        )
        self.splitter_label_2.grid(
            row=16, column=0, columnspan=2, sticky="w"
        )

    def buttons(self) -> None:
        """
        Create buttons for obtaining parameters and program buttons.

        Includes buttons for DTC, MTC, ITC, DRDY, boric acid, DYDT,
        START button, BACK button, INFO button and NFME parameters
        buttons as well.
        """
        self.get_ITC_button = TestButtons(
              self.right_frame,
              text='Get the ITC',
              command=lambda: self.get_entry(self.ITC_entry, 'ITC'),
        )
        self.get_ITC_button.grid(
            row=10, column=1,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'],
            sticky="w"
        )
        self.get_PrCR_button = TestButtons(
              self.right_frame,
              text='Get the PrCR',
              command=lambda: self.get_entry(self.PrCR_entry, 'PrCR'),
        )
        self.get_PrCR_button.grid(
            row=11, column=1,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'],
            sticky="w"
        )
        self.get_MC_button = TestButtons(
              self.right_frame,
              text='Get the MC',
              command=lambda: self.get_entry(self.MC_entry, 'MC_computed'),
        )
        self.get_MC_button.grid(
            row=12, column=1,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'],
            sticky="w"
        )
        self.get_PCR_button = TestButtons(
              self.right_frame,
              text='Get the PCR',
              command=lambda: self.get_entry(
                  self.PCR_computed_entry, 'PCR_computed'
              ),
        )
        self.get_PCR_button.grid(
            row=13, column=1,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'],
            sticky="w"
        )
        self.get_sigma_DRDY_button = TestButtons(
              self.right_frame,
              text='Get the σ(DRDY)',
              command=lambda: self.get_entry(
                  self.sigma_DRDY_entry, 'sigma_DRDY'
              ),
        )
        self.get_sigma_DRDY_button.grid(
            row=14, column=1,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'],
            sticky="w"
        )
        self.get_base_button = TestButtons(
              self.right_frame,
              text='Get the base',
              command=lambda: self.get_entry(self.base_entry, 'base'),
        )
        self.get_base_button.grid(
            row=15, column=1,
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
            row=17, column=1,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'],
            sticky="w"
        )
        self.START_button = TestButtons(
              self.right_frame,
              text='START',
              command=self.start_PCR,
        )
        self.START_button.grid(
            row=18, column=0,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'],
            sticky="w"
        )
        self.BACK_button = MainButtons(
              self.right_frame,
              text='<< BACK',
              command=lambda: self.back(self.PCR_frame),
        )
        self.BACK_button.grid(
            row=18, column=1,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10'],
            sticky="w"
        )
        self.INFO_button = MainButtons(
              self.right_frame,
              text='User guide',
              command=lambda: show_info(self.root, "PCR/info_module.txt"),
        )
        self.INFO_button.grid(
            row=19, column=1,
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
                "Pressure",
                "Group position"
                ],
            state="readonly",
            width=20,
            font=FONTS['TEXT_FONT']
        )
        self.parameter_combobox.grid(
            row=17, column=0,
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
            command=lambda: show_info(self.root, "PCR/info_module.txt")
        )

        # Steam mode - mandatory, chosen here. Same side-submenu pattern as
        # the movement type of DRDH_module.
        mode_settings = tk.Menu(self.menu_bar, tearoff=1)
        self.menu_bar.add_cascade(label="Mode settings", menu=mode_settings)

        steam_menu = tk.Menu(mode_settings, tearoff=0)
        mode_settings.add_cascade(
            label="Steam mode",
            font=FONTS['DATA_FONT'],
            menu=steam_menu
        )

        # Empty until the user chooses: neither option is ticked
        self.steam_mode_var = tk.StringVar(value="")

        for option in (
            "With steam extraction",
            "Without steam extraction",
        ):
            steam_menu.add_radiobutton(
                label=option,
                font=FONTS['DATA_FONT'],
                value=option,
                variable=self.steam_mode_var,
                command=self.set_steam_mode
            )

        steam_menu.add_separator()
        steam_menu.add_command(
            label="Not selected",
            font=FONTS['DATA_FONT'],
            command=self.clear_steam_mode
        )

    def set_steam_mode(self) -> None:
        """Store the steam mode chosen in the menu and update the label."""
        self.steam_mode = self.steam_mode_var.get() or None
        self.update_steam_mode_label()

    def clear_steam_mode(self) -> None:
        """Reset the steam mode back to 'Not selected'."""
        self.steam_mode_var.set("")
        self.steam_mode = None
        self.update_steam_mode_label()

    def update_steam_mode_label(self) -> None:
        """Reflect the steam mode next to its on-screen label."""
        if not hasattr(self, "steam_mode_label"):
            return

        if self.steam_mode is None:
            self.steam_mode_label.config(text="⏱ Mode:")
        else:
            self.steam_mode_label.config(text=f"✓ Mode: {self.steam_mode}")

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
        getattr(self, attr_name).clear()
        if attr_name == 'NFME_parameters':
            self.reset_parameters('NFME')
            for columns in self.parameter_columns.values():
                self.set_column_buttons_state(columns, disabled=False)
            self.parameter_columns.clear()

            self.time_required_label.config(text="⏱ Time :1")
            self.temparature_required_label.config(text="⏱ Temperature")
            self.reactivity_required_label.config(text="⏱ Reactivity :2")
            self.preasure_required_label.config(text="⏱ Preasure :1")

        elif attr_name == 'computed_parameters':
            self.reset_parameters('computed')
            self.reset_entry(
                self.ITC_entry, self.PrCR_entry, self.MC_entry,
                self.PCR_computed_entry, self.sigma_DRDY_entry,
                self.base_entry
            )
            self.ITC_entry.focus_set()
            self.base_entry.insert(0, str(PCR_BASE_DEFAULT))

            self.ITC_required_label.config(text='⏱ ITC*')
            self.PrCR_required_label.config(text='⏱ PrCR')
            self.MC_required_label.config(text='⏱ MC')
            self.PCR_required_label.config(text='⏱ PCR')
            self.sigma_DRDY_required_label.config(text='⏱ σ(DRDY)*')
            self.base_required_label.config(text='  Base')

        if listbox is not None:
            listbox.delete(0, tk.END)

    def clear_last_parameter(self) -> None:
        """
        Remove the last parameter from currently chosen NFME parameters.
        """
        if self.selected_columns:
            _ = self.selected_columns.pop()

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
                removed_columns = self.parameter_columns.pop(
                    params[index], None
                )
                if removed_columns:
                    self.set_column_buttons_state(
                        removed_columns, disabled=False
                    )
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

            if 'Pressure' not in remaining_params:
                self.preasure_required_label.config(
                    text="⏱ Preasure :1"
                )

        elif attr_name == 'computed_parameters':

            for param in removed_params:
                if param == 'ITC':
                    self.ITC = None
                    self.ITC_required_label.config(text='⏱ ITC*')
                    self.ITC_entry.delete(0, tk.END)
                elif param == 'PrCR':
                    self.PrCR = None
                    self.PrCR_required_label.config(text='⏱ PrCR')
                    self.PrCR_entry.delete(0, tk.END)
                elif param == 'MC_computed':
                    self.MC = None
                    self.MC_required_label.config(text='⏱ MC')
                    self.MC_entry.delete(0, tk.END)
                elif param == 'PCR_computed':
                    self.PCR_reference = None
                    self.PCR_required_label.config(text='⏱ PCR')
                    self.PCR_computed_entry.delete(0, tk.END)
                elif param == 'sigma_DRDY':
                    self.sigma_DRDY = None
                    self.sigma_DRDY_required_label.config(text='⏱ σ(DRDY)*')
                    self.sigma_DRDY_entry.delete(0, tk.END)
                elif param == 'base':
                    self.base = PCR_BASE_DEFAULT
                    self.base_required_label.config(text='  Base')
                    self.base_entry.delete(0, tk.END)
                    self.base_entry.insert(0, str(PCR_BASE_DEFAULT))

    def start_PCR(self) -> None:
        """
        Launch PCR computation process.

        Checks that every mandatory parameter is set - including the steam
        mode, which has to be chosen in the menu; if something is missing,
        shows a warning. Initializes the PCR_processing window.
        """
        missing_parameters = []

        if self.Time is None:
            missing_parameters.append("Time")
        if self.Temperature is None:
            missing_parameters.append("Temperature")
        if self.Reactivity is None:
            missing_parameters.append("Reactivity")
        if self.Pressure is None:
            missing_parameters.append("Pressure")
        if self.Group_position is None:
            missing_parameters.append("Group position")
        if self.ITC is None:
            missing_parameters.append("ITC")
        if self.PrCR is None:
            missing_parameters.append("PrCR")
        if self.MC is None:
            missing_parameters.append("MC")
        if self.steam_mode is None:
            missing_parameters.append("Steam mode")

        if missing_parameters:
            if len(missing_parameters) == 1:
                Messages.show(
                    "warning", "MISSING_PARAMS",
                    param=missing_parameters[0], test='PCR'
                )
            else:
                params = "\n".join(f"• {p}" for p in missing_parameters)
                Messages.show(
                    "warning", "MISSING_PARAMS",
                    params=params, test='PCR'
                )
            return
        self.PCR_processing_interface = PCR_processing(self.PCR_frame, self)
        self.PCR_processing_interface.create_PCR_processing_window()

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
            "Pressure": {
                "columns": 1,
                "range": RANGES_EXPECTED['PRESSURE_RANGE'],
                "allow_exp": False,
                "attr": "Pressure",
                "label": lambda self: self.preasure_required_label,
                "label_text": "✓ Pressure :1"
            },
            "Temperature": {
                "columns": None,
                "range": RANGES_EXPECTED['TEMPERATURE_RANGE'],
                "allow_exp": False,
                "attr": "Temperature",
                "label": lambda self: self.temparature_required_label,
                "label_text": "✓ Temperature"
            },
            "Group position": {
                "columns": 1,
                "range": RANGES_EXPECTED['GROUP_POSITION_RANGE'],
                "allow_exp": False,
                "attr": "Group_position",
                "label": lambda self: self.group_position_required_label,
                "label_text": "✓ Group position :1"
            },
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

        # Remember which file headers were used for this NFME parameter,
        # so PCR_processing can re-resolve them by name in another file.
        self.column_headers[rules["attr"]] = list(self.selected_columns)
        self.parameter_columns[selected_param] = list(self.selected_columns)

        label = rules["label"](self)
        label.config(text=rules["label_text"])

        if selected_param not in self.NFME_parameters:
            self.NFME_parameters.append(selected_param)

        # Columns just assigned to a parameter become locked: visually
        # and functionally unavailable until the parameter is cleared.
        self.set_column_buttons_state(self.selected_columns, disabled=True)
        self.selected_columns.clear()

    def get_entry(self, entry, value_name: str) -> None:
        """
        Obtain a computed parameter via entry field.

        Args:
            entry (ttk.Entry): Entry widget contains user input value.
            value_name (str): Name of the parameter ('ITC', 'PrCR',
                              'MC_computed', 'PCR_computed', or 'base').

        Check whether the parameter complies with the requirements.
        Updates corresponding attribute and UI label.
        """
        VALUES_RULES: dict[str, dict[str, Any]] = {
            "ITC": {
                "attr": "ITC",
                "label": lambda self: self.ITC_required_label,
                "label_text": "✓ ITC",
                "sign": "negative"
            },
            "PrCR": {
                "attr": "PrCR",
                "label": lambda self: self.PrCR_required_label,
                "label_text": "✓ PrCR",
                "sign": "positive"
            },
            "MC_computed": {
                "attr": "MC",
                "label": lambda self: self.MC_required_label,
                "label_text": "✓ MC",
                "sign": "positive"
            },
            "PCR_computed": {
                "attr": "PCR_reference",
                "label": lambda self: self.PCR_required_label,
                "label_text": "✓ PCR",
                "sign": "negative"
            },
            "sigma_DRDY": {
                "attr": "sigma_DRDY",
                "label": lambda self: self.sigma_DRDY_required_label,
                "label_text": "✓ σ(DRDY)*",
                "sign": "positive"
            },
            "base": {
                "attr": "base",
                "label": lambda self: self.base_required_label,
                "label_text": "✓ Base",
                "sign": "range",
                "range": PCR_BASE_RANGE
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

        if rules["sign"] == "range":
            low, high = rules["range"]
            if not (low <= numeric_value <= high):
                Messages.show(
                    "warning", "BASE_OUT_OF_RANGE",
                    value=value_name, low=low, high=high
                )
                self.reset_entry(entry)
                return
            numeric_value = int(round(numeric_value))

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
        """
        Reset visual selection of currently selected NFME column buttons.

        Only touches columns picked but not yet assigned to a parameter
        (self.selected_columns); buttons already locked to a parameter
        are left untouched (see set_column_buttons_state).
        """
        for column_name in self.selected_columns:
            button = self.selected_column_buttons.get(column_name)
            if button:
                button.config(
                    relief=tk.RAISED,
                    bd=2
                )

        self.selected_columns.clear()

    def set_column_buttons_state(
            self,
            columns: List[str],
            disabled: bool
    ) -> None:
        """
        Enable or disable NFME column buttons for the given column names.

        Args:
            columns (List[str]): Column names to update.
            disabled (bool): True to lock the buttons (column already
                assigned to a parameter), False to make them clickable
                again (parameter cleared).
        """
        for column_name in columns:
            button = self.selected_column_buttons.get(column_name)
            if not button:
                continue
            if disabled:
                button.config(state=tk.DISABLED, relief=tk.SUNKEN, bd=2)
            else:
                button.config(state=tk.NORMAL, relief=tk.RAISED, bd=2)

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
            self.Pressure = None
            self.Group_position = None
            self.column_headers = {}
        if 'computed' in args:
            self.ITC = None
            self.PrCR = None
            self.MC = None
            self.PCR_reference = None
            self.sigma_DRDY = None
            self.base = PCR_BASE_DEFAULT

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
        self.selected_columns = []
        self.NFME_parameters = []
        self.computed_parameters = []
        self.parameter_columns.clear()

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
            self.PCR_frame,
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
            text="PCR Module",
            font=FONTS['TITLE_FONT'],
            bg=COLORS['BACKGROUND_COLOR'],
            anchor='center'
        )
        self.header_label.grid(row=0, column=0)

        self.left_header = tk.Frame(
            self.PCR_frame,
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
            self.PCR_frame,
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
            self.PCR_frame,
            bg=COLORS['PARAMETERS_BACKGROUND_COLOR'],
            highlightthickness=0,
            width=LEFT_CANVAS_WIDTH
        )

        self.right_canvas = tk.Canvas(
            self.PCR_frame,
            bg=COLORS['BACKGROUND_COLOR'],
            highlightthickness=0
        )

        right_scrollbar = ttk.Scrollbar(
            self.PCR_frame,
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
            self.PCR_frame,
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
                padx=GAPS['GAPS_X']['PAD_X_5'], pady=GAPS['GAPS_Y']['PAD_Y_2']
            )

        # Updating the scrolling area after adding all buttons
        buttons_frame.update_idletasks()
        self.left_canvas.config(scrollregion=self.left_canvas.bbox("all"))

        self.PCR_frame.grid_rowconfigure(2, weight=1)
        self.PCR_frame.grid_columnconfigure(0, weight=0)
        self.PCR_frame.grid_columnconfigure(1, weight=1)

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