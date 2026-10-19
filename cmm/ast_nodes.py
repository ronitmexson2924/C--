"""Abstract Syntax Tree (AST) node definitions for C-- per Section 12.5."""

from dataclasses import dataclass
from typing import Optional, Union


@dataclass
class ASTNode:
    """Base class for all AST nodes."""

    line: int
    col: int


@dataclass
class Stmt(ASTNode):
    """Base class for all statement nodes."""

    pass


@dataclass
class Expr(ASTNode):
    """Base class for all expression nodes.

    Every expression node additionally has start_line and start_col = position
    of its first token, including a leading '(' when parenthesized (§12.5).
    """

    start_line: int
    start_col: int


@dataclass
class Program(ASTNode):
    """Root program node.

    module <module_name>;
    fn main() { ... }
    """

    module_name: str
    body: "Block"


@dataclass
class Block(Stmt):
    """A block of statements enclosed in braces { ... }."""

    statements: list[Stmt]


@dataclass
class VarDecl(Stmt):
    """Variable declaration: (let | mut) <name> = <init>;"""

    mutable: bool
    name: str
    name_line: int
    name_col: int
    init: Expr


@dataclass
class Assign(Stmt):
    """Assignment statement: <name> <op> <value>;

    line and col record the position of the target identifier (§12.5).
    op_line and op_col record the position of the operator token.
    """

    name: str
    op: str  # one of '=', '+=', '-=', '*=', '/=', '%='
    op_line: int
    op_col: int
    value: Expr


@dataclass
class Print(Stmt):
    """Print statement: print(<expr>);"""

    expr: Expr


@dataclass
class If(Stmt):
    """If statement: if (<cond>) <then_block> [ else (<else_branch>) ]"""

    cond: Expr
    then_block: Block
    else_branch: Optional[Union[Block, "If"]]


@dataclass
class While(Stmt):
    """While loop: while (<cond>) <body>"""

    cond: Expr
    body: Block


@dataclass
class DoWhile(Stmt):
    """Do-while loop: do <body> while (<cond>);"""

    body: Block
    cond: Expr


@dataclass
class For(Stmt):
    """For loop: for (<init>; <cond>; <update>) <body>"""

    init: Optional[Union[VarDecl, Assign]]
    cond: Optional[Expr]
    update: Optional[Assign]
    body: Block


@dataclass
class Literal(Expr):
    """Literal constant: int, float, bool, or string."""

    type: str  # "int", "float", "bool", "string"
    value: object

    def __init__(
        self,
        type: str,
        value: object,
        line: int,
        col: int,
        start_line: int = -1,
        start_col: int = -1,
    ) -> None:
        self.type = type
        self.value = value
        self.line = line
        self.col = col
        self.start_line = line if start_line == -1 else start_line
        self.start_col = col if start_col == -1 else start_col


@dataclass
class Variable(Expr):
    """Variable reference identifier."""

    name: str

    def __init__(
        self,
        name: str,
        line: int,
        col: int,
        start_line: int = -1,
        start_col: int = -1,
    ) -> None:
        self.name = name
        self.line = line
        self.col = col
        self.start_line = line if start_line == -1 else start_line
        self.start_col = col if start_col == -1 else start_col


@dataclass
class UnaryOp(Expr):
    """Unary prefix operator expression: ! or -."""

    op: str  # "-" or "!"
    operand: Expr

    def __init__(
        self,
        op: str,
        operand: Expr,
        line: int,
        col: int,
        start_line: int = -1,
        start_col: int = -1,
    ) -> None:
        self.op = op
        self.operand = operand
        self.line = line
        self.col = col
        self.start_line = line if start_line == -1 else start_line
        self.start_col = col if start_col == -1 else start_col


@dataclass
class BinaryOp(Expr):
    """Binary infix operator expression."""

    op: str
    left: Expr
    right: Expr

    def __init__(
        self,
        op: str,
        left: Expr,
        right: Expr,
        line: int,
        col: int,
        start_line: int = -1,
        start_col: int = -1,
    ) -> None:
        self.op = op
        self.left = left
        self.right = right
        self.line = line
        self.col = col
        self.start_line = left.start_line if start_line == -1 else start_line
        self.start_col = left.start_col if start_col == -1 else start_col
