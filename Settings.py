import os
import tkinter as tk
from openpyxl.styles import Font
from typing import Any, Dict, Tuple, Union, cast

# DRDH_processing, plot appearance
PLOT_STYLE: Dict[str, Any] = {
    # Base curves
    'REACTIVITY_COLOR': "#1F4E79",   # reactivity curve
    'REACTIVITY_WIDTH': 1.4,
    'GROUP_WIDTH': 1.0,              # group position curves
    'GROUP_ALPHA': 0.75,
    'GRID_COLOR': "#DCE2E8",
    'GRID_WIDTH': 0.6,

    # Clicked points (left / right of an interval)
    'POINT_SIZE': 46,
    'POINT_COLOR': "#F2B134",
    'POINT_EDGE': "#6B4E12",
    'POINT_EDGE_WIDTH': 1.1,

    # Active interval line (the "yellow" one)
    'ACTIVE_LINE_COLOR': "#F2B134",
    'ACTIVE_LINE_WIDTH': 1.8,
    'ACTIVE_LINE_ALPHA': 0.95,
    'ACTIVE_LINE_ZORDER': 6,

    # Measured interval line (the "black" one)
    'FINISHED_LINE_COLOR': "#2F3640",
    'FINISHED_LINE_WIDTH': 1.3,
    'FINISHED_LINE_ALPHA': 0.85,
    'FINISHED_LINE_ZORDER': 5,

    # Vertical line of the group movement (the "red" one)
    'MOVE_LINE_COLOR': "#D64545",
    'MOVE_LINE_WIDTH': 1.5,
    'MOVE_LINE_ALPHA': 0.90,
    'MOVE_LINE_ZORDER': 8,

    # Intersection points (the "green" ones)
    'INTERSECTION_SIZE': 58,
    'INTERSECTION_COLOR': "#2E9E5B",
    'INTERSECTION_EDGE': "#FFFFFF",
    'INTERSECTION_EDGE_WIDTH': 1.2,
    'INTERSECTION_ZORDER': 11,
}

# Colors
COLORS: Dict[str, str] = {
    'PARAMETERS_BACKGROUND_COLOR': "#ffffff",
    'BACKGROUND_COLOR': "#ffedc0",
    'FOREGROUND_COLOR': "#454545",
    'MAIN_BUTTON_COLOR': "#E7C6C6",
    'TEST_BUTTON_COLOR': "#C6CEE7"
}

# Fonts
FONTS: Dict[str, Union[Tuple[str, int, str], Tuple[str, int], Font]] = {
    'HEADING_FONT': ("Times New Roman", 10, "bold"),
    'DATA_FONT': ("Times New Roman", 10),
    'BUTTON_FONT': ("Times New Roman", 12, "bold"),
    'TEXT_FONT': ("Times New Roman", 12, "bold"),
    'PARAMETER_FONT': ("Times New Roman", 15, "underline"),
    'TITLE_FONT': ("Times New Roman", 20, "bold"),
    'INFO_FONT': ("Times New Roman", 12),
    'SPLITTER_FONT': ("Times New Roman", 12, "underline"),
    'PLOT_FONT': ("Times New Roman", 11),
    'EXCEL_FONT': Font(name="Times New Roman", size=12)
}

# Gaps and spaces
GAPS: Dict[str, Dict[str, Union[int, Tuple[int, int]]]] = {
    'GAPS_Y': {
        'PAD_Y_2': 2,
        'PAD_Y_5': 5,
        'PAD_Y_10': 10,
        'PAD_Y_0_5': (0, 5),
        'PAD_Y_5_0': (5, 0),
        'PAD_Y_0_10': (0, 10),
        'PAD_Y_10_5': (10, 5),
        'PAD_Y_10_20': (10, 20)
    },
    'GAPS_X': {
        'PAD_X_5': 5,
        'PAD_X_10': 10,
        'PAD_X_0_10': (0, 10),
        'PAD_X_10_15': (10, 15),
        'PAD_X_10_30': (10, 30),
        'PAD_X_40_20': (40, 20)
    }
}

# Decimal, in ITC_Processing window
DECIMAL: Dict[str, int] = {
    'DECIMAL': 3,
    'DECIMAL_REACT': 3,
    'DECIMAL_TEMP': 2,
    'DECIMAL_GROUP': 2,

    # DRDH_processing. In Beff/cm the DRDH is a small number,
    # hence more decimals than for the rest.
    'DECIMAL_DRDH': 3,
    'DECIMAL_DRDC': 3,
    'DECIMAL_BORIC': 3
}

# Encodings available
ENCODINGS: list[str] = ["utf-8-sig", "cp1251", "cp1252", "utf-8", "latin-1"]

# Data ranges expected
# PCR constants
PCR_BASE_RANGE: Tuple[int, int] = (10, 300)  # base window range, seconds
PCR_BASE_DEFAULT: int = 60  # default base, seconds

# PCR uncertainty constants (methodology). Used by PCR_processing.
PCR_SIGMA: Dict[str, float] = {
    'SIGMA_ALPHA_T': 1.5,     # sigma of ITC, pcm/degC
    'SIGMA_DT': 0.1,          # sigma of temperature change, degC
    'SIGMA_DP': 0.01,         # sigma of pressure change (file unit)
    'SIGMA_MC_REL': 0.10,     # relative sigma of MC
    'SIGMA_V_REL': 0.10,      # relative sigma of a heating rate
    'SIGMA_RHO_REL': 0.05,    # relative sigma of the reactivity difference
}


# Approach-to-criticality polynomial coefficients (from the Excel
# calculator). Each list is [c6, c5, c4, c3, c2, c1, c0] for a
# 6th-degree polynomial in the given argument.
CRITICALITY_POLY: Dict[str, list] = {
    # primary-circuit water density from T, kg/m3
    'DENSITY_WATER': [
        -2.10489403684733e-11,
        3.07198231297434e-08,
        -1.85520856677002e-05,
        0.00589503700048866,
        -1.0341974949806,
        93.1849009612733,
        -2348.13761261558
    ],
    # purge water density from T, kg/m3
    'DENSITY_PURGE': [
        -2.02708327554091e-11,
        7.38812466760663e-09,
        -1.16632290314556e-06,
        0.000110728418803774,
        -0.00969981038360856,
        0.0781587505480275,
        999.82821692116
    ],
    # insertion: reactivity from sum of H10+H11+H12, %
    'INS_DR': [
        -2.29129173230558e-13,
        2.32464456560826e-10,
        -9.29918776172723e-08,
        1.86201413953964e-05,
        -0.00197958107533173,
        0.117983160189831,
        -4.68786635486164
    ],
    # insertion: boric acid conc. from sum of positions, g/kg
    'INS_C': [
        -1.41163281266009e-13,
        1.42310315163399e-10,
        -5.65030547395809e-08,
        1.1211531122664e-05,
        -0.00117867617151589,
        0.069414936703609,
        5.20089896550529
    ],
    # insertion: dr/dC from sum of positions
    'INS_DRDC': [
        -5.8120629785538e-15,
        6.85873786164577e-12,
        -3.18492746448932e-09,
        7.39913020688543e-07,
        -9.11148866250755e-05,
        0.00581955046546373,
        -2.01281846147128
    ],
    # extraction H10: reactivity from position
    'EXT_DR_H10': [
        6.1466467302425e-13,
        -1.58991031535015e-09,
        4.62866869734145e-07,
        -5.28525573176493e-05,
        0.00258189278152094,
        -0.0274274838261835,
        -1.23150256930619
    ],
    # extraction H10: conc. from position
    'EXT_C_H10': [
        1.22445986455635e-12,
        -1.22185248041268e-09,
        3.06300525283959e-07,
        -3.2770965997516e-05,
        0.00154471013210364,
        -0.0159620585224949,
        6.39078952589704
    ],
    # extraction H10: dr/dC from position
    'EXT_DRDC_H10': [
        -1.10014504991213e-12,
        3.47832180067872e-10,
        -3.999533637888e-08,
        1.87738933207988e-06,
        -2.35171848508533e-05,
        0.000252505462973594,
        -1.89937048171777
    ],
    # extraction H11: reactivity from position
    'EXT_DR_H11': [
        -9.27147663588239e-12,
        2.33496727004285e-09,
        -1.42599737484697e-07,
        -7.87400054318182e-06,
        0.00102252457866264,
        -0.0117229563645507,
        -1.00216676978571
    ],
    # extraction H11: conc. from position
    'EXT_C_H11': [
        -5.36449457616127e-12,
        1.31462800480396e-09,
        -7.13696373700896e-08,
        -5.78901474951798e-06,
        0.000649145915957855,
        -0.00758164553590584,
        7.1388316016774
    ],
    # extraction H11: dr/dC from position
    'EXT_DRDC_H11': [
        -7.52722899608578e-13,
        2.88567907335288e-10,
        -4.23356101024908e-08,
        2.89967437683541e-06,
        -8.89394895251432e-05,
        0.00105027477705408,
        -1.85656950690434
    ],
    # extraction H12: reactivity from position
    'EXT_DR_H12': [
        -7.13670282131477e-12,
        2.34494086479216e-09,
        -2.85314057678999e-07,
        1.46117435806757e-05,
        -0.000227678972909982,
        0.00269268875445101,
        -0.387415491126094
    ],
    # extraction H12: conc. from position
    'EXT_C_H12': [
        -1.99819959637395e-12,
        6.79913329495107e-10,
        -8.12884717354598e-08,
        3.35304199026738e-06,
        2.41846324719403e-05,
        -0.000477060005388531,
        7.73102473459205
    ],
    # extraction H12: dr/dC from position
    'EXT_DRDC_H12': [
        7.72666855746172e-13,
        -2.32129152369782e-10,
        2.53751846203174e-08,
        -1.16655012736709e-06,
        1.78878807660672e-05,
        -0.000174294251347099,
        -1.84155273714072
    ],
}


# Symmetry constants
SYMMETRY_N_DEFAULT: int = 6           # CRs per symmetry group by default
SYMMETRY_REF_PERIOD_DEFAULT: int = 6  # reference measured every N groups
SYMMETRY_CRITERIA: Dict[str, float] = {
    'CR': 10.0,          # a regular CR passes if |asymmetry| < 10 %
    'REFERENCE': 3.0,    # a reference CR passes if |deviation| < 3 %
}


RANGES_EXPECTED: Dict[str, Tuple[int, int]] = {
    'TIME_RANGE': (46000, 100000),
    'REACTIVITY_RANGE': (-25, 1),
    'GROUP_POSITION_RANGE': (0, 400),
    'TEMPERATURE_RANGE': (260, 300),
    'BORIC_ACID_RANGE': (0, 20),
    'PRESSURE_RANGE': (10, 20)
}

# Entry width, in ITC_module
ENTRY_WIDTH: int = 12

# Load file view, cell parameters
COLUMNS_LOAD_FILE_VIEW: Dict[str, int] = {
    'HEIGHT': 20,
    'WIDTH': 100
}

# Header in each window height
HEADER_FRAME_HEIGHT: int = 30

# ITC computation process parameters
ITC_COMPUTATION_VALUES: Dict[str, int] = {
    'MIN_POINTS': 300,     # Mimimum time interval selected, sec
    'POINTS_AMOUNT': 100,  # Points to compute the avg value (left and reght)
    'STEP_POINTS': 100     # Intervals length in Technique 3
}

# DHDH_processing, time sift after the group step
TIME_SHIFT = 5

# DRDH_processing, -/+ deviation range to obtain the avg reactivity value
# before and after the group step
REACTIVITY_RANGE = 5

# For plot in DRDH_processing
GROUP_COLORS = {
    "H12": "red",
    "H11": "orange",
    "H10": "gold",
    "H9": "green",
    "H8": "cyan",
    "H7": "blue",
    "H6": "purple",
    "H5": "magenta",
    "H4": "brown",
    "H3": "gray",
    "H2": "olive",
    "H1": "black"
}


# DRDH_processing, user hints (right-bottom corner)
# Keys are the stages of the measurement cycle.
DRDH_HINTS: Dict[str, str] = {
    # Line 1 (first cycle only: the line is built by clicking)
    'LEFT_1': "Line 1:  left-click to set the first point",
    'RIGHT_1': "Line 1:  right-click to set the second point",
    'FIX_1': "Line 1 is ready.\nPress  Fix 1",

    # Line 1 (next cycles: inherited from the previous step, locked)
    'FIX_1_INHERITED': (
        "Line 1 is taken from the previous step.\n"
        "Press  Fix 1  to confirm it"
    ),

    # Line 2
    'LEFT_2': "Line 2:  left-click to set the first point",
    'RIGHT_2': "Line 2:  right-click to set the second point",
    'FIX_2': "Line 2 is ready.\nPress  Fix 2",

    # Result
    'PROCEED': (
        "Adjust the red line:  click on the plot  or  arrow keys < / >.\n"
        "Then press  Proceed"
    ),
}

# DRDH_processing, experimental uncertainty of the differential worth
#
#   sigma(dRho/dH) = 1/dH * sqrt( sigma^2(dRho) + (dRho/dH)^2 * sigma^2(dH) )
#
#   sigma(dRho) = REACTIVITY_REL * dRho   (relative, reactivity measurement)
#   sigma(dH)   = POSITION_CM             (absolute, cm, group displacement)
#
# Error bars are drawn as +/- SIGMA_FACTOR * sigma.
DRDH_ERROR: Dict[str, float] = {
    'REACTIVITY_REL': 0.03,     # 3 % of dRho
    'POSITION_CM': 0.4,         # cm
    'SIGMA_FACTOR': 2.0,        # +/- 2 sigma on the plot
}

# DRDH_processing, appearance of the "DRDH plot" window
DRDH_PLOT: Dict[str, Any] = {
    'POINT_COLOR': "#1A1A1A",
    'POINT_SIZE': 4.5,
    'ERROR_COLOR': "#555555",
    'ERROR_WIDTH': 0.9,
    'ERROR_CAPSIZE': 2.5,
    'LINE_COLOR': "#C0392B",     # line connecting the measured points
    'LINE_WIDTH': 1.1,
    'GRID_COLOR': "#DCE2E8",
    'GRID_WIDTH': 0.6,
    'RULER_STEP': 10,            # tick step on a group ruler, %
    'RULER_MAX': 100,            # rulers are drawn up to this position, %
    'RULER_GAP': 0.09,           # vertical gap between group rulers
    'Y_LABEL': "Differential efficiency, pcm/cm",
}

# Averaging window for the concentration taken from the file, seconds.
# If less data is available before the click, whatever exists is used.
DRDC_WINDOW_SEC = 60


GROUP_MAP = {
    12: "H12_position",
    11: "H11_position",
    10: "H10_position",
    9: "H9_position",
    8: "H8_position",
    7: "H7_position",
    6: "H6_position",
    5: "H5_position",
    4: "H4_position",
    3: "H3_position",
    2: "H2_position",
    1: "H1_position",
}

# Minimum window size (plot and table)
SPLITTER_MINSIZES: Dict[str, int] = {
    'RIGHT': 50,  # Minimum plot size
    'LEFT': 50    # Minimum table size
}

# Muuse wheel delta (speed)
MOUSE_WHEEL_DELTA: int = 120

# NFME buttons parameters (ITC_module, left frame)
NFME_BUTTONS: Dict[str, int] = {
    'BUTTONS_WIDTH': 390,
    'BUTTONS_FRAME_WIDTH': 400
}

# Window parameters (x3)
MINSIZE_RIGHT_FRAME: int = 250

LEFT_CANVAS_WIDTH: int = 410

MINSIZE_RIGHT_HEADER: int = 235

# Extended cursor parameters
CURSOR: Dict[str, Union[int, float]] = {
    'CURSOR_LINEWIDTH': 0.8,   # dash line width
    'CURSOR_TEXT_SIZE': 9,     # text font size in frame
    'DISTANCE_LABEL_SIZE': 10  # distance label font size (left-down corner)
}

# Main plot parameters, ITC_Processing window
PLOT: Dict[str, int] = {
    'PLOT_LABEL_SIZE': 8,  # axes labels size
    'AXIS_SHIFT': 50       # additional axes shift
}

# Table with result, cell parameters
TABLE: Dict[str, int] = {
    'CELL_WIDTH': 80,
    'CELL_HEIGHT': 20
}


def show_info(window: tk.Tk, filename: str) -> None:
    """Represent an info window which comprises info test from the
    relevant file.

    This function creates a new Tkinter Toplevel window and inserts
    the content from the text file relevant to Module and Processing
    files for each experiment, and relevant to main window as well.

    Args:
        window: The parent Tkinter root window.
        filename: Path to the text file to display.

    Returns:
        None
    """
    info_window: tk.Toplevel = tk.Toplevel(window)
    info_window.title("User Guide")
    info_window.geometry("700x500")
    info_window.config(bg=COLORS['BACKGROUND_COLOR'])

    frame = tk.Frame(info_window, bg=COLORS['BACKGROUND_COLOR'])
    frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    text_widget = tk.Text(
        frame,
        wrap=tk.WORD,
        # for typing only. font=FONTS['INFO_FONT'] is acceptable as well
        font=cast(Tuple[str, int] | Tuple[str, int, str], FONTS['INFO_FONT']),
        bg="white",
        fg=COLORS['FOREGROUND_COLOR']
    )
    text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scrollbar = tk.Scrollbar(frame, command=text_widget.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    text_widget.config(yscrollcommand=scrollbar.set)

    with open(filename, "r", encoding="utf-8") as f:
        text_widget.insert(tk.END, f.read())

    text_widget.config(state=tk.DISABLED)


class CreditOverlay:
    """
    A small panel pinned to the lower-left corner of a window, showing the
    ATE (Novovoronezh branch) logo and a credit line. A double click on it
    hides it; it can be shown again through the returned controller.

    The panel mirrors the criticality formula overlay: it floats over the
    content and does not take part in the layout.
    """

    #: the credit text, in English, naming the Novovoronezh branch
    TEXT = ("The ATE file (Novovoronezh branch) was taken\n"
            "as the basis for development.")

    def __init__(self, parent):
        self.parent = parent
        self.visible = True
        self._img = None

        self.frame = tk.Frame(parent, bg="white", bd=1, relief="solid")

        logo_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "Icons", "ate_logo.png"
        )
        if os.path.exists(logo_path):
            try:
                self._img = tk.PhotoImage(file=logo_path)
                # shrink the logo if it is wide, to keep the panel compact
                if self._img.width() > 200:
                    factor = max(1, self._img.width() // 200)
                    self._img = self._img.subsample(factor, factor)
                logo = tk.Label(self.frame, image=self._img, bg="white")
                logo.pack(padx=6, pady=(6, 2))
                logo.bind("<Double-Button-1>", lambda e: self.toggle())
            except Exception:
                self._img = None

        text = tk.Label(
            self.frame, text=self.TEXT, justify="left",
            font=FONTS['DATA_FONT'], bg="white",
            fg=COLORS['FOREGROUND_COLOR']
        )
        text.pack(padx=6, pady=(0, 6))

        self.frame.bind("<Double-Button-1>", lambda e: self.toggle())
        text.bind("<Double-Button-1>", lambda e: self.toggle())

        self._place()

    def _place(self):
        self.frame.place(relx=0.0, rely=1.0, anchor="sw", x=20, y=-60)

    def toggle(self):
        """Hide or show the credit panel."""
        if self.visible:
            self.frame.place_forget()
        else:
            self._place()
        self.visible = not self.visible
