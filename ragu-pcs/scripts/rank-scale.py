#!/usr/bin/env python
"""The growth of Akita's Module-SIS ranks from the 128-bit floor to a higher one, as the
Pareto page's RANK_SCALE factor uses it: for each instance of the shipped catalog's security
report, the smallest module rank whose maximum secure width covers the instance's width, at
each floor, from the generated infinity width tables of the two checkouts; the factor is the
ratio of the summed ranks. The instance is looked up under its own modulus profile (the
page's 128-bit-field variant), under the 64-bit profile (the 64-bit-commitment and
Goldilocks variants, whose tables coincide for these cells), and, when the Pallas CSV tables
are given, under the Pallas modulus (the two Pasta variants).

The production tables hold each profile's own cells only, so the 64-bit mapping of the
other profiles' instances needs the estimator's CSV tables for the 64-bit modulus at every
cell (the 128-bit one is the Goldilocks table of the 2026-10 runs, identical for these cells).

Usage: python scripts/rank-scale.py REPORT.tsv TABLES_128_DIR TABLES_HIGH_DIR Q64_128.csv Q64_HIGH.csv [PALLAS_128.csv PALLAS_HIGH.csv]
"""
import csv, re, sys
from pathlib import Path

report, dir128, dirhigh, csv128, csvhigh = (Path(a) for a in sys.argv[1:6])
pallas = [Path(a) for a in sys.argv[6:8]]
PROFILE = {"Q128OffsetA7F7": "q128", "Q64Offset59": "q64", "Q32Offset99": "q32"}


def tables(directory):
    out = {}
    for name in ("q128", "q64", "q32"):
        text = (directory / f"{name}.rs").read_text()
        rows = {}
        for m in re.finditer(r"\((\d+), (\d+)\) => Some\(&\[([\d, ]+)\]\)", text):
            rows[(int(m.group(1)), int(m.group(2)))] = [int(x) for x in m.group(3).split(",")]
        out[name] = rows
    return out


def csv_table(path):
    """(d, bound) -> widths by rank, from the estimator's CSV; a width that hit the search
    cap or is uncertified counts as the cap."""
    rows = {}
    with path.open() as f:
        for r in csv.DictReader(f):
            rows.setdefault((int(r["d"]), int(r["coeff_linf_bound"])), {})[int(r["rank"])] = int(r["max_width"])
    return {k: [v[r] for r in sorted(v)] for k, v in rows.items()}


def min_rank(table, d, bound, width):
    widths = table[(d, bound)]
    for rank, w in enumerate(widths, 1):
        if width <= w:
            return rank
    raise SystemExit(f"width {width} exceeds every rank at d={d} bound={bound}")


t128, thigh = tables(dir128), tables(dirhigh)
t128["q64map"], thigh["q64map"] = csv_table(csv128), csv_table(csvhigh)
mappings = [("own", None), ("q64", "q64map")]
if pallas:
    t128["pallas"], thigh["pallas"] = csv_table(pallas[0]), csv_table(pallas[1])
    mappings.append(("pallas", "pallas"))
with report.open() as f:
    instances = list(csv.DictReader(f, delimiter="\t"))
sums = {key: [0, 0] for key, _ in mappings}
moves = {key: 0 for key, _ in mappings}
for inst in instances:
    kind, bound = inst["norm_bound"].split(":")
    assert kind == "linf", inst
    d, width = int(inst["d"]), int(inst["width"])
    for key, profile in mappings:
        profile = profile or PROFILE[inst["modulus_profile"]]
        r0 = min_rank(t128[profile], d, int(bound), width)
        r1 = min_rank(thigh[profile], d, int(bound), width)
        sums[key][0] += r0
        sums[key][1] += r1
        moves[key] += r1 != r0
print(f"{len(instances)} instances")
for key in sums:
    a, b = sums[key]
    print(f"{key}: summed ranks {a} -> {b}, factor {b / a:.3f}, {moves[key]} instances move")
