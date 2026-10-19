"""Tests for C-- semantic analysis, type checking, and scope rules per Section 14."""

from cmm.analyzer import analyze
from cmm.ast_nodes import Program
from cmm.errors import SemanticError
from cmm.lexer import normalize_source, tokenize
from cmm.parser import parse


def analyze_src(source: str) -> list[SemanticError]:
    """Helper to parse and analyze C-- source code."""
    norm = normalize_source(source)
    tokens = tokenize(norm)
    prog = parse(tokens)
    return analyze(prog)


# ============================================================================
# 1. Valid operator typing table cases (§7.2)
# ============================================================================

def test_valid_binary_arithmetic() -> None:
    src = """
    module main;
    fn main() {
        let a = 1 + 2;
        let b = 1.0 + 2.0;
        let c = 1 + 2.0;
        let d = 1.0 + 2;

        let s1 = 10 - 2;
        let s2 = 10.0 - 2.0;
        let s3 = 10 - 2.0;
        let s4 = 10.0 - 2;

        let m1 = 3 * 4;
        let m2 = 3.0 * 4.0;
        let m3 = 3 * 4.0;
        let m4 = 3.0 * 4;

        let d1 = 8 / 2;
        let d2 = 8.0 / 2.0;
        let d3 = 8 / 2.0;
        let d4 = 8.0 / 2;

        let rem = 7 % 3;
    }
    """
    errors = analyze_src(src)
    assert errors == []


def test_valid_comparisons() -> None:
    src = """
    module main;
    fn main() {
        let c1 = 1 < 2;
        let c2 = 1.0 < 2.0;
        let c3 = 1 < 2.0;
        let c4 = 1.0 < 2;

        let c5 = 1 <= 2;
        let c6 = 1.0 <= 2.0;
        let c7 = 1 <= 2.0;
        let c8 = 1.0 <= 2;

        let c9 = 1 > 2;
        let c10 = 1.0 > 2.0;
        let c11 = 1 > 2.0;
        let c12 = 1.0 > 2;

        let c13 = 1 >= 2;
        let c14 = 1.0 >= 2.0;
        let c15 = 1 >= 2.0;
        let c16 = 1.0 >= 2;

        let eq1 = 1 == 2;
        let eq2 = 1.0 == 2.0;
        let eq3 = 1 == 2.0;
        let eq4 = 1.0 == 2;
        let eq5 = true == false;
        let eq6 = "a" == "b";

        let neq1 = 1 != 2;
        let neq2 = 1.0 != 2.0;
        let neq3 = 1 != 2.0;
        let neq4 = 1.0 != 2;
        let neq5 = true != false;
        let neq6 = "a" != "b";
    }
    """
    errors = analyze_src(src)
    assert errors == []


def test_valid_logical_and_unary() -> None:
    src = """
    module main;
    fn main() {
        let b1 = true && false;
        let b2 = true || false;
        let b3 = !true;
        let u1 = -5;
        let u2 = -5.5;
    }
    """
    errors = analyze_src(src)
    assert errors == []


# ============================================================================
# 2. Invalid operator typing table cases (§7.2, E005, E006)
# ============================================================================

def test_invalid_modulo_on_float() -> None:
    src = "module main; fn main() { let x = 1.0 % 2; }"
    errors = analyze_src(src)
    assert len(errors) == 1
    assert errors[0].code == "E006"
    assert errors[0].message == "operator '%' cannot be applied to float and int"


def test_invalid_modulo_on_both_floats() -> None:
    src = "module main; fn main() { let x = 5.0 % 2.0; }"
    errors = analyze_src(src)
    assert len(errors) == 1
    assert errors[0].code == "E006"
    assert errors[0].message == "operator '%' cannot be applied to float and float"


def test_invalid_arithmetic_bool_string() -> None:
    src = 'module main; fn main() { let x = true + 1; let y = "a" * 2; }'
    errors = analyze_src(src)
    assert len(errors) == 2
    assert errors[0].code == "E006"
    assert errors[0].message == "operator '+' cannot be applied to bool and int"
    assert errors[1].code == "E006"
    assert errors[1].message == "operator '*' cannot be applied to string and int"


def test_invalid_relational_string() -> None:
    src = 'module main; fn main() { let x = "a" < "b"; }'
    errors = analyze_src(src)
    assert len(errors) == 1
    assert errors[0].code == "E006"
    assert errors[0].message == "operator '<' cannot be applied to string and string"


def test_invalid_equality_mismatched_types() -> None:
    src = 'module main; fn main() { let x = 1 == true; let y = "a" == 1; }'
    errors = analyze_src(src)
    assert len(errors) == 2
    assert errors[0].code == "E006"
    assert errors[0].message == "operator '==' cannot be applied to int and bool"
    assert errors[1].code == "E006"
    assert errors[1].message == "operator '==' cannot be applied to string and int"


def test_invalid_logical_operands() -> None:
    src = "module main; fn main() { let x = 1 && true; let y = false || 0; }"
    errors = analyze_src(src)
    assert len(errors) == 2
    assert errors[0].code == "E006"
    assert errors[0].message == "operator '&&' cannot be applied to int and bool"
    assert errors[1].code == "E006"
    assert errors[1].message == "operator '||' cannot be applied to bool and int"


def test_invalid_unary_bang_on_non_bool() -> None:
    src = "module main; fn main() { let x = !0; }"
    errors = analyze_src(src)
    assert len(errors) == 1
    assert errors[0].code == "E005"
    assert errors[0].message == "operator '!' cannot be applied to int"


def test_invalid_unary_minus_on_bool_and_string() -> None:
    src = 'module main; fn main() { let x = -true; let y = -"str"; }'
    errors = analyze_src(src)
    assert len(errors) == 2
    assert errors[0].code == "E005"
    assert errors[0].message == "operator '-' cannot be applied to bool"
    assert errors[1].code == "E005"
    assert errors[1].message == "operator '-' cannot be applied to string"


# ============================================================================
# 3. Scope and Variable Declaration Rules (§6.1, §6.2, E001, E002, E003)
# ============================================================================

def test_e001_undeclared_variable_in_expr() -> None:
    src = "module main;\nfn main() {\n    print(undeclared_var);\n}"
    errors = analyze_src(src)
    assert len(errors) == 1
    assert errors[0].code == "E001"
    assert errors[0].message == "undeclared variable 'undeclared_var'"
    assert errors[0].line == 3 and errors[0].col == 11


def test_e001_undeclared_variable_in_assign() -> None:
    src = "module main;\nfn main() {\n    target = 5;\n}"
    errors = analyze_src(src)
    assert len(errors) == 1
    assert errors[0].code == "E001"
    assert errors[0].message == "undeclared variable 'target'"
    assert errors[0].line == 3 and errors[0].col == 5


def test_e001_variable_not_visible_in_own_initializer() -> None:
    src = "module main;\nfn main() {\n    let x = x + 1;\n}"
    errors = analyze_src(src)
    assert len(errors) == 1
    assert errors[0].code == "E001"
    assert errors[0].message == "undeclared variable 'x'"
    assert errors[0].line == 3 and errors[0].col == 13


def test_initializer_sees_outer_variable_on_shadow() -> None:
    src = """
    module main;
    fn main() {
        let x = 1;
        {
            let x = x + 1;
            print(x);
        }
    }
    """
    errors = analyze_src(src)
    assert errors == []


def test_e002_redeclaration_same_scope() -> None:
    src = """module main;
fn main() {
    let a = 1;
    let a = 2;
}
"""
    errors = analyze_src(src)
    assert len(errors) == 1
    assert errors[0].code == "E002"
    assert errors[0].message == "variable 'a' is already declared in this scope (at line 3, column 9)"
    assert errors[0].line == 4 and errors[0].col == 9


def test_shadowing_in_inner_scope_allowed() -> None:
    src = """
    module main;
    fn main() {
        let a = 1;
        {
            let a = "shadowed";
            print(a);
        }
        print(a);
    }
    """
    errors = analyze_src(src)
    assert errors == []


def test_variable_out_of_scope_after_block() -> None:
    src = """module main;
fn main() {
    {
        let inner = 42;
    }
    print(inner);
}
"""
    errors = analyze_src(src)
    assert len(errors) == 1
    assert errors[0].code == "E001"
    assert errors[0].message == "undeclared variable 'inner'"
    assert errors[0].line == 6 and errors[0].col == 11


def test_e003_cannot_assign_to_immutable() -> None:
    src = """module main;
fn main() {
    let x = 10;
    x = 20;
}
"""
    errors = analyze_src(src)
    assert len(errors) == 1
    assert errors[0].code == "E003"
    assert errors[0].message == "cannot assign to immutable variable 'x' (declared with 'let' at line 3, column 9); declare it with 'mut' to allow assignment"
    assert errors[0].line == 4 and errors[0].col == 5


# ============================================================================
# 4. Condition Type Check (§8, E004)
# ============================================================================

def test_e004_condition_in_if() -> None:
    src = "module main;\nfn main() {\n    if (42) {}\n}"
    errors = analyze_src(src)
    assert len(errors) == 1
    assert errors[0].code == "E004"
    assert errors[0].message == "condition must be of type bool, found int"
    assert errors[0].line == 3 and errors[0].col == 9


def test_e004_condition_with_parentheses() -> None:
    src = "module main;\nfn main() {\n    if ((1 + 2)) {}\n}"
    errors = analyze_src(src)
    assert len(errors) == 1
    assert errors[0].code == "E004"
    assert errors[0].message == "condition must be of type bool, found int"
    # Position must be the first token of the condition expression, i.e. '(' at col 9
    assert errors[0].line == 3 and errors[0].col == 9


def test_e004_condition_in_while() -> None:
    src = "module main;\nfn main() {\n    while (\"str\") {}\n}"
    errors = analyze_src(src)
    assert len(errors) == 1
    assert errors[0].code == "E004"
    assert errors[0].message == "condition must be of type bool, found string"


def test_e004_condition_in_do_while() -> None:
    src = "module main;\nfn main() {\n    do {} while (3.14);\n}"
    errors = analyze_src(src)
    assert len(errors) == 1
    assert errors[0].code == "E004"
    assert errors[0].message == "condition must be of type bool, found float"


def test_e004_condition_in_for() -> None:
    src = "module main;\nfn main() {\n    for (; 100; ) {}\n}"
    errors = analyze_src(src)
    assert len(errors) == 1
    assert errors[0].code == "E004"
    assert errors[0].message == "condition must be of type bool, found int"


# ============================================================================
# 5. Assignment Type Check & Compound Assignment (§6.3, E007, E006)
# ============================================================================

def test_e007_simple_assignment_type_mismatch() -> None:
    src = "module main;\nfn main() {\n    mut i = 1;\n    i = 2.0;\n}"
    errors = analyze_src(src)
    assert len(errors) == 1
    assert errors[0].code == "E007"
    assert errors[0].message == "cannot assign value of type float to variable 'i' of type int"
    assert errors[0].line == 4 and errors[0].col == 5


def test_e007_compound_assignment_result_mismatch() -> None:
    # mut i = 1; i += 0.5 -> binary '+' on (int, float) yields float != int -> E007 (§6.3)
    src = "module main;\nfn main() {\n    mut i = 1;\n    i += 0.5;\n}"
    errors = analyze_src(src)
    assert len(errors) == 1
    assert errors[0].code == "E007"
    assert errors[0].message == "cannot assign value of type float to variable 'i' of type int"
    assert errors[0].line == 4 and errors[0].col == 5


def test_valid_compound_assignment_widening() -> None:
    # mut f = 1.0; f += 1 -> binary '+' on (float, int) yields float == float -> valid
    src = "module main;\nfn main() {\n    mut f = 1.0;\n    f += 1;\n}"
    errors = analyze_src(src)
    assert errors == []


def test_e006_compound_assignment_invalid_operator() -> None:
    src = 'module main;\nfn main() {\n    mut i = 1;\n    i += "hi";\n}'
    errors = analyze_src(src)
    assert len(errors) == 1
    assert errors[0].code == "E006"
    assert errors[0].message == "operator '+=' cannot be applied to int and string"
    assert errors[0].line == 4 and errors[0].col == 7  # position of '+='


# ============================================================================
# 6. Loop Scope Rules (§6.2)
# ============================================================================

def test_for_loop_scope_isolated() -> None:
    src = """module main;
fn main() {
    for (mut i = 0; i < 5; i += 1) {
        print(i);
    }
    print(i);
}
"""
    errors = analyze_src(src)
    assert len(errors) == 1
    assert errors[0].code == "E001"
    assert errors[0].message == "undeclared variable 'i'"
    assert errors[0].line == 6 and errors[0].col == 11


def test_for_body_can_shadow_loop_variable() -> None:
    src = """
    module main;
    fn main() {
        for (mut i = 0; i < 5; i += 1) {
            let i = "shadowed";
            print(i);
        }
    }
    """
    errors = analyze_src(src)
    assert errors == []


def test_do_while_condition_cannot_see_body_variables() -> None:
    src = """module main;
fn main() {
    do {
        let inside = true;
    } while (inside);
}
"""
    errors = analyze_src(src)
    assert len(errors) == 1
    assert errors[0].code == "E001"
    assert errors[0].message == "undeclared variable 'inside'"
    assert errors[0].line == 5 and errors[0].col == 14


# ============================================================================
# 7. Cascade Suppression and Error Ordering (§10.2, §10.5)
# ============================================================================

def test_cascade_suppression_undeclared_var() -> None:
    # undeclared 'x' produces E001; x + 1 does NOT produce E006; let y = (x + 1) does NOT produce further errors
    src = """module main;
fn main() {
    let y = x + 1;
    let z = y + 2;
}
"""
    errors = analyze_src(src)
    assert len(errors) == 1
    assert errors[0].code == "E001"
    assert errors[0].message == "undeclared variable 'x'"


def test_cascade_suppression_invalid_condition() -> None:
    # if (undeclared) should report E001 for undeclared, but NOT E004 for condition type
    src = """module main;
fn main() {
    if (undeclared) {
        print(1);
    }
}
"""
    errors = analyze_src(src)
    assert len(errors) == 1
    assert errors[0].code == "E001"
    assert errors[0].message == "undeclared variable 'undeclared'"


def test_cascade_suppression_both_binary_operands_analyzed() -> None:
    # let c = undeclared1 + undeclared2; should report E001 for both undeclared variables
    src = """module main;
fn main() {
    let c = undeclared1 + undeclared2;
}
"""
    errors = analyze_src(src)
    assert len(errors) == 2
    assert errors[0].code == "E001"
    assert errors[0].message == "undeclared variable 'undeclared1'"
    assert errors[1].code == "E001"
    assert errors[1].message == "undeclared variable 'undeclared2'"


def test_normative_semantic_multiple_example() -> None:
    # From Section 17.2 semantic_multiple.cmm
    src = """module main;
fn main() {
    let a = 1;
    a = 2;
    b = 3;
    let c = a + "x";
}
"""
    errors = analyze_src(src)
    assert len(errors) == 3

    assert errors[0].code == "E003"
    assert errors[0].message == "cannot assign to immutable variable 'a' (declared with 'let' at line 3, column 9); declare it with 'mut' to allow assignment"
    assert errors[0].line == 4 and errors[0].col == 5

    assert errors[1].code == "E001"
    assert errors[1].message == "undeclared variable 'b'"
    assert errors[1].line == 5 and errors[1].col == 5

    assert errors[2].code == "E006"
    assert errors[2].message == "operator '+' cannot be applied to int and string"
    assert errors[2].line == 6 and errors[2].col == 15


def test_normative_semantic_condition_example() -> None:
    # From Section 17.2 semantic_condition.cmm
    src = """module main;
fn main() {
    mut i = 0;
    while (i) {
        i = 0;
    }
}
"""
    errors = analyze_src(src)
    assert len(errors) == 1
    assert errors[0].code == "E004"
    assert errors[0].message == "condition must be of type bool, found int"
    assert errors[0].line == 4 and errors[0].col == 12


def test_invalid_string_equality_with_other_types() -> None:
    src = 'module main; fn main() { let e1 = "a" == true; let e2 = "a" == 1.0; }'
    errors = analyze_src(src)
    assert len(errors) == 2
    assert errors[0].code == "E006"
    assert errors[0].message == "operator '==' cannot be applied to string and bool"
    assert errors[1].code == "E006"
    assert errors[1].message == "operator '==' cannot be applied to string and float"


def test_compound_assign_to_immutable_e003() -> None:
    src = "module main;\nfn main() {\n    let count = 0;\n    count += 1;\n}"
    errors = analyze_src(src)
    assert len(errors) == 1
    assert errors[0].code == "E003"
    assert errors[0].message == "cannot assign to immutable variable 'count' (declared with 'let' at line 3, column 9); declare it with 'mut' to allow assignment"
    assert errors[0].line == 4 and errors[0].col == 5


def test_compound_assign_undeclared_e001() -> None:
    src = "module main;\nfn main() {\n    missing += 1;\n}"
    errors = analyze_src(src)
    assert len(errors) == 1
    assert errors[0].code == "E001"
    assert errors[0].message == "undeclared variable 'missing'"
    assert errors[0].line == 3 and errors[0].col == 5


def test_if_else_branches_isolated_scope() -> None:
    src = """module main;
fn main() {
    if (true) {
        let branch_var = 10;
    } else {
        print(branch_var);
    }
}
"""
    errors = analyze_src(src)
    assert len(errors) == 1
    assert errors[0].code == "E001"
    assert errors[0].message == "undeclared variable 'branch_var'"
    assert errors[0].line == 6 and errors[0].col == 15


def test_for_init_immutable_assign_e003() -> None:
    src = """module main;
fn main() {
    let i = 0;
    for (i = 1; i < 5; i += 1) {}
}
"""
    errors = analyze_src(src)
    assert len(errors) == 2
    assert errors[0].code == "E003"
    assert errors[0].line == 4 and errors[0].col == 10
    assert errors[1].code == "E003"
    assert errors[1].line == 4 and errors[1].col == 24


def test_error_sorting_by_line_and_col() -> None:
    src = """module main;
fn main() {
    print(z);
    let x = a + b;
    y = 1;
}
"""
    errors = analyze_src(src)
    # Errors: z (line 3 col 11), y (line 5 col 5), a (line 4 col 13), b (line 4 col 17)
    # Must be sorted by (line, col):
    # (3, 11), (4, 13), (4, 17), (5, 5)
    positions = [(e.line, e.col) for e in errors]
    assert positions == [(3, 11), (4, 13), (4, 17), (5, 5)]

