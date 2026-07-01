"""
parametric_sweep.py
===================
OpenMC parametric sweep driver for the NuScale US600-like SMR
degradation neutronics screening study.

Companion code for:
  Kim, D. "Screening-Level Pin-Cell Neutronic Sensitivity of a NuScale
  US600-Like SMR Fuel Lattice to Coolant-Density Perturbations from
  Simplified Primary-System Degradation Models." Journal of Nuclear
  Engineering (submitted).

Scope and limitations
----------------------
This script drives a two-dimensional (2D) infinite reflective pin-cell
OpenMC eigenvalue calculation. It does NOT represent the full NuScale
US600 core geometry. The computed eigenvalue is a lattice-level
multiplication factor (k-infinity), not a full-core effective
multiplication factor. See manuscript Section 2.5 for the full scope
and limitations discussion.

NuScale US600-like pin-cell specification (manuscript Section 2.4)
------------------------------------------------------------------
  2D infinite lattice (XY reflective, infinite in Z)
  Fuel pellet radius   : 0.4095 cm   (UO2, 4.95 wt% U235)
  He gap outer radius  : 0.4178 cm
  Cladding outer radius: 0.4750 cm   (Zircaloy-4)
  Pin pitch            : 1.26 cm
  UO2 density          : 10.4 g/cm^3 (~95% theoretical density)
  H/U ratio            : ~3.62        (undermoderated spectrum)
  Fuel temperature     : 900 K (fixed; beginning-of-life, fresh UO2)
  Nuclear data         : ENDF/B-VIII.0 (manuscript ref. [18])
  S(alpha,beta)        : c_H_in_H2O for hydrogen in water

Usage
-----
  # Set nuclear data path (once)
  export OPENMC_CROSS_SECTIONS=/path/to/endfb80_hdf5/cross_sections.xml

  # Quick pipeline test (100 particles, ~10 s)
  python parametric_sweep.py --test

  # Single scenario sweep
  python parametric_sweep.py --scenario SG_FOULING --n-steps 21

  # All three scenarios sequentially
  python parametric_sweep.py --all-scenarios

  # High-statistics run as used in the manuscript
  python parametric_sweep.py --all-scenarios --particles 500000 --batches 200 --inactive 100

Design basis: NuScale US600-like configuration, 160 MWt / 50 MWe
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import shutil
import time
import warnings
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import numpy as np

from degradation_scenarios import (
    DegradationModel, NominalConditions, ScenarioType,
)
from iapws_coolant import PhysicsLimits, from_coolant_state

try:
    import openmc
    OPENMC_AVAILABLE = True
except ImportError:
    OPENMC_AVAILABLE = False
    warnings.warn(
        "openmc package not found. Running in Mock mode (MTC-based estimate).",
        ImportWarning,
    )

warnings.filterwarnings("ignore")


# ---------------------------------------------------------------
# Pin-cell geometry constants
# ---------------------------------------------------------------
class PinCell:
    """
    NuScale US600-like standard pin-cell dimensions
    (17x17 Westinghouse-type fuel assembly; manuscript Section 2.4).
    """
    PITCH        = 1.26      # pin pitch [cm]
    R_FUEL       = 0.4095    # fuel pellet radius [cm]
    R_GAP        = 0.4178    # He gap outer radius [cm]
    R_CLAD       = 0.4750    # cladding outer radius [cm]
    # UO2 composition (atom fraction, OpenMC normalizes automatically)
    # 4.95 wt% U235 -> ~5.010 at% U235
    AO_U235      = 0.050102  # U235 atom fraction (within uranium)
    AO_U238      = 0.949898  # U238 atom fraction
    AO_O_PER_U   = 2.0       # O atoms per U atom (UO2 stoichiometry)
    FUEL_DENSITY = 10.4      # UO2 density [g/cm^3] (~95% theoretical)
    CLAD_DENSITY = 6.55      # Zircaloy-4 [g/cm^3]
    GAP_DENSITY  = 1.598e-4  # He at operating pressure [g/cm^3]
    T_FUEL_K     = 900.0     # fuel temperature [K] (fixed for all cases)


# ---------------------------------------------------------------
# Nuclear data path detection
# ---------------------------------------------------------------
def _find_cross_sections(user_path: Optional[str] = None) -> Optional[str]:
    """
    Locate the ENDF/B-VIII.0 cross_sections.xml file.

    Search order:
      1) user-supplied path (--nuclear-data argument)
      2) OPENMC_CROSS_SECTIONS environment variable
      3) common installation locations
    """
    candidates = []
    if user_path:
        candidates.append(user_path)
    env_path = os.environ.get("OPENMC_CROSS_SECTIONS")
    if env_path:
        candidates.append(env_path)
    for search in [
        "/opt/openmc/data/cross_sections.xml",
        "/usr/local/share/openmc/cross_sections.xml",
        os.path.expanduser("~/openmc-data/cross_sections.xml"),
        os.path.expanduser("~/endfb80_hdf5/cross_sections.xml"),
        os.path.expanduser("~/nndc_hdf5/cross_sections.xml"),
    ]:
        candidates.append(search)
    for path in candidates:
        if path and Path(path).exists():
            return str(path)
    return None


# ---------------------------------------------------------------
# 2D infinite pin-cell model builder
# ---------------------------------------------------------------
def build_pincell_model(
        coolant_density: float,
        T_moderator_K:   float,
        particles:  int = 10_000,
        batches:    int = 110,
        inactive:   int = 10,
        run_dir:    Path = Path("openmc_run"),
) -> tuple:
    """
    Build and export the NuScale US600-like 2D infinite pin-cell
    OpenMC model (manuscript Section 2.4).

    The model uses:
    - XY reflective boundary conditions (true 2D infinite lattice)
    - No axial boundaries (k-infinity geometry)
    - UO2 composition specified in atom fractions (auto-normalized)
    - Explicit XPlane/YPlane surfaces for version compatibility
    - S(alpha,beta) thermal scattering for H in water

    Parameters
    ----------
    coolant_density : float
        Coolant density [g/cm^3] from the IAPWS-IF97 pipeline
    T_moderator_K : float
        Moderator temperature [K] for material and cell temperature
    particles : int
        Number of particles per batch
    batches : int
        Total number of batches (including inactive)
    inactive : int
        Number of inactive (source-convergence) batches
    run_dir : Path
        Directory to write OpenMC XML input files

    Returns
    -------
    (materials, geometry, settings, tallies)
    """
    pc = PinCell

    # -- Materials -----------------------------------------------
    fuel = openmc.Material(name="fuel_uo2")
    fuel.add_nuclide("U235", pc.AO_U235,     "ao")
    fuel.add_nuclide("U238", pc.AO_U238,     "ao")
    fuel.add_nuclide("O16",  pc.AO_O_PER_U, "ao")
    fuel.set_density("g/cm3", pc.FUEL_DENSITY)
    fuel.temperature = pc.T_FUEL_K

    coolant = openmc.Material(name="coolant")
    coolant.add_nuclide("H1",  2.0, "ao")
    coolant.add_nuclide("O16", 1.0, "ao")
    coolant.add_s_alpha_beta("c_H_in_H2O")
    coolant.set_density("g/cm3", coolant_density)
    coolant.temperature = T_moderator_K

    clad = openmc.Material(name="cladding_zry4")
    clad.add_element("Zr", 0.982, "wo")
    clad.add_element("Sn", 0.015, "wo")
    clad.add_element("Fe", 0.002, "wo")
    clad.add_element("Cr", 0.001, "wo")
    clad.set_density("g/cm3", pc.CLAD_DENSITY)
    clad.temperature = T_moderator_K

    gap = openmc.Material(name="gap_he")
    gap.add_element("He", 1.0, "ao")
    gap.set_density("g/cm3", pc.GAP_DENSITY)
    gap.temperature = T_moderator_K

    materials = openmc.Materials([fuel, gap, clad, coolant])
    materials.export_to_xml(str(run_dir / "materials.xml"))

    # -- Geometry (2D infinite pin cell) -------------------------
    fuel_cyl = openmc.ZCylinder(r=pc.R_FUEL)
    gap_cyl  = openmc.ZCylinder(r=pc.R_GAP)
    clad_cyl = openmc.ZCylinder(r=pc.R_CLAD)

    # Explicit XPlane/YPlane for version compatibility
    left  = openmc.XPlane(-pc.PITCH / 2, boundary_type="reflective")
    right = openmc.XPlane(+pc.PITCH / 2, boundary_type="reflective")
    front = openmc.YPlane(-pc.PITCH / 2, boundary_type="reflective")
    back  = openmc.YPlane(+pc.PITCH / 2, boundary_type="reflective")
    box   = +left & -right & +front & -back

    fuel_cell    = openmc.Cell(fill=fuel,    region=-fuel_cyl,            name="fuel")
    gap_cell     = openmc.Cell(fill=gap,     region=+fuel_cyl & -gap_cyl, name="gap")
    clad_cell    = openmc.Cell(fill=clad,    region=+gap_cyl & -clad_cyl, name="clad")
    coolant_cell = openmc.Cell(fill=coolant, region=+clad_cyl & box,      name="coolant")
    coolant_cell.temperature = T_moderator_K

    universe = openmc.Universe(cells=[fuel_cell, gap_cell, clad_cell, coolant_cell])
    geometry = openmc.Geometry(universe)
    geometry.export_to_xml(str(run_dir / "geometry.xml"))

    # -- Settings ------------------------------------------------
    settings = openmc.Settings()
    settings.run_mode  = "eigenvalue"
    settings.particles = particles
    settings.batches   = batches
    settings.inactive  = inactive
    settings.temperature = {
        "default": T_moderator_K,
        "method":  "interpolation",
    }
    settings.source = openmc.IndependentSource(
        space=openmc.stats.Box(
            [-pc.PITCH / 2, -pc.PITCH / 2, -1],
            [ pc.PITCH / 2,  pc.PITCH / 2,  1],
        )
    )
    settings.export_to_xml(str(run_dir / "settings.xml"))

    # -- Tallies (neutron flux spectrum) -------------------------
    e_filter   = openmc.EnergyFilter(np.logspace(-3, 7, 121))  # 0.001 eV - 10 MeV
    flux_tally = openmc.Tally(name="flux_spectrum")
    flux_tally.filters = [e_filter]
    flux_tally.scores  = ["flux"]

    tallies = openmc.Tallies([flux_tally])
    tallies.export_to_xml(str(run_dir / "tallies.xml"))

    return materials, geometry, settings, tallies


# ---------------------------------------------------------------
# OpenMC execution and result collection
# ---------------------------------------------------------------
def run_and_collect(run_dir: Path, batches: int) -> tuple[float, float]:
    """
    Execute OpenMC in run_dir and return (keff, keff_std).

    Uses glob to locate the statepoint file, which avoids
    dependence on the exact batch number in the filename.
    """
    orig_dir = Path.cwd()
    os.chdir(run_dir)
    try:
        openmc.run(output=False)
        sp_files = sorted(glob.glob("statepoint.*.h5"))
        if not sp_files:
            raise FileNotFoundError(
                f"No statepoint file found in {run_dir}"
            )
        with openmc.StatePoint(sp_files[-1]) as sp:
            keff     = float(sp.keff.n)
            keff_std = float(sp.keff.s)
    finally:
        os.chdir(orig_dir)
    return keff, keff_std


# ---------------------------------------------------------------
# Result data class
# ---------------------------------------------------------------
@dataclass
class SweepPoint:
    scenario:           str
    degradation_level:  float
    T_inlet_C:          float
    T_outlet_C:         float
    T_avg_C:            float
    T_moderator_K:      float
    P_MPa:              float
    mdot_kg_s:          float
    rho_g_cm3:          float
    delta_rho_pct:      float
    phase:              str
    subcooling_C:       float
    keff:               float
    keff_std:           float
    delta_keff_pcm:     float
    is_safe:            bool
    wall_time_s:        float


# ---------------------------------------------------------------
# Parametric sweep engine
# ---------------------------------------------------------------
class ParametricSweep:
    """
    Run and store a degradation-level parametric sweep.

    The sweep implements the one-way property-update workflow described
    in the manuscript (Section 2): for each degradation level eta,
    the coolant density is computed via the IAPWS-IF97 pipeline and
    passed to a fresh OpenMC pin-cell eigenvalue calculation. Results
    are stored as SweepPoint instances and can be exported to CSV/JSON.

    Example
    -------
    sweep = ParametricSweep(
        scenario=ScenarioType.SG_FOULING,
        n_steps=21,
        particles=500_000,
        batches=200,
        inactive=100,
        output_dir="results",
    )
    sweep.run()
    sweep.save_csv()
    sweep.print_summary()
    """

    def __init__(
            self,
            scenario:          ScenarioType = ScenarioType.SG_FOULING,
            n_steps:           int   = 21,
            particles:         int   = 50_000,
            batches:           int   = 110,
            inactive:          int   = 10,
            output_dir:        str   = "results",
            nuclear_data_path: Optional[str] = None,
            verbose:           bool  = True,
    ):
        self.scenario   = scenario
        self.n_steps    = n_steps
        self.particles  = particles
        self.batches    = batches
        self.inactive   = inactive
        self.out_dir    = Path(output_dir)
        self.ndata_path = nuclear_data_path
        self.verbose    = verbose
        self.results:   list[SweepPoint] = []
        self._k_nominal: Optional[float] = None

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg, flush=True)

    def _setup_nuclear_data(self) -> None:
        """Locate and configure the ENDF/B-VIII.0 nuclear data library."""
        xs_path = _find_cross_sections(self.ndata_path)
        if xs_path:
            openmc.config["cross_sections"] = xs_path
            self._log(f"  Nuclear data: {xs_path}")
        else:
            raise EnvironmentError(
                "\nCould not find nuclear data library (cross_sections.xml).\n"
                "Please run one of the following:\n"
                "  export OPENMC_CROSS_SECTIONS=/path/to/cross_sections.xml\n"
                "or use the --nuclear-data argument."
            )

    def _run_single(self, level: float) -> tuple[float, float, float]:
        """
        Run OpenMC at a single degradation level eta.
        Returns (keff, keff_std, wall_time_s).
        """
        th    = DegradationModel(self.scenario).compute(level)
        props = from_coolant_state(th)

        run_dir = self.out_dir / "openmc_runs" / f"eta_{level:.4f}"
        run_dir.mkdir(parents=True, exist_ok=True)

        t0 = time.perf_counter()

        if OPENMC_AVAILABLE:
            build_pincell_model(
                coolant_density = props.openmc_material_density(),
                T_moderator_K   = props.T_K,
                particles       = self.particles,
                batches         = self.batches,
                inactive        = self.inactive,
                run_dir         = run_dir,
            )
            keff, keff_std = run_and_collect(run_dir, self.batches)
        else:
            # Mock fallback (MTC-based linear estimate)
            # Note: this is for pipeline testing ONLY and does NOT
            # reproduce the manuscript results. All reported results
            # were obtained with OPENMC_AVAILABLE = True.
            MTC_pcm = -30.0
            k0      = 1.0320
            nc      = NominalConditions
            dT      = props.T_C - nc.T_AVG_C
            drho    = props.delta_rho_pct
            keff     = k0 + (MTC_pcm * dT + (-120.0) * abs(drho) * np.sign(drho)) * 1e-5
            keff_std = 0.00015 + abs(np.random.normal(0, 0.00003))
            time.sleep(0.01)

        return keff, abs(keff_std), time.perf_counter() - t0

    def run(self) -> list[SweepPoint]:
        """Execute the full degradation-level sweep."""
        self.out_dir.mkdir(parents=True, exist_ok=True)
        mode = "OpenMC" if OPENMC_AVAILABLE else "Mock (pipeline test only)"

        if OPENMC_AVAILABLE:
            self._setup_nuclear_data()

        self._log("=" * 65)
        self._log(f"NuScale US600-like pin-cell neutronics sweep  [{mode}]")
        self._log(f"  Scenario      : {self.scenario.name}")
        self._log(f"  Steps         : {self.n_steps}  (eta = 0.0 -> 1.0)")
        self._log(f"  Particles/batch: {self.particles:,}  Batches: {self.batches}")
        self._log(f"  Inactive       : {self.inactive}  Active: {self.batches - self.inactive}")
        self._log(f"  Output dir     : {self.out_dir.resolve()}")
        self._log("=" * 65)

        levels = np.linspace(0.0, 1.0, self.n_steps)
        self.results = []

        for i, level in enumerate(levels):
            th    = DegradationModel(self.scenario).compute(float(level))
            props = from_coolant_state(th)

            if not props.is_safe():
                self._log(
                    f"  [eta={level:.3f}] Coolant state approaches "
                    f"single-phase validity limit "
                    f"(T_outlet={th.T_outlet_C:.1f} degC, phase={props.phase}) "
                    f"-- continuing with capped state"
                )

            keff, keff_std, wt = self._run_single(float(level))

            if i == 0:
                self._k_nominal = keff
            delta_pcm = (keff - self._k_nominal) * 1e5

            pt = SweepPoint(
                scenario          = self.scenario.name,
                degradation_level = round(float(level), 4),
                T_inlet_C         = round(th.T_inlet_C, 4),
                T_outlet_C        = round(th.T_outlet_C, 4),
                T_avg_C           = round(th.T_avg_C, 4),
                T_moderator_K     = round(props.T_K, 4),
                P_MPa             = round(th.P_MPa, 6),
                mdot_kg_s         = round(th.mdot_kg_s, 4),
                rho_g_cm3         = round(props.rho_g_cm3, 7),
                delta_rho_pct     = round(props.delta_rho_pct, 5),
                phase             = props.phase,
                subcooling_C      = round(props.subcooling_C, 3),
                keff              = round(keff, 6),
                keff_std          = round(keff_std, 6),
                delta_keff_pcm    = round(delta_pcm, 2),
                is_safe           = props.is_safe(),
                wall_time_s       = round(wt, 2),
            )
            self.results.append(pt)

            eta_pct = (i + 1) / len(levels) * 100
            self._log(
                f"  [{eta_pct:5.1f}%]  eta={level:.3f}  "
                f"T={props.T_C:.2f} degC  rho={props.rho_g_cm3:.6f} g/cm^3  "
                f"k={keff:.5f}+/-{keff_std:.5f}  "
                f"Dk={delta_pcm:+.1f} pcm  ({wt:.1f}s)"
            )

        total_time = sum(r.wall_time_s for r in self.results)
        self._log(
            f"\n  Completed: {len(self.results)} points  "
            f"Total wall time: {total_time:.1f} s"
        )
        return self.results

    # -- Output --------------------------------------------------
    def save_csv(self, fname: Optional[str] = None) -> Path:
        fname = fname or f"keff_vs_degradation_{self.scenario.name.lower()}.csv"
        path  = self.out_dir / fname
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(asdict(self.results[0]).keys()))
            w.writeheader()
            w.writerows([asdict(r) for r in self.results])
        self._log(f"  -> CSV : {path}")
        return path

    def save_json(self, fname: Optional[str] = None) -> Path:
        fname = fname or f"keff_vs_degradation_{self.scenario.name.lower()}.json"
        path  = self.out_dir / fname
        meta  = {
            "description": (
                "Screening-level NuScale US600-like pin-cell "
                "neutronics degradation sweep"
            ),
            "manuscript": (
                "Kim, D. Screening-Level Pin-Cell Neutronic Sensitivity "
                "of a NuScale US600-Like SMR Fuel Lattice to Coolant-Density "
                "Perturbations from Simplified Primary-System Degradation Models. "
                "Journal of Nuclear Engineering (submitted)."
            ),
            "model"      : "2D infinite pin cell, 17x17 Westinghouse-type",
            "scenario"   : self.scenario.name,
            "n_steps"    : self.n_steps,
            "particles"  : self.particles,
            "batches"    : self.batches,
            "inactive"   : self.inactive,
            "mode"       : "OpenMC" if OPENMC_AVAILABLE else "Mock",
            "nominal_keff": self._k_nominal,
            "data"       : [asdict(r) for r in self.results],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        self._log(f"  -> JSON: {path}")
        return path

    # -- Analysis ------------------------------------------------
    def compute_sensitivity(self) -> dict:
        """
        Compute apparent sensitivity coefficients from the sweep results.

        Note: these are apparent scenario-dependent sensitivities derived
        from linear regression over the coolant states generated by the
        simplified degradation models. They should NOT be interpreted as
        licensing-grade moderator temperature coefficients or void
        coefficients (manuscript Section 3.4).
        """
        safe = [r for r in self.results if r.is_safe]
        if len(safe) < 3:
            return {"error": "Fewer than 3 points within diagnostic thresholds"}

        T   = np.array([r.T_avg_C           for r in safe])
        rho = np.array([r.delta_rho_pct     for r in safe])
        k   = np.array([r.keff              for r in safe])
        eta = np.array([r.degradation_level for r in safe])

        MTC  = np.polyfit(T,   k, 1)[0] * 1e5
        VC   = np.polyfit(rho, k, 1)[0] * 1e5
        dkde = np.polyfit(eta, k, 1)[0] * 1e5

        k_all = np.array([r.keff for r in self.results])
        return {
            "apparent_temp_sensitivity_pcm_per_C"   : round(float(MTC),  2),
            "apparent_density_response_pcm_per_pct" : round(float(VC),   2),
            "dk_d_eta_pcm"                          : round(float(dkde), 1),
            "delta_keff_pcm_max"                    : round(float((k_all.min() - k_all[0]) * 1e5), 1),
            "eta_within_thresholds_max"             : float(max(r.degradation_level for r in safe)),
            "n_within_thresholds"                   : len(safe),
            "n_total"                               : len(self.results),
        }

    def print_summary(self) -> None:
        sens = self.compute_sensitivity()
        print(f"\n{'-' * 70}")
        print(f"  {self.scenario.name}  --  sweep summary")
        print(f"{'-' * 70}")
        print(f"  {'eta':>6}  {'T_avg(degC)':>12}  {'rho(g/cm3)':>11}  "
              f"{'k-eff':>9}  {'Dk(pcm)':>9}  {'sigma':>8}")
        for r in self.results:
            flag = " [threshold]" if not r.is_safe else ""
            print(f"  {r.degradation_level:>6.3f}  "
                  f"{r.T_avg_C:>12.3f}  "
                  f"{r.rho_g_cm3:>11.6f}  "
                  f"{r.keff:>9.5f}  "
                  f"{r.delta_keff_pcm:>+9.2f}  "
                  f"{r.keff_std:>8.5f}{flag}")
        print(f"\n  Apparent temp sensitivity    : "
              f"{sens.get('apparent_temp_sensitivity_pcm_per_C', '?'):>8} pcm/degC")
        print(f"  Apparent density response    : "
              f"{sens.get('apparent_density_response_pcm_per_pct', '?'):>8} pcm/%")
        print(f"  dk/d_eta                     : "
              f"{sens.get('dk_d_eta_pcm', '?'):>8} pcm/eta")
        print(f"  Max eigenvalue change        : "
              f"{sens.get('delta_keff_pcm_max', '?'):>8} pcm")


# ---------------------------------------------------------------
# Quick pipeline test
# ---------------------------------------------------------------
def run_test(
        output_dir: str = "results",
        nuclear_data: Optional[str] = None,
) -> None:
    """
    Run a minimal 3-point sweep with 100 particles to verify the
    full pipeline before committing to a production run.
    """
    if not OPENMC_AVAILABLE:
        print("OpenMC not available. Cannot run test.")
        return

    print("=" * 60)
    print("Quick pipeline test (100 particles, 3 points)")
    print("=" * 60)

    sweep = ParametricSweep(
        scenario=ScenarioType.BYPASS_LEAKAGE,
        n_steps=3,
        particles=100,
        batches=20,
        inactive=5,
        output_dir=output_dir,
        nuclear_data_path=nuclear_data,
        verbose=True,
    )
    try:
        results = sweep.run()
        print(f"\nPipeline test passed.")
        print(f"  eta=0.0  k = {results[0].keff:.5f} +/- {results[0].keff_std:.5f}")
        print(f"  eta=0.5  k = {results[1].keff:.5f} +/- {results[1].keff_std:.5f}")
        print(f"  eta=1.0  k = {results[2].keff:.5f} +/- {results[2].keff_std:.5f}")
        print("\nReady to run production sweep.")
    except Exception as e:
        print(f"\nTest failed: {e}")
        raise


# ---------------------------------------------------------------
# CLI
# ---------------------------------------------------------------
def _parse():
    p = argparse.ArgumentParser(
        description=(
            "Screening-level NuScale US600-like pin-cell neutronics "
            "degradation parametric sweep"
        )
    )
    p.add_argument(
        "--test", action="store_true",
        help="Run quick pipeline test (100 particles, 3 points)",
    )
    p.add_argument(
        "--scenario", default="SG_FOULING",
        choices=[s.name for s in ScenarioType],
        help="Degradation scenario to sweep (default: SG_FOULING)",
    )
    p.add_argument(
        "--all-scenarios", action="store_true",
        help="Run all three scenarios sequentially",
    )
    p.add_argument("--n-steps",     type=int, default=21,
                   help="Number of degradation levels (default: 21)")
    p.add_argument("--particles",   type=int, default=50_000,
                   help="Particles per batch (default: 50000; manuscript used 500000)")
    p.add_argument("--batches",     type=int, default=110,
                   help="Total batches (default: 110; manuscript used 200)")
    p.add_argument("--inactive",    type=int, default=10,
                   help="Inactive batches (default: 10; manuscript used 100)")
    p.add_argument("--output-dir",  default="results",
                   help="Directory for CSV/JSON output and OpenMC run directories")
    p.add_argument("--nuclear-data", default=None,
                   help="Path to ENDF/B-VIII.0 cross_sections.xml")
    return p.parse_args()


if __name__ == "__main__":
    np.random.seed(42)
    args = _parse()

    if args.test:
        run_test(args.output_dir, args.nuclear_data)
    else:
        scenarios = (
            list(ScenarioType) if args.all_scenarios
            else [ScenarioType[args.scenario]]
        )
        all_results = {}
        for sc in scenarios:
            sweep = ParametricSweep(
                scenario=sc,
                n_steps=args.n_steps,
                particles=args.particles,
                batches=args.batches,
                inactive=args.inactive,
                output_dir=args.output_dir,
                nuclear_data_path=args.nuclear_data,
                verbose=True,
            )
            sweep.run()
            sweep.print_summary()
            sweep.save_csv()
            sweep.save_json()
            all_results[sc.name] = sweep

        if len(scenarios) > 1:
            print(f"\n{'=' * 65}")
            print(f"  All scenarios -- eigenvalue change at eta = 1.0")
            print(f"{'-' * 65}")
            print(f"  {'Scenario':<24} {'Dk(pcm)':>9}  {'d_rho(%)':>9}  {'T_avg':>10}")
            for sc_name, sw in all_results.items():
                r = sw.results[-1]
                print(
                    f"  {sc_name:<24} {r.delta_keff_pcm:>+9.1f}  "
                    f"{r.delta_rho_pct:>+9.4f}%  {r.T_avg_C:>10.2f} degC"
                )
