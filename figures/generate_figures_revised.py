#!/usr/bin/env python3
"""
Generate the two manuscript figures (KERN-2026-0074, revised) from the
revised parametric-sweep data.

This reproduces Figure 1 and Figure 2 exactly as they appear in the revised
manuscript: it is the actual generator script used for the submitted images,
not a re-derivation.

Minor 6  no star marker (every point has the same batch statistics, so
         nothing is singled out)
Minor 7  the four original figures are consolidated into two
Minor 8  scenario is encoded by marker shape and degradation level eta by
         color, so identity is never carried by color alone

Input   revised_sweep_data/{sg_fouling,bypass_leakage,riser_corrosion}_21pt.csv
        (the revised sweep behind the current manuscript figures -- distinct
        from the frozen keff_vs_degradation_*.csv files at the repository
        root, which are the as-submitted 2026-07-01 sweep and are not
        reproduced by this script; see the top-level README.)
Output  Figure_1_density_reactivity.png
        Figure_2_three_scenarios.png
"""
import csv
import math
import os
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

_REPO_ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("KERN_DATA", str(_REPO_ROOT / "revised_sweep_data")))
OUT = Path(os.environ.get("KERN_FIGOUT", str(_REPO_ROOT / "figures")))
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.size": 10, "font.family": "sans-serif",
    "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": 0.8, "figure.dpi": 300,
    "legend.frameon": False,
})

# Single sequential hue -- still readable by luminance in grayscale print
CMAP = plt.get_cmap("YlGnBu")
NORM = plt.Normalize(0, 1)
INK, MUTED = "#1a1a1a", "#6b6b6b"

SIGMA_R = 9.00          # batch-statistics standard deviation [pcm], reactivity units (M11)
# The 42-point coefficient and its uncertainty are computed directly here,
# using the same max(OLS, propagated) convention as checks/fit_coefficient.py
# (the independent numerical check of this same value). Not hardcoded --
# if the underlying sweep changes, the figure annotation changes with it.


def load(name):
    r = list(csv.DictReader(open(DATA / name)))
    d = {k: np.array([float(x[k]) for x in r]) for k in
         ("degradation_level", "rho_g_cm3", "keff", "keff_std")}
    k0 = d["keff"][0]
    d["rea"] = (d["keff"] - k0) / (d["keff"] * k0) * 1e5      # reactivity change [pcm], own eta=0 reference
    d["rea_std"] = d["keff_std"] * 1e5 / d["keff"] ** 2
    return d


sg, bp, ri = (load("sg_fouling_21pt.csv"),
              load("bypass_leakage_21pt.csv"),
              load("riser_corrosion_21pt.csv"))

SCEN = [("SG helical-coil fouling", sg, "o"),
        ("Core barrel bypass",      bp, "s"),
        ("Riser oxide growth",      ri, "^")]

# ----------------------------------------------------------------
# Figure 1 -- reactivity vs. coolant density
# ----------------------------------------------------------------
fig, ax = plt.subplots(figsize=(6.6, 4.6))

# 42-point regression (SG + bypass). The riser scenario clusters at one
# point on the density axis and contributes no information to the slope.
rho42 = np.r_[sg["rho_g_cm3"], bp["rho_g_cm3"]]
rea42 = np.r_[sg["rea"],       bp["rea"]]
sig42 = np.r_[sg["rea_std"], bp["rea_std"]]
m, c = np.polyfit(rho42, rea42, 1)
_xb = rho42.mean(); _Sxx = ((rho42 - _xb) ** 2).sum()
_resid = rea42 - (m * rho42 + c)
_se_ols = math.sqrt((_resid ** 2).sum() / (len(rho42) - 2) / _Sxx)
_se_prop = math.sqrt((((rho42 - _xb) / _Sxx) ** 2 * sig42 ** 2).sum())
se = max(_se_ols, _se_prop)          # max(OLS, propagated) -- matches the manuscript's methodology
xf = np.array([rho42.min(), rho42.max()])
ax.plot(xf, m * xf + c, "-", color=MUTED, lw=1.2, zorder=1)

for lbl, d, mk in SCEN:
    ax.scatter(d["rho_g_cm3"], d["rea"], c=d["degradation_level"], cmap=CMAP,
               norm=NORM, marker=mk, s=42, linewidths=0.7, edgecolors="white", zorder=3)

ax.axhline(0, color=MUTED, lw=0.7, ls=":", zorder=0)
ax.set_xlabel("Coolant density  $\\rho_\\mathrm{coolant}$  (g/cm$^3$)")
ax.set_ylabel("Reactivity change  $\\Delta\\rho$  (pcm)")
ax.text(0.97, 0.06,
        f"slope  {m:,.0f} $\\pm$ {se:,.0f} pcm/(g/cm$^3$)\n"
        f"42 points, fouling + bypass",
        transform=ax.transAxes, fontsize=9, color=INK, va="bottom", ha="right")

handles = [Line2D([], [], marker=mk, ls="none", color=MUTED, mfc="white",
                   mec=MUTED, ms=6.5, label=lbl) for lbl, _, mk in SCEN]
ax.legend(handles=handles, loc="upper left", fontsize=9, handletextpad=0.4)

cb = fig.colorbar(plt.cm.ScalarMappable(norm=NORM, cmap=CMAP), ax=ax, pad=0.02)
cb.set_label("Degradation level  $\\eta$")
cb.outline.set_visible(False)

fig.tight_layout()
fig.savefig(OUT / "Figure_1_density_reactivity.png", bbox_inches="tight")
plt.close(fig)
print(f"Figure 1  slope {m:,.1f} +- {se:.1f}  (OLS {_se_ols:.1f} / prop {_se_prop:.1f})  "
      f"intercept-at-nominal {m * 0.7495811 + c:+.2f} pcm")

# ----------------------------------------------------------------
# Figure 2 -- three scenarios, physical units on the x axis
# ----------------------------------------------------------------
fig, axes = plt.subplots(1, 3, figsize=(11.2, 4.1), sharey=True)

panels = [
    (sg, "o", "SG helical-coil fouling",
     lambda e: e * 8.0,               "Fouling resistance  $R_f$  ($10^{-5}$ m$^2$K/W)",
     1.761, "FSAR design\nallowance"),
    (bp, "s", "Core barrel bypass",
     lambda e: 7.3 + e * 7.7,         "Bypass fraction  (%)",
     8.5,   "FSAR analytical\nvalue"),
    (ri, "^", "Riser oxide growth",
     lambda e: 3.0 * np.sqrt(e),      "Oxide thickness  $\\delta$  (mm)",
     None,  None),
]

for ax, (d, mk, title, xmap, xlab, mark, mlbl) in zip(axes, panels):
    x = xmap(d["degradation_level"])
    ax.axhspan(-SIGMA_R, SIGMA_R, color=MUTED, alpha=0.13, lw=0, zorder=0)
    ax.axhline(0, color=MUTED, lw=0.7, ls=":", zorder=1)
    if mark is not None:
        ax.axvline(mark, color=INK, lw=0.9, ls="--", zorder=2)
        ax.annotate(mlbl, xy=(mark, 1.0), xycoords=("data", "axes fraction"),
                     xytext=(4, -6), textcoords="offset points",
                     fontsize=8, color=INK, va="top", ha="left", linespacing=1.25)
    ax.errorbar(x, d["rea"], yerr=d["rea_std"], fmt="none",
                ecolor=MUTED, elinewidth=0.7, alpha=0.65, zorder=3)
    ax.scatter(x, d["rea"], c=d["degradation_level"], cmap=CMAP, norm=NORM,
               marker=mk, s=40, linewidths=0.7, edgecolors="white", zorder=4)
    ax.set_title(title, fontsize=10.5, pad=10)
    ax.set_xlabel(xlab)

axes[0].set_ylabel("Reactivity change  $\\Delta\\rho$  (pcm)")
axes[0].text(0.04, 0.05,
             f"shaded band:  $\\pm\\sqrt{{2}}\\sigma$ = {SIGMA_R:.2f} pcm\n"
             f"(difference of two independent runs)",
             transform=axes[0].transAxes, fontsize=8.5, color=MUTED,
             va="bottom", ha="left", linespacing=1.3)

fig.tight_layout()
fig.savefig(OUT / "Figure_2_three_scenarios.png", bbox_inches="tight")
plt.close(fig)

for lbl, d, _ in SCEN:
    print(f"  {lbl:<26} d(rho)(eta=1) = {d['rea'][-1]:+7.2f} pcm "
          f"({abs(d['rea'][-1]) / SIGMA_R:5.2f} sigma)")
