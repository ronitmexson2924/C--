"""Tree-walk interpreter for C-- per Section 7, 8, 9, 10.6, 12.7, and Spec v0.2."""

from __future__ import annotations

import copy
import math
import sys
import threading
from typing import Any, Optional, TextIO

from cmm.ast_nodes import (
    Assign,
    ASTNode,
    ArrayLiteral,
    BinaryOp,
    Block,
    Call,
    CallStmt,
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
from cmm.builtins import BUILTIN_FUNCTION_NAMES
from cmm.errors import CmmRuntimeError
from cmm.formatting import format_value
from cmm.runtime_io import cmm_parse_float, cmm_parse_int, cmm_read_line
from cmm.runtime_values import (
    CmmArray,
    CmmList,
    CmmQueue,
    CmmStack,
    MAX_COLLECTION_SIZE,
    copy_value,
)

INT64_MIN = -9223372036854775808
INT64_MAX = 9223372036854775807


class ReturnSignal(Exception):
    """Internal exception raised to handle return statements."""

    def __init__(self, value: Any = None) -> None:
        super().__init__()
        self.value = value


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

    def __init__(
        self,
        out: TextIO,
        max_steps: Optional[int] = None,
        stdin: Optional[TextIO] = None,
    ) -> None:
        self._out = out
        self._max_steps = max_steps
        self._stdin = stdin if stdin is not None else sys.stdin
        self._steps = 0
        self._envs: list[dict[str, object]] = []
        self._functions: dict[str, FunctionDef] = {}
        self._call_depth = 0

    def _step(self, node: ASTNode) -> None:
        """Increment step counter and check max-steps bound (R005) per §10.6."""
        if self._max_steps is not None:
            if self._steps + 1 > self._max_steps:
                raise CmmRuntimeError(
                    "R005",
                    f"step limit exceeded ({self._max_steps} steps)",
                    node.line,
                    node.col,
                    details={"max_steps": self._max_steps},
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
        """Execute the program starting from main() at call depth 0 (§A6.1)."""
        main_func = None
        for fn in program.functions:
            if fn.name == "main":
                main_func = fn
                break

        if main_func is None:
            raise CmmRuntimeError("R000", "internal error: main function not found", 1, 1)

        self._functions = {fn.name: fn for fn in program.functions}

        err: list[BaseException] = []

        def _worker() -> None:
            try:
                sys.setrecursionlimit(50000)
                self._call_depth = 0
                self._call_function(main_func, [], main_func.line, main_func.col)
            except ReturnSignal:
                pass
            except BaseException as e:
                err.append(e)

        try:
            threading.stack_size(256 * 1024 * 1024)
        except (ValueError, OverflowError):
            pass

        t = threading.Thread(target=_worker)
        t.start()
        t.join()

        if err:
            raise err[0]

    def _call_function(
        self,
        func_def: FunctionDef,
        args: list[Any],
        line: int,
        col: int,
    ) -> Any:
        """Execute user-defined function in a fresh environment per §A6.1."""
        if self._call_depth >= 1000:
            raise CmmRuntimeError("R007", "call depth limit exceeded (1000)", line, col, details={"limit": 1000})

        self._call_depth += 1
        saved_envs = self._envs

        # Parameters enclosed in scope around body block
        param_env = {
            param.name: copy_value(val)
            for param, val in zip(func_def.params, args)
        }
        self._envs = [param_env]

        try:
            self._execute_block(func_def.body)
            return None
        except ReturnSignal as sig:
            return sig.value
        finally:
            self._envs = saved_envs
            self._call_depth -= 1

    def _execute_stmt(self, stmt: Stmt) -> None:
        if isinstance(stmt, VarDecl):
            self._step(stmt)
            val = copy_value(self._eval_expr(stmt.init))
            self._define(stmt.name, val)

        elif isinstance(stmt, Assign):
            self._step(stmt)
            self._execute_assign(stmt)

        elif isinstance(stmt, IndexAssign):
            self._step(stmt)
            self._execute_index_assign(stmt)

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
                    self._step(stmt.init)
                    if isinstance(stmt.init, VarDecl):
                        init_val = copy_value(self._eval_expr(stmt.init.init))
                        self._define(stmt.init.name, init_val)
                    elif isinstance(stmt.init, Assign):
                        self._execute_assign(stmt.init)
                    elif isinstance(stmt.init, IndexAssign):
                        self._execute_index_assign(stmt.init)

                while True:
                    if stmt.cond is not None:
                        self._step(stmt)  # Step on condition evaluation (§10.6)
                        cond_val = self._eval_expr(stmt.cond)
                        if cond_val is not True:
                            break
                    self._execute_block(stmt.body)
                    if stmt.update is not None:
                        self._step(stmt.update)
                        if isinstance(stmt.update, Assign):
                            self._execute_assign(stmt.update)
                        elif isinstance(stmt.update, IndexAssign):
                            self._execute_index_assign(stmt.update)
            finally:
                self._pop_env()

        elif isinstance(stmt, SwitchStmt):
            self._step(stmt)
            self._execute_switch(stmt)

        elif isinstance(stmt, ReturnStmt):
            self._step(stmt)
            val = copy_value(self._eval_expr(stmt.expr)) if stmt.expr is not None else None
            raise ReturnSignal(val)

        elif isinstance(stmt, CallStmt):
            self._step(stmt)
            self._eval_expr(stmt.call)

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
        rhs_val = copy_value(self._eval_expr(assign.value))
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
            self._set_var(assign.name, copy_value(new_val), assign.line, assign.col)

    def _execute_index_assign(self, assign: IndexAssign) -> None:
        target_val = self._get_var(assign.name, assign.line, assign.col)
        idx_val = self._eval_expr(assign.index)
        rhs_val = copy_value(self._eval_expr(assign.value))

        if not isinstance(target_val, (CmmArray, CmmList)):
            raise CmmRuntimeError("R000", "internal error: index assign target is not array or list", assign.line, assign.col)

        if not isinstance(idx_val, int):
            raise CmmRuntimeError("R000", "internal error: index is not int", assign.line, assign.col)

        if assign.op == "=":
            target_val.set(idx_val, rhs_val, assign.line, assign.col)
        else:
            cur_val = target_val.get(idx_val, assign.line, assign.col)
            new_val = self._compute_binary_op(
                assign.op[:-1],
                cur_val,
                rhs_val,
                assign.op_line,
                assign.op_col,
            )
            target_val.set(idx_val, copy_value(new_val), assign.line, assign.col)

    def _execute_switch(self, switch: SwitchStmt) -> None:
        selector_val = self._eval_expr(switch.selector)
        for clause in switch.cases:
            clause_values = [self._eval_expr(v) for v in clause.values]
            if selector_val in clause_values:
                self._execute_block(clause.body)
                return

        if switch.default_body is not None:
            self._execute_block(switch.default_body)

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

        elif isinstance(expr, Call):
            return self._eval_call(expr)

        elif isinstance(expr, MethodCall):
            return self._eval_method_call(expr)

        elif isinstance(expr, Index):
            return self._eval_index(expr)

        elif isinstance(expr, ArrayLiteral):
            elements = [copy_value(self._eval_expr(el)) for el in expr.elements]
            return CmmArray(elements)

        elif isinstance(expr, NewCollection):
            return self._eval_new_collection(expr)

        raise CmmRuntimeError("R000", f"internal error: unexpected expression node {type(expr)}", expr.line, expr.col)

    def _eval_call(self, call: Call) -> Any:
        """Evaluate function call or built-in function per §A6.1 and §A6.2."""
        if call.name in BUILTIN_FUNCTION_NAMES:
            if call.name == "input":
                if len(call.args) == 0:
                    return cmm_read_line(self._stdin, line=call.line, col=call.col)
                elif len(call.args) == 1:
                    prompt = self._eval_expr(call.args[0])
                    if not isinstance(prompt, str):
                        raise CmmRuntimeError("R000", "internal error: prompt must be string", call.line, call.col)
                    self._out.write(prompt)
                    self._out.flush()
                    return cmm_read_line(self._stdin, line=call.line, col=call.col)

            elif call.name == "parse_int":
                arg_val = self._eval_expr(call.args[0])
                if not isinstance(arg_val, str):
                    raise CmmRuntimeError("R000", "internal error: parse_int arg must be string", call.line, call.col)
                return cmm_parse_int(arg_val, call.line, call.col)

            elif call.name == "parse_float":
                arg_val = self._eval_expr(call.args[0])
                if not isinstance(arg_val, str):
                    raise CmmRuntimeError("R000", "internal error: parse_float arg must be string", call.line, call.col)
                return cmm_parse_float(arg_val, call.line, call.col)

        func_def = self._functions.get(call.name)
        if func_def is None:
            raise CmmRuntimeError("R000", f"internal error: function '{call.name}' not found", call.line, call.col)

        evaluated_args = [copy_value(self._eval_expr(arg)) for arg in call.args]
        return self._call_function(func_def, evaluated_args, call.line, call.col)

    def _eval_method_call(self, call: MethodCall) -> Any:
        """Evaluate collection or string method call per §A6.4."""
        rec = self._get_var(call.receiver_name, call.line, call.col)
        evaluated_args = [self._eval_expr(arg) for arg in call.args]

        if call.method == "len":
            if isinstance(rec, str):
                return len(rec)
            elif isinstance(rec, (CmmArray, CmmList, CmmStack, CmmQueue)):
                return rec.len()

        elif call.method == "is_empty":
            if isinstance(rec, (CmmList, CmmStack, CmmQueue)):
                return rec.is_empty()

        elif call.method == "contains":
            if isinstance(rec, CmmList):
                return rec.contains(evaluated_args[0])

        elif call.method == "push":
            if isinstance(rec, (CmmList, CmmStack)):
                rec.push(copy_value(evaluated_args[0]), call.line, call.col)
                return None

        elif call.method == "pop":
            if isinstance(rec, (CmmList, CmmStack)):
                return copy_value(rec.pop(call.line, call.col))

        elif call.method == "insert":
            if isinstance(rec, CmmList):
                rec.insert(evaluated_args[0], copy_value(evaluated_args[1]), call.line, call.col)
                return None

        elif call.method == "remove":
            if isinstance(rec, CmmList):
                return copy_value(rec.remove(evaluated_args[0], call.line, call.col))

        elif call.method == "clear":
            if isinstance(rec, (CmmList, CmmStack, CmmQueue)):
                rec.clear()
                return None

        elif call.method == "enqueue":
            if isinstance(rec, CmmQueue):
                rec.enqueue(copy_value(evaluated_args[0]), call.line, call.col)
                return None

        elif call.method == "dequeue":
            if isinstance(rec, CmmQueue):
                return copy_value(rec.dequeue(call.line, call.col))

        elif call.method == "peek":
            if isinstance(rec, (CmmStack, CmmQueue)):
                return copy_value(rec.peek(call.line, call.col))

        raise CmmRuntimeError("R000", f"internal error: unhandled method '{call.method}'", call.line, call.col)

    def _eval_index(self, node: Index) -> Any:
        """Evaluate indexing s[i] or a[i] per §A6.3 and §A6.4."""
        target_val = self._eval_expr(node.target)
        idx_val = self._eval_expr(node.index)

        if not isinstance(idx_val, int):
            raise CmmRuntimeError("R000", "internal error: index must be int", node.line, node.col)

        if isinstance(target_val, str):
            if idx_val < 0 or idx_val >= len(target_val):
                raise CmmRuntimeError(
                    "R006",
                    f"index out of range (index {idx_val}, length {len(target_val)})",
                    node.line,
                    node.col,
                    details={
                        "index": idx_val,
                        "length": len(target_val),
                        "max_index": max(0, len(target_val) - 1),
                        "kind": "string",
                    },
                )
            return target_val[idx_val]

        elif isinstance(target_val, (CmmArray, CmmList)):
            return copy_value(target_val.get(idx_val, node.line, node.col))

        raise CmmRuntimeError("R000", f"internal error: cannot index {type(target_val)}", node.line, node.col)

    def _eval_new_collection(self, node: NewCollection) -> Any:
        """Construct new collection per §A6.4."""
        if node.kind == "array":
            n = self._eval_expr(node.args[0])
            fill = copy_value(self._eval_expr(node.args[1]))
            if not isinstance(n, int):
                raise CmmRuntimeError("R000", "internal error: array size must be int", node.line, node.col)
            if n < 0:
                raise CmmRuntimeError("R014", f"array size must not be negative (got {n})", node.line, node.col, details={"size": n})
            if n > MAX_COLLECTION_SIZE:
                raise CmmRuntimeError("R013", f"collection size limit exceeded ({MAX_COLLECTION_SIZE})", node.line, node.col, details={"limit": MAX_COLLECTION_SIZE})
            return CmmArray([copy.deepcopy(fill) for _ in range(n)])

        elif node.kind == "list":
            return CmmList([])

        elif node.kind == "stack":
            return CmmStack([])

        elif node.kind == "queue":
            return CmmQueue([])

        raise CmmRuntimeError("R000", f"internal error: unknown collection kind '{node.kind}'", node.line, node.col)

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


def run(
    program: Program,
    out: TextIO,
    max_steps: Optional[int] = None,
    stdin: Optional[TextIO] = None,
) -> None:
    """Execute a C-- AST program per Section 12.3 and Section 12.7.

    Args:
        program: Parsed Program AST node (assumed to have passed semantic analysis).
        out: TextIO output stream for print statements.
        max_steps: Optional maximum execution step limit (raises R005 if exceeded).
        stdin: Optional input stream for input() built-in.

    Raises:
        CmmRuntimeError: Upon encountering any runtime error (R001 - R014).
    """
    interpreter = Interpreter(out, max_steps, stdin=stdin)
    interpreter.run_program(program)
