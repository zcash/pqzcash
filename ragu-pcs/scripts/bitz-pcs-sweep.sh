#!/usr/bin/env bash
# BitZ's raw PCS benchmark (its Table 10) at the page's geometry: 2^25 to 2^27 committed bits,
# one thread (the binary is built without `parallel`), three timed reps per shape. The claim
# prime is transcript-sampled after the commitment, as the benchmark does, so the integer lift
# of the paper's Round 1 is not needed. Profiles: `custom:<log inverse rate>:<k0>[:<bits>]`;
# the paper's Table 10 is `custom:1:4` at 100 bits. Outputs: one log per profile here, the
# RESULT lines collected in bitz-pcs-results.txt, and the benchmark's own LaTeX tables.
set -o pipefail
work="${RAGU_PCS_WORK:-$(cd "$(dirname "$0")/../work" && pwd)}"  # the external checkouts and outputs
cd "$work/bitz-poc" || exit 1
BIN=target/release/bitz
OUT=../bitz-out
mkdir -p "$OUT"
: > "$OUT/bitz-pcs-results.txt"
for profile in custom:1:4 custom:1:4:128 custom:3:4:128; do
  tag=${profile//:/-}
  echo "=== $profile $(date)" | tee -a "$OUT/bitz-pcs-results.txt"
  "$BIN" --sweep 25-27 --threads 1 --reps 3 --cooldown 5 --profile "$profile" \
    --latex "$OUT/table-$tag.tex" 2>&1 | tee "$OUT/sweep-$tag.log" | grep "^RESULT\|^instance\|^security\|^note" | tee -a "$OUT/bitz-pcs-results.txt"
done
echo "=== done $(date)" | tee -a "$OUT/bitz-pcs-results.txt"
