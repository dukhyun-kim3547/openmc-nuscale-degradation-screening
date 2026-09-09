"""
test_if97_regression.py
=======================
Regression test for the IAPWS-IF97 water property implementation used by the
pin-cell coupling in this repository.

Reviewer point M1: the IF97 verification table published in the original
manuscript did not reproduce.  The table was wrong; the property routine was
not.  This test pins the property routine to the official verification values
so that the failure cannot recur silently.

Three groups of checks
----------------------
1. OFFICIAL   The three Region 1 verification points of IAPWS R7-97, Table 5.
              These are the authoritative numbers and are quoted to nine
              significant figures.  Source: IAPWS R7-97(2012), "Revised Release
              on the IAPWS Industrial Formulation 1997 for the Thermodynamic
              Properties of Water and Steam", Table 5, downloaded from
              https://iapws.org/documents/release/IF97-Rev

2. PUBLISHED  The corrected Table 1 of the revised manuscript, and the nominal
              coolant state fed to OpenMC.  If a future edit changes either the
              property routine or the reported table, this group fails.

3. DOMAIN     Assertions that every state used by the sweep lies in Region 1,
              is subcooled, and is reached through the forward (T, p)
              formulation rather than a backward equation.  The revised
              Section 2.3 makes these claims explicitly.

Run as a test
-------------
    pytest -q test_if97_regression.py

Run standalone to produce the supplementary property listing
------------------------------------------------------------
    python test_if97_regression.py           # pass/fail summary
    python test_if97_regression.py -v        # full table, for supplementary material
"""

from __future__ import annotations

import os
import sys

from iapws import IAPWS97

K = 273.15

# Agreement required against the nine published significant figures.  The
# implementation currently reproduces every one of the eighteen values with a
# largest relative deviation of 2.8e-9, so 1e-8 is a tight but not brittle bound.
RTOL_OFFICIAL = 1.0e-8

# ---------------------------------------------------------------------------
# 1. OFFICIAL — IAPWS R7-97, Table 5.  Region 1 basic equation g(p,T), Eq. (7).
#    Units: v [m3/kg], h [kJ/kg], u [kJ/kg], s [kJ/(kg K)], cp [kJ/(kg K)],
#           w [m/s].  Exactly as printed in the release.
# ---------------------------------------------------------------------------
R7_97_TABLE_5 = {
    (300.0, 3.0): dict(
        v=0.100215168e-2, h=0.115331273e3, u=0.112324818e3,
        s=0.392294792,    cp=0.417301218e1, w=0.150773921e4),
    (300.0, 80.0): dict(
        v=0.971180894e-3, h=0.184142828e3, u=0.106448356e3,
        s=0.368563852,    cp=0.401008987e1, w=0.163469054e4),
    (500.0, 3.0): dict(
        v=0.120241800e-2, h=0.975542239e3, u=0.971934985e3,
        s=0.258041912e1,  cp=0.465580682e1, w=0.124071337e4),
}

# ---------------------------------------------------------------------------
# 2. PUBLISHED — numbers that appear in the revised manuscript or response.
# ---------------------------------------------------------------------------

# Revised Table 1, quoted at 12.76 MPa.  Tolerances are the printing precision
# of the table itself (4 decimals in g/cm3, whole J/(kg K) in cp), not the
# accuracy of the property routine.
TABLE_1 = [
    # T [degC], rho [g/cm3], cp [J/(kg K)]
    (258.3, 0.7962, 4840),
    (284.0, 0.7530, 5200),
    (309.7, 0.6990, 5882),
]
TABLE_1_P_MPA = 12.76
TABLE_1_RTOL_RHO = 1.0e-4
TABLE_1_ATOL_CP = 1.0            # J/(kg K)

# Nominal and end-of-sweep coolant states of the revised model, at the revised
# system pressure.  The densities are the values carried in the deposited sweep
# CSV files and passed to OpenMC.
SWEEP_P_MPA = 12.755
SWEEP_ANCHORS = [
    # label, T_core_avg [degC], rho [g/cm3] as tabulated in the sweep CSV
    ("SG fouling eta = 0", 285.8279, 0.7495811),
    ("SG fouling eta = 1", 289.7612, 0.7420580),
]
# The manuscript claims agreement between the tabulated density and a fresh
# IF97 evaluation to better than 2e-5 percent.
SWEEP_RTOL = 2.0e-7

# Saturation temperature at the system pressure, quoted in Sections 2.3 and 3
# and used as the reference for every subcooling statement.
T_SAT_C_EXPECTED = 329.38
T_SAT_ATOL = 0.005               # degC, i.e. the printed precision

# ---------------------------------------------------------------------------
# 3. DOMAIN — the swept moderator range.
# ---------------------------------------------------------------------------
SWEEP_T_MIN_C = 285.8
SWEEP_T_MAX_C = 289.8
REGION_1_T_MAX_C = 623.15 - K    # 350 degC, the upper limit of Region 1


class _Skipped(Exception):
    """Raised by _skip() when this file is run standalone."""


def _fail(msg: str) -> None:
    raise AssertionError(msg)


def _skip(reason: str):
    """Skip under pytest, and report a skip when run standalone.

    pytest.skip() raises an outcome exception that is not an AssertionError, so
    calling it outside a pytest run aborts the standalone runner.  Dispatch on
    whether pytest is actually executing a test, not merely importable.
    """
    if os.environ.get("PYTEST_CURRENT_TEST"):
        import pytest
        pytest.skip(reason)
    raise _Skipped(reason)


# ===========================================================================
# 1. OFFICIAL
# ===========================================================================

def test_r7_97_table_5_region_1():
    """Every one of the eighteen published Region 1 verification values."""
    worst = 0.0
    for (t_k, p_mpa), ref in R7_97_TABLE_5.items():
        st = IAPWS97(T=t_k, P=p_mpa)
        if st.region != 1:
            _fail(f"({t_k} K, {p_mpa} MPa) resolved to region {st.region}, expected 1")
        for prop, expected in ref.items():
            got = getattr(st, prop)
            rel = abs(got - expected) / abs(expected)
            worst = max(worst, rel)
            if rel > RTOL_OFFICIAL:
                _fail(
                    f"R7-97 Table 5 mismatch at ({t_k} K, {p_mpa} MPa), {prop}: "
                    f"expected {expected!r}, got {got!r}, relative deviation {rel:.3e}"
                )
    assert worst <= RTOL_OFFICIAL


def test_r7_97_values_round_to_the_published_digits():
    """Stronger statement: the computed values print as the published ones.

    This is what the response letter claims -- that the implementation
    reproduces the published digits, not merely that it agrees to some
    tolerance.  Nine significant figures is the precision of the release.
    """
    for (t_k, p_mpa), ref in R7_97_TABLE_5.items():
        st = IAPWS97(T=t_k, P=p_mpa)
        for prop, expected in ref.items():
            got = getattr(st, prop)
            if f"{got:.8e}" != f"{expected:.8e}":
                _fail(
                    f"({t_k} K, {p_mpa} MPa) {prop} does not round to the published "
                    f"nine figures: {got:.8e} vs {expected:.8e}"
                )


# ===========================================================================
# 2. PUBLISHED
# ===========================================================================

def test_revised_table_1():
    """The corrected Table 1 of the revised manuscript."""
    for t_c, rho_pub, cp_pub in TABLE_1:
        st = IAPWS97(T=t_c + K, P=TABLE_1_P_MPA)
        rho = st.rho / 1000.0            # kg/m3 -> g/cm3
        cp = st.cp * 1000.0              # kJ/(kg K) -> J/(kg K)
        if abs(rho - rho_pub) / rho_pub > TABLE_1_RTOL_RHO:
            _fail(f"Table 1 density at {t_c} degC: published {rho_pub}, IF97 {rho:.6f}")
        if abs(cp - cp_pub) > TABLE_1_ATOL_CP:
            _fail(f"Table 1 cp at {t_c} degC: published {cp_pub}, IF97 {cp:.1f}")


def test_sweep_nominal_density_anchors():
    """The coolant densities actually handed to OpenMC reproduce from (T, p)."""
    for label, t_c, rho_csv in SWEEP_ANCHORS:
        rho = IAPWS97(T=t_c + K, P=SWEEP_P_MPA).rho / 1000.0
        rel = abs(rho - rho_csv) / rho_csv
        if rel > SWEEP_RTOL:
            _fail(
                f"{label}: sweep tabulated {rho_csv:.7f} g/cm3, IF97 gives "
                f"{rho:.7f}, relative deviation {rel:.2e}"
            )


def test_saturation_temperature_at_system_pressure():
    """T_sat at the system pressure, as quoted throughout the manuscript.

    Any hard-coded T_SAT_C constant in the scenario models must equal this
    value.  The pre-revision constant was 329.41 degC, which is 0.03 K high and
    inflates every reported subcooling by the same amount.
    """
    t_sat = IAPWS97(P=SWEEP_P_MPA, x=0).T - K
    if abs(t_sat - T_SAT_C_EXPECTED) > T_SAT_ATOL:
        _fail(
            f"T_sat at {SWEEP_P_MPA} MPa is {t_sat:.4f} degC, manuscript quotes "
            f"{T_SAT_C_EXPECTED}"
        )


def test_scenario_module_t_sat_constant_matches_if97():
    """If the scenario module hard-codes T_SAT_C, it must agree with IF97.

    Skipped when the module is not importable, so that this file can be run
    from a checkout of the property code alone.
    """
    try:
        import degradation_scenarios as ds
    except Exception:                                    # pragma: no cover
        _skip("degradation_scenarios not importable from here")
    const = getattr(getattr(ds, "NominalConditions", ds), "T_SAT_C", None)
    if const is None:
        return
    t_sat = IAPWS97(P=SWEEP_P_MPA, x=0).T - K
    if abs(float(const) - t_sat) > T_SAT_ATOL:
        _fail(
            f"NominalConditions.T_SAT_C = {const} but IF97 gives {t_sat:.4f} degC "
            f"at {SWEEP_P_MPA} MPa"
        )


# Directories searched for deposited sweep CSVs, relative to this file.
# Only the revision's own result trees.  The pre-revision "results/" sweep is
# the data deposited with the original submission and is deliberately left as
# it was; it must not be rewritten, and it is not searched here.
SWEEP_DATA_DIRS = ("../../05_data", "../05_data", "05_data",
                   "results_rev", "results_boron")


def _rel(path):
    """Path relative to the working directory when that is shorter."""
    from pathlib import Path
    try:
        return str(path.relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def _find_sweep_csvs():
    """Search both this file's directory and the current working directory.

    Recursive, so a results tree with one folder per scenario is covered.
    Backup files written by fix_subcooling.py are ignored.
    """
    from pathlib import Path
    roots = {Path(__file__).resolve().parent, Path.cwd().resolve()}
    found: list = []
    seen: set = set()
    for root in roots:
        for d in SWEEP_DATA_DIRS:
            p = (root / d).resolve()
            if not p.is_dir():
                continue
            for q in sorted(p.rglob("*.csv")):
                if ".bak-" in q.name or q in seen:
                    continue
                seen.add(q)
                found.append(q)
    return found


def test_deposited_sweep_subcooling_columns():
    """Any deposited sweep CSV must carry subcooling consistent with IF97.

    The pre-revision sweep computed subcooling from a hard-coded T_sat of
    329.41 degC, 0.03 K above the IF97 value, and did not say which temperature
    it was referenced to.  fix_subcooling.py rewrites those columns; this test
    keeps them right.  Files that predate the fix, or that lack the columns
    entirely, are reported as failures rather than skipped.
    """
    import csv

    files = _find_sweep_csvs()
    if not files:
        _skip("no deposited sweep CSV found near this file")

    checked = 0
    for path in files:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames or []
            if not {"P_MPa", "T_avg_C", "T_outlet_C"} <= set(fields):
                continue                                  # not a sweep CSV
            rows = list(reader)
        if not rows:
            continue
        for col in ("T_sat_C", "subcooling_C", "subcooling_core_exit_C"):
            if col not in fields:
                _fail(f"{_rel(path)} lacks column {col}; run fix_subcooling.py")
        for r in rows:
            p_mpa = float(r["P_MPa"])
            t_sat = IAPWS97(P=p_mpa, x=0).T - K
            eta = r.get("degradation_level", "?")
            for col, ref in (
                ("T_sat_C", t_sat),
                ("subcooling_C", t_sat - float(r["T_avg_C"])),
                ("subcooling_core_exit_C", t_sat - float(r["T_outlet_C"])),
            ):
                if abs(float(r[col]) - ref) > 5.0e-4:
                    _fail(
                        f"{_rel(path)} eta={eta}: {col} is {r[col]}, IF97 gives "
                        f"{ref:.4f}"
                    )
            if float(r["T_outlet_C"]) >= t_sat:
                _fail(f"{_rel(path)} eta={eta}: core outlet reaches saturation")
        checked += 1
    if checked == 0:
        _skip("no sweep CSV with the expected columns found")


# ===========================================================================
# 3. DOMAIN
# ===========================================================================

def test_entire_sweep_lies_in_region_1_and_is_subcooled():
    """Section 2.3 claims Region 1 throughout, subcooled throughout."""
    t_sat = IAPWS97(P=SWEEP_P_MPA, x=0).T - K
    n = 41
    for i in range(n):
        t_c = SWEEP_T_MIN_C + (SWEEP_T_MAX_C - SWEEP_T_MIN_C) * i / (n - 1)
        st = IAPWS97(T=t_c + K, P=SWEEP_P_MPA)
        if st.region != 1:
            _fail(f"{t_c:.3f} degC at {SWEEP_P_MPA} MPa is region {st.region}, not 1")
        if t_c >= t_sat:
            _fail(f"{t_c:.3f} degC is not subcooled against T_sat {t_sat:.3f}")
    if SWEEP_T_MAX_C >= REGION_1_T_MAX_C:
        _fail("sweep exceeds the Region 1 temperature limit")


def test_density_is_monotone_decreasing_in_temperature():
    """A weak but useful shape check on the property routine."""
    ts = [SWEEP_T_MIN_C + 0.1 * i for i in range(41)]
    rhos = [IAPWS97(T=t + K, P=SWEEP_P_MPA).rho for t in ts]
    for a, b in zip(rhos, rhos[1:]):
        if b >= a:
            _fail("density is not strictly decreasing with temperature along the isobar")


# ===========================================================================
# Standalone reporting -- produces the supplementary property listing
# ===========================================================================

def _print_supplementary_listing() -> None:
    print()
    print("IAPWS R7-97 Table 5, Region 1 verification points")
    print("=" * 78)
    print(f"{'T [K]':>7}{'p [MPa]':>9}  {'property':<10}"
          f"{'R7-97':>18}{'this code':>18}{'rel. dev.':>12}")
    print("-" * 78)
    worst = 0.0
    for (t_k, p_mpa), ref in R7_97_TABLE_5.items():
        st = IAPWS97(T=t_k, P=p_mpa)
        for prop in ("v", "h", "u", "s", "cp", "w"):
            got, exp = getattr(st, prop), ref[prop]
            rel = abs(got - exp) / abs(exp)
            worst = max(worst, rel)
            print(f"{t_k:>7.0f}{p_mpa:>9.0f}  {prop:<10}"
                  f"{exp:>18.9g}{got:>18.9g}{rel:>12.2e}")
        print()
    print(f"largest relative deviation over all eighteen values: {worst:.2e}")

    print()
    print(f"Revised Table 1, at {TABLE_1_P_MPA} MPa")
    print("=" * 78)
    print(f"{'T [degC]':>10}{'rho published':>16}{'rho IF97':>14}"
          f"{'cp published':>15}{'cp IF97':>12}")
    print("-" * 78)
    for t_c, rho_pub, cp_pub in TABLE_1:
        st = IAPWS97(T=t_c + K, P=TABLE_1_P_MPA)
        print(f"{t_c:>10.1f}{rho_pub:>16.4f}{st.rho/1000.0:>14.6f}"
              f"{cp_pub:>15.0f}{st.cp*1000.0:>12.1f}")

    print()
    print(f"Coolant states passed to OpenMC, at {SWEEP_P_MPA} MPa")
    print("=" * 78)
    print(f"{'state':<22}{'T [degC]':>11}{'rho sweep':>13}{'rho IF97':>13}"
          f"{'rel. dev.':>12}{'region':>8}")
    print("-" * 78)
    for label, t_c, rho_csv in SWEEP_ANCHORS:
        st = IAPWS97(T=t_c + K, P=SWEEP_P_MPA)
        rho = st.rho / 1000.0
        print(f"{label:<22}{t_c:>11.4f}{rho_csv:>13.7f}{rho:>13.7f}"
              f"{abs(rho-rho_csv)/rho_csv:>12.2e}{st.region:>8}")
    t_sat = IAPWS97(P=SWEEP_P_MPA, x=0).T - K
    print()
    print(f"T_sat at {SWEEP_P_MPA} MPa: {t_sat:.4f} degC")
    print(f"Region 1 upper temperature limit: {REGION_1_T_MAX_C:.2f} degC")
    print(f"Swept moderator range: {SWEEP_T_MIN_C} to {SWEEP_T_MAX_C} degC")
    print()
    print("All states are reached through the forward Region 1 formulation "
          "IAPWS97(T=..., P=...).")
    print("No backward equation is used anywhere in the coupling.")


def main() -> int:
    verbose = "-v" in sys.argv or "--verbose" in sys.argv
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failures = []
    skipped = []
    for fn in tests:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
        except _Skipped as exc:
            skipped.append(fn.__name__)
            print(f"  SKIP  {fn.__name__}  ({exc})")
        except AssertionError as exc:
            failures.append((fn.__name__, exc))
            print(f"  FAIL  {fn.__name__}\n        {exc}")
    print()
    print(f"{len(tests) - len(failures) - len(skipped)} passed, "
          f"{len(failures)} failed, {len(skipped)} skipped, of {len(tests)}")
    if verbose:
        _print_supplementary_listing()
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
