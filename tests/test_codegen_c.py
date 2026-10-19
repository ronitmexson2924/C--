"""Tests for the C99 backend (cmm/codegen_c.py and 'cmm transpile') per Section 16."""

from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from cmm.ast_nodes import Block, Literal, Program, VarDecl
from cmm.codegen_c import generate_c

CC = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")

if CC is None:
    pytestmark = pytest.mark.skip(reason="No C99 compiler (cc/gcc/clang) found on system")


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Execute a subprocess command capturing output."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )


# ============================================================================
# 1. Normative Examples in examples/*.cmm
# ============================================================================

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
EXAMPLE_FILES = sorted(EXAMPLES_DIR.glob("*.cmm"))


@pytest.mark.parametrize("cmm_path", EXAMPLE_FILES, ids=lambda p: p.name)
def test_codegen_matches_interpreter_on_examples(cmm_path: Path, tmp_path: Path) -> None:
    """Verify that every program in examples/ has identical stdout, stderr, and exit code."""
    # 1. Run interpreter via CLI
    interp_res = run_cmd([sys.executable, "-m", "cmm", "run", str(cmm_path)])

    # 2. Transpile via CLI
    c_file = tmp_path / f"{cmm_path.stem}.c"
    transpile_res = run_cmd([
        sys.executable, "-m", "cmm", "transpile", str(cmm_path), "-o", str(c_file)
    ])
    assert transpile_res.returncode == 0, f"Transpile failed: {transpile_res.stderr}"
    assert c_file.is_file()

    # 3. Compile with standard C99 compiler (-Wall -Werror)
    bin_file = tmp_path / f"{cmm_path.stem}_bin"
    compile_res = run_cmd([
        CC, "-std=c99", "-Wall", "-Werror", str(c_file), "-o", str(bin_file)
    ])
    assert compile_res.returncode == 0, f"C compilation failed:\n{compile_res.stderr}"

    # 4. Run compiled C binary
    bin_res = run_cmd([str(bin_file)])

    # 5. Verify outputs match interpreter exactly
    assert bin_res.returncode == interp_res.returncode
    assert bin_res.stdout == interp_res.stdout
    assert bin_res.stderr == interp_res.stderr

    # Also verify against .out file
    expected_out = cmm_path.with_suffix(".out").read_text(encoding="utf-8")
    assert bin_res.stdout == expected_out


# ============================================================================
# 2. Runtime Error Examples in examples/errors/*.cmm
# ============================================================================

RUNTIME_ERROR_FILES = [
    EXAMPLES_DIR / "errors" / "runtime_overflow.cmm",
    EXAMPLES_DIR / "errors" / "runtime_div_zero.cmm",
    EXAMPLES_DIR / "errors" / "runtime_mod_zero.cmm",
    EXAMPLES_DIR / "errors" / "runtime_float_overflow.cmm",
]


@pytest.mark.parametrize("err_path", RUNTIME_ERROR_FILES, ids=lambda p: p.name)
def test_codegen_matches_interpreter_on_runtime_errors(err_path: Path, tmp_path: Path) -> None:
    """Verify that runtime errors produce identical 3-line stderr and exit code 2."""
    file_name = err_path.name
    cwd = err_path.parent

    interp_res = subprocess.run(
        [sys.executable, "-m", "cmm", "run", file_name],
        cwd=cwd,
        capture_output=True,
        text=True,
    )

    c_file = tmp_path / f"{err_path.stem}.c"
    transpile_res = subprocess.run(
        [sys.executable, "-m", "cmm", "transpile", file_name, "-o", str(c_file)],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    assert transpile_res.returncode == 0
    assert c_file.is_file()

    bin_file = tmp_path / f"{err_path.stem}_bin"
    compile_res = run_cmd([
        CC, "-std=c99", "-Wall", "-Werror", str(c_file), "-o", str(bin_file)
    ])
    assert compile_res.returncode == 0, f"C compilation failed:\n{compile_res.stderr}"

    bin_res = run_cmd([str(bin_file)])

    assert bin_res.returncode == 2
    assert bin_res.returncode == interp_res.returncode
    assert bin_res.stdout == interp_res.stdout
    assert bin_res.stderr == interp_res.stderr

    expected_err = err_path.with_suffix(".err").read_text(encoding="utf-8")
    assert bin_res.stderr == expected_err


# ============================================================================
# 3. Unit Tests: let vs mut constness & string escaping
# ============================================================================

def test_let_variables_declared_const() -> None:
    """Verify that 'let' variables are declared const and 'mut' are not (§16)."""
    ast = Program(
        line=1,
        col=1,
        module_name="main",
        body=Block(
            line=2,
            col=1,
            statements=[
                VarDecl(
                    line=3,
                    col=5,
                    mutable=False,
                    name="a",
                    name_line=3,
                    name_col=9,
                    init=Literal(type="int", value=10, line=3, col=13),
                ),
                VarDecl(
                    line=4,
                    col=5,
                    mutable=True,
                    name="b",
                    name_line=4,
                    name_col=9,
                    init=Literal(type="int", value=20, line=4, col=13),
                ),
            ],
        ),
    )
    c_code = generate_c(ast, "test.cmm", ["module main;", "fn main() {", "    let a = 10;", "    mut b = 20;", "}"])
    assert "const int64_t _v_1_a = 10LL;" in c_code
    assert "int64_t _v_2_b = 20LL;" in c_code
