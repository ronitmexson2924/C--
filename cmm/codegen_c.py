"""C99 code generator for C-- per Section 16."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Optional, Union

from cmm.ast_nodes import (
    ASTNode,
    ArrayLiteral,
    Assign,
    BinaryOp,
    Block,
    Call,
    CallStmt,
    DoWhile,
    Expr,
    For,
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
from cmm.errors import CmmError, TranspileError
from cmm.types import (
    BINARY_OPERATORS,
    COMPOUND_TO_BINARY,
    Type,
    UNARY_OPERATORS,
)


@dataclass
class CVar:
    """A variable symbol in the C codegen environment."""

    c_name: str
    type: Type
    mutable: bool


def to_c_string_literal(s: str) -> str:
    """Convert a string to a C99 string literal using \\xNN hex escapes per §16."""
    raw_bytes = s.encode("utf-8")
    escapes = "".join(f"\\x{b:02x}" for b in raw_bytes)
    return f'"{escapes}"'


C_RUNTIME_HEADER = r"""#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <float.h>
#include <inttypes.h>
"""

RUNTIME_ERROR_HELPER = r"""static void cmm_runtime_error(const char *msg, int line, int col) {
    fflush(stdout);
    fprintf(stderr, "%s:%d:%d: runtime error: %s\n", cmm_source_path, line, col, msg);
    const char *src = (line >= 1 && line <= CMM_NUM_SOURCE_LINES) ? cmm_source_lines[line - 1] : "";
    int lw = 1;
    for (int t = line; t >= 10; t /= 10) lw++;
    for (int i = 0; i <= lw; i++) fputc(' ', stderr);
    fprintf(stderr, "|\n");
    fprintf(stderr, "%*d | %s\n", lw, line, src);
    for (int i = 0; i <= lw; i++) fputc(' ', stderr);
    fprintf(stderr, "| ");
    const char *p = src;
    for (int i = 0; i < col - 1; i++) {
        if (*p != '\0') {
            if (*p == '\t') {
                fputc('\t', stderr);
                p++;
            } else {
                fputc(' ', stderr);
                p++;
                while ((*p & 0xC0) == 0x80) p++;
            }
        } else {
            fputc(' ', stderr);
        }
    }
    fputc('^', stderr);
    fputc('\n', stderr);

    if (strcmp(msg, "integer overflow") == 0) {
        fprintf(stderr, "what went wrong:\n");
        fprintf(stderr, "  The arithmetic calculation produced an integer too large to fit in 64\n");
        fprintf(stderr, "  bits.\n");
        fprintf(stderr, "how to fix:\n");
        fprintf(stderr, "  Check the numbers being computed to prevent exceeding integer limits.\n");
    } else if (strcmp(msg, "division by zero") == 0) {
        fprintf(stderr, "what went wrong:\n");
        fprintf(stderr, "  The program attempted to divide a number by zero.\n");
        fprintf(stderr, "how to fix:\n");
        fprintf(stderr, "  Check that the divisor is not zero before dividing.\n");
        fprintf(stderr, "      if (divisor != 0) {\n");
        fprintf(stderr, "            let q = n / divisor;\n");
        fprintf(stderr, "      }\n");
    } else if (strcmp(msg, "modulo by zero") == 0) {
        fprintf(stderr, "what went wrong:\n");
        fprintf(stderr, "  The program attempted to compute remainder ('%%') with a divisor of zero.\n");
        fprintf(stderr, "how to fix:\n");
        fprintf(stderr, "  Check that the second number is not zero before using '%%'.\n");
        fprintf(stderr, "      if (b != 0) {\n");
        fprintf(stderr, "            let r = a %% b;\n");
        fprintf(stderr, "      }\n");
    } else if (strcmp(msg, "float overflow") == 0) {
        fprintf(stderr, "what went wrong:\n");
        fprintf(stderr, "  The floating point calculation produced a number too large to represent.\n");
        fprintf(stderr, "how to fix:\n");
        fprintf(stderr, "  Check your numbers to keep values within standard 64-bit float limits.\n");
    }
    exit(2);
}
"""

HELPER_DEFS: dict[str, str] = {
    "cmm_add": r"""static int64_t cmm_add(int64_t a, int64_t b, int line, int col) {
    if ((b > 0 && a > INT64_MAX - b) || (b < 0 && a < INT64_MIN - b)) {
        cmm_runtime_error("integer overflow", line, col);
    }
    return a + b;
}
""",
    "cmm_sub": r"""static int64_t cmm_sub(int64_t a, int64_t b, int line, int col) {
    if ((b < 0 && a > INT64_MAX + b) || (b > 0 && a < INT64_MIN + b)) {
        cmm_runtime_error("integer overflow", line, col);
    }
    return a - b;
}
""",
    "cmm_mul": r"""static int64_t cmm_mul(int64_t a, int64_t b, int line, int col) {
    if (a == 0 || b == 0) return 0;
    if (a > 0) {
        if (b > 0) {
            if (a > INT64_MAX / b) cmm_runtime_error("integer overflow", line, col);
        } else {
            if (b < INT64_MIN / a) cmm_runtime_error("integer overflow", line, col);
        }
    } else {
        if (b > 0) {
            if (a < INT64_MIN / b) cmm_runtime_error("integer overflow", line, col);
        } else {
            if (a == INT64_MIN || b == INT64_MIN) cmm_runtime_error("integer overflow", line, col);
            else if (a < INT64_MAX / b) cmm_runtime_error("integer overflow", line, col);
        }
    }
    return a * b;
}
""",
    "cmm_div": r"""static int64_t cmm_div(int64_t a, int64_t b, int line, int col) {
    if (b == 0) cmm_runtime_error("division by zero", line, col);
    if (a == INT64_MIN && b == -1) cmm_runtime_error("integer overflow", line, col);
    return a / b;
}
""",
    "cmm_mod": r"""static int64_t cmm_mod(int64_t a, int64_t b, int line, int col) {
    if (b == 0) cmm_runtime_error("modulo by zero", line, col);
    if (a == INT64_MIN && b == -1) return 0;
    return a % b;
}
""",
    "cmm_neg": r"""static int64_t cmm_neg(int64_t a, int line, int col) {
    if (a == INT64_MIN) cmm_runtime_error("integer overflow", line, col);
    return -a;
}
""",
    "cmm_fadd": r"""static double cmm_fadd(double a, double b, int line, int col) {
    double r = a + b;
    if (r > DBL_MAX || r < -DBL_MAX) cmm_runtime_error("float overflow", line, col);
    return r;
}
""",
    "cmm_fsub": r"""static double cmm_fsub(double a, double b, int line, int col) {
    double r = a - b;
    if (r > DBL_MAX || r < -DBL_MAX) cmm_runtime_error("float overflow", line, col);
    return r;
}
""",
    "cmm_fmul": r"""static double cmm_fmul(double a, double b, int line, int col) {
    double r = a * b;
    if (r > DBL_MAX || r < -DBL_MAX) cmm_runtime_error("float overflow", line, col);
    return r;
}
""",
    "cmm_fdiv": r"""static double cmm_fdiv(double a, double b, int line, int col) {
    if (b == 0.0) cmm_runtime_error("division by zero", line, col);
    double r = a / b;
    if (r > DBL_MAX || r < -DBL_MAX) cmm_runtime_error("float overflow", line, col);
    return r;
}
""",
    "cmm_fneg": r"""static double cmm_fneg(double a, int line, int col) {
    double r = -a;
    if (r > DBL_MAX || r < -DBL_MAX) cmm_runtime_error("float overflow", line, col);
    return r;
}
""",
    "cmm_streq": r"""static bool cmm_streq(const char *a, const char *b) {
    return strcmp(a, b) == 0;
}
""",
    "cmm_strne": r"""static bool cmm_strne(const char *a, const char *b) {
    return strcmp(a, b) != 0;
}
""",
    "cmm_print_float": r"""static void cmm_print_float(double v) {
    uint64_t u;
    memcpy(&u, &v, sizeof(u));
    bool is_neg = ((u >> 63) & 1) != 0;
    if (v == 0.0) {
        if (is_neg) {
            printf("-0.0\n");
        } else {
            printf("0.0\n");
        }
        return;
    }
    double abs_v = is_neg ? -v : v;
    char buf[64];
    int chosen_p = -1;
    for (int p = 1; p <= 17; p++) {
        snprintf(buf, sizeof(buf), "%.*e", p - 1, abs_v);
        char *endptr;
        double parsed = strtod(buf, &endptr);
        if (parsed == abs_v) {
            chosen_p = p;
            break;
        }
    }
    if (chosen_p == -1) {
        snprintf(buf, sizeof(buf), "%.16e", abs_v);
    }

    char D[64];
    int d_len = 0;
    char *e_ptr = strchr(buf, 'e');
    if (!e_ptr) e_ptr = strchr(buf, 'E');
    for (char *p = buf; p < e_ptr; p++) {
        if (*p >= '0' && *p <= '9') {
            D[d_len++] = *p;
        }
    }
    while (d_len > 1 && D[d_len - 1] == '0') {
        d_len--;
    }
    D[d_len] = '\0';
    int E = atoi(e_ptr + 1);

    char out[128];
    int out_len = 0;
    if (is_neg) {
        out[out_len++] = '-';
    }

    if (E >= -4 && E < 16) {
        if (E >= 0) {
            int int_part_len = E + 1;
            if (d_len >= int_part_len) {
                for (int i = 0; i < int_part_len; i++) {
                    out[out_len++] = D[i];
                }
                out[out_len++] = '.';
                if (d_len > int_part_len) {
                    for (int i = int_part_len; i < d_len; i++) {
                        out[out_len++] = D[i];
                    }
                } else {
                    out[out_len++] = '0';
                }
            } else {
                for (int i = 0; i < d_len; i++) {
                    out[out_len++] = D[i];
                }
                for (int i = 0; i < int_part_len - d_len; i++) {
                    out[out_len++] = '0';
                }
                out[out_len++] = '.';
                out[out_len++] = '0';
            }
        } else {
            out[out_len++] = '0';
            out[out_len++] = '.';
            int num_zeros = -E - 1;
            for (int i = 0; i < num_zeros; i++) {
                out[out_len++] = '0';
            }
            for (int i = 0; i < d_len; i++) {
                out[out_len++] = D[i];
            }
        }
    } else {
        out[out_len++] = D[0];
        out[out_len++] = '.';
        if (d_len > 1) {
            for (int i = 1; i < d_len; i++) {
                out[out_len++] = D[i];
            }
        } else {
            out[out_len++] = '0';
        }
        out[out_len++] = 'e';
        if (E >= 0) {
            out[out_len++] = '+';
            if (E < 10) out[out_len++] = '0';
            out_len += sprintf(out + out_len, "%d", E);
        } else {
            out[out_len++] = '-';
            int abs_E = -E;
            if (abs_E < 10) out[out_len++] = '0';
            out_len += sprintf(out + out_len, "%d", abs_E);
        }
    }
    out[out_len] = '\0';
    printf("%s\n", out);
}
""",
}

ARITHMETIC_HELPERS = {
    "cmm_add",
    "cmm_sub",
    "cmm_mul",
    "cmm_div",
    "cmm_mod",
    "cmm_neg",
    "cmm_fadd",
    "cmm_fsub",
    "cmm_fmul",
    "cmm_fdiv",
    "cmm_fneg",
}


class CCodegen:
    """C99 code generator for C-- AST."""

    def __init__(self, source_path: str, source_lines: list[str]) -> None:
        self.source_path = source_path
        self.source_lines = source_lines
        self._scopes: list[dict[str, CVar]] = []
        self._var_counter = 0
        self._used_helpers: set[str] = set()

    def _push_scope(self) -> None:
        self._scopes.append({})

    def _pop_scope(self) -> None:
        self._scopes.pop()

    def _lookup(self, name: str) -> CVar:
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        raise KeyError(f"Variable '{name}' not found during code generation")

    def _declare(self, name: str, cvar: CVar) -> None:
        self._scopes[-1][name] = cvar

    def c_type(self, t: Type, is_const: bool = False) -> str:
        """Return C99 type string for a C-- type."""
        if t == Type.INT:
            return "const int64_t" if is_const else "int64_t"
        elif t == Type.FLOAT:
            return "const double" if is_const else "double"
        elif t == Type.BOOL:
            return "const bool" if is_const else "bool"
        elif t == Type.STRING:
            return "const char * const" if is_const else "const char *"
        raise ValueError(f"Cannot map type {t} to C")

    def gen_expr(self, expr: Expr) -> tuple[Type, str]:
        """Generate C99 expression code and return (Type, c_code)."""
        if isinstance(expr, Literal):
            if expr.type == "int":
                val = int(expr.value)  # type: ignore
                if val == -9223372036854775808:
                    return Type.INT, "(-9223372036854775807LL - 1LL)"
                return Type.INT, f"{val}LL"
            elif expr.type == "float":
                val = float(expr.value)  # type: ignore
                if val == 0.0:
                    if math.copysign(1.0, val) < 0:
                        return Type.FLOAT, "-0.0"
                    return Type.FLOAT, "0.0"
                rep = repr(val)
                if "." not in rep and "e" not in rep and "E" not in rep:
                    rep += ".0"
                return Type.FLOAT, rep
            elif expr.type == "bool":
                return Type.BOOL, "true" if expr.value else "false"
            elif expr.type == "string":
                return Type.STRING, to_c_string_literal(str(expr.value))
            raise ValueError(f"Unknown literal type: {expr.type}")

        elif isinstance(expr, Variable):
            cvar = self._lookup(expr.name)
            return cvar.type, cvar.c_name

        elif isinstance(expr, UnaryOp):
            op_t, op_code = self.gen_expr(expr.operand)
            res_t = UNARY_OPERATORS[(expr.op, op_t)]
            if expr.op == "-":
                if op_t == Type.INT:
                    self._used_helpers.add("cmm_neg")
                    return res_t, f"cmm_neg({op_code}, {expr.line}, {expr.col})"
                else:
                    self._used_helpers.add("cmm_fneg")
                    return res_t, f"cmm_fneg({op_code}, {expr.line}, {expr.col})"
            elif expr.op == "!":
                return res_t, f"(!({op_code}))"
            raise ValueError(f"Unknown unary operator: {expr.op}")

        elif isinstance(expr, BinaryOp):
            l_t, l_code = self.gen_expr(expr.left)
            r_t, r_code = self.gen_expr(expr.right)
            res_t = BINARY_OPERATORS[(expr.op, l_t, r_t)]

            if expr.op in ("+", "-", "*"):
                if l_t == Type.INT and r_t == Type.INT:
                    fn = {"+": "cmm_add", "-": "cmm_sub", "*": "cmm_mul"}[expr.op]
                    self._used_helpers.add(fn)
                    return res_t, f"{fn}({l_code}, {r_code}, {expr.line}, {expr.col})"
                elif l_t == Type.FLOAT and r_t == Type.FLOAT:
                    fn = {"+": "cmm_fadd", "-": "cmm_fsub", "*": "cmm_fmul"}[expr.op]
                    self._used_helpers.add(fn)
                    return res_t, f"{fn}({l_code}, {r_code}, {expr.line}, {expr.col})"
                elif l_t == Type.INT and r_t == Type.FLOAT:
                    fn = {"+": "cmm_fadd", "-": "cmm_fsub", "*": "cmm_fmul"}[expr.op]
                    self._used_helpers.add(fn)
                    return res_t, f"{fn}((double)({l_code}), {r_code}, {expr.line}, {expr.col})"
                elif l_t == Type.FLOAT and r_t == Type.INT:
                    fn = {"+": "cmm_fadd", "-": "cmm_fsub", "*": "cmm_fmul"}[expr.op]
                    self._used_helpers.add(fn)
                    return res_t, f"{fn}({l_code}, (double)({r_code}), {expr.line}, {expr.col})"

            elif expr.op == "/":
                if l_t == Type.INT and r_t == Type.INT:
                    self._used_helpers.add("cmm_div")
                    return res_t, f"cmm_div({l_code}, {r_code}, {expr.line}, {expr.col})"
                elif l_t == Type.FLOAT and r_t == Type.FLOAT:
                    self._used_helpers.add("cmm_fdiv")
                    return res_t, f"cmm_fdiv({l_code}, {r_code}, {expr.line}, {expr.col})"
                elif l_t == Type.INT and r_t == Type.FLOAT:
                    self._used_helpers.add("cmm_fdiv")
                    return res_t, f"cmm_fdiv((double)({l_code}), {r_code}, {expr.line}, {expr.col})"
                elif l_t == Type.FLOAT and r_t == Type.INT:
                    self._used_helpers.add("cmm_fdiv")
                    return res_t, f"cmm_fdiv({l_code}, (double)({r_code}), {expr.line}, {expr.col})"

            elif expr.op == "%":
                self._used_helpers.add("cmm_mod")
                return res_t, f"cmm_mod({l_code}, {r_code}, {expr.line}, {expr.col})"

            elif expr.op in ("<", "<=", ">", ">="):
                if l_t == Type.INT and r_t == Type.FLOAT:
                    return res_t, f"(((double)({l_code})) {expr.op} ({r_code}))"
                elif l_t == Type.FLOAT and r_t == Type.INT:
                    return res_t, f"(({l_code}) {expr.op} ((double)({r_code})))"
                else:
                    return res_t, f"(({l_code}) {expr.op} ({r_code}))"

            elif expr.op in ("==", "!="):
                if l_t == Type.STRING:
                    fn = "cmm_streq" if expr.op == "==" else "cmm_strne"
                    self._used_helpers.add(fn)
                    return res_t, f"{fn}({l_code}, {r_code})"
                elif l_t == Type.INT and r_t == Type.FLOAT:
                    return res_t, f"(((double)({l_code})) {expr.op} ({r_code}))"
                elif l_t == Type.FLOAT and r_t == Type.INT:
                    return res_t, f"(({l_code}) {expr.op} ((double)({r_code})))"
                else:
                    return res_t, f"(({l_code}) {expr.op} ({r_code}))"

            elif expr.op in ("&&", "||"):
                return res_t, f"(({l_code}) {expr.op} ({r_code}))"

            raise ValueError(f"Unknown binary operator: {expr.op}")

        raise TypeError(f"Unknown expression node type: {type(expr)}")

    def gen_stmt(self, stmt: Stmt) -> list[str]:
        """Generate C99 statement lines."""
        if isinstance(stmt, VarDecl):
            init_t, init_code = self.gen_expr(stmt.init)
            self._var_counter += 1
            c_name = f"_v_{self._var_counter}_{stmt.name}"
            cvar = CVar(c_name, init_t, stmt.mutable)
            self._declare(stmt.name, cvar)
            type_str = self.c_type(init_t, is_const=not stmt.mutable)
            return [f"{type_str} {c_name} = {init_code};"]

        elif isinstance(stmt, Assign):
            cvar = self._lookup(stmt.name)
            val_t, val_code = self.gen_expr(stmt.value)
            if stmt.op == "=":
                return [f"{cvar.c_name} = {val_code};"]
            else:
                bin_op = COMPOUND_TO_BINARY[stmt.op]
                if bin_op in ("+", "-", "*"):
                    if cvar.type == Type.INT and val_t == Type.INT:
                        fn = {"+": "cmm_add", "-": "cmm_sub", "*": "cmm_mul"}[bin_op]
                        self._used_helpers.add(fn)
                        rhs = f"{fn}({cvar.c_name}, {val_code}, {stmt.op_line}, {stmt.op_col})"
                    elif cvar.type == Type.FLOAT and val_t == Type.INT:
                        fn = {"+": "cmm_fadd", "-": "cmm_fsub", "*": "cmm_fmul"}[bin_op]
                        self._used_helpers.add(fn)
                        rhs = f"{fn}({cvar.c_name}, (double)({val_code}), {stmt.op_line}, {stmt.op_col})"
                    else:
                        fn = {"+": "cmm_fadd", "-": "cmm_fsub", "*": "cmm_fmul"}[bin_op]
                        self._used_helpers.add(fn)
                        rhs = f"{fn}({cvar.c_name}, {val_code}, {stmt.op_line}, {stmt.op_col})"
                elif bin_op == "/":
                    if cvar.type == Type.INT and val_t == Type.INT:
                        self._used_helpers.add("cmm_div")
                        rhs = f"cmm_div({cvar.c_name}, {val_code}, {stmt.op_line}, {stmt.op_col})"
                    elif cvar.type == Type.FLOAT and val_t == Type.INT:
                        self._used_helpers.add("cmm_fdiv")
                        rhs = f"cmm_fdiv({cvar.c_name}, (double)({val_code}), {stmt.op_line}, {stmt.op_col})"
                    else:
                        self._used_helpers.add("cmm_fdiv")
                        rhs = f"cmm_fdiv({cvar.c_name}, {val_code}, {stmt.op_line}, {stmt.op_col})"
                elif bin_op == "%":
                    self._used_helpers.add("cmm_mod")
                    rhs = f"cmm_mod({cvar.c_name}, {val_code}, {stmt.op_line}, {stmt.op_col})"
                else:
                    raise ValueError(f"Unknown compound operator: {stmt.op}")
                return [f"{cvar.c_name} = {rhs};"]

        elif isinstance(stmt, Print):
            e_t, e_code = self.gen_expr(stmt.expr)
            if e_t == Type.INT:
                return [f'printf("%" PRId64 "\\n", {e_code});']
            elif e_t == Type.FLOAT:
                self._used_helpers.add("cmm_print_float")
                return [f"cmm_print_float({e_code});"]
            elif e_t == Type.BOOL:
                return [f'printf("%s\\n", ({e_code}) ? "true" : "false");']
            elif e_t == Type.STRING:
                return [f'printf("%s\\n", {e_code});']
            raise ValueError(f"Unknown print type: {e_t}")

        elif isinstance(stmt, If):
            _, cond_code = self.gen_expr(stmt.cond)
            lines = [f"if ({cond_code}) {{"]
            lines.extend(self.gen_block_body(stmt.then_block))
            curr_else = stmt.else_branch
            while curr_else is not None:
                if isinstance(curr_else, If):
                    _, else_cond = self.gen_expr(curr_else.cond)
                    lines.append(f"}} else if ({else_cond}) {{")
                    lines.extend(self.gen_block_body(curr_else.then_block))
                    curr_else = curr_else.else_branch
                elif isinstance(curr_else, Block):
                    lines.append("} else {")
                    lines.extend(self.gen_block_body(curr_else))
                    curr_else = None
            lines.append("}")
            return lines

        elif isinstance(stmt, While):
            _, cond_code = self.gen_expr(stmt.cond)
            lines = [f"while ({cond_code}) {{"]
            lines.extend(self.gen_block_body(stmt.body))
            lines.append("}")
            return lines

        elif isinstance(stmt, DoWhile):
            lines = ["do {"]
            lines.extend(self.gen_block_body(stmt.body))
            _, cond_code = self.gen_expr(stmt.cond)
            lines.append(f"}} while ({cond_code});")
            return lines

        elif isinstance(stmt, For):
            lines = ["{"]
            self._push_scope()
            if stmt.init:
                for l in self.gen_stmt(stmt.init):
                    lines.append(f"    {l}")
            cond_str = ""
            if stmt.cond:
                _, c_code = self.gen_expr(stmt.cond)
                cond_str = c_code
            upd_str = ""
            if stmt.update:
                upd_lines = self.gen_stmt(stmt.update)
                upd_str = upd_lines[0].rstrip(";")
            lines.append(f"    for (; {cond_str}; {upd_str}) {{")
            lines.extend(f"    {l}" for l in self.gen_block_body(stmt.body))
            lines.append("    }")
            self._pop_scope()
            lines.append("}")
            return lines

        elif isinstance(stmt, Block):
            lines = ["{"]
            lines.extend(self.gen_block_body(stmt))
            lines.append("}")
            return lines

        raise TypeError(f"Unknown statement node type: {type(stmt)}")

    def gen_block_body(self, block: Block) -> list[str]:
        """Generate statement lines inside a block body with indentation and scope."""
        self._push_scope()
        lines: list[str] = []
        try:
            for s in block.statements:
                s_lines = self.gen_stmt(s)
                for sl in s_lines:
                    lines.append(f"    {sl}")
        finally:
            self._pop_scope()
        return lines

    def _validate_v01_subset(self, program: Program) -> None:
        """Reject v0.2-only features before C code generation per §A10."""
        for fn in program.functions:
            if fn.name != "main":
                raise TranspileError("T001", f"C backend does not support user-defined functions other than 'main' ('{fn.name}')", fn.line, fn.col)

        def walk(node: ASTNode) -> None:
            if isinstance(node, (Call, CallStmt)):
                name = node.name if isinstance(node, Call) else (node.call.name if isinstance(node.call, Call) else "call")
                raise TranspileError("T001", f"C backend does not support function calls ('{name}')", node.line, node.col)
            elif isinstance(node, MethodCall):
                raise TranspileError("T001", f"C backend does not support method calls ('.{node.method}')", node.line, node.col)
            elif isinstance(node, (Index, IndexAssign)):
                raise TranspileError("T001", "C backend does not support indexing", node.line, node.col)
            elif isinstance(node, (ArrayLiteral, NewCollection)):
                raise TranspileError("T001", "C backend does not support collections", node.line, node.col)
            elif isinstance(node, SwitchStmt):
                raise TranspileError("T001", "C backend does not support 'switch' statements", node.line, node.col)
            elif isinstance(node, ReturnStmt):
                raise TranspileError("T001", "C backend does not support 'return' in main", node.line, node.col)
            elif isinstance(node, VarDecl):
                walk(node.init)

            elif isinstance(node, Block):
                for s in node.statements:
                    walk(s)
            elif isinstance(node, Assign):
                walk(node.value)
            elif isinstance(node, Print):
                walk(node.expr)
            elif isinstance(node, If):
                walk(node.cond)
                walk(node.then_block)
                if node.else_branch:
                    walk(node.else_branch)
            elif isinstance(node, While):
                walk(node.cond)
                walk(node.body)
            elif isinstance(node, DoWhile):
                walk(node.body)
                walk(node.cond)
            elif isinstance(node, For):
                if node.init:
                    walk(node.init)
                if node.cond:
                    walk(node.cond)
                if node.update:
                    walk(node.update)
                walk(node.body)
            elif isinstance(node, BinaryOp):
                walk(node.left)
                walk(node.right)
            elif isinstance(node, UnaryOp):
                walk(node.operand)

        walk(program.body)

    def generate(self, program: Program) -> str:
        """Generate complete standard C99 source code."""
        self._validate_v01_subset(program)
        # First generate the main body statements so self._used_helpers is populated
        body_lines = self.gen_block_body(program.body)


        parts: list[str] = [C_RUNTIME_HEADER]

        needs_runtime_error = any(h in self._used_helpers for h in ARITHMETIC_HELPERS)

        if needs_runtime_error:
            path_lit = to_c_string_literal(self.source_path)
            parts.append(f"static const char * const cmm_source_path = {path_lit};")

            clean_lines = [l.rstrip("\r\n") for l in self.source_lines]
            num_lines = len(clean_lines)
            if num_lines == 0:
                lines_init = '""'
            else:
                lines_init = ",\n    ".join(to_c_string_literal(l) for l in clean_lines)
            parts.append(f"#define CMM_NUM_SOURCE_LINES {num_lines}")
            parts.append(f"static const char * const cmm_source_lines[] = {{\n    {lines_init}\n}};\n")
            parts.append(RUNTIME_ERROR_HELPER)

        for helper_name, helper_code in HELPER_DEFS.items():
            if helper_name in self._used_helpers:
                parts.append(helper_code)

        # Main function
        parts.append("int main(void) {")
        for line in body_lines:
            parts.append(line)
        parts.append("    return 0;")
        parts.append("}\n")

        return "\n".join(parts)


def generate_c(ast: Program, source_path: str, source_lines: list[str]) -> str:
    """Public API: generate standard C99 code for a C-- program."""
    codegen = CCodegen(source_path, source_lines)
    return codegen.generate(ast)
