"""Tests for C-- friendly diagnostic explanations, plain-language linting, suggestions, and rendering (§9)."""

import io
from pathlib import Path
import re
import subprocess
import sys
import pytest

from cmm.analyzer import analyze
from cmm.diagnostic_render import render_diagnostic
from cmm.errors import CmmError, ParseError, SemanticError, CmmRuntimeError
from cmm.explanations import EXPLANATIONS, ExplanationContext
from cmm.interpreter import run
from cmm.lexer import normalize_source, tokenize
from cmm.parser import parse, Parser
from cmm.suggest import damerau_levenshtein, find_suggestion


def parse_src(source: str):
    return parse(tokenize(normalize_source(source)))


# ============================================================================
# 1. Suggestion & Edit-Distance Tests (§9.5)
# ============================================================================

def test_suggestion_damerau_levenshtein() -> None:
    # Exact match
    assert damerau_levenshtein("hello", "hello") == 0
    # Single typo
    assert damerau_levenshtein("whlie", "while") == 1  # transposition
    assert damerau_levenshtein("retrun", "return") == 1  # transposition
    assert damerau_levenshtein("fucntion", "function") == 1  # transposition
    # Case difference counts as distance 1
    assert damerau_levenshtein("Main", "main") == 1
    assert damerau_levenshtein("MAIN", "main") == 1


def test_find_suggestion() -> None:
    candidates = ["while", "for", "return", "switch", "mut", "let"]
    assert find_suggestion("whlie", candidates) == "while"
    assert find_suggestion("retrun", candidates) == "return"
    # Case difference
    assert find_suggestion("While", candidates) == "while"
    # Distance 3: no suggestion
    assert find_suggestion("completelywrong", candidates) is None

    # Alphabetical tie breaker
    tie_candidates = ["beta", "alpha"]
    assert find_suggestion("alphb", tie_candidates) == "alpha"


# ============================================================================
# 2. Plain-Language Jargon & Placeholder Scanner (§9.2)
# ============================================================================

BANNED_JARGON_WORDS = [
    r"\btoken\b",
    r"\btokens\b",
    r"\blexer\b",
    r"\bparser\b",
    r"\bast\b",
    r"\boperand\b",
    r"\boperands\b",
    r"\bidentifier\b",
    r"\bidentifiers\b",
    r"\barity\b",
    r"\blvalue\b",
    r"\bsymbol table\b",
    r"\bscope resolution\b",
    r"\bexpression statement\b",
]


def test_plain_language_no_banned_jargon() -> None:
    """Verify that no explanation uses compiler jargon from §3."""
    for code, expl in EXPLANATIONS.items():
        ctx = ExplanationContext(code=code, message="test message", line=1, col=1)
        what_text = expl.render_what(ctx)
        fix_text = expl.render_fix(ctx)

        for pattern in BANNED_JARGON_WORDS:
            assert not re.search(pattern, what_text, re.IGNORECASE), (
                f"[{code}] 'what went wrong' contains banned jargon matching {pattern}: '{what_text}'"
            )
            assert not re.search(pattern, fix_text, re.IGNORECASE), (
                f"[{code}] 'how to fix' contains banned jargon matching {pattern}: '{fix_text}'"
            )


def test_no_unfilled_placeholders() -> None:
    """Verify that every explanation renders with default context without leftover {placeholder}."""
    for code, expl in EXPLANATIONS.items():
        ctx = ExplanationContext(code=code, message="test message", line=1, col=1)
        what_text = expl.render_what(ctx)
        fix_text = expl.render_fix(ctx)

        assert not re.search(r"\{[a-zA-Z0-9_]+\}", what_text), (
            f"[{code}] 'what' contains leftover placeholder: {what_text}"
        )
        assert not re.search(r"\{[a-zA-Z0-9_]+\}", fix_text), (
            f"[{code}] 'fix' contains leftover placeholder: {fix_text}"
        )


def test_what_and_fix_limits() -> None:
    """Verify sentence limits per §3: max 2 sentences for what, non-empty fix."""
    for code, expl in EXPLANATIONS.items():
        ctx = ExplanationContext(code=code, message="test message", line=1, col=1)
        what_text = expl.render_what(ctx)
        fix_text = expl.render_fix(ctx)

        # Count sentence ending periods (excluding abbreviations like e.g.)
        sentences = [s.strip() for s in re.split(r"[.!?]+", what_text) if s.strip()]
        assert len(sentences) <= 2, f"[{code}] 'what' has more than 2 sentences: {what_text}"
        assert len(fix_text.strip()) > 0, f"[{code}] 'fix' is empty"


# ============================================================================
# 3. Diagnostic Code Coverage (§9.8)
# ============================================================================

def test_explanations_catalog_complete() -> None:
    """Verify all 58 active diagnostic codes are present and retired codes are omitted."""
    # L001 - L012
    for i in range(1, 13):
        code = f"L{i:03d}"
        assert code in EXPLANATIONS, f"Missing lexical code {code}"

    # Syntax codes
    assert "S001" in EXPLANATIONS
    assert "S003" in EXPLANATIONS
    assert "S004" in EXPLANATIONS
    assert "S002" not in EXPLANATIONS, "S002 is retired and must not be present"

    # Semantic codes E001 - E031 (omitting E018)
    for i in range(1, 32):
        if i == 18:
            assert "E018" not in EXPLANATIONS, "E018 is unassigned and must not be present"
            continue
        code = f"E{i:03d}"
        assert code in EXPLANATIONS, f"Missing semantic code {code}"

    # Runtime codes R001 - R014
    for i in range(1, 15):
        code = f"R{i:03d}"
        assert code in EXPLANATIONS, f"Missing runtime code {code}"

    # Transpiler code
    assert "T001" in EXPLANATIONS

    assert len(EXPLANATIONS) == 60


# ============================================================================
# 4. Renderer Edge Cases (§9.4)
# ============================================================================

def test_render_long_line_trimmed() -> None:
    """Lines longer than 100 characters must be trimmed around caret with '...'."""
    long_line = "let very_long_variable_name_one_two_three_four_five = 100 + 200 + 300 + 400 + 500 + 600 + 700 + 800 + 900 + 1000;"
    assert len(long_line) > 100
    err = SemanticError("E001", "type mismatch", line=1, col=85)
    rendered = render_diagnostic(err, "test.cmm", [long_line], help_enabled=True)
    assert "..." in rendered
    assert "test.cmm:1:85: semantic error: type mismatch" in rendered


def test_render_tabs_preserved() -> None:
    """Tabs before the caret must be preserved in the caret line."""
    tabbed_line = "\t\tlet x = 1;"
    err = ParseError("S001", "syntax error", line=1, col=3)
    rendered = render_diagnostic(err, "test.cmm", [tabbed_line], help_enabled=True)
    lines = rendered.splitlines()
    caret_line = [l for l in lines if "^" in l][0]
    assert "\t\t" in caret_line


def test_render_missing_source() -> None:
    """When source_lines is empty or missing, diagnostic renders without crash."""
    err = SemanticError("E001", "type mismatch", line=1, col=1)
    rendered = render_diagnostic(err, "test.cmm", [], help_enabled=True)
    assert "test.cmm:1:1: semantic error: type mismatch\n" in rendered
    assert "what went wrong:" in rendered
    assert "how to fix:" in rendered


def test_render_no_help_flag() -> None:
    """When help_enabled=False, produces exact original 3-line format."""
    src = ["let x = 10;"]
    err = SemanticError("E001", "type mismatch", line=1, col=5)
    rendered = render_diagnostic(err, "test.cmm", src, help_enabled=False)
    assert rendered == (
        "test.cmm:1:5: semantic error: type mismatch\n"
        "    let x = 10;\n"
        "        ^\n"
    )


def test_cli_no_help_flag_integration(tmp_path: Path) -> None:
    """Verify that --no-help works from the CLI for run and check commands."""
    p = tmp_path / "bad.cmm"
    p.write_text("module test;\nfn main() {\n    let x = 10\n}\n", encoding="utf-8")

    # With --no-help
    res_no_help = subprocess.run(
        [sys.executable, "-m", "cmm", "run", "--no-help", str(p)],
        capture_output=True,
        text=True,
    )
    assert res_no_help.returncode == 1
    assert "what went wrong:" not in res_no_help.stderr
    assert len(res_no_help.stderr.strip().splitlines()) == 3

    # Default (with help)
    res_help = subprocess.run(
        [sys.executable, "-m", "cmm", "run", str(p)],
        capture_output=True,
        text=True,
    )
    assert res_help.returncode == 1
    assert "what went wrong:" in res_help.stderr
    assert "how to fix:" in res_help.stderr


# ============================================================================
# 5. Documentation Drift Test (§10)
# ============================================================================

def test_docs_up_to_date() -> None:
    """Verify that docs/errors.md matches generate_error_docs output."""
    import importlib.util
    gen_script = Path(__file__).resolve().parent.parent / "scripts" / "generate_error_docs.py"
    spec = importlib.util.spec_from_file_location("generate_error_docs", str(gen_script))
    gen_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen_mod)

    expected_doc = gen_mod.generate_markdown()
    doc_path = Path(__file__).resolve().parent.parent / "docs" / "errors.md"
    assert doc_path.exists()
    assert doc_path.read_text(encoding="utf-8") == expected_doc


# ============================================================================
# 6. Golden Output Tests for Every Diagnostic Code (§9.1)
# ============================================================================

GOLDEN_TESTS = sorted((Path(__file__).resolve().parent / "errors").glob("*.cmm"))


@pytest.mark.parametrize("cmm_path", GOLDEN_TESTS, ids=lambda p: p.stem)
def test_golden_diagnostic_output(cmm_path: Path) -> None:
    """Verify that each code's golden program produces exact expected output."""
    err_path = cmm_path.with_suffix(".err")
    assert err_path.exists(), f"Missing expected stderr for {cmm_path.name}"
    expected = err_path.read_text(encoding="utf-8")

    code = cmm_path.stem.split("_")[0]
    extra_args = ["--max-steps", "10"] if code == "R005" else (["-o", "/dev/null"] if code == "T001" else [])
    cmd = "transpile" if code == "T001" else "run"

    res = subprocess.run(
        [sys.executable, "-m", "cmm", cmd, *extra_args, cmm_path.name],
        cwd=str(cmm_path.parent),
        input="" if code == "R008" else None,
        capture_output=True,
        text=True,
    )
    assert res.stderr == expected


def test_r011_invalid_utf8_stdin() -> None:
    """Verify R011 diagnostic for non-UTF8 input."""
    from cmm.runtime_io import cmm_read_line
    with pytest.raises(CmmRuntimeError) as exc_info:
        cmm_read_line(stream=io.BytesIO(b"\xff\xff\xff"), line=1, col=1)
    err = exc_info.value
    assert err.code == "R011"
    rendered = render_diagnostic(err, "test.cmm", ["read_line();"], help_enabled=True)
    assert "test.cmm:1:1: runtime error: standard input is not valid UTF-8" in rendered
    assert "what went wrong:" in rendered
    assert "how to fix:" in rendered


def test_example_validity() -> None:
    """Verify that all example strings in EXPLANATIONS tokenize without lexical errors (§9.3)."""
    ctx = ExplanationContext("TEST", "test", 1, 1)
    for code, expl in EXPLANATIONS.items():
        ex = expl.render_example(ctx)
        if ex is not None:
            tokens = tokenize(normalize_source(ex))
            assert len(tokens) > 0


# ============================================================================
# 6. Pilot & Interactive Diagnostic Render Tests
# ============================================================================

def test_pilot_e013_render() -> None:
    src = """module test;
fn sum(a: int, b: int) -> int {
    let x = a + b;
}
fn main() {}
"""
    prog = parse_src(src)
    errors = analyze(prog)
    assert len(errors) == 1
    err = errors[0]
    assert err.code == "E013"

    rendered = render_diagnostic(err, "test.cmm", src.splitlines(), help_enabled=True)
    assert "test.cmm:2:4: semantic error: function 'sum' does not return a value on all paths" in rendered
    assert "what went wrong:" in rendered
    assert "The function 'sum' promises to give back a int" in rendered
    assert "how to fix:" in rendered
    assert "return 0;" in rendered


def test_pilot_s001_render() -> None:
    src = """module test;
fn main() {
    let x = 10
}
"""
    with pytest.raises(ParseError) as exc_info:
        Parser(tokenize(src)).parse_program()

    err = exc_info.value
    assert err.code == "S001"
    rendered = render_diagnostic(err, "test.cmm", src.splitlines(), help_enabled=True)
    assert "test.cmm:4:1: syntax error: expected ';', found '}'" in rendered
    assert "what went wrong:" in rendered
    assert "At this spot C-- expected ';', but found '}'." in rendered
    assert "how to fix:" in rendered
    assert "Add a semicolon ';' at the end of the line." in rendered


def test_pilot_r006_render() -> None:
    src = """module test;
fn main() {
    let a = [1, 2, 3];
    print(a[10]);
}
"""
    prog = parse_src(src)
    with pytest.raises(CmmRuntimeError) as exc_info:
        run(prog, out=io.StringIO())

    err = exc_info.value
    assert err.code == "R006"
    rendered = render_diagnostic(err, "test.cmm", src.splitlines(), help_enabled=True)
    assert "test.cmm:4:12: runtime error: index out of range (index 10, length 3)" in rendered
    assert "what went wrong:" in rendered
    assert "You asked for position 10, but the array only has 3 items" in rendered
    assert "how to fix:" in rendered
