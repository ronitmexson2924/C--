# C-- (C Minus Minus) — Language Guide & Programmer's Manual

**Version:** 0.1.0  
**Status:** Stable Reference  
**Normative Specification:** [`SPEC.md`](./SPEC.md)

Welcome to the **C-- Language Guide**. This document serves as the practical programmer's manual for learning, writing, and debugging programs in **C--**, a modern imperative language engineered around the foundational philosophy of **"Safety by Removal"**.

---

## Table of Contents

1. [Philosophy: Safety by Removal](#1-philosophy-safety-by-removal)
2. [Program Structure & Entry Point](#2-program-structure--entry-point)
3. [Type System & Literals](#3-type-system--literals)
4. [Variables, Bindings & Scoping](#4-variables-bindings--scoping)
5. [Expressions & Operators](#5-expressions--operators)
6. [Control Flow Constructs](#6-control-flow-constructs)
7. [Built-in Functions (I/O)](#7-built-in-functions-io)
8. [Compiler Diagnostics & Error Rectification](#8-compiler-diagnostics--error-rectification)
9. [Execution Modes: Interpreter vs C99 Transpiler](#9-execution-modes-interpreter-vs-c99-transpiler)
10. [Idiomatic Code Recipes](#10-idiomatic-code-recipes)

---

## 1. Philosophy: Safety by Removal

For over 50 years, systems programming languages like C and C++ have suffered from memory safety vulnerabilities. Industry research reveals that **over 70% of all high-severity CVEs** trace back to memory corruption, uninitialized pointers, or arithmetic misbehavior.

Traditional solutions either add complex runtime garbage collectors (which compromise predictable latency) or intricate borrow-checkers (which impose steep cognitive overhead).

**C-- takes a different approach: Safety by Removal.** Rather than attempting to patch dangerous behavior at runtime, C-- completely eliminates unsafe constructs from the grammar and type system:

| Unsafe Pitfall in C/C++ | How C-- Eliminates It |
|:---|:---|
| **NULL Pointer Dereferences (`SIGSEGV`)** | **Zero NULL pointers.** The concept of NULL or raw memory pointers does not exist in C--. |
| **Out-of-Bounds Pointer Arithmetic** | **Zero pointer arithmetic.** Memory cannot be indexed or offset beyond safe boundaries. |
| **Uninitialized Variable Reads** | **Mandatory initialization.** Every variable must be initialized with an expression upon declaration. |
| **Silent Mutation Bugs** | **Immutable by default.** Variables declared with `let` are permanent constants; mutability requires `mut`. |
| **Silent Integer Wrap-Around** | **Trapped 64-bit overflow.** Integer operations exceeding $[-2^{63}, 2^{63}-1]$ immediately trap with `R001`. |
| **Implicit Type Coercion / Truthy Bugs** | **Strict boolean typing.** Conditionals require exact `bool` values (`true` or `false`). Integers never coerce to booleans. |
| **Dangling Pointers & Memory Leaks** | **Stack-only memory model.** Dynamic heap allocation (`malloc`/`free`) is eliminated; variables live purely on the stack. |

---

## 2. Program Structure & Entry Point

Every C-- program is contained within a single file ending with the `.cmm` extension.

### A. The Module Declaration
Every program must begin with a single `module` header specifying the module's name:
```cmm
module my_program;
```
* The module name must be a valid C-- identifier (alphanumeric and underscores, starting with a letter or underscore).
* Exactly one module declaration is permitted per file, and it must precede all other constructs.

### B. The Entry Point: `fn main()`
Execution begins and ends within `fn main()`:
```cmm
module hello;

fn main() {
    print("Hello, world!");
}
```

### C. Structural Invariants
1. **No Code Outside `fn main()`**: Top-level statements, global variable declarations, or code outside the `fn main() { ... }` block are rejected with syntax error `S003`.
2. **Mandatory Semicolons**: Every statement in C-- must be terminated by a semicolon `;`.
3. **Mandatory Braces**: Bodies of functions and control-flow blocks must always be enclosed in curly braces `{ ... }`, even for single-line statements.

---

## 3. Type System & Literals

C-- is a **statically typed** language with four primitive types:

| Type | Size / Representation | Permitted Literals / Range | Description |
|:---:|:---:|:---|:---|
| **`int`** | 64-bit signed two's complement | `0`, `42`, `-10`, `9223372036854775807` | Range: $[-2^{63}, 2^{63}-1]$. Leading zeros are forbidden (e.g., `012` is rejected as `L008`). |
| **`float`** | 64-bit IEEE-754 double precision | `3.14`, `0.0`, `-0.5`, `1.5e10`, `1e-3` | Must contain either a fractional point `.` or exponent `e`/`E`. Digits required before and after `.`. |
| **`bool`** | 1-bit logical truth value | `true`, `false` | Strict boolean logic. Never coerced to or from integer `0` or `1`. |
| **`string`** | Immutable UTF-8 text sequence | `"Hello"`, `"Value: \n\t\"quote\""` | Enclosed in double quotes `"..."`. Supports standard escape sequences and arbitrary Unicode. |

### Escape Sequences in Strings
The following escape sequences are recognized:
* `\n`: Line feed (U+000A)
* `\t`: Horizontal tab (U+0009)
* `\r`: Carriage return (U+000D)
* `\"`: Double quote (U+0022)
* `\\`: Literal backslash (U+005C)

Any unrecognized escape sequence (such as `\x`, `\a`, or `\z`) triggers lexical error `L005`.

---

## 4. Variables, Bindings & Scoping

### A. Immutable Bindings (`let`)
Variables defined with `let` are **immutable constants**. Once assigned, their value can never be modified:
```cmm
let max_users = 100;
let greeting = "Welcome";

// max_users = 200; // Semantic error: cannot assign to immutable variable 'max_users'
```

### B. Mutable Variables (`mut`)
When a variable needs to be updated or reassigned (e.g., in loop counters or accumulators), declare it using `mut`:
```cmm
mut count = 0;
count += 1;
count = count * 2;
```

### C. Mandatory Initialization
Variables cannot be declared without an initial value. Uninitialized variable reads—a primary source of undefined behavior in C—are impossible in C--:
```cmm
// ILLEGAL:
// let x;
// mut y: int;

// LEGAL:
let x = 0;
mut y = 10.5;
```

### D. Block Scoping & Shadowing
C-- enforces strict lexical block scoping delimited by `{ ... }`:
* Variables declared inside an inner block are visible only within that block.
* **Variable Shadowing**: An inner block may declare a variable with the same name as an outer variable. The inner declaration shadows the outer one until the block terminates.
* **Self-Referential Shadowing**: Initializers are evaluated *before* the new binding is registered, allowing clean re-binding idioms:
```cmm
let x = 10;
{
    // Evaluates outer x (10) + 5, then binds inner x to 15:
    let x = x + 5;
    print(x); // Prints 15
}
print(x); // Prints 10 (outer binding restored)
```

---

## 5. Expressions & Operators

### A. Operator Precedence & Associativity
Operators follow standard C precedence rules (from highest to lowest):

| Precedence | Operator | Description | Associativity |
|:---:|:---:|:---|:---:|
| 1 (Highest) | `( )` | Grouping parentheses | N/A |
| 2 | `!`, `-` | Logical NOT, Unary negation | Right-to-left |
| 3 | `*`, `/`, `%` | Multiplication, Division, Modulo | Left-to-right |
| 4 | `+`, `-` | Addition, Subtraction | Left-to-right |
| 5 | `<`, `<=`, `>`, `>=` | Relational comparisons | Left-to-right |
| 6 | `==`, `!=` | Equality comparisons | Left-to-right |
| 7 | `&&` | Logical AND (short-circuiting) | Left-to-right |
| 8 (Lowest) | `\|\|` | Logical OR (short-circuiting) | Left-to-right |

### B. Mathematical Determinism: Truncating Division & Modulo
In C--, integer division `/` and modulo `%` **strictly truncate toward zero**, matching standard mathematical truncating integer arithmetic:
* `7 / 2 = 3`, `7 % 2 = 1`
* `-7 / 2 = -3`, `-7 % 2 = -1`
* `7 / -2 = -3`, `7 % -2 = 1`
* `-7 / -2 = 3`, `-7 % -2 = -1`
* The mathematical identity `(a / b) * b + (a % b) == a` holds universally for all non-zero divisors.

### C. Checked Arithmetic Traps
* **Integer Overflow (`R001`)**: If an integer addition, subtraction, or multiplication overflows the 64-bit signed boundary (e.g., `9223372036854775807 + 1`), the program immediately terminates with runtime error `R001`.
* **Division by Zero (`R002`)**: Dividing an integer or float by zero triggers runtime error `R002`.
* **Modulo by Zero (`R003`)**: Taking modulo by zero triggers runtime error `R003`.

### D. Implicit Widening (`int` $\rightarrow$ `float`)
When an arithmetic operator (`+`, `-`, `*`, `/`) operates on an `int` and a `float`, the `int` operand is automatically widened to `float`:
```cmm
let a = 10 + 2.5; // Evaluates to float 12.5
```
*(Note: Relational comparisons `<, <=, >, >=` also support mixed `int` and `float` comparison. However, assignment does not perform implicit conversion; a `float` cannot be assigned to an `int` variable).*

### E. Short-Circuiting Logic
Logical `&&` and `||` guarantee left-to-right short-circuit evaluation:
* In `A && B`, if `A` evaluates to `false`, `B` is never evaluated.
* In `A || B`, if `A` evaluates to `true`, `B` is never evaluated.

### F. Pure Assignment Statements
Assignments (`=`, `+=`, `-=`, `*=`, `/=`, `%=`) are **statements, not expressions**. They cannot be chained or used inside expressions:
```cmm
// ILLEGAL:
// let x = (y = 5);
// if (x = 10) { ... }

// LEGAL:
mut y = 0;
y = 5;
y += 10;
```

---

## 6. Control Flow Constructs

### A. Conditionals: `if`, `else if`, `else`
* Conditions must evaluate to a strict `bool`.
* Braces `{}` are mandatory.
```cmm
let score = 85;

if (score >= 90) {
    print("Grade: A");
} else if (score >= 80) {
    print("Grade: B");
} else {
    print("Grade: C");
}
```

### B. `while` Loop
Executes repeatedly while the condition evaluates to `true`:
```cmm
mut n = 5;
while (n > 0) {
    print(n);
    n -= 1;
}
```

### C. `do-while` Loop
Guaranteed to execute the loop body at least once before evaluating the condition:
```cmm
mut attempts = 0;
do {
    attempts += 1;
    print("Attempt made");
} while (attempts < 1);
```

### D. `for` Loop
Standard 3-part loop `for (init; cond; update)`:
* The `init` statement creates a dedicated scope private to the loop.
* The `cond` expression is evaluated before each iteration.
* The `update` statement is executed at the end of each iteration.
```cmm
for (mut i = 0; i < 5; i += 1) {
    print(i);
}
// i is not in scope here
```

---

## 7. Built-in Functions (I/O)

C-- provides the built-in `print(...)` function for standard output:
```cmm
print("Hello world!");
print(42);
print(3.14159);
print(true);
```

### Output Rules
1. **Newline Termination**: Every `print(...)` invocation appends a single `\n` line ending.
2. **Shortest Round-Trip Float Formatting (§9.1)**:
   * Floating-point numbers are printed in their shortest representation that rounds back to the exact same 64-bit IEEE-754 value.
   * Floating-point values with zero fractional part always include `.0` (e.g., `print(5.0);` outputs `5.0`, not `5`).
   * Extremely large or small floats use exponential notation (e.g., `1e-05` or `1e+20`).
3. **Booleans**: Output exactly as `true` or `false`.

---

## 8. Compiler Diagnostics & Error Rectification

C-- features human-friendly 3-line error diagnostics pointing to the exact file, line, column, and caret position (`^`).

### Diagnostic Format
```text
<file>:<line>:<col>: <category> error: <message>
    <source code line>
    <caret pointer line>
```

### Error Taxonomy Reference

#### 1. Lexical Errors (`L001` – `L012`, Exit Code `1`)
| Code | Reason | Example | How to Rectify |
|:---:|:---|:---|:---|
| **`L001`** | Invalid/unexpected character | `let @x = 10;` | Remove invalid symbol. |
| **`L002`** | Unterminated string literal | `let s = "hello;` | Close the string with `"`. |
| **`L004`** | Unterminated block comment | `/* comment` | Close comment with `*/`. |
| **`L005`** | Invalid string escape sequence | `"val: \x20"` | Use valid escape (`\n`, `\t`, `\r`, `\"`, `\\`). |
| **`L006`** | 64-bit integer literal overflow | `99999999999999999999` | Value must be $\le 2^{63}-1$. |
| **`L008`** | Leading zeros in integer literal | `let x = 05;` | Write `let x = 5;`. |
| **`L011`** | Unsupported `++` or `--` operator | `i++;` | Write `i += 1;` or `i -= 1;`. |
| **`L012`** | Unsupported bitwise `&` or `\|` | `a & b` | C-- uses logical `&&` and `\|\|`. |

#### 2. Syntax Errors (`S001` – `S004`, Exit Code `1`)
| Code | Reason | Example | How to Rectify |
|:---:|:---|:---|:---|
| **`S001`** | Unexpected token / syntax error | `let x = 5` (missing `;`) | Add terminating semicolon `;`. |
| **`S002`** | Unexpected end of file (EOF) | `fn main() {` (unclosed brace) | Add matching closing brace `}`. |
| **`S003`** | Top-level statement outside `main` | `let x = 10; fn main() {}` | Move variable inside `fn main()`. |
| **`S004`** | Excessive recursion depth (> 200) | 250 nested parentheses `((...))` | Simplify expression nesting. |

#### 3. Semantic Errors (`E001` – `E007`, Exit Code `1`)
| Code | Reason | Example | How to Rectify |
|:---:|:---|:---|:---|
| **`E001`** | Undeclared variable reference | `print(unknown);` | Declare variable with `let` or `mut` first. |
| **`E002`** | Re-declaration in same scope | `let a = 1; let a = 2;` | Use assignment or declare in inner scope. |
| **`E003`** | Type mismatch | `let a: int = "text";` | Ensure value matches declared/variable type. |
| **`E004`** | Non-boolean condition | `if (1) { ... }` | Use explicit boolean: `if (x != 0)`. |
| **`E005`** | Assignment to immutable `let` | `let x = 1; x = 2;` | Declare variable with `mut x = 1;`. |
| **`E007`** | Invalid operand types | `"text" - 5` | Use operators with compatible types. |

#### 4. Runtime Traps (`R001` – `R005`, Exit Code `2`)
| Code | Reason | Example Trigger |
|:---:|:---|:---|
| **`R001`** | 64-bit integer overflow trap | `9223372036854775807 + 1` |
| **`R002`** | Division by zero | `100 / 0` |
| **`R003`** | Modulo by zero | `100 % 0` |
| **`R004`** | Float overflow to infinity | Float multiplication exceeding IEEE-754 range |
| **`R005`** | Step execution limit exceeded | Exceeding `--max-steps N` during `cmm run` |

---

## 9. Execution Modes: Interpreter vs C99 Transpiler

C-- offers two independent execution pipelines:

### A. Reference Tree-Walking Interpreter
Designed for instant development feedback without a C toolchain:
```bash
# Type-check without running
cmm check program.cmm

# Execute immediately
cmm run program.cmm

# Execute with step limit to prevent infinite loops (R005)
cmm run program.cmm --max-steps 10000
```

### B. High-Performance C99 Transpiler
Translates C-- into clean, standard ISO C99 code that compiles cleanly with zero warnings:
```bash
# 1. Transpile C-- to ISO C99
cmm transpile program.cmm -o program.c

# 2. Compile natively with GCC or Clang (warning-free guarantee)
cc -std=c99 -Wall -Werror -pedantic program.c -o program

# 3. Run native binary
./program
```

#### Transpiler Guarantees:
* **Zero Heap Allocations**: Never emits `malloc`, `calloc`, or `free`. Variables reside entirely on the native execution stack.
* **Checked Arithmetic Lowering**: Math operations lower to checked static inline functions (`cmm_add`, `cmm_sub`, `cmm_mul`, `cmm_div`, etc.) that trap on 64-bit overflow and division-by-zero, mirroring interpreter behavior exactly.
* **String Safety**: Emits byte-escaped hexadecimal string literals (`\xNN`), preventing format-string injection and literal breakouts.

---

## 10. Idiomatic Code Recipes

### Recipe 1: Fibonacci Sequence
```cmm
module fibonacci;

fn main() {
    let count = 10;
    mut a = 0;
    mut b = 1;

    print("Fibonacci series:");
    for (mut i = 0; i < count; i += 1) {
        print(a);
        let next = a + b;
        a = b;
        b = next;
    }
}
```

### Recipe 2: Primality Check
```cmm
module prime_check;

fn main() {
    let n = 29;
    mut is_prime = true;

    if (n <= 1) {
        is_prime = false;
    } else {
        mut d = 2;
        while (d * d <= n) {
            if (n % d == 0) {
                is_prime = false;
            }
            d += 1;
        }
    }

    if (is_prime) {
        print("Prime");
    } else {
        print("Not prime");
    }
}
```

### Recipe 3: Safe Compound Calculations
```cmm
module banking;

fn main() {
    let principal = 1000.0;
    let rate = 0.05;
    let years = 5;

    mut balance = principal;
    for (mut y = 1; y <= years; y += 1) {
        balance += balance * rate;
    }

    print("Final balance after 5 years:");
    print(balance);
}
```
