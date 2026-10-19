"""Tests for the C-- interpreter per Section 7, 8, 10.6, 12.7, and Section 14."""

import io
import pytest

from cmm.errors import CmmRuntimeError
from cmm.interpreter import run
from cmm.lexer import normalize_source, tokenize
from cmm.parser import parse


def execute_src(source: str, max_steps: int | None = None) -> str:
    """Helper to run a C-- source program and return its stdout output string."""
    norm = normalize_source(source)
    tokens = tokenize(norm)
    prog = parse(tokens)
    out = io.StringIO()
    run(prog, out, max_steps=max_steps)
    return out.getvalue()


# ============================================================================
# 1. Operators & Int/Float mixing (§7.2, §7.3)
# ============================================================================

def test_operators_basic() -> None:
    src = """
    module main;
    fn main() {
        print(7 + 3);
        print(7 - 10);
        print(7 * 3);
        print(8 / 2);
        print(8 % 3);
        print(-5);
        print(!true);
        print(true && true);
        print(false || true);
    }
    """
    out = execute_src(src)
    assert out == "10\n-3\n21\n4\n2\n-5\nfalse\ntrue\ntrue\n"


def test_int_float_mixing_arithmetic() -> None:
    src = """
    module main;
    fn main() {
        print(1 + 2.5);
        print(10.0 - 4);
        print(3 * 1.5);
        print(10 / 4.0);
    }
    """
    out = execute_src(src)
    assert out == "3.5\n6.0\n4.5\n2.5\n"


def test_int_float_mixing_comparisons() -> None:
    src = """
    module main;
    fn main() {
        print(3 == 3.0);
        print(3 != 3.5);
        print(3 < 4.0);
        print(3.0 < 4);
        print(5.0 >= 5);
        print(4.5 <= 5);
    }
    """
    out = execute_src(src)
    assert out == "true\ntrue\ntrue\ntrue\ntrue\ntrue\n"


# ============================================================================
# 2. Truncating division and modulo across all 4 sign combinations (§7.3)
# ============================================================================

def test_truncating_division_four_signs() -> None:
    src = """
    module main;
    fn main() {
        print(7 / 2);
        print(-7 / 2);
        print(7 / -2);
        print(-7 / -2);
    }
    """
    out = execute_src(src)
    assert out == "3\n-3\n-3\n3\n"


def test_modulo_four_signs() -> None:
    src = """
    module main;
    fn main() {
        print(7 % 3);
        print(-7 % 3);
        print(7 % -3);
        print(-7 % -3);
    }
    """
    out = execute_src(src)
    assert out == "1\n-1\n1\n-1\n"


# ============================================================================
# 3. 64-bit Integer Boundaries and Overflows (R001) (§7.3, §10.6)
# ============================================================================

def test_integer_boundary_values() -> None:
    src = """
    module main;
    fn main() {
        print(9223372036854775807);
        print(-9223372036854775807 - 1);
    }
    """
    out = execute_src(src)
    assert out == "9223372036854775807\n-9223372036854775808\n"


def test_r001_integer_overflow_addition() -> None:
    src = """module main;
fn main() {
    let max = 9223372036854775807;
    let overflow = max + 1;
}
"""
    with pytest.raises(CmmRuntimeError) as exc_info:
        execute_src(src)
    assert exc_info.value.code == "R001"
    assert exc_info.value.message == "integer overflow"
    assert exc_info.value.line == 4 and exc_info.value.col == 24  # '+' position


def test_r001_integer_overflow_subtraction() -> None:
    src = """module main;
fn main() {
    let min = -9223372036854775807 - 1;
    let underflow = min - 1;
}
"""
    with pytest.raises(CmmRuntimeError) as exc_info:
        execute_src(src)
    assert exc_info.value.code == "R001"
    assert exc_info.value.message == "integer overflow"


def test_r001_integer_overflow_multiplication() -> None:
    src = """module main;
fn main() {
    let big = 9223372036854775807;
    let mul = big * 2;
}
"""
    with pytest.raises(CmmRuntimeError) as exc_info:
        execute_src(src)
    assert exc_info.value.code == "R001"
    assert exc_info.value.message == "integer overflow"


def test_r001_integer_overflow_unary_negation() -> None:
    src = """module main;
fn main() {
    let min = -9223372036854775807 - 1;
    let neg = -min;
}
"""
    with pytest.raises(CmmRuntimeError) as exc_info:
        execute_src(src)
    assert exc_info.value.code == "R001"
    assert exc_info.value.message == "integer overflow"


def test_r001_min_int_divided_by_minus_one() -> None:
    src = """module main;
fn main() {
    let min = -9223372036854775807 - 1;
    let res = min / -1;
}
"""
    with pytest.raises(CmmRuntimeError) as exc_info:
        execute_src(src)
    assert exc_info.value.code == "R001"
    assert exc_info.value.message == "integer overflow"


def test_min_int_modulo_minus_one_defined_zero() -> None:
    # Per §7.3: -9223372036854775808 % -1 is defined as 0 (no error)
    src = """
    module main;
    fn main() {
        let min = -9223372036854775807 - 1;
        let res = min % -1;
        print(res);
    }
    """
    out = execute_src(src)
    assert out == "0\n"


# ============================================================================
# 4. Division / Modulo by Zero (R002, R003) and Float Overflow (R004)
# ============================================================================

def test_r002_integer_division_by_zero() -> None:
    src = """module main;
fn main() {
    let x = 10 / 0;
}
"""
    with pytest.raises(CmmRuntimeError) as exc_info:
        execute_src(src)
    assert exc_info.value.code == "R002"
    assert exc_info.value.message == "division by zero"
    assert exc_info.value.line == 3 and exc_info.value.col == 16


def test_r002_float_division_by_zero() -> None:
    src = """module main;
fn main() {
    let x = 10.0 / 0.0;
}
"""
    with pytest.raises(CmmRuntimeError) as exc_info:
        execute_src(src)
    assert exc_info.value.code == "R002"
    assert exc_info.value.message == "division by zero"


def test_r002_float_zero_divided_by_zero() -> None:
    # 0.0 / 0.0 must raise R002 division by zero before dividing (NaN never appears)
    src = """module main;
fn main() {
    let x = 0.0 / 0.0;
}
"""
    with pytest.raises(CmmRuntimeError) as exc_info:
        execute_src(src)
    assert exc_info.value.code == "R002"
    assert exc_info.value.message == "division by zero"


def test_r002_float_division_by_negative_zero() -> None:
    src = """module main;
fn main() {
    let x = 5.0 / -0.0;
}
"""
    with pytest.raises(CmmRuntimeError) as exc_info:
        execute_src(src)
    assert exc_info.value.code == "R002"
    assert exc_info.value.message == "division by zero"


def test_r003_integer_modulo_by_zero() -> None:
    src = """module main;
fn main() {
    let x = 10 % 0;
}
"""
    with pytest.raises(CmmRuntimeError) as exc_info:
        execute_src(src)
    assert exc_info.value.code == "R003"
    assert exc_info.value.message == "modulo by zero"
    assert exc_info.value.line == 3 and exc_info.value.col == 16


def test_r004_float_overflow() -> None:
    src = """module main;
fn main() {
    let x = 1.0e308 * 10.0;
}
"""
    with pytest.raises(CmmRuntimeError) as exc_info:
        execute_src(src)
    assert exc_info.value.code == "R004"
    assert exc_info.value.message == "float overflow"
    assert exc_info.value.line == 3 and exc_info.value.col == 21


# ============================================================================
# 5. Short-circuit Evaluation (§7.1, §7.4)
# ============================================================================

def test_short_circuit_and() -> None:
    # If left operand is false, right operand (which would divide by zero) must NOT run
    src = """
    module main;
    fn main() {
        let res = false && (10 / 0 == 0);
        print(res);
    }
    """
    out = execute_src(src)
    assert out == "false\n"


def test_short_circuit_or() -> None:
    # If left operand is true, right operand (which would divide by zero) must NOT run
    src = """
    module main;
    fn main() {
        let res = true || (10 / 0 == 0);
        print(res);
    }
    """
    out = execute_src(src)
    assert out == "true\n"


# ============================================================================
# 6. Compound Assignments (§6.3)
# ============================================================================

def test_compound_assignments_execution() -> None:
    src = """
    module main;
    fn main() {
        mut a = 10;
        a += 5;
        print(a);
        a -= 3;
        print(a);
        a *= 2;
        print(a);
        a /= 4;
        print(a);
        a %= 4;
        print(a);
    }
    """
    out = execute_src(src)
    assert out == "15\n12\n24\n6\n2\n"


def test_compound_assignment_overflow_r001() -> None:
    src = """module main;
fn main() {
    mut x = 9223372036854775807;
    x += 1;
}
"""
    with pytest.raises(CmmRuntimeError) as exc_info:
        execute_src(src)
    assert exc_info.value.code == "R001"
    assert exc_info.value.message == "integer overflow"
    assert exc_info.value.line == 4 and exc_info.value.col == 7  # '+=' position


# ============================================================================
# 7. Control Flow & Loops (§8)
# ============================================================================

def test_while_loop() -> None:
    src = """
    module main;
    fn main() {
        mut n = 3;
        while (n > 0) {
            print(n);
            n -= 1;
        }
    }
    """
    out = execute_src(src)
    assert out == "3\n2\n1\n"


def test_do_while_loop_runs_at_least_once() -> None:
    src = """
    module main;
    fn main() {
        mut k = 10;
        do {
            print(k);
            k += 1;
        } while (k < 10);
        print(k);
    }
    """
    out = execute_src(src)
    assert out == "10\n11\n"


def test_for_loop_full() -> None:
    src = """
    module main;
    fn main() {
        mut sum = 0;
        for (mut i = 1; i <= 5; i += 1) {
            sum += i;
        }
        print(sum);
    }
    """
    out = execute_src(src)
    assert out == "15\n"


def test_for_loop_fresh_scope_per_iteration() -> None:
    src = """
    module main;
    fn main() {
        for (mut i = 0; i < 3; i += 1) {
            let iter_val = i * 10;
            print(iter_val);
        }
    }
    """
    out = execute_src(src)
    assert out == "0\n10\n20\n"


def test_if_else_chain() -> None:
    src = """
    module main;
    fn main() {
        mut x = 2;
        if (x == 1) {
            print("one");
        } else if (x == 2) {
            print("two");
        } else {
            print("other");
        }
    }
    """
    out = execute_src(src)
    assert out == "two\n"


# ============================================================================
# 8. Step Limit Bounds (R005) (§10.6)
# ============================================================================

def test_r005_step_limit_while_loop() -> None:
    src = """module main;
fn main() {
    while (true) {}
}
"""
    with pytest.raises(CmmRuntimeError) as exc_info:
        execute_src(src, max_steps=10)
    assert exc_info.value.code == "R005"
    assert exc_info.value.message == "step limit exceeded (10 steps)"
    assert exc_info.value.line == 3 and exc_info.value.col == 5  # 'while' position


def test_r005_step_limit_for_loop() -> None:
    src = """module main;
fn main() {
    for (;;) {}
}
"""
    with pytest.raises(CmmRuntimeError) as exc_info:
        execute_src(src, max_steps=5)
    assert exc_info.value.code == "R005"
    assert exc_info.value.message == "step limit exceeded (5 steps)"


# ============================================================================
# 9. Normative Examples from Section 17.1
# ============================================================================

def test_normative_hello() -> None:
    src = """module main;
fn main() {
    print("Hello, C--!");
}
"""
    assert execute_src(src) == "Hello, C--!\n"


def test_normative_variables() -> None:
    src = """module main;
fn main() {
    let a = 5;
    mut b = a;
    b = b + 1;
    print(a);
    print(b);
    {
        let a = "inner";
        print(a);
    }
    print(a);
    let s = "hi";
    print(s == "hi");
    print(s != "ho");
}
"""
    expected = "5\n6\ninner\n5\ntrue\ntrue\n"
    assert execute_src(src) == expected


def test_normative_scoping() -> None:
    src = """module main;
fn main() {
    let x = 1;
    {
        let x = x + 1;
        print(x);
    }
    print(x);
}
"""
    expected = "2\n1\n"
    assert execute_src(src) == expected


def test_normative_factorial() -> None:
    src = """module main;
fn main() {
    mut f = 1;
    for (mut i = 1; i <= 20; i += 1) {
        f *= i;
    }
    print(f);
}
"""
    expected = "2432902008176640000\n"
    assert execute_src(src) == expected


def test_normative_fibonacci() -> None:
    src = """module main;
fn main() {
    mut a = 0;
    mut b = 1;
    for (mut i = 0; i < 10; i += 1) {
        print(a);
        let next = a + b;
        a = b;
        b = next;
    }
}
"""
    expected = "0\n1\n1\n2\n3\n5\n8\n13\n21\n34\n"
    assert execute_src(src) == expected


def test_normative_floats() -> None:
    src = """module main;
fn main() {
    print(2.0);
    print(0.1 + 0.2);
    print(1.0 / 3.0);
    print(1000000.0 * 10000000000.0);
    print(0.00001);
    print(-0.0);
    print(5 / 2.0);
    print(100.0);
}
"""
    expected = (
        "2.0\n"
        "0.30000000000000004\n"
        "0.3333333333333333\n"
        "1.0e+16\n"
        "1.0e-05\n"
        "-0.0\n"
        "2.5\n"
        "100.0\n"
    )
    assert execute_src(src) == expected


def test_normative_prime_check() -> None:
    src = """module main;
fn main() {
    for (mut n = 2; n <= 20; n += 1) {
        mut is_prime = true;
        mut d = 2;
        while (d * d <= n) {
            if (n % d == 0) {
                is_prime = false;
            }
            d += 1;
        }
        if (is_prime) {
            print(n);
        }
    }
}
"""
    expected = "2\n3\n5\n7\n11\n13\n17\n19\n"
    assert execute_src(src) == expected


# ============================================================================
# 10. Additional Operator, Boundary, and Type tests
# ============================================================================

def test_string_equality_identical() -> None:
    src = """module main;
fn main() {
    let s1 = "abc";
    let s2 = "abc";
    let s3 = "def";
    print(s1 == s2);
    print(s1 != s3);
}
"""
    assert execute_src(src) == "true\ntrue\n"


def test_nested_blocks_scopes() -> None:
    src = """module main;
fn main() {
    mut x = 1;
    {
        mut y = 2;
        {
            x += y;
        }
    }
    print(x);
}
"""
    assert execute_src(src) == "3\n"


def test_for_loop_with_assignment_init() -> None:
    src = """module main;
fn main() {
    mut i = 0;
    for (i = 5; i > 0; i -= 1) {}
    print(i);
}
"""
    assert execute_src(src) == "0\n"


def test_for_loop_no_update() -> None:
    src = """module main;
fn main() {
    mut i = 0;
    for (mut j = 0; j < 3;) {
        j += 1;
        i += j;
    }
    print(i);
}
"""
    assert execute_src(src) == "6\n"


def test_do_while_multiple_iterations() -> None:
    src = """module main;
fn main() {
    mut count = 0;
    do {
        count += 1;
    } while (count < 5);
    print(count);
}
"""
    assert execute_src(src) == "5\n"


def test_boolean_never_behaves_as_int() -> None:
    src = """module main;
fn main() {
    let b = true;
    print(b);
    let s = false;
    print(s);
}
"""
    assert execute_src(src) == "true\nfalse\n"


def test_unary_not_operator() -> None:
    src = """module main;
fn main() {
    print(!true);
    print(!false);
    print(!!true);
}
"""
    assert execute_src(src) == "false\ntrue\ntrue\n"


def test_relational_comparisons_int() -> None:
    src = """module main;
fn main() {
    print(1 < 2);
    print(2 <= 2);
    print(3 > 4);
    print(4 >= 5);
}
"""
    assert execute_src(src) == "true\ntrue\nfalse\nfalse\n"


def test_relational_comparisons_float() -> None:
    src = """module main;
fn main() {
    print(1.5 < 2.5);
    print(2.5 <= 2.5);
    print(3.5 > 4.5);
    print(4.5 >= 5.5);
}
"""
    assert execute_src(src) == "true\ntrue\nfalse\nfalse\n"


def test_float_arithmetic_operations() -> None:
    src = """module main;
fn main() {
    print(1.5 + 2.5);
    print(5.5 - 2.0);
    print(2.5 * 4.0);
}
"""
    assert execute_src(src) == "4.0\n3.5\n10.0\n"


def test_float_unary_negation() -> None:
    src = """module main;
fn main() {
    let x = 2.5;
    print(-x);
    let z = 0.0;
    print(-z);
}
"""
    assert execute_src(src) == "-2.5\n-0.0\n"


def test_compound_division_overflow_r001() -> None:
    src = """module main;
fn main() {
    mut min = -9223372036854775807 - 1;
    min /= -1;
}
"""
    with pytest.raises(CmmRuntimeError) as exc_info:
        execute_src(src)
    assert exc_info.value.code == "R001"
    assert exc_info.value.message == "integer overflow"


def test_compound_division_by_zero_r002() -> None:
    src = """module main;
fn main() {
    mut x = 10;
    x /= 0;
}
"""
    with pytest.raises(CmmRuntimeError) as exc_info:
        execute_src(src)
    assert exc_info.value.code == "R002"
    assert exc_info.value.message == "division by zero"


def test_compound_modulo_by_zero_r003() -> None:
    src = """module main;
fn main() {
    mut x = 10;
    x %= 0;
}
"""
    with pytest.raises(CmmRuntimeError) as exc_info:
        execute_src(src)
    assert exc_info.value.code == "R003"
    assert exc_info.value.message == "modulo by zero"


def test_r005_step_limit_do_while() -> None:
    src = """module main;
fn main() {
    do {} while (true);
}
"""
    with pytest.raises(CmmRuntimeError) as exc_info:
        execute_src(src, max_steps=10)
    assert exc_info.value.code == "R005"
    assert exc_info.value.message == "step limit exceeded (10 steps)"

