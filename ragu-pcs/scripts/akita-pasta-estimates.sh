#!/usr/bin/env bash
# SIS width tables and proof-size re-pricing for the Pallas base field and
# Goldilocks, using Akita's own estimator and planner code with the additions
# in work/akita-src (see pasta-proof-size.md). Paths are relative to the
# ragu-pcs directory; the clone that it
# builds lives under work/, or under $RAGU_PCS_WORK. The whole run takes a few hours, most of it in step 4.
#
# Usage: scripts/akita-pasta-estimates.sh [OUT_DIR]
# Everything is written under OUT_DIR (default work/akita-pasta-out), one
# log per step plus a summary. Steps run in order of increasing cost, and a
# failed step does not stop the later ones.

set -u -o pipefail
work="${RAGU_PCS_WORK:-$(cd "$(dirname "$0")/../work" && pwd)}"  # the external checkouts and outputs

repo="$work/akita-src"
out="${1:-$work/akita-pasta-out}"
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

# 1. Build everything that the later steps call, so that no step pays for
#    compilation inside its own timing.
run_step build-estimator cargo build --release -p akita-sis-estimator --features parallel --examples
run_step build-planner   cargo build --release -p akita-planner --features catalog-security --examples --bin gen_schedule_artifacts

est=target/release/examples

# 2. Fast checks: Euclidean rank ladder at every modulus, and the re-pricing
#    of every shipped schedule at Pallas and Goldilocks widths.
run_step pasta-rank      "$est/pasta_rank" 128 4194304 20 22 24 27 32 36 41.6 44 48
cp -f "$out/pasta-rank.log" "$out/pasta-rank.csv" 2>/dev/null || true

run_step catalog-reprice "$est/catalog_reprice"
cp -f "$out/catalog-reprice.log" "$out/catalog-reprice.tsv" 2>/dev/null || true

# 2b. Re-plan every fp128 family with the planner's byte objective priced at
#     Pasta widths (AKITA_PRICING_WIDTHS=base:challenge:claim_ext_degree), and
#     once more without the override as a reproduction baseline. About five
#     seconds per schedule row. The catalog snapshots carry proof_bytes at the
#     pricing used for selection; the re-pricing example then prices both
#     outputs at both widths for a side-by-side comparison.
fp128_families=$(ls artifacts/schedules | grep '^fp128_' | gsed 's/\.aks$//' | tr '\n' ' ')
mkdir -p "$out/replan-pallas" "$out/replan-base"
AKITA_PRICING_WIDTHS=255:255:1 \
run_step replan-pallas target/release/gen_schedule_artifacts "$out/replan-pallas" \
    --catalog-snapshot "$out/replan-pallas-catalog.tsv" $fp128_families
run_step replan-base target/release/gen_schedule_artifacts "$out/replan-base" \
    --catalog-snapshot "$out/replan-base-catalog.tsv" $fp128_families
# 2c. Re-plan with the commitment modulus decoupled from the claim field:
#     partials and sum-check messages at 255 bits, commitment coordinates at
#     64 bits (the fourth component of AKITA_PRICING_WIDTHS).
mkdir -p "$out/replan-q64"
AKITA_PRICING_WIDTHS=255:255:1:64 \
run_step replan-q64 target/release/gen_schedule_artifacts "$out/replan-q64" \
    --catalog-snapshot "$out/replan-q64-catalog.tsv" $fp128_families
run_step reprice-replan-q64 "$est/catalog_reprice" --artifacts "$out/replan-q64"
cp -f "$out/reprice-replan-q64.log" "$out/reprice-replan-q64.tsv" 2>/dev/null || true
run_step reprice-replan-pallas "$est/catalog_reprice" --artifacts "$out/replan-pallas"
cp -f "$out/reprice-replan-pallas.log" "$out/reprice-replan-pallas.tsv" 2>/dev/null || true
run_step reprice-replan-base "$est/catalog_reprice" --artifacts "$out/replan-base"
cp -f "$out/reprice-replan-base.log" "$out/reprice-replan-base.tsv" 2>/dev/null || true

# 3. Full Euclidean (L2) width tables for the two new moduli, every canonical
#    ring dimension and collision bucket, CSV output. Seconds to minutes.
run_step l2-table-pallas-goldilocks "$est/euclidean_width_table" \
    --families pallas,goldilocks --format csv \
    --output "$out/l2-width-table-pallas-goldilocks.csv"

# 4. Full coefficient-L-infinity width tables for the two new moduli over the
#    canonical role cells, CSV output. This is the long step: the local
#    minimum search with proven-pruned certification, as the README's regen
#    command uses. Progress lines go to the log.
run_step linf-table-pallas "$est/infinity_width_table" \
    --profiles pallas --format csv --profile local-minimum --progress-every 25 \
    --output "$out/linf-width-table-pallas.csv"
run_step linf-table-goldilocks "$est/infinity_width_table" \
    --profiles goldilocks --format csv --profile local-minimum --progress-every 25 \
    --output "$out/linf-width-table-goldilocks.csv"

# 5. The shipped catalog's own SIS report, for a same-estimator baseline.
run_step catalog-security "$est/catalog_security" --check
cp -f "$out/catalog-security.log" "$out/catalog-security.tsv" 2>/dev/null || true

log "done; outputs in $out"
