#!/usr/bin/env bash
# Plan Akita at the 165-bit level: a 165-bit ADPS16-quantum floor, the core-SVP level of
# ML-KEM-768 and ML-DSA-65, with the three-map compression chain that the level needs (images
# of 2,304, 1,152, and 1,024 bits; see scripts/compression-chain.sh). It works on the worktree
# work/akita-src-165 that scripts/akita-checkout.sh makes, on the branch level3-165, where
# scripts/patches/akita/0003-* has renamed the policy and put in the chain. The script
# regenerates the runtime width tables at the floor, re-sizes the nine compression cells from
# them, rebuilds, commits, and runs the re-plan. Each step is logged under OUT (default
# work/akita-165-out) and the script stops at the first failure:
#   scripts/akita-165-pipeline.sh [OUT]
# SKIP_TABLES=1 keeps the tables of an earlier run. The certified infinity table took about an
# hour at 147 bits.
#
# The patch is for planning only: the prover and the verifier are not adapted to the chain,
# so nothing here runs a proof.
set -u -o pipefail
scripts="$(cd "$(dirname "$0")" && pwd)"
work="${RAGU_PCS_WORK:-$(cd "$scripts/../work" && pwd)}"  # the external checkouts and outputs

repo="$work/akita-src-165"
out="${1:-$work/akita-165-out}"
mkdir -p "$out"
summary="$out/summary.txt"
: > "$summary"
export RUSTUP_TOOLCHAIN="${RUSTUP_TOOLCHAIN:-1.96.0}"
policy=Quantum165BitADPS16
trailer="Co-Authored-By: Claude Mythos 5.2 <noreply@anthropic.com>"

log() { printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$summary"; }
step() {
    # step NAME COMMAND... : log, run with output to NAME.log, stop on failure.
    local name="$1"; shift
    local start; start=$(date +%s)
    log "start $name"
    if "$@" > "$out/$name.log" 2>&1; then
        log "ok    $name ($(( $(date +%s) - start )) s)"
    else
        log "FAIL  $name ($(( $(date +%s) - start )) s), see $out/$name.log"
        exit 1
    fi
}

cd "$repo" || exit 2
if [ "$(git branch --show-current)" != "level3-165" ]; then
    log "unexpected branch $(git branch --show-current) in $repo"; exit 2
fi

# 1. Build the estimator's emitters and regenerate the runtime tables at the floor. The
#    emitters write into the akita-params crate.
if [ "${SKIP_TABLES:-0}" = 1 ]; then
    log "tables kept from the previous run (SKIP_TABLES=1)"
else
    step build-estimator cargo build --release -p akita-sis-estimator --examples
    step l2-rust-split target/release/examples/euclidean_width_table --format rust-split
    step linf-rust-split target/release/examples/infinity_width_table --format rust-split --policy "$policy"
fi

# 2. Re-size the nine compression cells from the regenerated tables. A cell's width is the
#    entry at its rank in the coefficient-bound-1 row of its ring dimension, the row
#    "(d, 1) =>", whose entries are in rank order from rank one. Each must cover the width
#    that an 8 KiB source needs, or the chain does not reach the floor.
python - "$out" <<'EOF' || { log "FAIL  compression cells"; exit 1; }
import re, sys, pathlib
out = pathlib.Path(sys.argv[1])
# (profile, table, ring dimension, rank, input bits of the map for an 8 KiB source)
cells = [("Q128OffsetA7F7", "q128", 2, 9, 65536), ("Q128OffsetA7F7", "q128", 1, 9, 2304),
         ("Q128OffsetA7F7", "q128", 8, 1, 1152),
         ("Q64Offset59", "q64", 4, 9, 65536), ("Q64Offset59", "q64", 2, 9, 2304),
         ("Q64Offset59", "q64", 16, 1, 1152),
         ("Q32Offset99", "q32", 8, 9, 65536), ("Q32Offset99", "q32", 4, 9, 2304),
         ("Q32Offset99", "q32", 32, 1, 1152)]
src = pathlib.Path("crates/akita-params/src/sis/compression.rs")
text = src.read_text()
report, short = [], []
for profile, table, d, rank, input_bits in cells:
    rows = pathlib.Path(f"crates/akita-params/src/sis/generated_sis_table/{table}.rs").read_text()
    m = re.search(rf"\({d}, 1\) => Some\(&\[([\d, ]+)\]", rows)
    if not m:
        sys.exit(f"no bound-1 row for {table} d={d}")
    widths = [int(w) for w in m.group(1).split(",") if w.strip()]
    if len(widths) < rank:
        sys.exit(f"the bound-1 row for {table} d={d} stops at rank {len(widths)}")
    width, needed = widths[rank - 1], -(-input_bits // d)
    if width < needed:
        short.append(f"{table} d={d} rank {rank}: {width} < {needed}")
    # the table's lines only, not the tests' calls
    pat = rf"^(\s+\(SisModulusProfileId::{profile}, {d}, {rank}, )[\d_]+\),$"
    text, n = re.subn(pat, lambda mm: f"{mm.group(1)}{width:_}),", text, flags=re.M)
    if n != 1:
        sys.exit(f"cell ({profile}, {d}, {rank}) not found once in compression.rs: {n}")
    report.append(f"{table} d={d} rank {rank}: {width} (needs {needed})")
(out / "compression-cells.txt").write_text("\n".join(report) + "\n")
print("\n".join(report))
if short:
    sys.exit("the chain does not reach the floor: " + "; ".join(short))
src.write_text(text)
EOF
log "compression cells: $(tr '\n' ';' < "$out/compression-cells.txt")"

# 3. Rebuild the planner and commit the level's state.
step build-planner cargo build --release -p akita-planner --features catalog-security --examples --bin gen_schedule_artifacts
git diff --name-only > "$out/165-bit-files.txt"
if [ -s "$out/165-bit-files.txt" ]; then
    xargs git add -- < "$out/165-bit-files.txt"
    git commit -q -F - <<EOF
The 165-bit runtime tables and compression cells

The width tables are regenerated at the 165-bit floor, and the nine
compression cells re-sized from them.

$trailer
EOF
    log "committed the 165-bit state as $(git rev-parse --short HEAD)"
fi

# 4. The re-plan, as scripts/akita-150-replan.sh but on this worktree, without
#    --catalog-report, which needs a catalog baseline, and into this run's output directory.
gsed -e 's/--catalog-report "[^"]*" //' -e 's#akita-src-150#akita-src-165#' \
     -e 's#akita-150-out/replan#akita-165-out/replan#' "$scripts/akita-150-replan.sh" > "$out/akita-165-replan.sh"
chmod +x "$out/akita-165-replan.sh"
log "start replan (its own summary is in $out/replan/summary.txt)"
RAGU_PCS_WORK="$work" "$out/akita-165-replan.sh" "$out/replan" > "$out/replan.log" 2>&1
log "replan finished with exit $? ; done"
