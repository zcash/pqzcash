#!/usr/bin/env bash
# One-thread sweeps of the BitZ proof of concept, with every all-core hop closed.
#   bitz-st-sweep.sh <outdir> <sweep> <profile> [<profile> ...]
# e.g. bitz-st-sweep.sh st 22-29 udrg:1:4:128 udrg:3:4:128
#
# The benchmark's --threads 1 sizes only its main pool; the library's Merkle trees, encoder,
# combine step and lincheck fold hop onto a second pool of every core unless RAYON_NUM_THREADS
# is set, which this script does. Outputs go under bitz-out/<outdir>/: one log
# and one LaTeX table per profile, and the RESULT lines appended to results.txt; summarize
# with `python bitz-summary.py bitz-out/<outdir>/sweep-*.log`.
set -o pipefail
work="${RAGU_PCS_WORK:-$(cd "$(dirname "$0")/../work" && pwd)}"  # the external checkouts and outputs
if command -v pmset > /dev/null && ! pmset -g batt | head -1 | grep -q 'AC Power'; then
  echo "not on mains power"; exit 3
fi
cd "$work/bitz-poc" || exit 1
out=../bitz-out/$1; sweep=$2; shift 2
mkdir -p "$out"
for profile in "$@"; do
  tag=${profile//:/-}-$sweep
  echo "=== $profile sweep $sweep RAYON_NUM_THREADS=1 $(date -u +%FT%TZ)" >> "$out/results.txt"
  RAYON_NUM_THREADS=1 target/release/bitz --sweep "$sweep" --sweep-threads 1 --reps 5 --cooldown 10 --rep-cooldown 2 \
    --profile "$profile" --latex "$out/table-$tag.tex" > "$out/sweep-$tag.log" 2>&1
  echo "$profile status $?"
  grep '^RESULT\|failed' "$out/sweep-$tag.log" >> "$out/results.txt"
done
