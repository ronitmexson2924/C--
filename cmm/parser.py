"""Recursive-descent parser for C-- per Section 5 and Section 12.5."""

from __future__ import annotations

import sys
from typing import NoReturn, Optional

# Ensure recursion limit is at least 10000 per §5.2 note 7 and §13.8
if sys.getrecursionlimit() < 10000:
    sys.setrecursionlimit(10000)

from cmm.ast_nodes import (
    Assign,
    BinaryOp,
    Block,
    DoWhile,
    Expr,
    For,
    If,
    Literal,
    Print,
    Program,
    Stmt,
    UnaryOp,
    VarDecl,
    Variable,
    While,
)
from cmm.errors import ParseError
from cmm.tokens import Token, TokenType


def _format_found_token(token: Token) -> str:
    """Format token description <Y> per Section 10.4."""
    if token.type == TokenType.EOF:
        return "end of file"
    elif token.type == TokenType.STRING:
        return "string literal"
    else:
        return f"'{token.lexeme}'"


class Parser:
    """Recursive descent parser implementing the C-- grammar."""

    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._pos = 0
        self._nesting_depth = 0

    def _peek(self) -> Token:
        return self._tokens[self._pos]

    def _is_at_end(self) -> bool:
        return self._peek().type == TokenType.EOF

    def _check(self, t_type: TokenType) -> bool:
        return self._peek().type == t_type

    def _advance(self) -> Token:
        token = self._tokens[self._pos]
        if not self._is_at_end():
            self._pos += 1
        return token

    def _error_expected(self, expected: str, token: Token) -> NoReturn:
        """Report syntax error S001 or S003 per Section 10.4."""
        if token.type == TokenType.RESERVED:
            raise ParseError(
                "S003",
                f"'{token.lexeme}' is reserved for future use and cannot be used in this version",
                token.line,
                token.col,
            )
        raise ParseError(
            "S001",
            f"expected {expected}, found {_format_found_token(token)}",
            token.line,
            token.col,
        )

    def _consume(self, t_type: TokenType, expected_str: str) -> Token:
        token = self._peek()
        if token.type == t_type:
            return self._advance()
        self._error_expected(expected_str, token)

    def _enter_nested(self, token: Token) -> None:
        """Increase nesting depth and check limit of 200 per Section 5.2 (S004)."""
        self._nesting_depth += 1
        if self._nesting_depth > 200:
            raise ParseError("S004", "program is nested too deeply (limit 200)", token.line, token.col)

    def _exit_nested(self) -> None:
        """Decrease nesting depth."""
        self._nesting_depth -= 1

    # -------------------------------------------------------------------------
    # Grammar rules
    # -------------------------------------------------------------------------

    def parse_program(self) -> Program:
        """program = 'module' IDENT ';' 'fn' 'main' '(' ')' block EOF ;"""
        module_token = self._consume(TokenType.MODULE, "'module'")

        if not (self._check(TokenType.IDENT) or self._check(TokenType.MAIN)):
            self._error_expected("identifier", self._peek())
        module_name_token = self._advance()

        self._consume(TokenType.SEMI, "';'")
        self._consume(TokenType.FN, "'fn'")
        self._consume(TokenType.MAIN, "'main'")
        self._consume(TokenType.LPAREN, "'('")
        self._consume(TokenType.RPAREN, "')'")

        body = self.parse_block()

        if not self._is_at_end():
            token = self._peek()
            if token.type == TokenType.RESERVED:
                raise ParseError(
                    "S003",
                    f"'{token.lexeme}' is reserved for future use and cannot be used in this version",
                    token.line,
                    token.col,
                )
            raise ParseError(
                "S002",
                f"unexpected {_format_found_token(token)} after end of program",
                token.line,
                token.col,
            )

        return Program(
            module_name=module_name_token.lexeme,
            body=body,
            line=module_token.line,
            col=module_token.col,
        )

    def parse_block(self) -> Block:
        """block = '{' { statement } '}' ;"""
        lbrace = self._consume(TokenType.LBRACE, "'{'")
        self._enter_nested(lbrace)

        statements: list[Stmt] = []
        try:
            while not self._check(TokenType.RBRACE):
                if self._is_at_end():
                    self._error_expected("'}'", self._peek())
                statements.append(self.parse_statement())
            self._consume(TokenType.RBRACE, "'}'")
        finally:
            self._exit_nested()

        return Block(statements=statements, line=lbrace.line, col=lbrace.col)

    def parse_statement(self) -> Stmt:
        """statement = varDecl | assignStmt | printStmt | ifStmt | whileStmt | doWhileStmt | forStmt | block ;"""
        token = self._peek()
        if token.type in (TokenType.LET, TokenType.MUT):
            return self.parse_var_decl()
        elif token.type == TokenType.IDENT:
            return self.parse_assign_stmt()
        elif token.type == TokenType.PRINT:
            return self.parse_print_stmt()
        elif token.type == TokenType.IF:
            return self.parse_if_stmt()
        elif token.type == TokenType.WHILE:
            return self.parse_while_stmt()
        elif token.type == TokenType.DO:
            return self.parse_do_while_stmt()
        elif token.type == TokenType.FOR:
            return self.parse_for_stmt()
        elif token.type == TokenType.LBRACE:
            return self.parse_block()
        else:
            self._error_expected("statement", token)

    def parse_var_decl(self) -> VarDecl:
        """varDecl = ( 'let' | 'mut' ) IDENT '=' expr ';' ;"""
        decl_token = self._advance()  # LET or MUT
        mutable = decl_token.type == TokenType.MUT

        if not self._check(TokenType.IDENT):
            self._error_expected("identifier", self._peek())
        name_token = self._advance()

        self._consume(TokenType.EQ, "'='")
        init_expr = self.parse_expr()
        self._consume(TokenType.SEMI, "';'")

        return VarDecl(
            mutable=mutable,
            name=name_token.lexeme,
            name_line=name_token.line,
            name_col=name_token.col,
            init=init_expr,
            line=decl_token.line,
            col=decl_token.col,
        )

    def parse_assign_stmt(self) -> Assign:
        """assignStmt = assignment ';' ;"""
        assign_node = self.parse_assignment()
        self._consume(TokenType.SEMI, "';'")
        return assign_node

    def parse_assignment(self) -> Assign:
        """assignment = IDENT assignOp expr ;"""
        name_token = self._advance()  # IDENT

        assign_ops = (
            TokenType.EQ,
            TokenType.PLUSEQ,
            TokenType.MINUSEQ,
            TokenType.STAREQ,
            TokenType.SLASHEQ,
            TokenType.PERCENTEQ,
        )
        if self._peek().type not in assign_ops:
            self._error_expected("assignment operator", self._peek())
        op_token = self._advance()

        val_expr = self.parse_expr()
        return Assign(
            name=name_token.lexeme,
            op=op_token.lexeme,
            op_line=op_token.line,
            op_col=op_token.col,
            value=val_expr,
            line=name_token.line,
            col=name_token.col,
        )

    def parse_print_stmt(self) -> Print:
        """printStmt = 'print' '(' expr ')' ';' ;"""
        print_token = self._consume(TokenType.PRINT, "'print'")
        self._consume(TokenType.LPAREN, "'('")
        expr = self.parse_expr()
        self._consume(TokenType.RPAREN, "')'")
        self._consume(TokenType.SEMI, "';'")
        return Print(expr=expr, line=print_token.line, col=print_token.col)

    def parse_if_stmt(self) -> If:
        """ifStmt = 'if' '(' expr ')' block [ 'else' ( ifStmt | block ) ] ;"""
        if_token = self._consume(TokenType.IF, "'if'")
        self._consume(TokenType.LPAREN, "'('")
        cond = self.parse_expr()
        self._consume(TokenType.RPAREN, "')'")
        then_block = self.parse_block()

        else_branch: Optional[Block | If] = None
        if self._check(TokenType.ELSE):
            self._advance()  # consume 'else'
            if self._check(TokenType.IF):
                else_branch = self.parse_if_stmt()
            elif self._check(TokenType.LBRACE):
                else_branch = self.parse_block()
            else:
                self._error_expected("'if' or '{'", self._peek())

        return If(
            cond=cond,
            then_block=then_block,
            else_branch=else_branch,
            line=if_token.line,
            col=if_token.col,
        )

    def parse_while_stmt(self) -> While:
        """whileStmt = 'while' '(' expr ')' block ;"""
        while_token = self._consume(TokenType.WHILE, "'while'")
        self._consume(TokenType.LPAREN, "'('")
        cond = self.parse_expr()
        self._consume(TokenType.RPAREN, "')'")
        body = self.parse_block()
        return While(cond=cond, body=body, line=while_token.line, col=while_token.col)

    def parse_do_while_stmt(self) -> DoWhile:
        """doWhileStmt = 'do' block 'while' '(' expr ')' ';' ;"""
        do_token = self._consume(TokenType.DO, "'do'")
        body = self.parse_block()
        self._consume(TokenType.WHILE, "'while'")
        self._consume(TokenType.LPAREN, "'('")
        cond = self.parse_expr()
        self._consume(TokenType.RPAREN, "')'")
        self._consume(TokenType.SEMI, "';'")
        return DoWhile(body=body, cond=cond, line=do_token.line, col=do_token.col)

    def parse_for_stmt(self) -> For:
        """forStmt = 'for' '(' forInit [ expr ] ';' [ assignment ] ')' block ;"""
        for_token = self._consume(TokenType.FOR, "'for'")
        self._consume(TokenType.LPAREN, "'('")

        # forInit = varDecl | assignStmt | ';'
        init_node: Optional[VarDecl | Assign] = None
        if self._check(TokenType.LET) or self._check(TokenType.MUT):
            init_node = self.parse_var_decl()
        elif self._check(TokenType.IDENT):
            init_node = self.parse_assign_stmt()
        elif self._check(TokenType.SEMI):
            self._consume(TokenType.SEMI, "';'")
            init_node = None
        else:
            self._error_expected("variable declaration, assignment or ';'", self._peek())

        # condition = [ expr ] ';'
        cond_node: Optional[Expr] = None
        if self._check(TokenType.SEMI):
            self._consume(TokenType.SEMI, "';'")
            cond_node = None
        else:
            cond_node = self.parse_expr()
            self._consume(TokenType.SEMI, "';'")

        # update = [ assignment ] ')'
        update_node: Optional[Assign] = None
        if self._check(TokenType.RPAREN):
            self._consume(TokenType.RPAREN, "')'")
            update_node = None
        elif self._check(TokenType.IDENT):
            update_node = self.parse_assignment()
            self._consume(TokenType.RPAREN, "')'")
        else:
            self._error_expected("assignment or ')'", self._peek())

        body = self.parse_block()
        return For(
            init=init_node,
            cond=cond_node,
            update=update_node,
            body=body,
            line=for_token.line,
            col=for_token.col,
        )

    # -------------------------------------------------------------------------
    # Expressions (precedence low to high, left-associative iterative)
    # -------------------------------------------------------------------------

    def parse_expr(self) -> Expr:
        """expr = or ;"""
        return self._parse_or()

    def _parse_or(self) -> Expr:
        """or = and { '||' and } ;"""
        left = self._parse_and()
        while self._check(TokenType.OROR):
            op = self._advance()
            right = self._parse_and()
            left = BinaryOp(
                op="||",
                left=left,
                right=right,
                line=op.line,
                col=op.col,
                start_line=left.start_line,
                start_col=left.start_col,
            )
        return left

    def _parse_and(self) -> Expr:
        """and = equality { '&&' equality } ;"""
        left = self._parse_equality()
        while self._check(TokenType.ANDAND):
            op = self._advance()
            right = self._parse_equality()
            left = BinaryOp(
                op="&&",
                left=left,
                right=right,
                line=op.line,
                col=op.col,
                start_line=left.start_line,
                start_col=left.start_col,
            )
        return left

    def _parse_equality(self) -> Expr:
        """equality = comparison { ( '==' | '!=' ) comparison } ;"""
        left = self._parse_comparison()
        while self._check(TokenType.EQEQ) or self._check(TokenType.BANGEQ):
            op = self._advance()
            right = self._parse_comparison()
            left = BinaryOp(
                op=op.lexeme,
                left=left,
                right=right,
                line=op.line,
                col=op.col,
                start_line=left.start_line,
                start_col=left.start_col,
            )
        return left

    def _parse_comparison(self) -> Expr:
        """comparison = term { ( '<' | '>' | '<=' | '>=' ) term } ;"""
        left = self._parse_term()
        comp_ops = (TokenType.LT, TokenType.GT, TokenType.LTEQ, TokenType.GTEQ)
        while self._peek().type in comp_ops:
            op = self._advance()
            right = self._parse_term()
            left = BinaryOp(
                op=op.lexeme,
                left=left,
                right=right,
                line=op.line,
                col=op.col,
                start_line=left.start_line,
                start_col=left.start_col,
            )
        return left

    def _parse_term(self) -> Expr:
        """term = factor { ( '+' | '-' ) factor } ;"""
        left = self._parse_factor()
        while self._check(TokenType.PLUS) or self._check(TokenType.MINUS):
            op = self._advance()
            right = self._parse_factor()
            left = BinaryOp(
                op=op.lexeme,
                left=left,
                right=right,
                line=op.line,
                col=op.col,
                start_line=left.start_line,
                start_col=left.start_col,
            )
        return left

    def _parse_factor(self) -> Expr:
        """factor = unary { ( '*' | '/' | '%' ) unary } ;"""
        left = self._parse_unary()
        factor_ops = (TokenType.STAR, TokenType.SLASH, TokenType.PERCENT)
        while self._peek().type in factor_ops:
            op = self._advance()
            right = self._parse_unary()
            left = BinaryOp(
                op=op.lexeme,
                left=left,
                right=right,
                line=op.line,
                col=op.col,
                start_line=left.start_line,
                start_col=left.start_col,
            )
        return left

    def _parse_unary(self) -> Expr:
        """unary = ( '!' | '-' ) unary | primary ;"""
        if self._check(TokenType.BANG) or self._check(TokenType.MINUS):
            op = self._advance()
            self._enter_nested(op)
            try:
                operand = self._parse_unary()
            finally:
                self._exit_nested()
            return UnaryOp(
                op=op.lexeme,
                operand=operand,
                line=op.line,
                col=op.col,
                start_line=op.line,
                start_col=op.col,
            )
        return self._parse_primary()

    def _parse_primary(self) -> Expr:
        """primary = INT | FLOAT | STRING | 'true' | 'false' | IDENT | '(' expr ')' ;"""
        token = self._peek()

        if token.type == TokenType.INT:
            self._advance()
            return Literal("int", token.value, token.line, token.col)
        elif token.type == TokenType.FLOAT:
            self._advance()
            return Literal("float", token.value, token.line, token.col)
        elif token.type == TokenType.STRING:
            self._advance()
            return Literal("string", token.value, token.line, token.col)
        elif token.type == TokenType.TRUE:
            self._advance()
            return Literal("bool", True, token.line, token.col)
        elif token.type == TokenType.FALSE:
            self._advance()
            return Literal("bool", False, token.line, token.col)
        elif token.type == TokenType.IDENT:
            self._advance()
            return Variable(token.lexeme, token.line, token.col)
        elif token.type == TokenType.LPAREN:
            lparen = self._advance()
            self._enter_nested(lparen)
            try:
                inner = self.parse_expr()
                self._consume(TokenType.RPAREN, "')'")
            finally:
                self._exit_nested()
            # Parenthesized expression sets start position on inner node (§12.5)
            inner.start_line = lparen.line
            inner.start_col = lparen.col
            return inner
        else:
            self._error_expected("expression", token)


def parse(tokens: list[Token]) -> Program:
    """Parse a list of tokens into a C-- AST Program node.

    Args:
        tokens: The list of Token objects from tokenizer, ending with EOF.

    Returns:
        The root Program AST node.

    Raises:
        ParseError: Upon encountering any syntax error (S001 - S004).
    """
    parser = Parser(tokens)
    return parser.parse_program()
