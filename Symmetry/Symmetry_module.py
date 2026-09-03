import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from typing import Any, Optional, List, Dict

import os
from openpyxl import Workbook
from openpyxl.utils import get_column_letter

from Buttons import MainButtons, TestButtons
from Messages import Messages
import Formulas
from Settings import (
    show_info, FONTS, COLORS, GAPS,
    SYMMETRY_N_DEFAULT, SYMMETRY_REF_PERIOD_DEFAULT,
    SYMMETRY_CRITERIA, CreditOverlay
)


class Symmetry_module:
    """
    Symmetry test: azimuthal asymmetry of the core multiplying properties.

    The window is an editable table, mirroring the reference Excel sheet.
    The user fills, for every CR drop, the initial and final reactivity;
    everything else is computed with the same formulas:

        d_rho_ik  = |rho_init - rho_fin|                       (per CR)
        d_rho_avg = mean of d_rho over the CRs of a group       (per group)
        asymmetry = (sqrt(d_rho_ik / d_rho_avg) - 1) * 100 %    (per CR)

    A reference CR is dropped before the first group, after the last, and
    between groups with the chosen period. For a reference row:

        N   = mean of d_rho over all previous reference drops
        dev = 100 * |N - d_rho| / N          (shown in the average column)

    Criteria: a regular CR passes if |asymmetry| < 10 %, a reference CR if
    |dev| < 3 %.

    The number of CRs per group and the reference period are set by the
    user, so the table is generated to the right size. The results can be
    exported to Excel. Visualisation lives in Symmetry_processing.
    """

    def __init__(self, root, main_app: Any) -> None:
        self.root: tk.Widget = root
        self.main_app: Any = main_app
        try:
            self.root.iconbitmap("Icons/Symmetry_icon.ico")
        except Exception:
            pass

        self.df = getattr(self.main_app, "df", None)
        self.Symmetry_frame: Optional[tk.Frame] = None
        self.menu_bar: Optional[tk.Menu] = None

        # Parameters set by the user
        self.n_cr: int = SYMMETRY_N_DEFAULT
        self.ref_period: int = SYMMETRY_REF_PERIOD_DEFAULT

        # Table state
        self.rows: List[Dict[str, Any]] = []
        self._edit_entry: Optional[tk.Entry] = None
        self._edit_iid: Optional[str] = None
        self._edit_col: Optional[str] = None

        # Column definition, mirroring the Excel sheet.
        # (key, heading, width, editable)
        self.columns = [
            ("step", "Drop No.", 70, False),
            ("group", "Sym. group", 90, True),
            ("cr_group", "CR group", 80, True),
            ("coord", "CR coordinate", 130, True),
            ("rho_init", "rho_init, Beff", 110, True),
            ("rho_fin", "rho_fin, Beff", 110, True),
            ("d_rho", "d_rho, Beff", 100, False),
            ("d_rho_avg", "avg / dev, %", 100, False),
            ("rho_calc", "rho_calc, Beff", 110, True),
            ("asymmetry", "Asymmetry, %", 110, False),
            ("criterion", "Criterion", 90, False),
        ]
        self.editable = {k for k, _, _, ed in self.columns if ed}

    # ------------------------------------------------------------------ #
    #  Window                                                             #
    # ------------------------------------------------------------------ #
    def create_Symmetry_window(self) -> None:
        """Build the table window."""
        root_window = self.root.winfo_toplevel()
        root_window.config(menu=None)
        if self.Symmetry_frame:
            self.Symmetry_frame.destroy()

        self.Symmetry_frame = tk.Frame(
            self.root, bg=COLORS['BACKGROUND_COLOR']
        )
        self.Symmetry_frame.place(x=0, y=0, relwidth=1, relheight=1)
        self.root.title('Symmetry')

        self.create_menu()
        self.top_controls()
        self.create_table()
        self.bottom_buttons()
        self.credit_overlay = CreditOverlay(self.Symmetry_frame)

        self.generate_rows()

    # ------------------------------------------------------------------ #
    #  Top controls                                                       #
    # ------------------------------------------------------------------ #
    def top_controls(self) -> None:
        """Inputs: total number of CRs and the reference period in CRs."""
        bar = tk.Frame(self.Symmetry_frame, bg=COLORS['BACKGROUND_COLOR'])
        bar.pack(side=tk.TOP, fill=tk.X,
                 padx=GAPS['GAPS_X']['PAD_X_10'],
                 pady=GAPS['GAPS_Y']['PAD_Y_10'])

        tk.Label(
            bar, text="Number of CRs:",
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        ).pack(side=tk.LEFT)
        self.n_cr_entry = ttk.Entry(bar, font=FONTS['DATA_FONT'], width=6)
        self.n_cr_entry.insert(0, str(self.n_cr))
        self.n_cr_entry.pack(side=tk.LEFT, padx=GAPS['GAPS_X']['PAD_X_10'])

        tk.Label(
            bar, text="Reference every N CRs:",
            font=FONTS['TEXT_FONT'], bg=COLORS['BACKGROUND_COLOR']
        ).pack(side=tk.LEFT)
        self.ref_entry = ttk.Entry(bar, font=FONTS['DATA_FONT'], width=6)
        self.ref_entry.insert(0, str(self.ref_period))
        self.ref_entry.pack(side=tk.LEFT, padx=GAPS['GAPS_X']['PAD_X_10'])

        TestButtons(
            bar, text="Build table", command=self.rebuild_table
        ).pack(side=tk.LEFT, padx=GAPS['GAPS_X']['PAD_X_10'])

        # Enter in either field rebuilds the table
        self.n_cr_entry.bind("<Return>", lambda e: self.rebuild_table())
        self.ref_entry.bind("<Return>", lambda e: self.rebuild_table())

    # ------------------------------------------------------------------ #
    #  Table                                                              #
    # ------------------------------------------------------------------ #
    def create_table(self) -> None:
        """Create the editable results table."""
        style = ttk.Style(self.root)
        # The 'clam' theme draws cell borders, so vertical column
        # separators become visible. Remember the previous theme to
        # restore it when leaving this window.
        self._prev_theme = style.theme_use()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "Sym.Treeview", font=FONTS['DATA_FONT'], rowheight=24,
            fieldbackground="#FFFFFF", bordercolor="#C0C0C0",
            borderwidth=1, relief="solid"
        )
        style.configure(
            "Sym.Treeview.Heading", font=FONTS['HEADING_FONT'],
            borderwidth=1, relief="raised", bordercolor="#808080"
        )
        style.map("Sym.Treeview", background=[])

        container = tk.Frame(
            self.Symmetry_frame, bg=COLORS['BACKGROUND_COLOR']
        )
        container.pack(side=tk.TOP, fill=tk.BOTH, expand=True,
                       padx=GAPS['GAPS_X']['PAD_X_10'],
                       pady=GAPS['GAPS_Y']['PAD_Y_10'])

        keys = [c[0] for c in self.columns]
        self.tree = ttk.Treeview(
            container, columns=keys, show="headings",
            style="Sym.Treeview", selectmode="browse"
        )
        for key, heading, width, _ in self.columns:
            self.tree.heading(key, text=heading)
            self.tree.column(key, width=width, anchor="center")

        vsb = ttk.Scrollbar(
            container, orient="vertical", command=self.tree.yview
        )
        hsb = ttk.Scrollbar(
            container, orient="horizontal", command=self.tree.xview
        )
        self.tree.configure(
            yscrollcommand=vsb.set, xscrollcommand=hsb.set
        )
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Reference rows get a clear highlight; CR rows use light stripes
        self.tree.tag_configure(
            "reference", background="#D6E4F0", font=FONTS['HEADING_FONT']
        )
        self.tree.tag_configure("fail", foreground="#B00000")
        self.tree.tag_configure("odd", background="#FFFFFF")
        self.tree.tag_configure("even", background="#F4F6F9")

        # Double click on an editable cell opens an entry overlay
        self.tree.bind("<Double-1>", self.on_double_click)
        # Arrow keys move a cell cursor; Enter opens the editor on it
        for arrow in ("Up", "Down", "Left", "Right"):
            self.tree.bind(
                f"<{arrow}>",
                lambda e, d=arrow: (self.on_arrow(d), "break")[1]
            )
        self.tree.bind("<Return>", lambda e: self.on_enter_key())
        # remember the focused cell on a single click, too
        self.tree.bind("<Button-1>", self._on_single_click, add="+")
        self._cursor = None

    def _on_single_click(self, event):
        """Remember the clicked cell as the current cursor."""
        if self.tree.identify("region", event.x, event.y) != "cell":
            return
        iid = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if iid and col:
            self._cursor = (iid, int(col[1:]) - 1)

    def on_double_click(self, event) -> None:
        """Open an inline entry over an editable cell."""
        if self.tree.identify("region", event.x, event.y) != "cell":
            return
        iid = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not iid or not col:
            return
        col_index = int(col[1:]) - 1
        self._cursor = (iid, col_index)
        self._open_editor(iid, col_index)

    def _open_editor(self, iid, col_index) -> None:
        """Open the inline entry over the given cell if it is editable."""
        key = self.columns[col_index][0]
        if key not in self.editable:
            return

        self.tree.see(iid)
        bbox = self.tree.bbox(iid, f"#{col_index + 1}")
        if not bbox:
            return
        x, y, w, h = bbox
        value = self.tree.set(iid, key)

        self._close_editor()
        entry = tk.Entry(self.tree, font=FONTS['DATA_FONT'], justify="center")
        entry.insert(0, value)
        entry.select_range(0, tk.END)
        entry.focus_set()
        entry.place(x=x, y=y, width=w, height=h)
        entry.bind("<Return>", lambda e: self._commit_editor())
        entry.bind("<Escape>", lambda e: self._close_editor())
        entry.bind("<FocusOut>", lambda e: self._commit_editor())
        self._edit_entry = entry
        self._edit_iid = iid
        self._edit_col = key

    # ------------------------------------------------------------------ #
    #  Keyboard navigation between cells                                  #
    # ------------------------------------------------------------------ #
    def on_arrow(self, direction) -> None:
        """
        Move the cell cursor with the arrow keys. The focused cell is
        highlighted; Enter opens the editor on it.
        """
        rows = self.tree.get_children()
        if not rows:
            return
        # start from the current cursor or the first cell
        if getattr(self, "_cursor", None) is None:
            self._cursor = (rows[0], 0)
        iid, col = self._cursor
        if iid not in rows:
            iid = rows[0]
        r = list(rows).index(iid)
        n_cols = len(self.columns)

        if direction == "Up":
            r = max(0, r - 1)
        elif direction == "Down":
            r = min(len(rows) - 1, r + 1)
        elif direction == "Left":
            col = max(0, col - 1)
        elif direction == "Right":
            col = min(n_cols - 1, col + 1)

        self._cursor = (rows[r], col)
        self._highlight_cursor()

    def _highlight_cursor(self) -> None:
        """Show which cell is focused and scroll it into view."""
        if getattr(self, "_cursor", None) is None:
            return
        iid, col = self._cursor
        self.tree.see(iid)
        self.tree.selection_set(iid)
        self.tree.focus(iid)

    def on_enter_key(self) -> None:
        """Open the editor on the focused cell."""
        if getattr(self, "_cursor", None) is None:
            return
        iid, col = self._cursor
        self._open_editor(iid, col)

    def _commit_editor(self) -> None:
        """Store the edited value and recompute the table."""
        if self._edit_entry is None:
            return
        raw = self._edit_entry.get().strip()
        iid, key = self._edit_iid, self._edit_col
        self._close_editor()

        row = self._row_by_iid(iid)
        if row is None:
            return

        if key in ("rho_init", "rho_fin", "rho_calc"):
            value = raw.replace(",", ".")
            if value == "":
                row[key] = None
            else:
                try:
                    row[key] = float(value)
                except ValueError:
                    Messages.show("error", "SYM_NOT_A_NUMBER", value=raw)
                    return
        else:
            row[key] = raw

        self.recompute()
        self.refresh_table()

    def _close_editor(self) -> None:
        """Remove the inline entry overlay."""
        if self._edit_entry is not None:
            self._edit_entry.destroy()
            self._edit_entry = None
            self._edit_iid = None
            self._edit_col = None

    def _row_by_iid(self, iid):
        for row in self.rows:
            if row["iid"] == iid:
                return row
        return None

    # ------------------------------------------------------------------ #
    #  Row generation                                                     #
    # ------------------------------------------------------------------ #
    def rebuild_table(self) -> None:
        """Read the sizes from the inputs and regenerate the rows."""
        try:
            n_cr = int(self.n_cr_entry.get())
            ref_period = int(self.ref_entry.get())
        except ValueError:
            Messages.show("error", "SYM_BAD_SIZES")
            return
        if n_cr < 1 or ref_period < 1:
            Messages.show("error", "SYM_BAD_SIZES")
            return

        self.n_cr = n_cr
        self.ref_period = ref_period
        self.generate_rows()

    def generate_rows(self) -> None:
        """
        Generate the table layout.

        A reference drop is placed before the first CR, after every
        `ref_period` CRs, and after the last CR. The CRs between two
        references form one symmetry group for the averaging. Existing
        entered values are preserved by position where possible.
        """
        old = {r["iid"]: r for r in self.rows} if self.rows else {}
        self.rows = []
        step = 0

        def add_ref():
            nonlocal step
            step += 1
            iid = f"row{step}"
            prev = old.get(iid, {})
            same = prev.get("kind") == "reference"
            self.rows.append({
                "iid": iid, "step": step, "kind": "reference",
                "group": prev.get("group", "") if same else "",
                "cr_group": prev.get("cr_group", "") if same else "",
                "coord": prev.get("coord", "") if same else "",
                "rho_init": prev.get("rho_init") if same else None,
                "rho_fin": prev.get("rho_fin") if same else None,
                "rho_calc": prev.get("rho_calc") if same else None,
            })

        def add_cr(group_no):
            nonlocal step
            step += 1
            iid = f"row{step}"
            prev = old.get(iid, {})
            same = prev.get("kind") == "cr"
            self.rows.append({
                "iid": iid, "step": step, "kind": "cr",
                "group": prev.get("group", str(group_no)) if same
                else str(group_no),
                "cr_group": prev.get("cr_group", "") if same else "",
                "coord": prev.get("coord", "") if same else "",
                "rho_init": prev.get("rho_init") if same else None,
                "rho_fin": prev.get("rho_fin") if same else None,
                "rho_calc": prev.get("rho_calc") if same else None,
            })

        add_ref()                       # reference before the first CR
        group_no = 1
        for i in range(1, self.n_cr + 1):
            add_cr(group_no)
            # a reference after every ref_period CRs, and after the last CR
            if i % self.ref_period == 0 or i == self.n_cr:
                add_ref()
                group_no += 1

        self.recompute()
        self.refresh_table()

    # ------------------------------------------------------------------ #
    #  Computation (Excel formulas)                                       #
    # ------------------------------------------------------------------ #
    def recompute(self) -> None:
        """Recompute every derived cell with the Formulas functions."""
        # 1) d_rho for every row that has both reactivities
        for row in self.rows:
            row["d_rho"] = Formulas.d_rho(
                row.get("rho_init"), row.get("rho_fin")
            )

        # 2) reference rows: running mean N of previous references, dev %
        ref_values = []
        for row in self.rows:
            if row["kind"] != "reference":
                continue
            g = row.get("d_rho")
            if ref_values:
                N = sum(ref_values) / len(ref_values)
            else:
                N = g            # the very first reference: N = its own d_rho
            row["_N"] = N
            row["d_rho_avg"] = Formulas.reference_deviation(g, N)
            if g is not None:
                ref_values.append(g)

        # 3) groups: average d_rho over the CRs of the group (non-empty)
        #    then the asymmetry of every CR against that average
        group = []

        def flush(group_rows):
            avg = Formulas.group_mean(
                [r.get("d_rho") for r in group_rows]
            )
            for r in group_rows:
                r["d_rho_avg"] = avg
                r["asymmetry"] = Formulas.asymmetry(r.get("d_rho"), avg)

        for row in self.rows:
            if row["kind"] == "cr":
                group.append(row)
            else:
                if group:
                    flush(group)
                    group = []
        if group:
            flush(group)

        # 4) criteria
        for row in self.rows:
            if row["kind"] == "reference":
                dev = row.get("d_rho_avg")
                row["criterion"] = self._criterion(dev, "reference")
                row["asymmetry"] = None
            else:
                asym = row.get("asymmetry")
                row["criterion"] = self._criterion(asym, "cr")

    def _criterion(self, value, kind) -> str:
        """YES / NO against the |value| < limit rule; blank if no value."""
        limit = (SYMMETRY_CRITERIA["REFERENCE"] if kind == "reference"
                 else SYMMETRY_CRITERIA["CR"])
        return Formulas.passes(value, limit)

    # ------------------------------------------------------------------ #
    #  Rendering                                                          #
    # ------------------------------------------------------------------ #
    def _fmt(self, value) -> str:
        """Format a cell value for display."""
        if value is None:
            return ""
        if isinstance(value, float):
            return f"{value:g}"
        return str(value)

    def refresh_table(self) -> None:
        """Redraw every row from self.rows."""
        self.tree.delete(*self.tree.get_children())
        for i, row in enumerate(self.rows):
            values = []
            for key, _, _, _ in self.columns:
                # the reference label follows the row kind, not stored data
                if (key == "coord" and row["kind"] == "reference"
                        and not row.get("coord")):
                    values.append("Reference CR")
                else:
                    values.append(self._fmt(row.get(key)))
            tags = ["even" if i % 2 else "odd"]
            if row["kind"] == "reference":
                tags = ["reference"]
            if row.get("criterion") == "NO":
                tags.append("fail")
            self.tree.insert(
                "", "end", iid=row["iid"], values=values, tags=tags
            )

    # ------------------------------------------------------------------ #
    #  Menu and buttons                                                   #
    # ------------------------------------------------------------------ #
    def create_menu(self) -> None:
        """Top menu: Save, INFO."""
        self.menu_bar = tk.Menu(self.root.winfo_toplevel())
        self.root.winfo_toplevel().config(menu=self.menu_bar)

        save_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Save", menu=save_menu)
        save_menu.add_command(
            label="Save to Excel", font=FONTS['DATA_FONT'],
            command=self.save_to_Excel
        )

        info = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="INFO", menu=info)
        info.add_command(
            label="INFO", font=FONTS['DATA_FONT'],
            command=lambda: show_info(self.root, "Symmetry/info_module.txt")
        )

    def bottom_buttons(self) -> None:
        """Bottom bar: go to plots, save, back."""
        bar = tk.Frame(self.Symmetry_frame, bg=COLORS['BACKGROUND_COLOR'])
        bar.pack(side=tk.BOTTOM, fill=tk.X,
                 padx=GAPS['GAPS_X']['PAD_X_10'],
                 pady=GAPS['GAPS_Y']['PAD_Y_10'])

        MainButtons(
            bar, text="<< BACK",
            command=lambda: self.back(self.Symmetry_frame)
        ).pack(side=tk.LEFT)

        TestButtons(
            bar, text="Plots >>", command=self.start_Symmetry
        ).pack(side=tk.LEFT, padx=GAPS['GAPS_X']['PAD_X_10'])

        MainButtons(
            bar, text="User guide",
            command=lambda: show_info(self.root, "Symmetry/info_module.txt")
        ).pack(side=tk.LEFT, padx=GAPS['GAPS_X']['PAD_X_10'])

        TestButtons(
            bar, text="Save to Excel", command=self.save_to_Excel
        ).pack(side=tk.RIGHT)

    # ------------------------------------------------------------------ #
    #  Navigation                                                         #
    # ------------------------------------------------------------------ #
    def start_Symmetry(self) -> None:
        """Open the plotting window, passing the table state along."""
        from .Symmetry_processing import Symmetry_processing
        self.Symmetry_processing_interface = Symmetry_processing(
            self.Symmetry_frame, self
        )
        self.Symmetry_processing_interface.create_Symmetry_processing_window()

    def back(self, window) -> None:
        """Return to the main menu."""
        # Restore the theme changed for the table
        try:
            if getattr(self, "_prev_theme", None):
                ttk.Style(self.root).theme_use(self._prev_theme)
        except Exception:
            pass
        try:
            self.root.winfo_toplevel().config(menu="")
        except Exception:
            pass
        if window is not None:
            window.destroy()
        self.main_app.create_main_window()

    # ------------------------------------------------------------------ #
    #  Excel export                                                       #
    # ------------------------------------------------------------------ #
    def save_to_Excel(self) -> None:
        """Export the table to an .xlsx file."""
        initial_dir = os.path.dirname(os.path.abspath(__file__))
        filename = filedialog.asksaveasfilename(
            initialdir=initial_dir, defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            title="Save the symmetry table"
        )
        if not filename:
            return

        wb = Workbook()
        ws = wb.active
        ws.title = "Symmetry"

        headers = [heading for _, heading, _, _ in self.columns]
        ws.append(headers)
        for row in self.rows:
            ws.append([self._fmt(row.get(key))
                       for key, _, _, _ in self.columns])

        for col_idx, (_, heading, _, _) in enumerate(self.columns, start=1):
            max_len = len(str(heading))
            for cell in ws[get_column_letter(col_idx)]:
                if cell.value is not None:
                    max_len = max(max_len, len(str(cell.value)))
            ws.column_dimensions[get_column_letter(col_idx)].width = (
                max_len + 2
            )

        wb.save(filename)
