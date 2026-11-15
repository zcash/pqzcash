#!/usr/bin/env bash
# The BitZ benchmarks, for an otherwise idle machine: rebuild the paper's PoC with the `parallel`
# feature, then run its raw PCS sweep for the three profiles the page uses, at 2^25 to 2^28
# committed bits, once per thread count (1, and 10 as in the paper's tables), five timed reps
# with cooldowns. Outputs under bitz-out/overnight/: one log and one LaTeX table per profile,
# the RESULT lines in results.txt, a summary table in summary.txt, and done.txt at the end.
set -o pipefail
work="${RAGU_PCS_WORK:-$(cd "$(dirname "$0")/../work" && pwd)}"  # the external checkouts and outputs
cd "$work/bitz-poc" || exit 1
OUT=../bitz-out/overnight
mkdir -p "$OUT"
echo "start $(date); $(pmset -g batt | head -1)" > "$OUT/results.txt"
RUSTFLAGS="-C target-cpu=native" ~/.cargo/bin/cargo build --release --features unchecked,span-metrics,parallel --bin bitz > "$OUT/build.log" 2>&1 || { echo "build failed $(date)" >> "$OUT/results.txt"; exit 1; }
for profile in custom:1:4 udrg:1:4:128 udrg:3:4:128; do
  tag=${profile//:/-}
  echo "=== $profile $(date)" >> "$OUT/results.txt"
  target/release/bitz --sweep 25-28 --sweep-threads 1,10 --reps 5 --cooldown 10 --rep-cooldown 2 \
    --profile "$profile" --latex "$OUT/table-$tag.tex" > "$OUT/sweep-$tag.log" 2>&1
  grep "^RESULT\|failed\|<" "$OUT/sweep-$tag.log" >> "$OUT/results.txt"
done
echo "=== done $(date); $(pmset -g batt | head -1)" >> "$OUT/results.txt"
python - "$OUT/results.txt" > "$OUT/summary.txt" <<'EOF'
import re, sys
print(f"{'profile':12} {'n':>2} {'thr':>3} {'commit':>7} {'prove':>8} {'gp':>7} {'lig':>7} {'verify':>6} {'proof':>8} {'nonlig':>7} {'lig_B':>7}")
for line in open(sys.argv[1]):
    if not line.startswith("RESULT"): continue
    r = dict(re.findall(r"(\w+)=(\S+)", line))
    print(f"{r['lig']:12} {r['n']:>2} {r['threads']:>3} {float(r['commit_ms']):7.1f} {float(r['prove_ms']):8.1f} {float(r['prove_gp_ms']):7.1f} {float(r['prove_lig_ms']):7.1f} {float(r['verify_ms']):6.2f} {int(r['proof_bytes']):8,} {int(r['proof_nonlig_bytes']):7,} {int(r['proof_lig_bytes']):7,}")
EOF
date > "$OUT/done.txt"
