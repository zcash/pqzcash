#!/usr/bin/env bash
# SIS width tables at a 150-bit ADPS16-quantum floor, using Akita's own
# estimator with the Quantum150BitADPS16 policy added in work/akita-src (see
# WORKING-NOTES.md, "NEXT OVERNIGHT RUN"). Paths are relative to the
# ragu-pcs directory; the clone that it
# builds lives under work/, or under $RAGU_PCS_WORK. The Euclidean tables take seconds to minutes; each coefficient
# L-infinity table takes one to three hours, so the whole run is an overnight
# one. Launch it detached, e.g.
#   nohup scripts/akita-150-tables.sh > work/akita-150-out/nohup.log 2>&1 &
#
# Usage: scripts/akita-150-tables.sh [OUT_DIR]
# Everything is written under OUT_DIR (default work/akita-150-out), one log
# per step plus a summary. A failed step does not stop the later ones.

set -u -o pipefail
work="${RAGU_PCS_WORK:-$(cd "$(dirname "$0")/../work" && pwd)}"  # the external checkouts and outputs

repo="$work/akita-src"
out="${1:-$work/akita-150-out}"
mkdir -p "$out"
summary="$out/summary.txt"
: > "$summary"

export RUSTUP_TOOLCHAIN="${RUSTUP_TOOLCHAIN:-1.96.0}"
policy=Quantum150BitADPS16

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

# 1. Build the estimator's examples, so that no step pays for compilation
#    inside its own timing.
run_step build-estimator cargo build --release -p akita-sis-estimator --features parallel --examples

est=target/release/examples

# 2. Euclidean (L2) width tables at 150 bits for the two shipped moduli and
#    the two comparison moduli, every canonical ring dimension and collision
#    bucket, CSV output.
run_step l2-table-150 "$est/euclidean_width_table" \
    --families q128,q64,pallas,goldilocks --target-bits 150 --format csv \
    --output "$out/l2-width-table-150.csv"

# 3. Coefficient-L-infinity width tables at 150 bits, one modulus per step,
#    shipped moduli first. The local-minimum search with proven-pruned
#    certification, as the README's regen command uses; progress lines go to
#    each log.
for family in q128 q64 pallas goldilocks; do
    run_step "linf-table-150-$family" "$est/infinity_width_table" \
        --policy "$policy" --profiles "$family" --format csv \
        --profile local-minimum --progress-every 25 \
        --output "$out/linf-width-table-150-$family.csv"
done

log "done; outputs in $out"
