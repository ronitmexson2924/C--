"""Abstract Syntax Tree (AST) node definitions for C-- v0.2.0."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Union
from cmm.types import Type


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
class Param(ASTNode):
    """Function parameter definition."""

    name: str
    type: Type


@dataclass
class FunctionDef(ASTNode):
    """Function definition node.

    fn <name>(<params>) [ -> <ret_type> ] { <body> }
    """

    name: str
    params: list[Param]
    ret_type: Optional[Type]  # None means void function
    body: "Block"

    @property
    def return_type(self) -> Optional[Type]:
        return self.ret_type



@dataclass
class Program(ASTNode):
    """Root program node.

    module <module_name>;
    fn function1(...) ...
    fn main() { ... }
    """

    module_name: str
    functions: list[FunctionDef] = field(default_factory=list)

    def __init__(
        self,
        module_name: str,
        functions: Optional[list[FunctionDef]] = None,
        line: int = 1,
        col: int = 1,
        body: Optional["Block"] = None,
    ) -> None:
        self.line = line
        self.col = col
        self.module_name = module_name
        if functions is not None:
            self.functions = functions
        elif body is not None:
            self.functions = [
                FunctionDef(
                    name="main",
                    params=[],
                    ret_type=None,
                    body=body,
                    line=body.line,
                    col=body.col,
                )
            ]
        else:
            self.functions = []

    @property
    def body(self) -> "Block":
        """Compatibility property returning the Block of the 'main' function."""
        for fn in self.functions:
            if fn.name == "main":
                return fn.body
        return Block(statements=[], line=self.line, col=self.col)



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
class IndexAssign(Stmt):
    """Element assignment statement: <name>[<index>] <op> <value>;

    line and col record the position of the target identifier.
    op_line and op_col record the position of the operator token.
    """

    name: str
    index: Expr
    op: str  # one of '=', '+=', '-=', '*=', '/=', '%='
    op_line: int
    op_col: int
    value: Expr


@dataclass
class Print(Stmt):
    """Print statement: print(<expr>);"""

    expr: Expr


@dataclass
class ReturnStmt(Stmt):
    """Return statement: return [ <expr> ];"""

    expr: Optional[Expr]


@dataclass
class Call(Expr):
    """Function call expression or statement: <name>(<args>)"""

    name: str
    args: list[Expr]

    def __init__(
        self,
        name: str,
        args: list[Expr],
        line: int,
        col: int,
        start_line: int = -1,
        start_col: int = -1,
    ) -> None:
        self.name = name
        self.args = args
        self.line = line
        self.col = col
        self.start_line = line if start_line == -1 else start_line
        self.start_col = col if start_col == -1 else start_col


@dataclass
class MethodCall(Expr):
    """Method call expression or statement: <receiver>.<method>(<args>)"""

    receiver_name: str
    method: str
    args: list[Expr]

    def __init__(
        self,
        receiver_name: str,
        method: str,
        args: list[Expr],
        line: int,
        col: int,
        start_line: int = -1,
        start_col: int = -1,
    ) -> None:
        self.receiver_name = receiver_name
        self.method = method
        self.args = args
        self.line = line
        self.col = col
        self.start_line = line if start_line == -1 else start_line
        self.start_col = col if start_col == -1 else start_col


@dataclass
class CallStmt(Stmt):
    """Call statement wrapping a Call or MethodCall."""

    call: Union[Call, MethodCall]


@dataclass
class Index(Expr):
    """Indexing expression: <target>[<index>]"""

    target: Expr
    index: Expr

    def __init__(
        self,
        target: Expr,
        index: Expr,
        line: int,
        col: int,
        start_line: int = -1,
        start_col: int = -1,
    ) -> None:
        self.target = target
        self.index = index
        self.line = line
        self.col = col
        self.start_line = target.start_line if start_line == -1 else start_line
        self.start_col = target.start_col if start_col == -1 else start_col


@dataclass
class ArrayLiteral(Expr):
    """Array literal expression: [<expr>, ...]"""

    elements: list[Expr]

    def __init__(
        self,
        elements: list[Expr],
        line: int,
        col: int,
        start_line: int = -1,
        start_col: int = -1,
    ) -> None:
        self.elements = elements
        self.line = line
        self.col = col
        self.start_line = line if start_line == -1 else start_line
        self.start_col = col if start_col == -1 else start_col


@dataclass
class NewCollection(Expr):
    """New collection expression: array<T>(n, fill) or list<T>() / stack<T>() / queue<T>()"""

    kind: str  # 'array', 'list', 'stack', 'queue'
    elem_type: Type
    args: list[Expr]

    def __init__(
        self,
        kind: str,
        elem_type: Type,
        args: list[Expr],
        line: int,
        col: int,
        start_line: int = -1,
        start_col: int = -1,
    ) -> None:
        self.kind = kind
        self.elem_type = elem_type
        self.args = args
        self.line = line
        self.col = col
        self.start_line = line if start_line == -1 else start_line
        self.start_col = col if start_col == -1 else start_col


@dataclass
class CaseClause(ASTNode):
    """Case clause inside switch: case <values>: <block>"""

    values: list[Expr]
    body: Block


@dataclass
class SwitchStmt(Stmt):
    """Switch statement: switch (<selector>) { <cases> [ default: <default_body> ] }"""

    selector: Expr
    cases: list[CaseClause]
    default_body: Optional[Block]


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

    init: Optional[Union[VarDecl, Assign, IndexAssign]]
    cond: Optional[Expr]
    update: Optional[Union[Assign, IndexAssign]]
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
    """Unary prefix operation: (! | -) <operand>"""

    op: str
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
    """Binary operation: <left> <op> <right>"""

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
