#!/usr/bin/env bash
# Builds the IEEE paper (paper/C--_IEEE_Paper.pdf).
#   ./paper/build.sh          reuse existing benchmark results if present
#   ./paper/build.sh --bench  re-run the performance benchmark first
# Requires: Python 3.10+, gcc, and TeX Live with IEEEtran (texlive-publishers),
# TikZ (texlive-pictures) and latexmk.
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(cd .. && pwd)"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
mkdir -p generated

# 1. Example program in Listing 1 must produce the output quoted in its comments
expected=$'5.333333333333333\n2'
actual="$(python3 -m cmm run examples/value_semantics.cmm)"
if [[ "$actual" != "$expected" ]]; then
  echo "Listing 1 output changed:"; echo "$actual"; exit 1
fi

# 2. Listing 2 is the real diagnostic printed by the compiler
(cd examples && python3 -m cmm run typo.cmm > /dev/null 2> ../generated/diag_typo.txt) || true
grep -q "did you mean 'maximum_score'" generated/diag_typo.txt

# 3. Performance table
if [[ "${1:-}" == "--bench" || ! -f generated/bench_rows.tex ]]; then
  python3 bench/run_bench.py
fi

# 4. LaTeX
latexmk -pdf -interaction=nonstopmode -halt-on-error -quiet main.tex > /dev/null
cp main.pdf "C--_IEEE_Paper.pdf"
latexmk -c -quiet main.tex > /dev/null 2>&1 || true
echo "wrote paper/C--_IEEE_Paper.pdf"
