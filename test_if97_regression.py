#!/usr/bin/env python3
"""
IF97 regression test for KERN-2026-0074 M1 response.
Verifies three validation points in Region 1.
"""

from iapws import IAPWS97

# Validation points: (Temperature [K], Pressure [MPa])
validation_points = [
    (300, 3),      # Point 1: 300 K, 3 MPa
    (300, 80),     # Point 2: 300 K, 80 MPa
    (500, 3),      # Point 3: 500 K, 3 MPa
]

print("IF97 Region 1 Validation Test")
print("=" * 70)
print()

all_valid = True
results = []

for T_K, P_MPa in validation_points:
    try:
        state = IAPWS97(T=T_K, P=P_MPa)
        region = state.region
        T_C = T_K - 273.15

        # Check if in Region 1
        is_region1 = (region == 1)
        status = "✓ PASS" if is_region1 else "✗ FAIL"

        print(f"Point: T = {T_K} K ({T_C:.2f} °C), P = {P_MPa} MPa")
        print(f"  Region: {region}  {status}")
        print(f"  ρ = {state.rho:.4f} kg/m³")
        print(f"  h = {state.h:.2f} J/kg")
        print(f"  s = {state.s:.4f} J/(kg·K)")
        print()

        results.append({
            'T_K': T_K,
            'T_C': T_C,
            'P_MPa': P_MPa,
            'Region': region,
            'Status': status,
            'rho': state.rho,
            'h': state.h,
            's': state.s
        })

        if not is_region1:
            all_valid = False
    except Exception as e:
        print(f"Point: T = {T_K} K, P = {P_MPa} MPa")
        print(f"  ERROR: {e}")
        print()
        all_valid = False

print("=" * 70)
print()
if all_valid:
    print("✓ All validation points are in Region 1")
    print()
    print("Summary:")
    for r in results:
        print(f"  ({r['T_K']} K, {r['P_MPa']} MPa) → Region {r['Region']} ✓")
    exit(0)
else:
    print("✗ Some validation points are NOT in Region 1")
    exit(1)
