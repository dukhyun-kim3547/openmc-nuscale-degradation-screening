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

NuScale US600-like nominal operating conditions (FSAR Tier 2, Rev. 5)
-----------------------------------------------------------------------
  Operating pressure         : 12.755 MPa (1850 psia)      FSAR Table 4.1-1
  Core inlet temperature      : 258.11 degC (496.6 degF)    FSAR Table 5.1-2
  RCS hot-leg temperature      : 310.06 degC (590.1 degF)   FSAR Table 5.1-2
  Core outlet temperature       : 313.59 degC (inlet + 99.8 degF rise)
  Core-average temperature        : 285.85 degC (pin-cell representative state)
  Primary coolant flow rate (RCS): 587.0 kg/s (TOTAL, not the core flow)
  Core bypass fraction              : 0.073 (best estimate)
  Thermal power                      : 160 MWt
  Electric power                      : 50 MWe
  Fuel assemblies                      : 37 (17x17, 2 m active height)
  Control rod assemblies                : 16
  RPV height / outer diameter             : 20 m / 2.7 m
  Core diameter / height                    : 1.5 m / 2.0 m

Note: an earlier version of this module recorded 309.7 degC as the "core
outlet temperature," but that value is the RCS hot-leg temperature (the
riser / SG primary-inlet condition), not the core exit. The state passed
to the pin-cell neutronics model is the core-average coolant temperature,
285.85 degC, and the three temperatures above are kept distinct throughout
this module (reviewer point M10 and pre-submission correction 6).

These nominal values follow the FSAR Tier 2, Rev. 5, tables cited above.
Geometric parameters for internal RPV components (riser, SG annulus)
marked as estimated values are not independently validated NuScale design
parameters and are used only as representative inputs to the parametric
degradation models below.
"""

from __future__ import annotations

import dataclasses
import math
from enum import Enum, auto
from typing import Iterator

import numpy as np
from loop_balance import PlantPoint, solve_loop


# ---------------------------------------------------------------
# NuScale US600-like nominal operating conditions
# ---------------------------------------------------------------
class NominalConditions:
    """
    NuScale US600-like nominal power module (NPM) operating conditions.
    """
    # -- Thermal-hydraulics --------------------------------------
    # Values from the NuScale FSAR Tier 2, Rev. 5:
    #   Table 4.1-1  core power, system pressure, core bypass fraction
    #   Table 5.1-2  primary temperatures and flow, best estimate at 100 % power
    #   Table 5.4-1  steam generator duty and secondary terminal conditions
    #   Table 5.4-2  steam generator heat transfer area and fouling allowance
    #
    # Three distinct primary temperatures are defined. The original model
    # conflated them; they must not be interchanged.
    #   T_INLET_C     core inlet = cold leg = SG primary outlet
    #   T_CORE_AVG_C  core-average coolant -- THIS is the pin-cell state
    #   T_HOT_C       riser = RCS hot leg = SG primary inlet
    POWER_MWT: float       = 160.0
    POWER_MWE: float       = 50.0
    P_MPa: float           = 12.755        # 1850 psia

    T_INLET_C: float       = 258.11        # 496.6 degF
    T_HOT_C: float         = 310.06        # 590.1 degF, riser / SG primary inlet
    T_RCS_AVG_C: float     = 284.06        # 543.3 degF, (inlet + hot) / 2
    T_CORE_OUT_C: float    = 313.59        # core exit, 99.8 degF rise over inlet
    T_CORE_AVG_C: float    = 285.85        # (inlet + core exit) / 2  <-- pin cell

    MDOT_TOTAL_KG_S: float = 587.0         # TOTAL RCS flow, NOT the core flow
    X_BYPASS: float        = 0.073         # core bypass fraction, best estimate
    MDOT_MIN_KG_S: float   = 538.5         # minimum design flow at 100 % power
    MDOT_MAX_KG_S: float   = 660.5         # maximum design flow at 100 % power

    # WATER_CP_J_KGK removed on purpose. A constant specific heat is not
    # adequate over a 55 K core rise: the IF97 value runs from about 4840 to
    # 6000 J/(kg*K). All energy balances now use IF97 enthalpy differences.

    # -- Steam generator ------------------------------------------
    SG_DUTY_W: float       = 159.13e6      # both SGs together
    SG_AREA_M2: float      = 1665.6        # 17928 ft2, module total
    SG_U0_W_M2K: float     = 3186.0        # from duty, area and nominal LMTD
    SG_T_FEED_C: float     = 148.72        # 299.7 degF
    SG_T_STEAM_C: float    = 306.89        # 584.4 degF
    RF_DESIGN_M2K_W: float = 1.761e-5      # 0.0001 hr-ft2-degF/BTU allowance
    RF_EOL_M2K_W: float    = 8.0e-5        # 60-year deposit, Turner et al.

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
    RISER_ID_M: float     = 1.350   # FSAR Table 4.4-1, upper riser 15.4 ft2 equivalent diameter
    RISER_OD_M: float     = 1.56       # estimated, 30 mm wall thickness
    RISER_HEIGHT_M: float = 10.0       # estimated effective natural-circulation driving height

    # SG annular region: hot riser outer wall to RPV inner wall
    SG_ANNULUS_WIDTH_M: float = (2.5 - 1.56) / 2.0   # ~0.47 m, estimated

    # Design life
    DESIGN_LIFE_YR: float = 60.0


# ---------------------------------------------------------------
# Loop-balance bridge (reviewer points M3, M7, M8, M9)
# ---------------------------------------------------------------
def _plant_point(x_bypass=None):
    """Build the loop-closure input from NominalConditions."""
    nc = NominalConditions
    return PlantPoint(
        P_MPa=nc.P_MPa,
        Q_core_W=nc.POWER_MWT * 1e6,
        Q_sg_W=nc.SG_DUTY_W,
        sg_area_m2=nc.SG_AREA_M2,
        sg_U0_W_m2K=nc.SG_U0_W_M2K,
        sg_T_feed_C=nc.SG_T_FEED_C,
        sg_T_steam_C=nc.SG_T_STEAM_C,
        T_cold_guess_C=nc.T_INLET_C,
        T_hot_guess_C=nc.T_HOT_C,
        mdot_guess_kg_s=nc.MDOT_TOTAL_KG_S,
        x_bypass=nc.X_BYPASS if x_bypass is None else x_bypass,
    )


def _as_dict(st, riser_dfl=0.0, sg_ua_red=0.0, x_bp=None):
    """
    Map a LoopState onto the dict shape the rest of the pipeline expects.

    T_inlet_C and T_outlet_C are the CORE inlet and CORE outlet, so that the
    T_avg computed downstream in DegradationModel.compute() is the core-average
    coolant temperature. The original model returned the RCS hot-leg
    temperature here, which is a different quantity.
    """
    nc = NominalConditions
    return dict(
        T_inlet_C=st.T_cold_C,
        T_outlet_C=st.T_core_out_C,
        P_MPa=nc.P_MPa,
        mdot_kg_s=st.mdot_total_kg_s,
        riser_friction_increase=riser_dfl,
        sg_ua_reduction=sg_ua_red,
        bypass_fraction=nc.X_BYPASS if x_bp is None else x_bp,
    )


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
        return self.T_avg_C - NominalConditions.T_CORE_AVG_C

    @property
    def delta_P_vs_nominal_MPa(self) -> float:
        return self.P_MPa - NominalConditions.P_MPa

    @property
    def mdot_ratio(self) -> float:
        return self.mdot_kg_s / NominalConditions.MDOT_TOTAL_KG_S

    def summary(self) -> str:
        nc = NominalConditions
        return (
            f"[{self.scenario.name}] eta={self.degradation_level:.3f}\n"
            f"  T_inlet  : {self.T_inlet_C:7.2f} degC  (d{self.T_inlet_C - nc.T_INLET_C:+.2f})\n"
            f"  T_outlet : {self.T_outlet_C:7.2f} degC  (d{self.T_outlet_C - nc.T_CORE_OUT_C:+.2f})\n"
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

    delta(eta) = delta_max * sqrt(eta), an assumed parabolic profile.

    The hydraulic response is delegated to loop_balance.solve_loop(), which
    applies both the flow-area reduction and the added surface roughness and
    lets the buoyancy head respond (reviewer points M7 and M9). An earlier
    version applied a fixed (D0/D_eff)^5 resistance ratio with the buoyancy
    head held constant, which modeled only half of the coupling and left
    roughness out altogether.

    Roughness is the dominant hydraulic effect for a deposit, but the riser is
    hydraulically smooth: at 3 um the relative roughness is 2e-6 and even a
    50 um deposit gives 4e-5, against Re of about 6.6e6. The scenario is
    therefore a measured null rather than an assumed one, and the loop
    temperatures do not move at any level. delta_max = 3.0 mm is used as a
    conservative parametric perturbation, not a validated NuScale riser
    corrosion prediction (manuscript Section 2.2); because the nominal riser
    inner diameter is large, this scenario serves as a negative-control case.
    """
    OXIDE_MAX_M: float = 3e-3     # delta_max = 3.0 mm
    DEPOSIT_ROUGHNESS_M: float = 3e-6   # added RMS roughness of magnetite deposit, Turner et al. (2000)
    NOMINAL_FL0: float = 5.0      # nominal (normalized) friction parameter

    def compute(self, level: float) -> dict:
        """
        Oxide growth on the riser inner wall, solved with the loop balance.

        Both the flow-area reduction and the added surface roughness are
        applied, and the buoyancy head is allowed to respond to the resulting
        temperature change (reviewer points M7 and M9). The original model
        held the buoyancy head fixed while changing only the resistance.
        """
        _validate_level(level)
        delta_ox = self.OXIDE_MAX_M * math.sqrt(level)
        st = solve_loop(_plant_point(),
                        delta_ox_m=delta_ox,
                        eps_m=self.DEPOSIT_ROUGHNESS_M)
        return _as_dict(st, riser_dfl=st.riser_friction_increase)


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

    Single-phase validity (reviewer point M10)
    ------------------------------------------
    T_sat = 329.38 degC at 12.755 MPa. No subcooling threshold is imposed.
    An earlier version froze the thermal-hydraulic state once the core outlet
    came within a fixed margin of saturation, which is what produced the
    plateau the reviewer identified; that construction has been removed.

    With R_f anchored to measured deposit data the whole swept range is
    single-phase. The core-outlet subcooling margin runs 15.70 K at eta = 0 to
    12.41 K at eta = 1, and the smallest margin anywhere in the three scenarios
    is 11.36 K, in the bypass extrapolation to 15 %. The margin is reported at
    every level rather than tested: a bulk pin cell carries one core-average
    coolant state and cannot resolve the hot channel where subcooled nucleate
    boiling actually begins, so a threshold on bulk subcooling would claim a
    capability this model does not have.
    """
    MAX_FOULING_RESISTANCE: float = NominalConditions.RF_EOL_M2K_W   # 8e-5, Turner et al. (2000, 2013); FSAR design allowance 1.76e-5
    NOMINAL_U_W_M2K: float        = NominalConditions.SG_U0_W_M2K   # 3186 W/m2K from FSAR duty, area and nominal LMTD
    T_SAT_C: float                = 329.38   # saturation temperature at 12.755 MPa, IF97

    def _compute_raw(self, level: float) -> dict:
        """
        Steam generator fouling, closed on an explicit energy balance.

        Q_sg = U_eff * A * LMTD(T_hot, T_cold; secondary fixed), with
        U_eff = U0 / (1 + R_f * U0). Areas, duty, secondary terminal
        conditions and U0 all come from the FSAR (reviewer point M3).
        """
        R_f = self.MAX_FOULING_RESISTANCE * level
        st = solve_loop(_plant_point(), r_fouling_m2K_W=R_f)
        return _as_dict(st, sg_ua_red=1.0 - st.f_UA)

    def compute(self, level: float) -> dict:
        """
        Steam generator fouling. No subcooling threshold is applied (M10).

        The only condition asserted is that the bulk core outlet stays below
        saturation, because the single-phase IF97 formulation is not defined
        above it. That condition is never approached over the swept range: the
        margin is 15.70 K at eta = 0 and 12.41 K at eta = 1.

        A state that did reach saturation would be raised, not silently
        replaced by a frozen one. Freezing is what produced the plateau the
        reviewer objected to, and it hid the fact that the input pair had left
        the single-phase region.
        """
        _validate_level(level)
        raw = self._compute_raw(level)
        if raw['T_outlet_C'] >= self.T_SAT_C:
            raise ValueError(
                f"core outlet {raw['T_outlet_C']:.2f} degC reaches saturation "
                f"({self.T_SAT_C:.2f} degC) at eta = {level:.3f}; the "
                f"single-phase property routine does not apply to this state"
            )
        return raw


# ---------------------------------------------------------------
# Mechanism 3: Core barrel-to-shroud gap bypass leakage (BYPASS_LEAKAGE)
# ---------------------------------------------------------------
class BypassLeakageModel:
    """
    Hot coolant bypass through the core barrel-to-shroud gap.

    Bypass diverts cold downcomer flow around the fuel (reviewer point M8).
    The core inlet temperature is unchanged, the core flow is reduced, and the
    bypassed stream rejoins the core exit flow in the upper plenum. An earlier
    version additionally mixed hot outlet coolant into the inlet, charging the
    bypass fraction twice and overpredicting the core-average temperature rise
    by a factor of about 2.8.

        x_bp(eta) = X_BYPASS + (MAX_BYPASS_FRACTION - X_BYPASS) * eta

    eta = 0 is the FSAR best-estimate bypass of 7.3 % (Table 4.1-1), not zero.
    The FSAR analytical value of 8.5 % falls at eta = 0.156; levels above that
    are an explicit extrapolation beyond the design basis and are labeled as
    such wherever they are plotted.
    """
    MAX_BYPASS_FRACTION: float = 0.15   # total bypass at eta = 1; design 7.3 %, analytical 8.5 %, beyond that extrapolated

    def compute(self, level: float) -> dict:
        """
        Core bypass, corrected and re-anchored (reviewer point M8).

        Bypass diverts cold downcomer flow around the fuel. The core inlet
        temperature is therefore unchanged and only the core flow is reduced;
        the bypassed stream rejoins downstream. The original model additionally
        mixed hot outlet coolant into the inlet, charging the bypass fraction
        twice and overpredicting the core-average temperature rise by a factor
        of about 2.8.

        eta = 0 is the FSAR best-estimate bypass of 7.3 % (Table 4.1-1), not
        zero. The FSAR analytical value of 8.5 % falls at eta = 0.156; higher
        levels are an explicit extrapolation beyond the design basis.
        """
        _validate_level(level)
        nc = NominalConditions
        x_bp = nc.X_BYPASS + (self.MAX_BYPASS_FRACTION - nc.X_BYPASS) * level
        st = solve_loop(_plant_point(x_bypass=x_bp), x_bypass=x_bp)
        return _as_dict(st, x_bp=x_bp)


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
    print(f"  P={nc.P_MPa} MPa  T_avg={nc.T_CORE_AVG_C} degC  mdot0={nc.MDOT_TOTAL_KG_S} kg/s")
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
