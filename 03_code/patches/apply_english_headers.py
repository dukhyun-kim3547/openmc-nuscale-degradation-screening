#!/usr/bin/env python3
"""
apply_english_headers.py
========================
세 모듈의 **모듈 docstring만** 영문으로 교체한다. 코드와 본문 주석은 건드리지 않는다.

왜
--
공개 저장소(openmc-nuscale-degradation-screening)는 영문판이고, 실행에 쓰인
작업 사본은 한국어 주석판이다. 개정본을 올리려면 둘 중 하나를 골라야 한다.

  (a) 한국어 사본을 그대로 올린다  -> 실행된 코드 그대로지만 독자가 못 읽는다
  (b) 영문판에 변경을 포팅한다     -> 올린 코드가 결과를 만든 코드와 달라진다.
                                     1 라운드에서 걸린 게 정확히 그 종류다
  (c) 한국어 사본 + 영문 헤더      -> 실행된 코드 그대로, 진입점은 영문

(c) 를 택했다. 로직은 한 줄도 바뀌지 않으므로 스윕 재실행이 필요 없다.
본문 주석은 한국어로 남으며, 그 사실을 각 헤더에 명시한다.

동시에 헤더의 낡은 사실을 정리한다
-----------------------------------
  degradation_scenarios.py  틀린 저널명(Journal of Nuclear Engineering -> Kerntechnik),
                            COMBINED 서술
  parametric_sweep.py       50,000 입자(실제 500,000), --all-scenarios 와 COMBINED 예시
  iapws_coolant.py          공칭 284.0 degC / 12.76 MPa, T_sat 329.41,
                            제거된 c_p 상수 5200 과의 비교,
                            "SG_FOULING eta>=0.6 에서 위험 구간"(상한 철회로 무효),
                            "독창성 포인트" 절

사용법
------
    python3 apply_english_headers.py            # dry run
    python3 apply_english_headers.py --apply

degradation_scenarios.py 는 apply_remove_ceiling.py 를 **먼저** 적용한 상태를
기대한다. 순서가 틀리면 ABORT 한다.
"""

from __future__ import annotations

import argparse
import ast
import shutil
import sys
import time
from pathlib import Path

# --------------------------------------------------------------------------
# 교체할 영문 헤더. 각 파일의 모듈 docstring 전체를 이것으로 바꾼다.
# --------------------------------------------------------------------------

NEW_DOCS: dict[str, str] = {}

NEW_DOCS["degradation_scenarios.py"] = '''
degradation_scenarios.py
========================
Primary-system degradation scenario models for a NuScale US600-like SMR.

Companion code for:
  Kim, D. "Screening-level pin-cell neutronic sensitivity of a NuScale
  US600-like SMR fuel lattice to coolant-density perturbations from
  simplified primary-system degradation models."
  Kerntechnik, manuscript KERN-2026-0074 (under revision).

Three degradation mechanisms inside the reactor pressure vessel, each mapped
to a coolant state that is passed to the pin-cell OpenMC model:

  RISER_CORROSION  oxide growth on the hot riser inner wall
  SG_FOULING       primary-side deposit on the steam generator helical coils
  BYPASS_LEAKAGE   coolant bypassing the fuel through the core barrel gap

Revision summary
----------------
Every scenario is now closed on the loop balance in loop_balance.py, which
solves the steam generator heat transfer relation, the loop energy balance in
enthalpy, and a buoyancy-versus-resistance momentum balance simultaneously for
the mass flow and the loop temperatures. The earlier version held the primary
flow fixed and, for the riser, modelled only half of the coupling.

  M3   steam generator energy balance written out explicitly, closed with
       FSAR Tables 5.4-1, 5.4-2 and 5.1-1. U0 = 3186 W/(m2 K), from the
       tabulated duty, area and nominal log-mean temperature difference
  M7   loop momentum balance added; flow solved with the temperatures
  M8   bypass corrected. Bypass diverts cold downcomer flow; the core inlet
       temperature is unchanged. The earlier version also mixed hot outlet
       coolant into the inlet, charging the bypass fraction twice
  M9   riser roughness added and the hydraulic response delegated to the
       loop balance, so the buoyancy head responds to the resistance change
  M10  the subcooling ceiling has been removed. Nothing freezes the
       thermal-hydraulic state; the margin is reported, not tested

Nominal conditions, NuScale FSAR Tier 2 Rev. 5
----------------------------------------------
Three distinct primary temperatures are kept separate; the earlier version
conflated them.

  system pressure       12.755 MPa (1850 psia)   Table 4.1-1
  core inlet, cold leg  258.11 degC (496.6 degF) Table 5.1-2
  core average          285.85 degC              <- the pin-cell state
  core outlet           313.59 degC              inlet + 99.8 degF rise
  riser, RCS hot leg    310.06 degC (590.1 degF) steam generator primary inlet
  total RCS flow        587.0 kg/s               NOT the core flow
  core bypass fraction  7.3 % best estimate, 8.5 % analytical

  Note: the original manuscript reported 309.7 degC as the core outlet. That
  is the RCS hot-leg temperature. The two are different quantities and are now
  named separately throughout.

Note on language
----------------
This is the working copy that produced the deposited results, so the inline
comments are in Korean. Nothing in the logic differs from what was run.
'''

NEW_DOCS["parametric_sweep.py"] = '''
parametric_sweep.py
===================
OpenMC parametric sweep driver for the pin-cell degradation study.

Companion code for:
  Kim, D. "Screening-level pin-cell neutronic sensitivity of a NuScale
  US600-like SMR fuel lattice to coolant-density perturbations from
  simplified primary-system degradation models."
  Kerntechnik, manuscript KERN-2026-0074 (under revision).

For each degradation level the coolant state is taken from
degradation_scenarios.py, converted to a density by iapws_coolant.py, and used
to build a two-dimensional 17x17 pin cell with reflective lateral boundaries.
The eigenvalue is then computed with OpenMC.

Production settings
-------------------
  particles per batch   500,000
  batches               110 total, 10 inactive
  cross sections        ENDF/B-VIII.0
  moderator temperature set per state point, S(alpha,beta) interpolated
  fuel temperature      900 K, a tabulation point, so no interpolation
  Shannon entropy mesh  4 x 4 x 1 over the cell, reported per batch

Ten inactive batches are justified by the entropy trajectory rather than
assumed: the first batch already lies within 0.0023 of the inactive-batch mean
for a reflective pin cell whose initial source fills the fuel region.

Running
-------
  export OPENMC_CROSS_SECTIONS=/path/to/cross_sections.xml

  # one degradation level, resumable
  python parametric_sweep.py --scenario SG_FOULING --eta-index 7 \\
      --n-steps 21 --particles 500000 --batches 110 --inactive 10 --resume

  # merge the per-index part files afterwards
  python merge_sweep.py results/sg_fouling --n-steps 21

Each worker writes one row to results/<scenario>/parts/<scenario>_eta###.csv,
so an interrupted sweep resumes without recomputing. Parallelise by process,
never by thread: the OpenMC run directory is changed with os.chdir, which is
process-global.

A COMBINED scenario exists in this file. It is a weighted superposition with
no independent physical justification and it is not used in the manuscript;
it is retained only so that the deposited code matches what was run.

Note on language
----------------
This is the working copy that produced the deposited results, so the inline
comments are in Korean. Nothing in the logic differs from what was run.
'''

NEW_DOCS["iapws_coolant.py"] = '''
iapws_coolant.py
================
IAPWS-IF97 coolant properties for the pin-cell degradation study.

Companion code for:
  Kim, D. "Screening-level pin-cell neutronic sensitivity of a NuScale
  US600-like SMR fuel lattice to coolant-density perturbations from
  simplified primary-system degradation models."
  Kerntechnik, manuscript KERN-2026-0074 (under revision).

Takes the (T, p) state computed by degradation_scenarios.py and returns the
coolant density that is written into the OpenMC material definition, together
with the other thermodynamic properties used by the loop balance.

The routine is called with temperature and pressure, which is the forward
Region 1 formulation. No backward equation is used anywhere. Where the energy
balances need a temperature from an enthalpy it is obtained by numerical
inversion of the same forward equation.

Verification
------------
Correctness is pinned by test_if97_regression.py, which checks the three
official Region 1 verification points of IAPWS R7-97 Table 5 at (300 K,
3 MPa), (300 K, 80 MPa) and (500 K, 3 MPa). All eighteen published values are
reproduced to nine significant figures, the largest relative deviation being
2.8e-9. That test also pins the coolant states actually passed to OpenMC and
the saturation temperature used throughout.

Nominal state (core average, 285.83 degC, 12.755 MPa)
------------------------------------------------------
  rho    = 749.5812 kg/m3
  T_sat  = 329.3788 degC at 12.755 MPa

The swept moderator range is 285.8 to 289.8 degC, entirely within IF97
Region 1, whose upper limit is 350 degC, and subcooled throughout. A constant
specific heat is no longer used anywhere: the energy balances take enthalpy
differences directly, since the IF97 value runs from about 4840 to 6000
J/(kg K) across the core temperature rise.

References
----------
  [1] IAPWS R7-97(2012), www.iapws.org
  [2] iapws Python package v1.5.5
  [3] degradation_scenarios.py, loop_balance.py (this package)

Note on language
----------------
This is the working copy that produced the deposited results, so the inline
comments are in Korean. Nothing in the logic differs from what was run.
'''

# 각 파일에서 반드시 사라져야 하는 낡은 표현
RESIDUE: dict[str, tuple[str, ...]] = {
    "degradation_scenarios.py": ("Journal of Nuclear Engineering",),
    "parametric_sweep.py":      ("50,000 입자", "--all-scenarios"),
    "iapws_coolant.py":         ("329.41", "5200 J/kg", "독창성 포인트", "위험 구간"),
}

# degradation_scenarios.py 는 apply_remove_ceiling.py 가 먼저 적용돼 있어야 한다
PREREQ = {
    "degradation_scenarios.py": (
        ("T_SUBCOOL_CEILING_C", False, "apply_remove_ceiling.py 를 먼저 적용하세요"),
        ("RCS 고온측 온도", True, "apply_remove_ceiling.py 의 편집 F 가 안 보입니다"),
    ),
}


def replace_module_docstring(src: str, new_doc: str) -> str:
    """모듈 docstring 노드의 실제 위치를 AST 로 찾아 교체한다."""
    tree = ast.parse(src)
    if not (tree.body and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)
            and isinstance(tree.body[0].value.value, str)):
        raise ValueError("모듈 docstring 이 없습니다")
    node = tree.body[0]
    lines = src.splitlines(keepends=True)
    start = sum(len(l) for l in lines[: node.lineno - 1])
    end = sum(len(l) for l in lines[: node.end_lineno])
    return src[:start] + '"""' + new_doc + '"""\n' + src[end:]


def process(path: Path, apply: bool) -> bool:
    name = path.name
    if name not in NEW_DOCS:
        print(f"  건너뜀  {name} (대상 아님)")
        return False
    if not path.is_file():
        print(f"  없음    {name}")
        return False

    src = path.read_text(encoding="utf-8")
    old_doc = ast.get_docstring(ast.parse(src), clean=False)

    # 멱등성 검사를 선행조건보다 먼저 한다. 헤더를 바꾸고 나면 선행조건이
    # 찾는 한국어 문구가 사라지므로, 순서가 반대면 재실행 때 엉뚱한 ABORT 가 난다.
    if old_doc and "Note on language" in old_doc:
        print(f"  이미 처리됨  {name}")
        return False

    for token, want, msg in PREREQ.get(name, ()):
        if (token in src) != want:
            sys.exit(f"ABORT: {name} — {msg}")

    new_src = replace_module_docstring(src, NEW_DOCS[name])

    try:
        ast.parse(new_src)
    except SyntaxError as e:
        sys.exit(f"ABORT: {name} 수정 결과가 파싱되지 않습니다: {e}")

    new_doc = ast.get_docstring(ast.parse(new_src), clean=False)
    bad = [t for t in RESIDUE.get(name, ()) if t in new_doc]
    if bad:
        sys.exit(f"ABORT: {name} 헤더에 낡은 표현이 남았습니다: {bad}")

    # docstring 밖은 한 글자도 바뀌지 않아야 한다
    def body_after_doc(s: str) -> str:
        t = ast.parse(s)
        ls = s.splitlines(keepends=True)
        return s[sum(len(l) for l in ls[: t.body[0].end_lineno]):]
    if body_after_doc(src) != body_after_doc(new_src):
        sys.exit(f"ABORT: {name} docstring 이외가 변경됐습니다")

    print(f"  OK      {name}   docstring {len(old_doc)} -> {len(new_doc)} chars, "
          f"본문 {len(body_after_doc(src))} chars 불변")

    if apply:
        backup = path.with_suffix(f".py.bak-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(path, backup)
        path.write_text(new_src, encoding="utf-8")
        print(f"          적용, 백업 {backup.name}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dir", default=".", help="세 모듈이 있는 폴더")
    args = ap.parse_args()

    d = Path(args.dir)
    print()
    print(f"모드: {'적용' if args.apply else 'DRY RUN (아무것도 바꾸지 않습니다)'}")
    print("=" * 78)
    n = sum(process(d / name, args.apply) for name in NEW_DOCS)
    print("=" * 78)
    print(f"{n} 개 파일 대상")
    if not args.apply and n:
        print()
        print("계획이 맞으면 --apply 를 붙여 다시 실행하세요.")
        print("로직은 한 줄도 바뀌지 않으므로 스윕 재실행은 필요 없습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
