"""Type enum, Symbol dataclass, and operator typing tables for C-- per Section 7.2 and 12.6."""

from dataclasses import dataclass
from enum import Enum


class Type(Enum):
    """The four types of C-- plus the internal INVALID type for error cascade suppression."""

    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    STRING = "string"
    INVALID = "invalid"

    def __str__(self) -> str:
        return self.value


@dataclass
class Symbol:
    """A symbol table entry recording variable metadata.

    Attributes:
        type: The inferred C-- type of the variable.
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

# Mapping of compound assignment operators to underlying binary arithmetic operators
COMPOUND_TO_BINARY: dict[str, str] = {
    "+=": "+",
    "-=": "-",
    "*=": "*",
    "/=": "/",
    "%=": "%",
}
