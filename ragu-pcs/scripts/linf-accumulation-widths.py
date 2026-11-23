#!/usr/bin/env python
"""The accumulation matrix's ℓ∞ width table, for pricing Ajtai commitments on the Pareto page
as Akita's catalog shapes them: for each commitment modulus and floor, at the ring degrees
Akita's catalog uses for its accumulation (inner) matrix, the largest width in ring elements
that Akita's ℓ∞ estimator certifies at each module rank and each coefficient ℓ∞ bound of the
catalog's ladder. A reader looks up the cheapest (rank, degree) that is binding at a vector's
bound for the vector's width.

Sources, one per modulus: the 64-bit and 128-bit moduli from the production tables that the
estimator writes into akita-params (`generated_sis_table/q64.rs`, `q128.rs`), which hold the
whole ladder at degrees 512 and 1024; Pallas from the estimator's CSV table for that comparison
profile. The Goldilocks CSV table coincides with the 64-bit modulus's at these cells, except
where a width sits at the estimator's search cap, which the two runs set differently, so the
Goldilocks variant reads the 64-bit modulus's rows; the script checks the coincidence.

Usage, one group of four arguments per floor, the second a directory of production tables or
the 64-bit and 128-bit CSV tables joined by a comma:
    python scripts/linf-accumulation-widths.py \\
        128 TABLES_128_DIR PALLAS_128.csv GOLDILOCKS_128.csv \\
        147 TABLES_147_DIR PALLAS_147.csv GOLDILOCKS_147.csv \\
        150 Q64_150.csv,Q128_150.csv PALLAS_150.csv GOLDILOCKS_150.csv > estimates/linf-accumulation-widths.tsv
"""

import csv
import re
import sys
from pathlib import Path

DEGREES = (512, 1024)
MAX_RANK = 6
MIN_BOUND = 2**12


def rust_table(path):
    """(d, bound) -> widths by rank, from a production table in akita-params."""
    cells = {}
    for m in re.finditer(r"\((\d+), (\d+)\) => Some\(&\[([\d, ]+)\]\)", Path(path).read_text()):
        cells[(int(m.group(1)), int(m.group(2)))] = [int(x) for x in m.group(3).split(",")]
    return cells


def csv_table(path):
    """(d, bound) -> widths by rank, from the estimator's CSV table."""
    rows = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            key = (int(r["d"]), int(r["coeff_linf_bound"]))
            rows.setdefault(key, {})[int(r["rank"])] = int(r["max_width"])
    return {k: [v[r] for r in sorted(v)] for k, v in rows.items()}


def check_coincidence(q64, goldilocks, floor):
    """The Goldilocks and 64-bit tables agree to a tenth of a percent, the moduli's difference
    in size, at every shared cell whose widths are below both runs' search caps, which are the
    estimator's 6.4e12 and its halvings, and above the certification's edge."""
    caps = {6_400_000_000_000 >> k for k in range(12)}
    for key in goldilocks:
        if key not in q64 or key[0] not in DEGREES:
            continue
        for rank, (a, b) in enumerate(zip(goldilocks[key], q64[key]), 1):
            if rank > MAX_RANK or a in caps or b in caps or min(a, b) < 16:
                continue
            assert abs(a - b) <= max(1, 1e-3 * b), (
                f"floor {floor}, cell {key}, rank {rank}: {a} against {b}"
            )


def main():
    args = sys.argv[1:]
    assert len(args) % 4 == 0 and args, __doc__
    print("modulus\tfloor\td\trank\tbound\tmax_width")
    for i in range(0, len(args), 4):
        floor, source, pallas, goldilocks = args[i : i + 4]
        if Path(source).is_dir():
            q64 = rust_table(Path(source) / "q64.rs")
            q128 = rust_table(Path(source) / "q128.rs")
        else:
            q64, q128 = (csv_table(path) for path in source.split(","))
        check_coincidence(q64, csv_table(goldilocks), floor)
        for modulus, table in (("pallas", csv_table(pallas)), ("q64", q64), ("q128", q128)):
            for (d, bound), widths in sorted(table.items()):
                if d not in DEGREES or bound < MIN_BOUND:
                    continue
                for rank, width in enumerate(widths[:MAX_RANK], 1):
                    print(f"{modulus}\t{floor}\t{d}\t{rank}\t{bound}\t{width}")


main()
