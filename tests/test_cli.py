"""Tests for C-- command-line interface (CLI) per Section 11 and Section 14."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


def run_cmm(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Helper to run the CLI via subprocess as required by Section 14."""
    cmd = [sys.executable, "-m", "cmm", *args]
    run_env = os.environ.copy()
    if env is not None:
        run_env.update(env)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=run_env,
    )


# ============================================================================
# 1. Version & Help Flags (§11.1)
# ============================================================================

def test_version_flag() -> None:
    res = run_cmm("--version")
    assert res.returncode == 0
    assert res.stdout == "cmm 0.1.0\n"
    assert res.stderr == ""


def test_help_flag_long() -> None:
    res = run_cmm("--help")
    assert res.returncode == 0
    assert "usage:" in res.stdout
    assert "run" in res.stdout
    assert res.stderr == ""


def test_help_flag_short() -> None:
    res = run_cmm("-h")
    assert res.returncode == 0
    assert "usage:" in res.stdout
    assert res.stderr == ""


def test_subcommand_help() -> None:
    res = run_cmm("run", "--help")
    assert res.returncode == 0
    assert "usage: cmm run" in res.stdout
    assert res.stderr == ""


# ============================================================================
# 2. Basic Commands: run, check, tokens, ast (§11.1, §11.6)
# ============================================================================

def test_run_success(tmp_path: Path) -> None:
    prog = tmp_path / "hello.cmm"
    prog.write_text('module main;\nfn main() {\n    print("Hello, C--!");\n}\n', encoding="utf-8")
    res = run_cmm("run", str(prog))
    assert res.returncode == 0
    assert res.stdout == "Hello, C--!\n"
    assert res.stderr == ""


def test_check_success(tmp_path: Path) -> None:
    prog = tmp_path / "check_ok.cmm"
    prog.write_text("module main;\nfn main() {\n    let x = 42;\n}\n", encoding="utf-8")
    res = run_cmm("check", str(prog))
    assert res.returncode == 0
    assert res.stdout == f"{prog}: OK\n"
    assert res.stderr == ""


def test_tokens_command(tmp_path: Path) -> None:
    prog = tmp_path / "tokens_test.cmm"
    prog.write_text("module mymod;\nfn main() {}\n", encoding="utf-8")
    res = run_cmm("tokens", str(prog))
    assert res.returncode == 0
    assert "1:1\tMODULE\tmodule\n" in res.stdout
    assert "1:8\tIDENT\tmymod\n" in res.stdout
    assert "1:13\tSEMI\t;\n" in res.stdout
    assert "2:1\tFN\tfn\n" in res.stdout
    assert "2:4\tMAIN\tmain\n" in res.stdout
    assert "EOF" in res.stdout
    assert res.stderr == ""


def test_ast_command(tmp_path: Path) -> None:
    prog = tmp_path / "ast_test.cmm"
    prog.write_text('module main;\nfn main() {\n    let x = 1 + 2;\n}\n', encoding="utf-8")
    res = run_cmm("ast", str(prog))
    assert res.returncode == 0
    assert 'Program(module="main")\n' in res.stdout
    assert '  body: Block\n' in res.stdout
    assert '    stmt: VarDecl(mutable=false, name="x")\n' in res.stdout
    assert '      init: BinaryOp(op="+")\n' in res.stdout
    assert '        left: Literal(type=int, value=1)\n' in res.stdout
    assert '        right: Literal(type=int, value=2)\n' in res.stdout
    assert res.stderr == ""


# ============================================================================
# 3. Exit Code 1: Lexical, Syntax, and Semantic Errors (§11.2)
# ============================================================================

def test_exit_code_1_lex_error(tmp_path: Path) -> None:
    prog = tmp_path / "lex_err.cmm"
    prog.write_text("module main;\nfn main() {\n    let x = @;\n}\n", encoding="utf-8")
    res = run_cmm("run", str(prog))
    assert res.returncode == 1
    assert "lexical error: unexpected character '@'" in res.stderr
    assert f"{prog}:3:13:" in res.stderr


def test_exit_code_1_syntax_error(tmp_path: Path) -> None:
    prog = tmp_path / "syn_err.cmm"
    prog.write_text("module main;\nfn main() {\n    let x = 1\n}\n", encoding="utf-8")
    res = run_cmm("run", str(prog))
    assert res.returncode == 1
    assert "syntax error:" in res.stderr
    assert "expected ';'" in res.stderr
    assert f"{prog}:4:1:" in res.stderr


def test_exit_code_1_semantic_error(tmp_path: Path) -> None:
    prog = tmp_path / "sem_err.cmm"
    prog.write_text("module main;\nfn main() {\n    let x = y + 1;\n}\n", encoding="utf-8")
    res = run_cmm("run", str(prog))
    assert res.returncode == 1
    assert "semantic error: undeclared variable 'y'" in res.stderr
    assert f"{prog}:3:13:" in res.stderr


def test_check_fails_with_exit_code_1(tmp_path: Path) -> None:
    prog = tmp_path / "check_fail.cmm"
    prog.write_text("module main;\nfn main() {\n    let a = true + 1;\n}\n", encoding="utf-8")
    res = run_cmm("check", str(prog))
    assert res.returncode == 1
    assert "semantic error:" in res.stderr
    assert res.stdout == ""


# ============================================================================
# 4. Exit Code 2: Runtime Errors (§11.2, §10.6)
# ============================================================================

def test_exit_code_2_runtime_division_by_zero(tmp_path: Path) -> None:
    prog = tmp_path / "div_zero.cmm"
    prog.write_text("module main;\nfn main() {\n    let x = 10 / 0;\n}\n", encoding="utf-8")
    res = run_cmm("run", str(prog))
    assert res.returncode == 2
    assert "runtime error: division by zero" in res.stderr
    assert f"{prog}:3:16:" in res.stderr


def test_exit_code_2_runtime_integer_overflow(tmp_path: Path) -> None:
    prog = tmp_path / "overflow.cmm"
    prog.write_text("module main;\nfn main() {\n    let big = 9223372036854775807;\n    let res = big + 1;\n}\n", encoding="utf-8")
    res = run_cmm("run", str(prog))
    assert res.returncode == 2
    assert "runtime error: integer overflow" in res.stderr


def test_stdout_flushed_before_runtime_error(tmp_path: Path) -> None:
    prog = tmp_path / "flush_test.cmm"
    prog.write_text('module main;\nfn main() {\n    print("before error");\n    let x = 5 / 0;\n}\n', encoding="utf-8")
    res = run_cmm("run", str(prog))
    assert res.returncode == 2
    assert res.stdout == "before error\n"
    assert "runtime error: division by zero" in res.stderr


# ============================================================================
# 5. Exit Code 3: I/O Errors (§11.2, §11.4)
# ============================================================================

def test_exit_code_3_io_file_not_found() -> None:
    res = run_cmm("run", "non_existent_file_12345.cmm")
    assert res.returncode == 3
    assert res.stderr == "cmm: error: cannot read 'non_existent_file_12345.cmm': file not found\n"
    assert res.stdout == ""


def test_exit_code_3_io_is_a_directory(tmp_path: Path) -> None:
    sub_dir = tmp_path / "some_dir"
    sub_dir.mkdir()
    res = run_cmm("run", str(sub_dir))
    assert res.returncode == 3
    assert f"cmm: error: cannot read '{sub_dir}': is a directory\n" in res.stderr


def test_exit_code_3_io_not_valid_utf8(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad_utf8.cmm"
    # Write invalid UTF-8 bytes (e.g. isolated 0xFF 0xFE)
    bad_file.write_bytes(b"\xff\xfe\x00\x00\x61\x62\x63")
    res = run_cmm("run", str(bad_file))
    assert res.returncode == 3
    assert f"cmm: error: cannot read '{bad_file}': not valid UTF-8\n" in res.stderr


# ============================================================================
# 6. Exit Code 4: Usage Errors (§11.2, §11.5)
# ============================================================================

def test_exit_code_4_usage_no_args() -> None:
    res = run_cmm()
    assert res.returncode == 4
    assert "usage:" in res.stderr
    assert "cmm: error: a command is required\n" in res.stderr


def test_exit_code_4_usage_unknown_command() -> None:
    res = run_cmm("foobar")
    assert res.returncode == 4
    assert "usage:" in res.stderr
    assert "cmm: error:" in res.stderr
    assert "foobar" in res.stderr


def test_exit_code_4_usage_missing_file_run() -> None:
    res = run_cmm("run")
    assert res.returncode == 4
    assert "usage: cmm run" in res.stderr
    assert "cmm: error:" in res.stderr
    assert "file" in res.stderr


def test_exit_code_4_usage_missing_file_check() -> None:
    res = run_cmm("check")
    assert res.returncode == 4
    assert "usage: cmm check" in res.stderr
    assert "cmm: error:" in res.stderr


def test_exit_code_4_bad_max_steps_negative(tmp_path: Path) -> None:
    prog = tmp_path / "test.cmm"
    prog.write_text("module main;\nfn main() {}\n", encoding="utf-8")
    res = run_cmm("run", str(prog), "--max-steps", "-5")
    assert res.returncode == 4
    assert "cmm: error: --max-steps must be a positive integer\n" in res.stderr


def test_exit_code_4_bad_max_steps_zero(tmp_path: Path) -> None:
    prog = tmp_path / "test.cmm"
    prog.write_text("module main;\nfn main() {}\n", encoding="utf-8")
    res = run_cmm("run", str(prog), "--max-steps", "0")
    assert res.returncode == 4
    assert "cmm: error: --max-steps must be a positive integer\n" in res.stderr


def test_exit_code_4_bad_max_steps_non_integer(tmp_path: Path) -> None:
    prog = tmp_path / "test.cmm"
    prog.write_text("module main;\nfn main() {}\n", encoding="utf-8")
    res = run_cmm("run", str(prog), "--max-steps", "abc")
    assert res.returncode == 4
    assert "cmm: error: --max-steps must be a positive integer\n" in res.stderr


def test_exit_code_4_unrecognized_option(tmp_path: Path) -> None:
    prog = tmp_path / "test.cmm"
    prog.write_text("module main;\nfn main() {}\n", encoding="utf-8")
    res = run_cmm("check", str(prog), "--max-steps", "10")
    assert res.returncode == 4
    assert "cmm: error: unrecognized arguments:" in res.stderr


def test_exit_code_4_version_with_command() -> None:
    res = run_cmm("--version", "run")
    assert res.returncode == 4
    assert "cmm: error:" in res.stderr


# ============================================================================
# 7. Max Steps Limit Bounds (§11.1, §10.6)
# ============================================================================

def test_run_max_steps_within_limit(tmp_path: Path) -> None:
    prog = tmp_path / "loop.cmm"
    prog.write_text("module main;\nfn main() {\n    mut i = 0;\n    while (i < 3) {\n        i += 1;\n    }\n    print(i);\n}\n", encoding="utf-8")
    res = run_cmm("run", str(prog), "--max-steps", "50")
    assert res.returncode == 0
    assert res.stdout == "3\n"
    assert res.stderr == ""


def test_run_max_steps_exceeded_r005(tmp_path: Path) -> None:
    prog = tmp_path / "infinite.cmm"
    prog.write_text("module main;\nfn main() {\n    while (true) {}\n}\n", encoding="utf-8")
    res = run_cmm("run", str(prog), "--max-steps", "10")
    assert res.returncode == 2
    assert "runtime error: step limit exceeded (10 steps)" in res.stderr
    assert f"{prog}:3:5:" in res.stderr


# ============================================================================
# 8. Platform Independence: UTF-8, CRLF, BOM (§13)
# ============================================================================

def test_utf8_output_non_ascii_strings(tmp_path: Path) -> None:
    prog = tmp_path / "unicode.cmm"
    prog.write_text('module main;\nfn main() {\n    print("Hello, 世界! ☕ 🚀");\n}\n', encoding="utf-8")
    res = run_cmm("run", str(prog))
    assert res.returncode == 0
    assert res.stdout == "Hello, 世界! ☕ 🚀\n"


def test_crlf_line_endings_handling(tmp_path: Path) -> None:
    prog = tmp_path / "crlf.cmm"
    # Write with Windows \r\n line endings
    crlf_content = b"module main;\r\nfn main() {\r\n    print(\"CRLF\");\r\n}\r\n"
    prog.write_bytes(crlf_content)
    res = run_cmm("run", str(prog))
    assert res.returncode == 0
    assert res.stdout == "CRLF\n"


def test_utf8_bom_handling(tmp_path: Path) -> None:
    prog = tmp_path / "bom.cmm"
    # Write with UTF-8 BOM prefix
    bom_content = b"\xef\xbb\xbfmodule main;\nfn main() {\n    print(\"BOM\");\n}\n"
    prog.write_bytes(bom_content)
    res = run_cmm("run", str(prog))
    assert res.returncode == 0
    assert res.stdout == "BOM\n"


# ============================================================================
# 9. Exit Code 70: Internal Errors and CMM_DEBUG (§11.2, §11.5)
# ============================================================================

def test_exit_code_70_internal_error_without_debug(tmp_path: Path) -> None:
    prog = tmp_path / "internal_bug.cmm"
    prog.write_text("module main;\nfn main() {}\n", encoding="utf-8")

    # Monkeypatch cmm.cli.analyze in a subprocess to raise an unexpected internal exception
    script = (
        "import sys, cmm.cli;"
        "cmm.cli.analyze = lambda _: (_ for _ in ()).throw(RuntimeError('simulated unexpected crash'));"
        "sys.exit(cmm.cli.main(['run', sys.argv[1]]))"
    )
    cmd = [sys.executable, "-c", script, str(prog)]
    env = os.environ.copy()
    env.pop("CMM_DEBUG", None)

    res = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert res.returncode == 70
    assert "cmm: internal error: RuntimeError: simulated unexpected crash\n" in res.stderr
    assert "Traceback" not in res.stderr


def test_exit_code_70_internal_error_with_cmm_debug(tmp_path: Path) -> None:
    prog = tmp_path / "internal_bug.cmm"
    prog.write_text("module main;\nfn main() {}\n", encoding="utf-8")

    script = (
        "import sys, cmm.cli;"
        "cmm.cli.analyze = lambda _: (_ for _ in ()).throw(RuntimeError('simulated unexpected crash'));"
        "sys.exit(cmm.cli.main(['run', sys.argv[1]]))"
    )
    cmd = [sys.executable, "-c", script, str(prog)]
    env = os.environ.copy()
    env["CMM_DEBUG"] = "1"

    res = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert res.returncode == 70
    assert "cmm: internal error: RuntimeError: simulated unexpected crash\n" in res.stderr
    assert "Traceback (most recent call last):" in res.stderr


# ============================================================================
# 10. Transpile Command (§16)
# ============================================================================

def test_transpile_success(tmp_path: Path) -> None:
    prog = tmp_path / "hello.cmm"
    out_c = tmp_path / "hello.c"
    prog.write_text('module main;\nfn main() {\n    print("Hello, C--!");\n}\n', encoding="utf-8")
    res = run_cmm("transpile", str(prog), "-o", str(out_c))
    assert res.returncode == 0
    assert res.stdout == ""
    assert res.stderr == ""
    assert out_c.is_file()
    assert "Hello, C--!" in out_c.read_text(encoding="utf-8") or r"\x48\x65\x6c\x6c\x6f" in out_c.read_text(encoding="utf-8")


def test_transpile_missing_out_flag(tmp_path: Path) -> None:
    prog = tmp_path / "hello.cmm"
    prog.write_text("module main;\nfn main() {}\n", encoding="utf-8")
    res = run_cmm("transpile", str(prog))
    assert res.returncode == 4
    assert "cmm: error:" in res.stderr
    assert "-o/--out" in res.stderr


def test_transpile_missing_file() -> None:
    res = run_cmm("transpile", "-o", "out.c")
    assert res.returncode == 4
    assert "cmm: error:" in res.stderr


def test_transpile_source_not_found(tmp_path: Path) -> None:
    non_existent = tmp_path / "missing.cmm"
    out_c = tmp_path / "out.c"
    res = run_cmm("transpile", str(non_existent), "-o", str(out_c))
    assert res.returncode == 3
    assert f"cmm: error: cannot read '{non_existent}': file not found\n" == res.stderr


def test_transpile_static_error(tmp_path: Path) -> None:
    bad_prog = tmp_path / "bad.cmm"
    out_c = tmp_path / "out.c"
    bad_prog.write_text("module main;\nfn main() {\n    let x = undeclared;\n}\n", encoding="utf-8")
    res = run_cmm("transpile", str(bad_prog), "-o", str(out_c))
    assert res.returncode == 1
    assert "semantic error: undeclared variable 'undeclared'" in res.stderr
    assert not out_c.exists()

