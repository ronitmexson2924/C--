#!/usr/bin/env python3
"""
C-- Interactive Web Playground & Documentation Server.
Zero-dependency backend powered by Python's standard http.server.
Directly communicates with the C-- compiler, interpreter, and C99 transpiler.
"""

from __future__ import annotations
import email.utils
import gzip
import hashlib
import http.server
import io
import json
import mimetypes
import os
from pathlib import Path
import sys
import traceback
from typing import Any, Dict, Optional
from urllib.parse import urlsplit

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cmm.lexer import normalize_source, tokenize
from cmm.parser import parse
from cmm.analyzer import analyze
from cmm.interpreter import Interpreter
from cmm.codegen_c import generate_c
from cmm.diagnostic_render import render_diagnostic
from cmm.astprint import format_tokens, format_ast
from cmm.errors import CmmError, LexError, ParseError, SemanticError, CmmRuntimeError, TranspileError
import seo

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
        # Empty stdin: input() reports end-of-input instead of blocking on the server's own stdin
        interp = Interpreter(out=out_buf, max_steps=100000, stdin=io.StringIO(""))
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
    def check_code(code_str: str, help_enabled: bool = True) -> Dict[str, Any]:
        """Run the static front-end (lex, parse, analyze) without executing the program."""
        normalized = normalize_source(code_str)
        source_lines = normalized.splitlines(keepends=True)
        path_str = "playground.cmm"

        try:
            tokens = tokenize(normalized)
        except LexError as e:
            err_msg = render_diagnostic(e, path_str, source_lines, help_enabled=help_enabled)
            return {"success": False, "stage": "lexer", "error": err_msg, "exit_code": 1}

        try:
            ast = parse(tokens)
        except ParseError as e:
            err_msg = render_diagnostic(e, path_str, source_lines, help_enabled=help_enabled)
            return {"success": False, "stage": "parser", "error": err_msg, "exit_code": 1}

        sem_errors = analyze(ast)
        if sem_errors:
            sem_errors.sort(key=lambda err: (err.line, err.col))
            rendered_errors = [render_diagnostic(err, path_str, source_lines, help_enabled=help_enabled) for err in sem_errors]
            return {"success": False, "stage": "analyzer", "error": "\n".join(rendered_errors), "exit_code": 1}

        return {"success": True, "stage": "analyzer", "exit_code": 0}

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
            c_code = generate_c(ast, path_str, source_lines)
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


# Files under web/ that may be served directly (templates, content and Python sources are private)
STATIC_EXTENSIONS = {".css", ".js", ".woff2", ".png", ".svg", ".ico", ".txt", ".json"}
COMPRESSIBLE_TYPES = ("text/", "application/javascript", "application/json", "application/xml",
                      "image/svg+xml", "application/manifest+json")
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".xml": "application/xml; charset=utf-8",
    ".webmanifest": "application/manifest+json; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".icns": "image/icns",
    ".pdf": "application/pdf",
    ".woff2": "font/woff2",
}
LEGACY_REDIRECTS = {"/index.html": "/"}
CACHE_HTML = "public, max-age=60, must-revalidate"
CACHE_STATIC = "public, max-age=86400"
CACHE_IMMUTABLE = "public, max-age=31536000, immutable"


def content_type_for(path: Path) -> str:
    return CONTENT_TYPES.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def safe_join(base: Path, subpath: str) -> Optional[Path]:
    """Resolve subpath under base, refusing anything that escapes it (path traversal)."""
    try:
        candidate = (base / subpath).resolve()
        base_resolved = base.resolve()
    except (OSError, ValueError):
        return None
    if candidate != base_resolved and base_resolved not in candidate.parents:
        return None
    return candidate if candidate.is_file() else None


class CmmRequestHandler(http.server.BaseHTTPRequestHandler):
    """Serves rendered pages, static assets, crawl files, and the C-- REST API."""

    server_version = "CmmStudio/0.2"
    protocol_version = "HTTP/1.1"

    # ------------------------------------------------------------------ API
    def do_POST(self):
        path = urlsplit(self.path).path
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            content_length = 0
        if content_length > 1_000_000:
            self._send_json({"success": False, "error": "Payload too large"}, status=413)
            return
        post_data = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            payload = json.loads(post_data.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("payload must be an object")
        except Exception:
            self._send_json({"success": False, "error": "Invalid JSON payload"}, status=400)
            return

        code = payload.get("code", "")
        if not isinstance(code, str):
            code = str(code)
        help_enabled = payload.get("help_enabled", True)

        if path == "/api/run":
            res = CompilerService.run_code(code, help_enabled=help_enabled)
            self._send_json(res)
        elif path == "/api/check":
            res = CompilerService.check_code(code, help_enabled=help_enabled)
            self._send_json(res)
        elif path == "/api/transpile":
            res = CompilerService.transpile_code(code, help_enabled=help_enabled)
            self._send_json(res)
        elif path == "/api/ast":
            res = CompilerService.inspect_ast(code)
            self._send_json(res)
        elif path == "/api/tokens":
            res = CompilerService.inspect_tokens(code)
            self._send_json(res)
        else:
            self._send_json({"error": "Endpoint not found"}, status=404)

    # ------------------------------------------------------------ GET/HEAD
    def do_GET(self):
        self._dispatch(send_body=True)

    def do_HEAD(self):
        self._dispatch(send_body=False)

    def _dispatch(self, send_body: bool):
        parts = urlsplit(self.path)
        path = parts.path or "/"

        if path == "/api/presets":
            self._send_json(SAMPLE_PRESETS, send_body=send_body)
            return
        if path.startswith("/api/"):
            self._send_json({"error": "Endpoint not found"}, status=404, send_body=send_body)
            return

        # Canonical URL forms: /index.html -> /, /reference/ -> /reference
        target = LEGACY_REDIRECTS.get(path)
        if target is None and len(path) > 1 and path.endswith("/") and path.rstrip("/") in seo.PAGES_BY_PATH:
            target = path.rstrip("/")
        if target is not None:
            self._redirect(target + (f"?{parts.query}" if parts.query else ""))
            return

        page = seo.PAGES_BY_PATH.get(path)
        if page is not None:
            self._send_page(page, status=200, send_body=send_body)
            return

        text_routes = {
            "/robots.txt": (seo.robots_txt, ".txt"),
            "/sitemap.xml": (lambda: seo.sitemap_xml(REPO_ROOT), ".xml"),
            "/site.webmanifest": (seo.web_manifest, ".webmanifest"),
        }
        if path in text_routes:
            producer, ext = text_routes[path]
            self._send_bytes(producer().encode("utf-8"), CONTENT_TYPES[ext], CACHE_HTML, send_body=send_body)
            return

        verification = seo.google_verification_file(path)
        if verification is not None:
            self._send_bytes(verification.encode("utf-8"), CONTENT_TYPES[".html"], CACHE_HTML, send_body=send_body)
            return

        if path == "/favicon.ico":
            self._send_file(REPO_ROOT / "assets" / "cmm.ico", query=parts.query, send_body=send_body)
            return

        for prefix, folder in (("/assets/", "assets"), ("/document/", "document"), ("/docs/", "docs")):
            if path.startswith(prefix):
                file_path = safe_join(REPO_ROOT / folder, path[len(prefix):])
                if file_path is not None:
                    self._send_file(file_path, query=parts.query, send_body=send_body)
                    return
                break

        file_path = safe_join(seo.WEB_DIR, path.lstrip("/"))
        if file_path is not None and file_path.suffix.lower() in STATIC_EXTENSIONS \
                and file_path.parent.name not in ("templates", "content", "__pycache__"):
            self._send_file(file_path, query=parts.query, send_body=send_body)
            return

        self._send_page(seo.NOT_FOUND, status=404, send_body=send_body, indexable=False)

    # ------------------------------------------------------------- helpers
    def _security_headers(self, csp: Optional[str] = None):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        if csp:
            self.send_header("Content-Security-Policy", csp)

    def _page_csp(self, document: str) -> str:
        scripts = " ".join(["'self'"] + seo.inline_script_hashes(document))
        return (
            "default-src 'self'; "
            f"script-src {scripts}; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "manifest-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'self'"
        )

    def _send_page(self, page, status: int, send_body: bool, indexable: bool = True):
        document = seo.render_page(page, indexable=indexable)
        self._send_bytes(document.encode("utf-8"), CONTENT_TYPES[".html"], CACHE_HTML, status=status,
                         send_body=send_body, csp=self._page_csp(document))

    def _send_file(self, file_path: Path, query: str, send_body: bool):
        ctype = content_type_for(file_path)
        cache = CACHE_IMMUTABLE if "v=" in query else CACHE_STATIC
        extra = {}
        if file_path.suffix.lower() == ".pdf":
            extra["X-Robots-Tag"] = "index, follow"
        stat = file_path.stat()
        extra["Last-Modified"] = email.utils.formatdate(stat.st_mtime, usegmt=True)
        try:
            body = file_path.read_bytes()
        except OSError:
            self._send_page(seo.NOT_FOUND, status=404, send_body=send_body, indexable=False)
            return
        self._send_bytes(body, ctype, cache, send_body=send_body, extra=extra)

    def _accepts_gzip(self) -> bool:
        return "gzip" in self.headers.get("Accept-Encoding", "").lower()

    def _send_bytes(self, body: bytes, ctype: str, cache: str, status: int = 200, send_body: bool = True,
                    csp: Optional[str] = None, extra: Optional[Dict[str, str]] = None):
        etag = '"' + hashlib.sha256(body).hexdigest()[:20] + '"'
        if status == 200 and etag in self.headers.get("If-None-Match", ""):
            self.send_response(304)
            self.send_header("ETag", etag)
            self.send_header("Cache-Control", cache)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        encoded = body
        compress = len(body) > 512 and ctype.startswith(COMPRESSIBLE_TYPES) and self._accepts_gzip()
        if compress:
            encoded = gzip.compress(body, compresslevel=6)

        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", cache)
        self.send_header("ETag", etag)
        if ctype.startswith(COMPRESSIBLE_TYPES):
            self.send_header("Vary", "Accept-Encoding")
        if compress:
            self.send_header("Content-Encoding", "gzip")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self._security_headers(csp)
        self.end_headers()
        if send_body:
            self._write(encoded)

    def _redirect(self, location: str):
        self.send_response(301)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()

    def _send_json(self, data: Dict[str, Any], status: int = 200, send_body: bool = True):
        body = json.dumps(data).encode("utf-8")
        if len(body) > 1024 and self._accepts_gzip():
            body_out, encoding = gzip.compress(body, compresslevel=6), "gzip"
        else:
            body_out, encoding = body, None
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body_out)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Vary", "Accept-Encoding")
        if encoding:
            self.send_header("Content-Encoding", encoding)
        self.send_header("Access-Control-Allow-Origin", "*")
        self._security_headers()
        self.end_headers()
        if send_body:
            self._write(body_out)

    def _write(self, data: bytes):
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass


class StudioServer(http.server.ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def run_server(port: int = DEFAULT_PORT):
    ports_to_try = [port] if port != DEFAULT_PORT else [port, 8080, 8081, 8888, 5000]
    for p in ports_to_try:
        try:
            with StudioServer(("", p), CmmRequestHandler) as httpd:
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
