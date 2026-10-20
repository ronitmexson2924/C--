#!/usr/bin/env python3
"""Generate docs/errors.md programmatically from cmm.explanations.EXPLANATIONS."""

from pathlib import Path
import sys

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from cmm.explanations import EXPLANATIONS, ExplanationContext


def _get_category(code: str) -> str:
    if code.startswith("L"):
        return "Lexical Diagnostics (L001 – L012)"
    elif code.startswith("S"):
        return "Syntax Diagnostics (S001 – S004)"
    elif code.startswith("E"):
        return "Semantic Diagnostics (E001 – E031)"
    elif code.startswith("R"):
        return "Runtime Diagnostics (R001 – R014)"
    elif code.startswith("T"):
        return "Transpilation Diagnostics (T001)"
    return "Other Diagnostics"


def generate_markdown() -> str:
    lines: list[str] = [
        "# C-- Diagnostic Reference Guide",
        "",
        "This guide documents all active compiler and runtime diagnostic codes in C-- v0.2.0,",
        "including plain-language explanations and recommended fix actions.",
        "",
        "## Diagnostic Codes Index",
        "",
        "| Code | Category | Plain Explanation Summary | Example Available |",
        "| :--- | :--- | :--- | :---: |",
    ]

    # Category grouping
    categories: dict[str, list[str]] = {}
    for code in sorted(EXPLANATIONS.keys(), key=lambda c: (c[0], int(c[1:]))):
        cat = _get_category(code)
        categories.setdefault(cat, []).append(code)

        expl = EXPLANATIONS[code]
        dummy_ctx = ExplanationContext(code=code, message="", line=1, col=1)
        what_str = expl.render_what(dummy_ctx).replace("\n", " ")
        if len(what_str) > 70:
            what_str = what_str[:67] + "..."
        has_ex = "Yes" if expl.example is not None else "No"
        lines.append(f"| `{code}` | {cat.split()[0]} | {what_str} | {has_ex} |")

    lines.append("")

    for cat_name, codes in categories.items():
        lines.append(f"## {cat_name}")
        lines.append("")
        for code in codes:
            expl = EXPLANATIONS[code]
            dummy_ctx = ExplanationContext(code=code, message="", line=1, col=1)
            what_text = expl.render_what(dummy_ctx)
            fix_text = expl.render_fix(dummy_ctx)
            example_code = expl.render_example(dummy_ctx)

            lines.append(f"### `{code}`")
            lines.append("")
            lines.append(f"**What went wrong:**  ")
            lines.append(what_text)
            lines.append("")
            lines.append(f"**How to fix:**  ")
            lines.append(fix_text)
            lines.append("")

            if example_code:
                lines.append("**Example:**")
                lines.append("```cmm")
                lines.append(example_code.strip())
                lines.append("```")
                lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    doc_path = REPO_ROOT / "docs" / "errors.md"
    content = generate_markdown()
    doc_path.write_text(content, encoding="utf-8")
    print(f"Generated {doc_path} ({len(content)} bytes)")


if __name__ == "__main__":
    main()
