"""
generate_figures.py
===================
Reproduces all manuscript figures from the CSV result files.

Companion code for:
  Kim, D. "Screening-Level Pin-Cell Neutronic Sensitivity of a NuScale
  US600-Like SMR Fuel Lattice to Coolant-Density Perturbations from
  Simplified Primary-System Degradation Models." Journal of Nuclear
  Engineering (submitted).

Usage
-----
  # From the repository root directory:
  python figures/generate_figures.py

  # Optional: specify custom input/output directories
  python figures/generate_figures.py --results-dir results --output-dir figures/output

Output
------
  fig1_density.png                 -- Fig. 1 in the manuscript
  fig2_eigenvalue_vs_eta.png       -- Fig. 2
  fig3_eigenvalue_vs_density.png   -- Fig. 3
  fig4_delta_k_vs_eta.png          -- Fig. 4

Requirements
------------
  numpy, pandas, matplotlib, scipy
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------
# Global plot style
# ---------------------------------------------------------------
plt.rcParams.update({
    'font.size':       12,
    'axes.grid':       True,
    'grid.alpha':      0.3,
    'lines.linewidth': 2,
    'figure.dpi':      300,
    'font.family':     'sans-serif',
})

SCENARIOS = ['SG_FOULING', 'BYPASS_LEAKAGE', 'RISER_CORROSION']

COLORS = {
    'SG_FOULING':      '#d62728',
    'BYPASS_LEAKAGE':  '#ff7f0e',
    'RISER_CORROSION': '#1f77b4',
}

LABELS = {
    'SG_FOULING':      'SG Fouling',
    'BYPASS_LEAKAGE':  'Core Barrel Bypass',
    'RISER_CORROSION': 'Riser Corrosion',
}


# ---------------------------------------------------------------
# Load CSV results
# ---------------------------------------------------------------
def load_results(results_dir: Path) -> dict[str, pd.DataFrame]:
    """
    Load the three scenario CSV files and compute Dk columns.

    Parameters
    ----------
    results_dir : Path
        Directory containing keff_vs_degradation_*.csv files.

    Returns
    -------
    dict mapping scenario name -> DataFrame with added 'delta_k_pcm' column
    """
    dfs = {}
    for sc in SCENARIOS:
        fpath = results_dir / f"keff_vs_degradation_{sc.lower()}.csv"
        if not fpath.exists():
            raise FileNotFoundError(
                f"Result file not found: {fpath}\n"
                f"Expected CSV files in: {results_dir.resolve()}"
            )
        df = pd.read_csv(fpath)
        k0 = df.loc[df['degradation_level'] == 0.0, 'keff'].values[0]
        df['delta_k_pcm'] = (df['keff'] - k0) * 1e5
        dfs[sc] = df.copy()
    return dfs


# ---------------------------------------------------------------
# Figure 1: Coolant density vs degradation level
# ---------------------------------------------------------------
def plot_fig1(dfs: dict, out_dir: Path) -> None:
    """
    Fig. 1 -- Coolant density rho as a function of degradation level eta.
    Left panel: absolute density [g/cm^3].
    Right panel: fractional density change relative to nominal [%].
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    for sc in SCENARIOS:
        df = dfs[sc]
        axes[0].plot(
            df['degradation_level'], df['rho_g_cm3'],
            '-o', color=COLORS[sc], label=LABELS[sc], markersize=4,
        )
        axes[1].plot(
            df['degradation_level'], df['delta_rho_pct'],
            '-o', color=COLORS[sc], label=LABELS[sc], markersize=4,
        )

    axes[0].set_xlabel('Degradation level eta')
    axes[0].set_ylabel('Coolant density rho (g/cm^3)')
    axes[0].set_title('Absolute coolant density')
    axes[0].legend()

    axes[1].set_xlabel('Degradation level eta')
    axes[1].set_ylabel('Delta_rho / rho_0 (%)')
    axes[1].set_title('Fractional density change relative to nominal')
    axes[1].axhline(0, color='gray', linestyle='--', linewidth=1)
    axes[1].legend()

    fig.tight_layout()
    out = out_dir / 'fig1_density.png'
    fig.savefig(out, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f'Fig. 1 saved -> {out}')


# ---------------------------------------------------------------
# Figure 2: Reflective pin-cell eigenvalue vs degradation level
# ---------------------------------------------------------------
def plot_fig2(dfs: dict, out_dir: Path) -> None:
    """
    Fig. 2 -- Reflective pin-cell eigenvalue as a function of
    degradation level eta.
    Left panel: absolute eigenvalue with +/-2sigma error bars.
    Right panel: eigenvalue change Dk relative to nominal [pcm].
    Stars mark the highest-precision calculation point per scenario.
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    offsets = {
        'SG_FOULING':      -0.01,
        'BYPASS_LEAKAGE':   0.00,
        'RISER_CORROSION':  0.01,
    }

    for sc in SCENARIOS:
        df = dfs[sc]
        x_off = df['degradation_level'] + offsets[sc]

        axes[0].plot(
            df['degradation_level'], df['keff'],
            '-', color=COLORS[sc], label=LABELS[sc],
        )
        axes[0].errorbar(
            x_off, df['keff'], yerr=df['keff_std'] * 2,
            fmt='none', ecolor=COLORS[sc], alpha=0.5, elinewidth=0.8,
        )

        hf = df[df['keff_std'] * 1e5 < 14]
        if len(hf):
            best = hf.loc[hf['keff_std'].idxmin()]
            axes[0].scatter(
                best['degradation_level'], best['keff'],
                marker='*', s=200, color=COLORS[sc], zorder=5,
            )

        axes[1].plot(
            df['degradation_level'], df['delta_k_pcm'],
            '-o', color=COLORS[sc], label=LABELS[sc], markersize=4,
        )
        if len(hf):
            best = hf.loc[hf['keff_std'].idxmin()]
            axes[1].scatter(
                best['degradation_level'], best['delta_k_pcm'],
                marker='*', s=200, color=COLORS[sc], zorder=5,
            )

    axes[0].set_xlabel('Degradation level eta')
    axes[0].set_ylabel('Reflective pin-cell eigenvalue')
    axes[0].set_title('Reflective pin-cell eigenvalue vs degradation level')
    axes[0].legend()

    axes[1].set_xlabel('Degradation level eta')
    axes[1].set_ylabel('Dk relative to nominal (pcm)')
    axes[1].set_title('Eigenvalue change Dk relative to nominal')
    axes[1].axhline(0, color='gray', linestyle='--', linewidth=1)
    axes[1].legend()

    fig.tight_layout()
    out = out_dir / 'fig2_eigenvalue_vs_eta.png'
    fig.savefig(out, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f'Fig. 2 saved -> {out}')


# ---------------------------------------------------------------
# Figure 3: Reflective pin-cell eigenvalue vs coolant density
# ---------------------------------------------------------------
def plot_fig3(dfs: dict, out_dir: Path) -> None:
    """
    Fig. 3 -- Reflective pin-cell eigenvalue change Dk as a function
    of primary coolant density rho for all scenarios (eta > 0).
    Color scale indicates the degradation level eta.
    Dashed line: linear regression fit for the Core Barrel Bypass scenario.
    """
    fig, ax = plt.subplots(figsize=(8, 6))

    sc_ = None
    for sc in SCENARIOS:
        df = dfs[sc]
        df_nz = df[df['degradation_level'] > 0]
        sc_ = ax.scatter(
            df_nz['rho_g_cm3'], df_nz['delta_k_pcm'],
            c=df_nz['degradation_level'], cmap='viridis',
            marker='o', s=40, label=LABELS[sc],
            vmin=0, vmax=1, alpha=0.8,
        )

    # Linear regression for Core Barrel Bypass only
    df_bp = dfs['BYPASS_LEAKAGE']
    df_bp_nz = df_bp[df_bp['degradation_level'] > 0]
    slope, intercept, r_val, p_val, se = stats.linregress(
        df_bp_nz['rho_g_cm3'], df_bp_nz['delta_k_pcm'],
    )
    rho_fit = np.linspace(
        df_bp_nz['rho_g_cm3'].min(),
        df_bp_nz['rho_g_cm3'].max(),
        100,
    )
    ax.plot(
        rho_fit, slope * rho_fit + intercept,
        '--', color=COLORS['BYPASS_LEAKAGE'], linewidth=1.5,
        label=f'Linear fit (Bypass): {slope:.0f} pcm/(g/cm^3)',
    )

    cb = fig.colorbar(sc_, ax=ax)
    cb.set_label('Degradation level eta')

    ax.set_xlabel('Primary coolant density rho (g/cm^3)')
    ax.set_ylabel('Dk relative to nominal (pcm)')
    ax.set_title('Reflective pin-cell eigenvalue vs coolant density')
    ax.legend(loc='upper left', fontsize=10)

    fig.tight_layout()
    out = out_dir / 'fig3_eigenvalue_vs_density.png'
    fig.savefig(out, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f'Fig. 3 saved -> {out}')


# ---------------------------------------------------------------
# Figure 4: Pin-cell eigenvalue change vs degradation level
# ---------------------------------------------------------------
def plot_fig4(dfs: dict, out_dir: Path) -> None:
    """
    Fig. 4 -- Pin-cell eigenvalue change Dk as a function of
    degradation level eta for all three scenarios.
    Dashed line at Dk = 0 indicates the nominal condition.
    Stars mark the highest-precision calculation point per scenario.
    """
    fig, ax = plt.subplots(figsize=(9, 6))

    for sc in SCENARIOS:
        df = dfs[sc]
        ax.plot(
            df['degradation_level'], df['delta_k_pcm'],
            '-o', color=COLORS[sc], label=LABELS[sc], markersize=4,
        )
        hf = df[df['keff_std'] * 1e5 < 14]
        if len(hf):
            best = hf.loc[hf['keff_std'].idxmin()]
            ax.scatter(
                best['degradation_level'], best['delta_k_pcm'],
                marker='*', s=200, color=COLORS[sc], zorder=5,
            )

    ax.axhline(0, color='gray', linestyle='--', linewidth=1.2,
               label='Nominal (Dk = 0)')
    ax.set_xlabel('Degradation level eta')
    ax.set_ylabel('Dk relative to nominal (pcm)')
    ax.set_title('Pin-cell eigenvalue change Dk vs degradation level')
    ax.legend()

    fig.tight_layout()
    out = out_dir / 'fig4_delta_k_vs_eta.png'
    fig.savefig(out, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f'Fig. 4 saved -> {out}')


# ---------------------------------------------------------------
# CLI
# ---------------------------------------------------------------
def _parse() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Reproduce all manuscript figures from CSV result files."
    )
    p.add_argument(
        '--results-dir', default='results',
        help=(
            "Directory containing keff_vs_degradation_*.csv files "
            "(default: results/)"
        ),
    )
    p.add_argument(
        '--output-dir', default=None,
        help=(
            "Directory to write PNG figures "
            "(default: same as --results-dir)"
        ),
    )
    return p.parse_args()


def main() -> None:
    args = _parse()
    results_dir = Path(args.results_dir)
    out_dir = Path(args.output_dir) if args.output_dir else results_dir / 'figures'
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading results from : {results_dir.resolve()}")
    print(f"Saving figures to    : {out_dir.resolve()}")
    print()

    dfs = load_results(results_dir)

    plot_fig1(dfs, out_dir)
    plot_fig2(dfs, out_dir)
    plot_fig3(dfs, out_dir)
    plot_fig4(dfs, out_dir)

    print(f"\nAll figures saved to {out_dir.resolve()}")


if __name__ == '__main__':
    main()
