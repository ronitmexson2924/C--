"""Tests for C-- value and float output formatting per Section 9 and Section 14."""

from cmm.formatting import format_float, format_value


# ============================================================================
# 1. Spec table cases from Section 9.1
# ============================================================================

def test_format_float_2_0() -> None:
    assert format_float(2.0) == "2.0"


def test_format_float_0_5() -> None:
    assert format_float(0.5) == "0.5"


def test_format_float_100_0() -> None:
    assert format_float(100.0) == "100.0"


def test_format_float_addition_roundtrip() -> None:
    assert format_float(0.1 + 0.2) == "0.30000000000000004"


def test_format_float_one_third() -> None:
    assert format_float(1.0 / 3.0) == "0.3333333333333333"


def test_format_float_1234567_891() -> None:
    assert format_float(1234567.891) == "1234567.891"


def test_format_float_1e15() -> None:
    assert format_float(1e15) == "1000000000000000.0"


def test_format_float_1e16() -> None:
    assert format_float(1e16) == "1.0e+16"


def test_format_float_1_5e300() -> None:
    assert format_float(1.5e300) == "1.5e+300"


def test_format_float_0_0001() -> None:
    assert format_float(0.0001) == "0.0001"


def test_format_float_0_00001() -> None:
    assert format_float(0.00001) == "1.0e-05"


def test_format_float_large_precision() -> None:
    assert format_float(123456789012345680.0) == "1.2345678901234568e+17"


def test_format_float_positive_zero() -> None:
    assert format_float(0.0) == "0.0"


def test_format_float_negative_zero() -> None:
    assert format_float(-0.0) == "-0.0"


def test_format_float_negative_number() -> None:
    assert format_float(-2.5) == "-2.5"


# ============================================================================
# 2. Section 14 Boundary values
# ============================================================================

def test_format_float_boundary_1e15() -> None:
    assert format_float(1000000000000000.0) == "1000000000000000.0"


def test_format_float_boundary_1e16() -> None:
    assert format_float(10000000000000000.0) == "1.0e+16"


def test_format_float_boundary_1e_minus_4() -> None:
    assert format_float(1e-4) == "0.0001"


def test_format_float_boundary_1e_minus_5() -> None:
    assert format_float(1e-5) == "1.0e-05"


def test_format_float_boundary_min_subnormal() -> None:
    assert format_float(5e-324) == "5.0e-324"


def test_format_float_boundary_max_finite() -> None:
    assert format_float(1.7976931348623157e308) == "1.7976931348623157e+308"


def test_format_float_negative_scientific() -> None:
    assert format_float(-1e16) == "-1.0e+16"


# ============================================================================
# 3. format_value for all four types (§9)
# ============================================================================

def test_format_value_int() -> None:
    assert format_value(0) == "0"
    assert format_value(42) == "42"
    assert format_value(-99) == "-99"


def test_format_value_bool() -> None:
    assert format_value(True) == "true"
    assert format_value(False) == "false"


def test_format_value_string() -> None:
    assert format_value("Hello, World!") == "Hello, World!"
    assert format_value("Line 1\nLine 2") == "Line 1\nLine 2"


def test_format_value_float() -> None:
    assert format_value(2.0) == "2.0"
    assert format_value(-0.0) == "-0.0"
