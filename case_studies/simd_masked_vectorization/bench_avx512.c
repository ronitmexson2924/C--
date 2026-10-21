/*
 * Group 16 case study: hardware experiment for
 *
 *     for (i = 0; i < N; i++) B[i] = (A[i] > 0.0f) ? sqrtf(A[i]) : 0.0f;
 *
 * Five implementations are timed on the same data:
 *   scalar_branchy   compiled without vectorization: CMP + conditional jump
 *   compiler_avx512  the plain C loop, auto-vectorized by the compiler (masked vsqrtps)
 *   avx512_masked    intrinsics: vcmpps -> k1, vsqrtps{k1}{z}, k2 tail mask (no scalar epilogue)
 *   avx512_max       intrinsics: sqrt(max(A, 0)), "algebraic predication", k2 tail mask
 *   avx512vl_ymm     the masked algorithm at 256-bit width (AVX-512VL: k1 masks on ymm)
 *   avx2_blend       intrinsics compiled for AVX2 only: vcmpps + vsqrtps + vblendvps, scalar epilogue
 *
 * Build:  see run.sh (avx2_blend.c is compiled separately with -march=haswell)
 * Hardware counters (instructions, branch misses, cycles) are read with
 * perf_event_open when the kernel allows it; otherwise only time is reported.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <immintrin.h>
#include <linux/perf_event.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>
#include <x86intrin.h>

#define N 65537          /* 4096 full zmm vectors + a 1-lane tail; A and B fit in L2 */
#define REPS 21          /* runs per kernel per trial; the best run counts (run 0 is a warm-up) */
#define TRIALS 15        /* kernels are interleaved within each trial; medians are reported */
#define MAXK 8

typedef void (*kernel_fn)(const float *restrict, float *restrict, int);

/* ------------------------------------------------------------------ kernels */

__attribute__((noinline, optimize("no-tree-vectorize", "no-tree-loop-vectorize", "no-tree-slp-vectorize")))
void scalar_branchy(const float *restrict A, float *restrict B, int n) {
    for (int i = 0; i < n; i++) {
        if (A[i] > 0.0f) {
            B[i] = sqrtf(A[i]);
        } else {
            B[i] = 0.0f;
        }
    }
}

__attribute__((noinline))
void compiler_avx512(const float *restrict A, float *restrict B, int n) {
    for (int i = 0; i < n; i++) {
        if (A[i] > 0.0f) {
            B[i] = sqrtf(A[i]);
        } else {
            B[i] = 0.0f;
        }
    }
}

__attribute__((noinline))
void avx512_masked(const float *restrict A, float *restrict B, int n) {
    const __m512 zero = _mm512_setzero_ps();
    int i = 0;
    for (; i + 16 <= n; i += 16) {
        __m512 a = _mm512_loadu_ps(A + i);
        __mmask16 k1 = _mm512_cmp_ps_mask(a, zero, _CMP_GT_OQ); /* k1 = A > 0          */
        __m512 r = _mm512_maskz_sqrt_ps(k1, a);                 /* sqrt where k1, else 0 */
        _mm512_storeu_ps(B + i, r);
    }
    if (i < n) {                                                /* tail: k2 = low (n-i) bits */
        __mmask16 k2 = (__mmask16)((1u << (n - i)) - 1u);
        __m512 a = _mm512_maskz_loadu_ps(k2, A + i);            /* no out-of-bounds read  */
        __mmask16 k1 = _mm512_mask_cmp_ps_mask(k2, a, zero, _CMP_GT_OQ);
        _mm512_mask_storeu_ps(B + i, k2, _mm512_maskz_sqrt_ps(k1, a));
    }
}

__attribute__((noinline))
void avx512_max(const float *restrict A, float *restrict B, int n) {
    const __m512 zero = _mm512_setzero_ps();
    int i = 0;
    for (; i + 16 <= n; i += 16) {
        /* MAXPS returns the 2nd operand for NaN and for +-0, so max(A, +0) maps
           NaN, -0.0 and negatives to +0.0: exactly the else-branch. */
        _mm512_storeu_ps(B + i, _mm512_sqrt_ps(_mm512_max_ps(_mm512_loadu_ps(A + i), zero)));
    }
    if (i < n) {
        __mmask16 k2 = (__mmask16)((1u << (n - i)) - 1u);
        __m512 a = _mm512_maskz_loadu_ps(k2, A + i);
        _mm512_mask_storeu_ps(B + i, k2, _mm512_sqrt_ps(_mm512_max_ps(a, zero)));
    }
}

__attribute__((noinline))
void avx512vl_ymm(const float *restrict A, float *restrict B, int n) {
    const __m256 zero = _mm256_setzero_ps();
    int i = 0;
    for (; i + 8 <= n; i += 8) {
        __m256 a = _mm256_loadu_ps(A + i);
        __mmask8 k1 = _mm256_cmp_ps_mask(a, zero, _CMP_GT_OQ);
        _mm256_storeu_ps(B + i, _mm256_maskz_sqrt_ps(k1, a));
    }
    if (i < n) {
        __mmask8 k2 = (__mmask8)((1u << (n - i)) - 1u);
        __m256 a = _mm256_maskz_loadu_ps(k2, A + i);
        __mmask8 k1 = _mm256_mask_cmp_ps_mask(k2, a, zero, _CMP_GT_OQ);
        _mm256_mask_storeu_ps(B + i, k2, _mm256_maskz_sqrt_ps(k1, a));
    }
}

/* avx2_blend lives in avx2_blend.c, compiled with -march=haswell so the compiler
   cannot turn the blend into AVX-512 masking. */
void avx2_blend(const float *restrict A, float *restrict B, int n);

/* ------------------------------------------------------------------ hardware counters */

static int perf_open(uint64_t config) {
    struct perf_event_attr attr;
    memset(&attr, 0, sizeof attr);
    attr.size = sizeof attr;
    attr.type = PERF_TYPE_HARDWARE;
    attr.config = config;
    attr.disabled = 1;
    attr.exclude_kernel = 1;
    attr.exclude_hv = 1;
    return (int)syscall(SYS_perf_event_open, &attr, 0, -1, -1, 0);
}

static int fd_instr = -1, fd_bmiss = -1, fd_cycles = -1, fd_branches = -1;

static void counters_init(void) {
    fd_instr = perf_open(PERF_COUNT_HW_INSTRUCTIONS);
    fd_bmiss = perf_open(PERF_COUNT_HW_BRANCH_MISSES);
    fd_cycles = perf_open(PERF_COUNT_HW_CPU_CYCLES);
    fd_branches = perf_open(PERF_COUNT_HW_BRANCH_INSTRUCTIONS);
}

static void counter_start(int fd) {
    if (fd >= 0) { ioctl(fd, PERF_EVENT_IOC_RESET, 0); ioctl(fd, PERF_EVENT_IOC_ENABLE, 0); }
}

static long long counter_stop(int fd) {
    long long v = -1;
    if (fd >= 0) {
        ioctl(fd, PERF_EVENT_IOC_DISABLE, 0);
        if (read(fd, &v, sizeof v) != sizeof v) v = -1;
    }
    return v;
}

/* ------------------------------------------------------------------ data */

static uint32_t rng = 2024u;
static uint32_t next_rand(void) { rng = rng * 1664525u + 1013904223u; return rng; }
static float frand(void) { return (next_rand() >> 8) * (1.0f / 16777216.0f); }

static void make_data(float *A, int n, int pattern) {
    rng = 2024u + (uint32_t)pattern;
    for (int i = 0; i < n; i++) {
        float mag = 0.01f + frand() * 100.0f;
        int positive;
        switch (pattern) {
            case 0:  positive = frand() < 0.5f; break;   /* random 50/50   */
            case 1:  positive = frand() < 0.9f; break;   /* 90% positive   */
            case 2:  positive = 1; break;                 /* all positive   */
            case 3:  positive = (i & 1) == 0; break;      /* alternating    */
            default: positive = i >= n / 2; break;        /* sorted: - then + */
        }
        A[i] = positive ? mag : -mag;
    }
}

static const char *pattern_name[] = {
    "random sign (50%)", "90% positive", "all positive", "alternating sign", "sorted (neg then pos)"
};

struct result { double tsc_per_elem; double instr_per_elem; double bmiss_per_elem; double cyc_per_elem; double br_per_elem; };

static struct result measure_once(kernel_fn f, const float *A, float *B) {
    struct result best = { 1e30, -1, -1, -1, -1 };
    for (int r = 0; r < REPS; r++) {
        counter_start(fd_instr); counter_start(fd_bmiss); counter_start(fd_cycles); counter_start(fd_branches);
        uint64_t t0 = __rdtsc();
        f(A, B, N);
        uint64_t t1 = __rdtsc();
        long long ins = counter_stop(fd_instr), bm = counter_stop(fd_bmiss);
        long long cy = counter_stop(fd_cycles), br = counter_stop(fd_branches);
        double tsc = (double)(t1 - t0) / N;
        if (r > 0 && tsc < best.tsc_per_elem) {   /* run 0 is a warm-up */
            best.tsc_per_elem = tsc;
            best.instr_per_elem = ins >= 0 ? (double)ins / N : -1;
            best.bmiss_per_elem = bm >= 0 ? (double)bm / N : -1;
            best.cyc_per_elem = cy >= 0 ? (double)cy / N : -1;
            best.br_per_elem = br >= 0 ? (double)br / N : -1;
        }
    }
    return best;
}

static double median(double *v, int n) {
    for (int i = 1; i < n; i++)                       /* insertion sort, n is tiny */
        for (int j = i; j > 0 && v[j - 1] > v[j]; j--) { double t = v[j]; v[j] = v[j - 1]; v[j - 1] = t; }
    return v[n / 2];
}

/* ------------------------------------------------------------------ correctness */

static int bitwise_equal(const float *x, const float *y, int n) {
    return memcmp(x, y, (size_t)n * sizeof(float)) == 0;
}

static int check_special_values(kernel_fn f) {
    /* IEEE corner cases where a naive rewrite would differ from the branch */
    float in[19] = { 0.0f, -0.0f, NAN, -NAN, INFINITY, -INFINITY, 1e-45f, -1e-45f, 4.0f, -4.0f,
                     2.0f, 1e38f, -1e38f, 0.25f, 9.0f, 16.0f, -2.0f, 1.0f, 100.0f };
    float ref[19], out[19];
    scalar_branchy(in, ref, 19);
    memset(out, 0x7f, sizeof out);
    f(in, out, 19);
    return bitwise_equal(ref, out, 19);
}

/* ------------------------------------------------------------------ frequency experiment */
/* Heavy 512-bit FP instructions make Skylake-SP / Cascade Lake cores drop to a lower
   frequency "license" and stay there for a short while afterwards. Time the 256-bit
   masked kernel (a) on a core that has only run scalar code and (b) run by run
   immediately after a burst of 512-bit vsqrtps. TSC ticks at a constant rate, so a
   lower core clock shows up as more TSC ticks for the same work. */
static double run_tsc(kernel_fn f, const float *A, float *B) {
    uint64_t t0 = __rdtsc();
    f(A, B, N);
    return (double)(__rdtsc() - t0) / N;
}

static void busy_scalar(double ms, const float *A, float *B) {
    uint64_t end = __rdtsc() + (uint64_t)(ms * 2.8e6);
    while (__rdtsc() < end) scalar_branchy(A, B, 4096);
}

static void frequency_experiment(const float *A, float *B) {
    printf("\nFrequency-license experiment (256-bit masked kernel, TSC ticks/elem):\n");
    busy_scalar(50.0, A, B);
    double cold = 1e30;
    for (int r = 0; r < 20; r++) { double t = run_tsc(avx512vl_ymm, A, B); if (t < cold) cold = t; }
    printf("  after 50 ms of scalar code only:      %.3f\n", cold);
    uint64_t end = __rdtsc() + (uint64_t)(30.0 * 2.8e6);
    while (__rdtsc() < end) avx512_masked(A, B, N);          /* 30 ms of 512-bit vsqrtps */
    uint64_t start = __rdtsc();
    printf("  right after 30 ms of 512-bit vsqrtps (time since burst -> ticks/elem):\n");
    double bucket_sum = 0; int bucket_n = 0; double next_report = 0.25;
    while (1) {
        double t = run_tsc(avx512vl_ymm, A, B);
        double ms = (double)(__rdtsc() - start) / 2.8e6;
        bucket_sum += t; bucket_n++;
        if (ms >= next_report) {
            printf("    %5.2f ms  %.3f\n", next_report, bucket_sum / bucket_n);
            bucket_sum = 0; bucket_n = 0;
            next_report += next_report < 2.0 ? 0.25 : 1.0;
            if (next_report > 6.0) break;
        }
    }
}

int main(void) {
    struct { const char *name; kernel_fn fn; } kernels[] = {
        { "scalar_branchy ", scalar_branchy },
        { "compiler_avx512", compiler_avx512 },
        { "avx512_masked  ", avx512_masked },
        { "avx512_max     ", avx512_max },
        { "avx512vl_ymm   ", avx512vl_ymm },
        { "avx2_blend     ", avx2_blend },
    };
    const int nk = (int)(sizeof kernels / sizeof kernels[0]);

    if (!__builtin_cpu_supports("avx512f")) {
        fprintf(stderr, "This CPU does not support AVX-512F.\n");
        return 1;
    }
    counters_init();
    int have_counters = fd_instr >= 0 && fd_bmiss >= 0;

    float *A = aligned_alloc(64, sizeof(float) * (N + 15));
    float *B = aligned_alloc(64, sizeof(float) * (N + 15));
    float *R = aligned_alloc(64, sizeof(float) * (N + 15));

    printf("N = %d floats (%d zmm vectors + %d tail lane); median of %d interleaved trials, each the best of %d runs\n",
           N, N / 16, N % 16, TRIALS, REPS - 1);
    printf("Hardware counters: %s\n\n", have_counters ? "available (perf_event_open)" : "unavailable in this environment (TSC timing only)");

    printf("Correctness on IEEE corner cases (0, -0, NaN, +-inf, denormals):\n");
    for (int k = 1; k < nk; k++) {
        printf("  %s %s\n", kernels[k].name, check_special_values(kernels[k].fn) ? "bit-identical to scalar" : "MISMATCH");
    }

    for (int p = 0; p < 5; p++) {
        make_data(A, N, p);
        scalar_branchy(A, R, N);
        printf("\nDataset: %s\n", pattern_name[p]);
        /* Interleave kernels inside every trial so a slow period on a shared VM
           affects all kernels alike; report medians of time and of per-trial speedup. */
        struct result last[MAXK];
        double tsc[MAXK][TRIALS], speedup[MAXK][TRIALS];
        int correct[MAXK];
        for (int k = 0; k < nk; k++) {
            memset(B, 0, sizeof(float) * N);
            kernels[k].fn(A, B, N);
            correct[k] = bitwise_equal(B, R, N);
        }
        for (int t = 0; t < TRIALS; t++) {
            for (int k = 0; k < nk; k++) {
                last[k] = measure_once(kernels[k].fn, A, B);
                tsc[k][t] = last[k].tsc_per_elem;
            }
            for (int k = 0; k < nk; k++) speedup[k][t] = tsc[0][t] / tsc[k][t];
        }
        if (have_counters) {
            printf("  %-15s %10s %10s %12s %12s %12s %8s %s\n", "kernel", "TSC/elem", "cyc/elem", "instr/elem",
                   "branch/elem", "bmiss/elem", "speedup", "result");
        } else {
            printf("  %-15s %10s %8s %s\n", "kernel", "TSC/elem", "speedup", "result");
        }
        for (int k = 0; k < nk; k++) {
            double med_tsc = median(tsc[k], TRIALS), med_speedup = median(speedup[k], TRIALS);
            const char *ok = correct[k] ? "ok" : "MISMATCH";
            if (have_counters) {
                printf("  %-15s %10.3f %10.3f %12.3f %12.4f %12.4f %7.2fx %s\n", kernels[k].name, med_tsc,
                       last[k].cyc_per_elem, last[k].instr_per_elem, last[k].br_per_elem, last[k].bmiss_per_elem,
                       med_speedup, ok);
            } else {
                printf("  %-15s %10.3f %7.2fx %s\n", kernels[k].name, med_tsc, med_speedup, ok);
            }
        }
    }
    make_data(A, N, 0);
    frequency_experiment(A, B);
    free(A); free(B); free(R);
    return 0;
}
