"""Unified diagnostic rendering for C-- with source snippet, plain explanation, and fix guidance."""

from __future__ import annotations

import textwrap
from typing import Optional

from cmm.errors import CmmError, format_error
from cmm.explanations import EXPLANATIONS, ExplanationContext


def render_diagnostic(
    err: CmmError,
    path: str,
    source_lines: list[str],
    help_enabled: bool = True,
) -> str:
    """Render a C-- diagnostic per §2 and §8.

    Args:
        err: The CmmError instance.
        path: File path as given on command line.
        source_lines: Normalized source lines.
        help_enabled: If False, formats as the original 3-line format of SPEC §10.1.

    Returns:
        The formatted diagnostic string ending with a newline.
    """
    if not help_enabled:
        return format_error(err, path, source_lines)

    # Line 1 is byte-for-byte the existing diagnostic line
    header = f"{path}:{err.line}:{err.col}: {err.kind} error: {err.message}\n"

    # Build snippet block
    snippet_lines: list[str] = []
    has_source = False
    line_idx = err.line - 1

    if source_lines and any(line.strip() for line in source_lines):
        has_source = True
        if line_idx >= len(source_lines):
            # EOF past last line: use last line
            line_idx = len(source_lines) - 1
            line_num = line_idx + 1
            raw_line = source_lines[line_idx].rstrip("\r\n")
            col = len(raw_line) + 1
        elif line_idx < 0:
            line_num = 1
            raw_line = source_lines[0].rstrip("\r\n") if source_lines else ""
            col = err.col
        else:
            line_num = err.line
            raw_line = source_lines[line_idx].rstrip("\r\n")
            col = err.col

        # Width of the line number column
        gutter_w = max(len(str(line_num)), 1)
        spacer = f"{' ' * (gutter_w + 1)}|"

        # Handle lines longer than 100 characters per §2
        display_line = raw_line
        display_col = col

        if len(raw_line) > 100:
            # Window around caret
            start = max(0, col - 40)
            end = min(len(raw_line), start + 80)
            prefix = "..." if start > 0 else ""
            suffix = "..." if end < len(raw_line) else ""
            display_line = prefix + raw_line[start:end] + suffix
            display_col = (col - start) + len(prefix)

        # Build caret line with tab preservation (§2)
        token_len = int(err.details.get("token_len", 1))
        if token_len < 1:
            token_len = 1

        prefix_chars: list[str] = []
        for i in range(display_col - 1):
            if i < len(display_line) and display_line[i] == "\t":
                prefix_chars.append("\t")
            else:
                prefix_chars.append(" ")

        caret_chars = "^" * token_len
        caret_line = f"{''.join(prefix_chars)}{caret_chars}"

        snippet_lines.append(f"{spacer}\n")
        snippet_lines.append(f"{line_num:>{gutter_w}} | {display_line}\n")
        snippet_lines.append(f"{spacer} {caret_line}\n")

    snippet_block = "".join(snippet_lines)

    # Explanation block
    expl = EXPLANATIONS.get(err.code)
    if expl is None:
        return f"{header}{snippet_block}"

    ctx = ExplanationContext(
        code=err.code,
        message=err.message,
        line=err.line,
        col=err.col,
        details=err.details,
        source_line=source_lines[line_idx].rstrip("\r\n") if (source_lines and 0 <= line_idx < len(source_lines)) else "",
    )

    what_text = expl.render_what(ctx)
    fix_text = expl.render_fix(ctx)
    example_code = expl.render_example(ctx)

    # Wrap what and fix at 76 columns, indenting by 2 spaces
    what_wrapped = textwrap.fill(what_text, width=76, initial_indent="  ", subsequent_indent="  ")
    fix_wrapped = textwrap.fill(fix_text, width=76, initial_indent="  ", subsequent_indent="  ")

    blocks: list[str] = [
        header,
        snippet_block,
        "what went wrong:\n",
        f"{what_wrapped}\n",
        "how to fix:\n",
        f"{fix_wrapped}\n",
    ]

    if example_code:
        for ex_line in example_code.strip("\n").splitlines():
            blocks.append(f"      {ex_line}\n")

    suggestion = err.details.get("suggestion")
    if suggestion:
        blocks.append(f"  did you mean '{suggestion}'?\n")

    return "".join(blocks)
