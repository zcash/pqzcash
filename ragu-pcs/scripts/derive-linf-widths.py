#!/usr/bin/env python
"""Derive the accumulation matrix's ℓ∞ width table at a floor that Akita's estimator has not
been run at, from the table at a floor where it has. The output is an extrapolation, for rows
that the page marks as derived, until the estimator's own tables replace it.

The rule. A Module-SIS instance of rank n over ring degree d and modulus q resists a BKZ block
of root Hermite factor delta up to a Euclidean norm of about 2^(2 sqrt(n d log2(q) log2(delta))).
A vector of `width` ring elements with coefficients bounded by B has Euclidean norm at most
B sqrt(width d). So the largest secure width W satisfies

    log2(W) + 2 log2(B) + log2(d) = 4 sqrt(n d log2(q) log2(delta)),

and between two floors the left-hand side scales by the square root of the ratio of their
log2(delta). The block size at a floor is the floor over the core-SVP exponent of the page's
cost model, and delta is the usual function of the block size.

`--check` tests the rule on the estimator's own tables: it predicts each floor's widths from
each lower floor's and prints the error in log2(width). A width at the estimator's search cap
is not a measurement and is left out of the check; in the derivation it stays at the cap.

Usage:
    python scripts/derive-linf-widths.py --check estimates/linf-accumulation-widths.tsv
    python scripts/derive-linf-widths.py SOURCE_FLOOR TARGET_FLOOR \\
        estimates/linf-accumulation-widths.tsv [MODULUS ...] \\
        > estimates/linf-accumulation-widths-derived.tsv
With moduli named, only their rows are derived. `--check` with a second table compares a
derived table with the estimator's own at the same floor:
    python scripts/derive-linf-widths.py --check DERIVED.tsv CERTIFIED.tsv
"""

import collections
import csv
import math
import statistics
import sys

QUANTUM_CORE_SVP_EXPONENT = 0.265  # ADPS16, as the page's floors are stated
SEARCH_CAPS = {6_400_000_000_000 >> k for k in range(14)}  # the estimator's cap and its halvings


def log2_delta(floor):
    """log2 of the root Hermite factor of BKZ at the block size of `floor` quantum bits."""
    block = floor / QUANTUM_CORE_SVP_EXPONENT
    return math.log2(block / (2 * math.pi * math.e) * (math.pi * block) ** (1 / block)) / (
        2 * (block - 1)
    )


def derive(width, d, bound, source, target):
    """The width at `target` from the one certified at `source`, by the rule above."""
    if width in SEARCH_CAPS or width <= 1:
        return width
    offset = 2 * math.log2(bound) + math.log2(d)
    scaled = (math.log2(width) + offset) * math.sqrt(log2_delta(target) / log2_delta(source))
    return max(0, math.floor(2 ** (scaled - offset)))


def read(path):
    with open(path) as f:
        return list(csv.DictReader(f, delimiter="\t"))


def check(path):
    cells = collections.defaultdict(dict)
    for r in read(path):
        key = (r["modulus"], int(r["d"]), int(r["rank"]), int(r["bound"]))
        cells[key][int(r["floor"])] = int(r["max_width"])
    floors = sorted({f for by in cells.values() for f in by})
    for i, source in enumerate(floors):
        for target in floors[i + 1 :]:
            errors = collections.defaultdict(list)
            for (modulus, d, _, bound), by in cells.items():
                a, b = by.get(source), by.get(target)
                if a is None or b is None or a in SEARCH_CAPS or b in SEARCH_CAPS:
                    continue
                if a <= 1 or b <= 1:
                    continue
                predicted = derive(a, d, bound, source, target)
                if predicted > 0:
                    errors[modulus].append(math.log2(predicted) - math.log2(b))
            for modulus, e in sorted(errors.items()):
                print(
                    f"{source} -> {target} {modulus}: {len(e)} cells, error in log2(width)"
                    f" median {statistics.median(e):+.3f},"
                    f" 5th to 95th percentile {statistics.quantiles(e, n=20)[0]:+.3f}"
                    f" to {statistics.quantiles(e, n=20)[-1]:+.3f}"
                )


def compare(derived_path, certified_path):
    """The error of a derived table against the estimator's own table at the same floor."""
    key = lambda r: (r["modulus"], int(r["floor"]), int(r["d"]), int(r["rank"]), int(r["bound"]))
    certified = {key(r): int(r["max_width"]) for r in read(certified_path)}
    errors, zeroed = collections.defaultdict(list), collections.Counter()
    for r in read(derived_path):
        a, b = int(r["max_width"]), certified.get(key(r))
        if b is None or a in SEARCH_CAPS or b in SEARCH_CAPS or b <= 1:
            continue
        if a <= 1:
            zeroed[r["modulus"]] += 1
        else:
            errors[r["modulus"]].append(math.log2(a) - math.log2(b))
    for modulus, e in sorted(errors.items()):
        print(
            f"{modulus}: {len(e)} cells, error in log2(width)"
            f" median {statistics.median(e):+.3f},"
            f" 5th to 95th percentile {statistics.quantiles(e, n=20)[0]:+.3f}"
            f" to {statistics.quantiles(e, n=20)[-1]:+.3f};"
            f" {zeroed[modulus]} cells derived as no width where the estimator certifies one"
        )


def main():
    if sys.argv[1] == "--check":
        if len(sys.argv) > 3:
            compare(sys.argv[2], sys.argv[3])
        else:
            check(sys.argv[2])
        return
    source, target, path = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    moduli = set(sys.argv[4:])
    out = csv.writer(sys.stdout, delimiter="\t", lineterminator="\n")
    out.writerow(["modulus", "floor", "d", "rank", "bound", "max_width"])
    for r in read(path):
        if int(r["floor"]) != source or (moduli and r["modulus"] not in moduli):
            continue
        width = derive(int(r["max_width"]), int(r["d"]), int(r["bound"]), source, target)
        out.writerow([r["modulus"], target, r["d"], r["rank"], r["bound"], width])


if __name__ == "__main__":
    main()
