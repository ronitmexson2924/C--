"""Runtime I/O and conversion helpers for C-- v0.2.0 per §A6.2."""

import re
import sys
from typing import Any, BinaryIO, Optional
from cmm.errors import CmmRuntimeError

_INT_REGEX = re.compile(r"^[+-]?[0-9]+$")
_FLOAT_REGEX = re.compile(r"^[+-]?[0-9]+(\.[0-9]+)?([eE][+-]?[0-9]+)?$")


import io


def cmm_read_line(
    stream: Optional[Any] = None,
    prompt: Optional[str] = None,
    line: int = 1,
    col: int = 1,
) -> str:
    """Read one line from standard input per §A6.2.

    - Flushes stdout if prompt is given.
    - Reads byte-by-byte (or char-by-char if text stream) until newline or EOF.
    - Decodes as strict UTF-8 (R011 on failure).
    - Removes one trailing '\\n', then one trailing '\\r' if present.
    - If EOF reached before any byte is read -> R008.
    """
    if prompt is not None:
        sys.stdout.write(prompt)
        sys.stdout.flush()

    if stream is None:
        if hasattr(sys.stdin, "buffer"):
            stream = sys.stdin.buffer
        else:
            stream = sys.stdin

    # If stream is a text stream (e.g. io.StringIO in tests)
    if isinstance(stream, io.TextIOBase):
        chars: list[str] = []
        while True:
            ch = stream.read(1)
            if not ch:
                if len(chars) == 0:
                    raise CmmRuntimeError("R008", "end of input", line, col)
                break
            chars.append(ch)
            if ch == "\n":
                break
        res = "".join(chars)
        if res.endswith("\n"):
            res = res[:-1]
        if res.endswith("\r"):
            res = res[:-1]
        return res

    # Binary stream (e.g. sys.stdin.buffer or BytesIO)
    raw_bytes = bytearray()
    while True:
        b = stream.read(1)
        if not b:
            # EOF
            if len(raw_bytes) == 0:
                raise CmmRuntimeError("R008", "end of input", line, col)
            break
        raw_bytes.extend(b)
        if b == b"\n":
            break

    # Decode strict UTF-8
    try:
        decoded = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise CmmRuntimeError("R011", "standard input is not valid UTF-8", line, col)

    # Strip one trailing \n, then one trailing \r if present
    if decoded.endswith("\n"):
        decoded = decoded[:-1]
    if decoded.endswith("\r"):
        decoded = decoded[:-1]

    return decoded


read_cmm_line = cmm_read_line



def cmm_parse_int(s: str, line: int = 1, col: int = 1) -> int:
    """Parse integer per §A6.2."""
    stripped = s.strip(" \t")
    if not stripped or not _INT_REGEX.match(stripped):
        raise CmmRuntimeError("R009", f"cannot convert '{s}' to int", line, col, details={"text": s})

    try:
        val = int(stripped)
    except ValueError:
        raise CmmRuntimeError("R009", f"cannot convert '{s}' to int", line, col, details={"text": s})

    # 64-bit signed integer limits: [-9223372036854775808, 9223372036854775807]
    if val < -9223372036854775808 or val > 9223372036854775807:
        raise CmmRuntimeError("R009", f"cannot convert '{s}' to int", line, col, details={"text": s})

    return val


def cmm_parse_float(s: str, line: int = 1, col: int = 1) -> float:
    """Parse float per §A6.2."""
    stripped = s.strip(" \t")
    # Reject inf, nan, hex, underscores, or regex mismatch
    lower = stripped.lower()
    if (
        not stripped
        or "inf" in lower
        or "nan" in lower
        or "0x" in lower
        or "_" in stripped
        or not _FLOAT_REGEX.match(stripped)
    ):
        raise CmmRuntimeError("R010", f"cannot convert '{s}' to float", line, col, details={"text": s})

    try:
        val = float(stripped)
        import math
        if math.isinf(val) or math.isnan(val):
            raise CmmRuntimeError("R010", f"cannot convert '{s}' to float", line, col, details={"text": s})
    except (ValueError, OverflowError):
        raise CmmRuntimeError("R010", f"cannot convert '{s}' to float", line, col, details={"text": s})

    return val
