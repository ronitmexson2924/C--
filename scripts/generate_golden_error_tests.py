#!/usr/bin/env python3
"""Generate golden tests for every diagnostic code into tests/errors/ per §9.1."""

from pathlib import Path
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
ERRORS_TEST_DIR = REPO_ROOT / "tests" / "errors"
ERRORS_TEST_DIR.mkdir(parents=True, exist_ok=True)

FAILING_PROGRAMS: dict[str, tuple[str, str, list[str], str]] = {
    # code: (short_name, source_code, extra_cli_args, command)
    "L001": ("unexpected_char", "module m;\nfn main() {\n    @\n}\n", [], "run"),
    "L002": ("unterminated_string", "module m;\nfn main() {\n    let s = \"hello;\n}\n", [], "run"),
    "L003": ("invalid_escape", "module m;\nfn main() {\n    let s = \"\\k\";\n}\n", [], "run"),
    "L004": ("unterminated_comment", "module m;\n/* unclosed comment\nfn main() {}\n", [], "run"),
    "L005": ("int_out_of_range", "module m;\nfn main() {\n    let x = 99999999999999999999;\n}\n", [], "run"),
    "L006": ("float_out_of_range", "module m;\nfn main() {\n    let x = 1.0e999;\n}\n", [], "run"),
    "L007": ("invalid_number", "module m;\nfn main() {\n    let x = 1.e;\n}\n", [], "run"),
    "L008": ("leading_zero", "module m;\nfn main() {\n    let x = 012;\n}\n", [], "run"),
    "L009": ("plus_plus", "module m;\nfn main() {\n    let x = 1;\n    x++;\n}\n", [], "run"),
    "L010": ("minus_minus", "module m;\nfn main() {\n    let x = 1;\n    x--;\n}\n", [], "run"),
    "L011": ("single_ampersand", "module m;\nfn main() {\n    let b = true & false;\n}\n", [], "run"),
    "L012": ("single_pipe", "module m;\nfn main() {\n    let b = true | false;\n}\n", [], "run"),
    "S001": ("missing_semicolon", "module m;\nfn main() {\n    let x = 10\n}\n", [], "run"),
    "S003": ("reserved_word", "module m;\nfn main() {\n    let break = 1;\n}\n", [], "run"),
    "S004": ("nesting_limit", "module m;\nfn main() {\n    let x = " + ("(" * 205) + "1" + (")" * 205) + ";\n}\n", [], "run"),
    "E001": ("undeclared_var", "module m;\nfn main() {\n    print(y);\n}\n", [], "run"),
    "E002": ("already_declared_var", "module m;\nfn main() {\n    let x = 1;\n    let x = 2;\n}\n", [], "run"),
    "E003": ("immutable_assign", "module m;\nfn main() {\n    let x = 10;\n    x = 20;\n}\n", [], "run"),
    "E004": ("condition_not_bool", "module m;\nfn main() {\n    if (10) {}\n}\n", [], "run"),
    "E005": ("unary_type_mismatch", "module m;\nfn main() {\n    let x = !10;\n}\n", [], "run"),
    "E006": ("binary_type_mismatch", "module m;\nfn main() {\n    let x = 10 + \"hello\";\n}\n", [], "run"),
    "E007": ("assign_type_mismatch", "module m;\nfn main() {\n    mut x = 10;\n    x = \"hello\";\n}\n", [], "run"),
    "E008": ("undefined_fn", "module m;\nfn main() {\n    foo();\n}\n", [], "run"),
    "E009": ("already_defined_fn", "module m;\nfn foo() {}\nfn foo() {}\nfn main() {}\n", [], "run"),
    "E010": ("redefine_builtin", "module m;\nfn print() {}\nfn main() {}\n", [], "run"),
    "E011": ("wrong_arg_count", "module m;\nfn foo(a: int) {}\nfn main() {\n    foo(1, 2);\n}\n", [], "run"),
    "E012": ("wrong_arg_type", "module m;\nfn foo(a: int) {}\nfn main() {\n    foo(\"hi\");\n}\n", [], "run"),
    "E013": ("missing_return", "module m;\nfn foo() -> int {\n}\nfn main() {}\n", [], "run"),
    "E014": ("value_in_void_return", "module m;\nfn foo() {\n    return 10;\n}\nfn main() {}\n", [], "run"),
    "E015": ("bare_return_in_typed", "module m;\nfn foo() -> int {\n    return;\n}\nfn main() {}\n", [], "run"),
    "E016": ("wrong_return_type", "module m;\nfn foo() -> int {\n    return \"hi\";\n}\nfn main() {}\n", [], "run"),
    "E017": ("invalid_main_sig", "module m;\nfn main(a: int) {}\n", [], "run"),
    "E019": ("call_main", "module m;\nfn main() {\n    main();\n}\n", [], "run"),
    "E020": ("void_used_as_value", "module m;\nfn foo() {}\nfn main() {\n    let x = foo();\n}\n", [], "run"),
    "E021": ("invalid_switch_selector", "module m;\nfn main() {\n    switch (1.5) {\n        case 1: {}\n    }\n}\n", [], "run"),
    "E022": ("case_type_mismatch", "module m;\nfn main() {\n    switch (1) {\n        case \"a\": {}\n    }\n}\n", [], "run"),
    "E023": ("duplicate_case", "module m;\nfn main() {\n    switch (1) {\n        case 1: {}\n        case 1: {}\n    }\n}\n", [], "run"),
    "E024": ("index_non_indexable", "module m;\nfn main() {\n    let x = 10;\n    print(x[0]);\n}\n", [], "run"),
    "E025": ("index_not_int", "module m;\nfn main() {\n    let a = [1];\n    print(a[\"zero\"]);\n}\n", [], "run"),
    "E026": ("unknown_method", "module m;\nfn main() {\n    let a = [1];\n    a.push(2);\n}\n", [], "run"),
    "E027": ("array_mixed_types", "module m;\nfn main() {\n    let a = [1, \"two\"];\n}\n", [], "run"),
    "E028": ("mutating_method_on_let", "module m;\nfn main() {\n    let s = stack<int>();\n    s.push(1);\n}\n", [], "run"),
    "E029": ("element_assign_on_let", "module m;\nfn main() {\n    let a = [1];\n    a[0] = 2;\n}\n", [], "run"),
    "E030": ("assign_to_string_element", "module m;\nfn main() {\n    mut s = \"hello\";\n    s[0] = \"H\";\n}\n", [], "run"),
    "E031": ("duplicate_param", "module m;\nfn foo(a: int, a: int) {}\nfn main() {}\n", [], "run"),
    "R001": ("overflow", "module m;\nfn main() {\n    let x = 9223372036854775807 + 1;\n}\n", [], "run"),
    "R002": ("div_zero", "module m;\nfn main() {\n    let x = 10 / 0;\n}\n", [], "run"),
    "R003": ("mod_zero", "module m;\nfn main() {\n    let x = 10 % 0;\n}\n", [], "run"),
    "R004": ("float_overflow", "module m;\nfn main() {\n    let x = 1.0e308 * 10.0;\n}\n", [], "run"),
    "R005": ("step_limit", "module m;\nfn main() {\n    for (mut i = 0; i < 100; i += 1) {}\n}\n", ["--max-steps", "10"], "run"),
    "R006": ("index_oob", "module m;\nfn main() {\n    let a = [1];\n    print(a[5]);\n}\n", [], "run"),
    "R007": ("call_depth", "module m;\nfn rec() {\n    rec();\n}\nfn main() {\n    rec();\n}\n", [], "run"),
    "R008": ("eof_read", "module m;\nfn main() {\n    read_line();\n}\n", [], "run"),
    "R009": ("parse_int_error", "module m;\nfn main() {\n    parse_int(\"abc\");\n}\n", [], "run"),
    "R010": ("parse_float_error", "module m;\nfn main() {\n    parse_float(\"abc\");\n}\n", [], "run"),
    "R012": ("empty_pop", "module m;\nfn main() {\n    mut s = stack<int>();\n    s.pop();\n}\n", [], "run"),
    "R013": ("limit_exceeded", "module m;\nfn main() {\n    let a = array<int>(10000001, 0);\n}\n", [], "run"),
    "R014": ("negative_size", "module m;\nfn main() {\n    let a = array<int>(-1, 0);\n}\n", [], "run"),
    "T001": ("transpile_v02", "module m;\nfn main() {\n    let a = [1, 2];\n}\n", ["-o", "/dev/null"], "transpile"),
}


def main() -> None:
    for code, (short_name, source, extra_args, cmd) in sorted(FAILING_PROGRAMS.items()):
        cmm_file = ERRORS_TEST_DIR / f"{code}_{short_name}.cmm"
        err_file = ERRORS_TEST_DIR / f"{code}_{short_name}.err"

        cmm_file.write_text(source, encoding="utf-8")

        cli_cmd = [sys.executable, "-m", "cmm", cmd, *extra_args, cmm_file.name]
        res = subprocess.run(
            cli_cmd,
            cwd=str(ERRORS_TEST_DIR),
            input="" if code == "R008" else None,
            capture_output=True,
            text=True,
        )

        assert res.returncode != 0, f"{code} did not fail!"
        err_file.write_text(res.stderr, encoding="utf-8")
        print(f"Generated test for {code} -> {cmm_file.name}")


if __name__ == "__main__":
    main()
