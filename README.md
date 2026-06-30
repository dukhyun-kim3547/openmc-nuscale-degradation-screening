# OpenMC NuScale Degradation Screening

Screening-level OpenMC pin-cell neutronic sensitivity analysis of a NuScale US600-like SMR fuel lattice to coolant-density perturbations from simplified primary-system degradation models.

## Overview

This repository contains the simulation code, raw results, and figure-generation scripts supporting the manuscript:

> Kim, D. *Screening-Level Pin-Cell Neutronic Sensitivity of a NuScale US600-Like SMR Fuel Lattice to Coolant-Density Perturbations from Simplified Primary-System Degradation Models.* Journal of Nuclear Engineering (submitted).

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
results/
    keff_vs_degradation_sg_fouling.csv
    keff_vs_degradation_bypass_leakage.csv
    keff_vs_degradation_riser_corrosion.csv
figures/
    generate_figures.py           - Reproduces all manuscript figures
```

## Requirements

- Python 3.13
- [OpenMC](https://docs.openmc.org/) 0.15.3
- ENDF/B-VIII.0 nuclear data libraries
- numpy, pandas, matplotlib, scipy

## Reproducing the results

Run the parametric sweep for a given scenario:

```bash
python openmc_model/parametric_sweep.py --scenario sg_fouling --particles 500000 --batches 200 --inactive 100
```

Regenerate figures from existing CSV results:

```bash
python figures/generate_figures.py
```

Each eigenvalue calculation uses 500,000 particles per batch, 200 total batches, and 100 inactive batches, yielding statistical uncertainties σ ≤ 15 pcm.

## Scope and limitations

This analysis is a screening-level study using a two-dimensional reflective pin-cell model with infinite-lattice boundary conditions. It does not represent the full NuScale US600 core geometry and excludes neutron leakage, axial power shaping, control rod worth, soluble boron, burnup effects, and coupled thermal-hydraulic feedback. Results should be interpreted as pin-cell-level sensitivity estimates, not plant-level safety or licensing conclusions. See the manuscript Section 2.5 for full details.

## Citation

If you use this code or data, please cite the manuscript (citation details to be updated upon publication).

## License

MIT License — see [LICENSE](LICENSE).

## Contact

Dukhyun Kim, Department of Nuclear Engineering, Kyung Hee University — kevin3547@khu.ac.kr
