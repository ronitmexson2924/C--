# Case Study — Group 16: AVX-512 SIMD Vectorization with Conditional Control Flow

**Kernel under study**

```c
for (int i = 0; i < N; i++) {
    if (A[i] > 0.0f) {
        B[i] = sqrtf(A[i]);
    } else {
        B[i] = 0.0f;
    }
}
```

**Questions**

1. Why do traditional branches (CMP + JMP) break SIMD pipelining and prevent vectorization?
2. How does the compiler use masked vector operations (AVX-512 `k1`–`k7`, or blend instructions) to vectorize the loop without branches?
3. What are the instruction-count and performance effects of eliminating branch mispredictions through vector predication?

---

## 1. Approach: a three-part experiment

Most answers to this problem stop at drawing the masked assembly. This study instead **proves every claim** three
independent ways and checks that they agree:

| Part | Tool | What it shows |
|---|---|---|
| **A. C-- SIMD lab** | [`masked_sqrt.cmm`](masked_sqrt.cmm), written in our own language **C--** | A safe software model of `zmm` registers and `k` masks. Runs the loop four ways, proves they agree lane by lane, simulates two branch predictors, and counts instructions and cycles. |
| **B. Compiler evidence** | GCC 13 output for the original loop ([`results/asm_*.s`](results/)) | What a real compiler emits for scalar, AVX2, and AVX-512, and *when* it refuses to vectorize. |
| **C. Hardware measurement** | [`bench_avx512.c`](bench_avx512.c) on an Intel Xeon (Cascade Lake, AVX-512F/DQ/BW/VL/VNNI, 2.8 GHz) | Real timings of six implementations on five data distributions, IEEE corner-case checks, and a frequency experiment. |

**Why C--?** C-- has no pointers, no inline assembly and checked array indexing, so a vector register *must* be
modelled as a value (`array<float>(16)`) and a mask as `array<bool>(16)`. That makes the lane semantics
explicit and testable. It also turns one of AVX-512's key features into something you can see: if the tail mask
`k2` is removed from the load, C-- stops the program with `R006 index out of range (index 100, length 100)`
([`results/unmasked_tail_trap.txt`](results/unmasked_tail_trap.txt)), where C would silently read past the array.

Reproduce everything with:

```bash
./case_studies/simd_masked_vectorization/run.sh
```

---

## 2. Question 1 — Why CMP + JMP breaks SIMD

This is the hot loop GCC emits at `-O2` ([`results/asm_scalar_O2.s`](results/asm_scalar_O2.s)):

```asm
.L5:  movss   (%rdi,%rax), %xmm0     ; load A[i]
      comiss  %xmm1, %xmm0           ; CMP  A[i] with 0.0
      jbe     .L11                   ; JMP  if A[i] <= 0   <-- data-dependent branch
      sqrtss  %xmm0, %xmm0           ; then-path
      movss   %xmm0, (%rsi,%rax)
      addq    $4, %rax
      cmpq    %rax, %rcx
      jne     .L5
.L11: pxor    %xmm0, %xmm0           ; else-path: B[i] = 0
      movss   %xmm0, (%rsi,%rax)
      ...
```

The branch is a problem for three separate reasons:

1. **One program counter, many lanes.** A SIMD instruction applies one operation to 16 lanes at once, but a
   jump moves the *single* instruction pointer. When lanes disagree (some `A[i] > 0`, some not), no jump target
   is right for all of them. The branch is *divergent*, so the loop body cannot be issued as one vector stream.
   To vectorize, the compiler first has to remove the control flow (**if-conversion**) and turn the branch into
   data: a per-lane predicate.
2. **The branch serializes the pipeline.** The CPU must guess the outcome of `jbe` before `comiss` has
   finished. With random signs the guess is wrong about half the time, and every wrong guess flushes the
   speculatively fetched and executed instructions and restarts the front end. We measured about **19–23 TSC
   ticks per mispredicted element** on this CPU (Section 4.3), several times the cost of the useful work.
3. **Hidden side effects block if-conversion.** Even after removing the branch, the compiler must compute
   `sqrtf` on lanes that the program never asked for. That is only legal if doing so has no visible effect.
   `sqrtf` of a negative number sets `errno` (C99 Annex F / POSIX), so GCC **refuses to vectorize at all** until
   `-fno-math-errno` is given ([`results/vectorizer_report.txt`](results/vectorizer_report.txt)):

   | Command | Result |
   |---|---|
   | `gcc -O3 -mavx512f -mprefer-vector-width=512` | 0 packed sqrt instructions, scalar loop |
   | `gcc -O3 -mavx512f -mprefer-vector-width=512 -fno-math-errno` | `loop vectorized using 64 byte vectors` |

   Out-of-range memory accesses in the final partial vector, and floating-point exception flags, are the other
   two side effects that predication has to suppress.

---

## 3. Question 2 — Masked vector operations

### 3.1 What the compiler emits

With `-O3 -mavx512f -mprefer-vector-width=512 -fno-math-errno`, GCC 13 if-converts the loop and predicates it
with an AVX-512 mask register ([`results/asm_avx512_O3.s`](results/asm_avx512_O3.s)):

```asm
.L4:  vcmpps   $1, (%rdi,%rax), %zmm1, %k1     ; k1[l] = (0.0 < A[i+l])      for 16 lanes
      vsqrtps  (%rdi,%rax), %zmm0{%k1}{z}      ; sqrt where k1 = 1, 0.0 where k1 = 0
      vmovups  %zmm0, (%rcx,%rax)              ; store 16 results
      addq     $64, %rax
      cmpq     %rax, %rsi
      jne      .L4                              ; the only branch: loop-back, always predictable
```

- **`vcmpps … %k1`**: the `if` condition is evaluated for all 16 lanes and written as 16 bits into mask
  register `k1`. The `CMP` survives as data; the `JMP` is gone.
- **`{%k1}`**: the sqrt only takes effect in lanes whose mask bit is 1. Masked-off lanes raise **no
  floating-point exceptions**: AVX-512 suppresses faults on inactive lanes.
- **`{z}` (zero-masking)**: inactive lanes are written as **0.0**. That *is* the `else` branch, executed by the
  same instruction for free. (Merge-masking, `{%k1}` without `{z}`, would instead keep the old register value.)
- Both branches collapse into **one** instruction stream; the loads fold into the memory operands of `vcmpps`
  and `vsqrtps`.

The hand-written intrinsics version ([`bench_avx512.c`](bench_avx512.c), `avx512_masked`) is the same idea, plus
a **second mask `k2` for the tail**, so no scalar clean-up loop is needed:

```c
__m512    a  = _mm512_loadu_ps(A + i);
__mmask16 k1 = _mm512_cmp_ps_mask(a, _mm512_setzero_ps(), _CMP_GT_OQ);  // k1 = A > 0
_mm512_storeu_ps(B + i, _mm512_maskz_sqrt_ps(k1, a));                    // sqrt or 0

// last partial vector: k2 = lanes that exist
__mmask16 k2 = (1u << (n - i)) - 1u;
a  = _mm512_maskz_loadu_ps(k2, A + i);                 // never reads past the array
k1 = _mm512_mask_cmp_ps_mask(k2, a, zero, _CMP_GT_OQ); // k1 = k2 AND (A > 0)
_mm512_mask_storeu_ps(B + i, k2, _mm512_maskz_sqrt_ps(k1, a));
```

### 3.2 The same masks, traced lane by lane in C--

The C-- lab executes these instructions as pure functions (`vcmp_gt_zero`, `vsqrt_maskz`, `vload_maskz`,
`vstore_mask`). For N = 100 the last vector starts at index 96 and has 4 valid lanes
([`results/cmm_output.txt`](results/cmm_output.txt)):

| Lane | A[i] | k2 (lane exists) | k1 = k2 ∧ (A > 0) | B[i] = zmm2 |
|---:|---:|:---:|:---:|---:|
| 0 | −61.17 | 1 | 0 | 0.0 |
| 1 | 58.69 | 1 | 1 | 7.6606 |
| 2 | −5.34 | 1 | 0 | 0.0 |
| 3 | −17.71 | 1 | 0 | 0.0 |
| 4–15 | — | 0 | 0 | not stored |

As integers (`kmovw`): `k2 = 15` (0b1111), `k1 = 2` (0b0010). The program checks that the masked result equals
the scalar branch for every element of every dataset.

### 3.3 Without mask registers: compare + blend (AVX2)

Before AVX-512 there are no `k` registers. The predicate is a vector of all-ones / all-zeros lanes, sqrt runs on
**every** lane (negative lanes produce NaN and set the invalid flag), and a blend picks the result. GCC emits
([`results/asm_avx2_O3.s`](results/asm_avx2_O3.s)):

```asm
.L4:  vsqrtps   (%rdi,%rax), %ymm1            ; sqrt of all 8 lanes, including negatives -> NaN
      vcmpltps  (%rdi,%rax), %ymm2, %ymm0     ; ymm0 = all-ones where 0 < A
      vandps    %ymm1, %ymm0, %ymm0           ; blend: keep sqrt where all-ones, else 0.0
      vmovups   %ymm0, (%rcx,%rax)
      ...
```

Because the `else` value is 0.0, a bitwise `vandps` is a cheaper blend than `vblendvps`. Without masks the
remainder (`N mod 8` elements) needs a separate scalar loop, which still contains the branch.

### 3.4 Algebraic predication: removing the condition entirely

This kernel has a property worth exploiting: `sqrt(0) = 0`. So the whole `if` equals

```
B[i] = sqrt(max(A[i], +0.0))
```

`vmaxps` returns its *second* operand when either input is NaN or both are zero, so `max(A, +0.0)` maps negatives,
`−0.0`, and NaN to `+0.0`: exactly the else branch, bit for bit (verified on 0, −0, ±NaN, ±∞, and denormals).
The condition disappears into arithmetic. No compare and no mask are needed, except `k2` for the tail
(`avx512_max` in the benchmark, `avx512_max` in the C-- lab).

---

## 4. Question 3 — Instruction count and performance

### 4.1 Instruction count (dynamic, per element)

Counted from the real hot loops ([`results/asm_benchmark_kernels.txt`](results/asm_benchmark_kernels.txt)):

| Implementation | Instructions / iteration | Elements / iteration | **Instructions / element** | Branches / element | Data-dependent branches / element |
|---|---:|---:|---:|---:|---:|
| Scalar, `if` + `jbe` (gcc -O2) | 8 (both paths) | 1 | **8.0** | 2.0 | **1.0** |
| AVX2 compare + blend (gcc -O3) | 7 | 8 | 0.875 | 0.125 | 0 |
| AVX2 blend, hand-written | 9 | 8 | 1.125 | 0.125 | 0 (+ scalar tail) |
| **AVX-512 masked, gcc -O3** | **6** | **16** | **0.375** | **0.0625** | **0** |
| AVX-512 masked, intrinsics | 7 | 16 | 0.4375 | 0.0625 | 0 |

- Masking cuts the dynamic instruction count by **~18–21×** (8.0 → 0.375–0.44 per element).
- Branches drop **32×** (2.0 → 0.0625 per element), and the only one left is the loop-back branch, which
  mispredicts once, at loop exit.
- **Data-dependent branches drop from one per element to zero.** The program's speed no longer depends on the
  data.

The C-- lab reaches the same conclusion for N = 100 (7 vectors, 4-lane tail): **800 → 46 instructions** and
**200 → 7 branches**.

### 4.2 Measured performance

N = 65 537 floats (4 096 full `zmm` vectors + 1 tail lane; A and B fit in L2). Times are TSC ticks per element
(the TSC runs at a constant 2.8 GHz). "Typical" is the stable value seen across more than ten runs; the range
includes runs disturbed by other tenants on this shared VM. All results are bit-identical to the scalar loop.

| Dataset | Scalar with branch: typical (range) | AVX-512 masked (`zmm`) | AVX2 blend (`ymm`) | Speedup, AVX-512 masked |
|---|---:|---:|---:|---:|
| Random sign (50%) | **13.7** (13.7–16.5) | **0.725** | 0.618 | **≈ 19×** |
| 90% positive | 4.4 (4.4–6.6) | 0.725 | 0.618 | ≈ 6× |
| Alternating sign | 2.3 (2.3–4.0) | 0.725 | 0.618 | ≈ 3.2× |
| Sorted (negatives, then positives) | 2.47 (2.47–4.7) | 0.725 | 0.618 | ≈ 3.4× |
| All positive | 2.47 | 0.725 | 0.618 | ≈ 3.4× |

The **compiler-generated** AVX-512 loop (`compiler_avx512`) and the **max-predicated** version (`avx512_max`)
run at the same 0.725 as the intrinsics: all three are limited by the same unit (Section 4.4).

### 4.3 What the branch mispredictions cost

- The scalar loop's time varies by up to **~6×** (2.3 → 13.7 ticks) with nothing but the *signs* of the data. Every vector version takes
  the same time on every dataset.
- **Mispredict penalty.** With random signs about half of the branches mispredict, since no predictor can learn
  random data. The *alternating* dataset does the same work (half the elements need a sqrt) but is perfectly
  predictable, so (13.7 − 2.3) / 0.5 ≈ **23 TSC ticks per mispredict**. The 90% dataset gives ≈ 19 ticks. That
  is about 7–8 ns, or roughly 20 core cycles, the figure the C-- model uses.
- **83%** of the scalar loop's time on random data is mispredict recovery ((13.7 − 2.3) / 13.7).
- **Prediction quality matters.** The C-- lab compares two predictors on the same 100 elements:

  | Dataset | 2-bit counter mispredicts | Two-level history predictor | Hardware |
  |---|---:|---:|---|
  | Random | 52 | 53 | unpredictable (13.7 ticks/elem) |
  | 90% positive | 10 | 10 | ~10% misses (4.4) |
  | Alternating | **50** | **4** | learned (2.3) |
  | All positive | 2 | 2 | no misses (2.47) |

  A textbook 2-bit counter fails on the alternating pattern; a history-based predictor (the kind real CPUs
  use) learns it, and the hardware confirms that. Only genuinely unpredictable data exposes the full penalty.
  Vector predication removes the penalty **in every case**, including the worst one.

### 4.4 What limits the vector code, and a surprise

Once branches are gone, the bottleneck is the **square-root unit**, not instructions. Using Agner Fog's
reciprocal-throughput figures for Skylake-SP / Cascade Lake, each measurement implies a core clock, and they are
consistent:

| Kernel | Sqrt throughput | Measured | Implied core clock |
|---|---|---:|---:|
| scalar `sqrtss` | 3 cycles / element | 2.471 ticks/elem | 3.4 GHz |
| 256-bit `vsqrtps ymm` | 6 cycles / 8 lanes | 0.618 ticks/elem | 3.4 GHz |
| 512-bit `vsqrtps zmm` | 12 cycles / 16 lanes | 0.725 ticks/elem | **2.9 GHz** |

On this microarchitecture a 512-bit sqrt has the same per-element throughput as a 256-bit one (0.75
cycles/element), so 512-bit vectors cannot be faster here, **and** they lower the clock. Heavy 512-bit FP
instructions move the core to a lower frequency "license". We captured this directly
(`frequency_experiment` in the benchmark):

| Identical 256-bit masked kernel | TSC ticks / element |
|---|---:|
| After 50 ms of scalar code | **0.619** |
| 0.25–1.0 ms after a 30 ms burst of 512-bit `vsqrtps` | **0.725–0.84** |
| ≈ 1.25–1.5 ms after the burst | back to ≈ 0.62–0.65 |

(Later samples fluctuate with VM noise.) Running the *same masked algorithm* at 256-bit width with AVX-512VL
(`avx512vl_ymm`) matches AVX2 when it runs on a cool core, which shows the difference comes from the clock, not
from masking. This is consistent with GCC defaulting to `-mprefer-vector-width=256` for `-march=cascadelake`.

### 4.5 C-- model compared with the hardware

| Dataset | C-- model, cycles/element (N = 100) | Hardware, TSC ticks/element |
|---|---:|---:|
| Random, scalar | 12.8 | 13.7 |
| 90% positive, scalar | 4.9 | 4.4 |
| Alternating, scalar | 3.0 | 2.3 |
| All positive, scalar | 3.6 | 2.47 |
| AVX-512 masked, any data | 1.04 (0.75 as N → ∞) | 0.725 |

A small cost model (issue width, sqrt throughput, branch predictor, mispredict penalty) written in C-- reproduces the
ordering and the magnitude of every result. The remaining gap comes from the small N (fixed loop overhead) and
from ignoring out-of-order overlap.

---

## 5. Conclusions

1. **Branches are the obstacle, not the condition.** A `CMP + JMP` gives every lane the same control flow and
   makes throughput depend on the predictor. Turning the condition into a **per-lane predicate** keeps the
   computation but removes the control flow.
2. **AVX-512 masks make predication complete.** `vcmpps → k1`, then `vsqrtps{k1}{z}`, executes both branches
   in one instruction: zero-masking supplies the `else`, masked lanes raise no exceptions, and a tail mask `k2`
   replaces the scalar epilogue without touching memory past the array.
3. **The payoff:** about **18–21× fewer instructions**, **32× fewer branches**, **zero data-dependent
   mispredictions**, and **3.4–19× measured speedups**, with run time independent of the data.
4. **Choose the vector width per CPU.** On Cascade Lake the sqrt unit, not the instruction count, is the limit,
   and 512-bit instructions lower the clock, so **AVX-512VL masking at 256 bits** is the fastest choice. On
   CPUs without that frequency penalty (e.g. Ice Lake and later, Zen 4), 512-bit masking is expected to win.
5. **Look for algebraic predication.** When the `else` value is the function's value at a boundary (here
   `sqrt(0) = 0`), `sqrt(max(A, 0))` removes the condition altogether.
6. **Compiler flags decide legality.** Without `-fno-math-errno`, `errno` semantics stop GCC from vectorizing at
   all.

---

## 6. Files

| File | Purpose |
|---|---|
| [`masked_sqrt.cmm`](masked_sqrt.cmm) | C-- SIMD lab: register/mask models, four kernels, verification, branch predictors, cost model |
| [`bench_avx512.c`](bench_avx512.c) | Hardware benchmark: scalar, compiler AVX-512, masked and max intrinsics, AVX-512VL 256-bit; frequency experiment |
| [`avx2_blend.c`](avx2_blend.c) | AVX2-only compare + blend kernel (built with `-march=haswell` so the compiler cannot substitute masks) |
| [`run.sh`](run.sh) | Rebuilds and reruns everything and regenerates `results/` |
| `results/cmm_output.txt` | Output of the C-- lab |
| `results/unmasked_tail_trap.txt` | C-- run with the tail mask removed: stopped by `R006` |
| `results/vectorizer_report.txt` | GCC vectorizer decisions with and without `-fno-math-errno` |
| `results/asm_scalar_O2.s`, `asm_avx2_O3.s`, `asm_avx512_O3.s` | Compiler output for the original loop |
| `results/asm_benchmark_kernels.txt` | Disassembly of every benchmarked kernel |
| `results/bench_output.txt` | One complete benchmark run |

**Environment:** Intel Xeon @ 2.80 GHz (Cascade Lake: AVX-512F/DQ/CD/BW/VL/VNNI), 4 vCPUs, GCC 13.3, Ubuntu
24.04, Python 3.13. Hardware performance counters are not exposed in this VM, so instruction and branch counts
come from disassembly and timings from the TSC.

**Notes on the model.** C-- floats are 64-bit; the 16-lane width models float32 in a 512-bit register.
Square roots in the C-- lab use Newton–Raphson iteration (C-- has no built-in sqrt), so the program checks
`B² ≈ A` rather than comparing with a library result. The C99 backend of C-- does not support arrays yet, so the
lab runs on the reference interpreter (`python3 -m cmm run …`, about 0.5 s).
