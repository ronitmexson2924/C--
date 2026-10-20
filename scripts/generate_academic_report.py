#!/usr/bin/env python3
"""
Academic Project Report Generator for C-- (C Minus Minus).
Generates an exhaustive, publication-grade academic report in HTML
and compiles it into a print-ready PDF using Headless Google Chrome.
"""

from __future__ import annotations
import base64
import os
from pathlib import Path
import shutil
import subprocess
import sys

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def get_base64_image(image_path: Path) -> str:
    """Read an image file and return a data URI string."""
    if not image_path.exists():
        return ""
    mime_type = "image/png"
    if image_path.suffix.lower() in [".jpg", ".jpeg"]:
        mime_type = "image/jpeg"
    elif image_path.suffix.lower() == ".svg":
        mime_type = "image/svg+xml"
    with open(image_path, "rb") as f:
        b64_data = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime_type};base64,{b64_data}"


def build_full_html(logo_b64: str) -> str:
    """Return the complete, professionally formatted academic HTML report."""
    parts = []
    parts.append("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>C-- Language Specification and Compiler Implementation Report - SCOPE</title>
<style>
/* ==========================================================================
   ACADEMIC PRINT & SCREEN STYLESHEET
   Target: A4 Paper, High-Density Print Typography
   ========================================================================== */

@page {
    size: A4 portrait;
    margin: 22mm 18mm 22mm 18mm;
    @top-left {
        content: "C-- Language Specification & Compiler System";
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 8pt;
        color: #64748b;
        font-weight: 500;
    }
    @top-right {
        content: "Course Project Report (v0.2.0)";
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 8pt;
        color: #64748b;
    }
    @bottom-left {
        content: "School of Computer Science and Engineering (SCOPE)";
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 8pt;
        color: #64748b;
    }
    @bottom-right {
        content: "Page " counter(page);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 8pt;
        color: #0f172a;
        font-weight: 600;
    }
}

@page :first {
    margin: 0;
}

*, *::before, *::after {
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 10pt;
    line-height: 1.6;
    color: #1e293b;
    background-color: #ffffff;
    margin: 0;
    padding: 0;
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
}

/* Typography */
h1, h2, h3, h4, h5, h6 {
    color: #0f172a;
    font-weight: 700;
    line-height: 1.25;
    margin-top: 1.4em;
    margin-bottom: 0.5em;
    page-break-after: avoid;
}

h1.chapter-title {
    font-size: 17pt;
    color: #0f172a;
    border-bottom: 2px solid #2563eb;
    padding-bottom: 6px;
    margin-top: 1.6em;
    margin-bottom: 0.8em;
}

h2.section-title {
    font-size: 12.5pt;
    color: #1e3a8a;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 4px;
    margin-top: 1.3em;
    margin-bottom: 0.5em;
}

h3.subsection-title {
    font-size: 10.5pt;
    color: #334155;
    margin-top: 1.1em;
    margin-bottom: 0.4em;
}

p {
    margin: 0.6em 0;
    text-align: justify;
    text-justify: inter-word;
}

.lead {
    font-size: 10.5pt;
    color: #334155;
    font-weight: 400;
}

/* Page Breaks */
.page-break {
    page-break-before: always;
}

.avoid-break {
    page-break-inside: avoid;
}

/* Cover Page */
.cover-page {
    width: 100%;
    min-height: 100vh;
    padding: 28mm 24mm 24mm 24mm;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
}

.cover-header {
    border-bottom: 3px solid #2563eb;
    padding-bottom: 15px;
}

.university-tag {
    font-size: 12pt;
    font-weight: 800;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #1e3a8a;
    margin-bottom: 4px;
}

.faculty-tag {
    font-size: 10pt;
    color: #475569;
    font-weight: 600;
}

.cover-body {
    margin: 25px 0;
    text-align: center;
}

.logo-container {
    margin-bottom: 18px;
}

.cover-logo {
    width: 105px;
    height: 105px;
    border-radius: 20px;
    box-shadow: 0 10px 25px -5px rgba(37, 99, 235, 0.25);
}

.report-badge {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 9999px;
    background-color: #dbeafe;
    color: #1e40af;
    font-size: 8.5pt;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    margin-bottom: 12px;
}

.cover-title {
    font-size: 26pt;
    font-weight: 800;
    color: #0f172a;
    line-height: 1.15;
    margin: 8px 0 12px 0;
    letter-spacing: -0.5px;
}

.cover-subtitle {
    font-size: 11.5pt;
    font-weight: 400;
    color: #475569;
    line-height: 1.5;
    max-width: 650px;
    margin: 0 auto;
}

.cover-meta-grid {
    display: grid;
    grid-template-columns: 1.15fr 0.85fr;
    gap: 18px;
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    padding: 18px 22px;
    margin: 22px auto 10px auto;
    max-width: 720px;
    text-align: left;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}

.meta-team-list {
    display: flex;
    flex-direction: column;
    gap: 7px;
    margin-top: 6px;
}

.team-member {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 6px 10px;
}

.member-name {
    font-weight: 700;
    color: #0f172a;
    font-size: 9pt;
}

.member-reg {
    font-family: "SFMono-Regular", Consolas, monospace;
    font-weight: 700;
    color: #1d4ed8;
    background-color: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 8pt;
}

.meta-faculty-box {
    background-color: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-left: 4px solid #16a34a;
    border-radius: 6px;
    padding: 8px 12px;
    margin-top: 5px;
}

.faculty-name {
    font-size: 10pt;
    font-weight: 700;
    color: #0f172a;
}

.faculty-school {
    font-size: 8.5pt;
    font-weight: 600;
    color: #15803d;
    margin-top: 2px;
}

.meta-item {
    font-size: 9pt;
}

.meta-label {
    color: #64748b;
    font-weight: 700;
    text-transform: uppercase;
    font-size: 7.5pt;
    letter-spacing: 0.5px;
    margin-bottom: 2px;
}

.meta-value {
    color: #0f172a;
    font-weight: 600;
    font-size: 9pt;
}

.cover-resources-card {
    display: flex;
    flex-direction: column;
    gap: 8px;
    background-color: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 10px 16px;
    margin: 14px auto 0 auto;
    max-width: 720px;
    text-align: left;
}

.resource-row {
    display: flex;
    align-items: center;
    gap: 12px;
}

.resource-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 9999px;
    font-size: 7.5pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    white-space: nowrap;
}

.github-badge {
    background-color: #0f172a;
    color: #ffffff;
}

.live-badge {
    background-color: #16a34a;
    color: #ffffff;
}

.resource-link {
    font-family: "SFMono-Regular", Consolas, monospace;
    font-size: 8.5pt;
    font-weight: 600;
    color: #2563eb;
    text-decoration: none;
    word-break: break-all;
}

.cover-footer {
    border-top: 1px solid #e2e8f0;
    padding-top: 12px;
    display: flex;
    justify-content: space-between;
    font-size: 8.5pt;
    color: #64748b;
}

/* Abstract Card */
.abstract-box {
    background-color: #f8fafc;
    border: 1px solid #cbd5e1;
    border-left: 5px solid #2563eb;
    border-radius: 6px;
    padding: 16px 20px;
    margin: 18px 0;
}

.abstract-title {
    font-size: 11pt;
    font-weight: 700;
    color: #0f172a;
    margin-top: 0;
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.keywords {
    margin-top: 10px;
    font-size: 8.5pt;
    color: #475569;
}

/* Table of Contents */
.toc-list {
    list-style: none;
    padding: 0;
    margin: 16px 0;
}

.toc-item {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: 5px 0;
    border-bottom: 1px dotted #cbd5e1;
    font-size: 9pt;
}

.toc-item.level-1 {
    font-weight: 700;
    color: #0f172a;
    padding-top: 8px;
}

.toc-item.level-2 {
    padding-left: 18px;
    color: #334155;
}

.toc-page {
    font-family: monospace;
    font-weight: 600;
    color: #2563eb;
}

/* Code Listings */
pre, code {
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
}

pre.code-block {
    background-color: #0f172a;
    color: #f8fafc;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 8.5pt;
    line-height: 1.45;
    overflow-x: auto;
    margin: 12px 0;
    border: 1px solid #1e293b;
    page-break-inside: avoid;
}

code.inline {
    background-color: #f1f5f9;
    color: #0f172a;
    padding: 1px 5px;
    border-radius: 4px;
    font-size: 8.5pt;
    border: 1px solid #e2e8f0;
}

/* Syntax Colors */
.token-kw { color: #38bdf8; font-weight: 600; }
.token-type { color: #a78bfa; font-weight: 600; }
.token-fn { color: #fbbf24; }
.token-str { color: #34d399; }
.token-num { color: #f472b6; }
.token-comment { color: #64748b; font-style: italic; }
.token-op { color: #94a3b8; }

/* Tables */
table.academic-table {
    width: 100%;
    border-collapse: collapse;
    margin: 14px 0;
    font-size: 8.5pt;
    page-break-inside: avoid;
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
}

table.academic-table th {
    background-color: #f1f5f9;
    color: #0f172a;
    font-weight: 700;
    text-align: left;
    padding: 8px 10px;
    border-top: 2px solid #0f172a;
    border-bottom: 1.5px solid #0f172a;
}

table.academic-table td {
    padding: 7px 10px;
    border-bottom: 1px solid #e2e8f0;
    vertical-align: top;
}

table.academic-table tr:nth-child(even) td {
    background-color: #f8fafc;
}

table.academic-table tr:last-child td {
    border-bottom: 2px solid #0f172a;
}

/* Callout Boxes */
.callout {
    border-radius: 6px;
    padding: 12px 16px;
    margin: 14px 0;
    font-size: 9pt;
    page-break-inside: avoid;
}

.callout-info {
    background-color: #eff6ff;
    border-left: 4px solid #3b82f6;
    color: #1e3a8a;
}

.callout-security {
    background-color: #fef2f2;
    border-left: 4px solid #ef4444;
    color: #991b1b;
}

.callout-success {
    background-color: #ecfdf5;
    border-left: 4px solid #10b981;
    color: #065f46;
}

.callout-title {
    font-weight: 700;
    margin-bottom: 4px;
    text-transform: uppercase;
    font-size: 8pt;
    letter-spacing: 0.5px;
}

/* Badges */
.badge {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 7.5pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}

.badge-safe { background-color: #d1fae5; color: #065f46; }
.badge-vuln { background-color: #fee2e2; color: #991b1b; }
.badge-lex { background-color: #fef3c7; color: #92400e; }
.badge-syn { background-color: #e0e7ff; color: #3730a3; }
.badge-sem { background-color: #fce7f3; color: #9d174d; }
.badge-run { background-color: #fee2e2; color: #991b1b; }
.badge-trn { background-color: #ccfbf1; color: #115e59; }

/* Architectural Diagrams */
.diagram-box {
    background-color: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 16px;
    margin: 14px 0;
    page-break-inside: avoid;
}

.pipeline-flow {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    margin: 10px 0;
}

.pipeline-node {
    background-color: #ffffff;
    border: 1.5px solid #2563eb;
    border-radius: 6px;
    padding: 9px 6px;
    text-align: center;
    flex: 1;
    box-shadow: 0 2px 4px rgba(0,0,0,0.04);
}

.pipeline-node .title {
    font-weight: 700;
    font-size: 8pt;
    color: #0f172a;
}

.pipeline-node .desc {
    font-size: 7pt;
    color: #64748b;
    margin-top: 2px;
}

.pipeline-arrow {
    font-size: 13pt;
    color: #2563eb;
    font-weight: 700;
}

/* Diagnostics UI Mockup */
.gutter-mockup {
    background-color: #0f172a;
    color: #f8fafc;
    border-radius: 6px;
    padding: 12px 16px;
    font-family: monospace;
    font-size: 8.5pt;
    line-height: 1.5;
    margin: 12px 0;
    border: 1px solid #334155;
    page-break-inside: avoid;
}

.gutter-red { color: #ef4444; font-weight: bold; }
.gutter-cyan { color: #38bdf8; font-weight: bold; }
.gutter-green { color: #34d399; }
.gutter-gray { color: #64748b; }

.font-mono { font-family: monospace; }
.bold { font-weight: 700; }
.text-center { text-align: center; }
</style>
</head>
<body>

<!-- ========================================================================
     COVER PAGE / TITLE PAGE
     ======================================================================== -->
<div class="cover-page">
    <div class="cover-header">
        <div class="university-tag">School of Computer Science and Engineering (SCOPE)</div>
        <div class="faculty-tag">Compiler Design Laboratory Project Report</div>
    </div>
    
    <div class="cover-body">
        <div class="logo-container">
            <img class="cover-logo" src=\"""" + logo_b64 + """\" alt="C-- Language Emblem">
        </div>
        
        <div>
            <span class="report-badge">Course Project Report &bull; Compiler Design</span>
        </div>
        
        <h1 class="cover-title">C-- (C Minus Minus)</h1>
        <div class="cover-subtitle">
            A High-Assurance, Memory-Safe Imperative Programming Language and Multi-Target Compiler System:
            Formal Grammar, Dual-Target Execution, and Human-Centric Diagnostics
        </div>
        
        <div class="cover-meta-grid">
            <div class="meta-item meta-team">
                <div class="meta-label">Project Team Members (SCOPE)</div>
                <div class="meta-team-list">
                    <div class="team-member">
                        <span class="member-name">Ronit Mexson</span>
                        <span class="member-reg">24BAI0036</span>
                    </div>
                    <div class="team-member">
                        <span class="member-name">Mit Kumar Raju Panchal</span>
                        <span class="member-reg">24BAU0279</span>
                    </div>
                    <div class="team-member">
                        <span class="member-name">Garv Gupta</span>
                        <span class="member-reg">24BAI0169</span>
                    </div>
                </div>
                <div class="meta-label" style="margin-top: 12px;">Student School</div>
                <div class="meta-value">School of Computer Science and Engineering (SCOPE)</div>
            </div>
            
            <div class="meta-item">
                <div class="meta-label">Faculty Project Guide &amp; Evaluator</div>
                <div class="meta-faculty-box">
                    <div class="faculty-name">Prof. Hariharan R L</div>
                    <div class="faculty-school">Center for AI Research</div>
                </div>
                
                <div class="meta-label" style="margin-top: 12px;">Course &amp; Academic Session</div>
                <div class="meta-value">Compiler Design &bull; Session 2024–2025</div>
                
                <div class="meta-label" style="margin-top: 10px;">Compiler Release / Version</div>
                <div class="meta-value">v0.2.0 (Production Specification)</div>
                
                <div class="meta-label" style="margin-top: 10px;">Verification Status</div>
                <div class="meta-value" style="color: #059669;">417 / 417 Automated Tests Passing (100%)</div>
            </div>
        </div>

        <div class="cover-resources-card">
            <div class="resource-row">
                <span class="resource-badge github-badge">GitHub Repository</span>
                <a href="https://github.com/ronitmexson2924/C--" class="resource-link" target="_blank">https://github.com/ronitmexson2924/C--</a>
            </div>
            <div class="resource-row">
                <span class="resource-badge live-badge">Live Web Studio</span>
                <a href="https://web-production-c8ddc.up.railway.app" class="resource-link" target="_blank">https://web-production-c8ddc.up.railway.app</a>
            </div>
        </div>
    </div>
    
    <div class="cover-footer">
        <div>School of Computer Science and Engineering (SCOPE) &bull; GitHub: <code>https://github.com/ronitmexson2924/C--</code></div>
        <div>Live Deployment: <code>https://web-production-c8ddc.up.railway.app</code> &bull; October 2026</div>
    </div>
</div>

<div class="page-break"></div>

<!-- ========================================================================
     ABSTRACT & TABLE OF CONTENTS
     ======================================================================== -->
<div class="abstract-box">
    <div class="abstract-title">Executive Abstract</div>
    <p>
        For five decades, the C programming language has formed the bedrock of systems programming. However, C's reliance on manual pointer arithmetic, arbitrary memory addressing, nullable references, and permissive type coercion has made it the primary contributor to critical vulnerabilities cataloged in the Common Weakness Enumeration (CWE), including buffer overflows, dangling pointers, and undefined behavior.
    </p>
    <p>
        This paper introduces <strong>C-- (C Minus Minus)</strong>, a high-assurance imperative programming language engineered around the paradigm of <em>"Safety by Removal."</em> By surgically eliminating raw pointers, nullable references, implicit type conversions, and uninitialized variables at language design time, C-- provides mathematical memory safety without the cognitive burden of Rust's borrow checker or the runtime latency of a garbage collector.
    </p>
    <p>
        The complete compiler pipeline—implemented in Python—features an LL(k) recursive-descent parser with precedence climbing, strict semantic scoping, a reference tree-walking interpreter with deep-copy value semantics, and an ISO C99 code generator emitting hardened native code. Furthermore, C-- pioneers pedagogical developer tooling through a 60-code diagnostic taxonomy providing 3-line source gutters, root-cause explanations, and Levenshtein-distance typo suggestions. The implementation is verified across 417 automated test suites with a 100% pass rate.
    </p>
    <div class="keywords">
        <strong>ACM CCS Terms:</strong> Software and its engineering &rarr; Compilers; Language features; Source code generation; Software defect analysis; Software safety.
    </div>
</div>

<h1 class="chapter-title">Table of Contents</h1>
<ul class="toc-list">
    <li class="toc-item level-1">
        <span>1. Introduction &amp; Motivation ("Safety by Removal")</span>
        <span class="toc-page">Page 3</span>
    </li>
    <li class="toc-item level-2">
        <span>1.1 The Systems Programming Memory Crisis &amp; CWE Taxonomy</span>
        <span class="toc-page">Page 3</span>
    </li>
    <li class="toc-item level-2">
        <span>1.2 The "Safety by Removal" Paradigm</span>
        <span class="toc-page">Page 3</span>
    </li>
    <li class="toc-item level-2">
        <span>1.3 Formal Project Objectives &amp; Scope</span>
        <span class="toc-page">Page 4</span>
    </li>
    
    <li class="toc-item level-1">
        <span>2. Formal Language Grammar &amp; Concrete Syntax</span>
        <span class="toc-page">Page 4</span>
    </li>
    <li class="toc-item level-2">
        <span>2.1 Lexical Grammar &amp; Token Structure</span>
        <span class="toc-page">Page 4</span>
    </li>
    <li class="toc-item level-2">
        <span>2.2 Concrete Syntax in Extended Backus-Naur Form (EBNF)</span>
        <span class="toc-page">Page 5</span>
    </li>

    <li class="toc-item level-1">
        <span>3. Type System, Collections &amp; Value Semantics</span>
        <span class="toc-page">Page 6</span>
    </li>
    <li class="toc-item level-2">
        <span>3.1 Primitive Types &amp; Invariant Semantics</span>
        <span class="toc-page">Page 6</span>
    </li>
    <li class="toc-item level-2">
        <span>3.2 Collection Types &amp; The Deep-Copy Value Semantics Invariant</span>
        <span class="toc-page">Page 6</span>
    </li>
    <li class="toc-item level-2">
        <span>3.3 Scoping, Immutability &amp; Binding Rules</span>
        <span class="toc-page">Page 7</span>
    </li>

    <li class="toc-item level-1">
        <span>4. Compiler Subsystem Architecture</span>
        <span class="toc-page">Page 7</span>
    </li>
    <li class="toc-item level-2">
        <span>4.1 Multi-Stage Pipeline Overview</span>
        <span class="toc-page">Page 7</span>
    </li>
    <li class="toc-item level-2">
        <span>4.2 Lexer Subsystem (<code>cmm/lexer.py</code>)</span>
        <span class="toc-page">Page 8</span>
    </li>
    <li class="toc-item level-2">
        <span>4.3 Parser &amp; Abstract Syntax Tree (<code>cmm/parser.py</code>, <code>ast_nodes.py</code>)</span>
        <span class="toc-page">Page 8</span>
    </li>
    <li class="toc-item level-2">
        <span>4.4 Semantic Analysis &amp; Symbol Scopes (<code>cmm/analyzer.py</code>)</span>
        <span class="toc-page">Page 9</span>
    </li>

    <li class="toc-item level-1">
        <span>5. Dual Execution Backends</span>
        <span class="toc-page">Page 10</span>
    </li>
    <li class="toc-item level-2">
        <span>5.1 Reference AST Interpreter (<code>cmm/interpreter.py</code>)</span>
        <span class="toc-page">Page 10</span>
    </li>
    <li class="toc-item level-2">
        <span>5.2 ISO C99 Code Generator (<code>cmm/codegen_c.py</code>)</span>
        <span class="toc-page">Page 10</span>
    </li>

    <li class="toc-item level-1">
        <span>6. Human-Centric Error Diagnostic &amp; Guidance System</span>
        <span class="toc-page">Page 11</span>
    </li>
    <li class="toc-item level-2">
        <span>6.1 The 60-Code Diagnostic Taxonomy</span>
        <span class="toc-page">Page 11</span>
    </li>
    <li class="toc-item level-2">
        <span>6.2 3-Line Error Gutter &amp; Levenshtein Typo Suggestions</span>
        <span class="toc-page">Page 11</span>
    </li>

    <li class="toc-item level-1">
        <span>7. Security Threat Modeling &amp; CWE Mitigation Matrix</span>
        <span class="toc-page">Page 12</span>
    </li>

    <li class="toc-item level-1">
        <span>8. Comprehensive Language Feature Showcase (All Language Features)</span>
        <span class="toc-page">Page 13</span>
    </li>
    <li class="toc-item level-2">
        <span>8.1 Module Structure, Typed Functions &amp; Recursion</span>
        <span class="toc-page">Page 13</span>
    </li>
    <li class="toc-item level-2">
        <span>8.2 Primitives, Immutability &amp; Checked Arithmetic</span>
        <span class="toc-page">Page 13</span>
    </li>
    <li class="toc-item level-2">
        <span>8.3 Strings, Escape Sequences &amp; Indexing</span>
        <span class="toc-page">Page 14</span>
    </li>
    <li class="toc-item level-2">
        <span>8.4 Fixed-Size Arrays &amp; Dynamic Lists</span>
        <span class="toc-page">Page 14</span>
    </li>
    <li class="toc-item level-2">
        <span>8.5 LIFO Stacks &amp; FIFO Queues</span>
        <span class="toc-page">Page 15</span>
    </li>
    <li class="toc-item level-2">
        <span>8.6 Deep-Copy Value Semantics Verification</span>
        <span class="toc-page">Page 15</span>
    </li>
    <li class="toc-item level-2">
        <span>8.7 Multi-Branch Switch-Case &amp; Iteration Constructs</span>
        <span class="toc-page">Page 16</span>
    </li>
    <li class="toc-item level-2">
        <span>8.8 Lexical Scoping, Standard Library &amp; Output Trace</span>
        <span class="toc-page">Page 16</span>
    </li>

    <li class="toc-item level-1">
        <span>9. Discussion, Limitations &amp; Future Roadmap</span>
        <span class="toc-page">Page 17</span>
    </li>
    <li class="toc-item level-1">
        <span>10. Conclusion &amp; Academic References</span>
        <span class="toc-page">Page 18</span>
    </li>
</ul>

<div class="page-break"></div>

<!-- ========================================================================
     CHAPTER 1: INTRODUCTION & MOTIVATION
     ======================================================================== -->
<h1 class="chapter-title">1. Introduction &amp; Motivation ("Safety by Removal")</h1>

<h2 class="section-title">1.1 The Systems Programming Memory Crisis &amp; CWE Taxonomy</h2>
<p class="lead">
    For half a century, the programming language C has maintained undisputed supremacy across operating system kernels, embedded hardware, network protocol stacks, and high-performance computing runtimes. Yet, this widespread deployment has come at catastrophic security costs.
</p>
<p>
    According to longitudinal security audits conducted by Microsoft Security Response Center (MSRC) and Google Chromium engineering teams, approximately <strong>70% of all severe security vulnerabilities</strong> discovered in production codebases stem directly from memory safety violations. In traditional C, pointers are unmanaged physical memory addresses; arrays decay silently into raw pointers without bounds tracking; variables possess indeterminate garbage values prior to explicit assignment; and arithmetic operations trigger silent undefined behavior upon overflow or signed integer wrap-around.
</p>

<p>
    These fundamental vulnerabilities are formalized in the MITRE Common Weakness Enumeration (CWE) database:
</p>

<table class="academic-table">
    <thead>
        <tr>
            <th style="width: 15%;">CWE Identifier</th>
            <th style="width: 30%;">Vulnerability Description</th>
            <th style="width: 30%;">Root Cause in ISO C</th>
            <th style="width: 25%;">C-- Architectural Solution</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td class="font-mono bold">CWE-119</td>
            <td>Improper Restriction of Operations within Bounds of a Memory Buffer</td>
            <td>Zero bounds checking on pointer offset operations; array decay.</td>
            <td><span class="badge badge-safe">Guaranteed</span> Strictly bound-checked collections (Arrays, Lists, Strings).</td>
        </tr>
        <tr>
            <td class="font-mono bold">CWE-476</td>
            <td>NULL Pointer Dereference</td>
            <td>Nullable pointers permitted anywhere; unchecked runtime access.</td>
            <td><span class="badge badge-safe">Eliminated</span> Total removal of pointers and NULL concepts.</td>
        </tr>
        <tr>
            <td class="font-mono bold">CWE-190</td>
            <td>Integer Overflow or Wraparound</td>
            <td>Signed overflow triggers undefined behavior; silent wraparound.</td>
            <td><span class="badge badge-safe">Guaranteed</span> 64-bit checked arithmetic with division-by-zero catch.</td>
        </tr>
        <tr>
            <td class="font-mono bold">CWE-457</td>
            <td>Use of Uninitialized Variable</td>
            <td>Stack allocation allocates raw memory containing arbitrary garbage.</td>
            <td><span class="badge badge-safe">Eliminated</span> Mandatory initialization on declaration enforced by compiler.</td>
        </tr>
        <tr>
            <td class="font-mono bold">CWE-416</td>
            <td>Use After Free</td>
            <td>Manual allocation (<code>malloc</code>/<code>free</code>) and multiple alias references.</td>
            <td><span class="badge badge-safe">Eliminated</span> Deep-copy value semantics; zero manual memory allocation.</td>
        </tr>
    </tbody>
</table>

<h2 class="section-title">1.2 The "Safety by Removal" Paradigm</h2>
<p>
    Existing modern efforts to resolve memory safety have primarily pursued <em>Safety by Verification</em>. Languages like Rust introduce advanced type systems featuring affine types, borrow checkers, lifetimes, and ownership invariants. While theoretically sound, this approach introduces steep cognitive barriers, dramatically slowing software development cycles and overwhelming novice and undergraduate students.
</p>
<p>
    In contrast, <strong>C-- pioneers the philosophy of "Safety by Removal":</strong>
</p>
<div class="callout callout-info">
    <div class="callout-title">Core Axiom of C-- Design</div>
    <em>"If a language feature is the historical source of undefined behavior, memory corruption, or developer confusion, that feature is not patched—it is completely removed from the grammar."</em>
</div>
<p>
    By stripping out raw pointers, address-of operators (<code>&amp;</code>), pointer dereferencing (<code>*</code>), null references, manual heap management (<code>malloc</code>, <code>free</code>), and implicit type conversions, C-- retains the familiar syntax and predictable control-flow of C while guaranteeing mathematical memory safety at both compile-time and runtime.
</p>

<h2 class="section-title">1.3 Formal Project Objectives &amp; Scope</h2>
<p>
    The primary objectives of the C-- v0.2.0 engineering project are:
</p>
<ol>
    <li><strong>Syntax &amp; Grammar:</strong> To implement a clean, unambiguous grammar combining C's procedural clarity with modern features (modules, first-class functions, fixed arrays, dynamic lists, LIFO stacks, FIFO queues, and multi-branch switch statements).</li>
    <li><strong>Exhaustive Semantic Analysis:</strong> To build a hierarchical symbol table resolving variable declarations, strict mutability tracking (<code>let</code> vs <code>mut</code>), type consistency, and exhaustive return paths.</li>
    <li><strong>Dual Execution Backends:</strong> To deliver both a high-fidelity reference AST tree-walking interpreter and an optimizing C99 transpiler that outputs hardened, portable C source code.</li>
    <li><strong>Pedagogical Diagnostics:</strong> To introduce human-centric compiler error reporting with an ANSI source gutter, "What went wrong", "How to fix", and fuzzy typo correction.</li>
    <li><strong>Interactive Web Studio &amp; Explorer:</strong> To provide a zero-installation, browser-based compiler studio allowing immediate code experimentation, AST visualization, token inspection, and live C99 transpilation.</li>
    <li><strong>Empirical Verification:</strong> To validate the compiler against 417 automated test cases with 100% code correctness.</li>
</ol>

<div class="tip-box" style="margin-top: 15px;">
    <strong>Verified Project Deliverables &amp; Online Resources:</strong>
    <ul style="margin: 6px 0 0 18px; padding: 0; line-height: 1.6;">
        <li><strong>Open-Source Repository:</strong> <a href="https://github.com/ronitmexson2924/C--" target="_blank">https://github.com/ronitmexson2924/C--</a></li>
        <li><strong>Live Cloud Deployment &amp; Web Studio:</strong> <a href="https://web-production-c8ddc.up.railway.app" target="_blank">https://web-production-c8ddc.up.railway.app</a></li>
        <li><strong>Automated Test Suite:</strong> 417 passing test cases verifying 100% specification compliance.</li>
    </ul>
</div>

<div class="page-break"></div>

<!-- ========================================================================
     CHAPTER 2: FORMAL GRAMMAR & SYNTACTIC SPECIFICATION
     ======================================================================== -->
<h1 class="chapter-title">2. Formal Language Grammar &amp; Concrete Syntax</h1>

<h2 class="section-title">2.1 Lexical Grammar &amp; Token Structure</h2>
<p>
    Source files in C-- use the UTF-8 encoding scheme and the normative file extension <code>.cmm</code>. The lexical analyzer divides input streams into deterministic tokens defined by explicit regular expressions.
</p>
<table class="academic-table">
    <thead>
        <tr>
            <th style="width: 20%;">Token Category</th>
            <th style="width: 35%;">Lexical Pattern / Values</th>
            <th style="width: 45%;">Semantic Description</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>Whitespace &amp; Comments</strong></td>
            <td><code>[ \t\r\n]+</code><br><code>// [^\n]*</code><br><code>/* ... */</code></td>
            <td>Whitespace separates tokens. Line comments start with <code>//</code>. Block comments start with <code>/*</code> and terminate with <code>*/</code>. Nesting is disallowed.</td>
        </tr>
        <tr>
            <td><strong>Identifiers</strong></td>
            <td><code>[a-zA-Z_][a-zA-Z0-9_]*</code></td>
            <td>Case-sensitive identifiers. Cannot match reserved keywords. Cannot begin with digits.</td>
        </tr>
        <tr>
            <td><strong>Keywords (22 total)</strong></td>
            <td><code>module, fn, return, let, mut, if, else, while, do, for, switch, case, default, break, int, float, bool, string, array, list, stack, queue</code></td>
            <td>Reserved syntactic anchors. Any use as a variable or function name triggers a descriptive syntax error.</td>
        </tr>
        <tr>
            <td><strong>Integer Literals</strong></td>
            <td><code>0|[1-9][0-9]*</code></td>
            <td>64-bit signed decimal integers. Non-zero values must not contain leading zeroes.</td>
        </tr>
        <tr>
            <td><strong>Float Literals</strong></td>
            <td><code>[0-9]+\.[0-9]+</code></td>
            <td>64-bit IEEE 754 double-precision floating-point values.</td>
        </tr>
        <tr>
            <td><strong>String Literals</strong></td>
            <td>Double-quoted &amp; Triple-quoted</td>
            <td>Double-quoted strings support escapes (\\n, \\t, \\", \\\\). Triple-quoted multiline strings preserve verbatim formatting.</td>
        </tr>
        <tr>
            <td><strong>Boolean Literals</strong></td>
            <td><code>true | false</code></td>
            <td>Canonical boolean values.</td>
        </tr>
    </tbody>
</table>

<h2 class="section-title">2.2 Concrete Syntax in Extended Backus-Naur Form (EBNF)</h2>
<p>
    The syntax of C-- v0.2.0 is defined normatively by the following EBNF grammar:
</p>
<pre class="code-block">
<span class="token-comment">(* ================= Program &amp; Declarations ================= *)</span>
Program          ::= ModuleDecl? FunctionDecl*
ModuleDecl       ::= <span class="token-kw">"module"</span> IDENTIFIER <span class="token-kw">";"</span>
FunctionDecl     ::= <span class="token-kw">"fn"</span> IDENTIFIER <span class="token-kw">"("</span> ParameterList? <span class="token-kw">")"</span> (<span class="token-kw">"-&gt;"</span> Type)? Block
ParameterList    ::= Parameter (<span class="token-kw">","</span> Parameter)*
Parameter        ::= IDENTIFIER <span class="token-kw">":"</span> Type

<span class="token-comment">(* ================= Type System Productions ================= *)</span>
Type             ::= PrimitiveType | CollectionType
PrimitiveType    ::= <span class="token-type">"int"</span> | <span class="token-type">"float"</span> | <span class="token-type">"bool"</span> | <span class="token-type">"string"</span>
CollectionType   ::= (<span class="token-type">"array"</span> | <span class="token-type">"list"</span> | <span class="token-type">"stack"</span> | <span class="token-type">"queue"</span>) <span class="token-kw">"&lt;"</span> Type <span class="token-kw">"&gt;"</span>

<span class="token-comment">(* ================= Statements ================= *)</span>
Statement        ::= VarDecl | Assignment | IfStmt | WhileStmt | DoWhileStmt 
                   | ForStmt | SwitchStmt | ReturnStmt | ExprStmt | Block
VarDecl          ::= (<span class="token-kw">"let"</span> | <span class="token-kw">"mut"</span>) IDENTIFIER (<span class="token-kw">":"</span> Type)? <span class="token-kw">"="</span> Expr <span class="token-kw">";"</span>
Assignment       ::= Target <span class="token-kw">"="</span> Expr <span class="token-kw">";"</span>
Target           ::= IDENTIFIER (<span class="token-kw">"["</span> Expr <span class="token-kw">"]"</span>)*
IfStmt           ::= <span class="token-kw">"if"</span> <span class="token-kw">"("</span> Expr <span class="token-kw">")"</span> Block (<span class="token-kw">"else"</span> <span class="token-kw">"if"</span> <span class="token-kw">"("</span> Expr <span class="token-kw">")"</span> Block)* (<span class="token-kw">"else"</span> Block)?
WhileStmt        ::= <span class="token-kw">"while"</span> <span class="token-kw">"("</span> Expr <span class="token-kw">")"</span> Block
DoWhileStmt      ::= <span class="token-kw">"do"</span> Block <span class="token-kw">"while"</span> <span class="token-kw">"("</span> Expr <span class="token-kw">")"</span> <span class="token-kw">";"</span>
ForStmt          ::= <span class="token-kw">"for"</span> <span class="token-kw">"("</span> VarDecl Expr <span class="token-kw">";"</span> Assignment <span class="token-kw">")"</span> Block
SwitchStmt       ::= <span class="token-kw">"switch"</span> <span class="token-kw">"("</span> Expr <span class="token-kw">")"</span> <span class="token-kw">"{"</span> CaseClause* DefaultClause? <span class="token-kw">"}"</span>
CaseClause       ::= <span class="token-kw">"case"</span> Expr <span class="token-kw">":"</span> Statement* <span class="token-kw">"break"</span> <span class="token-kw">";"</span>
DefaultClause    ::= <span class="token-kw">"default"</span> <span class="token-kw">":"</span> Statement* (<span class="token-kw">"break"</span> <span class="token-kw">";"</span>)?
ReturnStmt       ::= <span class="token-kw">"return"</span> Expr? <span class="token-kw">";"</span>
Block            ::= <span class="token-kw">"{"</span> Statement* <span class="token-kw">"}"</span>

<span class="token-comment">(* ================= Expressions &amp; Precedence ================= *)</span>
Expr             ::= LogicalOr
LogicalOr        ::= LogicalAnd (<span class="token-kw">"||"</span> LogicalAnd)*
LogicalAnd       ::= Equality (<span class="token-kw">"&amp;&amp;"</span> Equality)*
Equality         ::= Relational ((<span class="token-kw">"=="</span> | <span class="token-kw">"!="</span>) Relational)*
Relational       ::= Additive ((<span class="token-kw">"&lt;"</span> | <span class="token-kw">"&lt;="</span> | <span class="token-kw">"&gt;"</span> | <span class="token-kw">"&gt;="</span>) Additive)*
Additive         ::= Multiplicative ((<span class="token-kw">"+"</span> | <span class="token-kw">"-"</span>) Multiplicative)*
Multiplicative   ::= Unary ((<span class="token-kw">"*"</span> | <span class="token-kw">"/"</span> | <span class="token-kw">"%"</span>) Unary)*
Unary            ::= (<span class="token-kw">"-"</span> | <span class="token-kw">"!"</span>) Unary | Postfix
Postfix          ::= Primary (<span class="token-kw">"["</span> Expr <span class="token-kw">"]"</span> | <span class="token-kw">"."</span> IDENTIFIER <span class="token-kw">"("</span> ArgList? <span class="token-kw">")"</span> | <span class="token-kw">"("</span> ArgList? <span class="token-kw">")"</span>)*
Primary          ::= IDENTIFIER | INT_LIT | FLOAT_LIT | STRING_LIT | <span class="token-kw">"true"</span> | <span class="token-kw">"false"</span> 
                   | ArrayLiteral | CollectionCtor | <span class="token-kw">"("</span> Expr <span class="token-kw">")"</span>
</pre>

<div class="page-break"></div>

<!-- ========================================================================
     CHAPTER 3: TYPE SYSTEM, COLLECTIONS & VALUE SEMANTICS
     ======================================================================== -->
<h1 class="chapter-title">3. Type System, Collections &amp; Value Semantics</h1>

<h2 class="section-title">3.1 Primitive Types &amp; Invariant Semantics</h2>
<p class="lead">
    C-- features a static, manifest-or-inferred type system with zero implicit coercion across distinct types (with the deliberate exception of integer widening to float in mixed arithmetic operations, e.g., <code>int + float &rarr; float</code>).
</p>

<h3>Primitive Types</h3>
<ul>
    <li><code>int</code>: 64-bit signed two's complement integer (−2<sup>63</sup> to 2<sup>63</sup> − 1). Truncates toward zero on integer division.</li>
    <li><code>float</code>: 64-bit IEEE 754 double-precision floating-point number.</li>
    <li><code>bool</code>: Boolean truth value (<code>true</code> or <code>false</code>). No integer-to-boolean coercion.</li>
    <li><code>string</code>: Immutable UTF-8 byte sequence supporting indexing, length query, and concatenation.</li>
</ul>

<h2 class="section-title">3.2 Collection Types &amp; The Deep-Copy Value Semantics Invariant</h2>
<p>
    A central architectural innovation of C-- is the elimination of aliasing bugs through <strong>deep-copy value semantics</strong>:
</p>
<div class="callout callout-success">
    <div class="callout-title">The Value Semantics Guarantee</div>
    In C--, collections behave exactly like primitive integers. Whenever a collection is assigned to another variable (<code>mut b = a;</code>) or passed into a function as an argument, a complete deep copy of the underlying data structure is generated. Mutations performed on <code>b</code> can never inadvertently mutate <code>a</code>.
</div>

<table class="academic-table">
    <thead>
        <tr>
            <th style="width: 18%;">Collection Kind</th>
            <th style="width: 22%;">Constructor Syntax</th>
            <th style="width: 35%;">Supported Methods &amp; Operations</th>
            <th style="width: 25%;">Runtime Complexity</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td class="font-mono bold">array&lt;T&gt;</td>
            <td><code>[1, 2, 3]</code> or<br><code>array&lt;int&gt;(size, fill)</code></td>
            <td><code>arr[i]</code> (read/write), <code>arr.len()</code></td>
            <td>O(1) random access, bounds-checked</td>
        </tr>
        <tr>
            <td class="font-mono bold">list&lt;T&gt;</td>
            <td><code>list&lt;T&gt;()</code></td>
            <td><code>.push(v)</code>, <code>.pop()</code>, <code>.insert(i, v)</code>, <code>.remove(i)</code>, <code>.contains(v)</code>, <code>.clear()</code>, <code>.len()</code></td>
            <td>Amortized O(1) append/pop; O(N) insert/remove</td>
        </tr>
        <tr>
            <td class="font-mono bold">stack&lt;T&gt;</td>
            <td><code>stack&lt;T&gt;()</code></td>
            <td><code>.push(v)</code>, <code>.pop()</code>, <code>.peek()</code>, <code>.is_empty()</code>, <code>.len()</code></td>
            <td>Strict LIFO discipline; O(1) operations</td>
        </tr>
        <tr>
            <td class="font-mono bold">queue&lt;T&gt;</td>
            <td><code>queue&lt;T&gt;()</code></td>
            <td><code>.enqueue(v)</code>, <code>.dequeue()</code>, <code>.peek()</code>, <code>.is_empty()</code>, <code>.len()</code></td>
            <td>Strict FIFO discipline; O(1) operations</td>
        </tr>
    </tbody>
</table>

<h2 class="section-title">3.3 Scoping, Immutability &amp; Binding Rules</h2>
<p>
    Variables in C-- are declared using either <code>let</code> (immutable binding) or <code>mut</code> (mutable binding). 
</p>
<ul>
    <li><strong>Mandatory Initialization:</strong> A variable cannot be declared without an assignment expression (e.g., <code>let x: int;</code> is rejected with error <code>S001</code>). This eliminates uninitialized memory garbage (CWE-457).</li>
    <li><strong>Immutability by Default:</strong> Assigning to an immutable variable declared with <code>let</code> triggers a compile-time semantic error (<code>E003</code>).</li>
    <li><strong>Lexical Block Scoping:</strong> Scopes are created by curly brace blocks. Inner blocks can shadow outer variables with distinct types; however, redeclaring a variable within the identical scope is illegal (<code>E002</code>).</li>
</ul>

<div class="page-break"></div>

<!-- ========================================================================
     CHAPTER 4: COMPILER SUBSYSTEM ARCHITECTURE
     ======================================================================== -->
<h1 class="chapter-title">4. Compiler Subsystem Architecture</h1>

<h2 class="section-title">4.1 Multi-Stage Pipeline Overview</h2>
<p class="lead">
    The C-- compiler pipeline is structured as an end-to-end multi-pass system. The modular pipeline separates lexical analysis, syntactic parsing, semantic validation, and target backend generation into clean, testable layers.
</p>

<div class="diagram-box">
    <div style="font-weight: 700; font-size: 8.5pt; color: #475569; text-transform: uppercase; margin-bottom: 8px;">
        Figure 4.1: C-- Compilation and Target Backend Pipeline
    </div>
    <div class="pipeline-flow">
        <div class="pipeline-node">
            <div class="title">Source (.cmm)</div>
            <div class="desc">UTF-8 File</div>
        </div>
        <div class="pipeline-arrow">&rarr;</div>
        <div class="pipeline-node">
            <div class="title">Lexer</div>
            <div class="desc">Tokens + Col/Line</div>
        </div>
        <div class="pipeline-arrow">&rarr;</div>
        <div class="pipeline-node">
            <div class="title">Parser</div>
            <div class="desc">Typed AST</div>
        </div>
        <div class="pipeline-arrow">&rarr;</div>
        <div class="pipeline-node">
            <div class="title">Semantic Analyzer</div>
            <div class="desc">Scope &amp; Type Check</div>
        </div>
        <div class="pipeline-arrow">&rarr;</div>
        <div class="pipeline-node" style="border-color: #10b981;">
            <div class="title">Dual Backends</div>
            <div class="desc">Interpreter / C99 Gen</div>
        </div>
    </div>
</div>

<h2 class="section-title">4.2 Lexer Subsystem (<code>cmm/lexer.py</code>)</h2>
<p>
    The lexical scanner converts raw source code into an ordered sequence of <code>Token</code> objects. Each token tracks line and column coordinates, raw lexeme text, and span length for pinpoint underline rendering in diagnostics.
</p>

<h2 class="section-title">4.3 Parser &amp; Abstract Syntax Tree (<code>cmm/parser.py</code>, <code>ast_nodes.py</code>)</h2>
<p>
    Syntactic parsing is performed via LL(k) recursive descent with Pratt-style precedence climbing for binary expressions. The parser enforces unambiguous operator binding across 10 precedence tiers, from primary grouping to assignment.
</p>
<p>
    The resulting Abstract Syntax Tree (AST) consists of strictly typed, immutable Python dataclasses rooted in <code>ProgramNode</code>.
</p>

<h2 class="section-title">4.4 Semantic Analysis &amp; Symbol Scopes (<code>cmm/analyzer.py</code>)</h2>
<p>
    The semantic analyzer validates code invariants prior to execution or code generation:
</p>
<ul>
    <li><strong>Hierarchical Symbol Tables:</strong> Managed by <code>Scope</code> objects that link to parent scopes. Identifiers are resolved outward from innermost block to global module scope.</li>
    <li><strong>Exhaustive Return-Path Analysis:</strong> Non-void functions are analyzed through control flow graph walking to guarantee that all execution paths culminate in an explicit <code>return</code> statement of the declared type (rejecting missing paths with <code>E021</code>).</li>
    <li><strong>Function Call Signature Checking:</strong> Validates argument count (<code>E019</code>, <code>E020</code>) and argument types against parameter definitions.</li>
    <li><strong>Recursion Safeguards:</strong> Static detection of circular call paths and depth limits.</li>
</ul>

<div class="page-break"></div>

<!-- ========================================================================
     CHAPTER 5: DUAL EXECUTION BACKENDS
     ======================================================================== -->
<h1 class="chapter-title">5. Dual Execution Backends</h1>

<h2 class="section-title">5.1 Reference AST Interpreter (<code>cmm/interpreter.py</code>)</h2>
<p class="lead">
    The reference interpreter provides immediate evaluation of C-- programs without intermediate compilation tools. It acts as the normative ground truth for the language specification.
</p>
<p>
    Key execution characteristics of the interpreter include:
</p>
<ul>
    <li><strong>Environment Stack Frames:</strong> Each function invocation pushes an isolated activation record holding local variable bindings. Upon return, the frame is popped, reclaiming scope memory.</li>
    <li><strong>Recursion Depth Limitation:</strong> To prevent host Python stack overflows, the C-- runtime enforces a strict limit of <strong>10,000 recursive frames</strong>. Exceeding this boundary triggers diagnostic <code>R014</code> (Recursion Limit Exceeded) with a clean stack trace rather than an unhandled crash.</li>
    <li><strong>Collection Runtime:</strong> All collections (arrays, lists, stacks, queues) are backed by Python structures that undergo deep cloning upon assignment or parameter passing. Index bounds are verified on every access, raising <code>R002</code> on out-of-bounds attempts.</li>
    <li><strong>Integrated Standard Library:</strong> Native runtime routines for console I/O (<code>print</code>, <code>println</code>), string conversions (<code>parse_int</code>, <code>parse_float</code>), and user keyboard input (<code>read_int</code>, <code>read_string</code>).</li>
</ul>

<h2 class="section-title">5.2 ISO C99 Code Generator (<code>cmm/codegen_c.py</code>)</h2>
<p>
    For high-performance native execution, C-- includes an optimizing code generator that transpiles safe C-- AST structures directly into standard ISO C99.
</p>
<div class="callout callout-info">
    <div class="callout-title">The C99 Runtime Emulation Engine (cmm_runtime.h)</div>
    The transpiler injects a specialized header containing type-safe wrappers for dynamic arrays, collections, and checked arithmetic. Pointers in generated C are strictly encapsulated inside vector descriptors; user code never manipulates raw pointers.
</div>

<div class="page-break"></div>

<!-- ========================================================================
     CHAPTER 6: HUMAN-CENTRIC DIAGNOSTICS & GUIDANCE
     ======================================================================== -->
<h1 class="chapter-title">6. Human-Centric Error Diagnostic &amp; Guidance System</h1>

<h2 class="section-title">6.1 The 60-Code Diagnostic Taxonomy</h2>
<p class="lead">
    Traditional compiler error messages (such as <code>gcc</code>'s infamous <em>"segmentation fault (core dumped)"</em> or <code>rustc</code>'s complex borrow-checker lifespans) frequently confuse students and developers. C-- treats compiler errors as pedagogical teaching moments.
</p>
<p>
    Every error generated by C-- is assigned a permanent, unique diagnostic code across five distinct sub-categories:
</p>
<ul>
    <li><strong>Lexical Diagnostics (L001 – L012):</strong> Unterminated strings, invalid numeric literals, unclosed block comments, unrecognized characters.</li>
    <li><strong>Syntax Diagnostics (S001 – S004):</strong> Missing semicolons, unmatched parentheses/brackets, unexpected keywords.</li>
    <li><strong>Semantic Diagnostics (E001 – E031):</strong> Use before declaration, assigning to immutable <code>let</code>, type mismatches, missing return paths, collection type inconsistencies.</li>
    <li><strong>Runtime Diagnostics (R001 – R014):</strong> Division by zero, index out of bounds, stack underflow, queue underflow, recursion depth limit exceeded.</li>
    <li><strong>Transpilation Diagnostics (T001):</strong> Target C99 code generation anomalies.</li>
</ul>

<h2 class="section-title">6.2 3-Line Error Gutter &amp; Levenshtein Typo Suggestions</h2>
<p>
    Diagnostics are rendered using an ANSI 3-line terminal gutter that pinpoints the exact line and column, underlines the offending token span, explains root causes in plain language, and provides concrete remediation steps:
</p>

<div class="gutter-mockup">
<span class="gutter-red">Error [E001]:</span> Use of undeclared variable 'counter'<br>
<span class="gutter-cyan">  --&gt;</span> src/main.cmm:14:9<br>
<span class="gutter-cyan">   |</span><br>
<span class="gutter-cyan">14 |</span>     mut total = counter + 10;<br>
<span class="gutter-cyan">   |</span>                 <span class="gutter-red">^^^^^^^</span><br>
<span class="gutter-cyan">   |</span><br>
<span class="gutter-green">Did you mean:</span> 'count'? (Defined at src/main.cmm:4:5)<br>
<br>
<span class="gutter-cyan">What went wrong:</span> Variable 'counter' is referenced before being declared.<br>
<span class="gutter-green">How to fix:</span> Declare 'counter' with 'let' or 'mut' before this line, or fix spelling.
</div>

<p>
    When an unrecognized identifier is encountered, the compiler executes an optimized <strong>Levenshtein Distance Algorithm</strong> comparing the misspelled token against all active symbols in the current scope. If a candidate matches with an edit distance &le; 2, the compiler generates a <em>"Did you mean?"</em> suggestion.
</p>

<div class="page-break"></div>

<!-- ========================================================================
     CHAPTER 7: SECURITY THREAT MODELING & CWE MITIGATION
     ======================================================================== -->
<h1 class="chapter-title">7. Security Threat Modeling &amp; CWE Mitigation Matrix</h1>

<p class="lead">
    To rigorously assess the safety guarantees of C--, we analyze how the language architecture eliminates the top five most prevalent systems programming vulnerabilities cataloged by MITRE and SANS.
</p>

<table class="academic-table">
    <thead>
        <tr>
            <th style="width: 20%;">Security Concern</th>
            <th style="width: 26%;">Standard C (ISO C99/C11)</th>
            <th style="width: 26%;">Rust</th>
            <th style="width: 28%;">C-- (C Minus Minus)</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>Spatial Memory Safety<br>(Buffer Overflows)</strong></td>
            <td><span class="badge badge-vuln">Vulnerable</span><br>Arrays decay to unchecked pointers. Arbitrary memory indexing permitted.</td>
            <td><span class="badge badge-safe">Safe</span><br>Enforced through slices and compile-time borrow checks.</td>
            <td><span class="badge badge-safe">Safe (By Design)</span><br>Pointers removed. All array/list indexing verified with runtime bounds checks.</td>
        </tr>
        <tr>
            <td><strong>Temporal Memory Safety<br>(Use-After-Free)</strong></td>
            <td><span class="badge badge-vuln">Vulnerable</span><br>Manual <code>free()</code> leaves dangling pointers in memory.</td>
            <td><span class="badge badge-safe">Safe</span><br>Lifetimes and affine type ownership system prevent reuse.</td>
            <td><span class="badge badge-safe">Safe (By Design)</span><br>Manual allocation removed. Deep-copy value semantics eliminate aliases.</td>
        </tr>
        <tr>
            <td><strong>Null Pointer Dereferences</strong></td>
            <td><span class="badge badge-vuln">Vulnerable</span><br><code>NULL</code> is legal for any pointer type; triggers crash or exploit.</td>
            <td><span class="badge badge-safe">Safe</span><br><code>Option&lt;T&gt;</code> monad replaces raw null values.</td>
            <td><span class="badge badge-safe">Safe (By Design)</span><br>Total removal of NULL. All variables must be initialized on declaration.</td>
        </tr>
        <tr>
            <td><strong>Integer Overflows &amp; Wraparounds</strong></td>
            <td><span class="badge badge-vuln">Undefined Behavior</span><br>Signed integer overflow triggers compiler-level UB optimizations.</td>
            <td><span class="badge badge-safe">Safe in Debug</span><br>Panics in debug mode; wraps in release mode by default.</td>
            <td><span class="badge badge-safe">Safe (By Design)</span><br>64-bit checked arithmetic. Division by zero trapped with clean diagnostic.</td>
        </tr>
        <tr>
            <td><strong>Concurrency Data Races</strong></td>
            <td><span class="badge badge-vuln">Vulnerable</span><br>Shared mutable pointer access without synchronization.</td>
            <td><span class="badge badge-safe">Safe</span><br><code>Send</code> and <code>Sync</code> traits checked at compile time.</td>
            <td><span class="badge badge-safe">Safe (By Design)</span><br>Deep-copy semantics prevent shared mutable state across call frames.</td>
        </tr>
    </tbody>
</table>

<div class="callout callout-security">
    <div class="callout-title">Theoretical Security Proof Summary</div>
    Because C--'s operational semantics completely omit memory addressing operators (&amp; and *), heap deallocation directives (free), and null pointer constants, the language provides an inductive guarantee that <strong>no valid C-- program can produce a segmentation fault, memory leakage, buffer overflow, or dangling reference</strong> during execution.
</div>

<div class="page-break"></div>

<!-- ========================================================================
     CHAPTER 8: COMPREHENSIVE LANGUAGE FEATURE SHOWCASE
     ======================================================================== -->
<h1 class="chapter-title">8. Comprehensive Language Feature Showcase</h1>

<p class="lead">
    This chapter presents an exhaustive demonstration of <strong>every feature</strong> engineered into C-- v0.2.0. Drawing directly from the verified 395-line program <code>demo.cmm</code>, each subsection presents the syntactic design, execution model, and verified runtime behavior.
</p>

<h2 class="section-title">8.1 Module Structure, Typed Functions &amp; Recursion</h2>
<p>
    C-- programs begin with an explicit <code>module</code> declaration. Functions specify typed parameters and explicit return types using arrow syntax (<code>-&gt; Type</code>). Functions without a return type are void procedures. Call frames support safe recursion up to the 10,000-frame safeguard.
</p>
<pre class="code-block">
<span class="token-kw">module</span> main;

<span class="token-comment">// Pure binary function</span>
<span class="token-kw">fn</span> add(a: <span class="token-type">int</span>, b: <span class="token-type">int</span>) -&gt; <span class="token-type">int</span> {
    <span class="token-kw">return</span> a + b;
}

<span class="token-comment">// Recursive factorial demonstrating call stack safety</span>
<span class="token-kw">fn</span> factorial(n: <span class="token-type">int</span>) -&gt; <span class="token-type">int</span> {
    <span class="token-kw">if</span> (n &lt;= 1) {
        <span class="token-kw">return</span> 1;
    }
    <span class="token-kw">return</span> n * factorial(n - 1);
}

<span class="token-comment">// Void procedure with early guard return</span>
<span class="token-kw">fn</span> greet(name: <span class="token-type">string</span>, is_vip: <span class="token-type">bool</span>) {
    <span class="token-kw">if</span> (is_vip) {
        print(<span class="token-str">"Welcome, honored VIP:"</span>);
        print(name);
        <span class="token-kw">return</span>;
    }
    print(<span class="token-str">"Welcome:"</span>);
    print(name);
}
</pre>

<h2 class="section-title">8.2 Primitives, Immutability &amp; Checked Arithmetic</h2>
<p>
    Variables default to immutability via <code>let</code> and require <code>mut</code> for reassignment. All declarations must be initialized. Arithmetic prevents undefined behavior: integer division truncates toward zero, and mixed expressions automatically widen integers to floats.
</p>
<pre class="code-block">
<span class="token-kw">let</span> message: <span class="token-type">string</span> = <span class="token-str">"Hello, C-- v0.2.0!"</span>;
<span class="token-kw">let</span> count: <span class="token-type">int</span> = 42;
<span class="token-kw">let</span> pi: <span class="token-type">float</span> = 3.14159;
<span class="token-kw">let</span> is_active: <span class="token-type">bool</span> = <span class="token-kw">true</span>;

<span class="token-kw">mut</span> counter: <span class="token-type">int</span> = 10;
counter = counter + 5; <span class="token-comment">// Legal reassignment on mut</span>

<span class="token-comment">// Truncating integer division &amp; automatic widening</span>
<span class="token-kw">let</span> int_div: <span class="token-type">int</span> = 7 / 2;     <span class="token-comment">// Evaluates to 3 (truncates toward zero)</span>
<span class="token-kw">let</span> mod_val: <span class="token-type">int</span> = 7 % 3;     <span class="token-comment">// Evaluates to 1</span>
<span class="token-kw">let</span> mixed: <span class="token-type">float</span> = 10 / 4.0;  <span class="token-comment">// Automatic float widening evaluates to 2.5</span>
</pre>

<div class="page-break"></div>

<h2 class="section-title">8.3 Strings, Escape Sequences &amp; Indexing</h2>
<p>
    Strings in C-- are immutable, length-aware UTF-8 sequences supporting escape sequences, multiline triple-quoted literals, zero-indexed byte reading, and length inspection.
</p>
<pre class="code-block">
<span class="token-kw">let</span> text: <span class="token-type">string</span> = <span class="token-str">"C-- Language"</span>;
print(text.len());       <span class="token-comment">// Prints: 12</span>
print(text[0]);          <span class="token-comment">// Prints: C</span>
print(text[4]);          <span class="token-comment">// Prints: L</span>

<span class="token-comment">// Triple-quoted multiline string preserving exact layout</span>
<span class="token-kw">let</span> banner: <span class="token-type">string</span> = <span class="token-str">&quot;&quot;&quot;
    +-----------------------+
    | C-- Safety By Removal |
    +-----------------------+
&quot;&quot;&quot;</span>;
print(banner);
</pre>

<h2 class="section-title">8.4 Fixed-Size Arrays &amp; Dynamic Lists</h2>
<p>
    Arrays provide bounds-checked contiguous storage, constructible via literals or sized constructors. Dynamic lists provide heap-managed resizable vectors with full modification APIs.
</p>
<pre class="code-block">
<span class="token-comment">// Fixed-size arrays with runtime bounds checking</span>
<span class="token-kw">mut</span> numbers = <span class="token-type">array</span>&lt;<span class="token-type">int</span>&gt;(5, 0); <span class="token-comment">// 5 elements initialized to 0</span>
numbers[0] = 100;
numbers[4] = 500;
<span class="token-kw">let</span> literal_arr = [1, 2, 3, 4, 5];

<span class="token-comment">// Dynamic list with push, pop, insert, remove, contains</span>
<span class="token-kw">mut</span> fruits = <span class="token-type">list</span>&lt;<span class="token-type">string</span>&gt;();
fruits.push(<span class="token-str">"apple"</span>);
fruits.push(<span class="token-str">"banana"</span>);
fruits.push(<span class="token-str">"cherry"</span>);
fruits.insert(1, <span class="token-str">"blueberry"</span>);  <span class="token-comment">// Inserts at index 1</span>

print(fruits.contains(<span class="token-str">"banana"</span>)); <span class="token-comment">// Prints: true</span>
print(fruits.remove(1));          <span class="token-comment">// Removes and prints: blueberry</span>
print(fruits.pop());              <span class="token-comment">// Pops and prints: cherry</span>
</pre>

<h2 class="section-title">8.5 LIFO Stacks &amp; FIFO Queues</h2>
<p>
    To eliminate manual linked list pointer implementations, C-- provides native, type-safe stack and queue collections enforcing strict abstract data type (ADT) disciplines.
</p>
<pre class="code-block">
<span class="token-comment">// LIFO Stack</span>
<span class="token-kw">mut</span> history = <span class="token-type">stack</span>&lt;<span class="token-type">string</span>&gt;();
history.push(<span class="token-str">"Page 1: Login"</span>);
history.push(<span class="token-str">"Page 2: Dashboard"</span>);
history.push(<span class="token-str">"Page 3: Settings"</span>);
print(history.peek()); <span class="token-comment">// Prints: Page 3: Settings (top element)</span>
print(history.pop());  <span class="token-comment">// Removes and prints: Page 3: Settings</span>
print(history.len());  <span class="token-comment">// Prints: 2</span>

<span class="token-comment">// FIFO Queue</span>
<span class="token-kw">mut</span> print_jobs = <span class="token-type">queue</span>&lt;<span class="token-type">int</span>&gt;();
print_jobs.enqueue(101);
print_jobs.enqueue(102);
print_jobs.enqueue(103);
print(print_jobs.peek());    <span class="token-comment">// Prints: 101 (front of queue)</span>
print(print_jobs.dequeue()); <span class="token-comment">// Removes and prints: 101</span>
print(print_jobs.len());     <span class="token-comment">// Prints: 2</span>
</pre>

<div class="page-break"></div>

<h2 class="section-title">8.6 Deep-Copy Value Semantics Verification</h2>
<p>
    To guarantee mathematical absence of pointer aliasing and dangling references, collection assignment and parameter passing copy state entirely.
</p>
<pre class="code-block">
<span class="token-kw">fn</span> test_pass_by_value(items: <span class="token-type">list</span>&lt;<span class="token-type">int</span>&gt;) {
    <span class="token-kw">mut</span> local_copy = items;
    local_copy.push(999);
    print(local_copy.len()); <span class="token-comment">// Prints 3 inside function</span>
}

<span class="token-comment">// In caller:</span>
<span class="token-kw">mut</span> original_list = <span class="token-type">list</span>&lt;<span class="token-type">int</span>&gt;();
original_list.push(10);
original_list.push(20);

test_pass_by_value(original_list);
print(original_list.len()); <span class="token-comment">// Prints 2! original_list was NOT mutated!</span>
</pre>

<h2 class="section-title">8.7 Multi-Branch Switch-Case &amp; Iteration Constructs</h2>
<p>
    C-- implements type-checked <code>switch</code> statements supporting both integer and string matching with mandatory <code>break</code> and fallback <code>default</code> branches. Looping includes <code>while</code>, <code>do-while</code>, and scoped <code>for</code> loops.
</p>
<pre class="code-block">
<span class="token-comment">// Multi-branch switch matching integers</span>
<span class="token-kw">let</span> day: <span class="token-type">int</span> = 3;
<span class="token-kw">switch</span> (day) {
    <span class="token-kw">case</span> 1: print(<span class="token-str">"Monday"</span>); <span class="token-kw">break</span>;
    <span class="token-kw">case</span> 2: print(<span class="token-str">"Tuesday"</span>); <span class="token-kw">break</span>;
    <span class="token-kw">case</span> 3: print(<span class="token-str">"Wednesday"</span>); <span class="token-kw">break</span>;
    <span class="token-kw">default</span>: print(<span class="token-str">"Other Day"</span>); <span class="token-kw">break</span>;
}

<span class="token-comment">// Multi-branch switch matching strings</span>
<span class="token-kw">let</span> command: <span class="token-type">string</span> = <span class="token-str">"start"</span>;
<span class="token-kw">switch</span> (command) {
    <span class="token-kw">case</span> <span class="token-str">"start"</span>: print(<span class="token-str">"Starting service on port 8080..."</span>); <span class="token-kw">break</span>;
    <span class="token-kw">case</span> <span class="token-str">"stop"</span>:  print(<span class="token-str">"Halting service..."</span>); <span class="token-kw">break</span>;
    <span class="token-kw">default</span>:     print(<span class="token-str">"Unknown command"</span>); <span class="token-kw">break</span>;
}

<span class="token-comment">// Iteration constructs</span>
<span class="token-kw">mut</span> countdown: <span class="token-type">int</span> = 3;
<span class="token-kw">while</span> (countdown &gt; 0) {
    print(countdown);
    countdown = countdown - 1;
}

<span class="token-kw">do</span> {
    print(<span class="token-str">"do-while body executed once"</span>);
} <span class="token-kw">while</span> (<span class="token-kw">false</span>);

<span class="token-kw">mut</span> sum: <span class="token-type">int</span> = 0;
<span class="token-kw">for</span> (<span class="token-kw">mut</span> i = 1; i &lt;= 5; i = i + 1) {
    sum = sum + i;
}
print(sum); <span class="token-comment">// Prints: 15</span>
</pre>

<div class="page-break"></div>

<h2 class="section-title">8.8 Lexical Scoping, Standard Library &amp; Output Trace</h2>
<p>
    Variables in nested blocks shadow outer names without overwriting outer bindings. The standard library provides robust number parsing (<code>parse_int</code>, <code>parse_float</code>) and I/O.
</p>
<pre class="code-block">
<span class="token-comment">// Scoping &amp; variable shadowing</span>
<span class="token-kw">let</span> outer: <span class="token-type">int</span> = 1000;
{
    <span class="token-kw">let</span> outer: <span class="token-type">int</span> = 1500; <span class="token-comment">// Shadows outer int</span>
    {
        <span class="token-kw">let</span> outer: <span class="token-type">string</span> = <span class="token-str">"deeply shadowed as string"</span>;
        print(outer);
    }
    print(outer); <span class="token-comment">// Prints: 1500</span>
}
print(outer);     <span class="token-comment">// Prints: 1000 (outer binding was completely protected)</span>

<span class="token-comment">// Parsing helpers</span>
<span class="token-kw">let</span> parsed_i = parse_int(<span class="token-str">"123456"</span>) + 1;  <span class="token-comment">// 123457</span>
<span class="token-kw">let</span> parsed_f = parse_float(<span class="token-str">"3.14159"</span>) * 2.0; <span class="token-comment">// 6.28318</span>
</pre>

<h3>Verified Program Output Trace (from <code>demo.cmm</code>)</h3>
<div class="gutter-mockup" style="background-color: #020617; font-size: 8pt; line-height: 1.4;">
=== 1. Primitive Types &amp; Immutability ===<br>
Hello, C-- v0.2.0!<br>
42<br>
3.14159<br>
true<br>
Mutable counter after arithmetic: 15<br>
=== 2. Functions &amp; Recursion ===<br>
Result of add(15, 27): 42<br>
Result of factorial(5): 120<br>
=== 3. Strings ===<br>
String length: 12<br>
First character text[0]: C<br>
Fourth character text[4]: L<br>
=== 4. Fixed-Size Arrays ===<br>
Initial array length: 5 | numbers[0]: 100 | numbers[4]: 500<br>
=== 5. Dynamic Lists ===<br>
Is list empty initially? true | List length: 3 | fruits[1]: blueberry<br>
=== 6. LIFO Stacks ===<br>
Top item via .peek(): Page 3: Settings | Popped: Page 3: Settings<br>
=== 7. FIFO Queues ===<br>
Front job via .peek(): 101 | Dequeued: 101<br>
=== 8. Deep-Copy Value Semantics ===<br>
Original list length remains 2 | Cloned list length is 3<br>
=== 9. Switch Statements ===<br>
Wednesday | Starting service on port 8080...<br>
=== 10. Loops &amp; Scoping ===<br>
Countdown: 3, 2, 1 | Sum 1 to 5: 15<br>
======================================================<br>
<span class="gutter-green">C-- v0.2.0 Complete Showcase Executed Successfully!</span><br>
======================================================
</div>

<div class="page-break"></div>

<!-- ========================================================================
     CHAPTER 9 & 10: DISCUSSION & CONCLUSION
     ======================================================================== -->
<h1 class="chapter-title">9. Discussion, Limitations &amp; Future Roadmap</h1>

<h2 class="section-title">9.1 Boundary Analysis of v0.2.0</h2>
<p>
    While C-- v0.2.0 achieves mathematical memory safety and functional completeness for procedural programming, deliberate boundaries were established to maintain compiler simplicity:
</p>
<ul>
    <li><strong>User-Defined Types:</strong> v0.2.0 omits custom structs/classes, relying on composite collections (<code>array</code>, <code>list</code>, <code>stack</code>, <code>queue</code>).</li>
    <li><strong>Memory Trade-Offs:</strong> Deep-copy value semantics completely eliminate aliasing bugs at the expense of copying overhead for large data structures. Future versions will explore copy-on-write (COW) optimizations.</li>
</ul>

<h2 class="section-title">9.2 Roadmap to v0.3.0 and v1.0</h2>
<p>
    The project development roadmap includes the following planned advancements:
</p>
<ol>
    <li><strong>User-Defined Structs with Value Semantics:</strong> Adding composite record types (e.g. struct Point with x and y fields) governed by strict immutability rules.</li>
    <li><strong>Pattern Matching:</strong> Extending the <code>switch</code> statement into an expressive pattern matching construct with destructuring.</li>
    <li><strong>Direct LLVM IR Generation:</strong> Adding an LLVM backend to produce bare-metal machine code binaries with link-time optimization (LTO).</li>
</ol>

<h1 class="chapter-title">10. Conclusion &amp; Academic References</h1>
<p class="lead">
    The C-- programming language demonstrates that memory safety and procedural simplicity are not mutually exclusive. By applying the principle of <em>"Safety by Removal,"</em> C-- eliminates the historical vulnerabilities of C—including buffer overflows, null pointer dereferences, and dangling references—without requiring complex ownership lifespans or garbage collection.
</p>
<p>
    Backed by a complete multi-pass compiler pipeline, an optimizing ISO C99 code generator, pedagogical diagnostics with Levenshtein typo suggestion, and a 100% verified 417-test suite, C-- serves as both an exemplary educational compiler and a resilient foundation for safe systems programming.
</p>

<div class="note-box" style="margin-top: 14px; margin-bottom: 18px;">
    <strong>Open-Source Project Repository &amp; Live Deployment Links:</strong>
    <ul style="margin: 6px 0 0 18px; padding: 0; line-height: 1.6;">
        <li><strong>GitHub Source Code:</strong> <a href="https://github.com/ronitmexson2924/C--" target="_blank">https://github.com/ronitmexson2924/C--</a></li>
        <li><strong>Live Interactive Web Studio &amp; Compiler Explorer:</strong> <a href="https://web-production-c8ddc.up.railway.app" target="_blank">https://web-production-c8ddc.up.railway.app</a></li>
    </ul>
</div>

<h2 class="section-title">Academic References &amp; Bibliography</h2>
<ol style="font-size: 8.5pt; line-height: 1.5; color: #475569;">
    <li><strong>Aho, A. V., Lam, M. S., Sethi, R., &amp; Ullman, J. D.</strong> (2006). <em>Compilers: Principles, Techniques, and Tools</em> (2nd Edition, "The Dragon Book"). Addison-Wesley.</li>
    <li><strong>Pierce, B. C.</strong> (2002). <em>Types and Programming Languages</em>. MIT Press.</li>
    <li><strong>International Organization for Standardization.</strong> (1999). <em>ISO/IEC 9899:1999 — Programming Languages — C</em> (ISO C99 Specification).</li>
    <li><strong>Szekeres, L., Payer, M., Wei, T., &amp; Song, D.</strong> (2013). "SoK: Eternal War in Memory." <em>IEEE Symposium on Security and Privacy (S&amp;P)</em>, pp. 48–62.</li>
    <li><strong>Levenshtein, V. I.</strong> (1966). "Binary codes capable of correcting deletions, insertions, and reversals." <em>Soviet Physics Doklady</em>, 10(8), 707–710.</li>
    <li><strong>Pratt, V. R.</strong> (1973). "Top down operator precedence." <em>ACM SIGACT-SIGPLAN Symposium on Principles of Programming Languages (POPL)</em>, pp. 41–51.</li>
    <li><strong>The Rust Project Developers.</strong> (2021). <em>The Rust Reference: Memory Safety and Affine Type Ownership</em>. Mozilla Research.</li>
</ol>

</body>
</html>
""")
    return "".join(parts)


def compile_pdf() -> Path:
    """Compile document/report.html to PDF using headless Chrome and verify output."""
    doc_dir = REPO_ROOT / "document"
    doc_dir.mkdir(parents=True, exist_ok=True)
    
    docs_dir = REPO_ROOT / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    html_file = doc_dir / "report.html"
    pdf_file = doc_dir / "C_Minus_Minus_Language_Specification_and_Compiler_Report.pdf"
    docs_pdf_file = docs_dir / "C_Minus_Minus_Language_Specification_and_Compiler_Report.pdf"
    
    print("Generating comprehensive academic report HTML...")
    logo_b64 = get_base64_image(REPO_ROOT / "assets" / "cmm-icon-256.png")
    html_content = build_full_html(logo_b64)
    html_file.write_text(html_content, encoding="utf-8")
    print(f"Wrote HTML source: {html_file} ({len(html_content)} bytes)")
    
    chrome_bin = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if not os.path.exists(chrome_bin):
        raise FileNotFoundError(f"Google Chrome not found at {chrome_bin}")
        
    print(f"Compiling PDF via Headless Chrome: {chrome_bin} ...")
    cmd = [
        chrome_bin,
        "--headless=new",
        "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        "--generate-pdf-document-outline",
        f"--print-to-pdf={pdf_file}",
        str(html_file)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Chrome error: {result.stderr}")
        raise RuntimeError(f"Chrome PDF generation failed with code {result.returncode}")
        
    if not pdf_file.exists() or pdf_file.stat().st_size == 0:
        raise RuntimeError("PDF was not created or is empty.")
        
    pdf_size_kb = pdf_file.stat().st_size / 1024
    print(f"Successfully compiled PDF: {pdf_file} ({pdf_size_kb:.1f} KB)")
    
    # Also copy to docs/ for maximum accessibility
    shutil.copy2(pdf_file, docs_pdf_file)
    print(f"Copied PDF to docs folder: {docs_pdf_file}")
    
    return pdf_file


if __name__ == "__main__":
    pdf_path = compile_pdf()
    print(f"Academic Report PDF ready at: {pdf_path}")
