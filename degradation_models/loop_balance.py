"""
loop_balance.py
===============
Lumped one-dimensional natural-circulation loop closure for the NuScale Power
Module primary system, calibrated and validated against the FSAR operating map.

Reviewer point M7: the original workflow held the primary mass flow fixed.
Here the flow is solved simultaneously with the loop temperatures, so that any
scenario which changes the loop temperatures changes the flow, and vice versa.

Three equations are solved for (mdot, T_cold, T_hot):

  1. Steam generator     Q_sg = U_eff * A * LMTD(T_hot, T_cold; secondary fixed)
  2. Loop energy         mdot * [h(T_hot) - h(T_cold)] = Q_core
  3. Loop momentum       C * g * [rho(T_cold) - rho(T_hot)] = dP_friction(mdot)

The module holds no plant constants of its own. Every physical value is passed
in by the caller, which avoids duplicating NominalConditions and avoids a
circular import.

CALIBRATION AND ITS LIMITS
--------------------------
C_LOOP and N_FRIC are two lumped parameters fitted to the FSAR part-load map
(Table 5.1-2) at 15, 50, 75 and 100 % power, reproducing it to RMS 0.55 %.
They absorb form losses, the steam generator shell-side crossflow resistance
and the use of equivalent circular hydraulic diameters. N_FRIC is therefore
NOT a pipe friction exponent and must not be presented as one. The FSAR notes
that the fuel assembly and steam generator regions dominate the loop pressure
loss; the latter is not resolved separately in this screening-level closure.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from iapws import IAPWS97
from scipy.optimize import brentq, fsolve

FT = 0.3048
FT2 = 0.09290304
G = 9.80665

# fitted against FSAR Table 5.1-2
C_LOOP = 0.4999
N_FRIC = 0.414

# RCS flow path, FSAR Table 4.4-1: (average flow area [m2], length [m])
SEGMENTS = {
    "core":      (10.3 * FT2, 7.9 * FT),
    "riser_lo":  (24.9 * FT2, 9.4 * FT),
    "riser_up":  (15.4 * FT2, 26.0 * FT),
    "downcomer": (25.7 * FT2, 46.0 * FT),
}

# hydraulic diameters: rod-bundle unit cell for the core, equivalent circular elsewhere
_PITCH, _R_CLAD = 0.0126, 0.00475
DH = {"core": 4.0 * (_PITCH ** 2 - math.pi * _R_CLAD ** 2) / (2.0 * math.pi * _R_CLAD)}
for _k in ("riser_lo", "riser_up", "downcomer"):
    DH[_k] = math.sqrt(4.0 * SEGMENTS[_k][0] / math.pi)


@dataclass
class PlantPoint:
    """Everything the loop closure needs. Populate from NominalConditions."""
    P_MPa: float
    Q_core_W: float
    Q_sg_W: float
    sg_area_m2: float
    sg_U0_W_m2K: float
    sg_T_feed_C: float
    sg_T_steam_C: float
    T_cold_guess_C: float
    T_hot_guess_C: float
    mdot_guess_kg_s: float
    x_bypass: float


@dataclass
class LoopState:
    mdot_total_kg_s: float
    mdot_core_kg_s: float
    T_cold_C: float
    T_hot_C: float
    T_core_out_C: float
    T_core_avg_C: float
    f_UA: float
    riser_friction_increase: float


def _state(t_c: float, p_mpa: float):
    return IAPWS97(T=t_c + 273.15, P=p_mpa)


def _lmtd(t_hot: float, t_cold: float, t_feed: float, t_steam: float) -> float:
    d1 = t_hot - t_steam
    d2 = t_cold - t_feed
    if d1 <= 0.0 or d2 <= 0.0:
        raise ValueError(
            f"non-physical approach temperatures: hot end {d1:.2f} K, "
            f"cold end {d2:.2f} K"
        )
    return (d1 - d2) / math.log(d1 / d2)


def _colebrook(re: float, rel_rough: float) -> float:
    """Darcy friction factor, Colebrook-White, by fixed-point iteration."""
    if re < 4000.0:
        return 64.0 / max(re, 1.0)
    f = 0.02
    for _ in range(60):
        rhs = -2.0 * math.log10(rel_rough / 3.7 + 2.51 / (re * math.sqrt(f)))
        f_new = 1.0 / rhs ** 2
        if abs(f_new - f) < 1e-12:
            return f_new
        f = f_new
    return f


def _friction(mdot: float, t_cold: float, t_hot: float, p_mpa: float,
              delta_ox_m: float = 0.0, eps_m: float = 0.0) -> float:
    """
    Lumped loop friction group.

    delta_ox_m thins the upper riser by 2*delta_ox_m (oxide layer).
    eps_m is the added surface roughness of that deposit; it enters through an
    explicit relative-roughness ratio so that the roughness effect is evaluated
    rather than assumed away (reviewer point M9).
    """
    total = 0.0
    for name, (area, length) in SEGMENTS.items():
        if name == "riser_up" and delta_ox_m:
            d = DH[name] - 2.0 * delta_ox_m
            a = area * (d / DH[name]) ** 2
        else:
            d, a = DH[name], area

        if name == "downcomer":
            t = t_cold
        elif name.startswith("riser"):
            t = t_hot
        else:
            t = 0.5 * (t_cold + t_hot)

        s = _state(t, p_mpa)
        v = mdot / (s.rho * a)
        re = s.rho * v * d / s.mu

        term = (length / d) * 0.5 * s.rho * v * v * re ** (-N_FRIC)

        if name == "riser_up" and eps_m:
            term *= _colebrook(re, eps_m / d) / _colebrook(re, 0.0)
        total += term
    return total


def solve_loop(pp: PlantPoint,
               r_fouling_m2K_W: float = 0.0,
               delta_ox_m: float = 0.0,
               eps_m: float = 0.0,
               x_bypass: float | None = None) -> LoopState:
    """
    Solve the coupled loop and return the state passed to the neutronics model.

    The pin cell receives T_core_avg_C, i.e. the mean of the core inlet and the
    core outlet. This is NOT the RCS average, which the original model used.
    """
    x_bp = pp.x_bypass if x_bypass is None else x_bypass
    f_ua = 1.0 / (1.0 + r_fouling_m2K_W * pp.sg_U0_W_m2K)
    ua = pp.sg_U0_W_m2K * pp.sg_area_m2 * f_ua

    def residuals(v):
        mdot, t_cold, t_hot = v
        try:
            e_sg = (ua * _lmtd(t_hot, t_cold, pp.sg_T_feed_C, pp.sg_T_steam_C)
                    - pp.Q_sg_W) / 1.0e6
        except (ValueError, NotImplementedError):
            return [1.0e6, 1.0e6, 1.0e6]
        dh = (_state(t_hot, pp.P_MPa).h - _state(t_cold, pp.P_MPa).h) * 1000.0
        e_energy = (dh * mdot - pp.Q_core_W) / 1.0e6
        buoy = G * (_state(t_cold, pp.P_MPa).rho - _state(t_hot, pp.P_MPa).rho)
        e_mom = C_LOOP * buoy - _friction(mdot, t_cold, t_hot, pp.P_MPa,
                                          delta_ox_m, eps_m)
        return [e_sg, e_energy, e_mom]

    guess = [pp.mdot_guess_kg_s, pp.T_cold_guess_C, pp.T_hot_guess_C]
    mdot, t_cold, t_hot = fsolve(residuals, guess)

    mdot_core = mdot * (1.0 - x_bp)
    h_in = _state(t_cold, pp.P_MPa).h * 1000.0
    t_core_out = brentq(
        lambda t: (_state(t, pp.P_MPa).h * 1000.0 - h_in) * mdot_core - pp.Q_core_W,
        t_cold + 0.1, 340.0,
    )

    d_fl = 0.0
    if delta_ox_m:
        d0 = DH["riser_up"]
        d_fl = (d0 / (d0 - 2.0 * delta_ox_m)) ** 5 - 1.0

    return LoopState(
        mdot_total_kg_s=mdot,
        mdot_core_kg_s=mdot_core,
        T_cold_C=t_cold,
        T_hot_C=t_hot,
        T_core_out_C=t_core_out,
        T_core_avg_C=0.5 * (t_cold + t_core_out),
        f_UA=f_ua,
        riser_friction_increase=d_fl,
    )
