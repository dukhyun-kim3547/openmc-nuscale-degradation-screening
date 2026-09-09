#!/usr/bin/env python3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

# Load data
sg_data = pd.read_csv("keff_vs_degradation_sg_fouling.csv")
bypass_data = pd.read_csv("keff_vs_degradation_bypass_leakage.csv")
riser_data = pd.read_csv("keff_vs_degradation_riser_corrosion.csv")

print(f"SG_FOULING: {len(sg_data)} rows")
print(f"BYPASS: {len(bypass_data)} rows")
print(f"RISER_CORROSION: {len(riser_data)} rows")

# Reference eigenvalues
k0_sg = sg_data.loc[sg_data['degradation_level'] == 0.0, 'keff'].values[0]
k0_bypass = bypass_data.loc[bypass_data['degradation_level'] == 0.0, 'keff'].values[0]
k0_riser = riser_data.loc[riser_data['degradation_level'] == 0.0, 'keff'].values[0]

print(f"\nReference keff: SG={k0_sg:.6f}, BYPASS={k0_bypass:.6f}, RISER={k0_riser:.6f}")

# Calculate reactivity
def calc_reactivity(keff, k0):
    return (1.0/k0 - 1.0/keff) * 1e5

sg_data['reactivity_pcm'] = calc_reactivity(sg_data['keff'], k0_sg)
bypass_data['reactivity_pcm'] = calc_reactivity(bypass_data['keff'], k0_bypass)
riser_data['reactivity_pcm'] = calc_reactivity(riser_data['keff'], k0_riser)

# Figure 1: 42-point regression
fig1_data = pd.concat([sg_data, bypass_data], ignore_index=True)
slope, intercept, r_value, _, std_err = stats.linregress(fig1_data['rho_g_cm3'], fig1_data['reactivity_pcm'])

print(f"\nLinear fit: slope={slope:.2f} pcm/(g/cm³), R²={r_value**2:.4f}")

fig, ax = plt.subplots(figsize=(10, 7))
ax.scatter(sg_data['rho_g_cm3'], sg_data['reactivity_pcm'], label='SG Fouling', alpha=0.6, s=80, marker='o')
ax.scatter(bypass_data['rho_g_cm3'], bypass_data['reactivity_pcm'], label='Bypass', alpha=0.6, s=80, marker='s')

rho_range = np.array([fig1_data['rho_g_cm3'].min(), fig1_data['rho_g_cm3'].max()])
reactivity_fit = slope * rho_range + intercept
ax.plot(rho_range, reactivity_fit, 'k--', linewidth=2, label=f'Linear fit: {slope:.0f} pcm/(g/cm³)')

ax.set_xlabel('Density ρ [g/cm³]', fontsize=12)
ax.set_ylabel('Reactivity [pcm]', fontsize=12)
ax.set_title('Lattice Reactivity vs. Coolant Density', fontsize=14, fontweight='bold')
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)
plt.tight_layout()
fig.savefig('Figure_1_density_reactivity.png', dpi=300, bbox_inches='tight')
print(f"✓ Figure 1 saved")

# Figure 2: Three scenarios
fig, axes = plt.subplots(1, 3, figsize=(15, 5))

axes[0].scatter(sg_data['degradation_level'], sg_data['reactivity_pcm'], s=80, alpha=0.6, color='C0')
axes[0].set_xlabel('R_f [×10⁻⁵ m²K/W]', fontsize=11)
axes[0].set_ylabel('Reactivity [pcm]', fontsize=11)
axes[0].set_title('SG Fouling', fontsize=12, fontweight='bold')
axes[0].grid(True, alpha=0.3)

axes[1].scatter(bypass_data['degradation_level'], bypass_data['reactivity_pcm'], s=80, alpha=0.6, color='C1')
axes[1].set_xlabel('Bypass Fraction [%]', fontsize=11)
axes[1].set_ylabel('Reactivity [pcm]', fontsize=11)
axes[1].set_title('Bypass', fontsize=12, fontweight='bold')
axes[1].grid(True, alpha=0.3)

axes[2].scatter(riser_data['degradation_level'], riser_data['reactivity_pcm'], s=80, alpha=0.6, color='C2')
axes[2].set_xlabel('Corrosion Depth [%]', fontsize=11)
axes[2].set_ylabel('Reactivity [pcm]', fontsize=11)
axes[2].set_title('Riser Corrosion', fontsize=12, fontweight='bold')
axes[2].grid(True, alpha=0.3)

plt.tight_layout()
fig.savefig('Figure_2_three_scenarios.png', dpi=300, bbox_inches='tight')
print(f"✓ Figure 2 saved")

print(f"\n✓ All figures generated!")
