#!/usr/bin/env bash
# WHIR's reference implementation over Goldilocks's quadratic extension at 128 bits, under the
# diagnostic switch of scripts/patches/whir/ (WHIR_DIAG_BEEP), which takes the fold's error as
# BEEP's with affine folding challenges. The same grid as estimates/whir-sweep-grind.tsv:
# 2^17, 2^18 and 2^20 variables, rates 1/2 to 1/64, and each maximum proof of work of that
# table, three verifier repetitions. Output: the table on stdout, in that table's columns.
set -u -o pipefail
work="${RAGU_PCS_WORK:-$(cd "$(dirname "$0")/../work" && pwd)}"  # the external checkouts and outputs
cd "$work/whir-src" || exit 2
printf 'field\tlog2_size\trate\tpow_max\tfirst_samples\tqueries\tproof_KiB\tverifier_khashes\tprover_ms\n'
for d in 17 18 20; do
  for p in 0 8 12 16 17 18 19 20 22 24; do
    for r in 1 2 3 4 5 6; do
      out=$(WHIR_DIAG_BEEP=1 target/release/main -l 128 -d "$d" -r "$r" -f Goldilocks2 -p "$p" --reps 3 2>&1) || exit 1
      samples=$(grep -o 'samples [0-9]* in-domain' <<< "$out" | grep -o '[0-9]*')
      first=$(head -n 1 <<< "$samples")
      queries=$(paste -sd+ - <<< "$samples" | bc)
      size=$(grep -o 'Proof size: [0-9.]*' <<< "$out" | grep -o '[0-9.]*$')
      hashes=$(grep -o 'Average hashes: [0-9.]*' <<< "$out" | grep -o '[0-9.]*$')
      prover=$(grep -o 'Prover time: .* = [0-9.]*ms' <<< "$out" | grep -o '[0-9.]*ms$' | tr -d 'ms')
      printf 'Goldilocks2\t%s\t1/%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$d" "$((1 << r))" "$p" "$first" "$queries" "$size" "$hashes" "$prover"
    done
  done
done
