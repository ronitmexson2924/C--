"""Tree-walk interpreter for C-- per Section 7, 8, 9, 10.6, and 12.7."""

from __future__ import annotations

import math
from typing import Optional, TextIO

from cmm.ast_nodes import (
    Assign,
    ASTNode,
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
from cmm.errors import CmmRuntimeError
from cmm.formatting import format_value

INT64_MIN = -9223372036854775808
INT64_MAX = 9223372036854775807


def _check_int_range(val: int, line: int, col: int) -> int:
    """Ensure integer is within 64-bit signed range [-2^63, 2^63 - 1] (R001)."""
    if val < INT64_MIN or val > INT64_MAX:
        raise CmmRuntimeError("R001", "integer overflow", line, col)
    return val


def _int_div(a: int, b: int, line: int, col: int) -> int:
    """Integer division truncated toward zero per Section 7.3."""
    if b == 0:
        raise CmmRuntimeError("R002", "division by zero", line, col)
    if a == INT64_MIN and b == -1:
        raise CmmRuntimeError("R001", "integer overflow", line, col)
    sign = -1 if (a < 0) ^ (b < 0) else 1
    res = sign * (abs(a) // abs(b))
    return _check_int_range(res, line, col)


def _int_mod(a: int, b: int, line: int, col: int) -> int:
    """Integer modulo with sign of dividend per Section 7.3."""
    if b == 0:
        raise CmmRuntimeError("R003", "modulo by zero", line, col)
    if a == INT64_MIN and b == -1:
        # Defined as 0 (no error) per §7.3
        return 0
    sign = -1 if (a < 0) ^ (b < 0) else 1
    q = sign * (abs(a) // abs(b))
    return a - q * b


def _float_check(val: float, line: int, col: int) -> float:
    """Check that float result is not infinite (R004)."""
    if math.isinf(val):
        raise CmmRuntimeError("R004", "float overflow", line, col)
    return val


def _float_div(a: float, b: float, line: int, col: int) -> float:
    """Float division checking divisor for zero before dividing (R002)."""
    if b == 0.0:
        raise CmmRuntimeError("R002", "division by zero", line, col)
    res = a / b
    return _float_check(res, line, col)


class Interpreter:
    """Tree-walking interpreter maintaining scope environments and execution steps."""

    def __init__(self, out: TextIO, max_steps: Optional[int] = None) -> None:
        self._out = out
        self._max_steps = max_steps
        self._steps = 0
        self._envs: list[dict[str, object]] = []

    def _step(self, node: ASTNode) -> None:
        """Increment step counter and check max-steps bound (R005) per §10.6."""
        if self._max_steps is not None:
            if self._steps + 1 > self._max_steps:
                raise CmmRuntimeError(
                    "R005",
                    f"step limit exceeded ({self._max_steps} steps)",
                    node.line,
                    node.col,
                )
            self._steps += 1

    def _push_env(self) -> None:
        self._envs.append({})

    def _pop_env(self) -> None:
        self._envs.pop()

    def _define(self, name: str, val: object) -> None:
        self._envs[-1][name] = val

    def _set_var(self, name: str, val: object, line: int, col: int) -> None:
        for env in reversed(self._envs):
            if name in env:
                env[name] = val
                return
        raise CmmRuntimeError("R000", f"internal error: variable '{name}' not found", line, col)

    def _get_var(self, name: str, line: int, col: int) -> object:
        for env in reversed(self._envs):
            if name in env:
                return env[name]
        raise CmmRuntimeError("R000", f"internal error: variable '{name}' not found", line, col)

    def run_program(self, program: Program) -> None:
        """Execute the statements of main body block in order (§5.1)."""
        self._execute_block(program.body)

    def _execute_stmt(self, stmt: Stmt) -> None:
        if isinstance(stmt, VarDecl):
            self._step(stmt)
            val = self._eval_expr(stmt.init)
            self._define(stmt.name, val)
        elif isinstance(stmt, Assign):
            self._step(stmt)
            self._execute_assign(stmt)
        elif isinstance(stmt, Print):
            self._step(stmt)
            val = self._eval_expr(stmt.expr)
            self._out.write(format_value(val) + "\n")
        elif isinstance(stmt, If):
            self._step(stmt)
            cond_val = self._eval_expr(stmt.cond)
            if cond_val is True:
                self._execute_block(stmt.then_block)
            elif stmt.else_branch is not None:
                if isinstance(stmt.else_branch, If):
                    self._execute_stmt(stmt.else_branch)
                else:
                    self._execute_block(stmt.else_branch)
        elif isinstance(stmt, While):
            self._step(stmt)
            while True:
                self._step(stmt)  # Step on loop condition evaluation (§10.6)
                cond_val = self._eval_expr(stmt.cond)
                if cond_val is not True:
                    break
                self._execute_block(stmt.body)
        elif isinstance(stmt, DoWhile):
            self._step(stmt)
            while True:
                self._execute_block(stmt.body)
                self._step(stmt)  # Step on loop condition evaluation (§10.6)
                cond_val = self._eval_expr(stmt.cond)
                if cond_val is not True:
                    break
        elif isinstance(stmt, For):
            self._step(stmt)
            self._push_env()  # Loop scope (§6.2, §8)
            try:
                if stmt.init is not None:
                    if isinstance(stmt.init, VarDecl):
                        self._step(stmt.init)
                        init_val = self._eval_expr(stmt.init.init)
                        self._define(stmt.init.name, init_val)
                    elif isinstance(stmt.init, Assign):
                        self._step(stmt.init)
                        self._execute_assign(stmt.init)

                while True:
                    if stmt.cond is not None:
                        self._step(stmt)  # Step on condition evaluation (§10.6)
                        cond_val = self._eval_expr(stmt.cond)
                        if cond_val is not True:
                            break
                    self._execute_block(stmt.body)
                    if stmt.update is not None:
                        self._step(stmt.update)
                        self._execute_assign(stmt.update)
            finally:
                self._pop_env()
        elif isinstance(stmt, Block):
            self._execute_block(stmt)

    def _execute_block(self, block: Block) -> None:
        self._step(block)
        self._push_env()
        try:
            for s in block.statements:
                self._execute_stmt(s)
        finally:
            self._pop_env()

    def _execute_assign(self, assign: Assign) -> None:
        rhs_val = self._eval_expr(assign.value)
        if assign.op == "=":
            self._set_var(assign.name, rhs_val, assign.line, assign.col)
        else:
            cur_val = self._get_var(assign.name, assign.line, assign.col)
            new_val = self._compute_binary_op(
                assign.op[:-1],  # '+=' -> '+'
                cur_val,
                rhs_val,
                assign.op_line,
                assign.op_col,
            )
            self._set_var(assign.name, new_val, assign.line, assign.col)

    def _eval_expr(self, expr: Expr) -> object:
        if isinstance(expr, Literal):
            return expr.value

        elif isinstance(expr, Variable):
            return self._get_var(expr.name, expr.line, expr.col)

        elif isinstance(expr, UnaryOp):
            val = self._eval_expr(expr.operand)
            if expr.op == "!":
                return not val
            elif expr.op == "-":
                if type(val) is int:
                    return _check_int_range(-val, expr.line, expr.col)
                elif type(val) is float:
                    return -val
                raise CmmRuntimeError("R000", f"internal error: cannot negate {type(val)}", expr.line, expr.col)

        elif isinstance(expr, BinaryOp):
            # Short-circuit logic for && and || (§7.1, §7.4)
            if expr.op == "&&":
                left_val = self._eval_expr(expr.left)
                if left_val is False:
                    return False
                return self._eval_expr(expr.right)

            elif expr.op == "||":
                left_val = self._eval_expr(expr.left)
                if left_val is True:
                    return True
                return self._eval_expr(expr.right)

            # Left operand evaluated before right operand (§7.1)
            left_val = self._eval_expr(expr.left)
            right_val = self._eval_expr(expr.right)
            return self._compute_binary_op(expr.op, left_val, right_val, expr.line, expr.col)

        raise CmmRuntimeError("R000", f"internal error: unexpected expression node {type(expr)}", expr.line, expr.col)

    def _compute_binary_op(self, op: str, left: object, right: object, line: int, col: int) -> object:
        # Check booleans and strings explicitly to prevent Python's bool subclassing int pitfall
        if type(left) is bool or type(right) is bool:
            if op == "==":
                return left == right
            elif op == "!=":
                return left != right
            raise CmmRuntimeError("R000", f"internal error: invalid bool operation {op}", line, col)

        if type(left) is str or type(right) is str:
            if op == "==":
                return left == right
            elif op == "!=":
                return left != right
            raise CmmRuntimeError("R000", f"internal error: invalid string operation {op}", line, col)

        # Mixed arithmetic / comparison: convert int to float first (§7.2, §12.7)
        if type(left) is int and type(right) is float:
            left = float(left)
        elif type(left) is float and type(right) is int:
            right = float(right)

        # Integer arithmetic
        if type(left) is int and type(right) is int:
            if op == "+":
                return _check_int_range(left + right, line, col)
            elif op == "-":
                return _check_int_range(left - right, line, col)
            elif op == "*":
                return _check_int_range(left * right, line, col)
            elif op == "/":
                return _int_div(left, right, line, col)
            elif op == "%":
                return _int_mod(left, right, line, col)
            elif op == "<":
                return left < right
            elif op == "<=":
                return left <= right
            elif op == ">":
                return left > right
            elif op == ">=":
                return left >= right
            elif op == "==":
                return left == right
            elif op == "!=":
                return left != right

        # Float arithmetic
        elif type(left) is float and type(right) is float:
            if op == "+":
                return _float_check(left + right, line, col)
            elif op == "-":
                return _float_check(left - right, line, col)
            elif op == "*":
                return _float_check(left * right, line, col)
            elif op == "/":
                return _float_div(left, right, line, col)
            elif op == "<":
                return left < right
            elif op == "<=":
                return left <= right
            elif op == ">":
                return left > right
            elif op == ">=":
                return left >= right
            elif op == "==":
                return left == right
            elif op == "!=":
                return left != right

        raise CmmRuntimeError("R000", f"internal error: unsupported operation {op} on {type(left)} and {type(right)}", line, col)


def run(program: Program, out: TextIO, max_steps: Optional[int] = None) -> None:
    """Execute a C-- AST program per Section 12.3 and Section 12.7.

    Args:
        program: Parsed Program AST node (assumed to have passed semantic analysis).
        out: TextIO output stream for print statements.
        max_steps: Optional maximum execution step limit (raises R005 if exceeded).

    Raises:
        CmmRuntimeError: Upon encountering any runtime error (R001 - R005).
    """
    interpreter = Interpreter(out, max_steps)
    interpreter.run_program(program)
