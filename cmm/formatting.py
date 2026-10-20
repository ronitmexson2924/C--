"""Value and float formatting per Section 9 of SPEC.md."""

import math


def format_float(x: float) -> str:
    """Format float per Section 9.1 of SPEC.md.

    1. If zero: print '0.0', or '-0.0' for negative zero.
    2. Shortest decimal round-trip representation d1.d2...dn * 10^E.
    3. Positional if -4 <= E < 16:
       - E >= 0: first E+1 digits (padded with 0s if shorter) . remaining (or 0)
       - E < 0: 0. followed by (-E-1) zeros followed by D
    4. Scientific otherwise:
       d1. + (d2...dn or '0') + 'e' + sign ('+' or '-') + abs(E) (>=2 digits)
    5. Prepend '-' for negative numbers.
    """
    # 1. Zero check
    if x == 0.0:
        if math.copysign(1.0, x) < 0.0:
            return "-0.0"
        return "0.0"

    sign_str = "-" if x < 0.0 or math.copysign(1.0, x) < 0.0 else ""
    abs_x = abs(x)

    # Use Python's shortest round-trip float representation (Ryu/dtoa)
    repr_str = repr(abs_x)

    # Extract D and E
    if "e" in repr_str or "E" in repr_str:
        mantissa, exp_part = repr_str.lower().split("e")
        e_val = int(exp_part)
        d_digits = mantissa.replace(".", "").rstrip("0")
    else:
        int_part, frac_part = repr_str.split(".")
        if int_part == "0":
            leading_zeros = len(frac_part) - len(frac_part.lstrip("0"))
            d_digits = frac_part.lstrip("0").rstrip("0")
            e_val = -1 - leading_zeros
        else:
            d_digits = (int_part + frac_part).rstrip("0")
            e_val = len(int_part) - 1

    # 3. Positional notation: -4 <= E < 16
    if -4 <= e_val < 16:
        if e_val >= 0:
            int_len = e_val + 1
            if len(d_digits) >= int_len:
                int_str = d_digits[:int_len]
                frac_str = d_digits[int_len:]
                if not frac_str:
                    frac_str = "0"
            else:
                int_str = d_digits + "0" * (int_len - len(d_digits))
                frac_str = "0"
            return f"{sign_str}{int_str}.{frac_str}"
        else:
            zero_count = -e_val - 1
            return f"{sign_str}0.{'0' * zero_count}{d_digits}"

    # 4. Scientific notation
    d1 = d_digits[0]
    rest = d_digits[1:] if len(d_digits) > 1 else "0"
    exp_sign = "+" if e_val >= 0 else "-"
    abs_exp_str = f"{abs(e_val):02d}"
    return f"{sign_str}{d1}.{rest}e{exp_sign}{abs_exp_str}"


from typing import Any

from cmm.runtime_values import CmmArray, CmmList, CmmQueue, CmmStack


def escape_collection_string(s: str) -> str:
    """Escape string element inside collections per §A6.7."""
    escaped = (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\t", "\\t")
        .replace("\r", "\\r")
    )
    return f'"{escaped}"'


def format_collection_element(v: Any) -> str:
    """Format primitive element inside collection per §A6.7."""
    if isinstance(v, str):
        return escape_collection_string(v)
    elif isinstance(v, bool):
        return "true" if v else "false"
    elif isinstance(v, int):
        return str(v)
    elif isinstance(v, float):
        return format_float(v)
    raise TypeError(f"Cannot format element of unexpected type: {type(v)}")


def format_value(v: Any) -> str:
    """Format any C-- runtime value for print statement per Section 9 and §A6.7."""
    if isinstance(v, bool):
        return "true" if v else "false"
    elif isinstance(v, int):
        return str(v)
    elif isinstance(v, float):
        return format_float(v)
    elif isinstance(v, str):
        return v
    elif isinstance(v, (CmmArray, CmmList)):
        inner = ", ".join(format_collection_element(x) for x in v.elements)
        return f"[{inner}]"
    elif isinstance(v, CmmStack):
        inner = ", ".join(format_collection_element(x) for x in v.elements)
        return f"stack[{inner}]"
    elif isinstance(v, CmmQueue):
        inner = ", ".join(format_collection_element(x) for x in v.elements)
        return f"queue[{inner}]"
    raise TypeError(f"Cannot format value of unexpected type: {type(v)}")

