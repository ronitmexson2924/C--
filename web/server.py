#!/usr/bin/env python3
"""
C-- Interactive Web Playground & Documentation Server.
Zero-dependency backend powered by Python's standard http.server.
Directly communicates with the C-- compiler, interpreter, and C99 transpiler.
"""

from __future__ import annotations
import http.server
import io
import json
import os
from pathlib import Path
import socketserver
import sys
import traceback
from typing import Any, Dict

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from cmm.lexer import normalize_source, tokenize
from cmm.parser import parse
from cmm.analyzer import analyze
from cmm.interpreter import Interpreter
from cmm.codegen_c import generate_c
from cmm.diagnostic_render import render_diagnostic
from cmm.astprint import format_tokens, format_ast
from cmm.errors import CmmError, LexError, ParseError, SemanticError, CmmRuntimeError, TranspileError

WEB_DIR = Path(__file__).resolve().parent
DEFAULT_PORT = 8000

SAMPLE_PRESETS = {
    "factorial": {
        "title": "1. Factorial & Pure Recursion",
        "description": "Demonstrates typed function declaration, pure recursion, and call stack safety.",
        "code": """module main;

// A recursive function computing factorial.
fn factorial(n: int) -> int {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

fn main() {
    let num = 6;
    let result = factorial(num);
    print("Factorial computation:");
    print(result);
}
"""
    },
    "collections": {
        "title": "2. Dynamic Lists & Slices",
        "description": "Demonstrates heap-managed dynamic lists with push, pop, insert, remove, and contains.",
        "code": """module main;

fn main() {
    mut fruits = list<string>();
    fruits.push("apple");
    fruits.push("banana");
    fruits.push("cherry");
    
    fruits.insert(1, "blueberry");
    
    print("Total fruits in list:");
    print(fruits.len());
    
    print("Contains 'banana'?");
    print(fruits.contains("banana"));
    
    print("Removed item at index 1:");
    print(fruits.remove(1));
    
    print("Popped last fruit:");
    print(fruits.pop());
}
"""
    },
    "stack_queue": {
        "title": "3. LIFO Stacks & FIFO Queues",
        "description": "Type-safe native ADTs without manual pointer management.",
        "code": """module main;

fn main() {
    // 1. LIFO Stack (Last In, First Out)
    mut nav_history = stack<string>();
    nav_history.push("Page 1: Home");
    nav_history.push("Page 2: Dashboard");
    nav_history.push("Page 3: Profile");
    
    print("Top page via .peek():");
    print(nav_history.peek());
    
    print("Back button (pop):");
    print(nav_history.pop());
    
    // 2. FIFO Queue (First In, First Out)
    mut job_queue = queue<int>();
    job_queue.enqueue(101);
    job_queue.enqueue(102);
    job_queue.enqueue(103);
    
    print("First job to service (dequeue):");
    print(job_queue.dequeue());
}
"""
    },
    "value_semantics": {
        "title": "4. Deep-Copy Value Semantics (No Aliasing)",
        "description": "Proves that copying or passing collections copies state completely, eliminating dangling references.",
        "code": """module main;

fn modify_copy(items: list<int>) {
    mut local_list = items;
    local_list.push(999);
    print("Inside modify_copy, length is:");
    print(local_list.len());
}

fn main() {
    mut original = list<int>();
    original.push(10);
    original.push(20);
    
    modify_copy(original);
    
    print("Caller original list length (still 2!):");
    print(original.len());
}
"""
    },
    "switch_matching": {
        "title": "5. Multi-Branch Switch-Case",
        "description": "Multi-branch pattern matching on integers and strings with mandatory break.",
        "code": """module main;

fn main() {
    let command = "start";
    
    switch (command) {
        case "start": {
            print("Server starting on port 8080...");
        }
        case "stop": {
            print("Server shutting down.");
        }
        default: {
            print("Unknown server directive.");
        }
    }
    
    let day = 3;
    switch (day) {
        case 1: { print("Monday"); }
        case 2: { print("Tuesday"); }
        case 3: { print("Wednesday"); }
        default: { print("Weekend"); }
    }
}
"""
    },
    "transpile_demo": {
        "title": "6. C99 Transpilation Showcase",
        "description": "Program suitable for immediate transpilation into hardened ISO C99 code.",
        "code": """module main;

fn main() {
    let base = 100;
    let multiplier = 5;
    mut sum = 0;
    
    for (mut i = 1; i <= 5; i = i + 1) {
        sum = sum + i * multiplier;
    }
    
    let total = base + sum;
    print("Transpiled C99 Computation Result:");
    print(total);
}
"""
    },
    "error_diagnostic": {
        "title": "7. Friendly Diagnostics & Typo Correction",
        "description": "Trigger the human-centric error engine with a typo to see the Levenshtein suggestion.",
        "code": """module main;

fn main() {
    let maximum_score = 100;
    // Deliberate typo below: 'maximum_scor' instead of 'maximum_score'
    mut current = maximum_scor + 10;
    print(current);
}
"""
    }
}


class CompilerService:
    """Wrapper around the C-- compiler pipeline."""

    @staticmethod
    def run_code(code_str: str, help_enabled: bool = True) -> Dict[str, Any]:
        normalized = normalize_source(code_str)
        source_lines = normalized.splitlines(keepends=True)
        path_str = "playground.cmm"

        # 1. Lex
        try:
            tokens = tokenize(normalized)
        except LexError as e:
            err_msg = render_diagnostic(e, path_str, source_lines, help_enabled=help_enabled)
            return {"success": False, "stage": "lexer", "error": err_msg, "exit_code": 1}

        # 2. Parse
        try:
            ast = parse(tokens)
        except ParseError as e:
            err_msg = render_diagnostic(e, path_str, source_lines, help_enabled=help_enabled)
            return {"success": False, "stage": "parser", "error": err_msg, "exit_code": 1}

        # 3. Analyze
        sem_errors = analyze(ast)
        if sem_errors:
            sem_errors.sort(key=lambda err: (err.line, err.col))
            rendered_errors = [render_diagnostic(err, path_str, source_lines, help_enabled=help_enabled) for err in sem_errors]
            return {"success": False, "stage": "analyzer", "error": "\n".join(rendered_errors), "exit_code": 1}

        # 4. Interpret
        out_buf = io.StringIO()
        interp = Interpreter(out=out_buf, max_steps=100000)
        try:
            interp.run_program(ast)
            output = out_buf.getvalue()
            return {"success": True, "stage": "interpreter", "output": output, "exit_code": 0}
        except CmmRuntimeError as e:
            err_msg = render_diagnostic(e, path_str, source_lines, help_enabled=help_enabled)
            return {"success": False, "stage": "runtime", "error": err_msg, "exit_code": 2}
        except Exception as e:
            return {"success": False, "stage": "internal", "error": f"Internal Error: {str(e)}\n{traceback.format_exc()}", "exit_code": 3}

    @staticmethod
    def transpile_code(code_str: str, help_enabled: bool = True) -> Dict[str, Any]:
        normalized = normalize_source(code_str)
        source_lines = normalized.splitlines(keepends=True)
        path_str = "playground.cmm"

        try:
            tokens = tokenize(normalized)
        except LexError as e:
            err_msg = render_diagnostic(e, path_str, source_lines, help_enabled=help_enabled)
            return {"success": False, "stage": "lexer", "error": err_msg}

        try:
            ast = parse(tokens)
        except ParseError as e:
            err_msg = render_diagnostic(e, path_str, source_lines, help_enabled=help_enabled)
            return {"success": False, "stage": "parser", "error": err_msg}

        sem_errors = analyze(ast)
        if sem_errors:
            sem_errors.sort(key=lambda err: (err.line, err.col))
            rendered_errors = [render_diagnostic(err, path_str, source_lines, help_enabled=help_enabled) for err in sem_errors]
            return {"success": False, "stage": "analyzer", "error": "\n".join(rendered_errors)}

        try:
            import importlib
            import cmm.codegen_c
            importlib.reload(cmm.codegen_c)
            c_code = cmm.codegen_c.generate_c(ast, path_str, source_lines)
            return {"success": True, "c_code": c_code}
        except TranspileError as e:
            err_msg = render_diagnostic(e, path_str, source_lines, help_enabled=help_enabled)
            return {"success": False, "stage": "transpiler", "error": err_msg}
        except Exception as e:
            return {"success": False, "stage": "internal", "error": f"Transpilation Failed: {str(e)}"}

    @staticmethod
    def inspect_ast(code_str: str) -> Dict[str, Any]:
        normalized = normalize_source(code_str)
        source_lines = normalized.splitlines(keepends=True)
        try:
            tokens = tokenize(normalized)
            ast = parse(tokens)
            return {"success": True, "ast": format_ast(ast)}
        except CmmError as e:
            err_msg = render_diagnostic(e, "playground.cmm", source_lines, help_enabled=True)
            return {"success": False, "error": err_msg}

    @staticmethod
    def inspect_tokens(code_str: str) -> Dict[str, Any]:
        normalized = normalize_source(code_str)
        source_lines = normalized.splitlines(keepends=True)
        try:
            tokens = tokenize(normalized)
            return {"success": True, "tokens": format_tokens(tokens)}
        except LexError as e:
            err_msg = render_diagnostic(e, "playground.cmm", source_lines, help_enabled=True)
            return {"success": False, "error": err_msg}


class CmmRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP request handler serving static files and C-- REST endpoints."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b"{}"
        
        try:
            payload = json.loads(post_data.decode("utf-8"))
        except Exception:
            self._send_json({"success": False, "error": "Invalid JSON payload"}, status=400)
            return

        code = payload.get("code", "")
        help_enabled = payload.get("help_enabled", True)

        if self.path == "/api/run":
            res = CompilerService.run_code(code, help_enabled=help_enabled)
            self._send_json(res)
        elif self.path == "/api/transpile":
            res = CompilerService.transpile_code(code, help_enabled=help_enabled)
            self._send_json(res)
        elif self.path == "/api/ast":
            res = CompilerService.inspect_ast(code)
            self._send_json(res)
        elif self.path == "/api/tokens":
            res = CompilerService.inspect_tokens(code)
            self._send_json(res)
        else:
            self._send_json({"error": "Endpoint not found"}, status=404)

    def do_GET(self):
        if self.path == "/api/presets":
            self._send_json(SAMPLE_PRESETS)
            return
        elif self.path.startswith("/assets/"):
            asset_subpath = self.path[len("/assets/"):]
            asset_file = REPO_ROOT / "assets" / asset_subpath
            if self._serve_custom_file(asset_file, send_body=True):
                return
        elif self.path.startswith("/document/") or self.path.startswith("/docs/"):
            prefix = "/document/" if self.path.startswith("/document/") else "/docs/"
            doc_folder = "document" if prefix == "/document/" else "docs"
            subpath = self.path[len(prefix):]
            doc_file = REPO_ROOT / doc_folder / subpath
            if self._serve_custom_file(doc_file, send_body=True):
                return
        
        # Default file serving from WEB_DIR
        super().do_GET()

    def do_HEAD(self):
        if self.path.startswith("/assets/"):
            asset_subpath = self.path[len("/assets/"):]
            asset_file = REPO_ROOT / "assets" / asset_subpath
            if self._serve_custom_file(asset_file, send_body=False):
                return
        elif self.path.startswith("/document/") or self.path.startswith("/docs/"):
            prefix = "/document/" if self.path.startswith("/document/") else "/docs/"
            doc_folder = "document" if prefix == "/document/" else "docs"
            subpath = self.path[len(prefix):]
            doc_file = REPO_ROOT / doc_folder / subpath
            if self._serve_custom_file(doc_file, send_body=False):
                return
        super().do_HEAD()

    def _serve_custom_file(self, file_path: Path, send_body: bool = True) -> bool:
        if file_path.exists() and file_path.is_file():
            self.send_response(200)
            suffix = file_path.suffix.lower()
            if suffix == ".png":
                self.send_header("Content-Type", "image/png")
            elif suffix == ".svg":
                self.send_header("Content-Type", "image/svg+xml")
            elif suffix == ".pdf":
                self.send_header("Content-Type", "application/pdf")
            elif suffix == ".html":
                self.send_header("Content-Type", "text/html; charset=utf-8")
            else:
                self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(file_path.stat().st_size))
            self.end_headers()
            if send_body:
                try:
                    with open(file_path, "rb") as f:
                        self.wfile.write(f.read())
                except (BrokenPipeError, ConnectionResetError):
                    pass
            return True
        return False

    def _send_json(self, data: Dict[str, Any], status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


def run_server(port: int = DEFAULT_PORT):
    # Allow port reuse
    socketserver.TCPServer.allow_reuse_address = True
    ports_to_try = [port] if port != DEFAULT_PORT else [port, 8080, 8081, 8888, 5000]
    for p in ports_to_try:
        try:
            with socketserver.TCPServer(("", p), CmmRequestHandler) as httpd:
                print(f"C-- Web Playground & Documentation Server running on port {p}")
                print(f"URL: http://localhost:{p}")
                print("Press Ctrl+C to terminate.")
                httpd.serve_forever()
                return
        except OSError as e:
            if port != DEFAULT_PORT:
                print(f"Error: Port {p} is unavailable: {e}")
                sys.exit(1)
            print(f"Port {p} in use, trying next port...")


if __name__ == "__main__":
    env_port = os.environ.get("PORT")
    if env_port and env_port.isdigit():
        port_arg = int(env_port)
    elif len(sys.argv) > 1 and sys.argv[1].isdigit():
        port_arg = int(sys.argv[1])
    else:
        port_arg = DEFAULT_PORT
    run_server(port_arg)
