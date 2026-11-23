#!/usr/bin/env bash
# Retarget the Akita worktree work/akita-src-150 from a 150-bit floor to 147 bits, the most
# that its rank-one compression maps allow at the catalog's geometry (the d=16 map at width
# 4,096 certifies at 147.34 bits; see WORKING-NOTES.md, 2026-11-12 04:40 UTC), regenerate its
# runtime width tables at that floor, re-size the six compression cells from them, rebuild,
# and run the re-plan. On the worktree that scripts/akita-checkout.sh makes, which is on the
# branch pasta-widths-147 with the 147-bit policy already applied, the script starts at the
# table regeneration. Each step is logged under OUT (default work/akita-147-out) and the
# script stops at the first failure:
#   scripts/akita-147-pipeline.sh
set -u -o pipefail
work="${RAGU_PCS_WORK:-$(cd "$(dirname "$0")/../work" && pwd)}"  # the external checkouts and outputs

here="$work"
repo="$here/akita-src-150"
out="${1:-$here/akita-147-out}"
mkdir -p "$out"
summary="$out/summary.txt"
: > "$summary"
export RUSTUP_TOOLCHAIN="${RUSTUP_TOOLCHAIN:-1.96.0}"
trailer="Co-Authored-By: Claude Mythos 5.1 <noreply@anthropic.com>"

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

# 1. Record the 150-bit state on its branch (every change there is a tracked modification:
#    the policy rename, the regenerated tables, the re-sized cells). Skipped when the
#    worktree is already on the 147-bit branch, so that the script can resume.
if [ "$(git branch --show-current)" = "pasta-widths-150" ]; then
    git diff --name-only > "$out/150-bit-files.txt"
    if [ -s "$out/150-bit-files.txt" ]; then
        xargs git add -- < "$out/150-bit-files.txt"
        git commit -q -F - <<EOF
The 150-bit policy, its runtime tables and compression cells

The single policy is the ADPS16-quantum gate at 150 bits, with the width tables regenerated at that floor and the six rank-one compression cells re-sized from them. At this floor the compression chain does not fit: the first map at ring dimension 16 has width 4,096 and the cell allows 3,806.

$trailer
EOF
        log "committed the 150-bit state as $(git rev-parse --short HEAD)"
    fi

    # 2. Retarget to 147 bits on a new branch: the policy's name everywhere (the generated
    #    tables' modules name it too, and must build before they are regenerated), its floor,
    #    the Euclidean target, and the comments that state the floor.
    git checkout -q -b pasta-widths-147 || exit 2
    grep -rl "Quantum150BitADPS16" crates --include=*.rs | xargs gsed -i 's/Quantum150BitADPS16/Quantum147BitADPS16/g'
    files=$(grep -rl "150-bit\|150 bits\|= 150.0" crates --include=*.rs | grep -v "generated_sis_table\|generated_l2_sis_table")
    # shellcheck disable=SC2086
    gsed -i -e 's/minimum_log2_rop: 150\.0/minimum_log2_rop: 147.0/' \
            -e 's/DEFAULT_EUCLIDEAN_TARGET_BITS: f64 = 150\.0/DEFAULT_EUCLIDEAN_TARGET_BITS: f64 = 147.0/' \
            -e 's/150-bit/147-bit/g' -e 's/at 150 bits/at 147 bits/g' $files
    grep -rn "150" crates --include=*.rs | grep -v "generated_sis_table\|generated_l2_sis_table" | grep -i "150\.\|150Bit\|150 bit\|150-bit\|= 150\b" > "$out/leftover-150.txt" || true
    log "retargeted; leftover mentions of 150: $(wc -l < "$out/leftover-150.txt" | tr -d ' ') (see leftover-150.txt)"
elif [ "$(git branch --show-current)" = "pasta-widths-147" ]; then
    log "resuming on pasta-widths-147"
else
    log "unexpected branch $(git branch --show-current)"; exit 2
fi

# 3. Rebuild the estimator's emitters and regenerate the runtime tables at 147 bits. The
#    emitters write into the akita-params crate; the certified infinity table takes about an
#    hour.
if [ "${SKIP_TABLES:-0}" = 1 ]; then
    log "tables kept from the previous run (SKIP_TABLES=1)"
else
    step build-estimator cargo build --release -p akita-sis-estimator --examples
    step l2-rust-split target/release/examples/euclidean_width_table --format rust-split
    step linf-rust-split target/release/examples/infinity_width_table --format rust-split --policy Quantum147BitADPS16
fi

# 4. Re-size the six compression cells from the regenerated tables: the rank-one, bound-1
#    entry of each (profile, d) cell is the first element of the "(d, 1) =>" row.
python - "$out" <<'EOF' || { log "FAIL  compression cells"; exit 1; }
import re, sys, pathlib
out = pathlib.Path(sys.argv[1])
cells = [("Q128OffsetA7F7", "q128", 8), ("Q128OffsetA7F7", "q128", 16), ("Q64Offset59", "q64", 16),
         ("Q64Offset59", "q64", 32), ("Q32Offset99", "q32", 32), ("Q32Offset99", "q32", 64)]
src = pathlib.Path("crates/akita-params/src/sis/compression.rs")
text = src.read_text()
report = []
for profile, table, d in cells:
    rows = pathlib.Path(f"crates/akita-params/src/sis/generated_sis_table/{table}.rs").read_text()
    m = re.search(rf"\({d}, 1\) => Some\(&\[(\d+),", rows)
    if not m:
        sys.exit(f"no rank-one bound-1 row for {table} d={d}")
    width = int(m.group(1))
    pat = rf"^(\s+\(SisModulusProfileId::{profile}, {d}, )[\d_]+\),$"  # the table's lines only, not the tests' calls
    new, n = re.subn(pat, lambda mm: f"{mm.group(1)}{width:_}),", text, flags=re.M)
    if n != 1:
        sys.exit(f"cell ({profile}, {d}) not found once in compression.rs: {n}")
    text = new
    report.append(f"{table} d={d}: {width}")
src.write_text(text)
(out / "compression-cells.txt").write_text("\n".join(report) + "\n")
print("\n".join(report))
EOF
log "compression cells: $(tr '\n' ';' < "$out/compression-cells.txt")"

# 5. Rebuild the planner and commit the 147-bit state.
step build-planner cargo build --release -p akita-planner --features catalog-security --examples --bin gen_schedule_artifacts
git diff --name-only > "$out/147-bit-files.txt"
xargs git add -- < "$out/147-bit-files.txt"
git commit -q -F - <<EOF
The 147-bit policy, its runtime tables and compression cells

The floor is 147 bits, the most the rank-one compression maps allow at the catalog's geometry: the first map at ring dimension 16 and width 4,096 certifies at 147.34 bits. The width tables are regenerated at that floor and the six compression cells re-sized from them.

$trailer
EOF
log "committed the 147-bit state as $(git rev-parse --short HEAD)"

# 6. The re-plan, as scripts/akita-150-replan.sh but without --catalog-report, which needs a
#    catalog baseline, and into this run's output directory.
gsed -e 's/--catalog-report "[^"]*" //' -e "s#akita-150-out/replan#akita-147-out/replan#" "$here/akita-150-replan.sh" > "$here/akita-147-replan.sh"
chmod +x "$here/akita-147-replan.sh"
log "start replan (its own summary is in $out/replan/summary.txt)"
"$here/akita-147-replan.sh" "$out/replan" > "$out/replan.log" 2>&1
log "replan finished with exit $? ; done"
