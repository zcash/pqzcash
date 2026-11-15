#!/usr/bin/env bash
# The BitZ reruns: the overnight sweep repeated with the
# current build (RUSTFLAGS native; features unchecked,span-metrics,parallel), one profile per
# invocation so that each run fits a foreground call, plus a longer repeat of any one cell.
#   bitz-rerun.sh build                       rebuild the PoC (a no-op if the flags match)
#   bitz-rerun.sh <profile> [sweep] [reps]    e.g. bitz-rerun.sh udrg:3:4:128 25-28 5
# Outputs under bitz-out/rerun/: build.log, one log and one LaTeX table per run, the RESULT
# lines appended to results.txt; summarize with `python bitz-summary.py bitz-out/rerun/results.txt`.
set -o pipefail
work="${RAGU_PCS_WORK:-$(cd "$(dirname "$0")/../work" && pwd)}"  # the external checkouts and outputs
cd "$work/bitz-poc" || exit 1
OUT=../bitz-out/rerun
mkdir -p "$OUT"
if [ "$1" = build ]; then
  RUSTFLAGS="-C target-cpu=native" ~/.cargo/bin/cargo build --release --features unchecked,span-metrics,parallel --bin bitz 2>&1 | tee "$OUT/build.log" | tail -3
  exit $?
fi
profile=$1
sweep=${2:-25-28}
reps=${3:-5}
tag=${profile//:/-}-${sweep}
{
  echo "=== $profile sweep $sweep reps $reps $(date -u +%FT%TZ); $(pmset -g batt | head -1)"
} >> "$OUT/results.txt"
target/release/bitz --sweep "$sweep" --sweep-threads 1,10 --reps "$reps" --cooldown 10 --rep-cooldown 2 \
  --profile "$profile" --latex "$OUT/table-$tag.tex" > "$OUT/sweep-$tag.log" 2>&1
status=$?
grep "^RESULT\|failed\|<" "$OUT/sweep-$tag.log" >> "$OUT/results.txt"
echo "=== done $profile $(date -u +%FT%TZ) status $status" >> "$OUT/results.txt"
exit "$status"
