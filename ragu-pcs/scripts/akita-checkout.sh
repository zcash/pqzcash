#!/usr/bin/env bash
# Clone LayerZero-Labs/akita at the revision the study pins and apply the study's patches with
# git am. The clone work/akita-src, on the branch pasta-widths, gets scripts/patches/akita/0001-*:
# the estimator-only Pallas and Goldilocks moduli and the re-pricing that pasta-proof-size.md
# describes. The worktree work/akita-src-150, on the branch pasta-widths-147, gets 0001-* and
# 0002-*, the 147-bit policy; scripts/akita-147-pipeline.sh then regenerates its width tables.
# The worktree work/akita-src-165, on the branch level3-165, gets all three patches: 0003-* is
# the 165-bit policy and the three-map compression chain of the frontier page's illustrative
# level, for planning only, and scripts/akita-165-pipeline.sh regenerates its width tables.
# The lattice estimator that scripts/knapsack-lwe-check.py runs is Akita's third_party submodule,
# initialised in the clone. Paths are relative to the ragu-pcs directory; the checkouts live under
# work/, or under $RAGU_PCS_WORK. A checkout that already exists is left as it is.
#
# Usage: scripts/akita-checkout.sh
# AKITA_URL and LATTICE_ESTIMATOR_URL name other sources to clone from, such as local mirrors.
set -e -u -o pipefail
work="${RAGU_PCS_WORK:-$(cd "$(dirname "$0")/.." && pwd)/work}"
patches="$(cd "$(dirname "$0")/patches/akita" && pwd)"
rev=60b82bc30f4f8f1130ccd71fe10b0b9bed909ab9
url="${AKITA_URL:-https://github.com/LayerZero-Labs/akita}"
estimator_url="${LATTICE_ESTIMATOR_URL:-https://github.com/malb/lattice-estimator.git}"
src="$work/akita-src"
src147="$work/akita-src-150"
src165="$work/akita-src-165"

mkdir -p "$work"
if [ -e "$src" ]; then
    echo "$src exists; left as it is"
else
    git clone --no-checkout "$url" "$src"
    git -C "$src" -c advice.detachedHead=false checkout -q "$rev"
    git -C "$src" checkout -q -b pasta-widths
    git -C "$src" am "$patches"/0001-*.patch
fi
git -C "$src" -c "submodule.third_party/lattice-estimator.url=$estimator_url" \
    submodule update --init third_party/lattice-estimator

if [ -e "$src147" ]; then
    echo "$src147 exists; left as it is"
else
    git -C "$src" worktree add -q -b pasta-widths-147 "$src147" "$rev"
    git -C "$src147" am "$patches"/0001-*.patch "$patches"/0002-*.patch
fi
if [ -e "$src165" ]; then
    echo "$src165 exists; left as it is"
else
    git -C "$src" worktree add -q -b level3-165 "$src165" "$rev"
    git -C "$src165" am "$patches"/0001-*.patch "$patches"/0002-*.patch "$patches"/0003-*.patch
fi
echo "Akita at $rev: $src on pasta-widths, $src147 on pasta-widths-147, $src165 on level3-165."
