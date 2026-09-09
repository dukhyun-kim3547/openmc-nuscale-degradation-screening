# Response to Reviewer — KERN-2026-0074

**Title:** Screening-level pin-cell neutronic sensitivity of a NuScale US600-like SMR fuel lattice to coolant-density perturbations from simplified primary-system degradation models
**Author:** Dukhyun Kim
**Decision:** Revise with Major Modifications (4 September 2026) — revision due ~3 December 2026

> **[작성 메모]** 대괄호로 표시된 모든 한국어 블록은 제출 전 삭제. `[TO RUN]` 은 재계산이 필요한 항목, `[VERIFY]` 는 확인이 필요한 항목.

---

## Part 0 — Cover letter to the Editor (draft)

Dear Dr. Kruessenberg,

Thank you for the opportunity to revise manuscript KERN-2026-0074, and please pass my thanks to the reviewer, whose report was unusually detailed and materially improved the work.

I have accepted essentially all of the reviewer's points. The principal changes are:

1. **Table 1 was in error and has been corrected.** The three IAPWS-IF97 verification state points reported in the original Table 1 were not the values produced by the coupling code. The code itself is correct: all 63 eigenvalue calculations used densities that reproduce IF97 to within 2×10⁻⁵ %, verifiable from the raw sweep data deposited in the public repository before submission. Table 1, the verification claim in Sections 2.3 and 3.1, and the associated discussion have been rewritten, and an IF97 regression test against the three official Region 1 verification points has been added to the repository.
2. **The comparative ranking has been withdrawn as the headline result.** The paper is now organised around a single lattice coefficient of reactivity with respect to coolant density, dρ/dρ_coolant, evaluated along the plant operating line so that the moderator temperature moves with the density, plus three separate and independently justified mappings from component condition to coolant density.
3. **All three degradation scenarios have been re-anchored to the NuScale Final Safety Analysis Report** rather than to unsupported parametric bounds. The steam generator energy balance is now written out explicitly using FSAR Tables 5.4-1 and 5.4-2; the core bypass fraction now uses the FSAR design value; and the fouling resistance range is now derived from measured plant data.
4. **A borated beginning-of-cycle case has been added**, and the moderator temperature treatment has been stated explicitly.
5. **Reactivity, rather than Δk, is now reported throughout**, with the definition stated once.

All numerical results have changed. A point-by-point response follows.

Sincerely,
Dukhyun Kim

> **[작성 메모]** 커버레터는 이 정도 길이가 적정. 리뷰어 칭찬 한 줄은 실제로 도움이 됨(리뷰가 정말 좋았음). 변경 항목은 5개를 넘기지 말 것.

---

## Part 1 — Major points

### M1. IF97 verification does not reproduce; density sensitivity ~half the correct value

**Disposition: The error is accepted without reservation. The diagnosis that every scenario result must be recomputed does not hold, and the evidence for that is in data deposited before submission.**

**Response.**

The reviewer is correct that Table 1 does not reproduce, and I have independently confirmed every deviation he reports. Table 1 as published is wrong, the claimed agreement with the NIST WebBook is withdrawn, and I am grateful the check was made.

The corrected table, computed at the stated pressure of 12.76 MPa, is:

| T [°C] | rho published | rho IF97 | deviation | c_p published | c_p IF97 | deviation |
|---|---|---|---|---|---|---|
| 258.3 | 0.7724 | **0.7962** | -2.99 % | 4363 | **4840** | -9.85 % |
| 284.0 | 0.7521 | **0.7530** | -0.12 % | 4495 | **5200** | -13.55 % |
| 309.7 | 0.7274 | **0.6990** | +4.07 % | 4712 | **5882** | -19.90 % |

I also confirm the reviewer's supporting observations. At 258.3 degC the saturated-liquid density is 0.7863 g/cm3, and density rises with pressure along an isotherm, so 0.7724 g/cm3 is inaccessible to liquid water at that temperature at any pressure; 0.7274 g/cm3 at 309.7 degC would require approximately 26.5 MPa; and the three published c_p values correspond to water at approximately 182, 213 and 245 degC.

**The property routine that generated the results is nevertheless correct, and this can be checked directly.** The coupling module calls an IAPWS-IF97 implementation with temperature and pressure and passes the returned density to OpenMC. Recomputing every one of the 63 deposited sweep points from the tabulated `T_avg_C` and `P_MPa` columns reproduces the tabulated `rho_g_cm3` to a maximum deviation of **2 x 10^-5 %**. The mean density derivative realised across the sweep is **-1.911 x 10^-3 g/cm3/K**, which is the IF97 value the reviewer quotes and not the -0.88 x 10^-3 g/cm3/K implied by the erroneous table. The nominal coolant densities used in the submitted calculations, 0.7520795 g/cm3 for the fouling and bypass sweeps and 0.7529985 g/cm3 for the riser sweep, are the correct IF97 values at the respective reference temperatures of 284.4955 and 284.0 degC. (That the two differ at all is a separate defect, corrected in the revision; see Part 3.)

These quantities are in the three sweep CSV files in the public repository, whose last commit predates submission. The same check has been repeated on the sixty-three points of the revised sweep, which reproduce IF97 to a maximum deviation of 1.8 × 10⁻⁵ %; the property routine is unchanged and behaves identically before and after the revision. Table 1 was a verification table of the property implementation at three representative core temperatures; the values printed in it were not produced by that implementation, and the error is confined to the table and to the verification text in Sections 2.3 and 3.1.

A second, independent check points the same way. A low-particle scoping calculation performed at the nominal state with 50,000 particles per batch gives k = 1.408517 +/- 0.000437, against 1.408397 +/- 0.000117 from the production calculation at 500,000 particles per batch. Two calculations differing by an order of magnitude in sample size agree within one standard deviation, which they could not do if the coolant state fed to them were misspecified.

**Actions taken.** Table 1 has been replaced with the values above, quoting the actual deviations rather than upper bounds, and restated at the revised nominal conditions. The c_p column has been removed rather than corrected, because the specific heat values were never used by the calculation; the energy balances now use IF97 enthalpy differences directly (see Part 3). Sections 2.3 and 3.1 have been rewritten and the NIST agreement claim deleted.

On the two specific questions asked: all states lie in **IF97 Region 1**, whose upper temperature limit of 623.15 K (350 degC) is well above the swept moderator range of 285.8 to 289.8 degC, and every state is subcooled (T_sat = 329.38 degC at 12.755 MPa). **No backward equations are used.** The routine is called with temperature and pressure, which is the forward Region 1 formulation; where the revised energy balances require a temperature from an enthalpy, it is obtained by numerical inversion of the same forward equation rather than by the IF97 backward equations.

A regression test against the three official Region 1 verification points of IAPWS R7-97 accompanies the revision. The implementation reproduces all published digits at (300 K, 3 MPa), (300 K, 80 MPa) and (500 K, 3 MPa) for specific volume, enthalpy and isobaric heat capacity. The raw property output and the corresponding NIST WebBook queries are provided as supplementary material.

The eigenvalue results have nonetheless changed substantially, for the separate reasons given under M3, M8 and M10.

> **[작성 메모]** 이 답변의 구조가 전체에서 가장 중요함. 순서를 바꾸지 말 것.
>
> 1) 오류를 **무조건 인정**하고 감사 표시. 방어부터 시작하면 나머지가 다 변명으로 읽힘.
> 2) 정정표를 먼저 제시.
> 3) 그다음에야 코드가 정확했다는 증거. 커밋일이 투고일(2026-07-27)보다 앞선다는 사실이 핵심 근거.
> 4) 50k 스코핑과 500k 생산이 1σ 안에서 일치한다는 독립 확인.
> 5) 리뷰어가 물은 두 가지(region, backward equations)에 직접 답변.
>
> "every scenario result has to be recomputed" 를 부정하되, 결과가 바뀌지 **않는다**고는 절대 쓰지 말 것. M3·M8·M10 때문에 실제로 크게 바뀜. 마지막 문장이 그 역할.
>
> `[TO RUN]` IF97 Region 1 회귀 테스트를 실제로 커밋할 것. 커밋 전에는 위 문장을 쓰면 안 됨.
> `[TO RUN]` 원 물성 출력 + NIST WebBook 쿼리 supplementary 정리
> **[검증 완료 — `03_code/checks/verify_m1_m5.py`]**
> - **개정본 63점 재검증 완료.** T_avg_C 와 P_MPa 로 IF97 을 다시 불러 rho_g_cm3 와 대조.
>   최대 편차 **1.83×10⁻⁵ %** (SG 1.73e-5, 바이패스 1.83e-5, 라이저 1.52e-5), 평균 7.1e-6.
>   본문의 '2×10⁻⁵ % 이내' 가 개정본에서도 성립한다. 본문에 한 절 추가함
> - **투고본 공칭 밀도도 재현됨.** 284.4955 °C → 0.7520795, 284.0 °C → 0.7529985,
>   둘 다 **P = 12.76 MPa** 에서 4×10⁻⁶ % 이내. 12.755 로 하면 10⁻³ % 어긋나므로
>   투고본이 12.76 을 썼다는 것도 확인된다
> - 밀도 미분: 개정 SG 스윕에서 **−1.9121×10⁻³ g/cm³/K**. 본문의 −1.911×10⁻³ 는 투고본
>   스윕(온도 구간이 더 넓음) 값이지만 사실상 같다. IF97 국소미분도 285.8 °C 에서
>   −1.880e-3, 289.8 °C 에서 −1.947e-3 으로 그 사이다
> - 50k/500k 대조는 **산술만** 확인: 차이 12.0 pcm, 결합 σ 45.2 pcm → **0.27 σ**.
>   '1 σ 이내' 참. 다만 두 keff 값 자체는 투고본 스윕 산출물이라 재현 불가
>
> **[아직 미확인 — 저장소 커밋일]** M1 논거의 핵심이 "마지막 커밋이 투고일(2026-07-27)보다
> 앞선다" 이다. 클론에서 확인할 것:
> `git log --format='%ci %s'`  → 최신 커밋이 2026-07-27 이전이어야 한다.
> **history 를 절대 건드리지 말 것** (force push · rebase · amend 금지).

---

### M2. The ranking is set by the choice of R_f,max, x_max and δ_max, not by physics

**Disposition: Accepted. The comparative ranking has been withdrawn, and the paper has been rebuilt around the quantity that does not depend on those choices.**

**Response.**

The reviewer is right, and this is the criticism that has most reshaped the paper. I am grateful for it, because checking it led me to the source of each of the three bounds, and none of them survived.

The three quantities that set the ordering had no defensible basis:

| Constant | Original manuscript | Revised, with source | Factor |
|---|---|---|---|
| R_f,max | 3×10⁻⁴ m²·K/W | 1.76×10⁻⁵ (FSAR Table 5.4-2 design allowance) and 8×10⁻⁵ (end-of-life, measured deposits) | ÷17 at the design allowance |
| U₀ | 8000 W/m²·K | 3.19 kW/m²·K (FSAR Tables 5.4-1, 5.4-2, 5.1-1 energy balance) | ÷2.5 |
| Core bypass | 0 to 8 %, parametric, nominal at 0 % | 7.3 % nominal (FSAR Table 4.1-1), 8.5 % analytical (FSAR §4.4.1.3) | redefined, not rescaled |
| δ_max | assumed oxide thickness scale, on a riser diameter of 1.50 m | 3 µm roughness increment from measured deposits, on the FSAR Table 4.4-1 upper-riser diameter of 1.35 m | mechanism changed (M9) |

Since the reported effect of each mechanism is very nearly proportional to its assumed bound, the ranking was a restatement of the three choices. The reviewer's diagnosis is exact, and the revised results confirm it directly: with the bounds re-anchored, every scenario magnitude changed by up to an order of magnitude, while the lattice response per unit coolant density change did not change at all.

**The primary result is now that invariant quantity.** Regressing reactivity against coolant density over the forty-two sweep points in which the coolant density actually changes gives

**dρ/dρ_coolant = 15,010 ± 494 pcm/(g/cm³)** (3.3 %, reactivity units; the same slope expressed in Δk is 29,757 pcm/(g/cm³)),

and the two mechanisms give it separately as 14,663 ± 609 (steam generator fouling) and 15,342 ± 1,121 (core bypass) pcm/(g/cm³), which differ by 679 ± 1,276, or 0.5 standard deviations. The lattice response is therefore a function of the coolant state alone and carries no memory of which component produced the change. That collapse is the physical finding of the paper, and it is now stated as the result rather than left as a feature of a figure. Because the regression absorbs the reference-point error into its intercept, the coefficient is obtained without differencing any single pair of eigenvalues, which also answers the statistical objection raised under M11; the fitted intercept places zero reactivity at 0.74958 g/cm³, the nominal coolant density, to within 5 pcm.

Two qualifications are stated with it. First, the coefficient is not a pure density coefficient: along the sweep the moderator temperature moves with the density as the two are linked by the plant energy balance at 12.755 MPa, so what is measured is the coupled density-and-spectrum response along the plant operating line (M5). The paper now names it as such, and the title has been adjusted for the same reason. Second, the riser sweep is excluded from the fit. Its coolant density is constant to 8×10⁻⁷ g/cm³ over the entire scenario range, so it carries no information about the slope; that it carries none is itself the negative-control result reported under M9.

**The three mechanisms are then presented as three separate mappings**, each from a component condition to a coolant density change, and each justified on its own evidence rather than on a common normalised scale. Each is reported at a plant-relevant condition and, where the range is carried further, the extrapolation is labelled as such:

| Mechanism | Condition | Basis | Δρ [pcm] |
|---|---|---|---|
| SG fouling | design fouling allowance, R_f = 1.76×10⁻⁵ m²·K/W (η = 0.220) | FSAR Table 5.4-2 | −22.8 |
| SG fouling | 60-year end-of-life deposit, R_f = 8×10⁻⁵ m²·K/W (η = 1) | measured deposits, Minor 9 | −120.2 |
| Core bypass | 8.5 % (η = 0.156) | FSAR §4.4.1.3 analytical value | −17.1 |
| Core bypass | 15 %, beyond design basis (η = 1) | extrapolation | −60.7 |
| Riser oxide | 3 mm oxide (η = 1) | assumed profile, M9 | +3.5 |

No entry is read off the fitted line. The three at η = 1 are calculated points; the two design-condition entries, at η = 0.220 and η = 0.156, are linear interpolations between the adjacent calculated points of a sweep whose grid spacing is 0.05, and each Δρ is referred to the η = 0 point of its own sweep (M11). Against the differencing standard deviation of 9.00 pcm in reactivity units (M11), the two density-mediated mechanisms sit at the edge of detectability within the design basis, at 2.5 σ and 1.9 σ, and become unambiguous only outside it; the riser is not detectable at any level. For the riser the coefficient and the measured density change together predict 0.012 pcm, and the observed +3.5 pcm is 0.4 σ of Monte Carlo scatter, so the null is consistent with the coefficient rather than merely assumed.

This reorganisation changes what the paper claims. It is no longer a ranking of ageing mechanisms by neutronic importance; it is a screening result stating that all three bulk-density-mediated mechanisms lie at or below the detection threshold of a pin-cell eigenvalue calculation under design conditions, together with the conditions under which each would become detectable. The phrase "clear ordering of neutronic sensitivity" has been removed from Section 4, from the Conclusion and from the abstract, and the abstract and Conclusion have been rewritten around the coefficient and the detection thresholds.

The reviewer offers two routes; the revision takes the first, with the supporting table above supplying the element of the second that is defensible, namely the mechanism-to-density mappings at justified conditions rather than at arbitrary maxima.

> **[작성 메모]** 구조는 M1과 동일. 인정 → 상수 3개가 근거 없었음을 표로 자백 → 그제서야 불변량(계수) → 매핑 표 → 논문 주장이 어떻게 바뀌는지.
>
> **리뷰어의 "δ_max를 30 mm로 했으면 negative control이 지배적이 되었을 것" 예시는 반박하지 말 것.** 원고 유압 모델로 계산하면 −30 pcm 수준이라 성립하지 않지만, M2의 본질이 옳고 M9에서 조도 지적이 유압 모델 자체를 무효화하므로 다툴 실익이 없음. 위 초안에 반박 없음 — 유지할 것.
>
> **단위 표기 확인 완료 (스크립트 verify_m2.py 출력 기준)**
> - 15,010 = 반응도 pcm/(g/cm³), 29,757 = Δk pcm/(g/cm³). k₀² = 1.982422 로 나눔
> - 9.00 pcm = 차분 √2σ, **반응도 단위**. 17.84 는 Δk 단위이므로 M2 에 쓰지 말 것
> - SG vs 바이패스 차이 679 ± 950 = 0.71σ (직접 계산 확인)
> - η 매핑: SG 1.761e-5/8e-5 = 0.220, 바이패스 (8.5−7.3)/(15−7.3) = 0.156. 둘 다 재현됨
> - 유의성 2.53 / 13.36 / 1.90 / 6.75 / 0.39 σ — 표에는 handoff 반올림값(2.5/13.4/1.9/6.7/0.4) 사용
>
> **[저장소 배포 전 반드시 처리]** `results_boron/sg_fouling/keff_vs_degradation_sg_fouling.csv` 는
> **1행짜리 잔여 파일**이다(η=0.9 만 들어 있음). 같은 폴더의 `merged.csv` 가 11점 전부를 담은
> 올바른 파일이다. 분석은 parts/merged 기준으로 했으므로 M4 수치에는 영향이 없으나,
> 이 파일을 그대로 올리면 붕소 스윕이 1점짜리로 보인다. 삭제하거나 merged 로 다시 생성할 것.
> (results_rev 의 세 시나리오는 keff_vs_… 와 merged 가 같은 범위를 보이므로 정상)
>
> **[미확보 — 채워야 할 것]** 매핑 표에 Δρ_coolant [g/cm³] 열을 넣으면 "조건 → 밀도 → 반응도" 사슬이 완성돼 훨씬 설득력 있음. 다만 SG η=0.220 과 바이패스 η=0.156 의 **실측** 밀도값은 스윕 CSV 에서 뽑아야 함. 계수로 역산하면 순환논증이고 실측·모델을 섞는 것이므로 금지. CSV 의 `rho_g_cm3` 열에서 해당 η 행을 읽어 채울 것. 라이저만 실측 8×10⁻⁷ g/cm³ 확보돼 있어 본문에 이미 반영함.
>
> **[원 기울기와의 비교 — 넣을지 판단 필요]** 같은 Δk 단위로 28,382 → 29,757, 즉 +4.8 %. "상수 세 개가 다 바뀌었는데 격자 응답은 그대로"라는 주장의 보강 근거가 되지만, 두 적합의 밀도 구간과 시나리오 모델이 달라 엄밀히 비교 가능하지 않음. 넣으려면 "두 적합은 밀도 구간이 달라 엄밀한 동일 비교가 아니다"라는 단서를 반드시 붙일 것. 단서 없이 쓰면 2라운드에서 걸림. 현재 초안에는 **넣지 않았음** — 시나리오 내부의 SG vs 바이패스 일치(0.7σ)만으로 불변성 주장이 이미 성립하므로 불필요한 위험임.
>
> `[TO RUN]` 없음. M2 는 새 계산 불필요 — 위 [미확보] CSV 열 추출만 남음.

---

### M3. The steam generator model contains no equation and cannot be reproduced

**Disposition: Accepted. The model has been rewritten.**

**Response.**

The reviewer is correct, and the omission was more serious than the manuscript suggested: the mapping from f_UA to the primary temperature was absent from the code as well as from the paper. The original model asserted a core temperature rise proportional to f_UA without a thermodynamic derivation, and the nominal overall heat transfer coefficient U₀ = 8000 W/m²·K had no source.

The scenario has been rebuilt on an explicit steady-state energy balance closed entirely with NuScale FSAR data:

- Secondary side, FSAR Table 5.4-1 (best estimate, full load): total heat transfer 159.13 MW_t; feedwater inlet 299.7 °F (148.7 °C); steam outlet 584.4 °F (306.9 °C) at 500.1 psia; secondary flow 532,298 lbm/hr.
- Geometry, FSAR Table 5.4-2: total heat transfer area 17,928 ft² (1665.6 m²), including a 10 % tube plugging margin; 1380 helical tubes; tube OD 0.625 in, wall 0.050 in.
- Primary side, FSAR Tables 4.1-1 and 5.1-2: 160 MW_t at 1850 psia; T_cold 496.6 °F, T_hot 590.1 °F, T_avg 543.3 °F, core temperature rise 99.8 °F, best-estimate flow 587.0 kg/s.

The area tabulated in Table 5.4-2 is taken as the module total. Table 5.4-2 labels the tube counts "per NPM" and gives the area without a per-unit qualifier, whereas Table 5.4-5 explicitly labels the corresponding decay heat removal system quantities "per condenser"; the tabulated area is therefore read as covering both steam generators, consistent with the footnote to Table 5.4-1 that the tabulated duty is for both units together. The implied tube length of 24.2 m per tube is consistent with the helical bundle geometry and with the steam generator region volume of 621 ft³ given in Table 5.1-1.

The primary hot-side stream entering the steam generator is the riser flow, at the RCS hot-leg temperature of 590.1 °F (310.06 °C), not the core outlet temperature. A counter-current log-mean temperature difference at the nominal state then gives LMTD = 30.0 K and

**U₀ = Q/(A · LMTD) = 3.19 kW/m²·K**

against the 8000 W/m²·K assumed in the original manuscript, a factor of 2.5. Two caveats are stated in the text. First, the hot-end approach temperature is only 3.2 K, so the single log-mean value is sensitive to the primary hot-leg temperature: a ±1 K shift moves U₀ between 2.97 and 3.49 kW/m²·K. Second, the once-through unit passes through preheat, boiling and superheat zones, so a single LMTD is not strictly valid and is used here only to fix an effective nominal UA. The quantity that governs the result is the product R_f·U₀, and it is now reported explicitly.

Degradation is imposed as f_UA = (1 + R_f U₀)⁻¹ with R_f justified as in Minor point 9, and the degraded primary terminal temperatures are obtained by solving the steam generator relation together with the loop energy and momentum balances at fixed duty and fixed secondary conditions, so that the primary flow responds rather than being held (M7). The resulting UA reduction is 5.3 % at the design fouling allowance and 20.3 % at the end-of-life value. Fluid enthalpy rather than a constant specific heat is now used throughout the energy balance; the original code used a fixed c_p of 5200 J/(kg·K) across a temperature rise over which the IF97 value varies from about 4840 to 6000 J/(kg·K), and that constant has been removed from the code rather than corrected.

This balance is implemented in the deposited code and every figure above is reproduced by it: the model returns a UA reduction of 20.31 % at η = 1, against 20.31 % from (1 + R_f U₀)⁻¹ evaluated by hand at R_f = 8×10⁻⁵ and U₀ = 3186 W/(m²·K).

The same coefficient also explains the plateau reported under M10. The original pairing of R_f,max = 3×10⁻⁴ m²·K/W with the assumed U₀ = 8000 W/(m²·K) implies a 71 % loss of UA; with U₀ at its actual value the same R_f still implies 49 %, which drives the primary above saturation. The plateau was therefore a consequence of this coefficient never having been established, which is why M3 and M10 are answered together.

> **[작성 메모]** 면적 이분법은 숨기지 말고 명시 → 리뷰어가 오히려 신뢰함.
>
> **코드 구현 완료. `[TO RUN]` 없음.** `loop_balance.solve_loop()` 가 SG 관계식·루프
> 에너지·운동량을 동시에 푼다. `degradation_scenarios.SGFoulingModel` 이 이를 호출한다.
>
> **전 수치 FSAR 원자료에서 재계산 확인 (`03_code/checks/verify_m3.py`)**
> - 17928 ft² = 1665.57 m²  (답변서 1665.6)
> - 고온단 접근 310.06 − 306.89 = **3.17 K**, 저온단 258.11 − 148.72 = 109.39 K
> - LMTD = (109.39 − 3.17)/ln(109.39/3.17) = **29.996 K**  (답변서 30.0)
> - U₀ = 159.13e6/(1665.57 × 29.996) = **3185.2 W/m²K**  (답변서 3.19 kW, 코드 상수 3186)
> - T_hot ±1 K → LMTD 32.21 / 27.35 K → U₀ **2.97 / 3.49 kW/m²K**  (답변서와 일치)
> - 관당 길이 1665.57/(1380 × π × 0.625 in) = **24.20 m**  (답변서 24.2)
> - UA 저감 설계 **5.31 %**, EOL **20.31 %**. 코드 `compute(1.0)` 반환 0.2031110544 와 일치
> - 원고 조합 3e-4 × 8000 → 70.6 %,  3e-4 × 3186 → **48.9 %**. M10 의 "49 %" 확인
>
> **[검증 못 한 것]** Table 5.1-1 의 SG 영역 부피 621 ft³, DHRS 관당 2.86 m 는 FSAR
> 원문이 있어야 확인된다. 면적 판별의 **주 근거는 라벨 관행**이고 관당 길이는 보조
> 정합성 검사일 뿐이다. 답변서도 그 순서로 써 있으니 뒤집지 말 것 — 24.2 m 가
> "그럴듯하다"는 것은 증명이 아니다(모듈 하나 기준이면 12.10 m 이고 그것도 불가능하지 않다).
>
> **[면적 판별 근거 — 논문 각주로 넣을 것]** Table 5.4-5(DHRS)는 "Total number of tubes **per condenser** 80", "Tube external surface area **per condenser** 258.2 ft²"로 단위별 라벨을 명시함. Table 5.4-2는 관 수를 "per NPM"으로 라벨하면서 면적 행에만 단서가 없음 → 모듈 전체. Table 5.4-1 각주("두 SG 운전 기준")도 같은 관행. 교차검증: DHRS 관당 2.86 m, SG 관당 24.2 m, 모두 타당.

---

### M4. Soluble boron is a physics omission, not a scope limitation

**Disposition: Accepted. A borated case has been computed and the reported coefficient is now corrected for it.**

**Response.**

I accept both the point and its sign: omitting the soluble boron overpredicts the reported sensitivity rather than conservatively bounding it, and the overprediction is large.

A borated sweep has been run at the NuScale equilibrium-cycle beginning-of-cycle concentration of **1235 ppm natural boron** (FSAR Section 4.3; the cycle ends at approximately 20 ppm). Boron is entered as an atom fraction in the coolant, with the boron-to-water ratio evaluated at run time from the ppm specification rather than tabulated, and the total coolant density held at the IF97 value for pure water, so that boron displaces water. The sweep uses the steam generator fouling scenario at eleven degradation levels, and the thermal-hydraulic solution at each level is identical to the corresponding unborated point to the last tabulated digit — the same core-average temperature, coolant density and primary flow — so that the boron is the only difference between the two series.

*Consistency with the FSAR.* The added boron reduces the lattice eigenvalue from 1.407985 to 1.299927, a change of −10,806 pcm in Δk, giving a boron worth of **−8.75 pcm/ppm on a Δk basis**, within the FSAR range of −7.6 to −13.7 pcm/ppm for this core. The comparison is made in Δk rather than in reactivity because the FSAR figure is quoted for a core at criticality, whereas this infinite lattice sits at k = 1.41; the same eigenvalue change expressed as a reactivity in this lattice is −4.78 pcm/ppm, and comparing that number with the FSAR range would be a unit error rather than a discrepancy. This is stated explicitly in the revised text.

*Effect on the reported coefficient.* Fitting reactivity against coolant density over the eleven matched points in each series gives

| series | dρ/dρ_coolant [pcm/(g/cm³), reactivity] |
|---|---|
| unborated | 14,536 ± 795 |
| borated, 1235 ppm | 6,210 ± 1,222 |
| difference | 8,327 ± 1,457 (5.7 σ) |

so that **the unborated lattice overpredicts the coefficient by a factor of 2.34**, and the borated coefficient retains 43 % of the unborated value. Both uncertainties follow the convention stated under M6: the larger of the least-squares standard error and the propagated single-calculation uncertainty. For the borated series the residual scatter exceeds the sampling noise, so the least-squares figure governs; for the unborated series the two agree to better than 1 %. The ratio is quoted in reactivity because reactivity is the quantity reported throughout the revised manuscript (M6); the corresponding factor in Δk is 2.74, the two differing by exactly the ratio of the squared eigenvalues of the two lattices, and the reactivity figure is the one that applies to the results as reported.

The headline coefficient in the abstract and in Section 3 remains the unborated value of 15,010 ± 494 pcm/(g/cm³), because it is fitted over forty-two points across two scenarios and is therefore the better determined number, and because every reactivity value tabulated in the revised manuscript comes from unborated calculations. The borated result is carried as a correction to it, stated wherever the coefficient is quoted: under design boron conditions the lattice response to a coolant density change is smaller by a factor of 2.34, and the screening margins reported here are correspondingly conservative. The unborated coefficient fitted over the eleven matched points alone, 14,536 ± 795, agrees with the forty-two-point value within 0.5 σ, so the correction factor and the headline coefficient are drawn from mutually consistent fits.

The correction does not change the screening conclusion, and it strengthens it in the direction the reviewer indicates: with boron present, all three mechanisms move further below the detection threshold of a pin-cell eigenvalue calculation under design conditions.

The moderator temperature range across the borated sweep, 558.98 to 562.91 K, is the same as for the unborated sweeps and lies within the same single interval of the thermal scattering tabulation, so the treatment described under M5 applies unchanged.

The gadolinia-bearing pins of the reference core remain outside the scope of a single-pin model. This is now stated as a specific limitation with its expected sign — a burnable absorber further reduces the lattice sensitivity to a coolant density change, in the same direction as the boron correction — rather than as a general caveat.

> **[작성 메모]** 붕소 11점 + 무붕소 11점 실측 기준. 스크립트 `03_code/checks/analyze_boron.py`, `m4_compare.py` 출력으로 확인함.
>
> **표본 정합이 이 답변의 뼈대다.** 무붕소 21점 중 짝이 되는 11행의 `T_avg_C`·`rho_g_cm3`·`mdot_kg_s` 가 붕소 11점과 완전히 같음을 확인했다. 열수력 해가 같으므로 두 계열의 차이가 붕소뿐이라고 쓸 수 있다. 이 문장을 빼지 말 것 — 리뷰어가 "두 계산이 정말 같은 조건이었나"를 물을 수 있는 유일한 지점이다.
>
> **단위 주의 (스크립트 확인 완료)**
> - 배율은 단위에 따라 다르다. 반응도 **2.34**, Δk **2.74**. 비 = k₀붕소²/k₀무붕소² = 1.689810/1.982422 = 0.8524
> - 감소율도 마찬가지. 반응도 **57.3 %**, Δk **63.5 %**
> - σ 도 두 계열이 다르다. 무붕소 12.42 pcm(keff) → 6.26 pcm(반응도), 붕소 13.20 → 7.81. k₀² 가 다르기 때문. **두 계열의 σ 를 섞지 말 것**
> - 붕소 가치는 Δk −8.75 pcm/ppm 으로만 FSAR 와 비교. 반응도 −4.78 은 범위 밖으로 보이지만 단위 문제
>
> **[handoff Part 3.8 정정]** 거기 적힌 "무붕소 15,838 / 붕소 5,779, 감소 63.5 %, 2.7배" 는 **6점 값이고 반응도 단위**다. 11점으로 다시 적합하면 14,536 / 6,210, 감소 57.3 %, 2.34배. 무붕소 6점 잔차가 0.82 pcm(기대 6.22)로 우연히 작았던 것이 원인으로 확인됐다. **6점 값을 쓰지 말 것.**
>
> **[63.5 % 의 우연]** handoff 의 63.5 % 는 반응도·6점, 이번 Δk·11점도 63.5 %. 단위도 표본도 다른데 숫자가 같다. 하나를 다른 하나의 근거로 인용하면 안 된다.
>
> **[Margulis 2024 인용 시 주의]** Madinka Mweetwa·Dahlfors·Margulis (2024) 의 "붕소 제거 시 MTC 약 10배" 와 우리 2.34배를 나란히 놓으면 "왜 10배가 아니냐"는 질문이 나온다. MTC(dρ/dT)와 밀도계수(dρ/dρ_c)는 다른 양이고 노형도 다르다. 인용은 유지하되 두 양이 다르다는 것을 한 문장으로 명시할 것. 정량 일치를 주장하지 말 것.
>
> **[선택 사항]** 붕소 계수 불확도 15.9 % 가 마음에 걸리면 홀수 인덱스 10점을 추가해 11.5 % 로 낮출 수 있다(10런 × 약 30 min ≈ 5 h). 43점까지 가야 8 %. 밀도 구간을 넓히는 것은 불가 — R_f 상한 8×10⁻⁵ 는 실측 근거이므로 늘리면 Minor 9 와 충돌한다. 현재 초안은 붕소를 대표값이 아니라 보정 배율로 쓰므로 15.9 % 로도 논지가 성립한다.
>
> **[확인된 부수 결과]**
> - 감속재 온도 558.98–562.91 K, 550/574 K 구간 안 → M5 문안 무수정 유효
> - 서브쿨링: **코어 평균** 43.55–39.62 K, **코어 출구** 15.70–12.41 K. CSV `subcooling_C` 열은
>   코어 평균 기준이고 옛 T_sat 329.41 로 계산돼 있다. 제한 위치는 코어 출구다.
>   M10 에서 임계값 자체를 철회했으므로 가드 통과 여부는 더 이상 판정 대상이 아니다
> - 2차항 F(1,8) = 0.256, p = 0.63 → 선형 적합으로 충분
> - χ² 검정: 무붕소 11점 9.06(df 9), 무붕소 21점 18.34(df 19), 붕소 11점 13.75(df 9) — 전부 95 % 구간 안
> - 무붕소 21점 재적합 14,663 ± 609 로 handoff 확정값 14,663 과 일치. 파이프라인 정상

---

### M5. State whether the moderator temperature and its S(α,β) data were updated with the density

**Disposition: Accepted; the information was omitted from the paper but the treatment was correct.**

**Response.**

The moderator temperature was updated together with the density at every sweep point. In the OpenMC model the coolant material temperature is set to the core-average coolant temperature for that degradation level, and the settings block specifies that temperature as the default with `method = "interpolation"`. The hydrogen-in-water thermal scattering data are therefore interpolated between the discrete library temperatures rather than held fixed. What is computed is a coupled moderator density and temperature effect that includes the spectrum-shift component, not a pure moderator density coefficient, and Section 2.4 now says so explicitly.

The specific information the reviewer asks for is as follows.

The `c_H_in_H2O` evaluation of ENDF/B-VIII.0 is tabulated at 284, 294, 300, 324, 350, 374, 400, 424, 450, 474, 500, 524, 550, 574, 600, 624, 650 and 800 K. The moderator temperatures reached across all three scenarios and all degradation levels span 558.98 to 562.91 K, so every one of the sixty-three points lies within the single interval bounded by the 550 K and 574 K tabulations, and the thermal scattering kernel is obtained by OpenMC's interpolation between that one pair throughout. The interval is 24 K wide and the swept range occupies less than 4 K of it, so no point approaches a tabulation boundary and the interpolation is uniform in character across the sweep.

The fuel temperature is held at 900 K. That value is one of the tabulated temperatures of the continuous-energy data for every fuel and structural nuclide used here — 250, 294, 600, 900, 1200 and 2500 K, alongside the 0 K base evaluation — so the fuel cross sections are taken directly from the library with no interpolation. The fuel temperature is not varied with the degradation level; this is stated as a limitation, since a coupled treatment would also move the Doppler contribution.

The moderator temperature at each point is tabulated alongside the density in the revised manuscript and is recorded in the `T_moderator_K` column of the deposited sweep data.

> **[검증 완료 — `03_code/checks/verify_m1_m5.py`, 개정본 63점]**
> - 감속재 온도 **558.9771 – 562.9112 K** (본문 558.98 – 562.91) — 일치
> - 550 / 574 K 한 구간 안: **참**. 하한까지 8.98 K, 상한까지 11.09 K 여유
> - 스팬 **3.93 K**, 구간 24 K 의 16.4 % — 본문의 "24 K 중 4 K 미만" 확인
> - 시나리오별: SG 558.978–562.911, 바이패스 558.978–561.149, 라이저 558.977–558.978
> - 붕소 11점도 558.978–562.911 로 동일 구간 (M4 참조)
>
> **[라이브러리 격자점 검증 완료]** VM 의 `endfb-viii.0-hdf5/thermal/c_H_in_H2O.h5` 를
> 직접 열어 확인. HDF5 그룹 이름이 곧 온도점이다:
> `284K 294K 300K 324K 350K 374K 400K 424K 450K 474K 500K 524K 550K 574K 600K 624K 650K 800K`
> — **답변서가 나열한 18개와 완전히 일치.** 스윕 558.977–562.911 K 을 감싸는 인접쌍은
> 550 / 574 K 이고, 이것도 본문 그대로다. (파일은 `neutron/` 이 아니라 `thermal/` 아래에 있다)
>
> **[연료 격자점도 검증 완료]** `neutron/{U235,U238,O16,Zr90}.h5` 의 `energy` 그룹 키가
> 네 핵종 모두 `0K 250K 294K 600K 900K 1200K 2500K` 로 동일하다.
> **900 K 가 격자점이므로 "보간 없음" 주장이 성립한다.**
>
> 다만 답변서가 나열한 6개에는 **0 K 가 빠져 있었다.** 0 K 는 공명 산란·on-the-fly
> 브로드닝용 기저 평가라 통상의 온도점과 성격이 다르지만, 라이브러리를 직접 열어 본
> 리뷰어는 7개를 본다. "alongside the 0 K base evaluation" 을 덧붙여 목록을 완전하게 했다.

> **[작성 메모]** 세 가지가 답변의 뼈대. (1) 갱신했다는 사실, (2) 어느 이산 온도 사이인지 — 550/574 K, (3) 연료 900 K 는 격자점이라 보간 없음.
>
> (3)이 유리한 부분이니 빼지 말 것. 리뷰어가 묻지 않았지만 온도 처리 전반의 신뢰도를 올려줌.
>
> 연료 온도를 열화 수준에 따라 바꾸지 않는다는 한계는 스스로 밝힐 것. 리뷰어가 2라운드에서 물을 여지가 있고, 먼저 밝히는 편이 낫다.
>
> 전 시나리오 63점 확정: SG 558.98–562.91, 바이패스 558.98–561.15, 라이저 558.98 K. 550/574 K 구간 안. 붕소 케이스는 같은 상태점이므로 범위가 바뀌지 않음.

> **[작성 메모]** 이건 순수하게 유리한 항목. 코드에 이미 되어 있었고 논문에만 안 적혀 있었음. 짧고 사실적으로 답하고 넘어갈 것.

---

### M6. Δk and reactivity are used interchangeably

**Disposition: Accepted.**

**Response.**

Reactivity is now used throughout, defined once as Δρ = (k − k₀)/(k·k₀) and reported in pcm. All figure ordinates, table headings, the abstract and the Conclusion have been made consistent, and the terms "eigenvalue perturbation" and "reactivity" are no longer used interchangeably.

The reviewer is right that the two quantities differ by close to a factor of two in this lattice. At the revised nominal eigenvalue of k₀ = 1.40799 the ratio Δk/Δρ is k₀·k = 1.979, so a change quoted in Δk is almost exactly twice the corresponding reactivity change. As an example from the revised results, the steam generator fouling case at the end-of-life fouling resistance gives Δk = −238 pcm and Δρ = −120 pcm.

This change also affects the slope reported in Figure 3, which the reviewer identifies in his closing remarks as the most transferable number in the paper. One point of nomenclature goes with it. The quantity is a coefficient of reactivity with respect to coolant density, and it is named as such, but it is not a coefficient at fixed temperature: along the sweep the moderator temperature moves with the density because the two are linked by the plant energy balance at 12.755 MPa, so what is measured is the coupled response along the plant operating line (M5). That is stated wherever the coefficient is quoted, including the abstract and the figure legend. The original regression slope of 28,382 pcm/(g/cm³) was expressed in Δk. On the revised model the corresponding lattice coefficient, obtained by regressing reactivity against coolant density over the scenarios in which the density actually changes, is

**dρ/dρ_coolant = 15,010 ± 494 pcm/(g/cm³)**

(42 points from the fouling and bypass sweeps; the same slope expressed in Δk is 29,757 pcm/(g/cm³)). The riser sweep is excluded from the fit because its coolant density is constant to within 8 × 10⁻⁷ g/cm³ over the whole scenario range, so it carries no information about the slope; that it carries none is itself the negative-control result reported under M9. The fitted intercept places zero reactivity at 0.74958 g/cm³, the nominal coolant density, to within 5 pcm.

The residual standard deviation of that regression is 5.31 pcm, against 6.39 pcm expected from the single-calculation uncertainty expressed in reactivity units; the fit is as tight as the Monte Carlo sampling allows. Every slope uncertainty quoted in this response is the larger of the ordinary least-squares standard error and the value obtained by propagating that single-calculation uncertainty through the fit. The two coincide when the residual scatter matches the sampling noise; where the residual falls below it, as here, the propagated figure is the honest one, and where it exceeds it the least-squares figure is. Since the individual scenarios give 14,663 ± 599 and 15,342 ± 737 pcm/(g/cm³) separately and agree within their uncertainties, the lattice response is a function of coolant density alone and does not depend on which mechanism produced the density change. This is the quantitative basis for the restructuring described under M2.

> **[검증 완료 — `03_code/checks/verify_m6.py`, 세 시나리오 63점 실측]**
> - 42점 통합 **15,010.3**, OLS SE **410.5**, σ기반 SE **493.9**, 잔차 5.31 / 기대 6.39
> - SG 단독 14,662.7 (OLS 598.7 / σ 609.3),  바이패스 단독 15,341.4 (OLS 737.1 / σ 1,120.8)
> - 절편: 적합선이 공칭 밀도에서 실제 공칭점과 **4.40 pcm** 차 → '5 pcm 이내' 확인
> - Δk 환산 기울기 **29,757** 확인
>
> **[SE 규약 확정]** `max(OLS, σ기반)`. 잔차가 우연히 작으면 σ기반이, 크면 OLS 가 큰 쪽이다.
> 그래서 42점은 **494**(411 아님), 붕소 11점은 **1,222**(988 아님)를 쓴다.
> M4 에서 붕소에 988 을 쓴 것은 작은 쪽이었고 정정했다. 차이의 유의성이 6.6 σ → **5.7 σ**.
> **규약을 M6 본문에 한 번 적어 뒀으니 다른 절에서 다시 설명하지 말 것.**
>
> **[표 기준점 — M11 과 공유]** 각 Δρ 는 **자기 스윕의 η=0** 기준이다. SG·바이패스는 공통
> 기준(k=1.407985)을 쓰지만 라이저는 자체 기준(k=1.407758)이라 22.7 pcm 어긋난다.
> 그래서 라이저 표기 **+3.5** 는 자체 기준값이고 공통 기준이면 **−8.0** 이다.
> 시나리오별 기준이 물리적으로 옳지만(열화 효과만 분리) **표에 반드시 밝힐 것.**
>
> **[보간 항목]** η 격자가 0.05 간격이라 **η = 0.220 과 0.156 은 격자 밖**이다.
> 두 항목은 인접 계산점 사이의 선형보간(−22.84, −17.06)이고 나머지 셋만 계산점이다.
> 옛 문장 "Every entry is a calculated point" 는 CSV 를 가진 리뷰어가 바로 반증한다. 정정했다.
>
> **[중복 점]** 42점 중 η=0 이 SG·바이패스 양쪽에 있고 공통 시드라 keff 까지 동일하다.
> 실질 독립 계산은 41개다. 중복을 빼면 14,931 ± 422 로 0.5 % 이동. 결론에는 영향 없으나
> "42 points" 라고 쓸 때 이 사실을 알고 있을 것.
>
> **[handoff 16,031 은 재현 안 됨]** 라이저를 넣은 63점 적합이 기준점 없는 형태에서는
> **14,412.7** 로 오히려 내려간다(handoff 3.4 는 16,031 로 올라간다고 적음).
> 어느 쪽이든 라이저는 제외가 맞고 본문도 그렇게 써 있으므로 실무 영향은 없다.

> **[작성 메모]** 리뷰어가 "가장 이식성 높은 숫자"라고 지목한 항목이므로 불확도와 표본 수를 반드시 병기할 것.
>
> 잔차 5.3 pcm 이 차분 σ 18 pcm 보다 작은 이유는 전 런이 시드 1 을 공유해 잡음이 상관되기 때문. 이 사실 자체가 M11 의 핵심 증거이므로 두 항목을 교차 참조할 것.
>
> 옛 값 −612 / −330 을 반응도로 환산해 제시하지 말 것. 그 값들은 개정본에 존재하지 않으며, 환산해 보이면 독자가 혼란스러움. 예시는 새 결과(−238 / −120)로만 들 것.
>
> 63점 회귀는 사용하지 않기로 확정함. 라이저 21점이 밀도축 한 점에 몰려 기울기를 16,031 로 6.8 % 끌어올리고 절편도 이동시킴. 42점 15,010 ± 411 이 올바른 값이며, 라이저 제외 사유를 본문에 명시했음.
> `[TO RUN]` 적분형 PWR 격자 감속재 밀도계수 문헌값과 비교 (리뷰어 마지막 문단 요구)

> **[해소됨 — 라이저 표기]** 절대단위 **8 × 10⁻⁷ g/cm³** 로 통일했다. 옛 표기
> "3 × 10⁻⁵ %" 는 실측(공칭 0.74958 대비 1.07×10⁻⁴ %)과 3.6배 어긋났다. 이제 M6 · M9 · M11 이
> 같은 숫자를 쓰고 ×15,010 하면 0.012 pcm 으로 바로 이어진다.
> **백분율 표기를 되살리지 말 것** — 이 프로젝트가 단위로 두 번 틀렸다.
>
> **[해소됨 — 명칭]** "coefficient of reactivity with respect to coolant density" 로 쓰되
> 고정 온도 계수가 아님을 본문에 명시했다. 기호가 dρ/dρ_coolant 이므로 이름은 글자 그대로
> 맞고, 온도 결합 단서가 M2 · M5 와 일관된다. 커버레터도 같이 고쳤다.
> **초록 · 그림 범례 · 결론에 같은 표현을 쓸 것.**
>
> `[VERIFY]` 공칭 k₀는 CSV의 1.408553 (라이저 η=0). 리뷰어가 가정한 1.409와 실질적으로 동일하나, 논문에는 실제 값을 쓸 것.

---

### M7. Constant mass flow is not defensible in a natural-circulation primary system

**Disposition: Accepted. A loop momentum balance has been implemented and validated.**

**Response.**

The reviewer's criticism is accepted in full, including the observation that the riser scenario modelled only half of the coupling. A lumped one-dimensional loop closure has been added and the primary flow is now solved simultaneously with the loop temperatures in all three scenarios.

Three equations are solved together for the mass flow, the cold-leg temperature and the hot-leg temperature: the steam generator heat transfer relation of M3, the loop energy balance in enthalpy, and a momentum balance equating the buoyancy head from the riser-to-downcomer density difference against the loop resistance. The loop geometry is taken from FSAR Table 4.4-1: lower riser and transition 24.9 ft² over 9.4 ft, upper riser and turn 15.4 ft² over 26.0 ft, downcomer including the steam generators 25.7 ft² over 46.0 ft, and the fuel assembly region 10.3 ft² over 7.9 ft, with the rod-bundle hydraulic diameter used for the core.

The closure carries two lumped parameters, an effective height group and a resistance exponent, fitted at the full-power condition and validated against the FSAR part-load operating map of Table 5.1-2:

| Power | FSAR flow [kg/s] | Model [kg/s] | Error |
|---|---|---|---|
| 15 % | 280.2 | 279.3 | −0.31 % |
| 50 % | 443.7 | 447.2 | +0.79 % |
| 75 % | 521.6 | 522.5 | +0.18 % |
| 100 % | 587.0 | 583.1 | −0.66 % |

The root-mean-square error over the four operating points is 0.55 %. A resistance exponent fixed at the smooth-pipe value does not reproduce the map (RMS 3.4 %), so the exponent is fitted. It is stated in the text that the two parameters are lumped empirical quantities absorbing form losses, the steam generator shell-side crossflow resistance and the use of equivalent circular hydraulic diameters, and that the exponent is therefore not a pipe friction exponent. The FSAR notes that the fuel assembly and steam generator regions dominate the loop pressure loss; the latter is not resolved separately in this screening-level closure, and that is stated as a limitation.

The coupling changes the results in ways that the fixed-flow treatment could not capture:

- **Steam generator fouling.** The flow response amplifies rather than suppresses the effect. As the overall heat transfer coefficient degrades the flow rises slightly, by 0.7 % at the end-of-life fouling resistance, and the loop temperature difference contracts, so the whole loop must sit at a higher temperature to reject the same duty; the cold leg therefore rises more than a fixed-flow treatment predicts. Solving the same model with the flow held at its nominal value instead of closing the momentum balance gives a core-average density change 3.5 % smaller, so for this scenario the coupling is a small correction. It is not small for the riser, where allowing the buoyancy head to respond removes the flow perturbation almost entirely, and that is where the fixed-flow treatment failed.
- **Riser oxide growth.** The response is self-cancelling. The added resistance reduces the flow, which increases the loop temperature difference, which increases the buoyancy head, which restores the flow. Allowing the buoyancy head to respond, which the original model did not, removes the flow perturbation almost entirely. This is precisely the missing half of the coupling the reviewer identifies, and it makes the negative-control interpretation of this scenario considerably stronger than it was.
- **Core bypass.** The loop terminal temperatures, the steam generator duty and the total flow are all unchanged; only the split between the core and bypass streams moves. The natural-circulation loop is therefore insensitive to this scenario to first order, and the effect is confined to the core stream.

The calibrated model reproduces the nominal FSAR flow to within 0.4 % and the nominal terminal temperatures to within 0.15 K. The residual sensitivity is bounded using the FSAR minimum and maximum design flows at full power, 538.5 and 660.5 kg/s.

> **[작성 메모]** 검증 표는 그대로 논문 본문에 넣을 것. 리뷰어가 "not difficult and would strengthen the paper considerably"라고 한 항목이므로, 검증했다는 사실을 표로 보이는 것이 답변의 핵심.
>
> 한계 문장을 빼지 말 것. n = 0.414가 배관 마찰지수처럼 읽히면 2라운드에서 반드시 걸림.
>
> **완료.** `loop_balance.py` 가 `degradation_scenarios.py` 에 통합됐고(`apply_loop_integration.py`),
> 세 시나리오 모두 21점 재실행됨 (`results_rev/{sg_fouling,bypass_leakage,riser_corrosion}`).
> 남은 것은 문안뿐.
> **[검증 완료 — `03_code/checks/verify_m7.py`, `verify_m7b.py`]**
> `loop_balance_calibration.py` 를 직접 실행해 답변서 수치를 전부 재현했다.
> - 교정 C = 0.4999 m, n = 0.414, RMS **0.55 %** — 표와 정확히 일치
> - 부분출력 모델값 279.3 / 447.2 / 522.5 / 583.1, 오차 −0.31 / +0.79 / +0.18 / −0.66 %
> - **n 을 Blasius 값 0.20 에 고정하면 RMS 3.41 %** — 본문의 '3.4 %' 확인
> - 공칭 584.76 kg/s (FSAR 587.0 대비 0.38 %), T_cold 편차 0.130 K, T_hot 0.007 K
> - 라이저 3 mm: 유량 −0.0018 %, 밀도 +7×10⁻⁷ g/cm³ → '거의 사라진다' 확인
> - 바이패스: 총유량 584.764 · T_cold 257.980 · T_hot 310.067 이 x_bp = 0.073/0.085/0.15
>   에서 **완전히 불변**. 코어 출구만 313.675 → 318.018 로 이동. 주장 그대로
>
> **[정정한 것]** 본문에 있던 "약 24 % 증폭"은 **틀렸다. 실제 3.5 %.**
> 유량만 공칭에 묶고 SG·에너지식으로 온도를 푼 대조(유일하게 성립하는 정의)에서
> 결합 −112.9 pcm vs 고정유량 −109.1 pcm 이다. T_cold 까지 고정하면 밀도 변화가
> 정의상 0 이 되어 비교 자체가 성립하지 않는다.
> 실행계획 Part 1.3 의 `−87 → −108 pcm` 은 현재 모델의 어느 값과도 맞지 않으며
> (현재: 결합 −112.9, 실측 −120.2), 상수 확정 이전 값으로 보인다. **쓰지 말 것.**
>
> **[남은 판단]** 공칭 유량이 FSAR 587.0 대비 0.38 % 낮다. C 를 공칭점에 재교정하면
> 이 편차는 없어지지만 부분출력 RMS 가 나빠진다. 현재는 4점 전체 최소제곱이므로
> 이 0.38 % 를 검증 오차로 보고하는 편이 일관된다. 본문이 그렇게 써 있음.

---

### M8. The core barrel bypass model does not describe core barrel bypass

**Disposition: Accepted. The model has been corrected and re-anchored.**

**Response.**

The reviewer is right on both counts. The original model raised the core inlet temperature by mixing hot outlet coolant into the inlet stream and simultaneously reduced the core flow by the same factor, charging the bypass fraction twice. Reconstructing the original equations gives a core-average temperature rise at the maximum bypass fraction that is **2.8 times** the value obtained from a correct treatment.

The model now follows the physics described in the FSAR. Bypass diverts cold downcomer flow around the fuel; the core inlet temperature is unchanged, the core flow is reduced, the core outlet temperature rises, and the bypassed stream mixes with the core exit flow in the upper plenum, lowering the riser temperature. Only the core stream enters the pin-cell coolant state. In the coupled solution this is exactly what happens: over the whole swept range the total primary flow, the cold leg and the hot leg are unchanged to the last tabulated digit at 584.76 kg/s, 257.98 °C and 310.07 °C, while the core outlet moves from 313.68 to 318.02 °C. The natural-circulation loop is insensitive to this scenario, and the effect is confined to the core stream (M7).

The scenario has also been re-anchored. FSAR Table 4.1-1 gives a best-estimate core bypass flow of **7.3 %**, and Sections 4.4.1.3 and 4.4.3.1.1 give **8.5 %** as the value used in subchannel analysis, through the reflector block cooling channels, the fuel assembly guide and instrument tubes, and the gap between the reflector block and the core barrel. The nominal condition therefore corresponds to 7.3 % bypass, not to zero, and degradation is modelled as leakage in excess of the design value. Within the design range of 7.3 to 8.5 % the neutronic effect is small; the parametric extrapolation beyond the design basis is retained but is now clearly labelled as an extrapolation, with the design range marked on the figures.

A related correction: the original model used the FSAR best-estimate flow of 587.3 kg/s as the core flow, whereas it is the total RCS flow. The core flow at nominal conditions is 544.2 kg/s, that is 7.3 % less, and an enthalpy balance at that flow reproduces the FSAR core temperature rise of 99.8 °F to within 0.07 °F. The coupled loop solution used by the sweep settles at a slightly lower total flow and gives 100.25 °F, a residual of 0.45 °F which follows from the cold and hot legs each being reproduced to better than 0.15 K rather than exactly (M7); the two small errors have opposite signs and therefore add in the difference.

The scenario title has been retained, since the model now describes core barrel bypass.

> **[검증 완료 — `03_code/checks/verify_m8.py`]**
> - **2.8 배 확인.** 원 모델 식(T_mix 이중계산)을 원고 상수로 재구성해 x = 0.08 에서
>   코어평균 상승 6.390 K, 정정 처리 2.278 K → **배율 2.805**.
>   **기준점 주의**: 이 비교의 기준은 원 모델이 x=0 에서 실제로 내놓는 284.4955 °C 다.
>   원고 본문이 적은 284.0 을 기준으로 하면 2.48 이 나오는데, 284.0 은 모델 출력이
>   아니다(모델은 310.691 / 284.4955 를 낸다). 선제수정 2 의 기준상태 불일치가 여기서도
>   드러난다. **자기일관적인 쪽이 2.8 이고 그것이 옳다.**
> - **0.07 °F 확인.** 코어유량 587.0 × (1−0.073) = 544.15 kg/s, IF97 엔탈피로 풀면
>   T_out 313.5934 °C, 상승 55.4834 K = **99.870 °F**. FSAR 99.8 대비 +0.070.
>   루프해(총유량 584.765)는 542.08 kg/s → 100.251 °F, +0.451. **본문에 두 값을 모두
>   밝혔다** — 배포 CSV 로 계산하면 후자가 나오므로 밝히지 않으면 모순으로 보인다.
> - 바이패스 불변성은 `verify_m7.py` 에서 확인됨: x = 0.073 / 0.085 / 0.15 에서
>   총유량 584.764, T_cold 257.980, T_hot 310.067 이 **완전 불변**.
>
> **[알아 둘 것]** M11 표의 8.5 % 실측 −17.1 pcm 은 밀도계수 기반 예측 −9.0 pcm 의
> 약 두 배다. 차이 8.1 pcm 은 σ = 9.00 안이라 모순은 아니지만, 그 점의 "1.9 σ" 유의성은
> 상당 부분 몬테카를로 요동이다. 15 % 는 예측 −61.9 vs 실측 −60.7 로 잘 맞는다.
> 리뷰어가 계수로 역산해 볼 수 있으니 알고는 있을 것.

> **완료.** 11점이 아니라 **21점** 재실행됨 (`results_rev/bypass_leakage`). 코어 출구
> 서브쿨링이 15.70 → 11.36 K 로, 세 시나리오 중 가장 낮다(M10 참조).
>
> **[확인 필요]** 본문의 "reproduces the FSAR core temperature rise of 99.8 °F to within
> 0.1 °F" 가 어느 계산인지 명시할 것. 검산 결과 **`NominalConditions` 상수 기준이면
> 99.864 °F(+0.064, 참), 루프해 기준이면 100.251 °F(+0.451, 거짓)** 이다.
> 루프해는 총유량 584.765 에 바이패스 7.3 % 를 제한 코어 542.1 kg/s 라 544 와 다르다.
> M7 의 "단자온도 0.15 K 이내"는 참(입구 0.13 K, 출구 0.086 K) — 두 오차가 반대
> 부호라 상승분에서 합쳐진 것. 문장을 고치거나 어느 계산인지 밝힐 것.

---

### M9. The riser corrosion scenario is a negative control by construction, and for the wrong reason

**Disposition: Accepted on both sub-points; the null result survives and is now demonstrated rather than assumed.**

**Response.**

*Surface roughness.* The reviewer is correct that for an oxide deposit the dominant hydraulic effect is the increase in relative roughness, not the change in flow area, and that roughness appeared nowhere in the model. A roughness term has been added, using the measurements of Turner, Klimas and Brideau (2000), who report that the bare tube surfaces are smooth (RMS roughness below 1 µm) and that deposit formation typically increases roughness by a further 2 to 3 µm.

The result is that the riser remains a null, but now for a demonstrated reason. Using the riser geometry of FSAR Table 4.4-1 (upper riser flow area 15.4 ft², equivalent diameter 1.35 m) and the nominal flow, the riser velocity is approximately 0.59 m/s and the Reynolds number approximately 6.6×10⁶. A 3 µm roughness gives a relative roughness of 2×10⁻⁶; even an extreme 50 µm deposit gives 4×10⁻⁵. The riser remains in the hydraulically smooth regime and the friction factor is essentially unchanged. It is not only the coolant density that is unmoved. Across the twenty-one levels the primary flow changes by 0.0018 %, the core-average temperature by 4 × 10⁻⁴ K, and the core-exit subcooling margin is constant at 15.70 K; the thermal-hydraulic state of the loop is the same at 3 mm of oxide as at zero. The coolant density varies by 8 × 10⁻⁷ g/cm³ over the whole range, which the lattice coefficient of M6 converts to 0.012 pcm of reactivity, and the twenty-one eigenvalues show no trend with the degradation level (Pearson r = +0.10, t = 0.43 on 19 degrees of freedom). The scenario returns a null that is measured rather than assumed. The scenario is therefore a genuine negative control rather than an artefact of the geometric model, and the text now says so on this basis. The nominal riser diameter has also been corrected: the manuscript used 1.50 m, whereas Table 4.4-1 gives equivalent diameters of 1.72 m for the lower riser and 1.35 m for the upper riser.

*The Robertson kinetic law.* Accepted. The appeal to a parabolic law in time while η was an abstract normalised level borrowed the form of a kinetic law without its content. η is now mapped to operating time [TO RUN — via the Robertson rate constant, or dropped in favour of an assumed profile with no kinetic claim].

*Typesetting.* The radical is present in the manuscript source and in the code, which uses `sqrt(level)`; it was lost in conversion to the review PDF. The equations have been re-set as images in the revised manuscript to prevent recurrence, and the PDF proof has been checked.

> **[작성 메모]** 조도를 넣어도 null이라는 것을 *계산해서 보여주는* 것이 이 항목의 핵심. "빠뜨렸지만 어차피 영향 없다"가 아니라 "넣어서 확인했고 영향이 없다"로 써야 함.
>
> **완료.** 조도항(ε = 3 µm)이 `loop_balance.friction()` 에 들어갔고 라이저 **21점**
> 재실행됨. 열수력 해가 전 구간 고정이라는 것이 실측으로 확인됨 — 코어 출구
> 서브쿨링이 21점 전부 **15.70 K 로 동일**하다. 밀도뿐 아니라 온도도 안 움직인다는
> 뜻이라 negative control 논거를 한 단계 강화한다. 본문에 반영할 것.
> **[검증 완료 — `03_code/checks/verify_m9.py`, 라이저 21점 실측]**
> - 밀도 스팬 0.7495818 → 0.7495826 = **8.0×10⁻⁷ g/cm³**, ×15,010 = **0.0120 pcm**
> - 유량 스팬 0.0108 kg/s (**0.0018 %**), T_avg 스팬 **4×10⁻⁴ K**,
>   코어출구 서브쿨링 21점 전부 **15.703 K** — 열수력이 통째로 고정
> - Pearson **r = +0.0974**, **t = +0.426**, df 19, p = 0.675 → 본문의 r=+0.10, t=0.43 확인
> - 유속 **0.5855 m/s**, Re **6.62×10⁶** — **고온측(310.07 °C) 물성 기준**. 라이저는 RCS
>   고온측 유체가 흐르므로 이것이 맞다. 코어 평균 물성으로 계산하면 0.545 / 5.92×10⁶ 이
>   나오는데 그건 틀린 기준이다. 본문 값이 옳다
> - 상대조도 3 µm/1.35 m = **2.2×10⁻⁶**, 50 µm = **3.7×10⁻⁵** → 본문의 2e-6 / 4e-5 확인
> - 기준상태가 SG 스윕과 일치: T_avg 차 **4×10⁻⁴ K**, 밀도 차 **7×10⁻⁷ g/cm³**
>
> **[M11 교차검증도 여기서 끝남]** 라이저 21점의 실측 sd **10.54 pcm**, 보고 σ 평균
> **12.50 pcm**, **χ² = 14.20** (df 20, 95 % 구간 9.6–34.2) — M11 본문과 정확히 일치.
> SG 공칭 k=1.407985 는 라이저 분포에서 z = **+1.62**, 경험 백분위 **90 %**(21점 중 19점이
> 아래). handoff 의 90 % 는 경험 분포 기준이고 정규 근사로는 94.7 % 다.
> 두 스윕의 η=0 k 가 **22.7 pcm(Δk)** 차이나는데 차분 √2σ = 17.7 pcm 대비 **1.28 σ** 로,
> 같은 상태를 독립 2회 계산한 결과로 정상이다.

> `[VERIFY]` Robertson (1991)에서 속도상수 값과 적용 조건 추출

---

### M10. The saturation plateau is a code limitation presented as a result

**Disposition: Accepted on both counts. The plateau no longer occurs, and the subcooling criterion has been withdrawn rather than replaced.**

**Response.**

*The plateau.* The reviewer's diagnosis was correct and the underlying cause was worse than a plotting choice. With the overall heat transfer coefficient established in M3, the assumed R_f,max of 3×10⁻⁴ m²·K/W reduces the UA by 49 % and drives the riser temperature to 327.7 °C, leaving only 1.7 K of subcooling against the saturation temperature of 329.4 °C at the system pressure; the core outlet, some 55 K above the cold leg, exceeds saturation outright. The plateau was therefore a symptom of an input pair that cannot be reached in single-phase operation, not a property of the fouling model. With R_f anchored to measured data (Minor point 9) and U₀ anchored to the FSAR, the entire revised sweep remains single-phase and no ceiling is applied at any point. The figures now show physics over the whole plotted range.

*The subcooling margin.* I accept without reservation that a 5 K margin is not defensible, since subcooled nucleate boiling in the hot channel begins well upstream of bulk saturation. Working out what should replace it, however, showed that the problem was not the value but the criterion, and I have therefore withdrawn the criterion rather than substituting a different number.

Two corrections have to be stated first, because both bear on how the original margin was read. The manuscript reported the core outlet as 309.7 °C; that is the RCS hot-leg temperature, and the core outlet in the revised model is 313.68 °C at the nominal state. Separately, the code applied an internal ceiling of 320 °C while the manuscript quoted T_sat − 5 K = 324.41 °C, so the two differed by 4.4 K and neither was documented. Both errors are mine, and both made the original margin appear larger and better defined than it was.

With those corrected, the margins across the steam generator fouling sweep are:

| location | η = 0 | η = 1 |
|---|---|---|
| core exit (limiting) | 15.70 K | 12.41 K |
| core average (pin-cell state) | 43.55 K | 39.62 K |

evaluated against T_sat = 329.38 °C at 12.755 MPa. The smallest core-exit margin anywhere in the three sweeps is 11.36 K, in the core bypass scenario at the beyond-design-basis extrapolation to 15 %; the riser scenario holds 15.70 K at every level, since its loop temperatures do not move at all. At the nominal state the riser, which is the steam generator primary inlet, sits at 310.06 °C and therefore at 19.32 K of subcooling. The margin contracts across the sweep not because the core temperature rise grows — it changes by only −1.28 K, from 55.70 to 54.41 K — but because the whole loop sits higher as the steam generator degrades.

These numbers are why no threshold is imposed. A criterion of 20 K applied at the limiting location would exclude the nominal design point itself, in every scenario. One at 15 K would admit the nominal point but exclude the fouling sweep beyond η ≈ 0.24 and the bypass sweep beyond η ≈ 0.17, that is three quarters and five sixths of those ranges respectively. A criterion low enough to admit the whole plant-relevant range would have to sit below 11.4 K, which is a value chosen to fit the answer — precisely the objection the reviewer raises against R_f,max, x_max and δ_max in M2, and it would be no more defensible here than there.

The deeper reason is that this model cannot support a subcooling criterion of any value. The pin cell carries a single bulk coolant state at the core-average condition; it has no axial or channel resolution, so it cannot represent the hot channel where subcooled boiling actually begins, and a bulk subcooling threshold would claim a capability the model does not have. Reporting the margin is honest; gating on it is not.

The revised manuscript therefore states the subcooling margin at each degradation level rather than testing it, names the core exit as the limiting location, and records in Section 2.5 that the onset of subcooled nucleate boiling in the hot channel is outside the scope of a bulk pin-cell model and would require a subchannel calculation. The single condition the model can legitimately assert is that the bulk coolant remains single-phase and in IF97 Region 1 throughout, which it does, with a minimum margin of 11.4 K at the core exit, reached only in the beyond-design-basis bypass extrapolation. The internal 320 °C ceiling has been removed from the code, and the deposited sweep data now carries the saturation temperature and the subcooling at both the core-average and core-exit conditions as explicit columns, so that any reader can apply whatever criterion they prefer.

> **[작성 메모]** 임계값 철회로 방향 확정. 계산은 `03_code/checks/probe_m10.py` 출력 기준.
>
> **철회가 옳은 이유 — 반드시 유지할 논리 순서**
> 1. 원고 자신의 오류 두 건(코어 출구 309.7 → 313.68, 코드 320 vs 논문 324.41)을 **먼저** 밝힌다. 그래야 "리뷰어 제안이 공칭을 배제한다"는 말이 반박이 아니라 자기 정정으로 읽힌다
> 2. 그다음에야 각 임계값이 무엇을 배제하는지 수치로 보인다
> 3. 마지막에 "값이 아니라 기준 자체가 이 모델에 맞지 않는다"로 닫는다
>
> **Part 9 규칙 준수**: 리뷰어의 15–20 K 제안을 "틀렸다"고 쓰지 않았다. "저희가 잘못 적은 값 때문에 원래 여유가 커 보였고, 바로잡고 보니 제안 범위가 설계점 위에 놓인다"로 서술. 이 프레이밍을 바꾸지 말 것.
>
> **확인된 수치 (스크립트 출력)**
> - T_sat(IF97, 12.755 MPa) = 329.3788 degC
> - 코어 출구 서브쿨링 15.70 (η=0) → 12.41 K (η=1)
> - 라이저는 η=0 의 19.32 K 만 확정. **스윕 CSV 에 라이저 온도 열이 없어 η=1 값은 계산 불가**
> - 코어 평균 43.55 → 39.62 K
> - 20 K → 세 시나리오 모두 공칭부터 배제
> - 15 K → SG η = 0.240 (76 % 배제), 바이패스 η = 0.171 (83 % 배제), 라이저 전 구간 통과
> - 12 K → SG·라이저 통과, 바이패스만 η = 0.861 부터 배제
> - **코어 출구 서브쿨링 전 스윕 최소 11.36 K** = 바이패스 η=1 (15 %, 설계기준 밖).
>   SG EOL 은 12.41 K. 처음에 SG 만 보고 12.4 를 전체 최소로 썼다가 정정함
> - 원고의 5 K 는 개정 스윕에서 **전 구간 통과**한다(최소 12.41 K). 즉 옛 기준은 실제로 한 번도 발동하지 않았다. 이 사실은 답변서에 쓰지 않았음 — "그러니 5 K 도 괜찮았다"로 읽힐 위험이 있고 리뷰어 지적의 요지가 아니다
> - 코어 온도상승 55.695 → 54.412 K (−1.283 K). 여유 감소는 루프 전체 상승 때문
>
> **[M8 에서 확인할 것 — 여기서 발견]** M8 초안이 "reproduces the FSAR core temperature rise of 99.8 °F to within 0.1 °F" 라고 썼는데, 배포 스윕의 η=0 코어 온도상승은 55.695 K = **100.25 °F** 로 FSAR 99.8 대비 0.45 °F 차이다. M8 의 그 문장이 코어유량 544 kg/s 단독 계산을 가리키는 것인지, 아니면 문장을 고쳐야 하는지 M8 작성 시 확인할 것. 스윕의 η=0 은 루프해(총유량 584.765, 바이패스 7.3 % 제하면 코어 542.1)라 544 와 다르다. **확인 전에는 0.1 °F 문장을 그대로 두지 말 것.**
>
> **[데이터에 없는 것]** CSV 열은 T_inlet_C · T_avg_C · T_outlet_C 뿐이고 T_avg = (in+out)/2 다.
> 라이저/고온측 온도가 열로 없으므로 η>0 의 라이저 서브쿨링은 이 데이터로 못 낸다.
> 필요하면 `solve_loop()` 를 다시 돌려 T_hot 을 뽑거나 스윕 출력에 열을 추가할 것.
>
> **[코드에 반영할 것]**
> - 내부 상한 320 degC 제거 (답변서가 제거했다고 서술함)
> - CSV 에 `T_sat_C`, `subcooling_core_exit_C` 열 추가, `subcooling_C` 는 IF97 T_sat 으로 재계산 → `fix_subcooling.py`
> - `is_safe` 열의 의미도 재정의 필요. 임계값이 없으면 "단상 + Region 1" 만 검사해야 함
>
> **[Minor 12 주의]** 이 답변이 길어졌다. 본문 §2.5 에 들어갈 분량은 두세 문장으로 줄일 것 — 답변서에서만 자세히 설명하고 본문은 짧게.

---

### M11. The significance test uses the wrong standard deviation

**Disposition: Accepted. The correct standard deviation has been measured rather than assumed.**

**Response.**

The reviewer is right on the arithmetic. A difference of two independent Monte Carlo results has a standard deviation of approximately √2 σ, not σ, and forming the signal-to-noise ratio against the single-calculation uncertainty overstates the significance by about 40 %. I also note an internal inconsistency in the original manuscript, now corrected: Section 2.4 stated σ ≤ 15 pcm while Table 3 used 13 pcm.

Because the revised manuscript reports reactivity rather than Δk (M6), the standard deviation must be stated in the same units, and the three relevant figures are given explicitly to avoid the ambiguity that produced the original error:

| quantity | value |
|---|---|
| batch-statistics σ, per calculation, in k | 12.61 pcm |
| differencing √2 σ, in Δk | 17.84 pcm |
| **differencing √2 σ, in reactivity** | **9.00 pcm** |

All significance statements are made against the last of these. On that basis the revised results are:

| scenario | condition | Δρ [pcm] | significance |
|---|---|---|---|
| SG fouling | FSAR design fouling allowance (η = 0.220) | −22.8 | 2.5 σ |
| SG fouling | end-of-life deposit (η = 1) | −120.2 | 13.4 σ |
| Core bypass | FSAR analytical value, 8.5 % (η = 0.156) | −17.1 | 1.9 σ |
| Core bypass | 15 %, beyond design basis (η = 1) | −60.7 | 6.7 σ |
| Riser oxide | 3 mm (η = 1) | +3.5 | 0.4 σ |

Two points about how the table is built. Each Δρ is referred to the η = 0 point of its own sweep, so that what is quoted is the change produced by the degradation and not the run-to-run scatter of the reference calculation; the fouling and bypass sweeps share a reference eigenvalue, the riser sweep has its own, and the two differ by 22.7 pcm in Δk, which is 1.3 differencing standard deviations and therefore ordinary Monte Carlo scatter. Referred instead to the common value the riser entry would read −8.0 pcm rather than +3.5, and 0.9 σ rather than 0.4 σ; it is undetectable either way. Second, the degradation levels were swept on a grid of 0.05, so the two design-condition entries at η = 0.220 and η = 0.156 are linear interpolations between the adjacent calculated points rather than calculations at those exact levels; the three remaining entries are calculated points. Within the design basis the two density-mediated mechanisms sit at the edge of detectability, at 2.5 σ and 1.9 σ; both become unambiguous only outside it, and the riser is not detectable at any level.

The reviewer's second remark, that batch-statistics uncertainties are underestimated in the presence of inter-cycle correlation and that the true figure is therefore likely to be worse still, can now be tested directly rather than assumed. The riser scenario changes the coolant density by 8 × 10⁻⁷ g/cm³ over its entire range, which is 0.012 pcm of reactivity. Its twenty-one points are therefore twenty-one realisations of what is physically the same calculation, and their scatter measures the true eigenvalue uncertainty.

The observed standard deviation across those twenty-one eigenvalues is **10.5 pcm**, against a mean reported batch-statistics uncertainty of **12.5 pcm**. A chi-squared test of the observed variance against the reported one gives 14.2 on 20 degrees of freedom, well inside the 95 % acceptance interval of 9.6 to 34.2. The reported uncertainty is consistent with the realised scatter and, for this problem, is if anything slightly conservative. The concern is real in general but is not borne out here, which is what one would expect for a single reflective pin cell whose fission source is converged from the first generation (Minor 11).

The same twenty-one points also settle a question about the use of a common random seed. The sweep is run with a fixed seed at every degradation level, and it might be supposed that this correlates the perturbed and reference calculations and so reduces the variance of their difference. It does not. The riser points share a seed and differ in input by one part in 10⁶, yet they scatter by the full single-calculation uncertainty. Once any input differs at all the random walks diverge immediately, and no useful correlation survives. The seed is therefore fixed for reproducibility, not for variance reduction, and every difference quoted in the revised manuscript is treated as a difference of independent results, with the standard deviation of 9.00 pcm in reactivity units given above.

The residual scatter of the density-coefficient regression is consistent with this. Fitting reactivity against coolant density leaves a residual standard deviation of 5.3 pcm, and since the regression absorbs the common reference-point error into its intercept, the expected residual is the single-calculation uncertainty expressed in reactivity units, 12.61/k₀² = 6.36 pcm. The observed 5.31 pcm agrees with that, and no correlation benefit is claimed.

On the reviewer's constructive suggestions: raising the history count was considered and rejected, since halving the uncertainty would require four times the sampling for a result that is already limited by the physics rather than by the statistics. Obtaining dk/dρ from a differential tally was examined; OpenMC's differential tallies give derivatives of tally scores rather than of the eigenvalue, so the route is not direct. Instead the coefficient is obtained from a regression over 42 points, which yields it with an uncertainty of 2.7 % (M6) without differencing any single pair.

> **[작성 메모]** 앞선 초안에서 "공통 시드가 차분 분산을 크게 줄였다"고 쓴 것은 **틀렸음**. 잔차 5.3~6.3 pcm 은 σ_keff 12.5 를 반응도 단위로 환산한 6.31 pcm 과 일치할 뿐, 상관의 증거가 아님. 라이저 21점이 시드 동일·입력 동일인데도 σ 만큼 흩어진 것이 결정적 반증. 이 문단을 되살리지 말 것.
>
> 라이저가 σ 검증 실험 역할을 하므로 시드 반복 세트는 **확인용**으로 격하됨. 돌리면 좋지만 M11 답변의 전제는 아님.
>
> `[VERIFY]` 사이클간 상관에 의한 분산 과소평가 1차 문헌 (Brissenden & Garlick 1986 계열). 실험실 문서 CNSAL-TR-2026-01 §2.4 는 OpenMC 문서만 인용하므로 논문 인용으로 쓸 수 없음
> `[TO RUN]` (선택) 표준 상태점에서 시드 반복 10회. 라이저 21점 결과와 교차 확인용
> **완료.** σ = 12.61 pcm(keff), 차분 √2σ = 17.84(Δk) / 9.00(반응도)로 본문 표에 확정 반영됨.
> 붕소 계열은 σ 가 다르다(13.20 pcm keff → 7.81 반응도). k₀² 가 1.6898 대 1.9824 이므로
> **두 계열의 σ 를 섞지 말 것** (M4 참조).

---

## Part 2 — Minor points

| # | Point | Disposition | Action |
|---|---|---|---|
| 1 | "NuScale US600" is the twelve-module plant; the 160 MW_t/50 MW_e unit is the NuScale Power Module | Accepted | Usage corrected throughout; "NuScale Power Module (NPM)" used for the unit, defined on first mention |
| 2 | Missing geometry (clad inner radius, pellet-clad gap, moderator temperature, gap treatment) | Accepted | Complete pin-cell table added: gap outer radius 0.4178 cm, helium gap at 1.598×10⁻⁴ g/cm³, moderator temperature per state point |
| 3 | 4.95 wt % is the design maximum, not a representative loading | Accepted | Stated as a bounding choice, with the effect on the reported k noted |
| 4 | Kim (2026) uncited | Accepted | Moved to the data availability statement only |
| 5 | DHRS and ECCS never appear in the body | Accepted | Nomenclature pruned to terms used |
| 6 | Star markers unexplained and inconsistent with uniform settings | Accepted | Markers removed; the reviewer is right that no point was more precise than any other |
| 7 | Figure 2 (right) duplicates Figure 4 | Accepted | Consolidated; four figures reduced to two |
| 8 | Figure 3 legend unusable (colour encodes η, not scenario) | Accepted | Marker shape now encodes scenario, colour retained for η |
| 9 | R_f,max justification: give the specific figure and page | **Accepted; the value has been replaced** | See below |
| 10 | Check the bypass claim against FSAR Tier 2 Chapter 4 | **Accepted; the FSAR value is now used** | See M8 |
| 11 | Report Shannon entropy convergence or state the basis | **Accepted, with a correction of record** | See below |
| 12 | Scope and limitations stated four times in near-identical wording | Accepted | Sections 2.5 and 5 cut by roughly half; the duplicated plateau sentence in 3.2/3.3 removed |

### Minor 11 — expanded response

The reviewer describes the inactive batch count as generous, on the basis of the 100 inactive batches reported in Section 2.4. That figure was wrong. The calculations used **10 inactive batches and 100 active batches, 110 in total**, not 100 inactive and 200 in total. The particle count of 500,000 per batch and the active batch count of 100 were reported correctly. The error is in the manuscript text, not in the calculations: the settings file written by the sweep records 110 batches with 10 inactive, and the same values appear in the run log. Section 2.4 has been corrected.

The choice therefore requires a justification rather than a claim of conservatism, and the Shannon entropy trajectory now provides one. A 4 × 4 × 1 entropy mesh spanning the pin cell was added; the maximum attainable entropy for that mesh is log₂ 16 = 4.

At the nominal state the trajectory is:

| | mean | standard deviation | range |
|---|---|---|---|
| Inactive batches (10) | 3.1061 | 0.0076 | 3.0888 – 3.1171 |
| Active batches (100) | 3.1059 | — | 3.0675 – 3.1552 |

Three features establish that ten inactive batches are sufficient here.

The entropy of the very first batch, 3.1038, already lies within 0.0023 of the inactive-batch mean; the fission source is converged at the first generation rather than approaching convergence over the inactive interval. The inactive and active means agree to 0.007 %, so the source distribution sampled during the inactive interval is the same as that sampled during tallying. And the spread over the inactive batches is 32 % of the spread over the active batches, so the residual variation during the inactive interval is smaller than the ordinary statistical fluctuation of the converged source.

The same behaviour holds at every state examined, not only at the nominal point. Across nine state points, three from each scenario at degradation levels of 0, 0.5 and 1, the first-batch entropy lies between 3.1024 and 3.1062 and the active-batch mean between 3.1031 and 3.1059. The difference between the inactive and active means ranges from −0.0049 to +0.0048 and changes sign between cases, which identifies it as statistical fluctuation rather than a systematic bias from an unconverged source. The mean standard deviation over the inactive batches is 0.0086, against a mean active-batch range of 0.0953, so the residual variation during the inactive interval is an order of magnitude smaller than the ordinary fluctuation of the converged source. The coolant density varies by about 1 % across the sweep while the entropy varies by about 0.1 %, so the source distribution is effectively insensitive to the degradation level.

This behaviour is expected for the problem class. The model is a two-dimensional single pin cell with reflective boundaries on all four lateral surfaces, so the spatial degrees of freedom of the source are minimal and the initial box source already fills the fuel region. The observed entropy of 3.106 against a maximum of 4 corresponds to a source that is close to uniform across the cell. The relevant OpenMC guidance of 50 to 100 inactive batches is directed at problems with large spatial degrees of freedom; it does not apply to a reflective pin cell, and the entropy trajectory is what settles the question.

The trajectory is reported in the revised manuscript and the statepoint files are included in the repository so that it can be reproduced.

> **[작성 메모]** 이 항목의 구조가 중요함. 리뷰어가 "100은 넉넉하다"고 전제하고 근거만 물었는데 실제가 10이므로, **먼저 오류를 밝히고** 그다음 근거를 대야 함. 순서를 바꾸면 은폐로 읽힘.
>
> 근거 세 가지 중 **첫 배치가 이미 수렴 상태**라는 것이 가장 강함. 배치 1의 3.1038이 비활성 평균과 0.0023 차이. "수렴해 가는" 것이 아니라 "처음부터 수렴해 있는" 상태임.
>
> `[TO RUN]` 엔트로피 궤적 그림 작성 (배치 대 H, 비활성/활성 구분). 본문 또는 supplementary.
> 9점 확정 완료. 첫 배치 3.1024–3.1062, 활성 평균 3.1031–3.1059, 비활성-활성 차 −0.0049~+0.0048.
>
> 별도 방증: 라이저 21점은 밀도가 사실상 고정이므로 동일 계산 21회 반복이며, 그 산포 10.5 pcm 이 보고 σ 12.5 pcm 과 카이제곱 검정에서 일치(χ²=14.2, df=20). 원천 수렴이 정상임을 엔트로피와 독립적으로 뒷받침함. M11 과 교차 참조할 것.



### Minor 9 — expanded response

The reviewer asked for the specific figure and page supporting R_f,max = 3×10⁻⁴ m²·K/W. On checking the three cited sources I found that none of them contains this value. Turner (2011) discusses the thermal effect of deposits only qualitatively and reports no thermal resistance; IAEA-TECDOC-1668 treats fouling as a monitoring and cleanliness-management topic and contains no quantitative fouling resistance; Turner (2013) likewise reports none. The citation as it stood cannot be supported and has been withdrawn.

The value has been replaced with a range derived from three independent sources that agree closely:

| Basis | R_f [m²·K/W] |
|---|---|
| NuScale design fouling factor, FSAR Table 5.4-2 (0.0001 hr·ft²·°F/BTU) | 1.76×10⁻⁵ |
| Largest deposit thickness measured by Turner, Klimas & Brideau (2000), Fig. 4 (~100 µm) | ~8×10⁻⁵ |
| 60-year accumulation from plant chemical-cleaning records reported by Turner (2013) | 6.2–8.5×10⁻⁵ |

The third line uses the recovered iron masses from Point Lepreau (830 kg from four steam generators after 11.7 EFPY) and Gentilly-2 (950 kg after approximately 18 EFPY) with the CANDU 6 tube-bundle area of 3500 m², converted to magnetite and to thickness at 30 % porosity, and to resistance using the measured conductivity. The deposit thermal resistance is evaluated with Equation (4) of Turner, Klimas & Brideau (2000), R_d = δ/κ + R_roughness, taking κ = 1.3 ± 0.2 W/(m·K) and R_roughness = −4×10⁻⁶ m²·K/W for primary-side deposits under single-phase forced convection (their Table 4, p. 59).

R_f,max is now set at **8×10⁻⁵ m²·K/W** as an end-of-life value, with 1.76×10⁻⁵ marked on the figures as the design allowance. The original 3×10⁻⁴ m²·K/W corresponds to a deposit approximately 395 µm thick and an areal loading of about 1430 g/m², against the 48 g/m² reported by Turner (2013) for an operating pilot-scale unit; it is a factor of four beyond the largest measured value and seventeen times the design allowance.

I note two consequences that the reviewer's comment did not reach but which follow from the same sources. First, the linear R_f(η) model is now supported rather than assumed, since Equation (4) is linear in thickness. Second, that equation has a negative intercept: thin deposits improve heat transfer, and many recirculating steam generators show a net improvement in thermal performance during their first years of operation before deteriorating. The linear model is therefore now stated as a bounding simplification applicable to the degradation phase, with the initial enhancement acknowledged.

> **[작성 메모]** 인용 3건 모두에 값이 없다는 것을 스스로 밝히는 것이 이 답변의 핵심. 리뷰어는 "페이지를 대라"고만 했지 "없을 것"이라고는 하지 않았음. 먼저 밝히고 대체하면 신뢰를 얻고, 숨기면 2라운드에서 치명적임.
>
> Turner, Klimas & Brideau (2000) 정확한 서지: *Can. J. Chem. Eng.* **78**: 53–60. DOI 10.1002/cjce.5450780109. Turner (2011)의 참고문헌 목록에 적힌 78: 1–12 는 오기이므로 따라 쓰지 말 것.
> Turner 2011은 세정 실적을 "iron oxide" 질량(1,112 / 1,280 kg)으로, Turner 2013은 "iron" 질량(830 / 950 kg)으로 보고함. Fe₃O₄의 철 분율 0.724로 환산하면 일치. 두 값을 섞지 말 것.

---

## Part 3 — Additional corrections made without being asked

> **[작성 메모]** 이 절은 실제 제출문에 넣을 것. 리뷰어가 못 본 것을 스스로 고쳤다고 밝히면 원고 전체의 신뢰도가 올라가고, 2라운드에서 발견될 위험이 사라짐.

In the course of responding I identified several further discrepancies and have corrected them.

1. **Fuel density.** Section 2.4 stated 10.29 g/cm³ while the model used 10.4 g/cm³. The model value is now reported. The hydrogen-to-uranium ratio of 3.62 quoted in the original manuscript is itself consistent only with 10.4 g/cm³ (10.29 g/cm³ gives 3.66), which confirms that the discrepancy was in the text rather than in the calculation.
2. **Reference state.** The three scenarios did not share a common η = 0 state: the riser sweep began at a core-average temperature of 284.00 °C and a density of 0.752999 g/cm³, while the fouling and bypass sweeps began at 284.50 °C and 0.752080 g/cm³, a difference of 0.12 % in density. In the revision all three are solved from the same plant condition and agree to 4 × 10⁻⁴ °C and 7 × 10⁻⁷ g/cm³, the residual being the convergence tolerance of the loop solver; the corresponding reactivity difference is 0.01 pcm, three orders of magnitude below the Monte Carlo uncertainty.
3. **Specific heat.** The energy balance used a constant 5200 J/(kg·K). Enthalpy differences from IF97 are now used throughout. The specific heat values in the original Table 1 were never used by the calculation, and the column has been removed rather than corrected.
4. **Primary flow.** The FSAR best-estimate flow of 587.3 kg/s is the total RCS flow, not the core flow; it was used as the core flow. Corrected as described under M8.
5. **Validity ceiling.** The code applied an internal diagnostic ceiling of 320 °C while the manuscript reported T_sat − 5 °C = 324.41 °C, a difference of 4.4 K, and neither was documented. Both have been removed: the revised model imposes no subcooling criterion and instead reports the margin at each degradation level, for the reasons given under M10. The only condition asserted is that the bulk coolant remains single-phase and in IF97 Region 1, which is verified for every point.
6. **Nominal moderator state, and three distinct temperatures.** The manuscript's nominal condition of 284.0 °C corresponds to the RCS average temperature (FSAR Table 5.1-2 gives 543.3 °F). The revised model distinguishes three temperatures that the original conflated: the cold leg at 258.11 °C, which sets the core inlet and the steam generator primary outlet; the core average at 285.85 °C, which is the state passed to the pin cell; and the riser at 310.06 °C, which is the steam generator primary inlet. Each is now defined where it is first used, and the reference eigenvalue has been recomputed at the core-average condition.
7. **First person.** The manuscript referred to "the authors" in Section 1 despite being single-authored. Corrected.
8. **Title and abstract.** The title refers to "coolant-density perturbations", but as established under M5 the calculation includes the coupled temperature and spectrum-shift effect. The title has been adjusted accordingly, and the abstract has been rewritten in full: every numerical value it contained has changed, the signal-to-noise figures have been recomputed on the correct differencing standard deviation, and the claim that steam generator fouling produces the largest effect has been removed in favour of the density coefficient result.
9. **Inactive batch count.** Section 2.4 reported 100 inactive batches and 200 batches in total. The calculations used 10 inactive and 110 in total; the particle count and the 100 active batches were reported correctly. Corrected, with the Shannon entropy trajectory now supplied as the justification (Minor 11).
10. **Data availability.** The repository has been extended with the IF97 regression test, the revised scenario models, the loop momentum balance, the borated case and the new sweep data; the statement and the accession date have been updated, and the Kim (2026) entry now appears there rather than in the reference list (Minor 4).

---

## Part 4 — Literature

The reviewer's three suggested references have been added and engaged with substantively rather than listed:

- **Madinka Mweetwa, B., Dahlfors, M. and Margulis, M. (2024)**, *Nucl. Eng. Des.* **428**: 113564 — cited in the discussion of M4, since the finding that removing soluble boron makes the moderator temperature coefficient roughly ten times more negative bears directly on the magnitude of the boron correction; and in the introduction as the point of comparison for full-core degraded-condition results.
- **Mweetwa, B.M. and Margulis, M. (2025)**, *Nucl. Eng. Des.* **445**: 114485 — cited in Section 5 to quantify the gap between a pin-cell reactivity figure and a plant-level margin statement.
- **Xing, Z., Cosgrove, P., Margulis, M. and Shwageraus, E. (2022)**, *Nucl. Eng. Des.* **393**: 111779 — cited in Section 2 as the methodological precedent for justifying a decoupled screening workflow on evidence rather than assertion. [TO CHECK — this study concerns a salt-cooled system; the citation is framed as a methodological precedent for independent property perturbation, not as a PWR result.]

**Crud deposition.** The reviewer identifies the absence of crud from the scenario set as a more significant gap than any of the three included mechanisms, because crud sits inside the pin cell and perturbs the flux directly. I accept this. Adding it properly requires a clad-surface deposit layer in the pin-cell model rather than a bulk density perturbation, which is beyond what can be added in this revision; it is now named explicitly in Section 5 as the highest-priority extension, with the reason, rather than left unmentioned.

**Additional citations added.** NuScale FSAR Tier 2 Chapters 4 and 5 are now cited directly and the AP1000 DCD reference has been removed. The moderator density coefficient reported here is compared with [TO ADD — one published integral PWR lattice value].

> `[VERIFY]` 적분형 PWR 격자 MDC 비교값. Fridman et al. (2023) 벤치마크, Ez Aldeen et al. (2025), Kitcher & Chirayath (2016) 순으로 확인. 이미 인용 중인 문헌에 있으면 추가 문헌 불필요.

---

## Part 5 — Work still outstanding

| Item | Type | Estimated cost |
|---|---|---|
| IF97 regression test + supplementary property output | code | 2 h |
| SG energy balance rewrite (LMTD, enthalpy-based) | code | 1 day |
| Bypass model correction and re-anchoring | code | 2 h |
| Riser roughness term | code | 2 h |
| 1D loop momentum balance (M7 option A) | code | 1 day |
| Boron material definition at 1235 ppm | code | 2 h |
| Differential tally / correlated sampling for dρ/dρ_c | code | 1 day |
| Shannon entropy mesh + reporting | code | 1 h |
| SG sweep, 11 points | compute | ~9 h |
| Bypass sweep, 11 points | compute | ~9 h |
| Riser sweep with roughness, 11 points | compute | ~9 h |
| Borated cases, 4 points | compute | ~3 h |
| Manuscript restructuring around dρ/dρ_c | writing | 2 days |
| Figure consolidation (4 → 2) | writing | 4 h |
| Response letter completion | writing | 1 day |

Measured throughput on the original sweep was 48.8 minutes per pin-cell case (63 cases, 51.3 hours total) at 500,000 particles and 100 active batches. The compute above totals approximately 30 hours and can run in the background against the writing.

**No outstanding source material.** Every major and minor point now has a documented basis. The steam generator heat transfer area, the last open item, is resolved to the module total by the labelling convention of FSAR Tables 5.4-1, 5.4-2 and 5.4-5, giving U₀ = 3.19 kW/m²·K. The only residual uncertainty carried into the paper is the sensitivity of the single log-mean temperature difference to the primary hot-leg temperature, which is stated and bounded in M3.

> **[작성 메모]** 자료 수집 종료. 남은 것은 계산과 집필뿐.

---

## Part 6 — Submission mechanics

> **[작성 메모]** 이 절은 제출문에 넣지 않음. 진행 체크리스트.

- **Upload order in ScholarOne** (mandatory, per the decision letter): (1) response to reviewer, (2) revised manuscript, (3) tables and figures, (4) supplementary material, (5) original files last if retained.
- **Change marking:** all changes in the revised manuscript must be underlined or coloured. Because essentially every number changes, mark at the level of sentence and table rather than word by word, and say so in one line at the top of the manuscript.
- **Reference count:** 19 in the original. Removing the AP1000 DCD and adding the three reviewer-suggested papers, FSAR Chapters 4 and 5, Turner/Klimas/Brideau (2000), a Monte Carlo variance reference, a Shannon entropy reference and a friction-factor reference brings the total to roughly 27, which answers the "thin literature" remark without padding.
- **Word budget:** 2,727 words originally. Sections 2.2 and 2.4 grow (energy balance, loop balance, boron, moderator temperature); Sections 2.5 and 5 halve (Minor 12); four figures become two (Minor 7). Net target 3,200–3,500 words.
- **PDF proof gate:** ScholarOne requires the PDF proof to be built and approved before submission unlocks. Check the equation rendering on that proof, since the lost radical in M9 was a conversion artefact.
