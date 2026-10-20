"""Recursive-descent parser for C-- v0.2.0 per §A5."""

from __future__ import annotations

import sys
from typing import NoReturn, Optional, Union

# Ensure recursion limit is at least 10000 per §5.2 note 7 and §13.8
if sys.getrecursionlimit() < 10000:
    sys.setrecursionlimit(10000)

from cmm.ast_nodes import (
    ArrayLiteral,
    Assign,
    BinaryOp,
    Block,
    Call,
    CallStmt,
    CaseClause,
    DoWhile,
    Expr,
    For,
    FunctionDef,
    If,
    Index,
    IndexAssign,
    Literal,
    MethodCall,
    NewCollection,
    Param,
    Print,
    Program,
    ReturnStmt,
    Stmt,
    SwitchStmt,
    UnaryOp,
    VarDecl,
    Variable,
    While,
)
from cmm.errors import ParseError
from cmm.tokens import Token, TokenType
from cmm.types import Type


def _format_found_token(token: Token) -> str:
    """Format token description <Y> per Section 10.4."""
    if token.type == TokenType.EOF:
        return "end of file"
    elif token.type == TokenType.STRING:
        return "string literal"
    else:
        return f"'{token.lexeme}'"


class Parser:
    """Recursive descent parser implementing the C-- v0.2.0 grammar."""

    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._pos = 0
        self._nesting_depth = 0

    def _peek(self) -> Token:
        return self._tokens[self._pos]

    def _peek_next(self) -> Token:
        if self._pos + 1 < len(self._tokens):
            return self._tokens[self._pos + 1]
        return self._tokens[-1]

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
        """Increase nesting depth and check limit of 200 per Section 5.2 & §A5 (S004)."""
        self._nesting_depth += 1
        if self._nesting_depth > 200:
            raise ParseError("S004", "program is nested too deeply (limit 200)", token.line, token.col)

    def _exit_nested(self) -> None:
        """Decrease nesting depth."""
        self._nesting_depth -= 1

    # -------------------------------------------------------------------------
    # Grammar rules (§A5)
    # -------------------------------------------------------------------------

    def parse_program(self) -> Program:
        """program = 'module' IDENT ';' function { function } EOF ;"""
        module_token = self._consume(TokenType.MODULE, "'module'")

        if not (self._check(TokenType.IDENT) or self._check(TokenType.MAIN)):
            self._error_expected("identifier", self._peek())
        module_name_token = self._advance()
        self._consume(TokenType.SEMI, "';'")

        functions: list[FunctionDef] = []
        if not self._check(TokenType.FN):
            self._error_expected("'fn'", self._peek())

        while self._check(TokenType.FN):
            functions.append(self.parse_function())

        if not self._is_at_end():
            self._error_expected("'fn'", self._peek())

        return Program(
            module_name=module_name_token.lexeme,
            functions=functions,
            line=module_token.line,
            col=module_token.col,
        )

    def parse_function(self) -> FunctionDef:
        """function = 'fn' ( IDENT | 'main' ) '(' [ param { ',' param } ] ')' [ '->' type ] block ;"""
        fn_token = self._consume(TokenType.FN, "'fn'")
        if not (self._check(TokenType.IDENT) or self._check(TokenType.MAIN)):
            self._error_expected("identifier or 'main'", self._peek())
        name_token = self._advance()
        name = name_token.lexeme

        self._consume(TokenType.LPAREN, "'('")
        params: list[Param] = []
        if self._check(TokenType.IDENT):
            params.append(self.parse_param())
            while self._check(TokenType.COMMA):
                self._advance()
                params.append(self.parse_param())
            self._consume(TokenType.RPAREN, "')'")
        else:
            self._consume(TokenType.RPAREN, "')'")


        ret_type: Optional[Type] = None
        if self._check(TokenType.ARROW):
            self._advance()  # consume '->'
            ret_type = self.parse_type()

        body = self.parse_block()
        return FunctionDef(
            name=name,
            params=params,
            ret_type=ret_type,
            body=body,
            line=fn_token.line,
            col=fn_token.col,
        )

    def parse_param(self) -> Param:
        """param = IDENT ':' type ;"""
        name_token = self._consume(TokenType.IDENT, "identifier")
        self._consume(TokenType.COLON, "':'")
        t = self.parse_type()
        return Param(name=name_token.lexeme, type=t, line=name_token.line, col=name_token.col)

    def parse_type(self) -> Type:
        """type = 'int' | 'float' | 'bool' | 'string' | collType ;"""
        tok = self._peek()
        if tok.type == TokenType.KW_INT:
            self._advance()
            return Type.INT
        elif tok.type == TokenType.KW_FLOAT:
            self._advance()
            return Type.FLOAT
        elif tok.type == TokenType.KW_BOOL:
            self._advance()
            return Type.BOOL
        elif tok.type == TokenType.KW_STRING:
            self._advance()
            return Type.STRING
        elif tok.type in (TokenType.KW_ARRAY, TokenType.KW_LIST, TokenType.KW_STACK, TokenType.KW_QUEUE):
            kind = self._advance().lexeme
            self._consume(TokenType.LT, "'<'")
            elem = self.parse_elem_type()
            self._consume(TokenType.GT, "'>'")
            return Type.coll(kind, elem)
        else:
            self._error_expected("type ('int', 'float', 'bool', 'string', 'array', 'list', 'stack' or 'queue')", tok)

    def parse_elem_type(self) -> Type:
        """elemType = 'int' | 'float' | 'bool' | 'string' ;"""
        tok = self._peek()
        if tok.type == TokenType.KW_INT:
            self._advance()
            return Type.INT
        elif tok.type == TokenType.KW_FLOAT:
            self._advance()
            return Type.FLOAT
        elif tok.type == TokenType.KW_BOOL:
            self._advance()
            return Type.BOOL
        elif tok.type == TokenType.KW_STRING:
            self._advance()
            return Type.STRING
        else:
            self._error_expected("element type ('int', 'float', 'bool' or 'string')", tok)

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
        """statement = varDecl | assignStmt | callStmt | printStmt | returnStmt
                     | ifStmt | whileStmt | doWhileStmt | forStmt | switchStmt | block ;
        """
        token = self._peek()
        if token.type in (TokenType.LET, TokenType.MUT):
            return self.parse_var_decl()
        elif token.type in (TokenType.IDENT, TokenType.MAIN):
            # Check next token (§A5 Note 1)
            next_token = self._peek_next()
            if next_token.type == TokenType.LPAREN:
                call = self.parse_call()
                self._consume(TokenType.SEMI, "';'")
                return CallStmt(call=call, line=call.line, col=call.col)
            elif next_token.type == TokenType.DOT:
                method_call = self.parse_method_call()
                self._consume(TokenType.SEMI, "';'")
                return CallStmt(call=method_call, line=method_call.line, col=method_call.col)
            elif next_token.type == TokenType.LBRACKET:
                return self.parse_index_assign_stmt()
            elif next_token.type in (
                TokenType.EQ,
                TokenType.PLUSEQ,
                TokenType.MINUSEQ,
                TokenType.STAREQ,
                TokenType.SLASHEQ,
                TokenType.PERCENTEQ,
            ):
                return self.parse_assign_stmt()
            else:
                # Unexpected token after IDENT (§A5 note 1, §A7.3)
                self._advance()
                self._error_expected("assignment, call or method call", next_token)
        elif token.type == TokenType.PRINT:
            return self.parse_print_stmt()
        elif token.type == TokenType.RETURN:
            return self.parse_return_stmt()
        elif token.type == TokenType.IF:
            return self.parse_if_stmt()
        elif token.type == TokenType.WHILE:
            return self.parse_while_stmt()
        elif token.type == TokenType.DO:
            return self.parse_do_while_stmt()
        elif token.type == TokenType.FOR:
            return self.parse_for_stmt()
        elif token.type == TokenType.SWITCH:
            return self.parse_switch_stmt()
        elif token.type == TokenType.LBRACE:
            return self.parse_block()
        else:
            self._error_expected("statement", token)

    def parse_var_decl(self) -> VarDecl:
        """varDecl = ( 'let' | 'mut' ) IDENT '=' expr ';' ;"""
        mut_token = self._advance()
        mutable = mut_token.type == TokenType.MUT

        name_token = self._consume(TokenType.IDENT, "identifier")
        self._consume(TokenType.EQ, "'='")
        init_expr = self.parse_expr()
        self._consume(TokenType.SEMI, "';'")

        return VarDecl(
            mutable=mutable,
            name=name_token.lexeme,
            name_line=name_token.line,
            name_col=name_token.col,
            init=init_expr,
            line=mut_token.line,
            col=mut_token.col,
        )

    def parse_assign_stmt(self) -> Assign:
        """assignStmt = IDENT assignOp expr ';' ;"""
        name_token = self._consume(TokenType.IDENT, "identifier")
        op_token = self._peek()
        if op_token.type not in (
            TokenType.EQ,
            TokenType.PLUSEQ,
            TokenType.MINUSEQ,
            TokenType.STAREQ,
            TokenType.SLASHEQ,
            TokenType.PERCENTEQ,
        ):
            self._error_expected("assignment operator", op_token)
        self._advance()
        val_expr = self.parse_expr()
        self._consume(TokenType.SEMI, "';'")

        return Assign(
            name=name_token.lexeme,
            op=op_token.lexeme,
            op_line=op_token.line,
            op_col=op_token.col,
            value=val_expr,
            line=name_token.line,
            col=name_token.col,
        )

    def parse_index_assign_stmt(self) -> IndexAssign:
        """assignStmt = IDENT '[' expr ']' assignOp expr ';' ;"""
        name_token = self._consume(TokenType.IDENT, "identifier")
        lbracket = self._consume(TokenType.LBRACKET, "'['")
        self._enter_nested(lbracket)
        index_expr = self.parse_expr()
        self._consume(TokenType.RBRACKET, "']'")
        self._exit_nested()

        op_token = self._peek()
        if op_token.type not in (
            TokenType.EQ,
            TokenType.PLUSEQ,
            TokenType.MINUSEQ,
            TokenType.STAREQ,
            TokenType.SLASHEQ,
            TokenType.PERCENTEQ,
        ):
            self._error_expected("assignment operator", op_token)
        self._advance()
        val_expr = self.parse_expr()
        self._consume(TokenType.SEMI, "';'")

        return IndexAssign(
            name=name_token.lexeme,
            index=index_expr,
            op=op_token.lexeme,
            op_line=op_token.line,
            op_col=op_token.col,
            value=val_expr,
            line=name_token.line,
            col=name_token.col,
        )

    def parse_assignment_without_semi(self) -> Union[Assign, IndexAssign]:
        """assignment = IDENT [ '[' expr ']' ] assignOp expr ;"""
        name_token = self._consume(TokenType.IDENT, "identifier")
        if self._check(TokenType.LBRACKET):
            lbracket = self._advance()
            self._enter_nested(lbracket)
            index_expr = self.parse_expr()
            self._consume(TokenType.RBRACKET, "']'")
            self._exit_nested()

            op_token = self._peek()
            if op_token.type not in (
                TokenType.EQ,
                TokenType.PLUSEQ,
                TokenType.MINUSEQ,
                TokenType.STAREQ,
                TokenType.SLASHEQ,
                TokenType.PERCENTEQ,
            ):
                self._error_expected("assignment operator", op_token)
            self._advance()
            val_expr = self.parse_expr()
            return IndexAssign(
                name=name_token.lexeme,
                index=index_expr,
                op=op_token.lexeme,
                op_line=op_token.line,
                op_col=op_token.col,
                value=val_expr,
                line=name_token.line,
                col=name_token.col,
            )
        else:
            op_token = self._peek()
            if op_token.type not in (
                TokenType.EQ,
                TokenType.PLUSEQ,
                TokenType.MINUSEQ,
                TokenType.STAREQ,
                TokenType.SLASHEQ,
                TokenType.PERCENTEQ,
            ):
                self._error_expected("assignment operator", op_token)
            self._advance()
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

    def parse_return_stmt(self) -> ReturnStmt:
        """returnStmt = 'return' [ expr ] ';' ;"""
        return_token = self._consume(TokenType.RETURN, "'return'")
        expr = None
        if not self._check(TokenType.SEMI):
            expr = self.parse_expr()
        self._consume(TokenType.SEMI, "';'")
        return ReturnStmt(expr=expr, line=return_token.line, col=return_token.col)

    def parse_if_stmt(self) -> If:
        """ifStmt = 'if' '(' expr ')' block [ 'else' ( ifStmt | block ) ] ;"""
        if_token = self._consume(TokenType.IF, "'if'")
        self._consume(TokenType.LPAREN, "'('")
        cond = self.parse_expr()
        self._consume(TokenType.RPAREN, "')'")
        then_block = self.parse_block()

        else_branch: Optional[Union[Block, If]] = None
        if self._check(TokenType.ELSE):
            self._advance()
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
        """forStmt = 'for' '(' forInit [ expr ] ';' [ assignment ] ')' block ;
        forInit = varDecl | assignStmt | ';' ;
        """
        for_token = self._consume(TokenType.FOR, "'for'")
        self._consume(TokenType.LPAREN, "'('")

        init: Optional[Union[VarDecl, Assign, IndexAssign]] = None
        if self._check(TokenType.SEMI):
            self._advance()
        elif self._check(TokenType.LET) or self._check(TokenType.MUT):
            init = self.parse_var_decl()
        elif self._check(TokenType.IDENT):
            next_tok = self._peek_next()
            if next_tok.type == TokenType.LBRACKET:
                init = self.parse_index_assign_stmt()
            else:
                init = self.parse_assign_stmt()
        else:
            self._error_expected("variable declaration, assignment or ';'", self._peek())

        cond: Optional[Expr] = None
        if not self._check(TokenType.SEMI):
            cond = self.parse_expr()
        self._consume(TokenType.SEMI, "';'")

        update: Optional[Union[Assign, IndexAssign]] = None
        if not self._check(TokenType.RPAREN):
            if not self._check(TokenType.IDENT):
                self._error_expected("assignment or ')'", self._peek())
            update = self.parse_assignment_without_semi()
        self._consume(TokenType.RPAREN, "')'")


        body = self.parse_block()
        return For(
            init=init,
            cond=cond,
            update=update,
            body=body,
            line=for_token.line,
            col=for_token.col,
        )

    def parse_switch_stmt(self) -> SwitchStmt:
        """switchStmt = 'switch' '(' expr ')' '{' caseClause { caseClause } [ defaultClause ] '}' ;"""
        switch_token = self._consume(TokenType.SWITCH, "'switch'")
        self._consume(TokenType.LPAREN, "'('")
        selector = self.parse_expr()
        self._consume(TokenType.RPAREN, "')'")

        lbrace = self._consume(TokenType.LBRACE, "'{'")
        self._enter_nested(lbrace)

        cases: list[CaseClause] = []
        default_body: Optional[Block] = None

        if not self._check(TokenType.CASE):
            self._error_expected("'case'", self._peek())

        try:
            while self._check(TokenType.CASE):
                case_tok = self._advance()
                values = [self.parse_case_value()]
                while self._check(TokenType.COMMA):
                    self._advance()
                    values.append(self.parse_case_value())
                self._consume(TokenType.COLON, "':'")
                body = self.parse_block()
                cases.append(CaseClause(values=values, body=body, line=case_tok.line, col=case_tok.col))

            if self._check(TokenType.DEFAULT):
                self._advance()
                self._consume(TokenType.COLON, "':'")
                default_body = self.parse_block()

            self._consume(TokenType.RBRACE, "'}'")
        finally:
            self._exit_nested()

        return SwitchStmt(
            selector=selector,
            cases=cases,
            default_body=default_body,
            line=switch_token.line,
            col=switch_token.col,
        )

    def parse_case_value(self) -> Expr:
        """caseValue = INT | '-' INT | STRING ;"""
        tok = self._peek()
        if tok.type == TokenType.INT:
            self._advance()
            return Literal("int", tok.value, tok.line, tok.col)
        elif tok.type == TokenType.MINUS:
            minus_tok = self._advance()
            int_tok = self._consume(TokenType.INT, "integer literal")
            return Literal("int", -int_tok.value, minus_tok.line, minus_tok.col)
        elif tok.type == TokenType.STRING:
            self._advance()
            return Literal("string", tok.value, tok.line, tok.col)
        else:
            self._error_expected("integer or string literal", tok)

    def parse_call(self) -> Call:
        """call = ( IDENT | 'main' ) '(' [ args ] ')' ;"""
        name_tok = self._advance()
        lparen = self._consume(TokenType.LPAREN, "'('")
        self._enter_nested(lparen)
        args: list[Expr] = []
        try:
            if not self._check(TokenType.RPAREN):
                args.append(self.parse_expr())
                while self._check(TokenType.COMMA):
                    self._advance()
                    args.append(self.parse_expr())
            self._consume(TokenType.RPAREN, "')'")
        finally:
            self._exit_nested()

        return Call(name=name_tok.lexeme, args=args, line=name_tok.line, col=name_tok.col)

    def parse_method_call(self) -> MethodCall:
        """methodCall = IDENT '.' IDENT '(' [ args ] ')' ;"""
        receiver_tok = self._consume(TokenType.IDENT, "identifier")
        self._consume(TokenType.DOT, "'.'")
        method_tok = self._consume(TokenType.IDENT, "identifier")

        lparen = self._consume(TokenType.LPAREN, "'('")
        self._enter_nested(lparen)
        args: list[Expr] = []
        try:
            if not self._check(TokenType.RPAREN):
                args.append(self.parse_expr())
                while self._check(TokenType.COMMA):
                    self._advance()
                    args.append(self.parse_expr())
            self._consume(TokenType.RPAREN, "')'")
        finally:
            self._exit_nested()

        return MethodCall(
            receiver_name=receiver_tok.lexeme,
            method=method_tok.lexeme,
            args=args,
            line=receiver_tok.line,
            col=receiver_tok.col,
        )

    # -------------------------------------------------------------------------
    # Expression Parsing
    # -------------------------------------------------------------------------

    def parse_expr(self) -> Expr:
        return self._parse_or()

    def _parse_or(self) -> Expr:
        expr = self._parse_and()
        while self._check(TokenType.OROR):
            op_tok = self._advance()
            right = self._parse_and()
            expr = BinaryOp(
                op="||",
                left=expr,
                right=right,
                line=op_tok.line,
                col=op_tok.col,
                start_line=expr.start_line,
                start_col=expr.start_col,
            )
        return expr

    def _parse_and(self) -> Expr:
        expr = self._parse_equality()
        while self._check(TokenType.ANDAND):
            op_tok = self._advance()
            right = self._parse_equality()
            expr = BinaryOp(
                op="&&",
                left=expr,
                right=right,
                line=op_tok.line,
                col=op_tok.col,
                start_line=expr.start_line,
                start_col=expr.start_col,
            )
        return expr

    def _parse_equality(self) -> Expr:
        expr = self._parse_comparison()
        while self._peek().type in (TokenType.EQEQ, TokenType.BANGEQ):
            op_tok = self._advance()
            right = self._parse_comparison()
            expr = BinaryOp(
                op=op_tok.lexeme,
                left=expr,
                right=right,
                line=op_tok.line,
                col=op_tok.col,
                start_line=expr.start_line,
                start_col=expr.start_col,
            )
        return expr

    def _parse_comparison(self) -> Expr:
        expr = self._parse_term()
        while self._peek().type in (TokenType.LT, TokenType.LTEQ, TokenType.GT, TokenType.GTEQ):
            op_tok = self._advance()
            right = self._parse_term()
            expr = BinaryOp(
                op=op_tok.lexeme,
                left=expr,
                right=right,
                line=op_tok.line,
                col=op_tok.col,
                start_line=expr.start_line,
                start_col=expr.start_col,
            )
        return expr

    def _parse_term(self) -> Expr:
        expr = self._parse_factor()
        while self._peek().type in (TokenType.PLUS, TokenType.MINUS):
            op_tok = self._advance()
            right = self._parse_factor()
            expr = BinaryOp(
                op=op_tok.lexeme,
                left=expr,
                right=right,
                line=op_tok.line,
                col=op_tok.col,
                start_line=expr.start_line,
                start_col=expr.start_col,
            )
        return expr

    def _parse_factor(self) -> Expr:
        expr = self._parse_unary()
        while self._peek().type in (TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op_tok = self._advance()
            right = self._parse_unary()
            expr = BinaryOp(
                op=op_tok.lexeme,
                left=expr,
                right=right,
                line=op_tok.line,
                col=op_tok.col,
                start_line=expr.start_line,
                start_col=expr.start_col,
            )
        return expr

    def _parse_unary(self) -> Expr:
        """unary = ( '!' | '-' ) unary | postfix ;"""
        tok = self._peek()
        if tok.type in (TokenType.BANG, TokenType.MINUS):
            op_tok = self._advance()
            operand = self._parse_unary()
            return UnaryOp(
                op=op_tok.lexeme,
                operand=operand,
                line=op_tok.line,
                col=op_tok.col,
                start_line=op_tok.line,
                start_col=op_tok.col,
            )
        return self._parse_postfix()

    def _parse_postfix(self) -> Expr:
        """postfix = primary { '[' expr ']' } ;"""
        node = self._parse_primary()
        while self._check(TokenType.LBRACKET):
            lbracket = self._advance()
            self._enter_nested(lbracket)
            index_expr = self.parse_expr()
            self._consume(TokenType.RBRACKET, "']'")
            self._exit_nested()
            node = Index(
                target=node,
                index=index_expr,
                line=lbracket.line,
                col=lbracket.col,
                start_line=node.start_line,
                start_col=node.start_col,
            )
        return node

    def _parse_primary(self) -> Expr:
        """primary = INT | FLOAT | STRING | 'true' | 'false'
                   | arrayLiteral | newCollection | call | methodCall | IDENT | '(' expr ')' ;
        """
        tok = self._peek()

        if tok.type == TokenType.INT:
            self._advance()
            return Literal("int", tok.value, tok.line, tok.col)
        elif tok.type == TokenType.FLOAT:
            self._advance()
            return Literal("float", tok.value, tok.line, tok.col)
        elif tok.type == TokenType.STRING:
            self._advance()
            return Literal("string", tok.value, tok.line, tok.col)
        elif tok.type == TokenType.TRUE:
            self._advance()
            return Literal("bool", True, tok.line, tok.col)
        elif tok.type == TokenType.FALSE:
            self._advance()
            return Literal("bool", False, tok.line, tok.col)
        elif tok.type == TokenType.LBRACKET:
            # arrayLiteral = '[' expr { ',' expr } ']'
            lbracket = self._advance()
            self._enter_nested(lbracket)
            elements: list[Expr] = []
            try:
                elements.append(self.parse_expr())
                while self._check(TokenType.COMMA):
                    self._advance()
                    elements.append(self.parse_expr())
                self._consume(TokenType.RBRACKET, "']'")
            finally:
                self._exit_nested()
            return ArrayLiteral(elements=elements, line=lbracket.line, col=lbracket.col)
        elif tok.type in (TokenType.KW_ARRAY, TokenType.KW_LIST, TokenType.KW_STACK, TokenType.KW_QUEUE):
            # newCollection = kind '<' elemType '>' '(' [ args ] ')'
            kind_tok = self._advance()
            self._consume(TokenType.LT, "'<'")
            elem_type = self.parse_elem_type()
            self._consume(TokenType.GT, "'>'")

            lparen = self._consume(TokenType.LPAREN, "'('")
            self._enter_nested(lparen)
            args: list[Expr] = []
            try:
                if not self._check(TokenType.RPAREN):
                    args.append(self.parse_expr())
                    while self._check(TokenType.COMMA):
                        self._advance()
                        args.append(self.parse_expr())
                self._consume(TokenType.RPAREN, "')'")
            finally:
                self._exit_nested()

            return NewCollection(
                kind=kind_tok.lexeme,
                elem_type=elem_type,
                args=args,
                line=kind_tok.line,
                col=kind_tok.col,
            )
        elif tok.type in (TokenType.IDENT, TokenType.MAIN):
            next_tok = self._peek_next()
            if next_tok.type == TokenType.LPAREN:
                return self.parse_call()
            elif next_tok.type == TokenType.DOT:
                return self.parse_method_call()
            else:
                self._advance()
                return Variable(name=tok.lexeme, line=tok.line, col=tok.col)
        elif tok.type == TokenType.LPAREN:
            lparen = self._advance()
            self._enter_nested(lparen)
            try:
                expr = self.parse_expr()
                self._consume(TokenType.RPAREN, "')'")
            finally:
                self._exit_nested()
            expr.start_line = lparen.line
            expr.start_col = lparen.col
            return expr
        else:
            self._error_expected("expression", tok)


def parse(tokens: list[Token]) -> Program:
    """Parse a list of tokens into a Program AST node."""
    parser = Parser(tokens)
    return parser.parse_program()
