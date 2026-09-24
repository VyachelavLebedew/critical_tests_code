import tkinter as tk
from tkinter import ttk
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
        show_selected_parameters: Represent parameters (current, NFME,
        computed) chosen.
        clear_all_parameters: Clear all parameters from a given attribute list.
        clear_last_parameter: Remove the last item from currently chosen
        NFME parameters.
        clear_selected_parameters: Clear selected parameters from a listbox.
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
        self.overlap: float = 50
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

    def create_DRDH_window(self) -> None:
        """
        Create the DRDH_module window interface.

        Initializes the frame, menu, NFME buttons, labels, entries,
        buttons, and combobox as well for selecting and obtainind parameters.
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

    def set_movement_type(self) -> None:
        """Store the movement type chosen in the menu."""
        self.movement_type = self.movement_type_var.get() or None

    def clear_movement_type(self) -> None:
        """Drop the movement type: it is an optional setting."""
        self.movement_type_var.set("")
        self.movement_type = None

    def switch_groups_amount(self) -> None:
        """Switch between 12 and 10 control groups."""

        if self.groups_count == 12:
            self.groups_count = 10
        else:
            self.groups_count = 12

        if self.groups_count == 10:
            # H12 label binds H10 group
            self.H12_position_required_label.config(text='⏱ H₁₀ :1')

            self.H11_position_required_label.config(text='')
            self.H10_position_required_label.config(text='')

            values = list(self.parameter_combobox["values"])
            values = [v for v in values if v not in ("12 Group position", "11 Group position")]
            self.parameter_combobox["values"] = values

            self.groups_mode_label.config(text="10 groups mode")

        else:
            self.H12_position_required_label.config(text='⏱ H₁₂ :1')

            self.H11_position_required_label.config(text='⏱ H₁₁ :1')
            self.H10_position_required_label.config(text='⏱ H₁₀ :1')

            self.parameter_combobox["values"] = [
                "Not selected",
                "Time",
                "Reactivity",
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
            ]

            self.groups_mode_label.config(text="12 groups mode")

    def create_menu(self) -> None:
        """
        Create the top menu bar for DRDH_module window.

        Menu includes:
            - Currently chosen buttons
            - NFME parameters (chosen)
            - Computed parameters (entered)
            - INFO
            - Groups amount setting
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

        # Starts empty: neither option is ticked until the user chooses
        self.movement_type_var = tk.StringVar(value="")

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
            self.clear_selected_column_buttons()

            self.time_required_label.config(text="⏱ Time :1")
            self.reactivity_required_label.config(text="⏱ Reactivity :2")
            if self.groups_count == 12:
                self.H12_position_required_label.config(text="⏱ H₁₂ :1")
            else:
                self.H12_position_required_label.config(text="⏱ H₁₀ :1")
            self.boric_acid_start_required_label.config(
                text="⏱ С(H₃BO₃) initial"
            )
            self.boric_acid_finish_required_label.config(
                text="⏱ С(H₃BO₃) final"
            )
            if self.groups_count == 12:
                self.H11_position_required_label.config(text="⏱ H₁₁ :1")
                self.H10_position_required_label.config(text="⏱ H₁₀ :1")
            else:
                self.H11_position_required_label.config(text="")
                self.H10_position_required_label.config(text="")
            self.H9_position_required_label.config(text="⏱ H₉ :1")
            self.H8_position_required_label.config(text="⏱ H₈ :1")
            self.H7_position_required_label.config(text="⏱ H₇ :1")
            self.H6_position_required_label.config(text="⏱ H₆ :1")
            self.H5_position_required_label.config(text="⏱ H₅ :1")
            self.H4_position_required_label.config(text="⏱ H₄ :1")
            self.H3_position_required_label.config(text="⏱ H₃ :1")
            self.H2_position_required_label.config(text="⏱ H₂ :1")
            self.H1_position_required_label.config(text="⏱ H₁ :1")

        elif attr_name == 'computed_parameters':
            self.reset_parameters('computed')

            self.DRDC_entry.delete(0, tk.END)
            self.DRDC_required_label.config(text='⏱ DRDC')
            self.boric_acid_finish_entry.delete(0, tk.END)
            self.boric_acid_finish_required_label.config(
                text='⏱ С(H₃BO₃) final'
            )
            self.boric_acid_start_entry.delete(0, tk.END)
            self.boric_acid_start_required_label.config(
                text='⏱ С(H₃BO₃) initial'
            )

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

            if 'Reactivity' not in remaining_params:
                self.reactivity_required_label.config(text="⏱ Reactivity :2")

            if 'Boric acid concentration' not in remaining_params:
                self.boric_acid_NFME = None
                self.boric_acid_NFME_required_label.config(text="⏱ Boric acid :2")

            for num, attr_name_group in GROUP_MAP.items():
                param_name = f"{num} Group position"

                if param_name not in remaining_params:
                    setattr(self, attr_name_group, None)

                    label_attr = f"H{num}_position_required_label"
                    label = getattr(self, label_attr, None)
                    if label:
                        label.config(text=f"⏱ H{num} :1")

        elif attr_name == 'computed_parameters':

            for param in removed_params:
                if param == 'DRDC':
                    self.DRDC = None
                    self.DRDC_required_label.config(text='⏱ DRDC')
                    self.DRDC_entry.delete(0, tk.END)
                elif param == 'boric_acid_start':
                    self.boric_acid_start = None
                    self.boric_acid_start_entry.delete(0, tk.END)
                    self.boric_acid_start_required_label.config(
                        text="⏱ С(H₃BO₃) initial"
                    )
                elif param == 'boric_acid_finish':
                    self.boric_acid_finish = None
                    self.boric_acid_finish_entry.delete(0, tk.END)
                    self.boric_acid_finish_required_label.config(
                        text="⏱ С(H₃BO₃) final"
                    )

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

        self.DRDH_processing_interface = DRDH_processing(self.DRDH_frame, self)
        self.DRDH_processing_interface.create_DRDH_processing_window()

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
                "label_text": "✓ Time :1"
            },
            "Reactivity": {
                "columns": 2,
                "range": RANGES_EXPECTED['REACTIVITY_RANGE'],
                "allow_exp": False,
                "attr": "Reactivity",
                "label": lambda self: self.reactivity_required_label,
                "label_text": "✓ Reactivity :2"
            },
            "Boric acid concentration": {
                "columns": 2,
                "range": RANGES_EXPECTED['BORIC_ACID_RANGE'],
                "allow_exp": False,
                "attr": "boric_acid_NFME",
                "label": lambda self: self.boric_acid_NFME_required_label,
                "label_text": "✓ Boric acid :2"
            },
            "12 Group position": {
                "columns": 1,
                "range": RANGES_EXPECTED['GROUP_POSITION_RANGE'],
                "allow_exp": False,
                "attr": "H12_position",
                "label": lambda self: self.H12_position_required_label,
                "label_text": "✓ H₁₂ :1"
            },
            "11 Group position": {
                "columns": 1,
                "range": RANGES_EXPECTED['GROUP_POSITION_RANGE'],
                "allow_exp": False,
                "attr": "H11_position",
                "label": lambda self: self.H11_position_required_label,
                "label_text": "✓ H₁₁ :1"
            },
            "10 Group position": {
                "columns": 1,
                "range": RANGES_EXPECTED['GROUP_POSITION_RANGE'],
                "allow_exp": False,
                "attr": "H10_position",
                "label": lambda self: (
                    self.H12_position_required_label
                    if self.groups_count == 10
                    else self.H10_position_required_label
                ),
                "label_text": "✓ H₁₀ :1"
            },
            "9 Group position": {
                "columns": 1,
                "range": RANGES_EXPECTED['GROUP_POSITION_RANGE'],
                "allow_exp": False,
                "attr": "H9_position",
                "label": lambda self: self.H9_position_required_label,
                "label_text": "✓ H₉ :1"
            },
            "8 Group position": {
                "columns": 1,
                "range": RANGES_EXPECTED['GROUP_POSITION_RANGE'],
                "allow_exp": False,
                "attr": "H8_position",
                "label": lambda self: self.H8_position_required_label,
                "label_text": "✓ H₈ :1"
            },
            "7 Group position": {
                "columns": 1,
                "range": RANGES_EXPECTED['GROUP_POSITION_RANGE'],
                "allow_exp": False,
                "attr": "H7_position",
                "label": lambda self: self.H7_position_required_label,
                "label_text": "✓ H₇ :1"
            },
            "6 Group position": {
                "columns": 1,
                "range": RANGES_EXPECTED['GROUP_POSITION_RANGE'],
                "allow_exp": False,
                "attr": "H6_position",
                "label": lambda self: self.H6_position_required_label,
                "label_text": "✓ H₆ :1"
            },
            "5 Group position": {
                "columns": 1,
                "range": RANGES_EXPECTED['GROUP_POSITION_RANGE'],
                "allow_exp": False,
                "attr": "H5_position",
                "label": lambda self: self.H5_position_required_label,
                "label_text": "✓ H₅ :1"
            },
            "4 Group position": {
                "columns": 1,
                "range": RANGES_EXPECTED['GROUP_POSITION_RANGE'],
                "allow_exp": False,
                "attr": "H4_position",
                "label": lambda self: self.H4_position_required_label,
                "label_text": "✓ H₄ :1"
            },
            "3 Group position": {
                "columns": 1,
                "range": RANGES_EXPECTED['GROUP_POSITION_RANGE'],
                "allow_exp": False,
                "attr": "H3_position",
                "label": lambda self: self.H3_position_required_label,
                "label_text": "✓ H₃ :1"
            },
            "2 Group position": {
                "columns": 1,
                "range": RANGES_EXPECTED['GROUP_POSITION_RANGE'],
                "allow_exp": False,
                "attr": "H2_position",
                "label": lambda self: self.H2_position_required_label,
                "label_text": "✓ H₂ :1"
            },
            "1 Group position": {
                "columns": 1,
                "range": RANGES_EXPECTED['GROUP_POSITION_RANGE'],
                "allow_exp": False,
                "attr": "H1_position",
                "label": lambda self: self.H1_position_required_label,
                "label_text": "✓ H₁ :1"
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

        # Remember which NFME columns were assigned to this parameter.
        self.parameter_columns[selected_param] = self.selected_columns.copy()

        label = rules["label"](self)
        label.config(text=rules["label_text"])

        if selected_param not in self.NFME_parameters:
            self.NFME_parameters.append(selected_param)

        # Columns just assigned to a parameter become locked: visually
        # and functionally unavailable until the parameter is cleared.
        self.set_column_buttons_state(self.selected_columns, disabled=True)
        self.selected_columns.clear()

    def reset_required_parameter_label(self, parameter: str) -> None:
        """Reset a required parameter label and its assigned columns."""

        self.parameter_columns.pop(parameter, None)

        label_map = {
            "Time": self.time_required_label,
            "Reactivity": self.reactivity_required_label,
            "Boric acid concentration": self.boric_acid_NFME_required_label,
            "12 Group position": self.H12_position_required_label,
            "11 Group position": self.H11_position_required_label,
            "10 Group position": (
                self.H12_position_required_label
                if self.groups_count == 10
                else self.H10_position_required_label
            ),
            "9 Group position": self.H9_position_required_label,
            "8 Group position": self.H8_position_required_label,
            "7 Group position": self.H7_position_required_label,
            "6 Group position": self.H6_position_required_label,
            "5 Group position": self.H5_position_required_label,
            "4 Group position": self.H4_position_required_label,
            "3 Group position": self.H3_position_required_label,
            "2 Group position": self.H2_position_required_label,
            "1 Group position": self.H1_position_required_label,
        }

        default_text = {
            "Time": "⏱ Time :1",
            "Reactivity": "⏱ Reactivity :2",
            "Boric acid concentration": "⏱ Boric acid :2",
            "12 Group position": "⏱ H₁₂ :1",
            "11 Group position": "⏱ H₁₁ :1",
            "10 Group position": "⏱ H₁₀ :1",
            "9 Group position": "⏱ H₉ :1",
            "8 Group position": "⏱ H₈ :1",
            "7 Group position": "⏱ H₇ :1",
            "6 Group position": "⏱ H₆ :1",
            "5 Group position": "⏱ H₅ :1",
            "4 Group position": "⏱ H₄ :1",
            "3 Group position": "⏱ H₃ :1",
            "2 Group position": "⏱ H₂ :1",
            "1 Group position": "⏱ H₁ :1",
        }

        label = label_map.get(parameter)
        if label:
            label.config(text=default_text[parameter])
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
            columns: list[str],
            disabled: bool
    ) -> None:
        """
        Enable or disable NFME column buttons for the given column names.

        Args:
            columns (list[str]): Column names to update.
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
        if 'computed' in args:
            self.DRDC = None
            self.boric_acid_start = None
            self.boric_acid_finish = None

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
        Create the NFME buttons field in the DRDH frame.

        Adds scrollbars for both fields.
        """
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