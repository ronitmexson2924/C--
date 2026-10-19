"""Tests for the C-- lexer, token definitions, and error formatting."""

import pytest

from cmm.errors import LexError, format_error
from cmm.lexer import normalize_source, tokenize
from cmm.tokens import KEYWORDS, RESERVED_WORDS, TokenType


# ============================================================================
# 1. Normalization & BOM handling (§2.3, §2.4)
# ============================================================================

def test_normalize_bom_removal() -> None:
    raw = "\ufeffmodule main;\n"
    norm = normalize_source(raw)
    assert norm == "module main;\n"


def test_normalize_crlf_and_lone_cr() -> None:
    raw = "let x = 1;\r\nlet y = 2;\rlet z = 3;\n"
    norm = normalize_source(raw)
    assert norm == "let x = 1;\nlet y = 2;\nlet z = 3;\n"


# ============================================================================
# 2. EOF position tracking (§2.6)
# ============================================================================

def test_eof_empty_file() -> None:
    tokens = tokenize("")
    assert len(tokens) == 1
    eof = tokens[0]
    assert eof.type == TokenType.EOF
    assert eof.lexeme == ""
    assert eof.line == 1
    assert eof.col == 1


def test_eof_trailing_newline() -> None:
    tokens = tokenize("let a = 1;\n")
    eof = tokens[-1]
    assert eof.type == TokenType.EOF
    assert eof.line == 2
    assert eof.col == 1


def test_eof_no_trailing_newline() -> None:
    tokens = tokenize("let a = 1;")
    eof = tokens[-1]
    assert eof.type == TokenType.EOF
    assert eof.line == 1
    assert eof.col == 11


# ============================================================================
# 3. Position tracking and Tab handling (§2.5)
# ============================================================================

def test_position_tracking_with_tabs() -> None:
    # \t counts as exactly 1 column
    tokens = tokenize("\tlet\tfoo")
    assert tokens[0].type == TokenType.LET
    assert tokens[0].line == 1
    assert tokens[0].col == 2  # after 1 tab (col 1)

    assert tokens[1].type == TokenType.IDENT
    assert tokens[1].line == 1
    assert tokens[1].col == 6  # col 2 + 3 chars of 'let' + 1 tab = 6


def test_multiline_positions() -> None:
    tokens = tokenize("let\n  x\n    = 5;")
    assert tokens[0].line == 1 and tokens[0].col == 1  # let
    assert tokens[1].line == 2 and tokens[1].col == 3  # x
    assert tokens[2].line == 3 and tokens[2].col == 5  # =
    assert tokens[3].line == 3 and tokens[3].col == 7  # 5
    assert tokens[4].line == 3 and tokens[4].col == 8  # ;


# ============================================================================
# 4. Comments (§3.2)
# ============================================================================

def test_line_comment() -> None:
    tokens = tokenize("// this is a comment\nlet x = 10; // inline comment")
    assert [t.type for t in tokens] == [
        TokenType.LET,
        TokenType.IDENT,
        TokenType.EQ,
        TokenType.INT,
        TokenType.SEMI,
        TokenType.EOF,
    ]


def test_block_comment() -> None:
    tokens = tokenize("let /* block */ x = /* multi\nline */ 20;")
    assert [t.type for t in tokens] == [
        TokenType.LET,
        TokenType.IDENT,
        TokenType.EQ,
        TokenType.INT,
        TokenType.SEMI,
        TokenType.EOF,
    ]
    # Check that position of '20' is line 2 col 9
    assert tokens[3].line == 2
    assert tokens[3].col == 9


# ============================================================================
# 5. Keywords vs Reserved Words vs Identifiers (§3.3, §3.4)
# ============================================================================

def test_all_active_keywords() -> None:
    for kw, expected_type in KEYWORDS.items():
        tokens = tokenize(kw)
        assert len(tokens) == 2
        assert tokens[0].type == expected_type
        assert tokens[0].lexeme == kw
        assert tokens[0].value is None


def test_all_reserved_words() -> None:
    for rw in RESERVED_WORDS:
        tokens = tokenize(rw)
        assert len(tokens) == 2
        assert tokens[0].type == TokenType.RESERVED
        assert tokens[0].lexeme == rw
        assert tokens[0].value is None


def test_identifiers() -> None:
    samples = ["x", "_", "_foo", "foo123", "CamelCase", "main_not_keyword"]
    for s in samples:
        tokens = tokenize(s)
        assert tokens[0].type == TokenType.IDENT
        assert tokens[0].lexeme == s


# ============================================================================
# 6. Literals: Integers, Floats, Strings, Booleans (§3.5)
# ============================================================================

def test_integer_literals() -> None:
    tokens = tokenize("0 1 42 9223372036854775807")
    expected = [0, 1, 42, 9223372036854775807]
    int_tokens = [t for t in tokens if t.type == TokenType.INT]
    assert [t.value for t in int_tokens] == expected


def test_float_literals() -> None:
    samples = [
        ("0.5", 0.5),
        ("3.14", 3.14),
        ("2.0", 2.0),
        ("1.5e10", 1.5e10),
        ("2.0E-3", 2.0e-3),
        ("0.05", 0.05),
        ("1.0e+16", 1.0e16),
    ]
    for text, expected in samples:
        tokens = tokenize(text)
        assert tokens[0].type == TokenType.FLOAT
        assert tokens[0].value == expected


def test_string_literals_and_escapes() -> None:
    tokens = tokenize(r'"" "hello world" "line1\nline2\ttab\r\"quote\\backslash"')
    assert tokens[0].type == TokenType.STRING and tokens[0].value == ""
    assert tokens[1].type == TokenType.STRING and tokens[1].value == "hello world"
    assert tokens[2].type == TokenType.STRING and tokens[2].value == 'line1\nline2\ttab\r"quote\\backslash'


def test_string_unicode_content() -> None:
    tokens = tokenize('"こんにちは 🚀"')
    assert tokens[0].type == TokenType.STRING
    assert tokens[0].value == "こんにちは 🚀"


# ============================================================================
# 7. Operators and Punctuation (§3.6, §3.8)
# ============================================================================

def test_all_operators_and_punctuation() -> None:
    src = "+ - * / % = == ! != < <= > >= && || += -= *= /= %= ( ) { } ;"
    tokens = tokenize(src)
    expected_types = [
        TokenType.PLUS,
        TokenType.MINUS,
        TokenType.STAR,
        TokenType.SLASH,
        TokenType.PERCENT,
        TokenType.EQ,
        TokenType.EQEQ,
        TokenType.BANG,
        TokenType.BANGEQ,
        TokenType.LT,
        TokenType.LTEQ,
        TokenType.GT,
        TokenType.GTEQ,
        TokenType.ANDAND,
        TokenType.OROR,
        TokenType.PLUSEQ,
        TokenType.MINUSEQ,
        TokenType.STAREQ,
        TokenType.SLASHEQ,
        TokenType.PERCENTEQ,
        TokenType.LPAREN,
        TokenType.RPAREN,
        TokenType.LBRACE,
        TokenType.RBRACE,
        TokenType.SEMI,
        TokenType.EOF,
    ]
    assert [t.type for t in tokens] == expected_types


# ============================================================================
# 8. Lexical Errors L001 - L012 (§10.3)
# ============================================================================

def test_error_l001_unexpected_character() -> None:
    with pytest.raises(LexError) as exc_info:
        tokenize("@")
    assert exc_info.value.code == "L001"
    assert exc_info.value.message == "unexpected character '@'"
    assert exc_info.value.line == 1 and exc_info.value.col == 1


def test_error_l001_control_character() -> None:
    with pytest.raises(LexError) as exc_info:
        tokenize("\0")
    assert exc_info.value.code == "L001"
    assert exc_info.value.message == "unexpected character 'U+0000'"


def test_error_l002_unterminated_string_newline() -> None:
    with pytest.raises(LexError) as exc_info:
        tokenize('"hello\nworld"')
    assert exc_info.value.code == "L002"
    assert exc_info.value.message == "unterminated string literal"
    assert exc_info.value.line == 1 and exc_info.value.col == 1


def test_error_l002_unterminated_string_eof() -> None:
    with pytest.raises(LexError) as exc_info:
        tokenize('"unterminated')
    assert exc_info.value.code == "L002"
    assert exc_info.value.message == "unterminated string literal"


def test_error_l002_string_backslash_newline() -> None:
    with pytest.raises(LexError) as exc_info:
        tokenize('  "abc\\\n"')
    assert exc_info.value.code == "L002"
    assert exc_info.value.message == "unterminated string literal"
    # Position must be at opening quote (col 3)
    assert exc_info.value.line == 1 and exc_info.value.col == 3


def test_error_l003_invalid_escape_sequence() -> None:
    with pytest.raises(LexError) as exc_info:
        tokenize('"bad escape \\x"')
    assert exc_info.value.code == "L003"
    assert exc_info.value.message == "invalid escape sequence '\\x'"
    # Position must be at the backslash
    assert exc_info.value.line == 1 and exc_info.value.col == 13


def test_error_l004_unterminated_block_comment() -> None:
    with pytest.raises(LexError) as exc_info:
        tokenize("/* start comment without end")
    assert exc_info.value.code == "L004"
    assert exc_info.value.message == "unterminated block comment"
    assert exc_info.value.line == 1 and exc_info.value.col == 1


def test_error_l004_unterminated_block_comment_reused_slash() -> None:
    with pytest.raises(LexError) as exc_info:
        tokenize("/*/")
    assert exc_info.value.code == "L004"
    assert exc_info.value.message == "unterminated block comment"


def test_error_l005_integer_overflow() -> None:
    with pytest.raises(LexError) as exc_info:
        tokenize("9223372036854775808")
    assert exc_info.value.code == "L005"
    assert exc_info.value.message == "integer literal out of range"
    assert exc_info.value.line == 1 and exc_info.value.col == 1


def test_error_l006_float_overflow() -> None:
    with pytest.raises(LexError) as exc_info:
        tokenize("1.0e400")
    assert exc_info.value.code == "L006"
    assert exc_info.value.message == "float literal out of range"
    assert exc_info.value.line == 1 and exc_info.value.col == 1


def test_error_l007_invalid_number_trailing_dot() -> None:
    with pytest.raises(LexError) as exc_info:
        tokenize("1.")
    assert exc_info.value.code == "L007"
    assert exc_info.value.message == "invalid number literal"


def test_error_l007_invalid_number_exponent_without_fraction() -> None:
    with pytest.raises(LexError) as exc_info:
        tokenize("1e10")
    assert exc_info.value.code == "L007"
    assert exc_info.value.message == "invalid number literal"


def test_error_l007_invalid_number_missing_exponent_digits() -> None:
    with pytest.raises(LexError) as exc_info:
        tokenize("1.5e")
    assert exc_info.value.code == "L007"
    assert exc_info.value.message == "invalid number literal"


def test_error_l007_invalid_number_letter_suffix() -> None:
    with pytest.raises(LexError) as exc_info:
        tokenize("42abc")
    assert exc_info.value.code == "L007"
    assert exc_info.value.message == "invalid number literal"


def test_error_l008_leading_zeros() -> None:
    with pytest.raises(LexError) as exc_info:
        tokenize("0123")
    assert exc_info.value.code == "L008"
    assert exc_info.value.message == "leading zeros are not allowed in number literals"
    assert exc_info.value.line == 1 and exc_info.value.col == 1


def test_error_l008_leading_zeros_double_zero() -> None:
    with pytest.raises(LexError) as exc_info:
        tokenize("00")
    assert exc_info.value.code == "L008"
    assert exc_info.value.message == "leading zeros are not allowed in number literals"


def test_error_l009_plus_plus() -> None:
    with pytest.raises(LexError) as exc_info:
        tokenize("x++")
    assert exc_info.value.code == "L009"
    assert exc_info.value.message == "'++' is not supported; use '+= 1'"
    assert exc_info.value.line == 1 and exc_info.value.col == 2


def test_error_l010_minus_minus() -> None:
    with pytest.raises(LexError) as exc_info:
        tokenize("x--")
    assert exc_info.value.code == "L010"
    assert exc_info.value.message == "'--' is not supported; use '-= 1'"
    assert exc_info.value.line == 1 and exc_info.value.col == 2


def test_error_l011_single_ampersand() -> None:
    with pytest.raises(LexError) as exc_info:
        tokenize("a & b")
    assert exc_info.value.code == "L011"
    assert exc_info.value.message == "single '&' is not supported; did you mean '&&'?"
    assert exc_info.value.line == 1 and exc_info.value.col == 3


def test_error_l012_single_pipe() -> None:
    with pytest.raises(LexError) as exc_info:
        tokenize("a | b")
    assert exc_info.value.code == "L012"
    assert exc_info.value.message == "single '|' is not supported; did you mean '||'?"
    assert exc_info.value.line == 1 and exc_info.value.col == 3


# ============================================================================
# 9. Error formatting (§10.1)
# ============================================================================

def test_format_error_spaces() -> None:
    err = LexError("L001", "unexpected character '@'", 2, 5)
    source_lines = ["module main;", "    @"]
    out = format_error(err, "test.cmm", source_lines)
    expected = (
        "test.cmm:2:5: lexical error: unexpected character '@'\n"
        "        @\n"
        "        ^\n"
    )
    assert out == expected


def test_format_error_tabs() -> None:
    err = LexError("L001", "unexpected character '@'", 1, 3)
    source_lines = ["\t\t@"]
    out = format_error(err, "test.cmm", source_lines)
    expected = (
        "test.cmm:1:3: lexical error: unexpected character '@'\n"
        "    \t\t@\n"
        "    \t\t^\n"
    )
    assert out == expected


def test_format_error_missing_line_at_eof() -> None:
    err = LexError("L002", "unterminated string literal", 5, 1)
    source_lines = ["line 1", "line 2"]
    out = format_error(err, "test.cmm", source_lines)
    expected = (
        "test.cmm:5:1: lexical error: unterminated string literal\n"
        "    \n"
        "    ^\n"
    )
    assert out == expected
