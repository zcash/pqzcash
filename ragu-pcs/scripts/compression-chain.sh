#!/usr/bin/env bash
# The security of a chain of compression maps under Akita's own estimator, one map a line:
# the map's input and output in bits, the minimizing block size, and the quantum core-SVP
# bits at 0.265 a block. A map is a Module-SIS instance at coefficient bound 1 whose security
# depends on its output's bits and its input's width, whatever the modulus, so each map is
# given as a scalar instance at the 32-bit modulus: its output's bits over 32 equations, and
# its input's bits as columns. A chain starts from the 8 KiB source, 65,536 bits.
#
# Usage, in a checkout of Akita with the estimator's examples built
# (cargo build --release -p akita-sis-estimator --examples):
#   scripts/compression-chain.sh AKITA_CHECKOUT
# It prints the shipped two-map chain, which the paper's Appendix G gives as 147.34 and
# 153.17 bits, and the chain for the illustrative level. That chain's first two maps are a
# two-map chain to 144 bytes, its first three a three-map chain to the shipped 128 bytes,
# which is the one the level assumes, and all four a chain to 120 bytes, whose last output is
# a multiple of 64 bits and not of 128.
set -euo pipefail
estimator="$1/target/release/examples/sis_estimator_once"

map() {
    # map INPUT_BITS OUTPUT_BITS
    "$estimator" --family q32 --n "$(( $2 / 32 ))" --m "$1" --coeff-linf-bound 1 | tail -n 1 |
        awk -F, -v input="$1" -v output="$2" \
            '{ printf "%s\t%s\t%s\t%.2f\n", input, output, $13, 0.265 * $13 }'
}

chain() {
    # chain LABEL SOURCE_BITS OUTPUT_BITS...
    echo "# $1"
    local input="$2"
    shift 2
    for output in "$@"; do
        map "$input" "$output"
        input="$output"
    done
}

printf 'input_bits\toutput_bits\tblock\tquantum_bits\n'
chain "shipped" 65536 2048 1024
chain "illustrative level: two maps, three, or four" 65536 2304 1152 1024 960
