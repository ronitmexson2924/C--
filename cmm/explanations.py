"""Plain-language diagnostic explanations, context model, and catalog for C-- per §3, §4, §5, §6."""

from __future__ import annotations

import re
from typing import Any, Callable, Optional


class ExplanationContext:
    """Carries rich context for building beginner-friendly diagnostic help."""

    def __init__(
        self,
        code: str,
        message: str,
        line: int,
        col: int,
        details: Optional[dict[str, Any]] = None,
        source_line: str = "",
    ) -> None:
        self.code = code
        self.message = message
        self.line = line
        self.col = col
        self.details = details or {}
        self.source_line = source_line

    def __getitem__(self, key: str) -> Any:
        return self.details.get(key, f"<{key}>")

    def get(self, key: str, default: Any = None) -> Any:
        return self.details.get(key, default)

    def sample_value(self, type_name: Optional[str] = None) -> str:
        """Return a harmless sample literal for code examples per §4.1."""
        t = (type_name or self.get("ret") or self.get("type") or "int").strip()
        if t == "int":
            return "0"
        elif t == "float":
            return "0.0"
        elif t == "bool":
            return "false"
        elif t == "string":
            return '""'
        elif t.startswith("array<"):
            inner = t[6:-1]
            return f"[{self.sample_value(inner)}]"
        elif t.startswith("list<"):
            return f"{t}()"
        elif t.startswith("stack<"):
            return f"{t}()"
        elif t.startswith("queue<"):
            return f"{t}()"
        return "0"


class Explanation:
    """Represents a plain-language explanation and fix action for an error."""

    def __init__(
        self,
        what: str | Callable[[ExplanationContext], str],
        fix: str | Callable[[ExplanationContext], str],
        example: Optional[str | Callable[[ExplanationContext], Optional[str]]] = None,
        example_type: str = "none",  # 'exact', 'pattern', or 'none'
        suggestion_type: str = "none",
    ) -> None:
        self.what = what
        self.fix = fix
        self.example = example
        self.example_type = example_type
        self.suggestion_type = suggestion_type

    def render_what(self, ctx: ExplanationContext) -> str:
        if callable(self.what):
            res = self.what(ctx)
        else:
            res = self.what
            for k, v in ctx.details.items():
                res = res.replace(f"{{{k}}}", str(v))
            res = re.sub(r"\{([a-zA-Z0-9_]+)\}", r"<\1>", res)
        return res

    def render_fix(self, ctx: ExplanationContext) -> str:
        if callable(self.fix):
            res = self.fix(ctx)
        else:
            res = self.fix
            for k, v in ctx.details.items():
                res = res.replace(f"{{{k}}}", str(v))
            res = re.sub(r"\{([a-zA-Z0-9_]+)\}", r"<\1>", res)
        return res

    def render_example(self, ctx: ExplanationContext) -> Optional[str]:
        if self.example is None:
            return None
        if callable(self.example):
            res = self.example(ctx)
            if res is None:
                return None
        else:
            res = self.example
            for k, v in ctx.details.items():
                res = res.replace(f"{{{k}}}", str(v))
            res = re.sub(r"\{([a-zA-Z0-9_]+)\}", r"<\1>", res)
        return res


def _format_s001_fix(ctx: ExplanationContext) -> str:
    expected = str(ctx.get("expected", ""))
    found = str(ctx.get("found", ""))

    if expected == "';'":
        return "Add a semicolon ';' at the end of the line."
    elif expected in ("'('", "')'"):
        return f"Add the missing {expected} to match the opening parenthesis."
    elif expected in ("'{'", "'}'"):
        return f"Add the missing {expected} to close the block."
    elif expected == "'fn'":
        return "Put this code inside a function. Start with 'fn main() { ... }'."
    elif expected == "assignment, call or method call":
        return "Check the statement after this name. You can assign with '=', call a function with '()', or call a method with '.'."
    elif expected == "expression":
        return "Provide a valid value or variable name here."
    elif expected == "statement":
        return "Provide a valid statement, such as a variable declaration, assignment, call, or loop."
    return f"Replace {found} with {expected}."


# Complete dictionary of explanations for all C-- v0.2.0 diagnostic codes
EXPLANATIONS: dict[str, Explanation] = {
    # -------------------------------------------------------------------------
    # Lexical Diagnostics (L001 - L012)
    # -------------------------------------------------------------------------
    "L001": Explanation(
        what="The character '{formatted_char}' is not recognized in C-- code.",
        fix="Remove this character or replace it with valid C-- code.",
        example=None,
        example_type="none",
    ),
    "L002": Explanation(
        what="This text starts with a quote but never ends.",
        fix="Add the closing quote on the same line. For text over several lines use triple quotes \"\"\"...\"\"\" or '''...'''.",
        example='"""multi-line text"""',
        example_type="exact",
    ),
    "L003": Explanation(
        what="A backslash must be followed by one of the allowed letters, and '\\{esc_display}' is not one.",
        fix="Use one of \\n, \\t, \\r, \\\", \\', \\\\. To write a real backslash type '\\\\'.",
        example=r'"first line\nsecond line"',
        example_type="exact",
    ),
    "L004": Explanation(
        what="A multi-line comment starts with '/*' here, but never reaches a closing '*/'.",
        fix="Add '*/' where the comment should end.",
        example="/* comment */",
        example_type="exact",
    ),
    "L005": Explanation(
        what="This integer number is too large to fit in a 64-bit signed integer.",
        fix="Use an integer between -9223372036854775808 and 9223372036854775807.",
        example="9223372036854775807",
        example_type="exact",
    ),
    "L006": Explanation(
        what="This decimal number is too large to fit in a 64-bit floating point number.",
        fix="Use a smaller number or adjust the exponent.",
        example="1.0e100",
        example_type="exact",
    ),
    "L007": Explanation(
        what="This number is malformed.",
        fix="Write digits after the dot (for example '1.0' instead of '1.') or check the exponent format.",
        example="1.0",
        example_type="exact",
    ),
    "L008": Explanation(
        what="Numbers cannot start with extra zeros.",
        fix="Remove the leading zero from the number.",
        example="7",
        example_type="exact",
    ),
    "L009": Explanation(
        what="C-- does not have a '++' operator.",
        fix="Use '+= 1' to increase the value by one.",
        example="x += 1;",
        example_type="exact",
    ),
    "L010": Explanation(
        what="C-- does not have a '--' operator.",
        fix="Use '-= 1' to decrease the value by one.",
        example="x -= 1;",
        example_type="exact",
    ),
    "L011": Explanation(
        what="C-- does not have a single '&' symbol.",
        fix="Use '&&' for logical AND.",
        example="a && b",
        example_type="exact",
    ),
    "L012": Explanation(
        what="C-- does not have a single '|' symbol.",
        fix="Use '||' for logical OR.",
        example="a || b",
        example_type="exact",
    ),

    # -------------------------------------------------------------------------
    # Syntax Diagnostics (S001, S003, S004) - Note: S002 is retired
    # -------------------------------------------------------------------------
    "S001": Explanation(
        what="At this spot C-- expected {expected}, but found {found}.",
        fix=_format_s001_fix,
        example=lambda ctx: ";" if ctx.get("expected") == "';'" else None,
        example_type="pattern",
        suggestion_type="keyword",
    ),
    "S003": Explanation(
        what="'{word}' is a reserved word saved for future versions of C--.",
        fix="Rename this to a different name, for example '{word}_val'.",
        example=None,
        example_type="none",
    ),
    "S004": Explanation(
        what="The code is nested more than 200 levels deep.",
        fix="Split the inner part into a separate function.",
        example=None,
        example_type="none",
    ),

    # -------------------------------------------------------------------------
    # Semantic Diagnostics (E001 - E031, omitting unassigned E018)
    # -------------------------------------------------------------------------
    "E001": Explanation(
        what="'{name}' has not been declared in this scope.",
        fix="Declare '{name}' before using it, with 'let {name} = ...;' or 'mut {name} = ...;'.",
        example=lambda ctx: f"let {ctx.get('name', 'x')} = 0;",
        example_type="pattern",
        suggestion_type="variable",
    ),
    "E002": Explanation(
        what="A variable named '{name}' already exists in this scope.",
        fix="Choose a different name for this variable, or assign to the existing one without 'let' or 'mut'.",
        example=lambda ctx: f"{ctx.get('name', 'x')} = 0;",
        example_type="pattern",
    ),
    "E003": Explanation(
        what="In C--, variables declared with 'let' cannot be changed.",
        fix="Declare '{name}' with 'mut' instead if you need to reassign it.",
        example=lambda ctx: f"mut {ctx.get('name', 'x')} = 0;",
        example_type="pattern",
    ),
    "E004": Explanation(
        what="Conditions in 'if' and loops must evaluate to true or false, but got {type}.",
        fix="Use a comparison such as '==', '!=', or '<', or a boolean variable.",
        example="x > 0",
        example_type="pattern",
    ),
    "E005": Explanation(
        what="The '{op}' operator cannot be used on a value of type {type}.",
        fix="Apply '{op}' to compatible types (for example '-' on numbers, or '!' on bool).",
        example=None,
        example_type="none",
    ),
    "E006": Explanation(
        what="The '{op}' operator cannot combine values of type {ltype} and {rtype}.",
        fix="Make sure both sides have matching compatible types. C-- never converts types automatically.",
        example=None,
        example_type="none",
    ),
    "E007": Explanation(
        what="The variable '{name}' holds {ltype}, but the new value is {rtype}.",
        fix="Provide a value of type {ltype}, or change the variable's initial type when declared.",
        example=None,
        example_type="none",
    ),
    "E008": Explanation(
        what="'{name}' is not a function that exists.",
        fix="Check the spelling or define it with 'fn {name}(...) {{ ... }}'.",
        example=lambda ctx: f"fn {ctx.get('name', 'foo')}() {{}}",
        example_type="pattern",
        suggestion_type="function",
    ),
    "E009": Explanation(
        what="There is already a function named '{name}'.",
        fix="Give this function a unique name or remove the duplicate definition.",
        example=None,
        example_type="none",
    ),
    "E010": Explanation(
        what="'{name}' is a built-in function that already exists, so you cannot define your own with that name.",
        fix="Pick another name, for example '{name}_value'.",
        example=lambda ctx: f"fn {ctx.get('name', 'custom')}_value() {{}}",
        example_type="pattern",
    ),
    "E011": Explanation(
        what="{kind} '{name}' requires {expected_count} argument(s), but received {got_count}.",
        fix="Provide the expected number of arguments in the call.",
        example=None,
        example_type="none",
    ),
    "E012": Explanation(
        what="Argument {arg_idx} of {kind} '{name}' requires a {expected_type}, but received a {got_type}.",
        fix="Pass a value of type {expected_type} for argument {arg_idx}. C-- does not convert types automatically.",
        example=None,
        example_type="none",
    ),
    "E013": Explanation(
        what="The function '{name}' promises to give back a {ret}, but in some cases it reaches the end without giving anything back.",
        fix="Make sure every possible path ends with 'return <{ret} value>;'. For example add this as the last line of the function:",
        example=lambda ctx: f"return {ctx.sample_value(ctx.get('ret', 'int'))};",
        example_type="pattern",
    ),
    "E014": Explanation(
        what="The function '{name}' has no return type, so it cannot return a value.",
        fix="Use a bare 'return;' without a value, or declare a return type with '-> <type>'.",
        example="return;",
        example_type="exact",
    ),
    "E015": Explanation(
        what="The function '{name}' promises to return a {ret}, but 'return;' provides no value.",
        fix="Provide a value of type {ret} with 'return <value>;'.",
        example=lambda ctx: f"return {ctx.sample_value(ctx.get('ret', 'int'))};",
        example_type="pattern",
    ),
    "E016": Explanation(
        what="The function '{name}' is declared to return {expected_ret}, but this line returns {got_ret}.",
        fix="Return a value of type {expected_ret}, or change the function's return type.",
        example=lambda ctx: f"return {ctx.sample_value(ctx.get('expected_ret', 'int'))};",
        example_type="pattern",
    ),
    "E017": Explanation(
        what="The 'main' function is the entry point and must take no parameters and return nothing.",
        fix="Declare it as 'fn main() { ... }'.",
        example="fn main() {\n}",
        example_type="exact",
    ),
    "E019": Explanation(
        what="'main' starts the program and cannot be called from other code.",
        fix="Remove the call to 'main'. Put shared code into a helper function and call that instead.",
        example=None,
        example_type="none",
    ),
    "E020": Explanation(
        what="'{name}' does not give back a value, so it cannot be used inside an expression.",
        fix="Call it on its own line: '{name}(...);'.",
        example=lambda ctx: f"{ctx.get('name', 'action')}();",
        example_type="pattern",
    ),
    "E021": Explanation(
        what="The value in 'switch (...)' must be an int or string, but got {type}.",
        fix="Switch on an integer or text value, or use 'if'/'else' for other types.",
        example="switch (x) {\n      case 1: {}\n      default: {}\n}",
        example_type="pattern",
    ),
    "E022": Explanation(
        what="The case value has type {case_type}, but the switch is checking a {selector_type}.",
        fix="Make sure all case values have the same type as the switch value ({selector_type}).",
        example=None,
        example_type="none",
    ),
    "E023": Explanation(
        what="The case value {val} appears more than once in this switch.",
        fix="Remove the duplicate case or change its value.",
        example=None,
        example_type="none",
    ),
    "E024": Explanation(
        what="Values of type {type} cannot be accessed with '[...]'.",
        fix="Only strings, arrays, and lists can be indexed with '[position]'.",
        example=None,
        example_type="none",
    ),
    "E025": Explanation(
        what="Positions inside '[...]' must be integers, but got {type}.",
        fix="Use an integer value or expression for indexing.",
        example="items[0]",
        example_type="pattern",
    ),
    "E026": Explanation(
        what="Values of type {type} do not have a method named '{name}'.",
        fix=lambda ctx: f"Use one of the supported methods for {ctx.get('type')}: {ctx.get('available_methods', 'len')}.",
        example=None,
        example_type="none",
        suggestion_type="method",
    ),
    "E027": Explanation(
        what="Every item in an array literal '[...]' must have the same primitive type.",
        fix="Make sure all elements have matching types, for example all int or all string.",
        example="[1, 2, 3]",
        example_type="exact",
    ),
    "E028": Explanation(
        what="The method '{name}' changes the collection, but '{v}' is an immutable 'let' variable.",
        fix="Declare '{v}' with 'mut' instead: 'mut {v} = ...;'.",
        example=lambda ctx: f"mut {ctx.get('v', 'items')} = list<int>();",
        example_type="pattern",
    ),
    "E029": Explanation(
        what="Elements of '{v}' cannot be modified because it was declared with 'let'.",
        fix="Declare '{v}' with 'mut' instead to allow element assignments.",
        example=lambda ctx: f"mut {ctx.get('v', 'items')} = [1, 2];",
        example_type="pattern",
    ),
    "E030": Explanation(
        what="Text cannot be changed letter by letter in C--.",
        fix="Build the result another way, for example with a list<string> or by creating a new string.",
        example=None,
        example_type="none",
    ),
    "E031": Explanation(
        what="The parameter '{name}' is listed more than once in this function's parameters.",
        fix="Give each parameter a distinct name.",
        example=None,
        example_type="none",
    ),

    # -------------------------------------------------------------------------
    # Runtime Diagnostics (R001 - R014)
    # -------------------------------------------------------------------------
    "R001": Explanation(
        what="The arithmetic calculation produced an integer too large to fit in 64 bits.",
        fix="Check the numbers being computed to prevent exceeding integer limits.",
        example=None,
        example_type="none",
    ),
    "R002": Explanation(
        what="The program attempted to divide a number by zero.",
        fix="Check that the divisor is not zero before dividing.",
        example="if (divisor != 0) {\n      let q = n / divisor;\n}",
        example_type="pattern",
    ),
    "R003": Explanation(
        what="The program attempted to compute remainder ('%') with a divisor of zero.",
        fix="Check that the second number is not zero before using '%'.",
        example="if (b != 0) {\n      let r = a % b;\n}",
        example_type="pattern",
    ),
    "R004": Explanation(
        what="The floating point calculation produced a number too large to represent.",
        fix="Check your numbers to keep values within standard 64-bit float limits.",
        example=None,
        example_type="none",
    ),
    "R005": Explanation(
        what="The program ran more steps than allowed by the --max-steps limit.",
        fix="Increase the --max-steps limit or check that your loops terminate.",
        example=None,
        example_type="none",
    ),
    "R006": Explanation(
        what="You asked for position {index}, but the {kind} only has {length} items (valid positions are 0 to {max_index}). Positions start at 0 and cannot be negative.",
        fix="Check that your position is less than the collection length before indexing.",
        example="if (i < items.len()) {\n      print(items[i]);\n}",
        example_type="pattern",
    ),
    "R007": Explanation(
        what="The function called itself (or others) more than 1000 levels deep.",
        fix="Check that your recursion has a base case that stops it.",
        example=None,
        example_type="none",
    ),
    "R008": Explanation(
        what="The program asked for input, but there is no more input.",
        fix="Provide another line of input, or check how many times the program reads.",
        example=None,
        example_type="none",
    ),
    "R009": Explanation(
        what="The text '{text}' could not be converted to an integer.",
        fix="Provide an integer such as '42' or '-7'. Spaces at the ends are allowed, but letters, underscores, and decimals are not.",
        example='parse_int("42")',
        example_type="exact",
    ),
    "R010": Explanation(
        what="The text '{text}' could not be converted to a decimal number.",
        fix="Provide a valid number such as '3.14' or '1e5'. Words like 'inf' or 'nan' are not allowed.",
        example='parse_float("3.14")',
        example_type="exact",
    ),
    "R011": Explanation(
        what="The input received contains bytes that are not valid UTF-8 text.",
        fix="Ensure standard input is encoded as UTF-8 text.",
        example=None,
        example_type="none",
    ),
    "R012": Explanation(
        what="You tried to take from an empty {kind}.",
        fix=lambda ctx: f"Check {ctx.get('kind', 'collection')}.is_empty() or {ctx.get('kind', 'collection')}.len() > 0 before taking an item.",
        example="if (!items.is_empty()) {\n      items.pop();\n}",
        example_type="pattern",
    ),
    "R013": Explanation(
        what="A collection grew beyond the limit of 10,000,000 elements.",
        fix="Ensure the collection stays within the 10,000,000 element limit.",
        example=None,
        example_type="none",
    ),
    "R014": Explanation(
        what="An array was created with a negative size of {size}.",
        fix="Provide a non-negative size (0 or greater) when creating an array.",
        example="array<int>(5, 0)",
        example_type="exact",
    ),

    # -------------------------------------------------------------------------
    # Transpile Diagnostics (T001)
    # -------------------------------------------------------------------------
    "T001": Explanation(
        what="The C backend only supports the v0.1 feature subset and cannot compile {feature}.",
        fix="Use the reference interpreter ('cmm run') to run programs using v0.2 features.",
        example=None,
        example_type="none",
    ),
}
