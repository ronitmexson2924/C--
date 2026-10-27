#!/usr/bin/env python3
"""
Performance evaluation for the C-- paper.

Experiment 1 (moderate N): C-- reference interpreter vs. the same program
transpiled to C99 and compiled with gcc -O2. Outputs must match exactly.

Experiment 2 (large N): transpiled C99 (checked arithmetic) vs. hand-written,
unchecked C (baseline.c), both gcc -O2, to measure the cost of the checks.

Writes ../generated/bench_table.tex and ../generated/bench_results.json.
Usage: python3 paper/bench/run_bench.py
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
GENERATED = HERE.parent / "generated"

BENCHMARKS = [
    # name, label, N for experiment 1, N for experiment 2
    ("fib", "Recursive Fibonacci", 22, 35),
    ("primes", "Prime counting (trial division)", 20_000, 2_000_000),
    ("collatz", "Collatz step totals", 3_000, 1_000_000),
    ("leibniz", "Leibniz series for $\\pi$ (float)", 200_000, 200_000_000),
]
CC = os.environ.get("CC", "gcc")
CFLAGS = ["-std=c99", "-O2"]


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONPATH=str(REPO))
    return subprocess.run(cmd, capture_output=True, text=True, check=True, env=env, **kw)


def best_time(cmd: list[str], repeats: int) -> tuple[float, str]:
    best, out = float("inf"), ""
    for _ in range(repeats):
        start = time.perf_counter()
        out = run(cmd).stdout
        best = min(best, time.perf_counter() - start)
    return best, out.strip()


def same_value(a: str, b: str) -> bool:
    try:
        return int(a) == int(b)
    except ValueError:
        return abs(float(a) - float(b)) <= 1e-12 * max(1.0, abs(float(b)))


def build(tmp: Path, name: str, n: int) -> tuple[Path, Path]:
    src = (HERE / f"{name}.cmm").read_text().replace("@N@", str(n))
    cmm = tmp / f"{name}_{n}.cmm"
    cmm.write_text(src)
    c_out = tmp / f"{name}_{n}.c"
    run([sys.executable, "-m", "cmm", "transpile", str(cmm), "-o", str(c_out)])
    exe = tmp / f"{name}_{n}_checked"
    run([CC, *CFLAGS, str(c_out), "-o", str(exe), "-lm"])
    return cmm, exe


def build_baseline(tmp: Path, name: str, n: int) -> Path:
    exe = tmp / f"{name}_{n}_plain"
    run([CC, *CFLAGS, f"-DBENCH_{name.upper()}", f"-DN={n}", str(HERE / "baseline.c"), "-o", str(exe)])
    return exe


def main() -> None:
    GENERATED.mkdir(exist_ok=True)
    results = []
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        for name, label, n1, n2 in BENCHMARKS:
            cmm, exe1 = build(tmp, name, n1)
            t_interp, out_interp = best_time([sys.executable, "-m", "cmm", "run", str(cmm)], 3)
            t_c99, out_c99 = best_time([str(exe1)], 5)
            _, exe2 = build(tmp, name, n2)
            plain = build_baseline(tmp, name, n2)
            t_checked, out_checked = best_time([str(exe2)], 5)
            t_plain, out_plain = best_time([str(plain)], 5)
            row = {
                "name": name, "label": label, "n_small": n1, "n_large": n2,
                "interpreter_s": t_interp, "c99_small_s": t_c99,
                "outputs_match_small": out_interp == out_c99,
                "c99_checked_s": t_checked, "c_plain_s": t_plain,
                "outputs_match_large": same_value(out_checked, out_plain),
                "output_small": out_interp,
            }
            results.append(row)
            print(f"{name:8s} interp {t_interp:8.3f}s  c99 {t_c99 * 1e3:8.2f}ms  match={row['outputs_match_small']}  "
                  f"| checked {t_checked:7.3f}s  plain {t_plain:7.3f}s  match={row['outputs_match_large']}")

    cc_version = run([CC, "--version"]).stdout.splitlines()[0]
    meta = {"python": platform.python_version(), "cc": cc_version, "machine": platform.machine(),
            "cpu": next((l.split(":", 1)[1].strip() for l in Path("/proc/cpuinfo").read_text().splitlines()
                         if l.startswith("model name")), platform.processor()) if Path("/proc/cpuinfo").exists() else platform.processor()}
    (GENERATED / "bench_results.json").write_text(json.dumps({"meta": meta, "results": results}, indent=2))

    def fmt_n(n: int) -> str:
        return f"{n:,}".replace(",", "\\,")

    lines = []
    for r in results:
        speedup = r["interpreter_s"] / r["c99_small_s"]
        overhead = (r["c99_checked_s"] / r["c_plain_s"] - 1.0) * 100.0
        lines.append(
            f"{r['label']} & {fmt_n(r['n_small'])} & {r['interpreter_s']:.2f} & {r['c99_small_s'] * 1e3:.1f} & "
            f"{speedup:.0f}$\\times$ & {fmt_n(r['n_large'])} & {r['c99_checked_s']:.3f} & {r['c_plain_s']:.3f} & "
            f"{overhead:+.0f}\\%\\\\")
    (GENERATED / "bench_rows.tex").write_text("\n".join(lines) + "\n")
    all_match = all(r["outputs_match_small"] and r["outputs_match_large"] for r in results)
    speedups = [r["interpreter_s"] / r["c99_small_s"] for r in results]
    overheads = [(r["c99_checked_s"] / r["c_plain_s"] - 1.0) * 100.0 for r in results]
    (GENERATED / "bench_meta.tex").write_text(
        f"\\newcommand{{\\benchSpeedupMin}}{{{min(speedups):.0f}}}\n"
        f"\\newcommand{{\\benchSpeedupMax}}{{{max(speedups):.0f}}}\n"
        f"\\newcommand{{\\benchOverheadMin}}{{{min(overheads):.0f}}}\n"
        f"\\newcommand{{\\benchOverheadMax}}{{{max(overheads):.0f}}}\n"
        f"\\newcommand{{\\benchCPU}}{{{meta['cpu'].replace('(R)', '').replace('  ', ' ')}}}\n"
        f"\\newcommand{{\\benchCC}}{{{cc_version.split(')')[-1].strip() if ')' in cc_version else cc_version}}}\n"
        f"\\newcommand{{\\benchPython}}{{{meta['python']}}}\n"
        f"\\newcommand{{\\benchAllMatch}}{{{'all outputs matched' if all_match else 'SOME OUTPUTS DIFFERED'}}}\n")
    print("wrote", GENERATED.relative_to(REPO))


if __name__ == "__main__":
    main()
