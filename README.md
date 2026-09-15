# OpenMC NuScale Degradation Screening

Screening-level OpenMC pin-cell neutronic sensitivity analysis of a NuScale Power Module-like SMR fuel lattice to coolant-state perturbations from primary-system degradation.

## Overview

This repository contains the simulation code, raw results, and figure-generation scripts supporting the manuscript:

> Kim, D. *Screening-Level Pin-Cell Neutronic Sensitivity of a NuScale Power Module-Like SMR Fuel Lattice to Coolant-State Perturbations from Primary-System Degradation.* Kerntechnik, manuscript KERN-2026-0074 (submitted 2026-07-27; under revision).

Three simplified primary-system degradation scenarios are modeled:

- **SG helical-coil fouling** -- linear fouling thermal resistance
- **Core barrel bypass leakage** -- linear bypass fraction
- **Hot riser tube corrosion** -- assumed monotone oxide growth, no kinetic content (negative-control case)

Each scenario is parameterized by a normalized degradation level η ∈ [0, 1] across 21 discrete levels. Coolant densities are computed via the IAPWS-IF97 thermodynamic formulation and passed to OpenMC pin-cell eigenvalue calculations using ENDF/B-VIII.0 nuclear data.

## Repository structure

```
degradation_models/
    degradation_scenarios.py      - SG fouling, bypass leakage, riser corrosion models
    loop_balance.py                - Natural-circulation loop closure (mdot, T_cold, T_hot)
thermal_hydraulics/
    iapws_coolant.py              - IAPWS-IF97 coolant property coupling
openmc_model/
    parametric_sweep.py           - OpenMC pin-cell model + sweep driver
tests/
    test_if97_regression.py       - IAPWS-IF97 property regression test
keff_vs_degradation_sg_fouling.csv
keff_vs_degradation_bypass_leakage.csv
keff_vs_degradation_riser_corrosion.csv
                                  - As-submitted sweep results (unchanged since 2026-07-01)
revised_sweep_data/
    sg_fouling_21pt.csv
    bypass_leakage_21pt.csv
    riser_corrosion_21pt.csv      - Revised-manuscript sweep results (corrected FSAR-based
                                    nominal conditions and loop closure; see below)
    sg_fouling_boron1235ppm_11pt.csv
                                  - SG-fouling sweep repeated at 1235 ppm soluble boron
                                    (FSAR equilibrium-cycle BOC concentration, reviewer M4)
figures/
    generate_figures.py           - Predates the current two-figure format (Minor 7); does
                                    not reproduce the figures currently in this repository
    generate_figures_revised.py   - Reproduces Figure 1 and Figure 2 exactly as they appear
                                    in the revised manuscript, from revised_sweep_data/
checks/
    fit_coefficient.py            - Independent numerical check of the coefficient printed
                                    on Figure 1 (Section 3.3) and the boron comparison
                                    (Section 3.5), fitted directly from revised_sweep_data/
```

### Two generations of sweep data

The three `keff_vs_degradation_*.csv` files at the repository root are the
as-submitted sweep (2026-07-01) and are kept unchanged as the basis for the
manuscript's original-submission reproducibility statement; they are not
regenerated or overwritten by any script here.

`revised_sweep_data/` is a separate, later sweep run against the corrected
FSAR Tier 2 nominal conditions and the natural-circulation loop closure
added during revision (`degradation_models/loop_balance.py`). Figure 1 and
Figure 2, as they appear in the revised manuscript, are generated from this
data by `figures/generate_figures_revised.py`, not from the root-level CSVs.

`degradation_scenarios.py` and `iapws_coolant.py` import their sibling modules
by bare name (for example `from loop_balance import ...`); each script that
needs them adds the sibling directories to `sys.path` relative to its own
location, so no `PYTHONPATH` setup is required to run the commands below
from the repository root.

## Requirements

- Python 3.13
- [OpenMC](https://docs.openmc.org/) 0.15.3
- ENDF/B-VIII.0 nuclear data libraries
- numpy, pandas, matplotlib, scipy
- iapws (for the property routine and its regression test)

## Reproducing the results

Run the parametric sweep for a given scenario:

```bash
python openmc_model/parametric_sweep.py --scenario sg_fouling --particles 500000 --batches 110 --inactive 10
```

A common random-number seed across all degradation levels (`--seed`, default 1) and a borated coolant option (`--boron-ppm`, reviewer point M4; the FSAR equilibrium-cycle beginning-of-cycle concentration is 1235 ppm) are also available; see `--help` for the rest of the resumable, per-eta-index CLI.

Regenerate the manuscript figures from the revised sweep data:

```bash
python figures/generate_figures_revised.py
```

(`figures/generate_figures.py` is retained for history but predates the
current two-figure format and does not reproduce the figures above.)

Independently check the fitted coefficient and the boron comparison:

```bash
python checks/fit_coefficient.py
```

Each eigenvalue calculation uses 500,000 particles per batch with 110 total batches, of which 10 are inactive. The batch-statistics uncertainty on the eigenvalue is 12.61 pcm; a difference of two independent calculations therefore carries sqrt(2) sigma, which is 17.84 pcm expressed in delta-k and 9.00 pcm expressed in reactivity.

The riser degradation law (`RiserCorrosionModel.compute`) varies only the oxide-driven flow-area reduction; deposit surface roughness is deliberately not folded into it. Running `python degradation_models/degradation_scenarios.py` also prints a standalone roughness sensitivity check (reviewer point M9): adding a representative +3 um deposit roughness (or an extreme +50 um case) on top of the maximum oxide thickness changes the whole-loop coolant density by at most 0.0011%, equivalent to at most 0.12 pcm in reactivity through the fitted coefficient -- about 75 times smaller than the 9.00 pcm differencing uncertainty above -- so it is reported separately rather than mixed into the swept degradation level.

## Property verification

The IAPWS-IF97 implementation is pinned to the three official Region 1 verification points of IAPWS R7-97, Table 5: (300 K, 3 MPa), (300 K, 80 MPa) and (500 K, 3 MPa), for specific volume, internal energy, enthalpy, entropy, isobaric heat capacity and speed of sound, together with domain assertions that every swept state lies in Region 1 and is subcooled.

```bash
pytest -q tests/test_if97_regression.py       # pass/fail
python tests/test_if97_regression.py -v       # full property listing
```

## Scope and limitations

This analysis is a screening-level study using a two-dimensional reflective pin-cell model with infinite-lattice boundary conditions. It does not represent the full NuScale Power Module core geometry and excludes neutron leakage, axial power shaping, control rod worth, burnup effects, and crud deposition on the cladding surface. Results should be interpreted as pin-cell-level sensitivity estimates, not plant-level safety or licensing conclusions.

The headline coefficient is fitted on an unborated lattice. A borated comparison at the beginning-of-cycle concentration is reported in the revision and is carried as a correction factor rather than as the representative value. See the manuscript for full details.

## Citation

If you use this code or data, please cite the manuscript (citation details to be updated upon publication).

## License

MIT License -- see [LICENSE](LICENSE).

## Contact

Dukhyun Kim, Department of Nuclear Engineering, Kyung Hee University -- kevin3547@khu.ac.kr
