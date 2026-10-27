/*
 * Hand-written, unchecked C baselines for the four benchmarks. Compiled once per
 * benchmark with -DBENCH_<NAME> -DN=<size>; used to measure the cost of the
 * checked arithmetic that the C-- transpiler emits.
 */
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

#if defined(BENCH_FIB)
static int64_t fib(int64_t n) { return n < 2 ? n : fib(n - 1) + fib(n - 2); }
int main(void) { printf("%lld\n", (long long)fib(N)); return 0; }

#elif defined(BENCH_PRIMES)
static bool is_prime(int64_t n) {
    if (n < 2) return false;
    for (int64_t d = 2; d * d <= n; d++) if (n % d == 0) return false;
    return true;
}
int main(void) {
    int64_t count = 0;
    for (int64_t i = 2; i <= N; i++) if (is_prime(i)) count++;
    printf("%lld\n", (long long)count);
    return 0;
}

#elif defined(BENCH_COLLATZ)
int main(void) {
    int64_t total = 0;
    for (int64_t n = 1; n <= N; n++) {
        int64_t x = n;
        while (x != 1) { x = (x % 2 == 0) ? x / 2 : 3 * x + 1; total++; }
    }
    printf("%lld\n", (long long)total);
    return 0;
}

#elif defined(BENCH_LEIBNIZ)
int main(void) {
    double sum = 0.0, sign = 1.0;
    for (int64_t k = 0; k < N; k++) { sum += sign / (2.0 * (double)k + 1.0); sign = -sign; }
    printf("%.17g\n", 4.0 * sum);
    return 0;
}
#endif
