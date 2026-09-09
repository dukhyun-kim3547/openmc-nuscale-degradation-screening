#!/usr/bin/env python3
"""
fix_subcooling.py
=================
스윕 CSV 의 서브쿨링 열을 IF97 기준으로 재계산하고, 기준 위치를 명시적으로 만든다.

왜 필요한가
-----------
배포된 스윕 CSV 의 `subcooling_C` 열은 두 가지 문제가 있다.

  1. 패치 전 상수 T_SAT_C = 329.41 degC 로 계산돼 있다. IF97 값은 12.755 MPa 에서
     329.3788 degC 이므로 0.031 K 과대다. (21 점 전부에서 T_avg + subcooling 을
     역산하면 329.4095–329.4105 가 나온다.)
  2. 어느 온도를 기준으로 한 값인지 열 이름이 말해 주지 않는다. 실제로는 코어
     **평균** 기준인데, 비등이 먼저 시작되는 제한 위치는 코어 **출구**다.
     이 모호함 때문에 두 값(43.55 K 와 15.70 K)이 혼동될 수 있다.

무엇을 하는가
-------------
행마다 그 행의 P_MPa 로 IF97 포화온도를 구해서

  T_sat_C                 신설. 기준을 자기설명적으로 만든다
  subcooling_C            재계산. 의미는 그대로 (T_sat - T_avg_C), 기존 열 이름 유지
  subcooling_core_exit_C  신설. T_sat - T_outlet_C. 제한 위치

스키마를 깨지 않도록 기존 열은 이름도 의미도 그대로 두고 값만 고친다.
신설 열은 뒤에 붙인다.

`is_safe` 열은 건드리지 않는다. M10 에서 서브쿨링 임계값을 철회했으므로 그 열의
정의는 코드 쪽에서 "단상 + IF97 Region 1" 로 다시 세워야 하며, 그것은 이 후처리
스크립트가 할 일이 아니다. 대신 각 행이 실제로 단상·Region 1 인지 검사해서
보고한다.

사용법
------
    python3 fix_subcooling.py results_rev/sg_fouling                  # dry run
    python3 fix_subcooling.py results_rev/sg_fouling --apply
    python3 fix_subcooling.py a.csv b.csv --apply
    python3 fix_subcooling.py results_rev results_boron -r --apply    # 재귀

디렉토리를 주면 그 안의 *.csv 를 처리한다. -r 을 주면 하위까지 훑는다.
--apply 시 원본은 <name>.csv.bak-<timestamp> 로 백업한다.
필요한 열(P_MPa, T_avg_C, T_outlet_C)이 없는 파일은 건너뛴다.
이미 처리된 파일(T_sat_C 열이 있고 값이 IF97 과 일치)은 건너뛴다.
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
import time
from pathlib import Path

try:
    from iapws import IAPWS97
except ImportError:                                      # pragma: no cover
    sys.exit("iapws 가 필요합니다:  pip install iapws")

K = 273.15

REQUIRED = ("P_MPa", "T_avg_C", "T_outlet_C")
NEW_COLS = ("T_sat_C", "subcooling_core_exit_C")

# 재계산 전후 차이가 이 값을 넘으면 경고한다. 예상되는 차이는 0.031 K 뿐이다.
EXPECTED_SHIFT_K = 0.05

_tsat_cache: dict[float, float] = {}


def t_sat_c(p_mpa: float) -> float:
    """IF97 포화온도 [degC]. 같은 압력이 반복되므로 캐시한다."""
    if p_mpa not in _tsat_cache:
        _tsat_cache[p_mpa] = IAPWS97(P=p_mpa, x=0).T - K
    return _tsat_cache[p_mpa]


def collect(targets: list[str], recursive: bool) -> list[Path]:
    out: list[Path] = []
    for t in targets:
        p = Path(t)
        if p.is_dir():
            out.extend(sorted(p.rglob("*.csv") if recursive else p.glob("*.csv")))
        elif p.is_file():
            out.append(p)
        else:
            print(f"  경로 없음: {t}", file=sys.stderr)
    # 백업 파일은 제외
    return [p for p in out if ".bak-" not in p.name]


def process(path: Path, apply: bool) -> str:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return "빈 파일"
        fields = list(reader.fieldnames)
        rows = list(reader)

    missing = [c for c in REQUIRED if c not in fields]
    if missing:
        return f"건너뜀 (열 없음: {', '.join(missing)})"
    if not rows:
        return "건너뜀 (데이터 행 없음)"

    already = "T_sat_C" in fields and all(
        abs(float(r["T_sat_C"]) - t_sat_c(float(r["P_MPa"]))) < 1e-3
        for r in rows if r.get("T_sat_C")
    )
    if already:
        return "이미 처리됨"

    had_sub = "subcooling_C" in fields
    max_shift = 0.0
    implied_old: list[float] = []
    not_liquid: list[str] = []
    not_region1: list[str] = []

    for r in rows:
        p = float(r["P_MPa"])
        ts = t_sat_c(p)
        t_avg = float(r["T_avg_C"])
        t_out = float(r["T_outlet_C"])

        if had_sub and r.get("subcooling_C"):
            old = float(r["subcooling_C"])
            implied_old.append(t_avg + old)          # 옛 계산이 쓴 T_sat
            max_shift = max(max_shift, abs((ts - t_avg) - old))

        r["T_sat_C"] = f"{ts:.4f}"
        r["subcooling_C"] = f"{ts - t_avg:.4f}"
        r["subcooling_core_exit_C"] = f"{ts - t_out:.4f}"

        # 임계값 판정이 아니라 사실 확인만 한다
        lbl = r.get("degradation_level", "?")
        if t_out >= ts:
            not_liquid.append(lbl)
        elif IAPWS97(T=t_avg + K, P=p).region != 1:
            not_region1.append(lbl)

    new_fields = list(fields)
    if not had_sub:
        new_fields.append("subcooling_C")
    for c in NEW_COLS:
        if c not in new_fields:
            new_fields.append(c)

    note = []
    if implied_old:
        lo, hi = min(implied_old), max(implied_old)
        note.append(f"옛 T_sat {lo:.4f}~{hi:.4f} -> IF97 {t_sat_c(float(rows[0]['P_MPa'])):.4f}")
        note.append(f"최대 변화 {max_shift:.4f} K")
        if max_shift > EXPECTED_SHIFT_K:
            note.append(f"** 예상({EXPECTED_SHIFT_K} K)보다 큼, 확인 필요 **")
    if not_liquid:
        note.append(f"** 코어 출구가 포화 이상인 행: {not_liquid} **")
    if not_region1:
        note.append(f"** Region 1 이 아닌 행: {not_region1} **")
    sub_exit = [float(r["subcooling_core_exit_C"]) for r in rows]
    note.append(f"코어 출구 서브쿨링 {min(sub_exit):.2f}~{max(sub_exit):.2f} K")

    if apply:
        backup = path.with_suffix(path.suffix + f".bak-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(path, backup)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=new_fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        tmp.replace(path)
        note.append(f"백업 {backup.name}")

    return "  |  ".join(note)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="+", help="CSV 파일 또는 디렉토리")
    ap.add_argument("--apply", action="store_true", help="실제로 쓴다 (기본은 dry run)")
    ap.add_argument("-r", "--recursive", action="store_true", help="하위 디렉토리까지")
    args = ap.parse_args()

    files = collect(args.targets, args.recursive)
    if not files:
        print("처리할 CSV 가 없습니다.")
        return 1

    print()
    print(f"모드: {'적용 (파일을 덮어씁니다)' if args.apply else 'DRY RUN (아무것도 바꾸지 않습니다)'}")
    print(f"대상: {len(files)} 개")
    print("=" * 78)
    changed = 0
    for p in files:
        result = process(p, args.apply)
        print(f"{p}")
        print(f"    {result}")
        if "건너뜀" not in result and "이미 처리됨" not in result:
            changed += 1
    print("=" * 78)
    print(f"{changed} 개 파일이 대상")
    if not args.apply:
        print()
        print("계획이 맞으면 --apply 를 붙여 다시 실행하세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
