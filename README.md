<div align="center">

<img src="assets/logo.png" width="180" alt="C-- Language Logo" />

# C-- (C Minus Minus)

**A high-assurance, statically checked imperative programming language designed on the principle of *"Safety by Removal"* — version 0.2.0.**

[![CI Matrix](https://github.com/ronitmexson2924/C--/actions/workflows/ci.yml/badge.svg)](https://github.com/ronitmexson2924/C--/actions)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-Railway%20Cloud-success.svg)](https://web-production-c8ddc.up.railway.app)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Zero Runtime Dependencies](https://img.shields.io/badge/dependencies-0%20external-brightgreen.svg)](#prerequisites)
[![Security Audited](https://img.shields.io/badge/security-audited%20%26%20hardened-success.svg)](#8-security-audit--zero-vulnerability-guarantee)
[![Platforms](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux%20%7C%20Docker-lightgrey.svg)](#3-installation-guide)

[What is C--?](#1-what-is-c) •
[Core Features](#2-core-language-features) •
[Web Playground](#3-web-playground--interactive-compiler-studio) •
[Installation Guide](#4-installation-guide) •
[Quickstart & Showcase](#5-quickstart--showcase-demo) •
[CLI Reference](#6-command-line-interface-cli) •
[Error Guidance](#7-compiler-diagnostics--beginner-friendly-fix-guidance) •
[C99 Backend](#8-c99-transpiler-backend) •
[Security & Hardening](#9-security-audit--zero-vulnerability-guarantee) •
[Testing](#10-testing--quality-assurance) •
[File Icons & IDE](#11-file-icons--ide-integration-cmm-association)

---

</div>

## 1. What is C--?

**C--** is a modern, statically typed, imperative programming language designed to eliminate the notorious memory corruption and undefined behavior pitfalls of C/C++. Rather than patching over vulnerabilities with complex runtime sanitizers or garbage collectors, C-- enforces safety through **"Safety by Removal"**:

- 🛡️ **Zero Null Pointers**: Null pointers do not exist. Pointer dereference crashes (`SIGSEGV`) are impossible.
- 🛡️ **Zero Pointer Arithmetic**: Memory cannot be corrupted or indexed out of bounds.
- 🔒 **Immutable by Default**: Variables declared with `let` cannot be reassigned; mutability requires an explicit `mut`.
- ⚡ **Mandatory Initialization**: Every variable must have an initializer at declaration; uninitialized reads are impossible.
- 🎯 **Mathematical Determinism**: Truncating integer division toward zero, checked 64-bit integer overflows, and IEEE-754 double precision float arithmetic with zero-division traps.
- 💡 **Beginner-Friendly Diagnostics**: Plain-language explanations without compiler jargon, actionable fixes with concrete code samples, and "did you mean" typo suggestions.
- 🚀 **Dual Execution Modes**: Instant execution via the built-in reference tree-walk interpreter, or compilation to ultra-fast, warning-free ISO C99 code for native compilation with GCC, Clang, or MSVC.
- 📦 **Zero External Runtime Dependencies**: Standard library only; completely portable across macOS, Windows, Linux, and Docker.

---

## 2. Core Language Features

| Category | Syntax & Constructs | Specification Details |
|:---|:---|:---|
| **Structure** | `module <name>;`<br>`fn main() { ... }` | Single-file modules with an explicit `main` entry point. Functions defined at module scope. |
| **Functions** | `fn name(a: int) -> int { ... }` | First-class functions, typed parameters, explicit return types, void functions, recursion stack depth safeguards (1000). |
| **Data Types** | `int`, `float`, `bool`, `string` | **`int`**: 64-bit signed two's complement.<br>**`float`**: 64-bit IEEE-754 double precision.<br>**`bool`**: Strict boolean (`true`, `false`).<br>**`string`**: UTF-8 immutable text with indexing and `.len()`. |
| **Collections** | `array<T>(size, fill)`<br>`list<T>()`<br>`stack<T>()`<br>`queue<T>()` | Fixed-size arrays, dynamic lists, LIFO stacks, FIFO queues. Deep-copy value semantics on assignment and parameter passing. |
| **Variables** | `let x = <expr>;`<br>`mut y = <expr>;` | `let` declares an immutable binding.<br>`mut` declares a mutable variable allowed to receive reassignment. |
| **Assignments** | `=`, `+=`, `-=`, `*=`, `/=`, `%=` | Pure statements. Compound operators perform checked arithmetic matching the operator rules. |
| **Scoping** | Lexical blocks `{ ... }` | Block scoping with support for inner-scope shadowing. Initializers evaluated before binding. |
| **Control Flow** | `if`, `else if`, `else`<br>`switch (val) { case ...: ... default: ... }` | Mandatory braces `{}`; conditions must evaluate to `bool`. Multi-branch `switch` with exact type checking and duplicate protection. |
| **Loops** | `while`, `do-while`, `for` | `while` loops, `do-while` loops (guaranteed to execute at least once), and `for (init; cond; update)`. |
| **Operators** | `!`, `-`<br>`*`, `/`, `%`<br>`+`, `-`<br `<`, `>`, `<=`, `>=`<br>`==`, `!=`<br>`&&`, `\|\|` | Standard C precedence; truncating division toward zero; short-circuiting `&&` and `\|\|`; automatic `int` $\rightarrow$ `float` widening. |
| **I/O & Stdlib** | `print(<expr>);`<br>`read_line()`<br>`parse_int(s)`, `parse_float(s)` | Built-in output statement, interactive stdin console reading, and robust numeric parsing helpers. |

---

## 3. Web Playground & Interactive Compiler Studio

C-- includes a zero-dependency web playground and interactive compiler explorer (`web/server.py`). Users can test language features, write code, inspect AST/tokens, run code in the reference interpreter, and transpile C-- directly into ISO C99 code through a split-screen browser interface with a top navigation bar.

### Live Online Playground
Try C-- directly in your browser without local installation:  
🌐 **[Open Live Web Studio (Hosted on Railway)](https://web-production-c8ddc.up.railway.app)**

### Launching Locally
```bash
python3 web/server.py
```
Open **`http://localhost:8000`** in any web browser.

### Key Capabilities of the Web Studio
- **Top Navigation Bar:** Tabs for **Playground & Transpiler**, **Overview**, **Key Features**, **Compiler Pipeline**, and **Syntax Cheatsheet**.
- **Split-Screen Studio:** Line-numbered code editor on the left; real-time execution output console & C99 transpiled code viewer on the right.
- **One-Click Transpilation:** Click **"⚙ Transpile to C"** to transpose the active C-- code into hardened ISO C99.
- **Preset Library:** 7 preloaded examples covering recursion, lists, stacks/queues, value semantics, switch-case, C99 transpilation, and typo diagnostics.
- **Academic PDF Report:** Download or view the comprehensive academic report right from the top header bar.

---

## 4. Installation Guide

C-- runs natively on **macOS**, **Linux**, and **Windows**. It requires **Python 3.10 or newer** and has **zero third-party runtime dependencies**.

### Prerequisites Check

Verify your installed Python version:

```bash
# macOS / Linux
python3 --version

# Windows (PowerShell or Command Prompt)
py --version
# or
python --version
```
*(Ensure the output displays Python 3.10.0 or higher.)*

---

### Method 1: Standard Installation (Recommended)

Installing C-- into a dedicated virtual environment ensures a clean environment and avoids system-managed environment restrictions (PEP 668):

#### macOS / Linux
```bash
# 1. Clone the repository
git clone https://github.com/ronitmexson2924/C--.git
cd C--

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install C-- in editable development mode
pip install -e .
```

#### Windows (PowerShell)
```powershell
# 1. Clone the repository
git clone https://github.com/ronitmexson2924/C--.git
cd C--

# 2. Create and activate a virtual environment
py -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install C-- in editable development mode
pip install -e .
```

#### Windows (Command Prompt `cmd.exe`)
```cmd
REM 1. Clone the repository
git clone https://github.com/ronitmexson2924/C--.git
cd C--

REM 2. Create and activate a virtual environment
py -m venv .venv
.\.venv\Scripts\activate.bat

REM 3. Install C-- in editable development mode
pip install -e .
```

*Tip: To include testing tools (e.g. pytest), install with the dev extra:*
```bash
pip install -e ".[dev]"
```

---

### Method 2: Zero-Installation Mode (Run Directly)

If you prefer not to install C-- or want to run it immediately without modifying your Python environment:

```bash
# macOS / Linux
python3 -m cmm --version
python3 -m cmm run examples/hello.cmm

# Windows (PowerShell / cmd)
py -m cmm --version
py -m cmm run examples/hello.cmm
```

---

### Method 3: Docker Container

Run C-- inside an isolated Docker container without installing Python on your host machine:

```bash
# 1. Build the lightweight Docker image
docker build -t cmm-lang .

# 2. Run any C-- program mounted from the current directory
docker run --rm -v "$PWD":/work -w /work cmm-lang run examples/hello.cmm

# 3. Run type checking inside Docker
docker run --rm -v "$PWD":/work -w /work cmm-lang check demo.cmm
```

---

### Method 4: Standalone Executable (Single Binary)

Build a self-contained, standalone single-file binary that runs without requiring Python to be installed on target machines:

```bash
# Install PyInstaller (build-time only)
pip install pyinstaller

# Run the build script
python scripts/build_executable.py
```
The compiled binary will be placed in `dist/cmm` (or `dist/cmm.exe` on Windows).

---

### Verifying Your Installation

Confirm that the `cmm` CLI command is accessible:

```bash
cmm --version
```
Expected output:
```text
cmm 0.1.0
```

Run the built-in `hello.cmm` sample:
```bash
cmm run examples/hello.cmm
```
Expected output:
```text
Hello, world!
```

---

## 5. Quickstart & Showcase Demo

### Running the Interactive Language Showcase
The repository includes a comprehensive demonstration program [`demo.cmm`](./demo.cmm) that exercises all 10 language feature areas (types, immutability, mutability, expressions, mixed arithmetic, short-circuit logic, scoping, shadowing, conditionals, and all 3 loop forms):

```bash
cmm run demo.cmm
```

### Writing Your First C-- Program

Create a file named `counter.cmm`:
```cmm
module counter;

fn main() {
    let greeting = "Counting in C--:";
    print(greeting);

    mut i = 1;
    while (i <= 5) {
        print(i);
        i += 1;
    }
}
```

Check the file for syntax or semantic errors:
```bash
cmm check counter.cmm
```
Output:
```text
counter.cmm: OK
```

Execute the program:
```bash
cmm run counter.cmm
```
Output:
```text
Counting in C--:
1
2
3
4
5
```

---

## 6. Command-Line Interface (CLI)

The `cmm` CLI follows standard UNIX conventions and guarantees platform-independent UTF-8 output with `\n` line endings.

```bash
cmm <command> [options] <file>
```

### Command Reference

| Command | Description | Exit Codes |
|:---|:---|:---|
| `cmm run <file> [--max-steps N] [--no-help]` | Lex, parse, type-check, and execute the program. The `--max-steps N` option bounds loop execution (R005). Use `--no-help` to suppress extended help blocks. | `0` (Success)<br>`1` (Static error)<br>`2` (Runtime error)<br>`3` (I/O error) |
| `cmm check <file> [--no-help]` | Statically type-check a program without running it. Prints `<file>: OK` on success. | `0` (Valid)<br>`1` (Static error)<br>`3` (I/O error) |
| `cmm tokens <file> [--no-help]` | Lex the source and print the stream of tokens with line:column coordinates. | `0` (Success)<br>`1` (Lexical error)<br>`3` (I/O error) |
| `cmm ast <file> [--no-help]` | Parse the source and print the indented Abstract Syntax Tree (AST). | `0` (Success)<br>`1` (Syntax error)<br>`3` (I/O error) |
| `cmm transpile <file> -o <out.c> [--no-help]` | Transpile C-- source code into clean, standard ISO C99 code. | `0` (Success)<br>`1` (Static error)<br>`3` (I/O error) |
| `cmm --version` | Print compiler version string (`cmm 0.2.0`). | `0` |
| `cmm --help` / `cmm -h` | Print detailed usage documentation. | `0` |

### CLI Exit Codes

- **`0`**: Success.
- **`1`**: Static failure (lexical error L001–L012, syntax error S001–S004, semantic error E001–E031).
- **`2`**: Runtime trap (arithmetic overflow R001, divide by zero R002, mod by zero R003, float overflow R004, step limit exceeded R005, index out of bounds R006, call depth exceeded R007, collection limits R013–R014).
- **`3`**: File I/O error (file not found, permission denied, invalid UTF-8, directory passed as file).
- **`4`**: Command-line usage error (invalid flag or missing arguments).
- **`70`**: Internal compiler bug (traceback suppressed unless `CMM_DEBUG=1`).

---

## 7. Compiler Diagnostics & Beginner-Friendly Fix Guidance

C-- features human-friendly compiler diagnostics designed for beginners. Diagnostics follow a clear layout with line-numbered source gutters, token underlines, plain-language explanations, actionable fixes with code examples, and "did you mean" suggestions:

```text
<path>:<line>:<col>: <kind> error: <message>
   |
<line> | <source line>
   |    ^^^^^
what went wrong:
  <plain-language explanation without compiler jargon>
how to fix:
  <concrete actionable fix>
      <sample corrected code>
  did you mean '<suggestion>'?
```

For advanced users or tooling, passing `--no-help` restores the concise 3-line format. See [`docs/errors.md`](./docs/errors.md) for the complete reference catalog of all 60 diagnostic codes.

### Common Diagnostic Examples & Rectification

#### 1. Mutating an Immutable Variable (`let`)
```text
demo.cmm:4:5: semantic error: cannot assign to immutable variable 'x' (declared with 'let' at line 3, column 9); declare it with 'mut' to allow assignment
  |
4 |     x = 10;
  |     ^
what went wrong:
  The variable 'x' was created with 'let', which means its value cannot be
  changed.
how to fix:
  Change 'let' to 'mut' where 'x' is created if you need to assign to it.
      mut x = 0;
```
> **How to Rectify**: Change the declaration from `let x = ...;` to `mut x = ...;`.

#### 2. Unsupported Operator (C++ / Java Muscle Memory)
```text
loop.cmm:5:6: lexical error: '++' is not supported; use '+= 1'
    i++;
     ^
```
> **How to Rectify**: Replace `i++` with `i += 1` (or `i--` with `i -= 1`).

#### 3. Missing Semicolon or Syntax Mistake
```text
calc.cmm:5:5: syntax error: expected ';', found 'print'
    print(result);
    ^
```
> **How to Rectify**: Add a terminating `;` at the end of the previous statement.

#### 4. Type Mismatch in Assignment
```text
types.cmm:6:5: semantic error: cannot assign value of type string to variable 'total' of type int
    total = "100";
    ^
```
> **How to Rectify**: Assign an expression of the matching type (`total = 100;`).

#### 5. Runtime Integer Overflow Trap
```text
overflow.cmm:4:16: runtime error: 64-bit signed integer overflow
    let max = 9223372036854775807 + 1;
               ^
```
> **How to Rectify**: Ensure values remain within the 64-bit signed range ($-2^{63} \le n \le 2^{63}-1$), or use `float` for larger magnitudes.

---

## 8. C99 Transpiler Backend

C-- includes an optimizing C99 transpiler (`cmm transpile <file> -o <out.c>`) conforming strictly to the ISO C99 standard.

### Transpiler Properties
- **ISO C99 Conforming**: Emits standard C code using only standard headers (`<stdint.h>`, `<stdio.h>`, `<stdlib.h>`, `<string.h>`, `<stdbool.h>`, `<float.h>`, `<inttypes.h>`). No non-standard extensions or compiler-specific builtins (`__builtin_*`) are used.
- **Checked Arithmetic**: Lowers operations to inline `static` helper functions (`cmm_add`, `cmm_sub`, `cmm_mul`, `cmm_div`, etc.) performing mathematical overflow and division-by-zero checks.
- **Shortest Round-Trip Float Printing**: Emits a custom C99 floating-point formatter matching the specification (§9.1) byte-for-byte.
- **Warning-Free Compilation**: Emits clean C that compiles with `-Wall -Werror -pedantic` without warnings.
- **Stack-Only Memory**: No heap allocation (`malloc`/`free`). Zero risk of memory leaks or use-after-free bugs.

### Transpiling and Compiling Natively

#### macOS / Linux (GCC or Clang)
```bash
# 1. Transpile to C99
cmm transpile demo.cmm -o demo.c

# 2. Compile natively with maximum warnings enabled
cc -std=c99 -Wall -Werror demo.c -o demo

# 3. Execute native binary
./demo
```

#### Windows (GCC via MinGW / MSYS2 or MSVC)
```powershell
# MinGW / GCC
cmm transpile demo.cmm -o demo.c
gcc -std=c99 -Wall -Werror demo.c -o demo.exe
.\demo.exe

# MSVC (Visual Studio Developer Command Prompt)
cmm transpile demo.cmm -o demo.c
cl /std:c99 /W4 /WX demo.c /Fe:demo.exe
.\demo.exe
```

---

## 9. Security Audit & Zero-Vulnerability Guarantee

The C-- compiler, interpreter, and code generator have undergone a comprehensive security audit to ensure safety when processing untrusted code and running in public environments:

| Threat / CWE Class | Risk Description | C-- Defense & Implementation |
|:---|:---|:---|
| **CWE-94 / CWE-95**<br>Code Injection | Executing untrusted code via `eval()` or `exec()` | **Hardened**: Neither `eval()`, `exec()`, `compile()`, `pickle`, nor `ctypes` are used anywhere in the codebase. Parsing and interpretation are 100% AST-based. |
| **CWE-78**<br>OS Command Injection | Executing shell commands via untrusted input | **Zero Shell Invocation**: The compiler core never invokes `os.system()`, `os.popen()`, or shell processes. CLI and tests use explicit argument lists without `shell=True`. |
| **CWE-119 / CWE-120**<br>Buffer Overflow | Corrupting memory through out-of-bounds access | **Eliminated by Design**: C-- contains no pointers, no pointer arithmetic, and no manual memory management. Stack memory only in transpiled C. |
| **CWE-476**<br>NULL Pointer Dereference | Application crash / exploit via null access | **Eliminated by Design**: Null pointers do not exist in the C-- grammar or type system. |
| **CWE-416 / CWE-401**<br>Use-After-Free / Leaks | Dangling pointers or memory exhaustion | **Eliminated by Design**: Dynamic heap allocation (`malloc`/`free`) is forbidden. Variables reside entirely on the execution stack. |
| **CWE-190**<br>Integer Overflow | Integer wrapping leading to security bypasses | **Trapped**: Every integer operation is checked against $[-2^{63}, 2^{63}-1]$. Overflow immediately traps with `R001` (exit code 2). |
| **CWE-369**<br>Divide by Zero | Denial of service / crash via arithmetic exception | **Trapped**: Division and modulo divisors are checked before evaluation. Zero traps immediately with `R002` / `R003` (exit code 2). |
| **CWE-400**<br>Uncontrolled Resource Consumption | Call-stack exhaustion via deeply nested code | **Guarded**: Recursive-descent parser enforces a hard recursion depth limit of 200 (S004). Interpreter supports bounded loop iterations via `--max-steps N`. |
| **CWE-22**<br>Path Traversal & Safe I/O | Reading files outside authorized paths | **Safe I/O**: Files are read with strict UTF-8 decoding, explicit OS exception handling, and normalized line endings. No arbitrary file writes. |
| **CWE-116**<br>Improper Output Neutralization | C code injection via string literals in transpiler | **Byte Escaping**: String literals emitted to C are byte-escaped (`\xNN`), preventing string breakout or format specifier exploits. |

---

## 10. Testing & Quality Assurance

The codebase includes an exhaustive test suite of **416 tests** validating lexical analysis, parsing, semantic analysis, float formatting, interpretation, CLI behaviors, example programs, v0.2 language features, beginner-friendly error diagnostics, and C99 code generation:

```bash
# Run the complete test suite
pytest -v
```

### Test Suite Structure

- [`tests/test_lexer.py`](./tests/test_lexer.py): 40 tests covering all tokens, keywords, operators, and lexical errors (L001–L012).
- [`tests/test_parser.py`](./tests/test_parser.py): 46 tests covering grammar rules, operator precedence, associativity, S001–S004, and AST printing.
- [`tests/test_analyzer.py`](./tests/test_analyzer.py): 42 tests covering scope stacks, immutable binding, cascade suppression, and E001–E007.
- [`tests/test_v02.py`](./tests/test_v02.py): 48 tests covering functions, collections (arrays, lists, stacks, queues), switch statements, and stdlib I/O.
- [`tests/test_formatting.py`](./tests/test_formatting.py): 26 tests covering shortest round-trip float representations (§9.1).
- [`tests/test_interpreter.py`](./tests/test_interpreter.py): 51 tests covering truncating arithmetic, 64-bit limits, short-circuiting, and R001–R014.
- [`tests/test_cli.py`](./tests/test_cli.py): 39 tests covering CLI commands, exit codes (0/1/2/3/4/70), I/O handling, and debug traces.
- [`tests/test_examples.py`](./tests/test_examples.py): 30 tests covering all normative examples with byte-exact stdout/stderr matching, plus CRLF and UTF-8 BOM parity.
- [`tests/test_codegen_c.py`](./tests/test_codegen_c.py): 16 tests covering C99 code generation, native GCC/Clang compilation, and execution parity.
- [`tests/test_error_help.py`](./tests/test_error_help.py): 78 tests covering plain-language jargon scanner, Damerau-Levenshtein suggestions, renderer edge cases, and 59 golden error programs in [`tests/errors/`](./tests/errors/).

**Status: 416 passed in 8.4s.**

---

## 11. File Icons & IDE Integration (.cmm Association)

<div align="center">
<img src="assets/logo.png" width="120" alt="C-- 3D Logo" />
</div>

C-- includes complete visual branding and system file icon associations so that whenever a `.cmm` file is saved or viewed in your file manager or code editor, it automatically displays the official **3D blue C-- hexagonal logo**.

### A. macOS Finder Integration

C-- provides seamless integration with macOS LaunchServices and Finder:

1. **System-wide File Association**:
   Run the setup script once to register the C-- Application bundle (`C--.app`) and `.icns` file icon with macOS LaunchServices:
   ```bash
   ./scripts/install_macos_association.sh
   ```
   After registration, macOS automatically associates all `*.cmm` files system-wide with the C-- 3D logo icon.

2. **Stamp Icon on Any File or Directory**:
   To manually stamp the C-- logo onto an existing `.cmm` file or recursively across a folder:
   ```bash
   # Stamp a single file
   python scripts/set_cmm_icon.py path/to/file.cmm

   # Stamp all .cmm files in the current workspace
   python scripts/set_cmm_icon.py .
   ```

3. **Automatic On-Save Watcher**:
   Keep the background watcher running to automatically stamp the C-- logo onto any `.cmm` file the moment you save it:
   ```bash
   python scripts/watch_cmm_icons.py .
   ```

---

### B. VS Code & Antigravity IDE Extension

A dedicated language and icon extension is located in [`extensions/cmm-lang/`](./extensions/cmm-lang):

- **Custom File Icon**: Shows the 3D C-- logo next to every `.cmm` file in the file explorer and tab bar.
- **Syntax Highlighting**: Comprehensive TextMate grammar highlighting keywords (`let`, `mut`, `fn`, `module`, `print`), types (`int`, `float`, `bool`, `string`), numbers, strings, and comments.
- **Automatic Stamp on Save**: Hooks into `onDidSaveTextDocument` to immediately update the file's Finder icon whenever `Cmd+S` (Save) is pressed.

To install into your local editor:
```bash
# Antigravity IDE
cp -r extensions/cmm-lang ~/.antigravity-ide/extensions/ronitmexson.cmm-lang-0.1.0/

# VS Code
cp -r extensions/cmm-lang ~/.vscode/extensions/ronitmexson.cmm-lang-0.1.0/
```

---

### C. Windows Explorer Association

Register `.cmm` files to display the high-resolution `assets/cmm.ico` icon in Windows Explorer:
1. Double-click or import [`assets/register_cmm_windows.reg`](./assets/register_cmm_windows.reg).
2. Windows Explorer will immediately associate `.cmm` files with the C-- icon and register `cmm run` as the default execution command.

---

### D. Linux FreeDesktop MIME Type

Install the C-- MIME type and icon for GNOME/KDE file managers:
```bash
mkdir -p ~/.local/share/mime/packages
cp assets/cmm.xml ~/.local/share/mime/packages/
update-mime-database ~/.local/share/mime
```

---

## 12. Repository Architecture & Layout

```text
compiler-mini-project/
├── assets/                      # Visual branding and platform icon assets
│   ├── logo.png                 # Official 3D C-- logo (1024x1007)
│   ├── cmm.icns                 # Native macOS multi-resolution icon bundle
│   ├── cmm.ico                  # Native Windows multi-resolution icon
│   ├── cmm-icon.png             # IDE file explorer icon (128x128)
│   ├── register_cmm_windows.reg # Windows Explorer file association
│   └── cmm.xml                  # Linux FreeDesktop MIME specification
├── cmm/                         # Core compiler & interpreter implementation
│   ├── __init__.py              # Package metadata (__version__ = "0.1.0")
│   ├── __main__.py              # CLI entry point (python -m cmm)
│   ├── tokens.py                # Token definitions & TokenKind enum
│   ├── errors.py                # Error hierarchy & 3-line diagnostic formatting
│   ├── lexer.py                 # UTF-8 normalizer & tokenizer
│   ├── ast_nodes.py             # Strongly-typed AST node definitions
│   ├── parser.py                # Recursive-descent parser (EBNF & precedence)
│   ├── types.py                 # Type enum & operator typing tables
│   ├── analyzer.py              # Scope analysis & type-checking engine
│   ├── formatting.py            # §9.1 float and value formatter
│   ├── interpreter.py           # Tree-walking runtime interpreter
│   ├── astprint.py              # AST & token debug printers
│   ├── cli.py                   # Command-line driver & argument parser
│   └── codegen_c.py             # Section 16 C99 backend generator
├── docs/
│   └── SPEC.md                  # Normative language specification (immutable)
├── examples/                    # Runnable sample programs
│   ├── hello.cmm                # Hello World
│   ├── factorial.cmm            # Factorial calculation
│   ├── fibonacci.cmm            # Fibonacci numbers
│   ├── prime_check.cmm          # Primality testing
│   ├── loops.cmm                # while, do-while, for loops
│   ├── scoping.cmm              # Lexical scoping and shadowing
│   ├── boundaries.cmm           # 64-bit integer limits
│   ├── floats.cmm               # Float formatting & edge cases
│   └── errors/                  # Negative test cases (.cmm, .err, .code)
├── demo.cmm                     # Full 10-feature language showcase program
├── extensions/                  # IDE extensions
│   └── cmm-lang/                # VS Code & Antigravity IDE language & icon extension
├── scripts/                     # Tooling & packaging scripts
│   ├── entry.py                 # PyInstaller entry wrapper
│   ├── build_executable.py      # Standalone binary builder
│   ├── set_cmm_icon.py          # File icon stamper utility
│   ├── watch_cmm_icons.py       # Background on-save icon watcher
│   └── install_macos_association.sh # macOS LaunchServices installer
├── tests/                       # Complete pytest test suite (290 tests)
├── .github/workflows/ci.yml     # Multi-platform CI pipeline (Ubuntu, Windows, macOS)
├── Dockerfile                   # Docker container specification
├── pyproject.toml               # Build configuration (PEP 517/518)
├── LICENSE                      # MIT License
└── README.md                    # Project documentation
```

---

## 13. Specification & Documentation

- 📘 **[Language Guide & Programmer's Manual](docs/LANGUAGE_GUIDE.md)**: Practical reference guide covering syntax, operators, control flow, diagnostics, and idiomatic code recipes.
- 📜 **[Normative Specification (SPEC.md)](docs/SPEC.md)**: The authoritative, character-exact specification of the C-- language grammar, semantics, and reference requirements.

---

## 14. License

This project is open-source software licensed under the **[MIT License](LICENSE)**.
