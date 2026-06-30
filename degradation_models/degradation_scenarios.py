"""
degradation_scenarios.py
========================
NuScale US600-like SMR primary-system degradation scenario models.

Companion code for:
  Kim, D. "Screening-Level Pin-Cell Neutronic Sensitivity of a NuScale
  US600-Like SMR Fuel Lattice to Coolant-Density Perturbations from
  Simplified Primary-System Degradation Models." Journal of Nuclear
  Engineering (submitted).

Design basis: NuScale US600-like configuration
  - Thermal power   : 160 MWt
  - Electric power   : 50 MWe
  - Primary coolant circulation: fully passive natural circulation (no pumps)

Scope and limitations
----------------------
These are SIMPLIFIED PARAMETRIC degradation models intended to generate
physically motivated coolant-property perturbations for a screening-level
pin-cell neutronics study. They are NOT validated component degradation
models for the actual NuScale US600 design. See manuscript Section 2.5
for the full scope and limitations discussion.

Three degradation mechanisms (RPV-internal, consistent with the integral
PWR layout, which has no external primary piping):
  RISER_CORROSION  : Hot riser tube inner-wall oxide growth -> increased
                      hydraulic resistance -> reduced natural-circulation
                      flow rate. Serves as a negative-control case.
  SG_FOULING       : SG helical-coil primary-side scale deposition ->
                      reduced overall heat transfer coefficient ->
                      elevated coolant temperature.
  BYPASS_LEAKAGE   : Core barrel-to-shroud gap leakage -> hot coolant
                      mixes directly into the core inlet stream.

NuScale US600-like nominal operating conditions
-------------------------------------------------
  Operating pressure       : 12.76 MPa
  Core inlet temperature    : 258.3 degC
  Core outlet temperature   : 309.7 degC
  Primary coolant flow rate : 587.3 kg/s
  Thermal power              : 160 MWt
  Electric power              : 50 MWe
  Fuel assemblies              : 37 (17x17, 2 m active height)
  Control rod assemblies        : 16
  RPV height / outer diameter   : 20 m / 2.7 m
  Core diameter / height          : 1.5 m / 2.0 m

These nominal values follow the specifications reported in the
manuscript references (Yu et al. 2022; Guo et al. 2022; Fridman et al.
2023). Geometric parameters for internal RPV components (riser, SG
annulus) marked as estimated values are not independently validated
NuScale design parameters and are used only as representative inputs
to the parametric degradation models below.
"""

from __future__ import annotations

import dataclasses
import math
from enum import Enum, auto
from typing import Iterator

import numpy as np


# ---------------------------------------------------------------
# NuScale US600-like nominal operating conditions
# ---------------------------------------------------------------
class NominalConditions:
    """
    NuScale US600-like nominal power module (NPM) operating conditions.
    """
    # -- Thermal-hydraulics --------------------------------------
    POWER_MWT: float      = 160.0
    POWER_MWE: float      = 50.0
    P_MPa: float          = 12.76
    T_INLET_C: float      = 258.3
    T_OUTLET_C: float     = 309.7
    T_AVG_C: float        = (258.3 + 309.7) / 2.0   # 284.0 degC
    MDOT_KG_S: float      = 587.3
    WATER_CP_J_KGK: float = 5_200.0   # specific heat of high-pressure water [J/(kg*K)]

    # -- RPV external geometry ------------------------------------
    RPV_HEIGHT_M: float   = 20.0
    RPV_OD_M: float       = 2.7
    RPV_ID_M: float       = 2.5        # estimated, assuming 100 mm wall thickness

    # -- Core geometry ----------------------------------------------
    CORE_DIAMETER_M: float = 1.5
    CORE_HEIGHT_M: float   = 2.0
    N_FA: int              = 37
    N_CR: int              = 16

    # -- RPV internal geometry (estimated parametric inputs) ---------
    # Hot riser tube: sized comparably to the core diameter to avoid
    # control-rod-drive interference.
    RISER_ID_M: float     = 1.50
    RISER_OD_M: float     = 1.56       # estimated, 30 mm wall thickness
    RISER_HEIGHT_M: float = 10.0       # estimated effective natural-circulation driving height

    # SG annular region: hot riser outer wall to RPV inner wall
    SG_ANNULUS_WIDTH_M: float = (2.5 - 1.56) / 2.0   # ~0.47 m, estimated

    # Design life
    DESIGN_LIFE_YR: float = 60.0


# ---------------------------------------------------------------
# Degradation scenario types
# ---------------------------------------------------------------
class ScenarioType(Enum):
    RISER_CORROSION = auto()
    SG_FOULING      = auto()
    BYPASS_LEAKAGE  = auto()


# ---------------------------------------------------------------
# Coolant state
# ---------------------------------------------------------------
@dataclasses.dataclass(frozen=True)
class CoolantState:
    scenario: ScenarioType
    degradation_level: float

    T_inlet_C: float
    T_outlet_C: float
    T_avg_C: float
    P_MPa: float
    mdot_kg_s: float

    riser_friction_increase: float
    sg_ua_reduction: float
    bypass_fraction: float

    @property
    def T_moderator_K(self) -> float:
        return self.T_avg_C + 273.15

    @property
    def delta_T_vs_nominal_C(self) -> float:
        return self.T_avg_C - NominalConditions.T_AVG_C

    @property
    def delta_P_vs_nominal_MPa(self) -> float:
        return self.P_MPa - NominalConditions.P_MPa

    @property
    def mdot_ratio(self) -> float:
        return self.mdot_kg_s / NominalConditions.MDOT_KG_S

    def summary(self) -> str:
        nc = NominalConditions
        return (
            f"[{self.scenario.name}] eta={self.degradation_level:.3f}\n"
            f"  T_inlet  : {self.T_inlet_C:7.2f} degC  (d{self.T_inlet_C - nc.T_INLET_C:+.2f})\n"
            f"  T_outlet : {self.T_outlet_C:7.2f} degC  (d{self.T_outlet_C - nc.T_OUTLET_C:+.2f})\n"
            f"  T_avg    : {self.T_avg_C:7.2f} degC  (d{self.delta_T_vs_nominal_C:+.2f})\n"
            f"  P        : {self.P_MPa:.4f} MPa\n"
            f"  mdot     : {self.mdot_kg_s:7.2f} kg/s  ({self.mdot_ratio:.3f}x nominal)\n"
            f"  riser dfL: {self.riser_friction_increase:.4f}  "
            f"SG UA reduction: {self.sg_ua_reduction:.4f}  "
            f"bypass: {self.bypass_fraction:.4f}"
        )


# ---------------------------------------------------------------
# Mechanism 1: Hot riser tube inner-wall corrosion (negative-control case)
# ---------------------------------------------------------------
class RiserCorrosionModel:
    """
    Hot riser tube inner-wall Fe3O4 oxide layer growth.

    Increased riser friction reduces the natural-circulation flow rate
    directly:
        mdot_ratio = sqrt(delta_P_buoyancy / total_friction)

    delta(eta)   = delta_max * sqrt(eta)        (parabolic, diffusion-limited
                                                   growth law; see manuscript
                                                   Section 2.2, ref. [15])
    D_eff(eta)   = D0 - 2 * delta(eta)
    dfL(eta)     = (D0 / D_eff)^5 - 1            (Darcy-Weisbach friction
                                                   parameter increase;
                                                   manuscript ref. [16])
    mdot(eta)/mdot0 = 1 / sqrt(1 + dfL(eta) / fL0)

    delta_max = 3.0 mm is used as a conservative parametric perturbation,
    not a validated NuScale riser corrosion prediction (manuscript
    Section 2.2). Because the nominal riser inner diameter is large, this
    scenario produces a negligible coolant-density change and serves as a
    negative-control case confirming that hydraulic resistance
    perturbations of this magnitude are neutronically insignificant at
    the pin-cell level.
    """
    OXIDE_MAX_M: float = 3e-3     # delta_max = 3.0 mm
    NOMINAL_FL0: float = 5.0      # nominal (normalized) friction parameter

    def compute(self, level: float) -> dict:
        _validate_level(level)
        nc = NominalConditions
        delta_ox  = self.OXIDE_MAX_M * math.sqrt(level)
        D0        = nc.RISER_ID_M
        D_eff     = max(D0 - 2 * delta_ox, D0 * 0.70)
        delta_fL  = (D0 / D_eff) ** 5 - 1.0
        mdot      = nc.MDOT_KG_S / math.sqrt(1.0 + delta_fL / self.NOMINAL_FL0)
        Q_W       = nc.POWER_MWT * 1e6
        CP        = nc.WATER_CP_J_KGK
        T_out     = nc.T_OUTLET_C + (Q_W / mdot / CP - Q_W / nc.MDOT_KG_S / CP)
        return dict(T_inlet_C=nc.T_INLET_C, T_outlet_C=T_out,
                    P_MPa=nc.P_MPa, mdot_kg_s=mdot,
                    riser_friction_increase=delta_fL,
                    sg_ua_reduction=0.0, bypass_fraction=0.0)


# ---------------------------------------------------------------
# Mechanism 2: SG helical-coil primary-side fouling (SG_FOULING)
# ---------------------------------------------------------------
class SGFoulingModel:
    """
    SG helical-coil tube primary-side (shell-side) scale deposition.

    Fouling resistance increases linearly with degradation level
    (manuscript Section 2.2):
        R_f(eta) = R_f,max * eta

    Effective overall heat transfer coefficient:
        1 / U_eff(eta) = 1 / U0 + R_f(eta)
        f_UA(eta)       = U_eff / U0 = 1 / (1 + R_f(eta) * U0)

    A reduction in f_UA lowers the SG heat removal capacity, elevating
    the primary coolant core-average temperature.

    Coolant-state validity ceiling
    --------------------------------
    Because the present simplified workflow assumes single-phase liquid
    coolant properties, a coolant-state validity ceiling is imposed at
    T_sat - 5 degC = 324.41 degC at 12.76 MPa. When the predicted core
    outlet temperature would exceed this limit, the coolant state is
    capped at the last sub-limit condition for all higher degradation
    levels (manuscript Section 2.2).

    This cap is a MODELING CONSTRAINT used to avoid extrapolating the
    single-phase screening model beyond its intended range. It is NOT a
    simulation of an actual reactor protection system trip response.
    Consequently, the coolant density and pin-cell eigenvalue computed
    from this model remain constant beyond eta ~ 0.1, and the effective
    neutronic sensitivity range for SG fouling reported in the
    manuscript is eta in [0, ~0.1].
    """
    MAX_FOULING_RESISTANCE: float = 3e-4    # R_f,max [m^2*K/W]
    NOMINAL_U_W_M2K: float        = 8_000.0  # U0
    T_SAT_C: float                = 329.41   # saturation temperature at 12.76 MPa
    T_SUBCOOL_CEILING_C: float    = 5.0       # subcooling margin defining the validity ceiling

    def _compute_raw(self, level: float) -> dict:
        """Pure physical model, without the coolant-state ceiling applied."""
        nc  = NominalConditions
        R_f = self.MAX_FOULING_RESISTANCE * level
        f_UA = 1.0 / (1.0 + R_f * self.NOMINAL_U_W_M2K)
        sg_ua_reduction = 1.0 - f_UA
        nominal_dT  = nc.T_OUTLET_C - nc.T_INLET_C
        actual_dT   = nominal_dT * f_UA
        T_inlet_new = nc.T_OUTLET_C - actual_dT
        mdot_ratio  = math.sqrt(max(actual_dT / nominal_dT, 0.25))
        mdot        = nc.MDOT_KG_S * mdot_ratio
        Q_W         = nc.POWER_MWT * 1e6
        T_out       = T_inlet_new + Q_W / (mdot * nc.WATER_CP_J_KGK)
        return dict(T_inlet_C=T_inlet_new, T_outlet_C=T_out,
                    P_MPa=nc.P_MPa, mdot_kg_s=mdot,
                    riser_friction_increase=0.0,
                    sg_ua_reduction=sg_ua_reduction, bypass_fraction=0.0)

    def compute(self, level: float) -> dict:
        _validate_level(level)
        raw = self._compute_raw(level)
        T_out = raw['T_outlet_C']
        T_ceiling_limit = self.T_SAT_C - self.T_SUBCOOL_CEILING_C  # 324.41 degC

        # If T_outlet exceeds the single-phase validity ceiling, cap the
        # coolant state at the last sub-limit condition.
        if T_out > T_ceiling_limit:
            # Bisection search for the eta at which the ceiling is first reached.
            lo, hi = 0.0, level
            for _ in range(30):
                mid = (lo + hi) / 2.0
                if self._compute_raw(mid)['T_outlet_C'] > T_ceiling_limit:
                    hi = mid
                else:
                    lo = mid
            return self._compute_raw(lo)  # state immediately below the ceiling

        return raw


# ---------------------------------------------------------------
# Mechanism 3: Core barrel-to-shroud gap bypass leakage (BYPASS_LEAKAGE)
# ---------------------------------------------------------------
class BypassLeakageModel:
    """
    Hot coolant bypass through the core barrel-to-shroud gap.

        x_bp(eta) = x_max * eta
        T_mix     = T_inlet_nom + x_bp * (T_outlet_nom - T_inlet_nom)
        mdot_eff  = mdot0 * (1 - x_bp)
        T_out     = T_mix + Q / (mdot_eff * cp)

    x_max = 0.08 (8%) is used as a representative PWR-scale parametric
    upper bound (manuscript Section 2.2, refs. [6,8]). Because publicly
    available NuScale-specific bypass leakage data are limited, this
    value is not a validated NuScale design parameter but a conservative
    parametric assumption informed by general PWR bypass-flow
    considerations.
    """
    MAX_BYPASS_FRACTION: float = 0.08

    def compute(self, level: float) -> dict:
        _validate_level(level)
        nc   = NominalConditions
        x_bp = self.MAX_BYPASS_FRACTION * level
        mdot = nc.MDOT_KG_S * (1.0 - x_bp)
        T_in = nc.T_INLET_C + x_bp * (nc.T_OUTLET_C - nc.T_INLET_C)
        Q_W  = nc.POWER_MWT * 1e6
        T_out = T_in + Q_W / (mdot * nc.WATER_CP_J_KGK)
        return dict(T_inlet_C=T_in, T_outlet_C=T_out,
                    P_MPa=nc.P_MPa, mdot_kg_s=mdot,
                    riser_friction_increase=0.0,
                    sg_ua_reduction=0.0, bypass_fraction=x_bp)


# ---------------------------------------------------------------
# Unified interface
# ---------------------------------------------------------------
class DegradationModel:
    """
    Note: a fourth "combined" scenario (simultaneous progression of all
    three mechanisms) was evaluated during development but permanently
    removed prior to manuscript submission because its time-weighted
    averaging scheme was found to be physically inconsistent. Only the
    three independent scenarios below are reported in the manuscript.
    """
    _MAP = {
        ScenarioType.RISER_CORROSION: RiserCorrosionModel,
        ScenarioType.SG_FOULING:      SGFoulingModel,
        ScenarioType.BYPASS_LEAKAGE:  BypassLeakageModel,
    }

    def __init__(self, scenario: ScenarioType, **kw):
        self.scenario = scenario
        cls = self._MAP[scenario]
        self._model = cls(**kw) if kw else cls()

    def compute(self, degradation_level: float) -> CoolantState:
        raw = self._model.compute(degradation_level)
        T_avg = (raw['T_inlet_C'] + raw['T_outlet_C']) / 2.0
        return CoolantState(
            scenario=self.scenario,
            degradation_level=degradation_level,
            T_inlet_C=raw['T_inlet_C'], T_outlet_C=raw['T_outlet_C'],
            T_avg_C=T_avg, P_MPa=raw['P_MPa'], mdot_kg_s=raw['mdot_kg_s'],
            riser_friction_increase=raw['riser_friction_increase'],
            sg_ua_reduction=raw['sg_ua_reduction'],
            bypass_fraction=raw['bypass_fraction'],
        )

    def sweep(self, n_steps=21, level_min=0.0, level_max=1.0) -> Iterator[CoolantState]:
        for lv in np.linspace(level_min, level_max, n_steps):
            yield self.compute(float(lv))

    def compare_all(self, level: float) -> dict[str, CoolantState]:
        return {s.name: DegradationModel(s).compute(level) for s in ScenarioType}


def _validate_level(level: float) -> None:
    if not (0.0 <= level <= 1.0):
        raise ValueError(f"degradation_level must be in [0,1], got: {level}")


def generate_sweep_table(scenario: ScenarioType, n_steps=21) -> list[dict]:
    model = DegradationModel(scenario)
    return [{
        'scenario':                st.scenario.name,
        'degradation_level':       round(st.degradation_level, 4),
        'T_inlet_C':               round(st.T_inlet_C, 4),
        'T_outlet_C':              round(st.T_outlet_C, 4),
        'T_avg_C':                 round(st.T_avg_C, 4),
        'delta_T_vs_nominal_C':    round(st.delta_T_vs_nominal_C, 4),
        'P_MPa':                  round(st.P_MPa, 6),
        'mdot_kg_s':               round(st.mdot_kg_s, 4),
        'mdot_ratio':              round(st.mdot_ratio, 5),
        'riser_friction_increase': round(st.riser_friction_increase, 6),
        'sg_ua_reduction':         round(st.sg_ua_reduction, 6),
        'bypass_fraction':        round(st.bypass_fraction, 6),
        'T_moderator_K':          round(st.T_moderator_K, 4),
    } for st in model.sweep(n_steps)]


if __name__ == '__main__':
    import csv
    import sys

    nc = NominalConditions
    print("=" * 65)
    print("NuScale US600-like (160 MWt / 50 MWe) RPV-internal degradation models")
    print(f"  P={nc.P_MPa} MPa  T_avg={nc.T_AVG_C} degC  mdot0={nc.MDOT_KG_S} kg/s")
    print("=" * 65)

    for scenario in ScenarioType:
        print(f"\n{'-' * 55}\n  {scenario.name}\n{'-' * 55}")
        model = DegradationModel(scenario)
        for lv in [0.0, 0.25, 0.5, 0.75, 1.0]:
            print(model.compute(lv).summary())
            print()

    if '--csv' in sys.argv:
        sample = generate_sweep_table(ScenarioType.RISER_CORROSION, 2)
        w = csv.DictWriter(sys.stdout, fieldnames=list(sample[0].keys()))
        w.writeheader()
        for sc in ScenarioType:
            w.writerows(generate_sweep_table(sc))
