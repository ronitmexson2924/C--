#!/usr/bin/env bash
# Reproduces every result in this case study. Run from the repository root or this folder.
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(cd ../.. && pwd)"
OUT=results
BUILD="${TMPDIR:-/tmp}/cmm-simd-build"
mkdir -p "$OUT" "$BUILD"

echo "[1/4] C-- SIMD lab (reference interpreter)"
(cd "$ROOT" && python3 -m cmm run case_studies/simd_masked_vectorization/masked_sqrt.cmm) | tee "$OUT/cmm_output.txt"

echo "[1b] Negative test: drop the k2 tail mask from the load (C-- must trap, not read out of bounds)"
python3 - "$BUILD/unmasked.cmm" <<'PY'
import sys
src = open("masked_sqrt.cmm").read()
masked = """    for (mut l = 0; l < lanes512(); l = l + 1) {
        if (k[l]) {
            v[l] = a[base + l];
        }
    }"""
assert masked in src
open(sys.argv[1], "w").write(src.replace(masked, """    for (mut l = 0; l < lanes512(); l = l + 1) {
        v[l] = a[base + l];   // UNMASKED load: ignores k2
    }"""))
PY
(cd "$ROOT" && python3 -m cmm run "$BUILD/unmasked.cmm" 2>&1 | sed "s|$BUILD/||" | tail -n 13) > "$OUT/unmasked_tail_trap.txt" || true
cat "$OUT/unmasked_tail_trap.txt"

echo "[2/4] What the compiler emits for the original loop"
cat > "$BUILD/kernel.c" <<'C'
#include <math.h>
void kernel(const float *restrict A, float *restrict B, int N) {
    for (int i = 0; i < N; i++) {
        if (A[i] > 0.0f) B[i] = sqrtf(A[i]);
        else B[i] = 0.0f;
    }
}
C
gcc -O2 -S -o "$OUT/asm_scalar_O2.s" "$BUILD/kernel.c"
gcc -O3 -mavx2 -fno-math-errno -S -o "$OUT/asm_avx2_O3.s" "$BUILD/kernel.c"
gcc -O3 -mavx512f -mprefer-vector-width=512 -fno-math-errno -S -o "$OUT/asm_avx512_O3.s" "$BUILD/kernel.c"
{
  for flags in "-O3 -mavx512f -mprefer-vector-width=512" "-O3 -mavx512f -mprefer-vector-width=512 -fno-math-errno"; do
    echo "gcc $flags:"
    gcc $flags -fopt-info-vec-optimized -c "$BUILD/kernel.c" -o "$BUILD/k.o" 2>&1 | sed 's/^/  /' || true
    echo "  packed sqrt instructions: $(objdump -d "$BUILD/k.o" | grep -c vsqrtps || true)"
  done
} | tee "$OUT/vectorizer_report.txt"

echo "[3/4] Build the hardware benchmark"
gcc -O3 -march=haswell -fno-math-errno -c avx2_blend.c -o "$BUILD/avx2_blend.o"
gcc -O3 -march=cascadelake -mprefer-vector-width=512 -fno-math-errno -Wall -Wextra \
    bench_avx512.c "$BUILD/avx2_blend.o" -o "$BUILD/bench" -lm
objdump -d --no-show-raw-insn "$BUILD/bench" > "$BUILD/bench.dis"
for f in scalar_branchy compiler_avx512 avx512_masked avx512_max avx512vl_ymm avx2_blend; do
  echo "<$f>:"
  awk -v f="<$f>:" '$2==f{p=1;next} p&&/^$/{exit} p' "$BUILD/bench.dis" | sed 's/^ *[0-9a-f]*:\t/  /'
done > "$OUT/asm_benchmark_kernels.txt"

echo "[4/4] Run the hardware benchmark"
"$BUILD/bench" | tee "$OUT/bench_output.txt"
