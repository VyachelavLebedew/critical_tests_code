import os
import sys
import tkinter as tk
from tkinter import filedialog, ttk
import pandas as pd
from typing import Optional


def _app_base_dir() -> str:
    """
    The directory that holds the program's resources (Icons/, the module
    packages with their info_*.txt, etc.).

    * running as a normal script  -> the folder of this file
    * running as a PyInstaller exe -> the bundle folder (sys._MEIPASS for a
      one-file build, or the executable's folder for a one-folder build)
    """
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


# every icon and info path in the program is relative to the project root,
# so anchoring the working directory here makes them all resolve, both as a
# script and inside the packaged executable
os.chdir(_app_base_dir())

from Buttons import MainButtons, TestButtons, SmallButtons
from Messages import Messages
from Settings import (
    show_info, ENCODINGS, FONTS, COLORS, GAPS, COLUMNS_LOAD_FILE_VIEW
)

from ITC import ITC_module
from DRDH import DRDH_module
from PCR import PCR_module
from Symmetry import Symmetry_module
from Criticality import Criticality_module


class Main:
    """
    Main application for the '3 in 1 v2' program.

    Obtains the data file, proceed with this data,
    obtains a beta value, and running ITC, DRDH, PCR, and Symmetry modules.

    Attributes:
        root (tk.Tk): Main Tkinter window.
        beta (float): Beta value entered by the user.
        df (DataFrame): Loaded data file.
        Molules interfaces.
    """

    def __init__(self, root):
        """
        Initialize the main window, buttons, and labels.

        Args:
            root (tk.Tk): The main Tkinter root window.
        """
        self.root = root
        self.root.title('3 in 1 v2')
        self.beta = None
        self.df = None
        self.ITC_interface = None
        self.DRDH_interface = None
        self.PCR_interface = None
        self.Symmetry_interface = None
        self.main_buttons()
        self.test_buttons()
        self.check_data_loaded()

    def main_buttons(self) -> None:
        """
        Create and locate the main action buttons:
        'Open file', 'View data', 'Enter beta', and 'User guide'.
        """
        self.open_file_button = MainButtons(
              self.root,
              text='Open file',
              command=self.open_file,
        )
        self.open_file_button.grid(
            row=1, column=1,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10']
        )

        self.view_data_button = MainButtons(
              self.root,
              text='View data',
              command=self.view_data,
        )
        self.view_data_button.grid(
            row=1, column=2,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10']
        )

        self.get_beta_button = MainButtons(
              self.root,
              text='Enter beta',
              command=self.enter_beta,
        )
        self.get_beta_button.grid(
            row=1, column=3,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10']
        )

        self.user_guide_button = MainButtons(
              self.root,
              text='User guide',
              command=lambda: show_info(self.root, "info.txt"),
        )
        self.user_guide_button.grid(
            row=6, column=1,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10']
        )

    def test_buttons(self) -> None:
        """
        Create and locate the test buttons:
        'ITC', 'DRDH', 'PCR', and 'Symmetry'.
        Initially disabled until a file and beta value are loaded.
        """
        self.ITC_button = TestButtons(
              self.root,
              text='ITC',
              command=self.ITC,
        )
        self.ITC_button.grid(
            row=2, column=1,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10']
        )
        self.ITC_button.config(state="disabled")

        self.DRDH_button = TestButtons(
              self.root,
              text='DRDH',
              command=self.DRDH,
        )
        self.DRDH_button.grid(
            row=2, column=2,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10']
        )
        self.DRDH_button.config(state="disabled")

        self.PCR_button = TestButtons(
              self.root,
              text='PCR',
              command=self.PCR,
        )
        self.PCR_button.grid(
            row=2, column=3,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10']
        )
        self.PCR_button.config(state="disabled")

        self.Symmetry_button = TestButtons(
              self.root,
              text='Symmetry',
              command=self.Symmetry,
        )
        self.Symmetry_button.grid(
            row=2, column=4,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10']
        )
        # Symmetry does not need a loaded file or a beta value, so it is
        # available from the start.

        # Next row, filled from the right: placeholders for the two
        # remaining experiments.
        self.criticality_button = TestButtons(
            self.root,
            text='Reaching\nCriticality',
            command=self.criticality,
        )
        self.criticality_button.grid(
            row=3, column=4,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10']
        )
        # Approach to criticality needs beta (used for reactivity), but not
        # a loaded file. It becomes available once beta is set.
        self.criticality_button.config(state="disabled")

        self.imax_button = TestButtons(
            self.root,
            text='Imax',
            command=self.imax,
        )
        self.imax_button.grid(
            row=3, column=3,
            padx=GAPS['GAPS_X']['PAD_X_40_20'],
            pady=GAPS['GAPS_Y']['PAD_Y_10']
        )

    def criticality(self) -> None:
        """Launch the approach-to-criticality calculator."""
        if self.beta is None:
            Messages.show("warning", "SET_BETA_FIRST")
            return
        self.Criticality_interface = Criticality_module(self.root, self)
        self.Criticality_interface.create_Criticality_window()

    def imax(self) -> None:
        """Placeholder for the Imax experiment."""
        pass

    def check_data_loaded(self) -> None:
        """
        Create labels to represent wheather beta value has been entered
        and data file has been loaded.
        """
        self.main_window_label = tk.Label(
            self.root, text='MAIN WINDOW',
            font=FONTS['TITLE_FONT'], bg=COLORS['BACKGROUND_COLOR']
        ).grid(
            row=0, column=1, columnspan=4,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_10_5']
            )
        self.check_beta_label: tk.Label = tk.Label(
            self.root, text='Beta value: is not set yet ⏱',
            font=FONTS['BUTTON_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.check_beta_label.grid(
            row=4, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_10_5']
        )
        self.check_file_label: tk.Label = tk.Label(
            self.root, text='File: is not set yet ⏱',
            font=FONTS['BUTTON_FONT'], bg=COLORS['BACKGROUND_COLOR']
        )
        self.check_file_label.grid(
            row=5, column=1,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_10_5']
        )

    def open_file(self) -> None:
        """
        Opens a file dialog to select a data file in ".txt" or ".s17" format.
        Tries to read the file using multiple encodings.
        """
        file_name: Optional[str] = filedialog.askopenfile(
            filetypes=(
                ("TXT files", "*.txt"),
                ("s17 files", "*.s17*"),
                ("All files", "*.*")
            )
        )

        if not file_name:
            Messages.show("warning", "NO_FILE")
            return

        last_error: list[Exception] = []

        for encoding in ENCODINGS:
            try:
                file = pd.read_csv(file_name, sep='\t', encoding=encoding)
                self.df = pd.DataFrame(file)

                self.check_file_label.config(
                    text='File: loaded successfully ✓'
                )

                if self.beta is not None:
                    self.ITC_button.config(state="normal")
                    self.DRDH_button.config(state="normal")
                    self.PCR_button.config(state="normal")

                Messages.show("info", "FILE_LOADED", enc=encoding)
                return

            except Exception as e:
                last_error += [e]

        Messages.show("error", "FILE_ERROR", error=last_error)

    def view_data(self) -> None:
        """Displays the file loaded"""
        data_window = tk.Toplevel(self.root)
        data_window.title('Data')
        data_window.geometry("840x500")
        data_window.config(bg=COLORS['BACKGROUND_COLOR'])

        frame: tk.Frame = tk.Frame(data_window)
        frame.pack(
            fill=tk.BOTH, expand=True,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_10']
        )

        if self.df is None:
            message_label = tk.Label(
                frame,
                text="File is not loaded yet",
                font=COLORS['TITLE_FONT'],
            )
            message_label.pack(expand=True)
            return

        style = ttk.Style()
        style.configure("Treeview.Heading", font=FONTS['HEADING_FONT'])

        columns: list[str] = list(self.df.columns)
        tree: ttk.Treeview = tk.ttk.Treeview(
            frame, columns=columns, show="headings",
            height=COLUMNS_LOAD_FILE_VIEW['HEIGHT']
        )
        style.configure("Treeview", font=FONTS['DATA_FONT'])

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=COLUMNS_LOAD_FILE_VIEW['WIDTH'],
                        anchor=tk.CENTER
                        )
        vsb = tk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hsb = tk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        for row in self.df.values.tolist():
            tree.insert("", tk.END, values=row)

    def get_entry(self, entry: ttk.Entry, window: tk.Toplevel) -> None:
        """
        Obtain a beta value from an Entry widget.

        Args:
            entry (ttk.Entry): Entry widget contains the beta value.
            window (tk.Toplevel): The window contains the entry.
        """
        value: str = entry.get().strip()
        value = value.replace(',', '.')
        try:
            beta: float = float(value)
            if beta < 0:
                Messages.show("error", "VALUE_POSTIVE",
                              value='Beta', sign='positive')
                window.lift()
                entry.delete(0, tk.END)
                entry.focus_set()
                return
            self.beta = beta
            self.check_beta_label.config(text='Beta value: successfully set ✓')

            # Criticality needs only beta, not a file
            self.criticality_button.config(state="normal")

            if self.df is not None:
                self.ITC_button.config(state="normal")
                self.DRDH_button.config(state="normal")
                self.PCR_button.config(state="normal")
                self.Symmetry_button.config(state="normal")

            window.destroy()
        except Exception as e:
            Messages.show("error", "BETA_ERROR", error=e)
            window.lift()
            entry.delete(0, tk.END)
            entry.focus_set()

    def enter_beta(self) -> None:
        """Creates a window aimed at entering the beta value."""
        beta_window: tk.Toplevel = tk.Toplevel(self.root)
        beta_window.title('Beta')
        self.beta_label = tk.Label(
            beta_window, text='Enter the Beta eff. value, %:',
            font=FONTS['DATA_FONT']
            ).grid(
                row=0, column=0,
                padx=GAPS['GAPS_X']['PAD_X_10'],
                pady=GAPS['GAPS_Y']['PAD_Y_10_5']
                )
        self.beta_entry: ttk.Entry = ttk.Entry(
            beta_window, font=FONTS['DATA_FONT']
        )
        self.beta_entry.grid(
            row=1, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_0_5']
            )
        self.beta_get_button = SmallButtons(
            beta_window,
            text='Get beta value',
            command=lambda: self.get_entry(self.beta_entry, beta_window),
        )
        self.beta_get_button.grid(
            row=2, column=0,
            padx=GAPS['GAPS_X']['PAD_X_10'],
            pady=GAPS['GAPS_Y']['PAD_Y_0_5']
            )
        beta_window.geometry("170x100")
        beta_window.config(bg=COLORS['BACKGROUND_COLOR'])
        self.beta_entry.focus_set()
        self.beta_entry.bind(
            '<Return>',
            lambda event: self.get_entry(self.beta_entry, beta_window)
        )

    def ITC(self) -> None:
        """Launch the ITC computation process via ITC_Module file"""
        self.ITC_interface = ITC_module(self.root, self)
        self.ITC_interface.create_ITC_window()

    def DRDH(self) -> None:
        """Launch the DRDH computation process via ITC_Module file"""
        self.DRDH_interface = DRDH_module(self.root, self)
        self.DRDH_interface.create_DRDH_window()

    def PCR(self) -> None:
        """Launch the PCR computation process via ITC_Module file"""
        self.PCR_interface = PCR_module(self.root, self)
        self.PCR_interface.create_PCR_window()

    def Symmetry(self) -> None:
        """Launch the Symmetry computation process via ITC_Module file"""
        self.Symmetry_interface = Symmetry_module(self.root, self)
        self.Symmetry_interface.create_Symmetry_window()


root = tk.Tk()
root.iconbitmap("Icons/main.ico")
app = Main(root)
root.geometry("925x500")
root.config(bg=COLORS['BACKGROUND_COLOR'])
root.mainloop()
