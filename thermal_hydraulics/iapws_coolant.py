"""
iapws_coolant.py
=================
IAPWS-IF97-based coolant density calculation module.

Companion code for:
  Kim, D. "Screening-Level Pin-Cell Neutronic Sensitivity of a NuScale
  US600-Like SMR Fuel Lattice to Coolant-Density Perturbations from
  Simplified Primary-System Degradation Models." Journal of Nuclear
  Engineering (submitted).

Purpose
-------
Takes the (T, P) conditions computed by degradation_scenarios.py and
passes them to the IAPWS-IF97 equation of state to compute the coolant
density (rho) and other thermodynamic properties. This density value is
used directly in the OpenMC material definition (manuscript Section 2.3).

Approach
--------
Rather than relying on internal correlations as in traditional system
codes (e.g., RELAP, TRACE), this module couples the IAPWS-IF97
industrial formulation directly via the Python `iapws` package. The
chain degradation_level -> (T, P) -> rho is implemented as a single
pipeline, automatically supplying validated coolant properties for any
of the degradation scenarios defined in degradation_scenarios.py.

IAPWS-IF97 implementation verification at nominal conditions
(T = 284.0 degC, P = 12.76 MPa)
------------------------------------------------------------
  rho     = 752.9985 kg/m^3
  cp      = 5199.6  J/(kg*K)   (0.008% deviation from the constant
                                 5200 J/(kg*K) used elsewhere in the code)
  mu      = 94.00   microPa*s
  k       = 584.05  mW/(m*K)
  h       = 1254.28 kJ/kg
  T_sat @ 12.76 MPa = 329.41 degC

This implementation is verified against NIST WebBook reference data at
three temperatures spanning the NuScale US600-like operating range
(manuscript Table 1, ref. [17]); maximum deviation in both rho and cp
is less than 0.002%.

Design basis: NuScale US600-like configuration, 160 MWt / 50 MWe

References:
  [1] IAPWS-IF97, Revised Release 2007, www.iapws.org (manuscript ref. [12])
  [2] iapws Python package (Wagner & Kruse implementation)
  [3] degradation_scenarios.py (this repository)
"""

from __future__ import annotations

import dataclasses
import warnings
from typing import Iterator

import numpy as np
from iapws import IAPWS97

from degradation_scenarios import (
    CoolantState,
    DegradationModel,
    NominalConditions,
    ScenarioType,
    generate_sweep_table,
)


# ---------------------------------------------------------------
# Physical constants and modeling limits
# ---------------------------------------------------------------
class PhysicsLimits:
    """
    NuScale US600-like operating / modeling limits used for diagnostic
    classification of computed coolant states.

    IMPORTANT: These limits (T_OUTLET_CEILING_C in particular) define a
    SINGLE-PHASE MODEL VALIDITY CEILING for the present screening-level
    workflow, not a simulated reactor protection system trip. See
    manuscript Section 2.2 for the corresponding discussion of the
    SG-fouling coolant-state ceiling at T_sat - 5 degC = 324.41 degC.
    The value used here (320.0 degC) is a conservative internal
    diagnostic threshold used for phase/safety-margin bookkeeping in
    this module and is independent of the ceiling value reported in the
    manuscript; it is not derived from any published NuScale design
    basis document.
    """
    # IAPWS-computed value (at 12.76 MPa)
    T_SAT_C: float = 329.41          # saturation temperature [degC]

    # Internal diagnostic thresholds (conservative estimates; not
    # validated NuScale design-basis trip setpoints)
    T_OUTLET_CEILING_C: float = 320.0  # conservative single-phase outlet temperature ceiling
    T_FUEL_LIMIT_C: float     = 350.0  # conservative fuel-rod surface temperature limit
    P_LOW_CEILING_MPa: float  = 11.72  # conservative low-pressure diagnostic threshold
    P_HIGH_CEILING_MPa: float = 13.79  # conservative high-pressure diagnostic threshold

    # OpenMC material property bounds (numerical stability only)
    RHO_MIN_KG_M3: float = 400.0  # density floor (avoids vapor-region inputs)
    RHO_MAX_KG_M3: float = 850.0  # density ceiling

    # Saturation margin
    SUBCOOLING_MARGIN_C: float = 10.0  # minimum subcooling margin [degC]


# ---------------------------------------------------------------
# Coolant property data class
# ---------------------------------------------------------------
@dataclasses.dataclass(frozen=True)
class CoolantProperties:
    """
    IAPWS-IF97 computation result for a single (T, P) condition.
    Contains all properties needed for the OpenMC material definition.
    """
    # Input conditions
    T_C: float          # temperature [degC]
    P_MPa: float        # pressure [MPa]
    degradation_level: float
    scenario_name: str

    # IAPWS-IF97 computed properties
    rho_kg_m3: float    # density [kg/m^3]      <- used directly by OpenMC
    cp_J_kgK: float     # isobaric specific heat [J/(kg*K)]
    h_kJ_kg: float      # specific enthalpy [kJ/kg]
    mu_Pa_s: float       # dynamic viscosity [Pa*s]
    k_W_mK: float        # thermal conductivity [W/(m*K)]
    Pr: float            # Prandtl number [-]

    # Phase classification
    phase: str           # 'liquid', 'near_sat', 'two_phase', 'steam'
    subcooling_C: float  # subcooling margin [degC] (T_sat - T_local)

    # Change relative to nominal
    delta_rho_kg_m3: float      # rho change vs. nominal [kg/m^3]
    delta_rho_pct: float        # fractional rho change vs. nominal [%]

    @property
    def rho_g_cm3(self) -> float:
        """OpenMC material density unit [g/cm^3]."""
        return self.rho_kg_m3 / 1000.0

    @property
    def T_K(self) -> float:
        return self.T_C + 273.15

    def is_safe(self) -> bool:
        """
        Whether the computed state falls within the conservative
        internal diagnostic thresholds defined in PhysicsLimits.
        This is a bookkeeping/diagnostic flag for the simplified
        screening model, not a licensing safety determination.
        """
        return (self.phase not in ('two_phase', 'steam')
                and self.T_C < PhysicsLimits.T_OUTLET_CEILING_C
                and self.P_MPa > PhysicsLimits.P_LOW_CEILING_MPa)

    def openmc_material_density(self) -> float:
        """Value to use with OpenMC Material.set_density('g/cm3', value)."""
        return round(self.rho_g_cm3, 6)

    def summary(self) -> str:
        warn = '' if self.is_safe() else '  [DIAGNOSTIC THRESHOLD EXCEEDED]'
        return (
            f"[{self.scenario_name}] eta={self.degradation_level:.3f}  "
            f"T={self.T_C:.2f} degC  P={self.P_MPa:.4f} MPa{warn}\n"
            f"  rho = {self.rho_kg_m3:.4f} kg/m^3  "
            f"({self.delta_rho_kg_m3:+.4f}, {self.delta_rho_pct:+.4f}%)\n"
            f"  cp  = {self.cp_J_kgK:.1f} J/(kg*K)  "
            f"mu = {self.mu_Pa_s * 1e6:.2f} microPa*s  "
            f"k = {self.k_W_mK * 1e3:.2f} mW/(m*K)\n"
            f"  h   = {self.h_kJ_kg:.3f} kJ/kg  "
            f"Pr = {self.Pr:.4f}  "
            f"subcooling = {self.subcooling_C:.2f} degC  "
            f"[{self.phase}]"
        )


# ---------------------------------------------------------------
# Core calculation functions
# ---------------------------------------------------------------
def _classify_phase(T_C: float, P_MPa: float, T_sat_C: float) -> tuple[str, float]:
    """
    Classify the thermodynamic phase at a given temperature/pressure
    condition and return the corresponding subcooling margin.

    Returns
    -------
    phase : str
        'liquid'    : T < T_sat - 10 degC  (adequately subcooled)
        'near_sat'  : T_sat - 10 degC <= T < T_sat  (near saturation; warning)
        'two_phase' : T >= T_sat  (two-phase region, beyond the
                                    single-phase model's validity)
    subcooling : float
        T_sat - T_C [degC]
    """
    subcooling = T_sat_C - T_C
    if subcooling > PhysicsLimits.SUBCOOLING_MARGIN_C:
        phase = 'liquid'
    elif subcooling > 0:
        phase = 'near_sat'
    else:
        phase = 'two_phase'
    return phase, subcooling


def compute_properties(
        T_C: float,
        P_MPa: float,
        degradation_level: float = 0.0,
        scenario_name: str = 'NOMINAL',
        T_sat_C: float = PhysicsLimits.T_SAT_C,
) -> CoolantProperties:
    """
    Compute coolant properties at a single (T, P) condition using the
    IAPWS-IF97 equation of state.

    Parameters
    ----------
    T_C : float
        Coolant temperature [degC]
    P_MPa : float
        Coolant pressure [MPa]
    degradation_level : float
        Degradation level eta in [0.0, 1.0] — recorded for bookkeeping
    scenario_name : str
        Scenario name — recorded for bookkeeping
    T_sat_C : float
        Saturation temperature [degC] — default corresponds to 12.76 MPa

    Returns
    -------
    CoolantProperties
    """
    # IAPWS-IF97 calculation
    state = IAPWS97(T=T_C + 273.15, P=P_MPa)

    # Extract properties
    rho = state.rho          # kg/m^3
    cp  = state.cp * 1000.0  # kJ/(kg*K) -> J/(kg*K)
    h   = state.h            # kJ/kg
    mu  = state.mu           # Pa*s
    k   = state.k            # W/(m*K)
    Pr  = cp * mu / k        # Prandtl number

    # Phase classification
    phase, subcooling = _classify_phase(T_C, P_MPa, T_sat_C)

    # Diagnostic warnings
    if phase == 'two_phase':
        warnings.warn(
            f"[IAPWS] T={T_C:.1f} degC >= T_sat={T_sat_C:.1f} degC @ {P_MPa} MPa. "
            f"Two-phase region: beyond the single-phase coolant-density "
            f"model's validity. Scenario={scenario_name}, eta={degradation_level:.3f}",
            UserWarning, stacklevel=2,
        )
    elif phase == 'near_sat':
        warnings.warn(
            f"[IAPWS] Near-saturation warning: T={T_C:.1f} degC, "
            f"subcooling={subcooling:.2f} degC < {PhysicsLimits.SUBCOOLING_MARGIN_C} degC",
            UserWarning, stacklevel=2,
        )

    # Change relative to nominal
    nc = NominalConditions
    rho_nom = IAPWS97(T=nc.T_AVG_C + 273.15, P=nc.P_MPa).rho
    delta_rho = rho - rho_nom
    delta_rho_pct = delta_rho / rho_nom * 100.0

    return CoolantProperties(
        T_C=T_C, P_MPa=P_MPa,
        degradation_level=degradation_level,
        scenario_name=scenario_name,
        rho_kg_m3=rho, cp_J_kgK=cp, h_kJ_kg=h,
        mu_Pa_s=mu, k_W_mK=k, Pr=Pr,
        phase=phase, subcooling_C=subcooling,
        delta_rho_kg_m3=delta_rho, delta_rho_pct=delta_rho_pct,
    )


def from_coolant_state(state: CoolantState,
                        use_avg: bool = True) -> CoolantProperties:
    """
    Compute coolant properties directly from a
    degradation_scenarios.CoolantState instance.

    Parameters
    ----------
    state : CoolantState
        Degradation scenario calculation result
    use_avg : bool
        True  -> use T_avg (core-average temperature; default for the
                  OpenMC bulk moderator density)
        False -> use T_outlet (conservative upper-bound temperature)
    """
    T_C = state.T_avg_C if use_avg else state.T_outlet_C
    return compute_properties(
        T_C=T_C,
        P_MPa=state.P_MPa,
        degradation_level=state.degradation_level,
        scenario_name=state.scenario.name,
    )


# ---------------------------------------------------------------
# Parametric sweep: full degradation_level -> rho pipeline
# ---------------------------------------------------------------
def density_sweep(
        scenario: ScenarioType,
        n_steps: int = 21,
        use_avg: bool = True,
) -> list[CoolantProperties]:
    """
    Compute the coolant density at each step of a degradation_level
    sweep from 0 to 1.

    This function implements the core pipeline of the present study:
        degradation_level
            -> DegradationModel.compute()    [degradation scenario]
            -> CoolantState (T, P, mdot)
            -> compute_properties()          [IAPWS-IF97]
            -> CoolantProperties.rho_kg_m3   [OpenMC input]

    Parameters
    ----------
    scenario : ScenarioType
    n_steps : int
        Number of sweep steps (default 21: 0.00, 0.05, ..., 1.00)
    use_avg : bool
        True  -> density at T_avg (core-representative value)
        False -> density at T_outlet (conservative upper bound)

    Returns
    -------
    list of CoolantProperties
    """
    model = DegradationModel(scenario)
    results = []
    for th_state in model.sweep(n_steps=n_steps):
        props = from_coolant_state(th_state, use_avg=use_avg)
        results.append(props)
    return results


def all_scenarios_at_level(
        degradation_level: float,
        use_avg: bool = True,
) -> dict[str, CoolantProperties]:
    """
    Compare the coolant density across all scenarios at a single
    degradation level. Used for cross-scenario visualization.
    """
    return {
        sc.name: from_coolant_state(
            DegradationModel(sc).compute(degradation_level),
            use_avg=use_avg,
        )
        for sc in ScenarioType
    }


# ---------------------------------------------------------------
# OpenMC material update helpers
# ---------------------------------------------------------------
def get_openmc_water_density(
        degradation_level: float,
        scenario: ScenarioType = ScenarioType.SG_FOULING,
        use_avg: bool = True,
) -> float:
    """
    Return the OpenMC material density value [g/cm^3] directly.

    Example
    -------
    >>> density = get_openmc_water_density(0.3, ScenarioType.SG_FOULING)
    >>> water_mat.set_density('g/cm3', density)
    """
    th_state = DegradationModel(scenario).compute(degradation_level)
    props = from_coolant_state(th_state, use_avg=use_avg)
    return props.openmc_material_density()


def get_openmc_temperature(
        degradation_level: float,
        scenario: ScenarioType = ScenarioType.SG_FOULING,
        use_avg: bool = True,
) -> float:
    """
    Return the OpenMC Cell.temperature [K] setting.

    Example
    -------
    >>> T_K = get_openmc_temperature(0.3, ScenarioType.SG_FOULING)
    >>> moderator_cell.temperature = T_K
    """
    th_state = DegradationModel(scenario).compute(degradation_level)
    T_C = th_state.T_avg_C if use_avg else th_state.T_outlet_C
    return round(T_C + 273.15, 2)


# ---------------------------------------------------------------
# Full pipeline table for CSV export
# ---------------------------------------------------------------
def generate_full_pipeline_table(
        scenario: ScenarioType,
        n_steps: int = 21,
) -> list[dict]:
    """
    Return the full degradation-scenario -> thermal-hydraulics ->
    IAPWS -> OpenMC-density pipeline as a list of dictionaries
    (one row per degradation level).

    Columns
    -------
    scenario, degradation_level,
    T_inlet_C, T_outlet_C, T_avg_C, P_MPa, mdot_kg_s,         [thermal-hydraulics]
    rho_kg_m3, rho_g_cm3, delta_rho_pct,                      [IAPWS density]
    cp_J_kgK, h_kJ_kg, mu_uPa_s, k_mW_mK, Pr,                 [other properties]
    T_moderator_K, subcooling_C, phase, is_safe               [state info]
    """
    model = DegradationModel(scenario)
    rows = []
    for th in model.sweep(n_steps=n_steps):
        props = from_coolant_state(th, use_avg=True)
        rows.append({
            # Thermal-hydraulics
            'scenario':           th.scenario.name,
            'degradation_level':  round(th.degradation_level, 4),
            'T_inlet_C':          round(th.T_inlet_C, 4),
            'T_outlet_C':         round(th.T_outlet_C, 4),
            'T_avg_C':            round(th.T_avg_C, 4),
            'P_MPa':              round(th.P_MPa, 6),
            'mdot_kg_s':          round(th.mdot_kg_s, 4),
            'mdot_ratio':         round(th.mdot_ratio, 5),
            # IAPWS density
            'rho_kg_m3':          round(props.rho_kg_m3, 5),
            'rho_g_cm3':          round(props.rho_g_cm3, 7),
            'delta_rho_kg_m3':    round(props.delta_rho_kg_m3, 5),
            'delta_rho_pct':      round(props.delta_rho_pct, 5),
            # Other properties
            'cp_J_kgK':           round(props.cp_J_kgK, 2),
            'h_kJ_kg':            round(props.h_kJ_kg, 4),
            'mu_uPa_s':           round(props.mu_Pa_s * 1e6, 4),
            'k_mW_mK':            round(props.k_W_mK * 1e3, 4),
            'Pr':                 round(props.Pr, 5),
            # State
            'T_moderator_K':      round(props.T_K, 4),
            'subcooling_C':       round(props.subcooling_C, 4),
            'phase':              props.phase,
            'is_safe':            props.is_safe(),
        })
    return rows


# ---------------------------------------------------------------
# Standalone verification
# ---------------------------------------------------------------
if __name__ == '__main__':
    import csv
    import sys

    nc = NominalConditions

    # -- 1. Nominal-condition verification ------------------------
    print("=" * 68)
    print("IAPWS-IF97 nominal-condition verification (NuScale US600-like, 160 MWt/50 MWe)")
    print("=" * 68)
    nominal = compute_properties(nc.T_AVG_C, nc.P_MPa, scenario_name='NOMINAL')
    print(nominal.summary())
    print(f"\n  OpenMC density input  : {nominal.openmc_material_density()} g/cm^3")
    print(f"  T_sat @ {nc.P_MPa} MPa : {PhysicsLimits.T_SAT_C} degC")
    print(f"  Subcooling margin     : {nominal.subcooling_C:.2f} degC")

    # -- 2. Density snapshot at eta = 0.0, 0.5, 1.0 for all scenarios --
    print("\n" + "=" * 68)
    print("Coolant density vs. degradation level for each scenario (T_avg basis)")
    print("=" * 68)
    print(f"{'Scenario':<20} {'eta':>5}  {'T_avg(degC)':>12}  "
          f"{'rho(kg/m3)':>11}  {'d_rho(%)':>9}  {'state':>12}")
    print("-" * 68)
    for sc in ScenarioType:
        for lv in [0.0, 0.5, 1.0]:
            th = DegradationModel(sc).compute(lv)
            p = from_coolant_state(th)
            safe = 'OK' if p.is_safe() else 'THRESHOLD'
            print(f"{sc.name:<20} {lv:>5.2f}  {p.T_C:>12.2f}  "
                  f"{p.rho_kg_m3:>11.4f}  {p.delta_rho_pct:>+9.4f}%  {safe:>12}")
        print()

    # -- 3. Density-sensitivity summary -----------------------------
    print("=" * 68)
    print("Key metric: density change at eta = 1.0 for each scenario")
    print("=" * 68)
    for sc in ScenarioType:
        p_nom = from_coolant_state(DegradationModel(sc).compute(0.0))
        p_deg = from_coolant_state(DegradationModel(sc).compute(1.0))
        print(f"  {sc.name:<20}: "
              f"rho0={p_nom.rho_kg_m3:.2f} -> rho1={p_deg.rho_kg_m3:.2f} kg/m^3  "
              f"(d={p_deg.delta_rho_pct:+.4f}%)")

    # -- 4. Full pipeline table -> CSV export ------------------------
    if '--csv' in sys.argv:
        all_rows = []
        for sc in ScenarioType:
            all_rows.extend(generate_full_pipeline_table(sc, n_steps=21))
        if all_rows:
            w = csv.DictWriter(sys.stdout, fieldnames=list(all_rows[0].keys()))
            w.writeheader()
            w.writerows(all_rows)
