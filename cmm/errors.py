from typing import Any, Optional


class CmmError(Exception):
    """Base exception for all C-- compiler and runtime errors."""

    def __init__(
        self,
        kind: str,
        code: str,
        message: str,
        line: int,
        col: int,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize a C-- error.

        Args:
            kind: One of "lexical", "syntax", "semantic", "runtime", "transpile".
            code: Error code such as "L001", "S001", "E003", "R002".
            message: Descriptive error message string.
            line: 1-based line number.
            col: 1-based column number.
            details: Optional structured contextual details for error explanation.
        """
        super().__init__(message)
        self.kind = kind
        self.code = code
        self.message = message
        self.line = line
        self.col = col
        self.details = details if details is not None else {}


class LexError(CmmError):
    """Lexical error raised during tokenization."""

    def __init__(
        self,
        code: str,
        message: str,
        line: int,
        col: int,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize a lexical error."""
        super().__init__("lexical", code, message, line, col, details)


class ParseError(CmmError):
    """Syntax error raised during parsing (not named SyntaxError to avoid shadowing builtin)."""

    def __init__(
        self,
        code: str,
        message: str,
        line: int,
        col: int,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize a syntax error."""
        super().__init__("syntax", code, message, line, col, details)


class SemanticError(CmmError):
    """Semantic error raised during analysis and type checking."""

    def __init__(
        self,
        code: str,
        message: str,
        line: int,
        col: int,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize a semantic error."""
        super().__init__("semantic", code, message, line, col, details)


class CmmRuntimeError(CmmError):
    """Runtime error raised during program execution (not named RuntimeError)."""

    def __init__(
        self,
        code: str,
        message: str,
        line: int,
        col: int,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize a runtime error."""
        super().__init__("runtime", code, message, line, col, details)


class TranspileError(CmmError):
    """Error raised during transpilation or code generation."""

    def __init__(
        self,
        code: str,
        message: str,
        line: int,
        col: int,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize a transpile error."""
        super().__init__("transpile", code, message, line, col, details)


def format_error(err: CmmError, path: str, source_lines: list[str]) -> str:
    """Return the exact 3-line text of §10.1 (including the final newline).

    Format:
    <path>:<line>:<col>: <kind> error: <message>
        <source line>
        <caret line>

    Args:
        err: The CmmError instance.
        path: File path as given on command line.
        source_lines: Normalized source lines.

    Returns:
        Exact 3-line formatted error string ending with newline.
    """
    header = f"{path}:{err.line}:{err.col}: {err.kind} error: {err.message}\n"

    line_idx = err.line - 1
    if 0 <= line_idx < len(source_lines):
        src_line = source_lines[line_idx].rstrip("\r\n")
    else:
        src_line = ""

    line2 = f"    {src_line}\n"

    prefix_chars: list[str] = []
    for i in range(err.col - 1):
        if i < len(src_line) and src_line[i] == "\t":
            prefix_chars.append("\t")
        else:
            prefix_chars.append(" ")

    caret_line = f"    {''.join(prefix_chars)}^\n"

    return f"{header}{line2}{caret_line}"
