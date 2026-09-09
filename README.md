# OpenMC NuScale Degradation Screening

Screening-level OpenMC pin-cell neutronic sensitivity analysis of a NuScale US600-like SMR fuel lattice to coolant-density perturbations from simplified primary-system degradation models.

## Overview

This repository contains the simulation code, raw results, and figure-generation scripts supporting the manuscript:

> Kim, D. *Screening-Level Pin-Cell Neutronic Sensitivity of a NuScale US600-Like SMR Fuel Lattice to Coolant-Density Perturbations from Simplified Primary-System Degradation Models.* Kerntechnik, manuscript KERN-2026-0074 (submitted 2026-07-27; under revision).

Three simplified primary-system degradation scenarios are modeled:

- **SG helical-coil fouling** — linear fouling thermal resistance
- **Core barrel bypass leakage** — linear bypass fraction
- **Hot riser tube corrosion** — parabolic oxide growth (negative-control case)

Each scenario is parameterized by a normalized degradation level η ∈ [0, 1] across 21 discrete levels. Coolant densities are computed via the IAPWS-IF97 thermodynamic formulation and passed to OpenMC pin-cell eigenvalue calculations using ENDF/B-VIII.0 nuclear data.

## Repository structure

```
degradation_models/
    degradation_scenarios.py      - SG fouling, bypass leakage, riser corrosion models
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
figures/
    generate_figures.py           - Reproduces all manuscript figures
```

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

Regenerate figures from existing CSV results:

```bash
python figures/generate_figures.py
```

Each eigenvalue calculation uses 500,000 particles per batch with 110 total batches, of which 10 are inactive. The batch-statistics uncertainty on the eigenvalue is 12.61 pcm; a difference of two independent calculations therefore carries √2 σ, which is 17.84 pcm expressed in Δk and 9.00 pcm expressed in reactivity.

## Property verification

The IAPWS-IF97 implementation is pinned to the three official Region 1 verification points of IAPWS R7-97, Table 5 — (300 K, 3 MPa), (300 K, 80 MPa) and (500 K, 3 MPa) — for specific volume, internal energy, enthalpy, entropy, isobaric heat capacity and speed of sound, together with domain assertions that every swept state lies in Region 1 and is subcooled.

```bash
pytest -q tests/test_if97_regression.py       # pass/fail
python tests/test_if97_regression.py -v       # full property listing
```

## Scope and limitations

This analysis is a screening-level study using a two-dimensional reflective pin-cell model with infinite-lattice boundary conditions. It does not represent the full NuScale US600 core geometry and excludes neutron leakage, axial power shaping, control rod worth, burnup effects, and crud deposition on the cladding surface. Results should be interpreted as pin-cell-level sensitivity estimates, not plant-level safety or licensing conclusions.

The headline coefficient is fitted on an unborated lattice. A borated comparison at the beginning-of-cycle concentration is reported in the revision and is carried as a correction factor rather than as the representative value. See the manuscript for full details.

## Citation

If you use this code or data, please cite the manuscript (citation details to be updated upon publication).

## License

MIT License — see [LICENSE](LICENSE).

## Contact

Dukhyun Kim, Department of Nuclear Engineering, Kyung Hee University — kevin3547@khu.ac.kr
