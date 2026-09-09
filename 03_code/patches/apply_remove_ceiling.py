#!/usr/bin/env python3
"""
apply_remove_ceiling.py
=======================
degradation_scenarios.py 에서 서브쿨링 상한(플래토 생성기)을 제거하고,
옛 모델 시절 문서를 개정본에 맞게 고친다. 리뷰어 지적 M10 대응.

배경
----
답변서 M10 은 서브쿨링 임계값을 **철회**했다. 값을 바꾸는 것이 아니라
기준 자체를 없앤다. 근거는 셋이다.

  - 코어 출구 기준 공칭 서브쿨링이 15.70 K 이므로 20 K 기준은 공칭 운전을
    배제하고, 15 K 는 SG 스윕의 76 % 와 바이패스 스윕의 83 % 를 배제한다
  - 전 구간을 통과시키는 값은 11.4 K 아래여야 하는데, 그것은 답에 맞춘
    임의 선택이고 리뷰어가 M2 에서 제기한 지적을 자초한다
  - 핀셀은 코어 평균 벌크 상태 하나만 갖는다. 고온채널을 표현할 수 없으므로
    벌크 서브쿨링 임계값은 모델에 없는 능력을 주장하는 것이다

그런데 코드에는 상한이 살아 있고, 넘으면 이분법으로 상한 직전 상태를 찾아
그것을 반환한다. **리뷰어가 지적한 플래토를 만드는 바로 그 구조다.**
현재 범위에서 발동하지는 않는다(바이패스 η=1 이 1.36 K 차이로 통과).

또한 옛 모델 시절 문서가 여러 곳에 남아 답변서와 정면으로 충돌한다.

적용 내용
---------
  A  SGFoulingModel 클래스 docstring
       "T_sat 329.41", "5°C 이내 SCRAM", "ETA_TRIP ≈ 0.35",
       "유효 분석 범위 η ∈ [0, 0.35]", "보호 계통 작동" 전부 제거
  B  T_SUBCOOL_CEILING_C 상수 제거
  C  SGFoulingModel.compute() 를 임계값 없는 형태로 교체.
       코어 출구가 포화에 닿으면 조용히 고정하지 말고 예외를 던진다
  D  BypassLeakageModel 클래스 docstring
       옛 T_mix 이중계산 식과 x_max = 0.08 제거 (M8 에서 이미 고친 물리)
  E  RiserCorrosionModel 클래스 docstring
       (D0/D_eff)^5 식 제거. 유압은 loop_balance 에 위임되고 조도가 들어갔다
  F  모듈 docstring 의 공칭 운전 조건
       12.76 MPa / 258.3 / 309.7 / 587.3 kg/s 를 개정값으로.
       특히 "노심 출구 309.7" 은 실제로 RCS 고온측이며, 답변서 M10 과
       선제수정 6 이 정정하는 바로 그 오류다

사용법
------
    python3 apply_remove_ceiling.py            # dry run, diff 만 출력
    python3 apply_remove_ceiling.py --apply    # 적용 (타임스탬프 백업)

기대한 텍스트가 정확히 한 번 나오지 않으면 아무것도 쓰지 않고 중단한다.
적용 후 결과가 파싱되는지 ast 로 확인한다.
"""

from __future__ import annotations

import argparse
import ast
import difflib
import shutil
import sys
import time
from pathlib import Path

TARGET = Path("degradation_scenarios.py")

EDITS: list[tuple[str, str, str]] = []

# ---------------------------------------------------------------- A
EDITS.append((
    "A  SGFoulingModel 클래스 docstring — SCRAM / ETA_TRIP 0.35 제거",
    """    물리적 유효 범위 (T_sat 한계)
    --------------------------------
    T_sat @ 12.76 MPa = 329.41°C.
    T_outlet 이 T_sat 에 5°C 이내로 근접하면 원자로 보호 계통이 SCRAM.
    모델은 이 한계(ETA_TRIP ≈ 0.35) 도달 시 열수력 상태를 고정(freeze)한다.
    ETA_TRIP 이후의 η 구간은 "보호 계통 작동 이후 / 분석 범위 외"로 처리되며,
    Phase 6 OpenMC 유효 분석 범위: η ∈ [0, 0.35].

    에너지 보존 검증 결과:
      η ≤ 0.35 : Q 오차 < 5% (유효)
      η > 0.35 : 보호 계통 작동 → 고정 상태 반환
    """,
    """    Single-phase validity (reviewer point M10)
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
    """,
))

# ---------------------------------------------------------------- B
EDITS.append((
    "B  T_SUBCOOL_CEILING_C 상수 제거",
    """    T_SAT_C: float               = 329.38   # saturation temperature at 12.755 MPa
    T_SUBCOOL_CEILING_C: float      = 10.0   # single-phase validity guard; nominal core-outlet subcooling is 15.70 K
""",
    """    T_SAT_C: float               = 329.38   # saturation temperature at 12.755 MPa, IF97
""",
))

# ---------------------------------------------------------------- C
EDITS.append((
    "C  compute() — 임계값과 이분법 고정 제거",
    """    def compute(self, level: float) -> dict:
        \"\"\"
        Apply the single-phase validity guard.

        This is a guard on the applicability of the single-phase property
        routine, not a simulation of a reactor protection action. With the
        fouling resistance anchored to measured deposit data it is never
        reached: the minimum core-outlet subcooling over the swept range is
        about 11 K, against the guard value of 10 K and a nominal 15.7 K.
        \"\"\"
        _validate_level(level)
        raw = self._compute_raw(level)
        ceiling = self.T_SAT_C - self.T_SUBCOOL_CEILING_C
        if raw['T_outlet_C'] <= ceiling:
            return raw
        lo, hi = 0.0, level
        for _ in range(30):
            mid = 0.5 * (lo + hi)
            if self._compute_raw(mid)['T_outlet_C'] > ceiling:
                hi = mid
            else:
                lo = mid
        return self._compute_raw(lo)
""",
    """    def compute(self, level: float) -> dict:
        \"\"\"
        Steam generator fouling. No subcooling threshold is applied (M10).

        The only condition asserted is that the bulk core outlet stays below
        saturation, because the single-phase IF97 formulation is not defined
        above it. That condition is never approached over the swept range: the
        margin is 15.70 K at eta = 0 and 12.41 K at eta = 1.

        A state that did reach saturation would be raised, not silently
        replaced by a frozen one. Freezing is what produced the plateau the
        reviewer objected to, and it hid the fact that the input pair had left
        the single-phase region.
        \"\"\"
        _validate_level(level)
        raw = self._compute_raw(level)
        if raw['T_outlet_C'] >= self.T_SAT_C:
            raise ValueError(
                f"core outlet {raw['T_outlet_C']:.2f} degC reaches saturation "
                f"({self.T_SAT_C:.2f} degC) at eta = {level:.3f}; the "
                f"single-phase property routine does not apply to this state"
            )
        return raw
""",
))

# ---------------------------------------------------------------- D
EDITS.append((
    "D  BypassLeakageModel docstring — 옛 T_mix 이중계산 식 제거",
    """    Core barrel/shroud 간극을 통한 고온 냉각재 바이패스.

    x_bp(η) = x_max × η
    T_mix = T_inlet_nom + x_bp × (T_outlet_nom - T_inlet_nom)
    ṁ_eff = ṁ₀ × (1 - x_bp)
    T_out = T_mix + Q / (ṁ_eff × cp)

    x_max = 0.08 (8%): integral PWR 간극 설계 기준 5~10%
    """,
    """    Core barrel/shroud 간극을 통한 냉각재 바이패스.

    Bypass diverts COLD downcomer flow around the fuel (reviewer point M8).
    The core inlet temperature is unchanged, the core flow is reduced, and the
    bypassed stream rejoins the core exit flow in the upper plenum. The earlier
    version additionally mixed hot outlet coolant into the inlet, charging the
    bypass fraction twice and overpredicting the core-average temperature rise
    by a factor of about 2.8.

    x_bp(eta) = X_BYPASS + (MAX_BYPASS_FRACTION - X_BYPASS) * eta

    eta = 0 is the FSAR best-estimate bypass of 7.3 % (Table 4.1-1), not zero.
    The FSAR analytical value of 8.5 % (Sections 4.4.1.3, 4.4.3.1.1) falls at
    eta = 0.156. Levels above that are an explicit extrapolation beyond the
    design basis and are labelled as such wherever they are plotted.
    """,
))

# ---------------------------------------------------------------- E
EDITS.append((
    "E  RiserCorrosionModel docstring — (D0/D_eff)^5 식 제거",
    """    Hot Riser Tube 내벽 산화막(Fe₃O₄) 성장.

    NuScale 자연 순환 특성상 Riser 마찰 증가 → 유량 직접 감소.
    ṁ ∝ √(ΔP_buoyancy / total_friction)

    δ(η) = δ_max × √η   (확산 지배 포물선 성장)
    ΔfL(η) = (D₀/D_eff)⁵ - 1
    ṁ(η)/ṁ₀ = 1/√(1 + ΔfL/fL₀)
    """,
    """    Hot Riser Tube 내벽 산화막(Fe3O4) 성장.

    delta(eta) = delta_max * sqrt(eta), an assumed parabolic profile.

    The hydraulic response is delegated to loop_balance.solve_loop(), which
    applies both the flow-area reduction and the added surface roughness and
    lets the buoyancy head respond (reviewer points M7 and M9). The earlier
    version applied a fixed (D0/D_eff)^5 resistance ratio with the buoyancy
    head held constant, which modelled only half of the coupling and left
    roughness out altogether.

    Roughness is the dominant hydraulic effect for a deposit, but the riser is
    hydraulically smooth: at 3 um the relative roughness is 2e-6 and even a
    50 um deposit gives 4e-5, against Re of about 6.6e6. The scenario is
    therefore a measured null rather than an assumed one, and the loop
    temperatures do not move at any level.
    """,
))

# ---------------------------------------------------------------- F
EDITS.append((
    "F  모듈 docstring 공칭 조건 — 309.7 은 노심 출구가 아니라 RCS 고온측",
    """  운전 압력      : 12.76 MPa (1851 psia)  [V] INL Sort_20117
  노심 입구 온도 : 258.3 °C               [V] DCA, Frontiers 2022
  노심 출구 온도 : 309.7 °C               [V] DCA, Frontiers 2022
  1차 냉각재 유량: 587.3 kg/s             [V] DCA 공칭값
""",
    """  운전 압력      : 12.755 MPa (1850 psia) [V] FSAR Table 4.1-1
  노심 입구 온도 : 258.11 °C              [V] FSAR 496.6 degF, 저온측
  RCS 고온측 온도: 310.06 °C              [V] FSAR 590.1 degF, SG 1차측 입구
  노심 출구 온도 : 313.59 °C              [V] 입구 + 99.8 degF 상승
  1차 냉각재 유량: 587.0 kg/s             [V] FSAR, RCS 총유량 (코어 유량 아님)

  주의: 이전 판은 309.7 °C 를 "노심 출구"로 적었으나 그것은 RCS 고온측이다.
        핀셀에 전달되는 상태는 노심 평균 285.85 °C 이며, 세 온도를 구분한다.
""",
))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="실제로 쓴다 (기본은 dry run)")
    ap.add_argument("--file", default=str(TARGET), help="대상 파일")
    args = ap.parse_args()

    path = Path(args.file)
    if not path.is_file():
        sys.exit(f"ABORT: {path} 없음. degradation_scenarios.py 가 있는 곳에서 실행하세요.")

    src = path.read_text(encoding="utf-8")
    original = src

    print()
    print(f"대상: {path}")
    print(f"모드: {'적용' if args.apply else 'DRY RUN (아무것도 바꾸지 않습니다)'}")
    print("=" * 78)

    for label, old, new in EDITS:
        n = src.count(old)
        if n != 1:
            sys.exit(
                f"ABORT: [{label}]\n"
                f"       기대한 텍스트가 {n} 번 나왔습니다 (1 이어야 함).\n"
                f"       파일이 이미 수정됐거나 다른 판본입니다. 아무것도 쓰지 않았습니다."
            )
        src = src.replace(old, new, 1)
        print(f"  OK  {label}")

    try:
        ast.parse(src)
    except SyntaxError as e:
        sys.exit(f"ABORT: 수정 결과가 파싱되지 않습니다: {e}")

    # 제거되어야 할 것이 정말 사라졌는지
    residue = {
        "T_SUBCOOL_CEILING_C": src.count("T_SUBCOOL_CEILING_C"),
        "ETA_TRIP":            src.count("ETA_TRIP"),
        "SCRAM":               src.count("SCRAM"),
        "329.41":              src.count("329.41"),
        # 옛 표기 그 자체만 본다. 아래 F 편집이 넣는 정정 각주에도 309.7 이
        # 나오므로 숫자만으로 세면 자기 자신을 잡는다.
        '노심 출구 온도 : 309.7': src.count("노심 출구 온도 : 309.7"),
        "(D₀/D_eff)⁵":         src.count("(D₀/D_eff)⁵"),
    }
    print()
    print("  잔존 검사 (전부 0 이어야 함)")
    bad = False
    for k, v in residue.items():
        print(f"    {k:<22} {v}")
        if v:
            bad = True
    if bad:
        sys.exit("ABORT: 제거 대상이 남았습니다. 아무것도 쓰지 않았습니다.")

    print()
    print("=" * 78)
    diff = list(difflib.unified_diff(
        original.splitlines(keepends=True), src.splitlines(keepends=True),
        fromfile=str(path), tofile=str(path) + " (수정본)", n=2))
    print(f"  변경 {sum(1 for l in diff if l.startswith('+') and not l.startswith('+++'))} 줄 추가, "
          f"{sum(1 for l in diff if l.startswith('-') and not l.startswith('---'))} 줄 삭제")

    if args.apply:
        backup = path.with_suffix(f".py.bak-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(path, backup)
        path.write_text(src, encoding="utf-8")
        print(f"  적용 완료. 백업 {backup.name}")
        print()
        print("  다음: 스윕을 다시 돌릴 필요는 없습니다. 상한이 발동한 적이 없어")
        print("        수치는 바뀌지 않습니다. import 가 되는지만 확인하세요:")
        print("          python3 -c 'import degradation_scenarios as d; "
              "print(d.SGFoulingModel().compute(1.0))'")
    else:
        print()
        print("  --- diff ---")
        sys.stdout.writelines(diff)
        print()
        print("  계획이 맞으면 --apply 를 붙여 다시 실행하세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
