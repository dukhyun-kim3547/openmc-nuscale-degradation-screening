#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fit_coefficient.py -- KERN-2026-0074 revision.

Canonical fit of the lattice coefficient of reactivity with respect to
coolant density, and of every slope uncertainty quoted in the revised
manuscript. Reads the same revised_sweep_data/ used by
figures/generate_figures_revised.py, so it is the independent numerical
check for the coefficient printed on Figure 1 as well as the boron
comparison of Section 3.5.

Convention, stated once and applied everywhere
------------------------------------------------
Reactivity of a swept point against its own sweep reference:

        rho_i = (k_i - k_0) / (k_i * k_0)          [reported in pcm]

The regression is an ORDINARY (unweighted) least squares fit of rho_i on
the coolant density. Weighting is not used: the reported batch-statistics
uncertainties are equal to within a few per cent across the sweep, and
weighting by them would bias the slope toward the low-density end.

Two standard errors are formed for every slope and the LARGER is quoted:

  (a) the ordinary least-squares standard error, which measures the
      realised residual scatter;

  (b) the standard error obtained by propagating each point's own reported
      batch-statistics uncertainty through the fit,

          SE_prop^2 = sum_i [ (x_i - xbar) / Sxx ]^2 * sigma_i^2 ,
          sigma_i   = sigma_k,i / k_i^2      (d rho / d k at fixed k_0),

      which measures what the Monte Carlo sampling alone permits.

k_0 is common to every point of a sweep, so its own uncertainty displaces
the intercept and not the slope; it is therefore NOT entered as an
independent per-point error, and the differencing sqrt(2)*sigma of
Section 3.4 is not used here. That factor applies to a difference of two
individual eigenvalues, which is a different quantity from a fitted slope.

Run:  python3 checks/fit_coefficient.py     (expects ../revised_sweep_data/*.csv,
                                              or set KERN_DATA to override)
"""
import csv
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get('KERN_DATA', os.path.join(HERE, '..', 'revised_sweep_data'))


def load(name):
    with open(os.path.join(DATA, name), newline='', encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def points(rows):
    """[(coolant density, reactivity vs this sweep's eta=0, its sigma)] in pcm."""
    k0 = float(rows[0]['keff'])
    out = []
    for r in rows:
        k, sk = float(r['keff']), float(r['keff_std'])
        out.append((float(r['rho_g_cm3']),
                    (k - k0) / (k * k0) * 1e5,
                    sk / (k * k) * 1e5))
    return out


def fit(p):
    n = len(p)
    xbar = sum(x for x, _, _ in p) / n
    Sxx = sum((x - xbar) ** 2 for x, _, _ in p)
    slope = sum((x - xbar) * y for x, y, _ in p) / Sxx
    icept = sum(y for _, y, _ in p) / n - slope * xbar
    resid = [y - (slope * x + icept) for x, y, _ in p]
    s2 = sum(r * r for r in resid) / (n - 2)
    se_ols = math.sqrt(s2 / Sxx)
    se_prop = math.sqrt(sum(((x - xbar) / Sxx) ** 2 * s * s for x, _, s in p))
    return dict(n=n, slope=slope, intercept=icept,
                se=max(se_ols, se_prop), se_ols=se_ols, se_prop=se_prop,
                resid_sd=math.sqrt(s2),
                sigma_mean=sum(s for _, _, s in p) / n)


def show(label, f):
    print('%-26s n=%2d  slope %9.1f  +- %6.1f   [OLS %6.1f | prop %6.1f]   '
          'resid sd %.2f (expected %.2f)'
          % (label, f['n'], f['slope'], f['se'], f['se_ols'], f['se_prop'],
             f['resid_sd'], f['sigma_mean']))
    return f


def main():
    unb = load('sg_fouling_21pt.csv')                  # steam generator fouling, unborated
    byp = load('bypass_leakage_21pt.csv')               # core barrel bypass
    ris = load('riser_corrosion_21pt.csv')               # hot riser oxide
    bor = load('sg_fouling_boron1235ppm_11pt.csv')      # fouling repeated at 1235 ppm

    rho_nom = float(unb[0]['rho_g_cm3'])
    print('nominal coolant density %.7f g/cm3\n' % rho_nom)

    print('--- headline coefficient (Section 3.3) ---')
    p42 = points(unb) + points(byp)
    f42 = show('42-pt pooled', fit(p42))
    print('%-26s %.2f %%' % ('   relative uncertainty', f42['se'] / f42['slope'] * 100))
    print('%-26s %+.2f pcm' % ('   reactivity at nominal',
                               f42['slope'] * rho_nom + f42['intercept']))
    fsg = show('   steam generator only', fit(points(unb)))
    fbp = show('   core bypass only', fit(points(byp)))
    d = fsg['slope'] - fbp['slope']
    sd = math.hypot(fsg['se'], fbp['se'])
    print('%-26s %.0f +- %.0f   (%.2f sigma)' % ('   they differ by', abs(d), sd, abs(d) / sd))

    print('\n--- properties of the fitted sample ---')
    f41 = show('41-pt, duplicate removed', fit(points(unb) + points(byp)[1:]))
    print('%-26s %.0f pcm/(g/cm3) = %.2f of the quoted SE'
          % ('   shift from 42-pt', f42['slope'] - f41['slope'],
             (f42['slope'] - f41['slope']) / f42['se']))
    fr = show('63-pt, riser included', fit(p42 + points(ris)))
    print('%-26s %+.1f %%' % ('   change from 42-pt',
                              (fr['slope'] / f42['slope'] - 1) * 100))

    print('\n--- soluble boron (Section 3.5) ---')
    etas = {round(float(r['degradation_level']), 3) for r in bor}
    unb11 = [r for r in unb if round(float(r['degradation_level']), 3) in etas]
    fu = show('unborated, 11 matched', fit(points(unb11)))
    fb = show('borated 1235 ppm', fit(points(bor)))
    d = fu['slope'] - fb['slope']
    sd = math.hypot(fu['se'], fb['se'])
    print('%-26s %.0f +- %.0f   (%.2f sigma)' % ('   difference', d, sd, d / sd))
    print('%-26s %.3f   (borated retains %.0f %%)'
          % ('   ratio unborated/borated', fu['slope'] / fb['slope'],
             fb['slope'] / fu['slope'] * 100))
    sd2 = math.hypot(f42['se'], fu['se'])
    print('%-26s %.0f = %.2f sigma' % ('   11-pt vs 42-pt', f42['slope'] - fu['slope'],
                                       (f42['slope'] - fu['slope']) / sd2))
    k0u, k0b = float(unb[0]['keff']), float(bor[0]['keff'])
    print('%-26s %.0f pcm in dk -> %.3f pcm/ppm' % ('   boron worth, 1235 ppm',
                                                    (k0b - k0u) * 1e5, (k0b - k0u) * 1e5 / 1235))
    r_b = (k0b - k0u) / (k0b * k0u) * 1e5
    print('%-26s %.0f pcm in reactivity -> %.2f pcm/ppm' % ('   same, reactivity', r_b, r_b / 1235))

    print('\n--- differencing uncertainty (Section 3.4) ---')
    sig = sum(float(r['keff_std']) for r in unb + byp + ris) / 63 * 1e5
    k0 = float(unb[0]['keff'])
    print('mean batch-statistics sigma over the 63 unborated points : %.2f pcm in k' % sig)
    print('sqrt(2) sigma, in dk                                      : %.2f pcm' % (math.sqrt(2) * sig))
    print('sqrt(2) sigma, in reactivity (divide by k0^2 = %.6f)  : %.2f pcm'
          % (k0 * k0, math.sqrt(2) * sig / (k0 * k0)))


if __name__ == '__main__':
    sys.exit(main())
