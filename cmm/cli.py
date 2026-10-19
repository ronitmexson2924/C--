"""Command-line interface (CLI) for C--."""

import argparse
import io
import os
from pathlib import Path
import sys
import traceback
from typing import Optional

from cmm import __version__
from cmm.analyzer import analyze
from cmm.astprint import format_ast, format_tokens
from cmm.codegen_c import generate_c
from cmm.errors import CmmError, CmmRuntimeError, LexError, ParseError, format_error
from cmm.interpreter import Interpreter
from cmm.lexer import normalize_source, tokenize
from cmm.parser import parse


class UsageError(Exception):
    """Raised when command-line invocation is invalid (§11.5)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class CmmArgumentParser(argparse.ArgumentParser):
    """Custom argument parser implementing §11 command-line interface."""

    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("prog", "cmm")
        super().__init__(*args, **kwargs)

    def error(self, message: str) -> None:
        """Override argparse default error method to print usage and exit code 4."""
        self.print_usage(sys.stderr)
        sys.stderr.write(f"cmm: error: {message}\n")
        raise UsageError(message)

    def exit(self, status: int = 0, message: Optional[str] = None) -> None:
        """Override exit to raise SystemExit so caller can intercept."""
        if message:
            sys.stderr.write(message)
        raise SystemExit(status)


class _IoError(Exception):
    """Internal exception for I/O reading failures (§11.4)."""

    def __init__(self, path: str, reason: str) -> None:
        super().__init__(f"{path}: {reason}")
        self.path = path
        self.reason = reason


def _configure_runtime() -> None:
    """Configure stream encoding and recursion limit per §11.3, §13.5, and §13.8."""
    if sys.getrecursionlimit() < 10000:
        sys.setrecursionlimit(10000)

    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="strict", newline="\n")
        elif hasattr(sys.stdout, "buffer"):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="strict", newline="\n")
    except Exception:
        pass

    try:
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="strict", newline="\n")
        elif hasattr(sys.stderr, "buffer"):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="strict", newline="\n")
    except Exception:
        pass


def _read_source_file(path_str: str) -> tuple[str, list[str]]:
    """Read bytes, strictly decode as UTF-8, and normalize line endings.

    Raises:
        _IoError: with exact reason string per §11.4.
    """
    p = Path(path_str)
    if p.is_dir():
        raise _IoError(path_str, "is a directory")

    try:
        raw_bytes = p.read_bytes()
    except FileNotFoundError:
        raise _IoError(path_str, "file not found")
    except PermissionError:
        raise _IoError(path_str, "permission denied")
    except IsADirectoryError:
        raise _IoError(path_str, "is a directory")
    except OSError as e:
        raise _IoError(path_str, e.strerror or str(e))

    try:
        raw_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise _IoError(path_str, "not valid UTF-8")

    normalized = normalize_source(raw_text)
    source_lines = normalized.splitlines(keepends=True)
    return normalized, source_lines


def _run_pipeline(path_str: str, max_steps: Optional[int] = None) -> int:
    """Execute pipeline for 'run' command: lex, parse, analyze, execute."""
    normalized, source_lines = _read_source_file(path_str)

    # 1. Lex
    try:
        tokens = tokenize(normalized)
    except LexError as e:
        sys.stdout.flush()
        sys.stderr.write(format_error(e, path_str, source_lines))
        return 1

    # 2. Parse
    try:
        ast = parse(tokens)
    except ParseError as e:
        sys.stdout.flush()
        sys.stderr.write(format_error(e, path_str, source_lines))
        return 1

    # 3. Analyze
    sem_errors = analyze(ast)
    if sem_errors:
        sem_errors.sort(key=lambda err: (err.line, err.col))
        sys.stdout.flush()
        for err in sem_errors:
            sys.stderr.write(format_error(err, path_str, source_lines))
        return 1

    # 4. Interpret
    interp = Interpreter(out=sys.stdout, max_steps=max_steps)
    try:
        interp.run_program(ast)
        sys.stdout.flush()
        return 0
    except CmmRuntimeError as e:
        sys.stdout.flush()
        sys.stderr.write(format_error(e, path_str, source_lines))
        return 2


def _check_pipeline(path_str: str) -> int:
    """Execute pipeline for 'check' command: lex, parse, analyze."""
    normalized, source_lines = _read_source_file(path_str)

    try:
        tokens = tokenize(normalized)
    except LexError as e:
        sys.stdout.flush()
        sys.stderr.write(format_error(e, path_str, source_lines))
        return 1

    try:
        ast = parse(tokens)
    except ParseError as e:
        sys.stdout.flush()
        sys.stderr.write(format_error(e, path_str, source_lines))
        return 1

    sem_errors = analyze(ast)
    if sem_errors:
        sem_errors.sort(key=lambda err: (err.line, err.col))
        sys.stdout.flush()
        for err in sem_errors:
            sys.stderr.write(format_error(err, path_str, source_lines))
        return 1

    sys.stdout.write(f"{path_str}: OK\n")
    sys.stdout.flush()
    return 0


def _tokens_pipeline(path_str: str) -> int:
    """Execute pipeline for 'tokens' command: lex and print token stream."""
    normalized, source_lines = _read_source_file(path_str)

    try:
        tokens = tokenize(normalized)
    except LexError as e:
        sys.stdout.flush()
        sys.stderr.write(format_error(e, path_str, source_lines))
        return 1

    sys.stdout.write(format_tokens(tokens))
    sys.stdout.flush()
    return 0


def _ast_pipeline(path_str: str) -> int:
    """Execute pipeline for 'ast' command: lex, parse and print AST."""
    normalized, source_lines = _read_source_file(path_str)

    try:
        tokens = tokenize(normalized)
    except LexError as e:
        sys.stdout.flush()
        sys.stderr.write(format_error(e, path_str, source_lines))
        return 1

    try:
        ast = parse(tokens)
    except ParseError as e:
        sys.stdout.flush()
        sys.stderr.write(format_error(e, path_str, source_lines))
        return 1

    sys.stdout.write(format_ast(ast))
    sys.stdout.flush()
    return 0


def _transpile_pipeline(path_str: str, out_path_str: str) -> int:
    """Execute pipeline for 'transpile' command per §16: lex, parse, analyze, codegen C."""
    normalized, source_lines = _read_source_file(path_str)

    try:
        tokens = tokenize(normalized)
    except LexError as e:
        sys.stdout.flush()
        sys.stderr.write(format_error(e, path_str, source_lines))
        return 1

    try:
        ast = parse(tokens)
    except ParseError as e:
        sys.stdout.flush()
        sys.stderr.write(format_error(e, path_str, source_lines))
        return 1

    sem_errors = analyze(ast)
    if sem_errors:
        sem_errors.sort(key=lambda err: (err.line, err.col))
        sys.stdout.flush()
        for err in sem_errors:
            sys.stderr.write(format_error(err, path_str, source_lines))
        return 1

    c_code = generate_c(ast, path_str, source_lines)

    try:
        out_p = Path(out_path_str)
        out_p.write_text(c_code, encoding="utf-8")
    except OSError as e:
        sys.stdout.flush()
        sys.stderr.write(f"cmm: error: cannot write '{out_path_str}': {e.strerror or str(e)}\n")
        return 3

    return 0


def create_parser() -> CmmArgumentParser:
    """Construct CLI argument parser per §11.1 and §16."""
    parser = CmmArgumentParser(
        prog="cmm",
        description="Reference interpreter for the C-- language.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="print compiler version and exit",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        metavar="<command>",
        parser_class=CmmArgumentParser,
    )

    # run <file> [--max-steps N]
    p_run = subparsers.add_parser("run", help="execute a C-- program")
    p_run.add_argument("file", help="source file path")
    p_run.add_argument(
        "--max-steps",
        type=str,
        default=None,
        help="maximum execution steps (positive integer)",
    )

    # check <file>
    p_check = subparsers.add_parser("check", help="type-check a C-- program")
    p_check.add_argument("file", help="source file path")

    # tokens <file>
    p_tokens = subparsers.add_parser("tokens", help="print token list")
    p_tokens.add_argument("file", help="source file path")

    # ast <file>
    p_ast = subparsers.add_parser("ast", help="print AST representation")
    p_ast.add_argument("file", help="source file path")

    # transpile <file> -o <out.c> per §16
    p_transpile = subparsers.add_parser("transpile", help="transpile a C-- program to C99")
    p_transpile.add_argument("file", help="source file path")
    p_transpile.add_argument(
        "-o",
        "--out",
        required=True,
        dest="out",
        help="output C file path",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """Main CLI entry point returning an exit code per §11.2."""
    _configure_runtime()

    if argv is None:
        argv = sys.argv[1:]

    parser = create_parser()

    try:
        args = parser.parse_args(argv)

        if args.version:
            if args.command is not None:
                parser.error("cannot combine --version with a command")
            sys.stdout.write(f"cmm {__version__}\n")
            sys.stdout.flush()
            return 0

        if args.command is None:
            parser.error("a command is required")

        if args.command == "run":
            max_steps: Optional[int] = None
            if args.max_steps is not None:
                try:
                    val = int(args.max_steps)
                    if val <= 0:
                        raise ValueError()
                    max_steps = val
                except ValueError:
                    parser.error("--max-steps must be a positive integer")
            return _run_pipeline(args.file, max_steps=max_steps)

        elif args.command == "check":
            return _check_pipeline(args.file)

        elif args.command == "tokens":
            return _tokens_pipeline(args.file)

        elif args.command == "ast":
            return _ast_pipeline(args.file)

        elif args.command == "transpile":
            return _transpile_pipeline(args.file, args.out)

        else:
            parser.error(f"unknown command '{args.command}'")
            return 4

    except UsageError:
        return 4
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 0
    except _IoError as e:
        sys.stdout.flush()
        sys.stderr.write(f"cmm: error: cannot read '{e.path}': {e.reason}\n")
        return 3
    except Exception as e:
        sys.stdout.flush()
        if os.environ.get("CMM_DEBUG") == "1":
            traceback.print_exc(file=sys.stderr)
        sys.stderr.write(f"cmm: internal error: {type(e).__name__}: {e}\n")
        return 70
