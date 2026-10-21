/*
 * AVX2 compare + blend version of the Group 16 loop. Built with -march=haswell
 * (no AVX-512), so this is what a CPU without mask registers must execute.
 */
#include <immintrin.h>
#include <math.h>

void avx2_blend(const float *restrict A, float *restrict B, int n) {
    const __m256 zero = _mm256_setzero_ps();
    int i = 0;
    for (; i + 8 <= n; i += 8) {
        __m256 a = _mm256_loadu_ps(A + i);
        __m256 m = _mm256_cmp_ps(a, zero, _CMP_GT_OQ);           /* all-ones lanes where A > 0 */
        __m256 s = _mm256_sqrt_ps(a);                            /* every lane (NaN if A < 0)  */
        _mm256_storeu_ps(B + i, _mm256_blendv_ps(zero, s, m));   /* per-lane select            */
    }
    for (; i < n; i++) {                                          /* scalar epilogue            */
        B[i] = (A[i] > 0.0f) ? sqrtf(A[i]) : 0.0f;
    }
}
