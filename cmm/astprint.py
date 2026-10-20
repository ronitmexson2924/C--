"""Debug formatters for tokens and AST representations per Section 11.6 and Spec v0.2."""

from typing import Optional

from cmm.ast_nodes import (
    Assign,
    ASTNode,
    ArrayLiteral,
    BinaryOp,
    Block,
    Call,
    CallStmt,
    CaseClause,
    DoWhile,
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
    SwitchStmt,
    UnaryOp,
    VarDecl,
    Variable,
    While,
)
from cmm.formatting import format_float
from cmm.tokens import Token


def format_tokens(tokens: list[Token]) -> str:
    """Format token list per Section 11.6.

    Format: <line>:<col> TAB <TYPE> TAB <lexeme>
    """
    lines: list[str] = []
    for t in tokens:
        lines.append(f"{t.line}:{t.col}\t{t.type.name}\t{t.lexeme}\n")
    return "".join(lines)


def _escape_string(s: str) -> str:
    """Escape string with double quotes and escapes per Section 11.6."""
    escaped = (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\t", "\\t")
        .replace("\r", "\\r")
    )
    return f'"{escaped}"'


def format_ast(node: ASTNode, role: Optional[str] = None, level: int = 0) -> str:
    """Format AST as indented tree per Section 11.6 and Spec v0.2.

    Indentation: 2 spaces per level.
    Node line: <role>: <NodeName>(<field>=<value>, ...)
    Root has no role prefix.
    """
    indent = "  " * level

    # 1. Determine node name and non-node fields
    node_name = type(node).__name__
    fields_str = ""

    if isinstance(node, Program):
        fields_str = f'module={_escape_string(node.module_name)}'
    elif isinstance(node, FunctionDef):
        ret_str = f', return_type={_escape_string(str(node.return_type))}' if node.return_type else ""
        fields_str = f'name={_escape_string(node.name)}{ret_str}'
    elif isinstance(node, Param):
        fields_str = f'name={_escape_string(node.name)}, type={_escape_string(str(node.type))}'
    elif isinstance(node, VarDecl):
        mut_str = "true" if node.mutable else "false"
        fields_str = f'mutable={mut_str}, name={_escape_string(node.name)}'
    elif isinstance(node, Assign):
        fields_str = f'name={_escape_string(node.name)}, op={_escape_string(node.op)}'
    elif isinstance(node, IndexAssign):
        fields_str = f'op={_escape_string(node.op)}'
    elif isinstance(node, BinaryOp):
        fields_str = f'op={_escape_string(node.op)}'
    elif isinstance(node, UnaryOp):
        fields_str = f'op={_escape_string(node.op)}'
    elif isinstance(node, Variable):
        fields_str = f'name={_escape_string(node.name)}'
    elif isinstance(node, Call):
        fields_str = f'name={_escape_string(node.name)}'
    elif isinstance(node, MethodCall):
        fields_str = f'method={_escape_string(node.method)}'
    elif isinstance(node, NewCollection):
        type_str = f', type_arg={_escape_string(str(node.type_arg))}' if node.type_arg else ""
        fields_str = f'kind={_escape_string(node.kind)}{type_str}'
    elif isinstance(node, CaseClause):
        vals = ", ".join(repr(v) for v in node.values)
        fields_str = f'values=[{vals}]'
    elif isinstance(node, Literal):
        if node.type == "int":
            val_str = str(node.value)
        elif node.type == "float":
            val_str = format_float(float(node.value))  # type: ignore[arg-type]
        elif node.type == "bool":
            val_str = "true" if node.value else "false"
        elif node.type == "string":
            val_str = _escape_string(str(node.value))
        else:
            val_str = str(node.value)
        fields_str = f'type={node.type}, value={val_str}'

    parens = f"({fields_str})" if fields_str else ""
    if role is None:
        header = f"{indent}{node_name}{parens}\n"
    else:
        header = f"{indent}{role}: {node_name}{parens}\n"

    # 2. Collect child nodes with roles
    children: list[tuple[str, ASTNode]] = []
    if isinstance(node, Program):
        for fn in node.functions:
            children.append(("function", fn))
    elif isinstance(node, FunctionDef):
        for p in node.params:
            children.append(("param", p))
        children.append(("body", node.body))
    elif isinstance(node, Block):
        for stmt in node.statements:
            children.append(("stmt", stmt))
    elif isinstance(node, VarDecl):
        children.append(("init", node.init))
    elif isinstance(node, Assign):
        children.append(("value", node.value))
    elif isinstance(node, IndexAssign):
        children.append(("target", node.target))
        children.append(("index", node.index))
        children.append(("value", node.value))
    elif isinstance(node, Print):
        children.append(("expr", node.expr))
    elif isinstance(node, If):
        children.append(("cond", node.cond))
        children.append(("then", node.then_block))
        if node.else_branch is not None:
            children.append(("else", node.else_branch))
    elif isinstance(node, While):
        children.append(("cond", node.cond))
        children.append(("body", node.body))
    elif isinstance(node, DoWhile):
        children.append(("body", node.body))
        children.append(("cond", node.cond))
    elif isinstance(node, For):
        if node.init is not None:
            children.append(("init", node.init))
        if node.cond is not None:
            children.append(("cond", node.cond))
        if node.update is not None:
            children.append(("update", node.update))
        children.append(("body", node.body))
    elif isinstance(node, BinaryOp):
        children.append(("left", node.left))
        children.append(("right", node.right))
    elif isinstance(node, UnaryOp):
        children.append(("operand", node.operand))
    elif isinstance(node, Call):
        for arg in node.args:
            children.append(("arg", arg))
    elif isinstance(node, MethodCall):
        children.append(("receiver", node.receiver))
        for arg in node.args:
            children.append(("arg", arg))
    elif isinstance(node, CallStmt):
        children.append(("call", node.call))
    elif isinstance(node, Index):
        children.append(("target", node.target))
        children.append(("index", node.index))
    elif isinstance(node, ArrayLiteral):
        for el in node.elements:
            children.append(("element", el))
    elif isinstance(node, NewCollection):
        for arg in node.args:
            children.append(("arg", arg))
    elif isinstance(node, SwitchStmt):
        children.append(("selector", node.selector))
        for c in node.cases:
            children.append(("case", c))
        if node.default_body is not None:
            children.append(("default", node.default_body))
    elif isinstance(node, CaseClause):
        children.append(("body", node.body))
    elif isinstance(node, ReturnStmt):
        if node.expr is not None:
            children.append(("expr", node.expr))

    # 3. Recursively format children
    child_lines: list[str] = []
    for child_role, child_node in children:
        child_lines.append(format_ast(child_node, role=child_role, level=level + 1))

    return header + "".join(child_lines)
