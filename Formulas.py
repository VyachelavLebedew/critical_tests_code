"""
Formulas - the shared computation core of the whole application.

Every experiment (ITC, DRDH, PCR, Symmetry, approach to criticality) keeps
its physics here, as pure functions that take explicit numeric arguments
and return numbers or dicts. The GUI modules import from this file and only
gather inputs and display results, so the maths lives in one place and can
be tested on its own.

Sections:
    * general helpers
    * ITC          (isothermal temperature coefficient)
    * PCR          (power reactivity coefficient)
    * Symmetry     (azimuthal asymmetry)
    * Criticality  (boric-acid approach-to-criticality calculator)
"""

import math
import numpy as np

from Settings import CRITICALITY_POLY


# ====================================================================== #
#  ITC - isothermal temperature coefficient                             #
# ====================================================================== #
def itc_two_point(reactivity, temperature, start_index, finish_index,
                  points_amount, beta):
    """
    Technique 1: ITC from averaged start and end points.

    Returns (ITC, d_reactivity, d_temperature). ITC is in pcm/degC
    (reactivity is in Beff, beta in percent, so * beta * 1000 -> pcm).
    """
    s0 = np.mean(reactivity[start_index:start_index + points_amount])
    t0 = np.mean(temperature[start_index:start_index + points_amount])
    s1 = np.mean(reactivity[finish_index - points_amount:finish_index])
    t1 = np.mean(temperature[finish_index - points_amount:finish_index])
    d_reactivity = s1 - s0
    d_temperature = t1 - t0
    itc = (d_reactivity / d_temperature) * beta * 1000
    return itc, d_reactivity, d_temperature


def itc_linear_fit(reactivity, temperature, start_index, finish_index,
                   beta):
    """
    Technique 2: ITC from a linear fit of reactivity vs temperature.
    """
    r = reactivity[start_index:finish_index]
    t = temperature[start_index:finish_index]
    slope = float(np.polyfit(t, r, 1)[0])
    return slope * beta * 1000


def itc_sliding_window(reactivity, temperature, times, start_index,
                       finish_index, step_points, beta):
    """
    Technique 3: ITC as the mean of sliding-window regressions over time.
    `times` must already be matplotlib date numbers.
    """
    itc_list = []
    for i in range(finish_index - start_index - step_points):
        start = start_index + i
        end = start + step_points
        time = times[start:end]
        r = reactivity[start:end]
        t = temperature[start:end]
        fR = np.polyfit(time, r, 1)
        fT = np.polyfit(time, t, 1)
        d_r = np.poly1d(fR)(time[-1]) - np.poly1d(fR)(time[0])
        d_t = np.poly1d(fT)(time[-1]) - np.poly1d(fT)(time[0])
        itc_list.append((d_r / d_t) * beta * 1000)
    return float(np.mean(itc_list))


def drdy_value(itc, dtc, dydt, boric_acid):
    """DRDY from ITC, DTC, DYDT and boric acid concentration, or None."""
    if boric_acid is None:
        return None
    drdt = 0.15 * boric_acid - 4.55
    return (itc - dtc - drdt) / dydt


def itc_error(delta_R_percent, delta_T):
    """ITC error term."""
    return (
        -(delta_R_percent / delta_T)
        * (0.05 ** 2 + 0.1 ** 2 / delta_T ** 4) ** 0.5 * 1000
    )


def drdy_error(itc_err, dtc, boric_acid):
    """DRDY error, or None when boric acid is unknown."""
    if boric_acid is None:
        return None
    return ((1.05 * (itc_err / 2) ** 2 + (0.15 * dtc) ** 2)) ** 0.5


# ====================================================================== #
#  PCR - power reactivity coefficient                                   #
# ====================================================================== #
def reactivity_pcm(reactivity_beff, beta):
    """Reactivity in pcm from a value in Beff (beta in percent)."""
    return reactivity_beff * beta * 1000.0


def pcm_to_unit(pcm, unit, beta):
    """Convert a pcm reactivity to the display unit ('%' or 'Beff')."""
    if unit == "%":
        return pcm / 1000.0
    if beta:
        return pcm / (beta * 1000.0)
    return pcm


def weighted_mean(values, sigmas):
    """
    Inverse-variance weighted mean of `values` with absolute `sigmas`.
    Returns (mean, sigma_mean); falls back to a plain mean if a sigma is 0.
    """
    values = list(values)
    sigmas = list(sigmas)
    if not values:
        return None, None
    if any(s <= 0 for s in sigmas):
        m = sum(values) / len(values)
        return m, 0.0
    weights = [1.0 / s ** 2 for s in sigmas]
    wsum = sum(weights)
    mean = sum(w * v for w, v in zip(weights, values)) / wsum
    sigma_mean = (1.0 / wsum) ** 0.5
    return mean, sigma_mean


# ====================================================================== #
#  Symmetry - azimuthal asymmetry                                       #
# ====================================================================== #
def d_rho(rho_init, rho_fin):
    """CR worth = |rho_init - rho_fin|, or None if a value is missing."""
    if rho_init is None or rho_fin is None:
        return None
    return abs(rho_init - rho_fin)


def group_mean(values):
    """Mean of the non-empty CR worths of a symmetry group, rounded."""
    vals = [v for v in values if v]
    return round(sum(vals) / len(vals), 3) if vals else None


def asymmetry(worth, mean):
    """Asymmetry coefficient (sqrt(worth/mean) - 1) * 100 %, or None."""
    if worth is None or mean in (None, 0) or worth / mean < 0:
        return None
    return round(((worth / mean) ** 0.5 - 1) * 100, 3)


def reference_deviation(worth, running_mean):
    """Reference deviation 100 * |N - worth| / N, in %, or None."""
    if worth is None or running_mean in (None, 0):
        return None
    return round(100 * abs(running_mean - worth) / running_mean, 3)


def passes(value, limit):
    """YES / NO against the |value| < limit rule; blank if no value."""
    if value is None:
        return ""
    return "YES" if abs(value) < limit else "NO"


# ====================================================================== #
#  DRDH - differential rod worth / dRho-dC                              #
# ====================================================================== #
def beff_to_display(value, in_percent, beta):
    """
    Convert a reactivity stored in Beff to the display unit. beta_eff is
    entered in percent, so Rho[%] = Rho[Beff] * beta_eff.
    """
    if value is None:
        return None
    return value * beta if in_percent else value


def compute_drdc(delta_rho, c_start, c_finish):
    """
    DRDC = dRho / dC, taken as (final - initial). None if a value is
    missing or the concentration difference is zero.
    """
    if delta_rho is None or c_start is None or c_finish is None:
        return None
    delta_c = c_finish - c_start
    if np.isclose(delta_c, 0):
        return None
    return delta_rho / delta_c


# ====================================================================== #
#  Criticality - boric-acid approach-to-criticality calculator          #
# ====================================================================== #
def poly(name, x):
    """Evaluate the named 6th-degree polynomial at x."""
    c = CRITICALITY_POLY[name]
    return sum(c[i] * x ** (6 - i) for i in range(7))


def pump_time_hours(c_init, c_req, c_makeup, volume, flow, rho_purge,
                    rho_circuit):
    """
    Time of the make-up pump, hours, from the material-balance formula:

        t = ln((c_req - c_makeup)/(c_init - c_makeup))
            * ( -volume / (flow * rho_purge / rho_circuit) )
    """
    denom = (flow * rho_purge) / rho_circuit
    return math.log((c_req - c_makeup) / (c_init - c_makeup)) * (
        -(volume / denom)
    )


def forecast(inp):
    """Forecast sheet: densities, volumes, pump time, unit conversions."""
    rho_water = poly("DENSITY_WATER", inp["T_circuit"])
    rho_purge = poly("DENSITY_PURGE", inp["T_purge"])

    vol_total = inp["V_KD"] + inp["V_circuit"]
    mass_total = vol_total * rho_water / 1000.0

    t_hours = pump_time_hours(
        inp["C_init"], inp["C_req"], inp["C_makeup"],
        inp["V_circuit"] + inp["V_KD"], inp["flow"], rho_purge, rho_water
    )
    vol_needed = inp["flow"] * t_hours

    vol_t_h = (inp["conv_kg_s"] * 3600) / 1000.0
    vol_m3_h = vol_t_h / (rho_purge / 1000.0)

    return {
        "rho_water": rho_water, "rho_purge": rho_purge,
        "vol_total": vol_total, "mass_total": mass_total,
        "t_hours": t_hours, "vol_needed": vol_needed,
        "vol_t_h": vol_t_h, "vol_m3_h": vol_m3_h,
    }


def insertion(inp):
    """Insertion sheet: reactivity, concentration, pump time from groups."""
    s_init = (inp["H10_init"] + inp["H11_init"]
              + inp.get("H12_init", 0))
    s_req = (inp["H10_req"] + inp["H11_req"]
             + inp.get("H12_req", 0))

    dr_init = poly("INS_DR", s_init)
    dr_req = poly("INS_DR", s_req)
    c_init = poly("INS_C", s_init)
    drdc = poly("INS_DRDC", s_req)

    rho_water = poly("DENSITY_WATER", inp["T_circuit"])
    rho_purge = poly("DENSITY_PURGE", inp["T_purge"])

    beta = inp.get("beta", 0.74)
    reactivity = (dr_req - dr_init) / beta
    c_req = c_init - ((dr_req - dr_init) / drdc)

    denom = (inp["flow"] * rho_purge) / rho_water
    t_min = math.log(
        (c_req - inp["C_makeup"]) / (c_init - inp["C_makeup"])
    ) * (-((inp["V_circuit"] + inp["V_KD"]) / denom) * 60)
    rate = reactivity / t_min if t_min else float("nan")
    vol_needed = inp["flow"] * (t_min / 60.0)

    return {
        "sum_init": s_init, "sum_req": s_req,
        "dr_init": dr_init, "dr_req": dr_req,
        "c_init": c_init, "drdc": drdc,
        "rho_water": rho_water, "rho_purge": rho_purge,
        "reactivity": reactivity, "c_req": c_req,
        "rate": rate, "t_min": t_min, "vol_needed": vol_needed,
    }


def extraction_block(inp, group):
    """One extraction block ('H10'/'H11'/'H12'), own polynomials."""
    p_init = inp["pos_init"]
    p_req = inp["pos_req"]

    dr_init = poly(f"EXT_DR_{group}", p_init)
    dr_req = poly(f"EXT_DR_{group}", p_req)
    c_init = poly(f"EXT_C_{group}", p_init)
    drdc = poly(f"EXT_DRDC_{group}", p_req)

    rho_water = poly("DENSITY_WATER", inp["T_circuit"])
    rho_purge = poly("DENSITY_PURGE", inp["T_purge"])

    beta = inp.get("beta", 0.74)
    reactivity = (dr_req - dr_init) / beta
    c_req = c_init - ((dr_req - dr_init) / drdc)

    denom = (inp["flow"] * rho_purge) / rho_water
    t_min = math.log(
        (c_req - inp["C_makeup"]) / (c_init - inp["C_makeup"])
    ) * (-((inp["V_circuit"] + inp["V_KD"]) / denom)) * 60
    rate = reactivity / t_min if t_min else float("nan")
    vol_needed = inp["flow"] * (t_min / 60.0)

    return {
        "dr_init": dr_init, "dr_req": dr_req,
        "c_init": c_init, "drdc": drdc,
        "rho_water": rho_water, "rho_purge": rho_purge,
        "reactivity": reactivity, "c_req": c_req,
        "rate": rate, "t_min": t_min, "vol_needed": vol_needed,
    }


def concentration_curve(c_init, c_req, c_makeup, flow, volume,
                        rho_purge, rho_circuit, n=100):
    """
    Exponential boric-acid decay used for the plots:

        C(t) = c_makeup + (c_init - c_makeup) * exp(-t / tau),
        tau = volume / (flow * rho_purge / rho_circuit)

    Returns (times, concentrations) over the whole pump run.
    """
    denom = (flow * rho_purge) / rho_circuit
    tau = volume / denom
    total = math.log((c_req - c_makeup) / (c_init - c_makeup)) * (-tau)
    times = [total * k / n for k in range(n + 1)]
    conc = [c_makeup + (c_init - c_makeup) * math.exp(-t / tau)
            for t in times]
    return times, conc


def render_formula_image(path):
    """
    Render the criticality formulas as a compact image (matplotlib
    mathtext). Reactivity is denoted R. Returns the path, or None.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return None

    lines = [
        r"$\rho(T),\ \Delta R,\ C,\ \partial R/\partial C$ "
        r"$-$ 6th-degree polynomials",
        r"$R = (\Delta R_{req} - \Delta R_{init}) / \beta_{eff}$",
        r"$C_{req} = C_{init} - "
        r"(\Delta R_{req}-\Delta R_{init})/(\partial R/\partial C)$",
        r"$t = \ln\dfrac{C_{req}-C_{mk}}{C_{init}-C_{mk}}\cdot"
        r"\left(-\dfrac{V}{q\,\rho_{purge}/\rho_{water}}\right)$",
        r"$V_{need} = q\cdot t \qquad rate = R / t$",
    ]
    n = len(lines)
    fig = plt.figure(figsize=(5.6, 0.5 * n + 0.3), dpi=130)
    fig.patch.set_facecolor("#FFFDE7")
    y = 0.92
    fig.text(0.03, y, "Formulas", fontsize=12, fontweight="bold",
             family="Times New Roman", va="top")
    y -= 0.9 / (n + 1)
    for ln in lines:
        fig.text(0.03, y, ln, fontsize=12, va="top")
        y -= 0.9 / (n + 1)
    try:
        fig.savefig(path, facecolor="#FFFDE7", bbox_inches="tight",
                    pad_inches=0.12)
        plt.close(fig)
        return path
    except Exception:
        plt.close(fig)
        return None
