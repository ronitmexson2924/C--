"""Test all normative examples from Section 17 per Section 14 and Acceptance Checklist."""

import os
from pathlib import Path
import subprocess
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = REPO_ROOT / "examples"
ERRORS_DIR = EXAMPLES_DIR / "errors"

VALID_EXAMPLES = sorted(list(EXAMPLES_DIR.glob("*.cmm")))
ERROR_EXAMPLES = sorted(list(ERRORS_DIR.glob("*.cmm")))


@pytest.mark.parametrize("cmm_file", VALID_EXAMPLES, ids=lambda p: p.name)
def test_valid_example(cmm_file: Path) -> None:
    """Run valid example program from its directory and verify stdout and exit code 0."""
    out_file = cmm_file.with_suffix(".out")
    assert out_file.exists(), f"Missing expected stdout file: {out_file}"
    expected_stdout = out_file.read_text(encoding="utf-8")

    cmd = [sys.executable, "-m", "cmm", "run", cmm_file.name]
    res = subprocess.run(
        cmd,
        cwd=str(cmm_file.parent),
        capture_output=True,
        text=True,
    )

    assert res.returncode == 0, f"Expected 0, got {res.returncode}. Stderr:\n{res.stderr}"
    assert res.stdout == expected_stdout, f"Stdout mismatch for {cmm_file.name}:\nExpected:\n{repr(expected_stdout)}\nGot:\n{repr(res.stdout)}"
    assert res.stderr == "", f"Expected empty stderr, got:\n{res.stderr}"


@pytest.mark.parametrize("cmm_file", ERROR_EXAMPLES, ids=lambda p: p.name)
def test_error_example(cmm_file: Path) -> None:
    """Run error program from its directory and verify stderr, exit code, and stdout."""
    err_file = cmm_file.with_suffix(".err")
    code_file = cmm_file.with_suffix(".code")
    assert err_file.exists(), f"Missing expected stderr file: {err_file}"
    assert code_file.exists(), f"Missing expected exit code file: {code_file}"

    expected_stderr = err_file.read_text(encoding="utf-8")
    expected_code = int(code_file.read_text(encoding="utf-8").strip())

    extra_args: list[str] = []
    args_file = cmm_file.with_suffix(".args")
    if args_file.exists():
        extra_args = args_file.read_text(encoding="utf-8").strip().split()

    cmd = [sys.executable, "-m", "cmm", "run", *extra_args, cmm_file.name]
    res = subprocess.run(
        cmd,
        cwd=str(cmm_file.parent),
        capture_output=True,
        text=True,
    )

    assert res.returncode == expected_code, (
        f"Exit code mismatch for {cmm_file.name}: expected {expected_code}, got {res.returncode}.\n"
        f"Stderr:\n{res.stderr}"
    )
    assert res.stderr == expected_stderr, (
        f"Stderr mismatch for {cmm_file.name}:\n"
        f"Expected:\n{repr(expected_stderr)}\n"
        f"Got:\n{repr(res.stderr)}"
    )

    out_file = cmm_file.with_suffix(".out")
    if out_file.exists():
        expected_stdout = out_file.read_text(encoding="utf-8")
        assert res.stdout == expected_stdout
    else:
        assert res.stdout == "", f"Expected empty stdout for {cmm_file.name}, got:\n{res.stdout}"


# ============================================================================
# Platform Independence: Identical Output for CRLF and BOM Variants (§13, §18)
# ============================================================================

def test_valid_program_crlf_and_bom_identical(tmp_path: Path) -> None:
    """Verify that a valid program produces byte-identical output with CRLF and BOM."""
    source_path = EXAMPLES_DIR / "operators.cmm"
    expected_stdout = (EXAMPLES_DIR / "operators.out").read_text(encoding="utf-8")
    original_text = source_path.read_text(encoding="utf-8")

    # 1. CRLF line endings
    crlf_file = tmp_path / "operators_crlf.cmm"
    crlf_bytes = original_text.replace("\n", "\r\n").encode("utf-8")
    crlf_file.write_bytes(crlf_bytes)

    res_crlf = subprocess.run(
        [sys.executable, "-m", "cmm", "run", str(crlf_file)],
        capture_output=True,
        text=True,
    )
    assert res_crlf.returncode == 0
    assert res_crlf.stdout == expected_stdout
    assert res_crlf.stderr == ""

    # 2. UTF-8 BOM prefix
    bom_file = tmp_path / "operators_bom.cmm"
    bom_bytes = b"\xef\xbb\xbf" + original_text.encode("utf-8")
    bom_file.write_bytes(bom_bytes)

    res_bom = subprocess.run(
        [sys.executable, "-m", "cmm", "run", str(bom_file)],
        capture_output=True,
        text=True,
    )
    assert res_bom.returncode == 0
    assert res_bom.stdout == expected_stdout
    assert res_bom.stderr == ""

    # 3. Both CRLF and UTF-8 BOM
    both_file = tmp_path / "operators_crlf_bom.cmm"
    both_bytes = b"\xef\xbb\xbf" + original_text.replace("\n", "\r\n").encode("utf-8")
    both_file.write_bytes(both_bytes)

    res_both = subprocess.run(
        [sys.executable, "-m", "cmm", "run", str(both_file)],
        capture_output=True,
        text=True,
    )
    assert res_both.returncode == 0
    assert res_both.stdout == expected_stdout
    assert res_both.stderr == ""


def test_error_program_crlf_and_bom_identical(tmp_path: Path) -> None:
    """Verify that an error program produces identical error positions and messages with CRLF and BOM."""
    source_path = ERRORS_DIR / "syntax_missing_semicolon.cmm"
    expected_stderr = (ERRORS_DIR / "syntax_missing_semicolon.err").read_text(encoding="utf-8")
    original_text = source_path.read_text(encoding="utf-8")

    # Run CRLF variant from within tmp_path with filename matching original
    crlf_file = tmp_path / "syntax_missing_semicolon.cmm"
    crlf_bytes = original_text.replace("\n", "\r\n").encode("utf-8")
    crlf_file.write_bytes(crlf_bytes)

    res_crlf = subprocess.run(
        [sys.executable, "-m", "cmm", "run", crlf_file.name],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )
    assert res_crlf.returncode == 1
    assert res_crlf.stderr == expected_stderr

    # Run BOM variant
    bom_bytes = b"\xef\xbb\xbf" + original_text.encode("utf-8")
    crlf_file.write_bytes(bom_bytes)

    res_bom = subprocess.run(
        [sys.executable, "-m", "cmm", "run", crlf_file.name],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )
    assert res_bom.returncode == 1
    assert res_bom.stderr == expected_stderr
