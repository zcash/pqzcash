#!/usr/bin/env bash
# WHIR's reference implementation (work/whir-src at afec1fa, the binary of the 2026-10 sweeps)
# at 2^17 variables over both fields and rates 1/2 to 1/8, at the 128-bit and 147-bit security
# levels with the binary's defaults otherwise (20 bits of proof of work, folding factor 4,
# Johnson regime), as the 150-bit sweep of 2026-10-14 ran. Output: work/whir-sweep-147.log.
set -u -o pipefail
work="${RAGU_PCS_WORK:-$(cd "$(dirname "$0")/../work" && pwd)}"  # the external checkouts and outputs
cd "$work/whir-src" || exit 2
for field in Field256 Goldilocks3; do
  for r in 1 2 3; do
    for l in 128 147; do
      echo "=== field $field vars 17 rate 2^-$r security $l"
      target/release/main -l "$l" -d 17 -r "$r" -f "$field" --reps 3 2>&1 | tr '\n' ' ' | grep -o 'Proof size: [0-9.]* KiB\|Average hashes: [0-9.]*k' | tr '\n' ' '
      echo
    done
  done
done
