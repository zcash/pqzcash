#!/usr/bin/env bash
# Re-plan Akita's catalog at the 150-bit ADPS16-quantum floor, using the
# worktree work/akita-src-150, whose single security policy is the 150-bit one
# (renamed from the shipped 128-bit policy, with its runtime width tables
# regenerated at 150 bits and its six rank-one compression cells re-sized from
# those tables; see WORKING-NOTES.md). Paths are relative to the ragu-pcs
# directory; the worktree lives under work/, or under $RAGU_PCS_WORK.
#
# Usage: scripts/akita-150-replan.sh [OUT_DIR]
# Everything is written under OUT_DIR (default work/akita-147-out/replan), one
# log per step plus a summary. A failed step does not stop the later ones. The
# steps mirror scripts/akita-pasta-estimates.sh and the per-K group runs behind
# the Pareto page, so that the 150-bit figures are produced the same way as
# the 128-bit ones:
#   replan-base    every fp128 family at Akita's own pricing;
#   replan-pallas  the same at Pasta widths (255:255:1);
#   replan-q64     the same with 64-bit commitment coordinates (255:255:1:64);
#   groups-k<K>    fp128_dense with a 2^14 final group and K separately
#                  committed 2^14 groups, at the 64-bit commitment pricing;
#   reprice-*      catalog_reprice over each output, which prices every row at
#                  all five width profiles (original, pallas, goldilocks,
#                  pallas_sis, pallas_q64).

set -u -o pipefail
work="${RAGU_PCS_WORK:-$(cd "$(dirname "$0")/../work" && pwd)}"  # the external checkouts and outputs

repo="$work/akita-src-150"
out="${1:-$work/akita-147-out/replan}"
mkdir -p "$out"
summary="$out/summary.txt"
: > "$summary"

export RUSTUP_TOOLCHAIN="${RUSTUP_TOOLCHAIN:-1.96.0}"

log() { printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$summary"; }

run_step() {
    # run_step NAME COMMAND...
    local name="$1"; shift
    local logfile="$out/$name.log"
    local start end
    local status
    start=$(date +%s)
    log "start $name"
    if "$@" > "$logfile" 2>&1; then
        status=0
    else
        status=$?
    fi
    end=$(date +%s)
    if [ "$status" -eq 0 ]; then
        log "ok    $name ($((end - start)) s)"
    else
        log "FAIL  $name ($((end - start)) s), exit $status, see $logfile"
    fi
}

cd "$repo" || exit 2

# 0. The binaries must have been built after the 150-bit tables were
#    regenerated (work/akita-147-out/replan/tables-rust-split.log); this is a
#    no-op rebuild that fails loudly if they were not.
run_step build-planner cargo build --release -p akita-planner --features catalog-security --examples --bin gen_schedule_artifacts

gen=target/release/gen_schedule_artifacts
est=target/release/examples
fp128_families=$(ls artifacts/schedules | grep '^fp128_' | gsed 's/\.aks$//' | tr '\n' ' ')
fp64_families=$(ls artifacts/schedules | grep '^fp64_' | gsed 's/\.aks$//' | tr '\n' ' ')

# 1. Every fp128 family at three pricings, each with the planner's own report.
#    The base run also covers the fp64 (Goldilocks-geometry) families, whose
#    fp64_dense row is the page's Goldilocks figure.
mkdir -p "$out/replan-base" "$out/replan-pallas" "$out/replan-q64"
run_step replan-base "$gen" "$out/replan-base" \
    --catalog-snapshot "$out/replan-base-catalog.tsv" $fp128_families $fp64_families
AKITA_PRICING_WIDTHS=255:255:1 \
run_step replan-pallas "$gen" "$out/replan-pallas" \
    --catalog-snapshot "$out/replan-pallas-catalog.tsv" $fp128_families
AKITA_PRICING_WIDTHS=255:255:1:64 \
run_step replan-q64 "$gen" "$out/replan-q64" \
    --catalog-snapshot "$out/replan-q64-catalog.tsv" $fp128_families
for step in base pallas q64; do
    run_step "reprice-replan-$step" "$est/catalog_reprice" --artifacts "$out/replan-$step"
    cp -f "$out/reprice-replan-$step.log" "$out/reprice-replan-$step.tsv" 2>/dev/null || true
done

# 2. The per-K group runs: one 2^14 final group plus K separately committed
#    2^14 groups, fp128_dense, at the 64-bit commitment pricing.
mkdir -p "$out/groups"
for k in 1 2 4 8 12; do
    pre=""
    for _ in $(seq "$k"); do pre="$pre --precommitted-group fp128_dense:14:1"; done
    mkdir -p "$out/groups/q64-k$k"
    AKITA_PRICING_WIDTHS=255:255:1:64 \
    run_step "groups-k$k" "$gen" "$out/groups/q64-k$k" fp128_dense \
        --final-group fp128_dense:14:1 $pre
    run_step "reprice-groups-k$k" "$est/catalog_reprice" --artifacts "$out/groups/q64-k$k"
    cp -f "$out/reprice-groups-k$k.log" "$out/reprice-groups-k$k.tsv" 2>/dev/null || true
done

# 3. The same sweep in Goldilocks geometry (fp64_dense, Akita's own pricing),
#    so that the page's Goldilocks variant is planned rather than scaled.
for k in 1 2 4 8 12; do
    pre=""
    for _ in $(seq "$k"); do pre="$pre --precommitted-group fp64_dense:14:1"; done
    mkdir -p "$out/groups/fp64-k$k"
    run_step "groups-fp64-k$k" "$gen" "$out/groups/fp64-k$k" fp64_dense \
        --final-group fp64_dense:14:1 $pre
    run_step "reprice-groups-fp64-k$k" "$est/catalog_reprice" --artifacts "$out/groups/fp64-k$k"
    cp -f "$out/reprice-groups-fp64-k$k.log" "$out/reprice-groups-fp64-k$k.tsv" 2>/dev/null || true
done

log "done; outputs in $out"
