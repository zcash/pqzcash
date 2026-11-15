#!/usr/bin/env python
"""How far Akita's maximum secure widths shrink from the 128-bit floor to a higher one, per
modulus and ring dimension: over the cells where the floor binds, that is where neither width
hit the estimator's search cap and the width at the higher floor is strictly smaller, the
median of width_128 / width_high, with the number of such cells. The 128-bit side is the
production table's policy audit for the shipped moduli and the estimator's CSV tables for the
comparison moduli; the higher floor's side is the regenerated audit or CSV tables.

The first version of this computation (2026-10-15, for the 150-bit floor) did not consult
hit_cap, so cells capped at 128 bits counted as shrinks of cap / width; its medians at the
larger ring dimensions were inflated by that.

Usage: python scripts/width-shrink.py HIGH_BITS AUDIT_128 AUDIT_HIGH name=CSV128:CSVHIGH ...
"""
import csv, statistics, sys
from collections import defaultdict

high_bits = int(sys.argv[1])
POLICY = {128: "Quantum128BitADPS16", high_bits: f"Quantum{high_bits}BitADPS16"}

def table(path, prof, bits):
    cells = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            if r["policy"] != POLICY[bits] or r["modulus_profile"] != prof or not r["profile"].startswith("local-minimum"):
                continue
            w = int(r["max_width"])
            cells[(int(r["d"]), int(r["coeff_linf_bound"]), int(r["rank"]))] = None if r["hit_cap"] == "true" or w == 0 else w
    return cells

T = {}
for prof in ("q128", "q64", "q32"):
    T[prof] = (table(sys.argv[2], prof, 128), table(sys.argv[3], prof, high_bits))
for spec in sys.argv[4:]:
    prof, paths = spec.split("=")
    p128, phigh = paths.split(":")
    T[prof] = (table(p128, prof, 128), table(phigh, prof, high_bits))
dims = sorted({d for low, _ in T.values() for d, _, _ in low})
print(f"median width_128 / width_{high_bits} over the cells the floor binds (count): neither width at the cap, the higher floor's smaller")
print("modulus    " + "".join(f"{d:>14}" for d in dims))
summary = defaultdict(list)
for prof, (low, high) in T.items():
    row = []
    for d in dims:
        ratios = [low[k] / high[k] for k in low if k[0] == d and k in high and low[k] and high[k] and high[k] < low[k]]
        if ratios:
            med = statistics.median(ratios); summary[d].append(med)
            row.append(f"{med:9.1f} ({len(ratios):3})")
        else:
            row.append(f"{'-':>14}")
    print(f"{prof:10} " + "".join(row))
print("ranges across moduli:", {d: (round(min(v), 1), round(max(v), 1)) for d, v in sorted(summary.items())})
