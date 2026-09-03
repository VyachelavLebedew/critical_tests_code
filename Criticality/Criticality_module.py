import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from typing import Any, Optional, Dict, List

import os
from openpyxl import Workbook
from openpyxl.styles import PatternFill
from openpyxl.utils import get_column_letter

from Buttons import MainButtons, TestButtons
from Messages import Messages
from Settings import show_info, FONTS, COLORS, GAPS, CreditOverlay
from Formulas import forecast, insertion, extraction_block

# Cell fills, matching the Excel sheet
FILL_INPUT = "#66FF66"     # green: user input
FILL_RESULT = "#FFFF00"    # yellow: final result


class Criticality_module:
    """
    Approach-to-criticality boric-acid calculator.

    Three tabs mirror the three Excel sheets - forecast, insertion and
    extraction. Each tab is an editable table (like Symmetry): the user
    types the input cells (green), and every computed cell (including the
    yellow results) is recalculated automatically. The whole set can be
    exported to one Excel file, and the key formulas are shown in a corner
    overlay that toggles with a double-click or from the menu.
    """

    def __init__(self, root, main_app: Any) -> None:
        self.root = root
        self.main_app = main_app
        # beta_eff (percent), entered in the main window; used everywhere
        self.beta = getattr(main_app, "beta", None)
        # 12 or 10 control groups
        self.groups_count = 12
        try:
            self.root.iconbitmap("Icons/Criticality_icon.ico")
        except Exception:
            pass

        self.frame: Optional[tk.Frame] = None
        self.menu_bar: Optional[tk.Menu] = None
        self._prev_theme = None

        # Per-tab state: {tab_key: {"tree":.., "rows":[..], "inputs":{..}}}
        self.tabs: Dict[str, Dict[str, Any]] = {}
        self._edit_entry = None
        self._edit_ctx = None
        self._cursor = None

        self._formulas_visible = True
        self.formula_overlay = None

        self.define_tables()

    # ------------------------------------------------------------------ #
    #  Table definitions (labels straight from the Excel sheet)           #
    # ------------------------------------------------------------------ #
    def define_tables(self) -> None:
        """
        Define the rows of each tab.

        Every row is a dict: key, label, kind ('input'/'calc'/'result'/
        'header'), and for inputs a default value. 'calc' and 'result'
        rows are read-only; 'result' rows are filled yellow, inputs green.
        """
        self.forecast_rows = [
            ("h1", "Initial data:", "header", None),
            ("C_init", "Initial concentration, g/kg", "input", 25),
            ("C_req", "Required concentration, g/kg", "input", 10.1),
            ("C_makeup", "Make-up concentration, g/kg", "input", 0),
            ("T_circuit", "Primary coolant temperature, C", "input", 280),
            ("rho_water", "Primary water density, kg/m3", "calc", None),
            ("flow", "CK or RBK flow, m3/h", "input", 20),
            ("T_purge", "CK or RBK temperature, C", "input", 30),
            ("rho_purge", "CK or RBK density, kg/m3", "calc", None),
            ("V_circuit", "Circuit volume without KD, m3", "input", 290),
            ("V_KD", "KD volume at MKU, m3", "input", 38.7),
            ("vol_total", "Total volume, m3", "calc", None),
            ("mass_total", "Total volume, t", "calc", None),
            ("h2", "Result:", "header", None),
            ("t_hours", "Make-up pump run time, h", "result", None),
            ("vol_needed", "Required medium volume, m3", "result", None),
            ("h3", "kg/s to m3/h conversion:", "header", None),
            ("vol_m3_h", "Volume in m3/h", "result", None),
            ("vol_t_h", "Volume in t/h", "result", None),
            ("conv_kg_s", "Volume in kg/s", "input", 6),
        ]

        # The three moving groups are always calculated (three blocks and
        # three insertion rows), because the Excel provides polynomials only
        # for the three top groups. Their DISPLAYED numbers depend on the
        # mode: in 12-group mode they are 10, 11, 12; in 10-group mode they
        # are the three top groups of ten, i.e. 8, 9, 10.
        if self.groups_count == 10:
            disp = {"H10": "8", "H11": "9", "H12": "10"}
        else:
            disp = {"H10": "10", "H11": "11", "H12": "12"}
        self.group_display = disp

        self.insertion_rows = [
            ("h1", "Initial data:", "header", None),
            ("H10_init", f"H{disp['H10']} initial position", "input", 100),
            ("H11_init", f"H{disp['H11']} initial position", "input", 66),
            ("H12_init", f"H{disp['H12']} initial position", "input", 16),
            ("H10_req", f"H{disp['H10']} required position", "input", 100),
            ("H11_req", f"H{disp['H11']} required position", "input", 60),
            ("H12_req", f"H{disp['H12']} required position", "input", 10),
            ("c_init", "Initial concentration, g/kg", "calc", None),
            ("C_makeup", "Make-up concentration, g/kg", "input", 0),
            ("flow", "CK or RBK flow, m3/h", "input", 20),
            ("V_circuit", "Circuit volume without KD, m3", "input", 290),
            ("V_KD", "KD volume at MKU, m3", "input", 38.7),
            ("T_circuit", "Primary temperature, C", "input", 285),
            ("T_purge", "CK or RBK temperature, C", "input", 30),
            ("rho_water", "Primary water density, kg/m3", "calc", None),
            ("rho_purge", "Purge water density, kg/m3", "calc", None),
            ("h2", "Results:", "header", None),
            ("rate", "Reactivity insertion rate, Beff/min", "result", None),
            ("reactivity", "Inserted reactivity, Beff", "result", None),
            ("drdc", "dr/dC, %/(g/kg)", "calc", None),
            ("c_req", "Required concentration, g/kg", "result", None),
            ("t_min", "Make-up pump run time, min", "result", None),
            ("vol_needed", "Required medium volume, m3", "result", None),
        ]

        # Extraction: three blocks, always. The internal keys stay
        # H10/H11/H12 (the polynomial names), only the shown number changes.
        self.extraction_groups = ["H10", "H11", "H12"]
        self.extraction_defaults = {
            "H10": dict(pos_init=30, pos_req=60, C_makeup=40, flow=5),
            "H11": dict(pos_init=50, pos_req=70, C_makeup=40, flow=3),
            "H12": dict(pos_init=20, pos_req=80, C_makeup=40, flow=4.5),
        }

    # ------------------------------------------------------------------ #
    #  Window                                                             #
    # ------------------------------------------------------------------ #
    def create_Criticality_window(self) -> None:
        """Build the tabbed calculator window."""
        if self.frame:
            self.frame.destroy()
        self.frame = tk.Frame(self.root, bg=COLORS['BACKGROUND_COLOR'])
        self.frame.place(x=0, y=0, relwidth=1, relheight=1)
        self.root.title('Approach to criticality')

        self.create_menu()

        # 'clam' draws cell borders (grid lines); restore on the way out
        style = ttk.Style(self.root)
        self._prev_theme = style.theme_use()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Crit.Treeview", font=FONTS['DATA_FONT'],
                        rowheight=24, fieldbackground="#FFFFFF",
                        bordercolor="#C0C0C0", borderwidth=1, relief="solid")
        style.configure("Crit.Treeview.Heading", font=FONTS['HEADING_FONT'])

        self.notebook = ttk.Notebook(self.frame)
        self.notebook.pack(side=tk.TOP, fill=tk.BOTH, expand=True,
                           padx=GAPS['GAPS_X']['PAD_X_10'],
                           pady=GAPS['GAPS_Y']['PAD_Y_10'])

        self.build_forecast_tab()
        self.build_insertion_tab()
        self.build_extraction_tab()

        self.build_formula_overlay()
        self.credit_overlay = CreditOverlay(self.frame)
        self.bottom_buttons()
        self.recompute_all()

    # ------------------------------------------------------------------ #
    #  Generic editable table                                             #
    # ------------------------------------------------------------------ #
    def _make_table(self, parent, rows):
        """Create a two-column (parameter/value) editable table."""
        container = tk.Frame(parent, bg=COLORS['BACKGROUND_COLOR'])
        container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        tree = ttk.Treeview(
            container, columns=("param", "value"), show="headings",
            style="Crit.Treeview", selectmode="browse"
        )
        tree.heading("param", text="Parameter")
        tree.heading("value", text="Value")
        tree.column("param", width=340, anchor="w")
        tree.column("value", width=170, anchor="center")

        vsb = ttk.Scrollbar(container, orient="vertical",
                            command=tree.yview)
        hsb = ttk.Scrollbar(container, orient="horizontal",
                            command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tree.tag_configure("header", background="#DCE6F1",
                           font=FONTS['HEADING_FONT'])
        tree.tag_configure("input", background=FILL_INPUT)
        tree.tag_configure("result", background=FILL_RESULT)
        tree.tag_configure("calc", background="#FFFFFF")

        tree.bind("<Double-1>", self.on_double_click)
        for arrow in ("Up", "Down"):
            tree.bind(
                f"<{arrow}>",
                lambda e, t=tree, d=arrow: (self.on_arrow(t, d), "break")[1]
            )
        tree.bind("<Return>", lambda e, t=tree: self.on_enter_key(t))
        tree.bind("<Button-1>", self._on_single_click, add="+")
        return tree

    def _on_single_click(self, event):
        """Remember the clicked row as the cursor for this table."""
        tree = event.widget
        if tree.identify("region", event.x, event.y) != "cell":
            return
        iid = tree.identify_row(event.y)
        if iid:
            self._cursor = (tree, iid)

    def build_forecast_tab(self):
        tab = tk.Frame(self.notebook, bg=COLORS['BACKGROUND_COLOR'])
        self.notebook.add(tab, text="Forecast")
        tree = self._make_table(tab, self.forecast_rows)
        inputs = {k: v for k, lbl, kind, v in self.forecast_rows
                  if kind == "input"}
        self.tabs["forecast"] = {
            "tree": tree, "rows": self.forecast_rows, "inputs": inputs
        }

    def build_insertion_tab(self):
        tab = tk.Frame(self.notebook, bg=COLORS['BACKGROUND_COLOR'])
        self.notebook.add(tab, text="Insertion")
        tree = self._make_table(tab, self.insertion_rows)
        inputs = {k: v for k, lbl, kind, v in self.insertion_rows
                  if kind == "input"}
        self.tabs["insertion"] = {
            "tree": tree, "rows": self.insertion_rows, "inputs": inputs
        }

    def build_extraction_tab(self):
        """Extraction: three stacked sub-tables (H10, H11, H12)."""
        tab = tk.Frame(self.notebook, bg=COLORS['BACKGROUND_COLOR'])
        self.notebook.add(tab, text="Extraction")

        block_rows = [
            ("h1", "Initial data:", "header", None),
            ("pos_init", "Initial position", "input", None),
            ("pos_req", "Required position", "input", None),
            ("c_init", "Initial concentration, g/kg", "calc", None),
            ("C_makeup", "Make-up concentration, g/kg", "input", 40),
            ("flow", "CK or RBK flow, m3/h", "input", 5),
            ("V_circuit", "Circuit volume without KD, m3", "input", 290),
            ("V_KD", "KD volume at MKU, m3", "input", 38.7),
            ("T_circuit", "Primary temperature, C", "input", 285),
            ("T_purge", "CK or RBK temperature, C", "input", 30),
            ("rho_water", "Primary water density, kg/m3", "calc", None),
            ("rho_purge", "Purge water density, kg/m3", "calc", None),
            ("h2", "Results:", "header", None),
            ("rate", "Reactivity rate, Beff/min", "result", None),
            ("reactivity", "Inserted reactivity, Beff", "result", None),
            ("drdc", "dr/dC, %/(g/kg)", "calc", None),
            ("c_req", "Required concentration, g/kg", "result", None),
            ("t_min", "Pump run time, min", "result", None),
            ("vol_needed", "Required medium volume, m3", "result", None),
        ]

        for grp in self.extraction_groups:
            lf = tk.LabelFrame(
                tab, text=f"Group H{self.group_display[grp]}",
                font=FONTS['TEXT_FONT'],
                bg=COLORS['BACKGROUND_COLOR']
            )
            lf.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                    padx=GAPS['GAPS_X']['PAD_X_10'],
                    pady=GAPS['GAPS_Y']['PAD_Y_10'])
            rows = [(k, lbl, kind,
                     self.extraction_defaults[grp].get(k, v))
                    for k, lbl, kind, v in block_rows]
            tree = self._make_table(lf, rows)
            inputs = {k: (self.extraction_defaults[grp].get(k)
                          if self.extraction_defaults[grp].get(k) is not None
                          else v)
                      for k, lbl, kind, v in rows if kind == "input"}
            self.tabs[f"ext_{grp}"] = {
                "tree": tree, "rows": rows, "inputs": inputs, "group": grp
            }

    # ------------------------------------------------------------------ #
    #  Cell editing                                                       #
    # ------------------------------------------------------------------ #
    def on_double_click(self, event):
        """Edit an input cell in whichever table was clicked."""
        tree = event.widget
        if tree.identify("region", event.x, event.y) != "cell":
            return
        iid = tree.identify_row(event.y)
        if not iid:
            return
        self._cursor = (tree, iid)
        self._open_editor(tree, iid)

    def _open_editor(self, tree, iid):
        """Open the inline entry on the value cell of a row if editable."""
        tab_key, row = self._locate(tree, iid)
        if row is None or row[2] == "header":
            return

        tree.see(iid)
        bbox = tree.bbox(iid, "#2")
        if not bbox:
            return
        x, y, w, h = bbox
        self._close_editor()
        entry = tk.Entry(tree, font=FONTS['DATA_FONT'], justify="center")
        entry.insert(0, tree.set(iid, "value"))
        entry.select_range(0, tk.END)
        entry.focus_set()
        entry.place(x=x, y=y, width=w, height=h)
        entry.bind("<Return>", lambda e: self._commit_editor())
        entry.bind("<Escape>", lambda e: self._close_editor())
        entry.bind("<FocusOut>", lambda e: self._commit_editor())
        self._edit_entry = entry
        self._edit_ctx = (tab_key, row[0], iid, tree)

    def on_arrow(self, tree, direction):
        """Move the row cursor within a table with Up/Down arrows."""
        rows = tree.get_children()
        if not rows:
            return
        cursor = getattr(self, "_cursor", None)
        iid = cursor[1] if cursor and cursor[0] is tree else rows[0]
        if iid not in rows:
            iid = rows[0]
        r = list(rows).index(iid)
        if direction == "Up":
            r = max(0, r - 1)
        elif direction == "Down":
            r = min(len(rows) - 1, r + 1)
        iid = rows[r]
        self._cursor = (tree, iid)
        tree.see(iid)
        tree.selection_set(iid)
        tree.focus(iid)

    def on_enter_key(self, tree):
        """Open the editor on the focused row."""
        cursor = getattr(self, "_cursor", None)
        if cursor and cursor[0] is tree:
            self._open_editor(tree, cursor[1])

    def _locate(self, tree, iid):
        """Return (tab_key, row_tuple) for a tree/iid."""
        for key, tab in self.tabs.items():
            if tab["tree"] is tree:
                for row in tab["rows"]:
                    if row[0] == iid:
                        return key, row
        return None, None

    def _commit_editor(self):
        if self._edit_entry is None:
            return
        raw = self._edit_entry.get().strip().replace(",", ".")
        tab_key, key, iid, tree = self._edit_ctx
        self._close_editor()
        try:
            value = float(raw)
        except ValueError:
            Messages.show("error", "CRIT_NOT_A_NUMBER", value=raw)
            return
        # Any cell can be edited. A real input feeds the calculation; a
        # computed cell is kept as a manual override for display.
        self.tabs[tab_key]["inputs"][key] = value
        self.tabs[tab_key].setdefault("overrides", {})[key] = value
        self.recompute_all()

    def _close_editor(self):
        if self._edit_entry is not None:
            self._edit_entry.destroy()
            self._edit_entry = None
            self._edit_ctx = None

    # ------------------------------------------------------------------ #
    #  Recompute + render                                                 #
    # ------------------------------------------------------------------ #
    def recompute_all(self):
        """Run the calculator for every tab and redraw the tables."""
        self._last_computed = {}
        # beta_eff is used by every calculation
        beta = self.beta if self.beta else 0.74
        for tab in self.tabs.values():
            tab["inputs"]["beta"] = beta

        # forecast
        try:
            fc = forecast(self.tabs["forecast"]["inputs"])
        except Exception:
            fc = {}
        self._last_computed["forecast"] = fc
        self._render("forecast", fc)

        # insertion
        try:
            ins = insertion(self.tabs["insertion"]["inputs"])
        except Exception:
            ins = {}
        self._last_computed["insertion"] = ins
        self._render("insertion", ins)

        # extraction blocks
        for grp in self.extraction_groups:
            key = f"ext_{grp}"
            try:
                res = extraction_block(self.tabs[key]["inputs"], grp)
            except Exception:
                res = {}
            self._last_computed[key] = res
            self._render(key, res)

    def _fmt(self, v):
        if v is None:
            return ""
        if isinstance(v, float):
            return f"{v:.4f}"
        return str(v)

    def _render(self, tab_key, computed):
        """Fill a tab's table from its inputs and the computed dict."""
        tab = self.tabs[tab_key]
        tree = tab["tree"]
        inputs = tab["inputs"]
        overrides = tab.get("overrides", {})
        tree.delete(*tree.get_children())
        for key, label, kind, default in tab["rows"]:
            if kind == "header":
                tree.insert("", "end", iid=key, values=(label, ""),
                            tags=("header",))
                continue
            if kind == "input":
                val = inputs.get(key, default)
            elif key in overrides:
                # a manually edited computed cell keeps the user's value
                val = overrides[key]
            else:
                val = computed.get(key)
            tree.insert("", "end", iid=key,
                        values=(label, self._fmt(val)), tags=(kind,))

    # ------------------------------------------------------------------ #
    #  Formula overlay                                                    #
    # ------------------------------------------------------------------ #
    def build_formula_overlay(self):
        """
        A panel with the key formulas rendered as an image (a clean formula
        sheet), pinned to the bottom-right corner over the tables. Double-
        click it (or the menu item) to hide or show it.
        """
        self.formula_overlay = tk.Frame(
            self.frame, bg="#FFFDE7", bd=1, relief="solid"
        )

        img_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "_formulas.png"
        )
        from Formulas import render_formula_image
        rendered = render_formula_image(img_path)

        if rendered:
            self._formula_img = tk.PhotoImage(file=rendered)
            lbl = tk.Label(self.formula_overlay, image=self._formula_img,
                           bg="#FFFDE7")
        else:
            # fall back to plain text if the image cannot be rendered
            text = (
                "Formulas:\n"
                "rho(T), dR, C, dR/dC - 6th-degree polynomials\n"
                "R = (dR_req - dR_init) / 0.74\n"
                "C_req = C_init - (dR_req - dR_init) / (dR/dC)\n"
                "t = ln((C_req - C_mk)/(C_init - C_mk))\n"
                "        * ( -V / (q * rho_purge / rho_water) )\n"
                "V_need = q * t     rate = R / t"
            )
            lbl = tk.Label(self.formula_overlay, text=text, justify="left",
                           font=FONTS['DATA_FONT'], bg="#FFFDE7")
        lbl.pack(padx=6, pady=4)

        # double-click hides/shows the overlay (see toggle_formulas)
        self.formula_overlay.bind("<Double-Button-1>",
                                  lambda e: self.toggle_formulas())
        lbl.bind("<Double-Button-1>", lambda e: self.toggle_formulas())

        self.formula_overlay.place(relx=1.0, rely=1.0, anchor="se",
                                   x=-20, y=-60)
        self._formulas_visible = True

    def toggle_formulas(self):
        """Hide or show the formula overlay."""
        if self._formulas_visible:
            self.formula_overlay.place_forget()
        else:
            self.formula_overlay.place(relx=1.0, rely=1.0, anchor="se",
                                       x=-20, y=-60)
        self._formulas_visible = not self._formulas_visible

    # ------------------------------------------------------------------ #
    #  Menu, buttons, navigation                                         #
    # ------------------------------------------------------------------ #
    def switch_groups_amount(self):
        """Switch between 12 and 10 control groups and rebuild the window."""
        self.groups_count = 10 if self.groups_count == 12 else 12
        self.tabs = {}
        self.define_tables()
        self.create_Criticality_window()
        Messages.show("info", "CRIT_GROUPS_MODE", n=self.groups_count)

    def create_menu(self):
        self.menu_bar = tk.Menu(self.root.winfo_toplevel())
        self.root.winfo_toplevel().config(menu=self.menu_bar)

        save_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Save", menu=save_menu)
        save_menu.add_command(
            label="Export all pages to Excel", font=FONTS['DATA_FONT'],
            command=self.export_all_to_excel
        )

        mode_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Mode settings", menu=mode_menu)
        mode_menu.add_command(
            label="Switch 12 <-> 10 groups", font=FONTS['DATA_FONT'],
            command=self.switch_groups_amount
        )

        view_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(
            label="Show / hide formulas", font=FONTS['DATA_FONT'],
            command=self.toggle_formulas
        )

        info = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="INFO", menu=info)
        info.add_command(
            label="INFO", font=FONTS['DATA_FONT'],
            command=lambda: show_info(self.root, "Criticality/info_module.txt")
        )

    def bottom_buttons(self):
        bar = tk.Frame(self.frame, bg=COLORS['BACKGROUND_COLOR'])
        bar.pack(side=tk.BOTTOM, fill=tk.X,
                 padx=GAPS['GAPS_X']['PAD_X_10'],
                 pady=GAPS['GAPS_Y']['PAD_Y_10'])
        MainButtons(
            bar, text="<< BACK", command=self.back
        ).pack(side=tk.LEFT)
        TestButtons(
            bar, text="Plots >>", command=self.start_processing
        ).pack(side=tk.LEFT, padx=GAPS['GAPS_X']['PAD_X_10'])
        TestButtons(
            bar, text="Export all to Excel", command=self.export_all_to_excel
        ).pack(side=tk.RIGHT)

    def start_processing(self):
        from .Criticality_processing import Criticality_processing
        self.proc = Criticality_processing(self.frame, self)
        self.proc.create_Criticality_processing_window()

    def back(self, *args):
        try:
            if self._prev_theme:
                ttk.Style(self.root).theme_use(self._prev_theme)
        except Exception:
            pass
        try:
            self.root.winfo_toplevel().config(menu="")
        except Exception:
            pass
        if self.frame is not None:
            self.frame.destroy()
        self.main_app.create_main_window()

    # ------------------------------------------------------------------ #
    #  Export all pages to one Excel file                                 #
    # ------------------------------------------------------------------ #
    def export_all_to_excel(self):
        initial_dir = os.path.dirname(os.path.abspath(__file__))
        filename = filedialog.asksaveasfilename(
            initialdir=initial_dir, defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            title="Export all pages"
        )
        if not filename:
            return

        green = PatternFill("solid", fgColor="66FF66")
        yellow = PatternFill("solid", fgColor="FFFF00")

        wb = Workbook()
        wb.remove(wb.active)

        def dump_sheet(title, tab_keys):
            ws = wb.create_sheet(title=title)
            r = 1
            for tab_key in tab_keys:
                tab = self.tabs[tab_key]
                if "group" in tab:
                    ws.cell(r, 1,
                            f"Group H{self.group_display[tab['group']]}")
                    r += 1
                computed = self._last_computed.get(tab_key, {})
                for key, label, kind, default in tab["rows"]:
                    if kind == "header":
                        ws.cell(r, 1, label)
                        r += 1
                        continue
                    val = (tab["inputs"].get(key, default)
                           if kind == "input"
                           else computed.get(key))
                    ws.cell(r, 1, label)
                    cell = ws.cell(r, 2, val)
                    if kind == "input":
                        cell.fill = green
                    elif kind == "result":
                        cell.fill = yellow
                    r += 1
                r += 1  # blank line between blocks
            ws.column_dimensions["A"].width = 42
            ws.column_dimensions["B"].width = 18

        dump_sheet("Forecast", ["forecast"])
        dump_sheet("Insertion", ["insertion"])
        dump_sheet("Extraction",
                   [f"ext_{g}" for g in self.extraction_groups])
        wb.save(filename)
