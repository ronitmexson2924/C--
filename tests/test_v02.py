"""Comprehensive test suite for C-- v0.2.0 specification addendum (Spec v0.2.md).

Covers:
- Lexer: string forms, escapes, L002, L003, new keywords/reserved words
- Parser: functions, chaining, switch, arrays, nesting limits
- Semantic Analyzer: E008-E031, return checks, collections, methods, shadowing
- Interpreter: value semantics, methods, recursion limit R007, collections formatting
- Runtime I/O: input(), parse_int(), parse_float(), R008-R014
- C Backend rejection: T001
"""

import io
import math
import sys
import pytest

from cmm.analyzer import analyze
from cmm.astprint import format_ast
from cmm.codegen_c import generate_c
from cmm.errors import CmmError, CmmRuntimeError, LexError, ParseError, SemanticError
from cmm.interpreter import Interpreter, run
from cmm.lexer import normalize_source, tokenize
from cmm.parser import parse
from cmm.runtime_io import cmm_parse_float, cmm_parse_int, cmm_read_line
from cmm.tokens import TokenType


def parse_src(source: str):
    norm = normalize_source(source)
    tokens = tokenize(norm)
    return parse(tokens)


def analyze_src(source: str) -> list[SemanticError]:
    prog = parse_src(source)
    return analyze(prog)


def run_src(source: str, stdin_text: str = "") -> str:
    prog = parse_src(source)
    errors = analyze(prog)
    assert not errors, f"Semantic errors: {errors}"
    out = io.StringIO()
    stdin_stream = io.StringIO(stdin_text)
    run(prog, out=out, stdin=stdin_stream)
    return out.getvalue()


# ============================================================================
# 1. Lexer Tests (§A3, §A9.1)
# ============================================================================

def test_lexer_string_literals() -> None:
    # Single quote
    tokens = tokenize("'hello world'")
    assert tokens[0].type == TokenType.STRING
    assert tokens[0].value == "hello world"

    # Double quote
    tokens = tokenize('"hello world"')
    assert tokens[0].type == TokenType.STRING
    assert tokens[0].value == "hello world"

    # Triple single quote
    tokens = tokenize("'''line 1\nline 2'''")
    assert tokens[0].type == TokenType.STRING
    assert tokens[0].value == "line 1\nline 2"

    # Triple double quote
    tokens = tokenize('"""line 1\nline 2"""')
    assert tokens[0].type == TokenType.STRING
    assert tokens[0].value == "line 1\nline 2"

    # Empty strings
    assert tokenize('""')[0].value == ""
    assert tokenize("''")[0].value == ""
    assert tokenize('""""""')[0].value == ""
    assert tokenize("''''''")[0].value == ""


def test_lexer_string_escapes() -> None:
    tokens = tokenize(r'"\n \t \r \" \' \\"')
    assert tokens[0].value == "\n \t \r \" ' \\"


def test_lexer_l002_unterminated_string() -> None:
    # Newline in single-line string
    with pytest.raises(LexError) as exc_info:
        tokenize('"hello\nworld"')
    assert exc_info.value.code == "L002"

    # EOF in triple-quoted string
    with pytest.raises(LexError) as exc_info:
        tokenize('"""unterminated')
    assert exc_info.value.code == "L002"

    # Backslash at EOF
    with pytest.raises(LexError) as exc_info:
        tokenize('"hello\\')
    assert exc_info.value.code == "L002"


def test_lexer_l003_invalid_escape() -> None:
    with pytest.raises(LexError) as exc_info:
        tokenize(r'"\x"')
    assert exc_info.value.code == "L003"
    assert exc_info.value.message == "invalid escape sequence '\\x'"

    # Escaped newline represented as U+000A
    with pytest.raises(LexError) as exc_info:
        tokenize('"""\\\n"""')
    assert exc_info.value.code == "L003"
    assert "U+000A" in exc_info.value.message


def test_lexer_punctuation_and_keywords() -> None:
    src = "-> , : . [ ] return switch case default array list stack queue"
    tokens = tokenize(src)
    expected_types = [
        TokenType.ARROW,
        TokenType.COMMA,
        TokenType.COLON,
        TokenType.DOT,
        TokenType.LBRACKET,
        TokenType.RBRACKET,
        TokenType.RETURN,
        TokenType.SWITCH,
        TokenType.CASE,
        TokenType.DEFAULT,
        TokenType.KW_ARRAY,
        TokenType.KW_LIST,
        TokenType.KW_STACK,
        TokenType.KW_QUEUE,
    ]
    for i, exp in enumerate(expected_types):
        assert tokens[i].type == exp


# ============================================================================
# 2. Parser Tests (§A5, §A9.2)
# ============================================================================

def test_parser_top_level_functions() -> None:
    src = """
    module test;
    fn add(a: int, b: int) -> int {
        return a + b;
    }
    fn main() {
        let x = add(1, 2);
    }
    """
    prog = parse_src(src)
    assert len(prog.functions) == 2
    assert prog.functions[0].name == "add"
    assert prog.functions[1].name == "main"


def test_parser_chained_indexing() -> None:
    src = "module test; fn main() { let x = a[0][1]; }"
    prog = parse_src(src)
    stmt = prog.body.statements[0]
    # Expr is Index on Index
    assert type(stmt.init).__name__ == "Index"
    assert type(stmt.init.target).__name__ == "Index"


def test_parser_negative_indexed_expr() -> None:
    src = "module test; fn main() { let x = -a[0]; }"
    prog = parse_src(src)
    stmt = prog.body.statements[0]
    assert type(stmt.init).__name__ == "UnaryOp"
    assert stmt.init.op == "-"


def test_parser_case_with_negative_int() -> None:
    src = """
    module test;
    fn main() {
        switch (x) {
            case -5, 0, 5: { print(1); }
            default: { print(0); }
        }
    }
    """
    prog = parse_src(src)
    sw = prog.body.statements[0]
    assert [v.value for v in sw.cases[0].values] == [-5, 0, 5]


# ============================================================================
# 3. Semantic Analyzer Tests (§A6, §A7.1, §A9.3)
# ============================================================================

def test_analyzer_e008_undefined_function() -> None:
    src = "module test; fn main() { foo(); }"
    errors = analyze_src(src)
    assert any(e.code == "E008" and "undefined function 'foo'" in e.message for e in errors)


def test_analyzer_e009_duplicate_function() -> None:
    src = "module test; fn foo() {} fn foo() {} fn main() {}"
    errors = analyze_src(src)
    assert any(e.code == "E009" and "function 'foo' is already defined" in e.message for e in errors)


def test_analyzer_e010_cannot_redefine_builtin() -> None:
    src = "module test; fn input() {} fn main() {}"
    errors = analyze_src(src)
    assert any(e.code == "E010" and "cannot redefine built-in function 'input'" in e.message for e in errors)


def test_analyzer_e011_wrong_arg_count() -> None:
    src = """
    module test;
    fn add(a: int, b: int) -> int { return a + b; }
    fn main() {
        let x = add(1);
    }
    """
    errors = analyze_src(src)
    assert any(e.code == "E011" and "expects 2 argument(s), got 1" in e.message for e in errors)


def test_analyzer_e012_wrong_arg_type() -> None:
    src = """
    module test;
    fn add(a: int, b: int) -> int { return a + b; }
    fn main() {
        let x = add(1, 2.0);
    }
    """
    errors = analyze_src(src)
    assert any(e.code == "E012" and "argument 2 of function 'add' must be int, got float" in e.message for e in errors)


def test_analyzer_e013_definitely_returns() -> None:
    src = """
    module test;
    fn test(c: bool) -> int {
        if (c) {
            return 1;
        }
    }
    fn main() {}
    """
    errors = analyze_src(src)
    assert any(e.code == "E013" and "does not return a value on all paths" in e.message for e in errors)


def test_analyzer_e014_void_func_returns_value() -> None:
    src = "module test; fn foo() { return 1; } fn main() {}"
    errors = analyze_src(src)
    assert any(e.code == "E014" and "void function 'foo' cannot return a value" in e.message for e in errors)


def test_analyzer_e015_bare_return_in_valued_func() -> None:
    src = "module test; fn foo() -> int { return; } fn main() {}"
    errors = analyze_src(src)
    assert any(e.code == "E015" and "function 'foo' must return a value of type int" in e.message for e in errors)


def test_analyzer_e016_wrong_return_type() -> None:
    src = "module test; fn foo() -> int { return 1.5; } fn main() {}"
    errors = analyze_src(src)
    assert any(e.code == "E016" and "cannot return float from function 'foo' declared to return int" in e.message for e in errors)


def test_analyzer_e017_main_signature() -> None:
    src = "module test; fn main(x: int) {}"
    errors = analyze_src(src)
    assert any(e.code == "E017" for e in errors)

    src2 = "module test; fn main() -> int { return 0; }"
    errors2 = analyze_src(src2)
    assert any(e.code == "E017" for e in errors2)


def test_analyzer_e019_cannot_call_main() -> None:
    src = "module test; fn main() { main(); }"
    errors = analyze_src(src)
    assert any(e.code == "E019" and "'main' cannot be called" in e.message for e in errors)


def test_analyzer_e020_void_in_expression() -> None:
    src = """
    module test;
    fn foo() {}
    fn main() {
        let x = foo();
    }
    """
    errors = analyze_src(src)
    assert any(e.code == "E020" and "function 'foo' returns no value" in e.message for e in errors)


def test_analyzer_e021_switch_selector_type() -> None:
    src = "module test; fn main() { switch (1.5) { case 1: {} } }"
    errors = analyze_src(src)
    assert any(e.code == "E021" and "switch selector must be int or string, got float" in e.message for e in errors)


def test_analyzer_e022_case_type_mismatch() -> None:
    src = "module test; fn main() { switch (1) { case \"one\": {} } }"
    errors = analyze_src(src)
    assert any(e.code == "E022" and "case value of type string does not match switch selector of type int" in e.message for e in errors)


def test_analyzer_e023_duplicate_case() -> None:
    src = "module test; fn main() { switch (1) { case 1: {} case 1: {} } }"
    errors = analyze_src(src)
    assert any(e.code == "E023" and "duplicate case value 1" in e.message for e in errors)


def test_analyzer_e024_indexing_non_indexable() -> None:
    src = "module test; fn main() { let x = 42; print(x[0]); }"
    errors = analyze_src(src)
    assert any(e.code == "E024" and "type int cannot be indexed" in e.message for e in errors)


def test_analyzer_e025_index_not_int() -> None:
    src = "module test; fn main() { let s = \"hi\"; print(s[1.5]); }"
    errors = analyze_src(src)
    assert any(e.code == "E025" and "index must be int, got float" in e.message for e in errors)


def test_analyzer_e026_unknown_method() -> None:
    src = "module test; fn main() { let s = \"hi\"; s.foo(); }"
    errors = analyze_src(src)
    assert any(e.code == "E026" and "type string has no method 'foo'" in e.message for e in errors)


def test_analyzer_e027_array_literal_mixed_types() -> None:
    src = "module test; fn main() { let a = [1, 2.5]; }"
    errors = analyze_src(src)
    assert any(e.code == "E027" for e in errors)


def test_analyzer_e028_mutating_method_on_immutable() -> None:
    src = "module test; fn main() { let l = list<int>(); l.push(1); }"
    errors = analyze_src(src)
    assert any(e.code == "E028" and "cannot call mutating method 'push' on immutable variable 'l'" in e.message for e in errors)


def test_analyzer_e029_assign_element_immutable() -> None:
    src = "module test; fn main() { let a = [1, 2]; a[0] = 5; }"
    errors = analyze_src(src)
    assert any(e.code == "E029" and "cannot assign to element of immutable variable 'a'" in e.message for e in errors)


def test_analyzer_e030_assign_string_element() -> None:
    src = "module test; fn main() { mut s = \"hi\"; s[0] = \"H\"; }"
    errors = analyze_src(src)
    assert any(e.code == "E030" and "strings are immutable; cannot assign to an element" in e.message for e in errors)


def test_analyzer_e031_duplicate_parameter() -> None:
    src = "module test; fn foo(x: int, x: int) {} fn main() {}"
    errors = analyze_src(src)
    assert any(e.code == "E031" and "duplicate parameter 'x'" in e.message for e in errors)


def test_analyzer_parameter_shadowing() -> None:
    src = """
    module test;
    fn foo(x: int) -> int {
        let x = 100;
        return x;
    }
    fn main() {}
    """
    errors = analyze_src(src)
    assert errors == []


def test_analyzer_forward_calls_and_mutual_recursion() -> None:
    src = """
    module test;
    fn main() {
        let x = is_even(4);
    }
    fn is_even(n: int) -> bool {
        if (n == 0) { return true; }
        return is_odd(n - 1);
    }
    fn is_odd(n: int) -> bool {
        if (n == 0) { return false; }
        return is_even(n - 1);
    }
    """
    errors = analyze_src(src)
    assert errors == []


# ============================================================================
# 4. Interpreter & Collections Tests (§A6, §A7.2, §A9.4)
# ============================================================================

def test_interpreter_value_semantics() -> None:
    src = """
    module test;
    fn modify(lst: list<int>) {
        mut local = lst;
        local.push(999);
    }
    fn main() {
        mut a = list<int>();
        a.push(1);
        a.push(2);

        mut b = a;
        b.push(3);

        print(a);
        print(b);

        modify(a);
        print(a);
    }
    """
    out = run_src(src)
    expected = "[1, 2]\n[1, 2, 3]\n[1, 2]\n"
    assert out == expected


def test_interpreter_collections_formatting() -> None:
    src = r"""
    module test;
    fn main() {
        let a = ["hello\nworld", "foo\tbar"];
        print(a);

        mut s = stack<string>();
        s.push("bottom");
        s.push("top");
        print(s);

        mut q = queue<int>();
        q.enqueue(10);
        q.enqueue(20);
        print(q);
    }
    """
    out = run_src(src)
    expected = (
        '["hello\\nworld", "foo\\tbar"]\n'
        'stack["bottom", "top"]\n'
        'queue[10, 20]\n'
    )
    assert out == expected


def test_interpreter_switch_execution() -> None:
    src = """
    module test;
    fn describe(n: int) -> string {
        switch (n) {
            case 1: { return "one"; }
            case 2, 3: { return "two or three"; }
            default: { return "other"; }
        }
    }
    fn main() {
        print(describe(1));
        print(describe(2));
        print(describe(3));
        print(describe(99));
    }
    """
    out = run_src(src)
    assert out == "one\ntwo or three\ntwo or three\nother\n"


def test_interpreter_methods() -> None:
    src = """
    module test;
    fn main() {
        mut l = list<int>();
        print(l.is_empty());
        l.push(10);
        l.push(20);
        l.insert(1, 15);
        print(l);
        print(l.contains(15));
        print(l.contains(99));
        let rem = l.remove(1);
        print(rem);
        print(l.pop());
        print(l);
        l.clear();
        print(l.is_empty());

        mut s = stack<int>();
        s.push(1);
        s.push(2);
        print(s.peek());
        print(s.pop());
        print(s.len());

        mut q = queue<int>();
        q.enqueue(1);
        q.enqueue(2);
        print(q.peek());
        print(q.dequeue());
        print(q.len());
    }
    """
    out = run_src(src)
    expected = (
        "true\n"
        "[10, 15, 20]\n"
        "true\n"
        "false\n"
        "15\n"
        "20\n"
        "[10]\n"
        "true\n"
        "2\n"
        "2\n"
        "1\n"
        "1\n"
        "1\n"
        "1\n"
    )
    assert out == expected


def test_interpreter_r006_out_of_range() -> None:
    src = "module test; fn main() { let a = [1, 2]; print(a[-1]); }"
    with pytest.raises(CmmRuntimeError) as exc_info:
        run_src(src)
    assert exc_info.value.code == "R006"
    assert "index out of range (index -1, length 2)" in exc_info.value.message


def test_interpreter_r012_empty_collection() -> None:
    src = "module test; fn main() { mut s = stack<int>(); s.pop(); }"
    with pytest.raises(CmmRuntimeError) as exc_info:
        run_src(src)
    assert exc_info.value.code == "R012"
    assert "pop on empty stack" in exc_info.value.message


def test_interpreter_r014_negative_array_size() -> None:
    src = "module test; fn main() { let a = array<int>(-5, 0); }"
    with pytest.raises(CmmRuntimeError) as exc_info:
        run_src(src)
    assert exc_info.value.code == "R014"
    assert "array size must not be negative (got -5)" in exc_info.value.message


def test_interpreter_r007_recursion_depth_limit() -> None:
    src = """
    module test;
    fn recurse(n: int) -> int {
        return recurse(n + 1);
    }
    fn main() {
        recurse(1);
    }
    """
    with pytest.raises(CmmRuntimeError) as exc_info:
        run_src(src)
    assert exc_info.value.code == "R007"
    assert "call depth limit exceeded (1000)" in exc_info.value.message


# ============================================================================
# 5. Runtime I/O & Conversions (§A6.2, §A7.2, §A9.5)
# ============================================================================

def test_io_input_prompts_and_lines() -> None:
    src = """
    module test;
    fn main() {
        let name = input("Enter name: ");
        print("Hello, " + name);
    }
    """
    # Note: no string concatenation in v0.2, so test print(name)
    src_valid = """
    module test;
    fn main() {
        let s1 = input("Prompt: ");
        print(s1);
        let s2 = input();
        print(s2);
    }
    """
    out_buf = io.StringIO()
    in_buf = io.StringIO("Line 1\r\nLine 2\n")
    prog = parse_src(src_valid)
    run(prog, out=out_buf, stdin=in_buf)
    assert out_buf.getvalue() == "Prompt: Line 1\nLine 2\n"


def test_io_r008_end_of_input() -> None:
    empty_stream = io.BytesIO(b"")
    with pytest.raises(CmmRuntimeError) as exc_info:
        cmm_read_line(empty_stream)
    assert exc_info.value.code == "R008"
    assert exc_info.value.message == "end of input"


def test_io_r011_invalid_utf8() -> None:
    bad_stream = io.BytesIO(b"\xff\xfe\n")
    with pytest.raises(CmmRuntimeError) as exc_info:
        cmm_read_line(bad_stream)
    assert exc_info.value.code == "R011"
    assert exc_info.value.message == "standard input is not valid UTF-8"


def test_io_parse_int() -> None:
    assert cmm_parse_int("  123  ") == 123
    assert cmm_parse_int("+42") == 42
    assert cmm_parse_int("-99") == -99
    assert cmm_parse_int("0007") == 7

    # Errors -> R009
    with pytest.raises(CmmRuntimeError) as exc_info:
        cmm_parse_int("abc")
    assert exc_info.value.code == "R009"
    assert "cannot convert 'abc' to int" in exc_info.value.message

    with pytest.raises(CmmRuntimeError) as exc_info:
        cmm_parse_int("12_34")
    assert exc_info.value.code == "R009"


def test_io_parse_float() -> None:
    assert cmm_parse_float("  123.45  ") == 123.45
    assert cmm_parse_float("1e3") == 1000.0
    assert cmm_parse_float("-2.5e-2") == -0.025

    # Errors -> R010
    with pytest.raises(CmmRuntimeError) as exc_info:
        cmm_parse_float("inf")
    assert exc_info.value.code == "R010"
    assert "cannot convert 'inf' to float" in exc_info.value.message

    with pytest.raises(CmmRuntimeError) as exc_info:
        cmm_parse_float("nan")
    assert exc_info.value.code == "R010"

    with pytest.raises(CmmRuntimeError) as exc_info:
        cmm_parse_float("0x12")
    assert exc_info.value.code == "R010"


# ============================================================================
# 6. C Backend Rejection Tests (§A10)
# ============================================================================

def test_c_backend_rejects_v02_features() -> None:
    # Multiple functions
    src_funcs = "module test; fn foo() {} fn main() {}"
    with pytest.raises(CmmError) as exc_info:
        generate_c(parse_src(src_funcs), "test.cmm", src_funcs.splitlines())
    assert exc_info.value.code == "T001"
    assert "user-defined functions" in exc_info.value.message

    # Collections
    src_coll = "module test; fn main() { let a = [1, 2]; }"
    with pytest.raises(CmmError) as exc_info:
        generate_c(parse_src(src_coll), "test.cmm", src_coll.splitlines())
    assert exc_info.value.code == "T001"
    assert "collections" in exc_info.value.message

    # Switch
    src_switch = "module test; fn main() { switch (1) { case 1: {} } }"
    with pytest.raises(CmmError) as exc_info:
        generate_c(parse_src(src_switch), "test.cmm", src_switch.splitlines())
    assert exc_info.value.code == "T001"
    assert "switch" in exc_info.value.message
