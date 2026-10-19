"""Tests for C-- AST nodes, recursive descent parser, and astprint per Section 14."""

import pytest

from cmm.ast_nodes import (
    Assign,
    BinaryOp,
    Block,
    DoWhile,
    For,
    If,
    Literal,
    Print,
    Program,
    UnaryOp,
    VarDecl,
    Variable,
    While,
)
from cmm.astprint import format_ast, format_tokens
from cmm.errors import ParseError
from cmm.lexer import normalize_source, tokenize
from cmm.parser import parse


def parse_src(source: str) -> Program:
    """Helper to normalize, tokenize and parse C-- source."""
    norm = normalize_source(source)
    tokens = tokenize(norm)
    return parse(tokens)


# ============================================================================
# 1. Statements and Program Structure (§5.1, §5.2)
# ============================================================================

def test_parse_minimal_program() -> None:
    src = "module my_module;\nfn main() {}\n"
    prog = parse_src(src)
    assert prog.module_name == "my_module"
    assert len(prog.body.statements) == 0


def test_parse_var_decl_let_and_mut() -> None:
    src = "module main; fn main() { let x = 1; mut y = 2.5; }"
    prog = parse_src(src)
    stmts = prog.body.statements
    assert len(stmts) == 2
    assert isinstance(stmts[0], VarDecl)
    assert stmts[0].mutable is False
    assert stmts[0].name == "x"
    assert isinstance(stmts[0].init, Literal)
    assert stmts[0].init.value == 1

    assert isinstance(stmts[1], VarDecl)
    assert stmts[1].mutable is True
    assert stmts[1].name == "y"
    assert isinstance(stmts[1].init, Literal)
    assert stmts[1].init.value == 2.5


def test_parse_assignment_all_operators() -> None:
    src = """
    module main;
    fn main() {
        mut x = 10;
        x = 1;
        x += 2;
        x -= 3;
        x *= 4;
        x /= 5;
        x %= 6;
    }
    """
    prog = parse_src(src)
    stmts = prog.body.statements[1:]
    expected_ops = ["=", "+=", "-=", "*=", "/=", "%="]
    for stmt, expected_op in zip(stmts, expected_ops):
        assert isinstance(stmt, Assign)
        assert stmt.name == "x"
        assert stmt.op == expected_op


def test_parse_print_stmt() -> None:
    src = 'module main; fn main() { print("hello"); }'
    prog = parse_src(src)
    stmt = prog.body.statements[0]
    assert isinstance(stmt, Print)
    assert isinstance(stmt.expr, Literal)
    assert stmt.expr.type == "string"
    assert stmt.expr.value == "hello"


def test_parse_if_without_else() -> None:
    src = "module main; fn main() { if (true) { print(1); } }"
    prog = parse_src(src)
    stmt = prog.body.statements[0]
    assert isinstance(stmt, If)
    assert stmt.else_branch is None
    assert len(stmt.then_block.statements) == 1


def test_parse_if_else() -> None:
    src = "module main; fn main() { if (true) { print(1); } else { print(2); } }"
    prog = parse_src(src)
    stmt = prog.body.statements[0]
    assert isinstance(stmt, If)
    assert isinstance(stmt.else_branch, Block)
    assert len(stmt.else_branch.statements) == 1


def test_parse_if_else_if_chain() -> None:
    src = """
    module main;
    fn main() {
        if (a) { print(1); }
        else if (b) { print(2); }
        else { print(3); }
    }
    """
    prog = parse_src(src)
    stmt = prog.body.statements[0]
    assert isinstance(stmt, If)
    assert isinstance(stmt.else_branch, If)
    assert isinstance(stmt.else_branch.else_branch, Block)


def test_parse_while_stmt() -> None:
    src = "module main; fn main() { while (x < 10) { x += 1; } }"
    prog = parse_src(src)
    stmt = prog.body.statements[0]
    assert isinstance(stmt, While)
    assert isinstance(stmt.cond, BinaryOp)
    assert len(stmt.body.statements) == 1


def test_parse_do_while_stmt() -> None:
    src = "module main; fn main() { do { x += 1; } while (x < 10); }"
    prog = parse_src(src)
    stmt = prog.body.statements[0]
    assert isinstance(stmt, DoWhile)
    assert isinstance(stmt.cond, BinaryOp)
    assert len(stmt.body.statements) == 1


def test_parse_for_full() -> None:
    src = "module main; fn main() { for (mut i = 0; i < 10; i += 1) { print(i); } }"
    prog = parse_src(src)
    stmt = prog.body.statements[0]
    assert isinstance(stmt, For)
    assert isinstance(stmt.init, VarDecl)
    assert isinstance(stmt.cond, BinaryOp)
    assert isinstance(stmt.update, Assign)
    assert len(stmt.body.statements) == 1


def test_parse_for_empty_parts() -> None:
    src = "module main; fn main() { for (;;) { print(1); } }"
    prog = parse_src(src)
    stmt = prog.body.statements[0]
    assert isinstance(stmt, For)
    assert stmt.init is None
    assert stmt.cond is None
    assert stmt.update is None


def test_parse_bare_nested_block() -> None:
    src = "module main; fn main() { { { print(1); } } }"
    prog = parse_src(src)
    outer = prog.body.statements[0]
    assert isinstance(outer, Block)
    inner = outer.statements[0]
    assert isinstance(inner, Block)
    assert isinstance(inner.statements[0], Print)


# ============================================================================
# 2. Operator Precedence and Associativity (§5.3)
# ============================================================================

def test_precedence_multiplication_over_addition() -> None:
    # 1 + 2 * 3 parses as 1 + (2 * 3)
    src = "module main; fn main() { let x = 1 + 2 * 3; }"
    prog = parse_src(src)
    expr = prog.body.statements[0].init
    assert isinstance(expr, BinaryOp)
    assert expr.op == "+"
    assert isinstance(expr.right, BinaryOp)
    assert expr.right.op == "*"


def test_left_associativity_subtraction() -> None:
    # 10 - 5 - 2 parses as (10 - 5) - 2
    src = "module main; fn main() { let x = 10 - 5 - 2; }"
    prog = parse_src(src)
    expr = prog.body.statements[0].init
    assert isinstance(expr, BinaryOp)
    assert expr.op == "-"
    assert isinstance(expr.left, BinaryOp)
    assert expr.left.op == "-"
    assert isinstance(expr.right, Literal)
    assert expr.right.value == 2


def test_comparison_left_associative() -> None:
    # a < b < c parses as (a < b) < c
    src = "module main; fn main() { let x = a < b < c; }"
    prog = parse_src(src)
    expr = prog.body.statements[0].init
    assert isinstance(expr, BinaryOp)
    assert expr.op == "<"
    assert isinstance(expr.left, BinaryOp)
    assert expr.left.op == "<"


def test_logical_and_over_or() -> None:
    # a || b && c parses as a || (b && c)
    src = "module main; fn main() { let x = a || b && c; }"
    prog = parse_src(src)
    expr = prog.body.statements[0].init
    assert isinstance(expr, BinaryOp)
    assert expr.op == "||"
    assert isinstance(expr.right, BinaryOp)
    assert expr.right.op == "&&"


def test_unary_prefix_right_associative() -> None:
    # - -x parses as -(-x)
    src = "module main; fn main() { let x = - -y; }"
    prog = parse_src(src)
    expr = prog.body.statements[0].init
    assert isinstance(expr, UnaryOp)
    assert expr.op == "-"
    assert isinstance(expr.operand, UnaryOp)
    assert expr.operand.op == "-"


def test_parentheses_override_precedence() -> None:
    # (1 + 2) * 3 parses as (1 + 2) * 3
    src = "module main; fn main() { let x = (1 + 2) * 3; }"
    prog = parse_src(src)
    expr = prog.body.statements[0].init
    assert isinstance(expr, BinaryOp)
    assert expr.op == "*"
    assert isinstance(expr.left, BinaryOp)
    assert expr.left.op == "+"


def test_expression_start_position_with_parentheses() -> None:
    # Check that start_line / start_col are set to the '(' (§12.5)
    src = "module main;\nfn main() {\n    let x = (10 + 20);\n}"
    prog = parse_src(src)
    expr = prog.body.statements[0].init
    assert isinstance(expr, BinaryOp)
    assert expr.line == 3 and expr.col == 17  # '+' operator position
    assert expr.start_line == 3 and expr.start_col == 13  # '(' position


def test_long_chain_of_binary_operators() -> None:
    # At least 1000 binary operators at the same precedence level must work (§5.2 note 7)
    terms = ["1"] * 1005
    chain = " + ".join(terms)
    src = f"module main; fn main() {{ let x = {chain}; }}"
    prog = parse_src(src)
    expr = prog.body.statements[0].init
    assert isinstance(expr, BinaryOp)


# ============================================================================
# 3. Syntax Errors (S001 with every <X> value, S002, S003, S004) (§10.4)
# ============================================================================

def test_s001_expected_module() -> None:
    with pytest.raises(ParseError) as exc_info:
        parse_src("fn main() {}")
    assert exc_info.value.code == "S001"
    assert exc_info.value.message == "expected 'module', found 'fn'"


def test_s001_expected_identifier_after_module() -> None:
    with pytest.raises(ParseError) as exc_info:
        parse_src("module ;")
    assert exc_info.value.code == "S001"
    assert exc_info.value.message == "expected identifier, found ';'"


def test_s001_expected_identifier_after_let() -> None:
    with pytest.raises(ParseError) as exc_info:
        parse_src("module main; fn main() { let = 1; }")
    assert exc_info.value.code == "S001"
    assert exc_info.value.message == "expected identifier, found '='"


def test_s001_expected_semicolon_after_module() -> None:
    with pytest.raises(ParseError) as exc_info:
        parse_src("module main fn main() {}")
    assert exc_info.value.code == "S001"
    assert exc_info.value.message == "expected ';', found 'fn'"


def test_s001_expected_semicolon_after_decl() -> None:
    with pytest.raises(ParseError) as exc_info:
        parse_src("module main; fn main() { let x = 1 print(x); }")
    assert exc_info.value.code == "S001"
    assert exc_info.value.message == "expected ';', found 'print'"


def test_s001_expected_fn() -> None:
    with pytest.raises(ParseError) as exc_info:
        parse_src("module main; main() {}")
    assert exc_info.value.code == "S001"
    assert exc_info.value.message == "expected 'fn', found 'main'"


def test_s001_expected_main() -> None:
    with pytest.raises(ParseError) as exc_info:
        parse_src("module main; fn foo() {}")
    assert exc_info.value.code == "S001"
    assert exc_info.value.message == "expected 'main', found 'foo'"


def test_s001_expected_lparen() -> None:
    with pytest.raises(ParseError) as exc_info:
        parse_src("module main; fn main {}")
    assert exc_info.value.code == "S001"
    assert exc_info.value.message == "expected '(', found '{'"


def test_s001_expected_rparen() -> None:
    with pytest.raises(ParseError) as exc_info:
        parse_src("module main; fn main( {}")
    assert exc_info.value.code == "S001"
    assert exc_info.value.message == "expected ')', found '{'"


def test_s001_expected_lbrace() -> None:
    with pytest.raises(ParseError) as exc_info:
        parse_src("module main; fn main() let x = 1;")
    assert exc_info.value.code == "S001"
    assert exc_info.value.message == "expected '{', found 'let'"


def test_s001_expected_rbrace_eof() -> None:
    with pytest.raises(ParseError) as exc_info:
        parse_src("module main; fn main() { let x = 1;")
    assert exc_info.value.code == "S001"
    assert exc_info.value.message == "expected '}', found end of file"


def test_s001_expected_statement_on_lone_semicolon() -> None:
    with pytest.raises(ParseError) as exc_info:
        parse_src("module main; fn main() { ; }")
    assert exc_info.value.code == "S001"
    assert exc_info.value.message == "expected statement, found ';'"


def test_s001_expected_statement_on_expression() -> None:
    with pytest.raises(ParseError) as exc_info:
        parse_src("module main; fn main() { 5; }")
    assert exc_info.value.code == "S001"
    assert exc_info.value.message == "expected statement, found '5'"


def test_s001_expected_eq_in_var_decl() -> None:
    with pytest.raises(ParseError) as exc_info:
        parse_src("module main; fn main() { let x 1; }")
    assert exc_info.value.code == "S001"
    assert exc_info.value.message == "expected '=', found '1'"


def test_s001_expected_expression() -> None:
    with pytest.raises(ParseError) as exc_info:
        parse_src("module main; fn main() { let x = ; }")
    assert exc_info.value.code == "S001"
    assert exc_info.value.message == "expected expression, found ';'"


def test_s001_expected_assignment_operator() -> None:
    # x + 1; where an assignment is expected
    with pytest.raises(ParseError) as exc_info:
        parse_src("module main; fn main() { x + 1; }")
    assert exc_info.value.code == "S001"
    assert exc_info.value.message == "expected assignment operator, found '+'"


def test_s001_expected_if_or_lbrace_after_else() -> None:
    with pytest.raises(ParseError) as exc_info:
        parse_src("module main; fn main() { if (true) {} else while(true) {} }")
    assert exc_info.value.code == "S001"
    assert exc_info.value.message == "expected 'if' or '{', found 'while'"


def test_s001_expected_while_after_do() -> None:
    with pytest.raises(ParseError) as exc_info:
        parse_src("module main; fn main() { do {} for(;;) {} }")
    assert exc_info.value.code == "S001"
    assert exc_info.value.message == "expected 'while', found 'for'"


def test_s001_expected_for_init() -> None:
    with pytest.raises(ParseError) as exc_info:
        parse_src("module main; fn main() { for (print(1);;) {} }")
    assert exc_info.value.code == "S001"
    assert exc_info.value.message == "expected variable declaration, assignment or ';', found 'print'"


def test_s001_expected_for_update() -> None:
    with pytest.raises(ParseError) as exc_info:
        parse_src("module main; fn main() { for (;; print(1)) {} }")
    assert exc_info.value.code == "S001"
    assert exc_info.value.message == "expected assignment or ')', found 'print'"


def test_s002_unexpected_after_end_of_program() -> None:
    with pytest.raises(ParseError) as exc_info:
        parse_src("module main; fn main() {} let x = 1;")
    assert exc_info.value.code == "S002"
    assert exc_info.value.message == "unexpected 'let' after end of program"


def test_s003_reserved_word_replaces_syntax_error() -> None:
    with pytest.raises(ParseError) as exc_info:
        parse_src("module main; fn main() { let return = 1; }")
    assert exc_info.value.code == "S003"
    assert exc_info.value.message == "'return' is reserved for future use and cannot be used in this version"


def test_s004_nesting_limit_blocks() -> None:
    # 201 nested blocks
    inner = "{ print(1); }"
    for _ in range(200):
        inner = f"{{ {inner} }}"
    src = f"module main; fn main() {inner}"
    with pytest.raises(ParseError) as exc_info:
        parse_src(src)
    assert exc_info.value.code == "S004"
    assert exc_info.value.message == "program is nested too deeply (limit 200)"


def test_s004_nesting_limit_parentheses() -> None:
    # 201 nested parentheses
    inner = "1"
    for _ in range(201):
        inner = f"({inner})"
    src = f"module main; fn main() {{ let x = {inner}; }}"
    with pytest.raises(ParseError) as exc_info:
        parse_src(src)
    assert exc_info.value.code == "S004"
    assert exc_info.value.message == "program is nested too deeply (limit 200)"


# ============================================================================
# 4. astprint.py formatting (§11.6)
# ============================================================================

def test_astprint_tokens_format() -> None:
    tokens = tokenize(normalize_source("module foo;"))
    out = format_tokens(tokens)
    expected = "1:1\tMODULE\tmodule\n1:8\tIDENT\tfoo\n1:11\tSEMI\t;\n1:12\tEOF\t\n"
    assert out == expected

    tokens_main = tokenize(normalize_source("module main;"))
    out_main = format_tokens(tokens_main)
    assert out_main == "1:1\tMODULE\tmodule\n1:8\tMAIN\tmain\n1:12\tSEMI\t;\n1:13\tEOF\t\n"


def test_astprint_ast_format_spec_example() -> None:
    src = """module main;
fn main() {
  let x = 1 + 2;
}
"""
    prog = parse_src(src)
    out = format_ast(prog)
    expected = (
        'Program(module="main")\n'
        '  body: Block\n'
        '    stmt: VarDecl(mutable=false, name="x")\n'
        '      init: BinaryOp(op="+")\n'
        '        left: Literal(type=int, value=1)\n'
        '        right: Literal(type=int, value=2)\n'
    )
    assert out == expected
