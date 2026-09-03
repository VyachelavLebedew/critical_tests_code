import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from typing import Any, Optional

import matplotlib as mpl
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk
)
from matplotlib.figure import Figure

from Buttons import MainButtons
from Messages import Messages
from Settings import show_info, FONTS, COLORS, GAPS
from Formulas import (
    forecast, insertion, extraction_block, concentration_curve, poly
)

mpl.rcParams['font.family'] = 'Times New Roman'


class Criticality_processing:
    """
    Plots for the approach-to-criticality calculator, three tabs matching
    the three calculator pages.

    Forecast: the boric-acid concentration decay versus time.
    Insertion / Extraction: the same decay, plus how the reactivity and the
    concentration change as the groups travel from the initial to the
    required position.

    Each plot can be saved from its toolbar or the Save menu.
    """

    def __init__(self, parent, main_app: Any) -> None:
        self.parent = parent
        self.main_app = main_app          # the Criticality_module instance
        self.root = main_app.root
        self.frame: Optional[tk.Frame] = None
        self.menu_bar = None
        # figures per tab, for saving
        self.figures = {}
        self.legends = []
        self.legend_visible = True

    # ------------------------------------------------------------------ #
    #  Window                                                             #
    # ------------------------------------------------------------------ #
    def create_Criticality_processing_window(self) -> None:
        if self.parent is not None:
            self.parent.destroy()
        self.frame = tk.Frame(self.root, bg=COLORS['BACKGROUND_COLOR'])
        self.frame.place(x=0, y=0, relwidth=1, relheight=1)
        self.root.title('Approach to criticality - plots')

        self.create_menu()

        self.notebook = ttk.Notebook(self.frame)
        self.notebook.pack(side=tk.TOP, fill=tk.BOTH, expand=True,
                           padx=GAPS['GAPS_X']['PAD_X_10'],
                           pady=GAPS['GAPS_Y']['PAD_Y_10'])

        self.build_forecast_plot()
        self.build_insertion_plot()
        self.build_extraction_plot()

        self.build_formula_overlay()

        bar = tk.Frame(self.frame, bg=COLORS['BACKGROUND_COLOR'])
        bar.pack(side=tk.BOTTOM, fill=tk.X,
                 padx=GAPS['GAPS_X']['PAD_X_10'],
                 pady=GAPS['GAPS_Y']['PAD_Y_10'])
        MainButtons(
            bar, text="<< BACK", command=self.back
        ).pack(side=tk.LEFT)

    def _embed(self, tab, fig):
        """Put a figure with its toolbar on a tab."""
        canvas = FigureCanvasTkAgg(fig, master=tab)
        toolbar = NavigationToolbar2Tk(canvas, tab)
        toolbar.update()
        toolbar.pack(side=tk.TOP, fill=tk.X)
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        canvas.draw()
        return canvas

    def _style_axis(self, ax, xlabel, ylabel, title):
        """Apply the Times New Roman plot styling."""
        family = FONTS['PLOT_FONT'][0]
        size = FONTS['PLOT_FONT'][1]
        ax.set_xlabel(xlabel, fontname=family, fontsize=size)
        ax.set_ylabel(ylabel, fontname=family, fontsize=size)
        ax.set_title(title, fontname=family, fontsize=size + 1)
        for t in ax.get_xticklabels() + ax.get_yticklabels():
            t.set_fontname(family)
            t.set_fontsize(size - 1)
        ax.grid(True, linewidth=0.3, alpha=0.5)

    # ------------------------------------------------------------------ #
    #  Forecast plot: concentration decay vs time                         #
    # ------------------------------------------------------------------ #
    def build_forecast_plot(self):
        tab = tk.Frame(self.notebook, bg=COLORS['BACKGROUND_COLOR'])
        self.notebook.add(tab, text="Forecast")

        inp = self.main_app.tabs["forecast"]["inputs"]
        try:
            fc = forecast(inp)
            times, conc = concentration_curve(
                inp["C_init"], inp["C_req"], inp["C_makeup"],
                inp["flow"], inp["V_circuit"] + inp["V_KD"],
                fc["rho_purge"], fc["rho_water"]
            )
        except Exception:
            times, conc = [], []

        fig = Figure(figsize=(8, 5), constrained_layout=True)
        ax = fig.add_subplot(111)
        ax.plot(times, conc, color="#E6194B", linewidth=1.8)
        self._style_axis(
            ax, "Time, h", "Boric acid concentration, g/kg",
            "Boric acid concentration vs time"
        )
        self.figures["forecast"] = fig
        self._embed(tab, fig)

    # ------------------------------------------------------------------ #
    #  Insertion plot: decay + reactivity/concentration along the path    #
    # ------------------------------------------------------------------ #
    def build_insertion_plot(self):
        tab = tk.Frame(self.notebook, bg=COLORS['BACKGROUND_COLOR'])
        self.notebook.add(tab, text="Insertion")

        inp = self.main_app.tabs["insertion"]["inputs"]
        fig = Figure(figsize=(10, 5), constrained_layout=True)

        # left: concentration decay vs time
        ax1 = fig.add_subplot(121)
        try:
            ins = insertion(inp)
            # time from the balance (minutes), decay curve
            times, conc = concentration_curve(
                ins["c_init"], ins["c_req"], inp["C_makeup"],
                inp["flow"], inp["V_circuit"] + inp["V_KD"],
                ins["rho_purge"], ins["rho_water"]
            )
            # concentration_curve returns hours-consistent units; scale to min
            times = [t * 60 for t in times]
        except Exception:
            times, conc = [], []
        ax1.plot(times, conc, color="#3CB44B", linewidth=1.8)
        self._style_axis(ax1, "Time, min", "Concentration, g/kg",
                         "Concentration vs time")

        # right: reactivity and concentration as the group sum travels
        ax2 = fig.add_subplot(122)
        try:
            s0 = inp["H10_init"] + inp["H11_init"] + inp["H12_init"]
            s1 = inp["H10_req"] + inp["H11_req"] + inp["H12_req"]
            sums = [s0 + (s1 - s0) * k / 100 for k in range(101)]
            dr = [poly("INS_DR", s) for s in sums]
            cc = [poly("INS_C", s) for s in sums]
            ax2.plot(sums, dr, color="#4363D8", linewidth=1.8,
                     label="Reactivity, %")
            ax2b = ax2.twinx()
            ax2b.plot(sums, cc, color="#F58231", linewidth=1.8,
                      label="Concentration, g/kg")
            ax2b.set_ylabel("Concentration, g/kg",
                            fontname=FONTS['PLOT_FONT'][0],
                            fontsize=FONTS['PLOT_FONT'][1])
            lines = ax2.get_lines() + ax2b.get_lines()
            leg = ax2.legend(lines, [ln.get_label() for ln in lines],
                             prop={"family": FONTS['PLOT_FONT'][0],
                                   "size": 8})
            self.legends.append(leg)
        except Exception:
            pass
        self._style_axis(ax2, "Sum of group positions",
                         "Reactivity, %", "Along the movement")

        self.figures["insertion"] = fig
        self._embed(tab, fig)

    # ------------------------------------------------------------------ #
    #  Extraction plot: three blocks                                      #
    # ------------------------------------------------------------------ #
    def build_extraction_plot(self):
        tab = tk.Frame(self.notebook, bg=COLORS['BACKGROUND_COLOR'])
        self.notebook.add(tab, text="Extraction")

        fig = Figure(figsize=(11, 5), constrained_layout=True)
        colours = {"H10": "#E6194B", "H11": "#3CB44B", "H12": "#4363D8"}

        # left: concentration decay vs time for each block
        ax1 = fig.add_subplot(121)
        for grp in self.main_app.extraction_groups:
            inp = self.main_app.tabs[f"ext_{grp}"]["inputs"]
            try:
                res = extraction_block(inp, grp)
                times, conc = concentration_curve(
                    res["c_init"], res["c_req"], inp["C_makeup"],
                    inp["flow"], inp["V_circuit"] + inp["V_KD"],
                    res["rho_purge"], res["rho_water"]
                )
                times = [t * 60 for t in times]
                ax1.plot(times, conc, color=colours[grp], linewidth=1.8,
                         label=grp)
            except Exception:
                continue
        self.legends.append(ax1.legend(
            prop={"family": FONTS["PLOT_FONT"][0], "size": 8}))
        self._style_axis(ax1, "Time, min", "Concentration, g/kg",
                         "Concentration vs time")

        # right: reactivity along the movement for each block
        ax2 = fig.add_subplot(122)
        for grp in self.main_app.extraction_groups:
            inp = self.main_app.tabs[f"ext_{grp}"]["inputs"]
            try:
                p0, p1 = inp["pos_init"], inp["pos_req"]
                pos = [p0 + (p1 - p0) * k / 100 for k in range(101)]
                dr = [poly(f"EXT_DR_{grp}", p) for p in pos]
                ax2.plot(pos, dr, color=colours[grp], linewidth=1.8,
                         label=grp)
            except Exception:
                continue
        self.legends.append(ax2.legend(
            prop={"family": FONTS["PLOT_FONT"][0], "size": 8}))
        self._style_axis(ax2, "Group position", "Reactivity, %",
                         "Reactivity along the movement")

        self.figures["extraction"] = fig
        self._embed(tab, fig)

    # ------------------------------------------------------------------ #
    #  Menu, saving, navigation                                          #
    # ------------------------------------------------------------------ #
    def create_menu(self):
        self.menu_bar = tk.Menu(self.root.winfo_toplevel())
        self.root.winfo_toplevel().config(menu=self.menu_bar)

        save_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Save", menu=save_menu)
        save_menu.add_command(
            label="Save current plot", font=FONTS['DATA_FONT'],
            command=self.save_current
        )

        view_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(
            label="Show / hide formulas", font=FONTS['DATA_FONT'],
            command=self.toggle_formulas
        )
        view_menu.add_command(
            label="Show / hide legend", font=FONTS['DATA_FONT'],
            command=self.toggle_legend
        )

        info = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="INFO", menu=info)
        info.add_command(
            label="INFO", font=FONTS['DATA_FONT'],
            command=lambda: show_info(
                self.root, "Criticality/info_processing.txt"
            )
        )

    def save_current(self):
        """Save the figure of the currently selected tab."""
        tabs = ["forecast", "insertion", "extraction"]
        idx = self.notebook.index(self.notebook.select())
        fig = self.figures.get(tabs[idx])
        if fig is None:
            Messages.show("warning", "CRIT_NO_PLOT")
            return
        path = filedialog.asksaveasfilename(
            title="Save the plot", defaultextension=".png",
            filetypes=[("PNG image", "*.png"), ("PDF document", "*.pdf"),
                       ("SVG image", "*.svg"), ("JPEG image", "*.jpg")]
        )
        if not path:
            return
        fig.savefig(path, dpi=200, bbox_inches="tight")

    def build_formula_overlay(self):
        """Formula sheet pinned over the plots; toggled by double-click."""
        self.formula_overlay = tk.Frame(
            self.frame, bg="#FFFDE7", bd=1, relief="solid"
        )
        import os
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
            lbl = tk.Label(
                self.formula_overlay,
                text=("R = (dR_req - dR_init)/0.74;  "
                      "C_req = C_init - (dR_req-dR_init)/(dR/dC)"),
                justify="left", font=FONTS['DATA_FONT'], bg="#FFFDE7"
            )
        lbl.pack(padx=6, pady=4)
        self.formula_overlay.bind("<Double-Button-1>",
                                  lambda e: self.toggle_formulas())
        lbl.bind("<Double-Button-1>", lambda e: self.toggle_formulas())
        self.formula_overlay.place(relx=1.0, rely=1.0, anchor="se",
                                   x=-20, y=-60)
        self._formulas_visible = True

    def toggle_legend(self):
        """Show or hide the legends on every plot."""
        self.legend_visible = not self.legend_visible
        for leg in self.legends:
            if leg is not None:
                leg.set_visible(self.legend_visible)
        for fig in self.figures.values():
            try:
                fig.canvas.draw_idle()
            except Exception:
                pass

    def toggle_formulas(self):
        """Hide or show the formula overlay."""
        if self._formulas_visible:
            self.formula_overlay.place_forget()
        else:
            self.formula_overlay.place(relx=1.0, rely=1.0, anchor="se",
                                       x=-20, y=-60)
        self._formulas_visible = not self._formulas_visible

    def back(self):
        try:
            self.root.winfo_toplevel().config(menu="")
        except Exception:
            pass
        if self.frame is not None:
            self.frame.destroy()
        self.main_app.create_Criticality_window()
