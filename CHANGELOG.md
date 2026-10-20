# Changelog
All notable changes to the C-- programming language and compiler are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-10-20

### Added
- **Beginner-Friendly Error Explanations & Fix Guidance**:
  - Unified diagnostic renderer with line-numbered source gutters, token underlines, and caret alignment.
  - Plain-language explanations ("what went wrong") free from compiler jargon across all 60 active diagnostic codes.
  - Concrete, actionable guidance ("how to fix") with sample code patterns and values.
  - Typo and fuzzy identifier suggestions ("did you mean '...'?") powered by a deterministic Damerau-Levenshtein distance algorithm.
  - Automatic 76-column word wrapping with 6-space indented code samples.
  - `--no-help` CLI flag to suppress extended help blocks and restore the concise 3-line format.
  - Automated diagnostic reference documentation generated at `docs/errors.md`.
  - Comprehensive test suite in `tests/test_error_help.py` and 59 golden error tests in `tests/errors/`.

- **C-- v0.2 Language Features**:
  - Functions: First-class named functions, typed parameters, explicit return types (`fn name(a: int) -> int { ... }`), and recursion limit safeguards.
  - Collections: Fixed-size arrays (`array<T>(size, fill)`), dynamic lists (`list<T>()`), LIFO stacks (`stack<T>()`), FIFO queues (`queue<T>()`).
  - Standard Library I/O: Interactive console input (`read_line()`), numeric parsing (`parse_int()`, `parse_float()`).
  - Control Flow: Multi-branch `switch` statement with exact type matching and exhaustiveness checks.
  - String Slicing: Native indexing into string literals.
  - String Operations: `len()` method on strings.
  - Deep-copy value semantics on variable assignment and parameter passing for all collections.

### Changed
- CLI default diagnostic output upgraded to friendly gutter format with extended explanations.
- Standardized error details dictionary across lexer, parser, analyzer, and interpreter.

## [0.1.0] - 2026-10-19

### Added
- Initial specification and reference implementation for C-- v0.1.0.
- Lexer, recursive-descent parser, semantic analyzer, and tree-walking interpreter.
- ANSI C99 transpilation pipeline via `cmm transpile`.
- Standard arithmetic, comparisons, logical expressions, and variable bindings (`let` vs `mut`).
- While loops, do-while loops, for loops, if-else conditionals.
- Comprehensive golden test suite and CLI test coverage.
