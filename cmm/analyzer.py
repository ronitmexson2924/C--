"""Semantic analyzer and type-checking engine for C-- v0.2.0 per §A6 and §A7.1."""

from __future__ import annotations

from typing import Optional
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
from cmm.builtins import BUILTIN_FUNCTION_NAMES, COLLECTION_METHODS
from cmm.errors import SemanticError
from cmm.types import (
    BINARY_OPERATORS,
    Symbol,
    Type,
    UNARY_OPERATORS,
)


class SemanticAnalyzer:
    """Two-pass semantic analyzer implementing C-- v0.2.0 semantics."""

    def __init__(self) -> None:
        self._scopes: list[dict[str, Symbol]] = []
        self._functions: dict[str, FunctionDef] = {}
        self._errors: list[SemanticError] = []
        self._current_function: Optional[FunctionDef] = None

    def _push_scope(self) -> None:
        self._scopes.append({})

    def _pop_scope(self) -> None:
        self._scopes.pop()

    def _lookup(self, name: str) -> Optional[Symbol]:
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        return None

    def _define(self, name: str, symbol: Symbol) -> None:
        if self._scopes:
            self._scopes[-1][name] = symbol

    def _record_error(self, code: str, message: str, line: int, col: int) -> None:
        self._errors.append(SemanticError(code, message, line, col))

    def analyze_program(self, program: Program) -> list[SemanticError]:
        """Analyze full program per §A8.3."""
        # Pass 1: Collect function signatures
        for fn in program.functions:
            fn_name = fn.name
            if fn_name in BUILTIN_FUNCTION_NAMES:
                self._record_error("E010", f"cannot redefine built-in function '{fn_name}'", fn.line, fn.col)
            elif fn_name in self._functions:
                self._record_error("E009", f"function '{fn_name}' is already defined", fn.line, fn.col)
            else:
                self._functions[fn_name] = fn

        # Verify 'main' exists and signature
        if "main" not in self._functions:
            self._record_error("E008", "undefined function 'main'", program.line, program.col)
        else:
            main_fn = self._functions["main"]
            if len(main_fn.params) > 0 or main_fn.ret_type is not None:
                self._record_error("E017", "'main' must have no parameters and no return type", main_fn.line, main_fn.col)

        # Pass 2: Check each function body
        for fn in program.functions:
            self._analyze_function(fn)

        # Sort errors by (line, col)
        self._errors.sort(key=lambda e: (e.line, e.col))
        return self._errors

    def _analyze_function(self, fn: FunctionDef) -> None:
        self._current_function = fn
        self._push_scope()  # Parameter scope

        param_names: set[str] = set()
        for p in fn.params:
            if p.name in param_names:
                self._record_error("E031", f"duplicate parameter '{p.name}'", p.line, p.col)
            else:
                param_names.add(p.name)
                # Parameters are immutable bindings (like 'let')
                self._define(p.name, Symbol(type=p.type, mutable=False, decl_line=p.line, decl_col=p.col))

        # Check body block in child scope (so body can shadow parameters)
        self._analyze_block(fn.body)
        self._pop_scope()

        # Check definitely returns rule (§A6.1.8)
        if fn.ret_type is not None:
            if not self._definitely_returns(fn.body):
                self._record_error("E013", f"function '{fn.name}' does not return a value on all paths", fn.line, fn.col)

    def _definitely_returns(self, stmt: Stmt) -> bool:
        """Conservative 'definitely returns' checker per §A6.1.8."""
        if isinstance(stmt, ReturnStmt):
            return True
        elif isinstance(stmt, Block):
            return any(self._definitely_returns(s) for s in stmt.statements)
        elif isinstance(stmt, If):
            if stmt.else_branch is None:
                return False
            then_ret = self._definitely_returns(stmt.then_block)
            else_ret = self._definitely_returns(stmt.else_branch)
            return then_ret and else_ret
        elif isinstance(stmt, SwitchStmt):
            if stmt.default_body is None:
                return False
            default_ret = self._definitely_returns(stmt.default_body)
            cases_ret = all(self._definitely_returns(c.body) for c in stmt.cases)
            return default_ret and cases_ret
        elif isinstance(stmt, DoWhile):
            return self._definitely_returns(stmt.body)
        return False

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
        elif isinstance(stmt, IndexAssign):
            self._analyze_index_assign(stmt)
        elif isinstance(stmt, CallStmt):
            self._analyze_call_stmt(stmt)
        elif isinstance(stmt, Print):
            self._analyze_print(stmt)
        elif isinstance(stmt, ReturnStmt):
            self._analyze_return_stmt(stmt)
        elif isinstance(stmt, If):
            self._analyze_if(stmt)
        elif isinstance(stmt, While):
            self._analyze_while(stmt)
        elif isinstance(stmt, DoWhile):
            self._analyze_do_while(stmt)
        elif isinstance(stmt, For):
            self._analyze_for(stmt)
        elif isinstance(stmt, SwitchStmt):
            self._analyze_switch_stmt(stmt)
        elif isinstance(stmt, Block):
            self._analyze_block(stmt)

    def _analyze_var_decl(self, stmt: VarDecl) -> None:
        init_type = self._analyze_expr(stmt.init)
        current_scope = self._scopes[-1]
        if stmt.name in current_scope:
            existing = current_scope[stmt.name]
            self._record_error(
                "E002",
                f"variable '{stmt.name}' is already declared in this scope (at line {existing.decl_line}, column {existing.decl_col})",
                stmt.name_line,
                stmt.name_col,
            )
        else:
            self._define(stmt.name, Symbol(type=init_type, mutable=stmt.mutable, decl_line=stmt.name_line, decl_col=stmt.name_col))

    def _analyze_assign(self, stmt: Assign) -> None:
        symbol = self._lookup(stmt.name)
        val_type = self._analyze_expr(stmt.value)
        if symbol is None:
            self._record_error("E001", f"undeclared variable '{stmt.name}'", stmt.line, stmt.col)
            return

        if not symbol.mutable:
            self._record_error(
                "E003",
                f"cannot assign to immutable variable '{stmt.name}' (declared with 'let' at line {symbol.decl_line}, column {symbol.decl_col}); declare it with 'mut' to allow assignment",
                stmt.line,
                stmt.col,
            )
            return

        if symbol.type == Type.INVALID or val_type == Type.INVALID:
            return

        if stmt.op == "=":
            if symbol.type != val_type:
                self._record_error(
                    "E007",
                    f"cannot assign value of type {val_type} to variable '{stmt.name}' of type {symbol.type}",
                    stmt.line,
                    stmt.col,
                )
        else:
            from cmm.types import COMPOUND_TO_BINARY
            base_op = COMPOUND_TO_BINARY[stmt.op]
            if (base_op, symbol.type, val_type) not in BINARY_OPERATORS:
                self._record_error(
                    "E006",
                    f"operator '{stmt.op}' cannot be applied to {symbol.type} and {val_type}",
                    stmt.op_line,
                    stmt.op_col,
                )
            else:
                op_result = BINARY_OPERATORS[(base_op, symbol.type, val_type)]
                if op_result != symbol.type:
                    self._record_error(
                        "E007",
                        f"cannot assign value of type {op_result} to variable '{stmt.name}' of type {symbol.type}",
                        stmt.line,
                        stmt.col,
                    )

    def _analyze_index_assign(self, stmt: IndexAssign) -> None:
        symbol = self._lookup(stmt.name)
        idx_type = self._analyze_expr(stmt.index)
        val_type = self._analyze_expr(stmt.value)

        if symbol is None:
            self._record_error("E001", f"undeclared variable '{stmt.name}'", stmt.line, stmt.col)
            return

        if symbol.type == Type.STRING:
            self._record_error("E030", "strings are immutable; cannot assign to an element", stmt.line, stmt.col)
            return

        if not symbol.mutable:
            self._record_error("E029", f"cannot assign to element of immutable variable '{stmt.name}'", stmt.line, stmt.col)
            return

        if symbol.type.name not in ("array", "list"):
            self._record_error("E024", f"type {symbol.type} cannot be indexed", stmt.line, stmt.col)
            return

        if idx_type != Type.INT and idx_type != Type.INVALID:
            self._record_error("E025", f"index must be int, got {idx_type}", stmt.index.start_line, stmt.index.start_col)

        elem_type = symbol.type.elem if symbol.type.elem else Type.INVALID
        if elem_type == Type.INVALID or val_type == Type.INVALID:
            return

        if stmt.op == "=":
            if elem_type != val_type:
                self._record_error(
                    "E007",
                    f"cannot assign value of type {val_type} to variable '{stmt.name}' of type {elem_type}",
                    stmt.line,
                    stmt.col,
                )
        else:
            from cmm.types import COMPOUND_TO_BINARY
            base_op = COMPOUND_TO_BINARY[stmt.op]
            if (base_op, elem_type, val_type) not in BINARY_OPERATORS:
                self._record_error("E006", f"operator '{stmt.op}' cannot be applied to {elem_type} and {val_type}", stmt.op_line, stmt.op_col)
            else:
                op_result = BINARY_OPERATORS[(base_op, elem_type, val_type)]
                if op_result != elem_type:
                    self._record_error("E007", f"cannot assign value of type {op_result} to variable '{stmt.name}' of type {elem_type}", stmt.line, stmt.col)


    def _analyze_call_stmt(self, stmt: CallStmt) -> None:
        # In statement context, returning void is allowed
        self._analyze_expr(stmt.call, is_statement=True)

    def _analyze_print(self, stmt: Print) -> None:
        self._analyze_expr(stmt.expr)

    def _analyze_return_stmt(self, stmt: ReturnStmt) -> None:
        if self._current_function is None:
            return
        if self._current_function.ret_type is None:
            # Void function
            if stmt.expr is not None:
                self._analyze_expr(stmt.expr)
                self._record_error("E014", f"void function '{self._current_function.name}' cannot return a value", stmt.line, stmt.col)
        else:
            # Non-void function
            if stmt.expr is None:
                self._record_error("E015", f"function '{self._current_function.name}' must return a value of type {self._current_function.ret_type}", stmt.line, stmt.col)
            else:
                ret_val_type = self._analyze_expr(stmt.expr)
                if ret_val_type != Type.INVALID and ret_val_type != self._current_function.ret_type:
                    self._record_error(
                        "E016",
                        f"cannot return {ret_val_type} from function '{self._current_function.name}' declared to return {self._current_function.ret_type}",
                        stmt.expr.start_line,
                        stmt.expr.start_col,
                    )

    def _analyze_if(self, stmt: If) -> None:
        cond_type = self._analyze_expr(stmt.cond)
        if cond_type != Type.BOOL and cond_type != Type.INVALID:
            self._record_error("E004", f"condition must be of type bool, found {cond_type}", stmt.cond.start_line, stmt.cond.start_col)
        self._analyze_block(stmt.then_block)
        if stmt.else_branch is not None:
            if isinstance(stmt.else_branch, Block):
                self._analyze_block(stmt.else_branch)
            else:
                self._analyze_if(stmt.else_branch)

    def _analyze_while(self, stmt: While) -> None:
        cond_type = self._analyze_expr(stmt.cond)
        if cond_type != Type.BOOL and cond_type != Type.INVALID:
            self._record_error("E004", f"condition must be of type bool, found {cond_type}", stmt.cond.start_line, stmt.cond.start_col)
        self._analyze_block(stmt.body)

    def _analyze_do_while(self, stmt: DoWhile) -> None:
        self._analyze_block(stmt.body)
        cond_type = self._analyze_expr(stmt.cond)
        if cond_type != Type.BOOL and cond_type != Type.INVALID:
            self._record_error("E004", f"condition must be of type bool, found {cond_type}", stmt.cond.start_line, stmt.cond.start_col)

    def _analyze_for(self, stmt: For) -> None:
        self._push_scope()
        try:
            if stmt.init is not None:
                if isinstance(stmt.init, VarDecl):
                    self._analyze_var_decl(stmt.init)
                elif isinstance(stmt.init, Assign):
                    self._analyze_assign(stmt.init)
                elif isinstance(stmt.init, IndexAssign):
                    self._analyze_index_assign(stmt.init)

            if stmt.cond is not None:
                cond_type = self._analyze_expr(stmt.cond)
                if cond_type != Type.BOOL and cond_type != Type.INVALID:
                    self._record_error("E004", f"condition must be of type bool, found {cond_type}", stmt.cond.start_line, stmt.cond.start_col)

            if stmt.update is not None:
                if isinstance(stmt.update, Assign):
                    self._analyze_assign(stmt.update)
                elif isinstance(stmt.update, IndexAssign):
                    self._analyze_index_assign(stmt.update)

            self._analyze_block(stmt.body)
        finally:
            self._pop_scope()

    def _analyze_switch_stmt(self, stmt: SwitchStmt) -> None:
        sel_type = self._analyze_expr(stmt.selector)
        if sel_type != Type.INVALID and sel_type not in (Type.INT, Type.STRING):
            self._record_error("E021", f"switch selector must be int or string, got {sel_type}", stmt.selector.start_line, stmt.selector.start_col)

        seen_values: set[object] = set()
        for clause in stmt.cases:
            for val_expr in clause.values:
                val_type = self._analyze_expr(val_expr)
                if sel_type in (Type.INT, Type.STRING) and val_type != Type.INVALID and val_type != sel_type:
                    self._record_error("E022", f"case value of type {val_type} does not match switch selector of type {sel_type}", val_expr.start_line, val_expr.start_col)
                if isinstance(val_expr, Literal):
                    if val_expr.value in seen_values:
                        self._record_error("E023", f"duplicate case value {val_expr.value}", val_expr.line, val_expr.col)
                    else:
                        seen_values.add(val_expr.value)
            self._analyze_block(clause.body)

        if stmt.default_body is not None:
            self._analyze_block(stmt.default_body)

    # -------------------------------------------------------------------------
    # Expression Analysis
    # -------------------------------------------------------------------------

    def _analyze_expr(self, expr: Expr, is_statement: bool = False) -> Type:
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


        elif isinstance(expr, Call):
            return self._analyze_call(expr, is_statement=is_statement)

        elif isinstance(expr, MethodCall):
            return self._analyze_method_call(expr, is_statement=is_statement)

        elif isinstance(expr, Index):
            target_type = self._analyze_expr(expr.target)
            idx_type = self._analyze_expr(expr.index)

            if target_type != Type.INVALID and not target_type.is_indexable():
                self._record_error("E024", f"type {target_type} cannot be indexed", expr.line, expr.col)
                return Type.INVALID

            if idx_type != Type.INVALID and idx_type != Type.INT:
                self._record_error("E025", f"index must be int, got {idx_type}", expr.index.start_line, expr.index.start_col)

            if target_type == Type.STRING:
                return Type.STRING
            elif target_type.elem is not None:
                return target_type.elem
            return Type.INVALID

        elif isinstance(expr, ArrayLiteral):
            if not expr.elements:
                return Type.INVALID
            elem_types = [self._analyze_expr(e) for e in expr.elements]
            t0 = elem_types[0]
            if not t0.is_primitive() and t0 != Type.INVALID:
                self._record_error("E027", "array literal elements must all have the same primitive type", expr.elements[0].start_line, expr.elements[0].start_col)
                return Type.INVALID

            for i, et in enumerate(elem_types[1:], start=1):
                if et != t0 and et != Type.INVALID:
                    self._record_error("E027", "array literal elements must all have the same primitive type", expr.elements[i].start_line, expr.elements[i].start_col)
                    return Type.INVALID

            return Type.coll("array", t0)

        elif isinstance(expr, NewCollection):
            arg_types = [self._analyze_expr(a) for a in expr.args]
            if expr.kind == "array":
                if len(arg_types) != 2:
                    self._record_error("E011", f"constructor 'array' expects 2 argument(s), got {len(arg_types)}", expr.line, expr.col)
                else:
                    if arg_types[0] != Type.INT and arg_types[0] != Type.INVALID:
                        self._record_error("E012", f"argument 1 of constructor 'array' must be int, got {arg_types[0]}", expr.args[0].start_line, expr.args[0].start_col)
                    if arg_types[1] != expr.elem_type and arg_types[1] != Type.INVALID:
                        self._record_error("E012", f"argument 2 of constructor 'array' must be {expr.elem_type}, got {arg_types[1]}", expr.args[1].start_line, expr.args[1].start_col)
            elif expr.kind in ("list", "stack", "queue"):
                if len(arg_types) != 0:
                    self._record_error("E011", f"constructor '{expr.kind}' expects 0 argument(s), got {len(arg_types)}", expr.line, expr.col)

            return Type.coll(expr.kind, expr.elem_type)

        return Type.INVALID

    def _analyze_call(self, call: Call, is_statement: bool = False) -> Type:
        name = call.name
        arg_types = [self._analyze_expr(a) for a in call.args]

        if name == "main":
            self._record_error("E019", "'main' cannot be called", call.line, call.col)
            return Type.INVALID

        if name in BUILTIN_FUNCTION_NAMES:
            if name == "input":
                if len(arg_types) == 0:
                    ret_t = Type.STRING
                elif len(arg_types) == 1:
                    if arg_types[0] != Type.STRING and arg_types[0] != Type.INVALID:
                        self._record_error("E012", f"argument 1 of function 'input' must be string, got {arg_types[0]}", call.args[0].start_line, call.args[0].start_col)
                    ret_t = Type.STRING
                else:
                    self._record_error("E011", f"function 'input' expects 1 argument(s), got {len(arg_types)}", call.line, call.col)
                    ret_t = Type.STRING
            elif name in ("parse_int", "parse_float"):
                exp_t = Type.INT if name == "parse_int" else Type.FLOAT
                if len(arg_types) != 1:
                    self._record_error("E011", f"function '{name}' expects 1 argument(s), got {len(arg_types)}", call.line, call.col)
                else:
                    if arg_types[0] != Type.STRING and arg_types[0] != Type.INVALID:
                        self._record_error("E012", f"argument 1 of function '{name}' must be string, got {arg_types[0]}", call.args[0].start_line, call.args[0].start_col)
                ret_t = exp_t
            return ret_t

        if name not in self._functions:
            self._record_error("E008", f"undefined function '{name}'", call.line, call.col)
            return Type.INVALID

        fn = self._functions[name]
        if len(arg_types) != len(fn.params):
            self._record_error("E011", f"function '{name}' expects {len(fn.params)} argument(s), got {len(arg_types)}", call.line, call.col)
        else:
            for i, (at, p) in enumerate(zip(arg_types, fn.params), start=1):
                if at != p.type and at != Type.INVALID:
                    self._record_error("E012", f"argument {i} of function '{name}' must be {p.type}, got {at}", call.args[i - 1].start_line, call.args[i - 1].start_col)

        ret_type = fn.ret_type if fn.ret_type is not None else Type.VOID
        if ret_type == Type.VOID and not is_statement:
            self._record_error("E020", f"function '{name}' returns no value and cannot be used in an expression", call.line, call.col)
        return ret_type

    def _analyze_method_call(self, call: MethodCall, is_statement: bool = False) -> Type:
        receiver_sym = self._lookup(call.receiver_name)
        arg_types = [self._analyze_expr(a) for a in call.args]

        if receiver_sym is None:
            self._record_error("E001", f"use of undeclared variable '{call.receiver_name}'", call.line, call.col)
            return Type.INVALID

        rec_type = receiver_sym.type
        kind = rec_type.name
        methods = COLLECTION_METHODS.get(kind, {})

        if call.method not in methods:
            self._record_error("E026", f"type {rec_type} has no method '{call.method}'", call.line, call.col)
            return Type.INVALID

        sig = methods[call.method]
        if sig.mutates and not receiver_sym.mutable:
            self._record_error("E028", f"cannot call mutating method '{call.method}' on immutable variable '{call.receiver_name}'", call.line, call.col)

        if len(arg_types) != len(sig.param_types):
            self._record_error("E011", f"method '{call.method}' expects {len(sig.param_types)} argument(s), got {len(arg_types)}", call.line, call.col)
        else:
            for i, (at, exp_pt) in enumerate(zip(arg_types, sig.param_types), start=1):
                exp_t = rec_type.elem if exp_pt == "T" else (Type.INT if exp_pt == "int" else Type.BOOL)
                if at != exp_t and at != Type.INVALID:
                    self._record_error("E012", f"argument {i} of method '{call.method}' must be {exp_t}, got {at}", call.args[i - 1].start_line, call.args[i - 1].start_col)

        ret_t: Type
        if sig.return_type == "void":
            ret_t = Type.VOID
        elif sig.return_type == "int":
            ret_t = Type.INT
        elif sig.return_type == "bool":
            ret_t = Type.BOOL
        elif sig.return_type == "T":
            ret_t = rec_type.elem if rec_type.elem else Type.INVALID
        else:
            ret_t = Type.INVALID

        if ret_t == Type.VOID and not is_statement:
            self._record_error("E020", f"method '{call.method}' returns no value and cannot be used in an expression", call.line, call.col)

        return ret_t

    analyze = analyze_program


def analyze(program: Program) -> list[SemanticError]:
    """Public API: run two-pass semantic analysis on Program AST."""
    analyzer = SemanticAnalyzer()
    return analyzer.analyze_program(program)


