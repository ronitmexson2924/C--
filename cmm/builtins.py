"""Built-in function and method signatures for C-- v0.2.0 per §A6.2 and §A6.4."""

from dataclasses import dataclass
from typing import Optional
from cmm.types import Type


@dataclass(frozen=True)
class FunctionSignature:
    """Signature of a function."""

    name: str
    param_types: list[Type]
    return_type: Type  # Type.VOID for void functions


@dataclass(frozen=True)
class MethodSignature:
    """Signature of a collection method."""

    name: str
    param_types: list[str]  # e.g. ["int", "T"] or ["T"]
    return_type: str        # e.g. "int", "bool", "void", "T"
    mutates: bool


# Built-in functions
BUILTIN_FUNCTION_NAMES: set[str] = {"input", "parse_int", "parse_float"}

# Method tables per receiver kind
COLLECTION_METHODS: dict[str, dict[str, MethodSignature]] = {
    "string": {
        "len": MethodSignature("len", [], "int", False),
    },
    "array": {
        "len": MethodSignature("len", [], "int", False),
    },
    "list": {
        "len": MethodSignature("len", [], "int", False),
        "is_empty": MethodSignature("is_empty", [], "bool", False),
        "contains": MethodSignature("contains", ["T"], "bool", False),
        "push": MethodSignature("push", ["T"], "void", True),
        "pop": MethodSignature("pop", [], "T", True),
        "insert": MethodSignature("insert", ["int", "T"], "void", True),
        "remove": MethodSignature("remove", ["int"], "T", True),
        "clear": MethodSignature("clear", [], "void", True),
    },
    "stack": {
        "push": MethodSignature("push", ["T"], "void", True),
        "pop": MethodSignature("pop", [], "T", True),
        "peek": MethodSignature("peek", [], "T", False),
        "len": MethodSignature("len", [], "int", False),
        "is_empty": MethodSignature("is_empty", [], "bool", False),
        "clear": MethodSignature("clear", [], "void", True),
    },
    "queue": {
        "enqueue": MethodSignature("enqueue", ["T"], "void", True),
        "dequeue": MethodSignature("dequeue", [], "T", True),
        "peek": MethodSignature("peek", [], "T", False),
        "len": MethodSignature("len", [], "int", False),
        "is_empty": MethodSignature("is_empty", [], "bool", False),
        "clear": MethodSignature("clear", [], "void", True),
    },
}
