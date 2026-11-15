#!/usr/bin/env python
"""Turn the 150-bit re-plan's re-pricing tables into the Pareto page's Akita inputs.

Reads the outputs of scripts/akita-150-replan.sh (default directory work/akita-150-out/replan) and
prints, in the shape of pareto-model.py's AKITA and SLOPE dicts, the opening bytes per variant
and per number K of separately committed 2^14 groups, and the bytes per doubling of the final
polynomial, at the 150-bit floor. The recipe is the one behind the page's 128-bit values:

  K = 0:  fp128      original_total   of fp128_dense final=14:1 in reprice-replan-base.tsv
          pasta_sis  pallas_sis_total of the same row
          pasta      pallas_total     of fp128_dense final=14:1 in reprice-replan-pallas.tsv
          pasta_q64  pallas_q64_total of fp128_dense final=14:1 in reprice-replan-q64.tsv
          goldilocks goldilocks_total of fp64_dense  final=14:1 in reprice-replan-base.tsv
  K > 0:  the same columns of fp128_dense final=14:1;precommitted=14:1,... in
          reprice-groups-k<K>.tsv (the 64-bit commitment pricing runs), and for goldilocks the
          fp64_dense row of reprice-groups-fp64-k<K>.tsv
  SLOPE:  (total at final=16:1 minus total at final=14:1) / 2, from the K = 0 files.

Usage: python scripts/akita-150-page-inputs.py [OUT_DIR]
"""

import csv
import sys
from pathlib import Path

out = Path(sys.argv[1] if len(sys.argv) > 1 else "work/akita-150-out/replan")
K = [0, 1, 2, 4, 8, 12]
VARIANTS = {  # variant: (K=0 file, column, family)
    "fp128": ("reprice-replan-base.tsv", "original_total", "fp128_dense"),
    "goldilocks": ("reprice-replan-base.tsv", "goldilocks_total", "fp64_dense"),
    "pasta_q64": ("reprice-replan-q64.tsv", "pallas_q64_total", "fp128_dense"),
    "pasta_sis": ("reprice-replan-base.tsv", "pallas_sis_total", "fp128_dense"),
    "pasta": ("reprice-replan-pallas.tsv", "pallas_total", "fp128_dense"),
}


def rows(path: Path) -> list[dict]:
    with path.open() as f:
        return list(csv.DictReader(f, delimiter="\t"))


def total(path: Path, family: str, key: str, column: str) -> int:
    for r in rows(path):
        if r["family"] == family and r["logical_key"] == key:
            return int(r[column])
    keys = sorted({r["logical_key"] for r in rows(path) if r["family"] == family})
    raise SystemExit(f"{path}: no row {family} {key!r}; its keys are {keys}")


def key(k: int) -> str:
    return "final=14:1;precommitted=" + ",".join(["14:1"] * k)


akita = {}
slope = {}
for variant, (file0, column, family) in VARIANTS.items():
    base = out / file0
    values = [total(base, family, key(0), column)]
    prefix = "fp64-" if variant == "goldilocks" else ""
    for k in K[1:]:
        values.append(total(out / f"reprice-groups-{prefix}k{k}.tsv", family, key(k), column))
    akita[variant] = values
    slope[variant] = (total(base, family, "final=16:1;precommitted=", column) - values[0]) // 2

print("AKITA_K =", K)
print("AKITA_150 = {")
for variant, values in akita.items():
    print(f'    "{variant}": {values},')
print("}")
print("SLOPE_150 =", slope)
