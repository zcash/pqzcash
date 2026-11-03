#!/usr/bin/env bash
# Build the book, generating the pages derived from the studies first.
#
# The PCS frontier page is a self-contained HTML file that ragu-pcs/pareto-model.py writes
# beside itself. It is generated here rather than committed, since each regeneration would add
# ten megabytes to the history. mdbook copies files other than Markdown from src/ into the
# output unchanged, so the generated page is served beside the chapter that embeds it.
#
# Run from anywhere; the book lands in book/book. `PYTHON` overrides the interpreter.
set -euo pipefail
cd "$(dirname "$0")/.."

# The model prints its summary line first, then every point; only the summary is shown.
"${PYTHON:-python3}" ragu-pcs/pareto-model.py | sed -n 1p
cp ragu-pcs/pareto.html book/src/proof-systems/pareto.html

# Run from within book/ so the todo preprocessor's relative command path resolves.
cd book && mdbook build
