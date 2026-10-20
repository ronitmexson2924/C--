"""Runtime representations of C-- v0.2 collections per Section A6.4, A6.6."""

from __future__ import annotations

import copy
from typing import Any

from cmm.errors import CmmRuntimeError

MAX_COLLECTION_SIZE = 10_000_000


class CmmArray:
    """Fixed-size array with zero-based index access."""

    def __init__(self, elements: list[Any]) -> None:
        self.elements = list(elements)

    def clone(self) -> CmmArray:
        return CmmArray(copy.deepcopy(self.elements))

    def get(self, index: int, line: int, col: int) -> Any:
        if index < 0 or index >= len(self.elements):
            raise CmmRuntimeError(
                "R006",
                f"index out of range (index {index}, length {len(self.elements)})",
                line,
                col,
            )
        return self.elements[index]

    def set(self, index: int, val: Any, line: int, col: int) -> None:
        if index < 0 or index >= len(self.elements):
            raise CmmRuntimeError(
                "R006",
                f"index out of range (index {index}, length {len(self.elements)})",
                line,
                col,
            )
        self.elements[index] = val

    def len(self) -> int:
        return len(self.elements)


class CmmList:
    """Dynamic list with push, pop, insert, remove, clear."""

    def __init__(self, elements: list[Any]) -> None:
        self.elements = list(elements)

    def clone(self) -> CmmList:
        return CmmList(copy.deepcopy(self.elements))

    def get(self, index: int, line: int, col: int) -> Any:
        if index < 0 or index >= len(self.elements):
            raise CmmRuntimeError(
                "R006",
                f"index out of range (index {index}, length {len(self.elements)})",
                line,
                col,
            )
        return self.elements[index]

    def set(self, index: int, val: Any, line: int, col: int) -> None:
        if index < 0 or index >= len(self.elements):
            raise CmmRuntimeError(
                "R006",
                f"index out of range (index {index}, length {len(self.elements)})",
                line,
                col,
            )
        self.elements[index] = val

    def len(self) -> int:
        return len(self.elements)

    def is_empty(self) -> bool:
        return len(self.elements) == 0

    def contains(self, item: Any) -> bool:
        return any(type(x) is type(item) and x == item for x in self.elements)

    def push(self, item: Any, line: int, col: int) -> None:
        if len(self.elements) + 1 > MAX_COLLECTION_SIZE:
            raise CmmRuntimeError(
                "R013",
                f"collection size limit exceeded ({MAX_COLLECTION_SIZE})",
                line,
                col,
            )
        self.elements.append(item)

    def pop(self, line: int, col: int) -> Any:
        if not self.elements:
            raise CmmRuntimeError("R012", "pop on empty list", line, col)
        return self.elements.pop()

    def insert(self, index: int, item: Any, line: int, col: int) -> None:
        if index < 0 or index > len(self.elements):
            raise CmmRuntimeError(
                "R006",
                f"index out of range (index {index}, length {len(self.elements)})",
                line,
                col,
            )
        if len(self.elements) + 1 > MAX_COLLECTION_SIZE:
            raise CmmRuntimeError(
                "R013",
                f"collection size limit exceeded ({MAX_COLLECTION_SIZE})",
                line,
                col,
            )
        self.elements.insert(index, item)

    def remove(self, index: int, line: int, col: int) -> Any:
        if index < 0 or index >= len(self.elements):
            raise CmmRuntimeError(
                "R006",
                f"index out of range (index {index}, length {len(self.elements)})",
                line,
                col,
            )
        return self.elements.pop(index)

    def clear(self) -> None:
        self.elements.clear()


class CmmStack:
    """LIFO stack."""

    def __init__(self, elements: list[Any]) -> None:
        self.elements = list(elements)

    def clone(self) -> CmmStack:
        return CmmStack(copy.deepcopy(self.elements))

    def push(self, item: Any, line: int, col: int) -> None:
        if len(self.elements) + 1 > MAX_COLLECTION_SIZE:
            raise CmmRuntimeError(
                "R013",
                f"collection size limit exceeded ({MAX_COLLECTION_SIZE})",
                line,
                col,
            )
        self.elements.append(item)

    def pop(self, line: int, col: int) -> Any:
        if not self.elements:
            raise CmmRuntimeError("R012", "pop on empty stack", line, col)
        return self.elements.pop()

    def peek(self, line: int, col: int) -> Any:
        if not self.elements:
            raise CmmRuntimeError("R012", "peek on empty stack", line, col)
        return self.elements[-1]

    def len(self) -> int:
        return len(self.elements)

    def is_empty(self) -> bool:
        return len(self.elements) == 0

    def clear(self) -> None:
        self.elements.clear()


class CmmQueue:
    """FIFO queue."""

    def __init__(self, elements: list[Any]) -> None:
        self.elements = list(elements)

    def clone(self) -> CmmQueue:
        return CmmQueue(copy.deepcopy(self.elements))

    def enqueue(self, item: Any, line: int, col: int) -> None:
        if len(self.elements) + 1 > MAX_COLLECTION_SIZE:
            raise CmmRuntimeError(
                "R013",
                f"collection size limit exceeded ({MAX_COLLECTION_SIZE})",
                line,
                col,
            )
        self.elements.append(item)

    def dequeue(self, line: int, col: int) -> Any:
        if not self.elements:
            raise CmmRuntimeError("R012", "dequeue on empty queue", line, col)
        return self.elements.pop(0)

    def peek(self, line: int, col: int) -> Any:
        if not self.elements:
            raise CmmRuntimeError("R012", "peek on empty queue", line, col)
        return self.elements[0]

    def len(self) -> int:
        return len(self.elements)

    def is_empty(self) -> bool:
        return len(self.elements) == 0

    def clear(self) -> None:
        self.elements.clear()


def copy_value(val: Any) -> Any:
    """Ensure collections are deeply cloned on assignment, parameter passing, and return."""
    if isinstance(val, (CmmArray, CmmList, CmmStack, CmmQueue)):
        return val.clone()
    return val
