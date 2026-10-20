"""Type definitions, Symbol dataclass, and operator typing tables for C-- per SPEC §7.2 and v0.2.0 §A4."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Type:
    """Type representation in C-- v0.2.0.

    Can be a primitive type ('int', 'float', 'bool', 'string'),
    a composite collection type ('array<T>', 'list<T>', 'stack<T>', 'queue<T>'),
    or internal 'void' / 'invalid'.
    """

    name: str  # "int", "float", "bool", "string", "array", "list", "stack", "queue", "void", "invalid"
    elem: Optional[Type] = None

    def __str__(self) -> str:
        if self.elem is not None:
            return f"{self.name}<{self.elem}>"
        return self.name

    def is_primitive(self) -> bool:
        return self.name in ("int", "float", "bool", "string")

    def is_collection(self) -> bool:
        return self.name in ("array", "list", "stack", "queue")

    def is_indexable(self) -> bool:
        return self.name in ("string", "array", "list")

    @classmethod
    def coll(cls, kind: str, elem: Type) -> Type:
        return cls(kind, elem)


# Class constants matching v0.1 enum interface
Type.INT = Type("int")
Type.FLOAT = Type("float")
Type.BOOL = Type("bool")
Type.STRING = Type("string")
Type.VOID = Type("void")
Type.INVALID = Type("invalid")


@dataclass
class Symbol:
    """A symbol table entry recording variable metadata.

    Attributes:
        type: The inferred or declared C-- type of the variable.
        mutable: True if declared with 'mut', False if declared with 'let'.
        decl_line: Line number of the variable name in its declaration.
        decl_col: Column number of the variable name in its declaration.
    """

    type: Type
    mutable: bool
    decl_line: int
    decl_col: int


# Unary operators table: (operator, operand_type) -> result_type (§7.2)
UNARY_OPERATORS: dict[tuple[str, Type], Type] = {
    ("-", Type.INT): Type.INT,
    ("-", Type.FLOAT): Type.FLOAT,
    ("!", Type.BOOL): Type.BOOL,
}

# Binary operators table: (operator, left_type, right_type) -> result_type (§7.2)
BINARY_OPERATORS: dict[tuple[str, Type, Type], Type] = {
    # Binary arithmetic (+, -, *, /)
    ("+", Type.INT, Type.INT): Type.INT,
    ("+", Type.FLOAT, Type.FLOAT): Type.FLOAT,
    ("+", Type.INT, Type.FLOAT): Type.FLOAT,
    ("+", Type.FLOAT, Type.INT): Type.FLOAT,

    ("-", Type.INT, Type.INT): Type.INT,
    ("-", Type.FLOAT, Type.FLOAT): Type.FLOAT,
    ("-", Type.INT, Type.FLOAT): Type.FLOAT,
    ("-", Type.FLOAT, Type.INT): Type.FLOAT,

    ("*", Type.INT, Type.INT): Type.INT,
    ("*", Type.FLOAT, Type.FLOAT): Type.FLOAT,
    ("*", Type.INT, Type.FLOAT): Type.FLOAT,
    ("*", Type.FLOAT, Type.INT): Type.FLOAT,

    ("/", Type.INT, Type.INT): Type.INT,
    ("/", Type.FLOAT, Type.FLOAT): Type.FLOAT,
    ("/", Type.INT, Type.FLOAT): Type.FLOAT,
    ("/", Type.FLOAT, Type.INT): Type.FLOAT,

    # Integer modulo (%)
    ("%", Type.INT, Type.INT): Type.INT,

    # Relational comparison (<, <=, >, >=)
    ("<", Type.INT, Type.INT): Type.BOOL,
    ("<", Type.FLOAT, Type.FLOAT): Type.BOOL,
    ("<", Type.INT, Type.FLOAT): Type.BOOL,
    ("<", Type.FLOAT, Type.INT): Type.BOOL,

    ("<=", Type.INT, Type.INT): Type.BOOL,
    ("<=", Type.FLOAT, Type.FLOAT): Type.BOOL,
    ("<=", Type.INT, Type.FLOAT): Type.BOOL,
    ("<=", Type.FLOAT, Type.INT): Type.BOOL,

    (">", Type.INT, Type.INT): Type.BOOL,
    (">", Type.FLOAT, Type.FLOAT): Type.BOOL,
    (">", Type.INT, Type.FLOAT): Type.BOOL,
    (">", Type.FLOAT, Type.INT): Type.BOOL,

    (">=", Type.INT, Type.INT): Type.BOOL,
    (">=", Type.FLOAT, Type.FLOAT): Type.BOOL,
    (">=", Type.INT, Type.FLOAT): Type.BOOL,
    (">=", Type.FLOAT, Type.INT): Type.BOOL,

    # Equality comparison (==, !=)
    ("==", Type.INT, Type.INT): Type.BOOL,
    ("==", Type.FLOAT, Type.FLOAT): Type.BOOL,
    ("==", Type.INT, Type.FLOAT): Type.BOOL,
    ("==", Type.FLOAT, Type.INT): Type.BOOL,
    ("==", Type.BOOL, Type.BOOL): Type.BOOL,
    ("==", Type.STRING, Type.STRING): Type.BOOL,

    ("!=", Type.INT, Type.INT): Type.BOOL,
    ("!=", Type.FLOAT, Type.FLOAT): Type.BOOL,
    ("!=", Type.INT, Type.FLOAT): Type.BOOL,
    ("!=", Type.FLOAT, Type.INT): Type.BOOL,
    ("!=", Type.BOOL, Type.BOOL): Type.BOOL,
    ("!=", Type.STRING, Type.STRING): Type.BOOL,

    # Logical operators (&&, ||)
    ("&&", Type.BOOL, Type.BOOL): Type.BOOL,
    ("||", Type.BOOL, Type.BOOL): Type.BOOL,
}


COMPOUND_TO_BINARY: dict[str, str] = {
    "+=": "+",
    "-=": "-",
    "*=": "*",
    "/=": "/",
    "%=": "%",
}

