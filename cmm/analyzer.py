"""Semantic analyzer and type checker for C-- per Sections 4, 6, 7.2, 10.5, and 12.6."""

from __future__ import annotations

from typing import Optional

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
from cmm.errors import SemanticError
from cmm.types import (
    BINARY_OPERATORS,
    COMPOUND_TO_BINARY,
    Symbol,
    Type,
    UNARY_OPERATORS,
)


class Analyzer:
    """Semantic analyzer implementing C-- scope rules, type checking, and cascade suppression."""

    def __init__(self) -> None:
        self._scopes: list[dict[str, Symbol]] = []
        self._errors: list[SemanticError] = []

    def _push_scope(self) -> None:
        self._scopes.append({})

    def _pop_scope(self) -> None:
        self._scopes.pop()

    def _lookup(self, name: str) -> Optional[Symbol]:
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        return None

    def _lookup_current_scope(self, name: str) -> Optional[Symbol]:
        if self._scopes:
            return self._scopes[-1].get(name)
        return None

    def _declare(self, name: str, symbol: Symbol) -> None:
        if self._scopes:
            self._scopes[-1][name] = symbol

    def _record_error(self, code: str, message: str, line: int, col: int) -> None:
        self._errors.append(SemanticError(code, message, line, col))

    def analyze_program(self, program: Program) -> list[SemanticError]:
        """Analyze program starting at main body block."""
        self._analyze_block(program.body)
        # Sort errors by (line, col); ties preserve discovery order (§10.2)
        self._errors.sort(key=lambda e: (e.line, e.col))
        return self._errors

    def _analyze_block(self, block: Block) -> None:
        self._push_scope()
        try:
            for stmt in block.statements:
                self._analyze_stmt(stmt)
        finally:
            self._pop_scope()

    def _analyze_stmt(self, stmt: Stmt) -> None:
        if isinstance(stmt, VarDecl):
            self._analyze_var_decl(stmt)
        elif isinstance(stmt, Assign):
            self._analyze_assign(stmt)
        elif isinstance(stmt, Print):
            self._analyze_print(stmt)
        elif isinstance(stmt, If):
            self._analyze_if(stmt)
        elif isinstance(stmt, While):
            self._analyze_while(stmt)
        elif isinstance(stmt, DoWhile):
            self._analyze_do_while(stmt)
        elif isinstance(stmt, For):
            self._analyze_for(stmt)
        elif isinstance(stmt, Block):
            self._analyze_block(stmt)

    def _analyze_var_decl(self, decl: VarDecl) -> None:
        """Analyze variable declaration per §6.1, §6.2, and §10.5.

        Rule: Initializer is analyzed before the name is added to the scope.
        Rule: Redeclaration in the same scope produces E002 (earlier declaration remains in effect).
        """
        init_type = self._analyze_expr(decl.init)

        existing = self._lookup_current_scope(decl.name)
        if existing is not None:
            self._record_error(
                "E002",
                f"variable '{decl.name}' is already declared in this scope (at line {existing.decl_line}, column {existing.decl_col})",
                decl.name_line,
                decl.name_col,
            )
            # Earlier declaration remains in effect; do not overwrite
        else:
            self._declare(
                decl.name,
                Symbol(
                    type=init_type,
                    mutable=decl.mutable,
                    decl_line=decl.name_line,
                    decl_col=decl.name_col,
                ),
            )

    def _analyze_assign(self, assign: Assign) -> None:
        """Analyze assignment statement per §6.3 and §10.5.

        Rules:
        - name must be declared (E001) and mut (E003).
        - RHS is analyzed even if target is undeclared (§10.5).
        - Simple assignment requires exact type match (E007).
        - Compound assignment checked as binary op (E006), then result type match (E007).
        """
        sym = self._lookup(assign.name)

        target_type: Type = Type.INVALID
        if sym is None:
            self._record_error("E001", f"undeclared variable '{assign.name}'", assign.line, assign.col)
            # Target is invalid; suppress cascade errors
        else:
            target_type = sym.type
            if not sym.mutable:
                self._record_error(
                    "E003",
                    f"cannot assign to immutable variable '{assign.name}' (declared with 'let' at line {sym.decl_line}, column {sym.decl_col}); declare it with 'mut' to allow assignment",
                    assign.line,
                    assign.col,
                )

        val_type = self._analyze_expr(assign.value)

        # Cascade suppression (§10.5)
        if target_type == Type.INVALID or val_type == Type.INVALID:
            return

        if assign.op == "=":
            if val_type != target_type:
                self._record_error(
                    "E007",
                    f"cannot assign value of type {val_type} to variable '{assign.name}' of type {target_type}",
                    assign.line,
                    assign.col,
                )
        else:
            # Compound assignment op in += -= *= /= %=
            base_op = COMPOUND_TO_BINARY[assign.op]
            if (base_op, target_type, val_type) not in BINARY_OPERATORS:
                self._record_error(
                    "E006",
                    f"operator '{assign.op}' cannot be applied to {target_type} and {val_type}",
                    assign.op_line,
                    assign.op_col,
                )
            else:
                result_type = BINARY_OPERATORS[(base_op, target_type, val_type)]
                if result_type != target_type:
                    self._record_error(
                        "E007",
                        f"cannot assign value of type {result_type} to variable '{assign.name}' of type {target_type}",
                        assign.line,
                        assign.col,
                    )

    def _analyze_print(self, print_stmt: Print) -> None:
        self._analyze_expr(print_stmt.expr)

    def _analyze_if(self, if_stmt: If) -> None:
        cond_type = self._analyze_expr(if_stmt.cond)
        if cond_type != Type.INVALID and cond_type != Type.BOOL:
            self._record_error(
                "E004",
                f"condition must be of type bool, found {cond_type}",
                if_stmt.cond.start_line,
                if_stmt.cond.start_col,
            )

        self._analyze_block(if_stmt.then_block)

        if if_stmt.else_branch is not None:
            if isinstance(if_stmt.else_branch, If):
                self._analyze_if(if_stmt.else_branch)
            else:
                self._analyze_block(if_stmt.else_branch)

    def _analyze_while(self, while_stmt: While) -> None:
        cond_type = self._analyze_expr(while_stmt.cond)
        if cond_type != Type.INVALID and cond_type != Type.BOOL:
            self._record_error(
                "E004",
                f"condition must be of type bool, found {cond_type}",
                while_stmt.cond.start_line,
                while_stmt.cond.start_col,
            )
        self._analyze_block(while_stmt.body)

    def _analyze_do_while(self, do_while: DoWhile) -> None:
        """Analyze do-while loop per §6.2.

        Rule: Variables declared inside body are not visible in the condition.
        """
        self._analyze_block(do_while.body)

        cond_type = self._analyze_expr(do_while.cond)
        if cond_type != Type.INVALID and cond_type != Type.BOOL:
            self._record_error(
                "E004",
                f"condition must be of type bool, found {cond_type}",
                do_while.cond.start_line,
                do_while.cond.start_col,
            )

    def _analyze_for(self, for_stmt: For) -> None:
        """Analyze for loop per §6.2.

        Rule: A for statement creates its own loop scope for forInit.
        Rule: Loop body block is a separate nested scope inside the loop scope.
        """
        self._push_scope()
        try:
            if for_stmt.init is not None:
                if isinstance(for_stmt.init, VarDecl):
                    self._analyze_var_decl(for_stmt.init)
                elif isinstance(for_stmt.init, Assign):
                    self._analyze_assign(for_stmt.init)

            if for_stmt.cond is not None:
                cond_type = self._analyze_expr(for_stmt.cond)
                if cond_type != Type.INVALID and cond_type != Type.BOOL:
                    self._record_error(
                        "E004",
                        f"condition must be of type bool, found {cond_type}",
                        for_stmt.cond.start_line,
                        for_stmt.cond.start_col,
                    )

            if for_stmt.update is not None:
                self._analyze_assign(for_stmt.update)

            self._analyze_block(for_stmt.body)
        finally:
            self._pop_scope()

    def _analyze_expr(self, expr: Expr) -> Type:
        if isinstance(expr, Literal):
            if expr.type == "int":
                return Type.INT
            elif expr.type == "float":
                return Type.FLOAT
            elif expr.type == "bool":
                return Type.BOOL
            elif expr.type == "string":
                return Type.STRING
            return Type.INVALID

        elif isinstance(expr, Variable):
            sym = self._lookup(expr.name)
            if sym is None:
                self._record_error("E001", f"undeclared variable '{expr.name}'", expr.line, expr.col)
                return Type.INVALID
            return sym.type

        elif isinstance(expr, UnaryOp):
            operand_type = self._analyze_expr(expr.operand)
            if operand_type == Type.INVALID:
                return Type.INVALID
            if (expr.op, operand_type) not in UNARY_OPERATORS:
                self._record_error(
                    "E005",
                    f"operator '{expr.op}' cannot be applied to {operand_type}",
                    expr.line,
                    expr.col,
                )
                return Type.INVALID
            return UNARY_OPERATORS[(expr.op, operand_type)]

        elif isinstance(expr, BinaryOp):
            # Both operands are analyzed even when one is erroneous (§10.5)
            left_type = self._analyze_expr(expr.left)
            right_type = self._analyze_expr(expr.right)

            if left_type == Type.INVALID or right_type == Type.INVALID:
                return Type.INVALID

            if (expr.op, left_type, right_type) not in BINARY_OPERATORS:
                self._record_error(
                    "E006",
                    f"operator '{expr.op}' cannot be applied to {left_type} and {right_type}",
                    expr.line,
                    expr.col,
                )
                return Type.INVALID
            return BINARY_OPERATORS[(expr.op, left_type, right_type)]

        return Type.INVALID


def analyze(program: Program) -> list[SemanticError]:
    """Analyze a C-- AST program for semantic correctness per Section 12.3.

    Args:
        program: The parsed Program AST node.

    Returns:
        List of SemanticError instances, sorted by (line, col). Empty list means valid.
    """
    analyzer = Analyzer()
    return analyzer.analyze_program(program)
