/**
 * C-- Interactive Compiler Explorer & Language Specification
 * Client controller: editor, compiler pipeline API client, navigation, and command palette.
 */

const FALLBACK_PRESETS = {
    "factorial": {
        "title": "01 — Factorial & Recursion",
        "description": "Typed function declaration, pure recursion, and call stack safety.",
        "code": `module main;

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
`
    },
    "collections": {
        "title": "02 — Dynamic Lists & Slices",
        "description": "Heap-managed dynamic lists with push, pop, insert, remove, and contains.",
        "code": `module main;

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
`
    },
    "stack_queue": {
        "title": "03 — LIFO Stacks & FIFO Queues",
        "description": "Type-safe native ADTs without manual pointer management.",
        "code": `module main;

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
`
    },
    "value_semantics": {
        "title": "04 — Deep-Copy Value Semantics",
        "description": "Proves that copying or passing collections copies state completely, eliminating aliasing.",
        "code": `module main;

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
    
    print("Caller original list length (still 2):");
    print(original.len());
}
`
    },
    "switch_matching": {
        "title": "05 — Switch-Case Matching",
        "description": "Multi-branch pattern matching on integers and strings with mandatory break.",
        "code": `module main;

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
`
    },
    "transpile_demo": {
        "title": "06 — ISO C99 Transpilation",
        "description": "Program suitable for immediate transpilation into hardened ISO C99 code.",
        "code": `module main;

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
`
    },
    "error_diagnostic": {
        "title": "07 — Diagnostics & Typo Recovery",
        "description": "Trigger the diagnostic engine with an identifier typo to inspect Levenshtein suggestions.",
        "code": `module main;

fn main() {
    let maximum_score = 100;
    // Deliberate typo below: 'maximum_scor' instead of 'maximum_score'
    mut current = maximum_scor + 10;
    print(current);
}
`
    }
};

const REFERENCE_SNIPPETS = {
    "bindings": `module main;

fn main() {
    let immut = 42;
    mut counter = 0;
    counter = counter + 1;

    let pi = 3.14159;
    let active = true;
    let name = "C--";

    print(name);
    print(immut + counter);
    print(pi);
    print(active);
}
`,
    "functions": `module main;

fn add(a: int, b: int) -> int {
    return a + b;
}

fn greet(user: string) {
    print("Hello,");
    print(user);
    return;
}

fn main() {
    greet("Systems Engineer");
    print(add(18, 24));
}
`,
    "loops": `module main;

fn main() {
    let score = 85;
    if (score >= 90) {
        print("Grade: A");
    } else if (score >= 80) {
        print("Grade: B");
    } else {
        print("Grade: C");
    }

    for (mut i = 0; i < 4; i = i + 1) {
        print(i);
    }
}
`
};


let activePresets = FALLBACK_PRESETS;

const IS_MAC = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);
const STORAGE_KEYS = { theme: "cmm-theme", draft: "cmm-draft", split: "cmm-split" };
const TAB_IDS = ["playground", "overview", "features", "pipeline", "syntax"];
const TAB_LABELS = { playground: "Playground", overview: "Overview", features: "Architecture", pipeline: "Pipeline", syntax: "Reference" };
const STAGES = ["lexer", "parser", "analyzer", "backend"];

const state = {
    backendOnline: false,
    checkEndpoint: true,      // false once the server reports /api/check is unavailable
    diagnostics: [],
    outputs: { console: "", problems: "", c99: "", ast: "", tokens: "" },
    inflight: null,
    liveCheck: null,
    healthTimer: null,
    c99Ready: false
};

document.addEventListener("DOMContentLoaded", () => {
    applyPlatformLabels();
    initThemeToggle();
    initNavigationTabs();
    initCodeEditor();
    initSplitResizer();
    initOutputTabs();
    initPresets();
    initReferenceLoaders();
    initActionButtons();
    initPipelineActions();
    initReferenceFilter();
    initCopyButtons();
    initCommandPalette();
    initShortcutsModal();
    initGlobalShortcuts();
    checkBackendHealth();
});

/* ==========================================================================
   0. SMALL UTILITIES
   ========================================================================== */
function $(id) {
    return document.getElementById(id);
}

function storageGet(key) {
    try { return localStorage.getItem(key); } catch { return null; }
}

function storageSet(key, value) {
    try { localStorage.setItem(key, value); } catch { /* storage unavailable */ }
}

function escapeHtml(str) {
    if (!str) return "";
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function modLabel(key) {
    return IS_MAC ? `\u2318${key}` : `Ctrl ${key}`;
}

function applyPlatformLabels() {
    if (!IS_MAC) return;
    document.querySelectorAll("[data-mod-key]").forEach(el => {
        el.textContent = el.textContent.replace("Ctrl ", "\u2318");
    });
}

function copyText(text, message = "Copied to clipboard") {
    const done = () => showToast(message);
    if (navigator.clipboard && window.isSecureContext) {
        return navigator.clipboard.writeText(text).then(done, () => fallbackCopy(text) && done());
    }
    if (fallbackCopy(text)) done();
    else showToast("Copy failed", "error");
    return Promise.resolve();
}

function fallbackCopy(text) {
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.cssText = "position:fixed;opacity:0;pointer-events:none";
    document.body.appendChild(area);
    area.select();
    let ok = false;
    try { ok = document.execCommand("copy"); } catch { ok = false; }
    area.remove();
    return ok;
}

function downloadFile(filename, text) {
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function encodeShare(text) {
    const bytes = new TextEncoder().encode(text);
    let bin = "";
    bytes.forEach(b => { bin += String.fromCharCode(b); });
    return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function decodeShare(param) {
    const b64 = param.replace(/-/g, "+").replace(/_/g, "/");
    const bin = atob(b64 + "===".slice((b64.length + 3) % 4));
    const bytes = Uint8Array.from(bin, c => c.charCodeAt(0));
    return new TextDecoder().decode(bytes);
}

/* ==========================================================================
   1. TOASTS
   ========================================================================== */
function showToast(message, type = "success") {
    const region = $("toast-region");
    if (!region) return;
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    const icon = type === "error"
        ? '<path d="M12 8v5M12 16h.01"></path><circle cx="12" cy="12" r="9"></circle>'
        : '<polyline points="20 6 9 17 4 12"></polyline>';
    toast.innerHTML = `<svg class="toast-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icon}</svg><span></span>`;
    toast.querySelector("span").textContent = message;
    region.appendChild(toast);
    while (region.children.length > 3) region.firstElementChild.remove();
    setTimeout(() => {
        toast.classList.add("leaving");
        toast.addEventListener("animationend", () => toast.remove(), { once: true });
        setTimeout(() => toast.remove(), 400);
    }, 2200);
}

/* ==========================================================================
   2. THEME TOGGLE (DARK / LIGHT)
   ========================================================================== */
function currentTheme() {
    return document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
}

function toggleTheme() {
    const next = currentTheme() === "light" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", next);
    storageSet(STORAGE_KEYS.theme, next);
}

function initThemeToggle() {
    const toggleBtn = $("btn-theme-toggle");
    if (toggleBtn) toggleBtn.addEventListener("click", toggleTheme);
}

/* ==========================================================================
   3. NAVIGATION TABS (HASH ROUTED)
   ========================================================================== */
function initNavigationTabs() {
    const tabButtons = document.querySelectorAll(".nav-tab");

    tabButtons.forEach((btn, index) => {
        btn.addEventListener("click", () => navigateTo(btn.getAttribute("data-tab")));
        btn.addEventListener("keydown", (e) => {
            if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
            e.preventDefault();
            const delta = e.key === "ArrowRight" ? 1 : -1;
            const next = tabButtons[(index + delta + tabButtons.length) % tabButtons.length];
            next.focus();
            navigateTo(next.getAttribute("data-tab"));
        });
    });

    window.addEventListener("hashchange", () => activateTab(tabFromHash()));
    window.addEventListener("resize", () => positionNavIndicator());
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => positionNavIndicator(false));

    activateTab(tabFromHash(), false);
}

function tabFromHash() {
    const hash = location.hash.replace("#", "");
    return TAB_IDS.includes(hash) ? hash : "playground";
}

function navigateTo(tab) {
    if (!TAB_IDS.includes(tab)) return;
    if (location.hash !== `#${tab}`) {
        history.pushState(null, "", `#${tab}`);
    }
    activateTab(tab);
}

function activateTab(targetTab, animate = true) {
    document.querySelectorAll(".nav-tab").forEach(b => {
        const isActive = b.getAttribute("data-tab") === targetTab;
        b.classList.toggle("active", isActive);
        b.setAttribute("aria-selected", String(isActive));
        b.tabIndex = isActive ? 0 : -1;
    });
    document.querySelectorAll(".tab-view").forEach(v => {
        v.classList.toggle("active", v.id === `view-${targetTab}`);
    });
    const view = $(`view-${targetTab}`);
    if (view && targetTab !== "playground") view.scrollTop = 0;
    positionNavIndicator(animate);
    if (targetTab === "playground") editorApi.refresh();
}

function positionNavIndicator(animate = true) {
    const indicator = $("nav-indicator");
    const active = document.querySelector(".nav-tab.active");
    if (!indicator || !active) return;
    if (!animate) indicator.style.transition = "none";
    indicator.style.width = `${active.offsetWidth - 20}px`;
    indicator.style.transform = `translateX(${active.offsetLeft + 10}px)`;
    if (!animate) {
        indicator.getBoundingClientRect();
        indicator.style.transition = "";
    }
}

/* ==========================================================================
   4. SYNTAX HIGHLIGHTING
   ========================================================================== */
const LANGS = {
    cmm: {
        keywords: new Set(["module", "fn", "main", "let", "mut", "if", "else", "while", "do", "for", "print",
            "true", "false", "return", "switch", "case", "default"]),
        types: new Set(["int", "float", "bool", "string", "array", "list", "stack", "queue"]),
        builtins: new Set(["read_line", "parse_int", "parse_float"]),
        preprocessor: false
    },
    c: {
        keywords: new Set(["if", "else", "while", "do", "for", "return", "switch", "case", "default", "break",
            "continue", "goto", "sizeof", "typedef", "struct", "union", "enum", "static", "const", "extern",
            "inline", "volatile", "register", "true", "false", "NULL"]),
        types: new Set(["int", "char", "void", "double", "float", "long", "short", "unsigned", "signed", "bool",
            "size_t", "int64_t", "uint64_t", "int32_t", "uint32_t", "uint8_t", "FILE"]),
        builtins: new Set(),
        preprocessor: true
    }
};

const HIGHLIGHT_RE = {
    cmm: /(\/\/[^\n]*|\/\*[\s\S]*?(?:\*\/|(?![\s\S])))|("(?:[^"\\\n]|\\.)*"?)|(\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b)|([A-Za-z_]\w*)|(->|==|!=|<=|>=|&&|\|\||[+\-*/%=<>!])/g,
    c: /(\/\/[^\n]*|\/\*[\s\S]*?(?:\*\/|(?![\s\S])))|("(?:[^"\\\n]|\\.)*"?|'(?:[^'\\\n]|\\.)*'?)|(\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?[uUlLfF]*\b)|([A-Za-z_]\w*)|(->|==|!=|<=|>=|&&|\|\||[+\-*/%=<>!&|^~?])|(^[ \t]*#[^\n]*)/gm
};

function highlight(code, langName = "cmm") {
    const lang = LANGS[langName];
    const re = HIGHLIGHT_RE[langName];
    re.lastIndex = 0;
    let out = "";
    let last = 0;
    let m;
    while ((m = re.exec(code)) !== null) {
        if (m.index > last) out += escapeHtml(code.slice(last, m.index));
        const text = m[0];
        let cls = null;
        if (m[1]) cls = "token-comment";
        else if (m[2]) cls = "token-str";
        else if (m[3]) cls = "token-num";
        else if (m[4]) {
            if (lang.keywords.has(text)) cls = "token-kw";
            else if (lang.types.has(text)) cls = "token-type";
            else if (lang.builtins.has(text) || /^\s*\(/.test(code.slice(re.lastIndex, re.lastIndex + 16))) cls = "token-fn";
        } else if (m[5]) cls = "token-op";
        else if (m[6]) cls = "token-pre";
        out += cls ? `<span class="${cls}">${escapeHtml(text)}</span>` : escapeHtml(text);
        last = re.lastIndex;
        if (text.length === 0) re.lastIndex++;
    }
    if (last < code.length) out += escapeHtml(code.slice(last));
    return out;
}

/* ==========================================================================
   5. CODE EDITOR (HIGHLIGHT OVERLAY, GUTTER, SMART EDITING, DRAFTS)
   ========================================================================== */
const editorApi = { refresh() {}, setCode() {}, goTo() {}, setDiagnostics() {} };

function initCodeEditor() {
    const editor = $("code-editor");
    const surface = $("editor-surface");
    const highlightLayer = $("editor-highlight");
    const decorations = $("editor-decorations");
    const activeLine = $("active-line");
    const gutterInner = $("gutter-inner");
    const lineColIndicator = $("editor-line-col");
    const charCountIndicator = $("editor-char-count");
    const saveIndicator = $("save-indicator");
    const copySourceBtn = $("btn-copy-source");

    const styles = getComputedStyle(document.documentElement);
    const LINE_HEIGHT = parseFloat(styles.getPropertyValue("--editor-lh")) || 21;
    const PAD_Y = parseFloat(styles.getPropertyValue("--editor-pad-y")) || 16;
    const INDENT = "    ";

    let lineCount = 0;
    let currentLine = 1;
    let errorLines = new Map();
    let renderQueued = false;
    let saveTimer = null;

    function renderGutter() {
        let html = "";
        for (let i = 1; i <= lineCount; i++) {
            const err = errorLines.get(i);
            const cls = `gutter-line${i === currentLine ? " active" : ""}${err ? " has-error" : ""}`;
            html += err
                ? `<div class="${cls}" data-line="${i}" title="${escapeHtml(err)}">${i}</div>`
                : `<div class="${cls}">${i}</div>`;
        }
        gutterInner.innerHTML = html;
    }

    function renderDecorations() {
        decorations.querySelectorAll(".error-line").forEach(el => el.remove());
        errorLines.forEach((_, line) => {
            if (line > lineCount) return;
            const el = document.createElement("div");
            el.className = "error-line";
            el.style.top = `${PAD_Y + (line - 1) * LINE_HEIGHT}px`;
            decorations.appendChild(el);
        });
    }

    function render() {
        renderQueued = false;
        const value = editor.value;
        highlightLayer.innerHTML = highlight(value, "cmm") + "\n";
        const newCount = value.split("\n").length;
        lineCount = newCount;
        renderGutter();
        renderDecorations();
        charCountIndicator.textContent = `${value.length.toLocaleString()} chars`;
        syncScroll();
        updateCursorPosition();
    }

    function scheduleRender() {
        if (renderQueued) return;
        renderQueued = true;
        requestAnimationFrame(render);
    }

    function syncScroll() {
        const x = editor.scrollLeft;
        const y = editor.scrollTop;
        highlightLayer.style.transform = `translate(${-x}px, ${-y}px)`;
        decorations.style.transform = `translate(0, ${-y}px)`;
        gutterInner.style.transform = `translateY(${-y}px)`;
    }

    function updateCursorPosition() {
        const pos = editor.selectionStart;
        const before = editor.value.slice(0, pos);
        const line = before.split("\n").length;
        const col = pos - before.lastIndexOf("\n");
        lineColIndicator.textContent = `Ln ${line}, Col ${col}`;
        activeLine.style.top = `${PAD_Y + (line - 1) * LINE_HEIGHT}px`;
        if (line !== currentLine) {
            const prev = gutterInner.children[currentLine - 1];
            const next = gutterInner.children[line - 1];
            if (prev) prev.classList.remove("active");
            if (next) next.classList.add("active");
            currentLine = line;
        }
    }

    function markDirty() {
        saveIndicator.textContent = "Editing";
        saveIndicator.classList.add("dirty");
        clearTimeout(saveTimer);
        saveTimer = setTimeout(saveDraft, 450);
    }

    function saveDraft() {
        clearTimeout(saveTimer);
        storageSet(STORAGE_KEYS.draft, JSON.stringify({ code: editor.value, preset: $("preset-select").value }));
        saveIndicator.textContent = "Saved";
        saveIndicator.classList.remove("dirty");
    }

    /* --- Text mutation that preserves the native undo stack --- */
    function insertText(text, selectStart, selectEnd) {
        editor.focus();
        if (selectStart !== undefined) editor.setSelectionRange(selectStart, selectEnd);
        let ok = false;
        try {
            ok = text === ""
                ? document.execCommand("delete", false)
                : document.execCommand("insertText", false, text);
        } catch { ok = false; }
        if (!ok) {
            editor.setRangeText(text, editor.selectionStart, editor.selectionEnd, "end");
            editor.dispatchEvent(new Event("input"));
        }
    }

    function lineBounds(value, start, end) {
        const lineStart = value.lastIndexOf("\n", start - 1) + 1;
        let lineEnd = value.indexOf("\n", end > start && value[end - 1] === "\n" ? end - 1 : end);
        if (lineEnd === -1) lineEnd = value.length;
        return [lineStart, lineEnd];
    }

    function transformLines(fn) {
        const { value, selectionStart: s, selectionEnd: e } = editor;
        const [ls, le] = lineBounds(value, s, e);
        const original = value.slice(ls, le);
        const updated = fn(original.split("\n")).join("\n");
        if (updated === original) return;
        insertText(updated, ls, le);
        editor.setSelectionRange(ls, ls + updated.length);
    }

    function indentLines(outdent) {
        transformLines(lines => lines.map(l => {
            if (!outdent) return l.length ? INDENT + l : l;
            const m = l.match(/^( {1,4}|\t)/);
            return m ? l.slice(m[0].length) : l;
        }));
    }

    function toggleComment() {
        transformLines(lines => {
            const nonEmpty = lines.filter(l => l.trim());
            const allCommented = nonEmpty.length > 0 && nonEmpty.every(l => /^\s*\/\//.test(l));
            if (allCommented) return lines.map(l => l.replace(/^(\s*)\/\/ ?/, "$1"));
            const minIndent = Math.min(...nonEmpty.map(l => l.match(/^\s*/)[0].length));
            return lines.map(l => l.trim() ? `${l.slice(0, minIndent)}// ${l.slice(minIndent)}` : l);
        });
    }

    const PAIRS = { "(": ")", "[": "]", "{": "}", '"': '"' };
    const CLOSERS = new Set([")", "]", "}", '"']);

    editor.addEventListener("keydown", (e) => {
        const mod = e.ctrlKey || e.metaKey;
        const { value, selectionStart: s, selectionEnd: end } = editor;
        const prev = value[s - 1];
        const next = value[end];

        if (mod && e.shiftKey && e.key === "Enter") {
            e.preventDefault();
            $("btn-transpile").click();
            return;
        }
        if (mod && e.key === "Enter") {
            e.preventDefault();
            $("btn-run").click();
            return;
        }
        if (mod && (e.key === "s" || e.key === "S")) {
            e.preventDefault();
            saveDraft();
            showToast("Draft saved in this browser");
            return;
        }
        if (mod && e.key === "/") {
            e.preventDefault();
            toggleComment();
            return;
        }
        if (e.altKey || mod || e.isComposing) return;

        if (e.key === "Tab") {
            e.preventDefault();
            const multiLine = value.slice(s, end).includes("\n");
            if (e.shiftKey || multiLine) indentLines(e.shiftKey);
            else insertText(INDENT);
            return;
        }

        if (e.key === "Enter") {
            e.preventDefault();
            const lineStart = value.lastIndexOf("\n", s - 1) + 1;
            const indent = value.slice(lineStart, s).match(/^[ \t]*/)[0];
            const opensBlock = /[{(\[]\s*$/.test(value.slice(lineStart, s));
            if (opensBlock && next && /[})\]]/.test(next) && s === end) {
                insertText(`\n${indent}${INDENT}\n${indent}`);
                const caret = s + 1 + indent.length + INDENT.length;
                editor.setSelectionRange(caret, caret);
            } else {
                insertText(`\n${indent}${opensBlock ? INDENT : ""}`);
            }
            return;
        }

        if (e.key === "Backspace" && s === end && prev && PAIRS[prev] === next) {
            e.preventDefault();
            insertText("", s - 1, s + 1);
            return;
        }

        if (e.key === "Backspace" && s === end && s > 0) {
            const lineStart = value.lastIndexOf("\n", s - 1) + 1;
            const before = value.slice(lineStart, s);
            if (before.length >= INDENT.length && /^ +$/.test(before)) {
                e.preventDefault();
                const remove = ((before.length - 1) % INDENT.length) + 1;
                insertText("", s - remove, s);
                return;
            }
        }

        if (CLOSERS.has(e.key) && s === end && next === e.key) {
            if (e.key !== '"' || value[s - 1] !== "\\") {
                e.preventDefault();
                editor.setSelectionRange(s + 1, s + 1);
                updateCursorPosition();
                return;
            }
        }

        if (e.key === "}" && s === end) {
            const lineStart = value.lastIndexOf("\n", s - 1) + 1;
            const before = value.slice(lineStart, s);
            if (before.length >= INDENT.length && /^ +$/.test(before)) {
                e.preventDefault();
                insertText(`${before.slice(INDENT.length)}}`, lineStart, s);
                return;
            }
        }

        if (PAIRS[e.key]) {
            const selected = value.slice(s, end);
            if (selected && !selected.includes("\n")) {
                e.preventDefault();
                insertText(e.key + selected + PAIRS[e.key]);
                editor.setSelectionRange(s + 1, s + 1 + selected.length);
                return;
            }
            const nextOk = !next || /[\s)\]};,]/.test(next);
            const quoteOk = e.key !== '"' || ((!prev || !/[\w"\\]/.test(prev)) && countQuotes(value, s) % 2 === 0);
            if (!selected && nextOk && quoteOk) {
                e.preventDefault();
                insertText(e.key + PAIRS[e.key]);
                editor.setSelectionRange(s + 1, s + 1);
            }
        }
    });

    function countQuotes(value, pos) {
        const lineStart = value.lastIndexOf("\n", pos - 1) + 1;
        return (value.slice(lineStart, pos).replace(/\\./g, "").match(/"/g) || []).length;
    }

    editor.addEventListener("input", () => {
        if (errorLines.size) {
            errorLines = new Map();
            document.querySelectorAll(".problem-item").forEach(el => el.classList.add("stale"));
        }
        scheduleRender();
        markDirty();
        scheduleLiveCheck();
    });
    editor.addEventListener("scroll", syncScroll, { passive: true });
    ["click", "keyup", "select", "focus"].forEach(evt => editor.addEventListener(evt, updateCursorPosition));
    editor.addEventListener("focus", () => surface.classList.add("focused"));
    editor.addEventListener("blur", () => surface.classList.remove("focused"));

    gutterInner.addEventListener("click", (e) => {
        const line = e.target.closest(".gutter-line.has-error");
        if (!line) return;
        const diag = state.diagnostics.find(d => d.line === Number(line.dataset.line));
        if (diag) editorApi.goTo(diag.line, diag.col);
    });

    if (copySourceBtn) {
        copySourceBtn.addEventListener("click", () => copyText(editor.value, "Source copied"));
    }

    editorApi.refresh = () => requestAnimationFrame(render);
    editorApi.save = saveDraft;
    editorApi.setCode = (code) => {
        editor.value = code;
        editor.dispatchEvent(new Event("input"));
        editor.setSelectionRange(0, 0);
        editor.scrollTop = 0;
        editor.scrollLeft = 0;
        saveDraft();
    };
    editorApi.setDiagnostics = (diags) => {
        errorLines = new Map();
        diags.forEach(d => {
            if (!errorLines.has(d.line)) errorLines.set(d.line, d.message);
        });
        renderGutter();
        renderDecorations();
    };
    editorApi.goTo = (line, col = 1, length = 0) => {
        navigateTo("playground");
        const lines = editor.value.split("\n");
        const ln = Math.max(1, Math.min(line, lines.length));
        let offset = 0;
        for (let i = 0; i < ln - 1; i++) offset += lines[i].length + 1;
        offset += Math.max(0, Math.min(col - 1, lines[ln - 1].length));
        editor.focus({ preventScroll: true });
        editor.setSelectionRange(offset, offset + length);
        const targetTop = PAD_Y + (ln - 1) * LINE_HEIGHT;
        if (targetTop < editor.scrollTop || targetTop > editor.scrollTop + editor.clientHeight - LINE_HEIGHT * 2) {
            editor.scrollTop = Math.max(0, targetTop - editor.clientHeight / 3);
        }
        updateCursorPosition();
        syncScroll();
    };

    // Initial content: shared link > saved draft > default example
    let initial = FALLBACK_PRESETS["factorial"].code;
    let presetKey = "factorial";
    let fromShare = false;
    const shared = new URLSearchParams(location.search).get("code");
    if (shared) {
        try {
            initial = decodeShare(shared);
            fromShare = true;
            history.replaceState(null, "", location.pathname + location.hash);
        } catch { /* malformed share link: fall through to draft */ }
    }
    if (!fromShare) {
        try {
            const draft = JSON.parse(storageGet(STORAGE_KEYS.draft) || "null");
            if (draft && typeof draft.code === "string") {
                initial = draft.code;
                if (draft.preset) presetKey = draft.preset;
            }
        } catch { /* ignore corrupt draft */ }
    }

    const select = $("preset-select");
    if (select && [...select.options].some(o => o.value === presetKey)) {
        select.value = presetKey;
        const hint = $("preset-hint");
        if (hint && FALLBACK_PRESETS[presetKey]) hint.textContent = FALLBACK_PRESETS[presetKey].description;
    }

    editor.value = initial;
    render();
    if (fromShare) {
        saveDraft();
        setTimeout(() => showToast("Loaded shared program"), 300);
    }
}

/* ==========================================================================
   6. INTERACTIVE SPLIT PANE RESIZER
   ========================================================================== */
function initSplitResizer() {
    const splitPane = $("studio-split-pane");
    const resizer = $("pane-resizer");
    if (!splitPane || !resizer) return;

    const saved = parseFloat(storageGet(STORAGE_KEYS.split));
    let currentPct = Number.isFinite(saved) ? saved : null;
    if (currentPct) splitPane.style.setProperty("--left-pane-width", `${currentPct}%`);

    function setPct(pct) {
        const rect = splitPane.getBoundingClientRect();
        const minPct = (280 / rect.width) * 100;
        currentPct = Math.max(minPct, Math.min(100 - minPct, pct));
        splitPane.style.setProperty("--left-pane-width", `${currentPct.toFixed(2)}%`);
        resizer.setAttribute("aria-valuenow", String(Math.round(currentPct)));
    }

    let isDragging = false;

    resizer.addEventListener("pointerdown", (e) => {
        e.preventDefault();
        isDragging = true;
        resizer.setPointerCapture(e.pointerId);
        resizer.classList.add("dragging");
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
    });

    resizer.addEventListener("pointermove", (e) => {
        if (!isDragging) return;
        const rect = splitPane.getBoundingClientRect();
        setPct(((e.clientX - rect.left) / rect.width) * 100);
    });

    const stopDrag = () => {
        if (!isDragging) return;
        isDragging = false;
        resizer.classList.remove("dragging");
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
        if (currentPct) storageSet(STORAGE_KEYS.split, currentPct.toFixed(2));
    };
    resizer.addEventListener("pointerup", stopDrag);
    resizer.addEventListener("pointercancel", stopDrag);

    resizer.addEventListener("keydown", (e) => {
        if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
        e.preventDefault();
        setPct((currentPct || 50) + (e.key === "ArrowRight" ? 2 : -2));
        storageSet(STORAGE_KEYS.split, currentPct.toFixed(2));
    });

    resizer.addEventListener("dblclick", () => {
        currentPct = null;
        splitPane.style.setProperty("--left-pane-width", "1fr");
        storageSet(STORAGE_KEYS.split, "");
    });
}

/* ==========================================================================
   7. OUTPUT TABS, STATUS & STAGE TRACE
   ========================================================================== */
function initOutputTabs() {
    const outputTabs = [...document.querySelectorAll(".output-tab")];

    outputTabs.forEach((tab, index) => {
        tab.addEventListener("click", () => switchOutputTab(tab.getAttribute("data-output")));
        tab.addEventListener("keydown", (e) => {
            if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
            e.preventDefault();
            const next = outputTabs[(index + (e.key === "ArrowRight" ? 1 : -1) + outputTabs.length) % outputTabs.length];
            next.focus();
            switchOutputTab(next.getAttribute("data-output"));
        });
    });

    $("btn-copy-output").addEventListener("click", () => {
        const active = document.querySelector(".output-tab.active");
        const key = active ? active.getAttribute("data-output") : "console";
        const view = document.querySelector(".output-view.active");
        const text = state.outputs[key] || (view ? view.textContent : "");
        if (text.trim()) copyText(text, "Output copied");
        else showToast("Nothing to copy yet", "error");
    });

    $("btn-clear-output").addEventListener("click", clearOutput);

    // Clickable diagnostic locations in rendered output
    $("output-content-container").addEventListener("click", (e) => {
        const loc = e.target.closest(".diag-loc");
        if (loc) editorApi.goTo(Number(loc.dataset.line), Number(loc.dataset.col));
    });
}

function clearOutput() {
    $("terminal-display").innerHTML = '<span class="terminal-dim">// Console cleared.</span>';
    state.outputs.console = "";
    resetTrace();
    setStatus("Ready", "status-ready");
}

function switchOutputTab(tabName) {
    document.querySelectorAll(".output-tab").forEach(t => {
        const isActive = t.getAttribute("data-output") === tabName;
        t.classList.toggle("active", isActive);
        t.setAttribute("aria-selected", String(isActive));
        t.tabIndex = isActive ? 0 : -1;
    });
    document.querySelectorAll(".output-view").forEach(v => {
        v.classList.toggle("active", v.id === `output-view-${tabName}`);
    });
}

function setStatus(text, className) {
    const pill = $("execution-status-pill");
    pill.textContent = text;
    pill.className = `status-pill ${className}`;
}

function resetTrace(backendLabel) {
    document.querySelectorAll(".trace-step").forEach(step => {
        step.className = "trace-step";
        if (backendLabel && step.dataset.stage === "backend") step.textContent = backendLabel;
    });
    $("trace-meta").textContent = "";
}

function setTrace(okThrough, failedAt, running) {
    const okIndex = STAGES.indexOf(okThrough);
    document.querySelectorAll(".trace-step").forEach(step => {
        const idx = STAGES.indexOf(step.dataset.stage);
        step.className = "trace-step";
        if (idx <= okIndex) step.classList.add("ok");
        if (step.dataset.stage === failedAt) step.classList.add("fail");
        if (step.dataset.stage === running) step.classList.add("running");
    });
}

function stageFromServer(stage) {
    if (stage === "runtime" || stage === "transpiler" || stage === "internal" || stage === "interpreter") return "backend";
    return stage;
}

function previousStage(stage) {
    const idx = STAGES.indexOf(stage);
    return idx > 0 ? STAGES[idx - 1] : null;
}

/* ==========================================================================
   8. DIAGNOSTICS: PARSING, RENDERING & PROBLEMS PANEL
   ========================================================================== */
const DIAG_HEADER_RE = /^([^\s:]+\.cmm):(\d+):(\d+): ([a-z ]*error): (.*)$/;

function parseDiagnostics(text) {
    const diags = [];
    let current = null;
    let section = null;
    (text || "").split("\n").forEach(line => {
        const m = line.match(DIAG_HEADER_RE);
        if (m) {
            current = { line: Number(m[2]), col: Number(m[3]), kind: m[4], message: m[5], explanation: "", fix: "" };
            diags.push(current);
            section = null;
            return;
        }
        if (!current) return;
        if (/^what went wrong:/.test(line)) { section = "explanation"; return; }
        if (/^how to fix:/.test(line)) { section = "fix"; return; }
        if (section && /^ {2}\S/.test(line) && !current[section]) current[section] = line.trim();
    });
    return diags;
}

function stageFromDiagnostics(diags) {
    const kind = diags.length ? diags[0].kind : "";
    if (kind.includes("lexical")) return "lexer";
    if (kind.includes("syntax")) return "parser";
    if (kind.includes("semantic")) return "analyzer";
    if (kind.includes("runtime")) return "backend";
    return "parser";
}

function renderDiagnosticText(text) {
    return (text || "").split("\n").map(line => {
        const m = line.match(DIAG_HEADER_RE);
        if (m) {
            return `<span class="diag-loc" data-line="${m[2]}" data-col="${m[3]}" title="Jump to line ${m[2]}">${escapeHtml(`${m[1]}:${m[2]}:${m[3]}`)}</span>: ` +
                `<span class="diag-kind">${escapeHtml(m[4])}</span>: ${escapeHtml(m[5])}`;
        }
        if (/^(what went wrong|how to fix):$/.test(line)) return `<span class="diag-section">${escapeHtml(line)}</span>`;
        const caret = line.match(/^(\s*\|)(\s*)(\^+.*)$/);
        if (caret) return `<span class="diag-gutter">${escapeHtml(caret[1])}</span>${caret[2]}<span class="diag-caret">${escapeHtml(caret[3])}</span>`;
        const src = line.match(/^(\s*\d*\s*\|)(.*)$/);
        if (src) return `<span class="diag-gutter">${escapeHtml(src[1])}</span>${escapeHtml(src[2])}`;
        return escapeHtml(line);
    }).join("\n");
}

function applyDiagnostics(diags) {
    state.diagnostics = diags;
    editorApi.setDiagnostics(diags);

    const count = $("problems-count");
    count.hidden = diags.length === 0;
    count.textContent = String(diags.length);
    count.classList.toggle("has-errors", diags.length > 0);

    const list = $("problems-list");
    if (!diags.length) {
        list.innerHTML = '<div class="empty-state"><div class="empty-title">No problems detected</div><div class="empty-sub">Lexical, syntactic, and semantic checks passed.</div></div>';
        state.outputs.problems = "";
        return;
    }
    list.innerHTML = diags.map((d, i) => `
        <button class="problem-item" data-index="${i}">
            <svg class="problem-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"></circle><path d="M12 8v5M12 16h.01"></path></svg>
            <span>
                <span class="problem-msg">${escapeHtml(d.message)}</span>
                <span class="problem-kind">${escapeHtml(d.kind)}</span>
                ${d.fix ? `<span class="problem-hint">${escapeHtml(d.fix)}</span>` : ""}
            </span>
            <span class="problem-loc">Ln ${d.line}, Col ${d.col}</span>
        </button>`).join("");
    state.outputs.problems = diags.map(d => `playground.cmm:${d.line}:${d.col}: ${d.kind}: ${d.message}`).join("\n");
    list.querySelectorAll(".problem-item").forEach(item => {
        item.addEventListener("click", () => {
            const d = diags[Number(item.dataset.index)];
            editorApi.goTo(d.line, d.col);
        });
    });
}

/* ==========================================================================
   9. PRESETS & REFERENCE SNIPPET LOADERS
   ========================================================================== */
function loadPreset(key) {
    const preset = activePresets[key] || FALLBACK_PRESETS[key];
    if (!preset) return false;
    const select = $("preset-select");
    if ([...select.options].some(o => o.value === key)) {
        select.value = key;
        $("preset-hint").textContent = (FALLBACK_PRESETS[key] || preset).description;
    }
    editorApi.setCode(preset.code);
    applyDiagnostics([]);
    setStatus("Ready", "status-ready");
    return true;
}

function initPresets() {
    const select = $("preset-select");
    select.addEventListener("change", () => loadPreset(select.value));
    $("btn-reset").addEventListener("click", () => {
        if (loadPreset(select.value)) {
            setStatus("Reset", "status-ready");
            showToast("Editor reset to example");
        }
    });
}

function initReferenceLoaders() {
    document.querySelectorAll(".btn-load-snippet").forEach(btn => {
        btn.addEventListener("click", () => {
            const key = btn.getAttribute("data-snippet");
            const preset = activePresets[key] || FALLBACK_PRESETS[key];
            const code = preset ? preset.code : REFERENCE_SNIPPETS[key];
            if (!code) return;
            navigateTo("playground");
            if (preset) loadPreset(key);
            else {
                editorApi.setCode(code);
                setStatus("Ready", "status-ready");
            }
        });
    });
}

function initReferenceFilter() {
    const input = $("reference-search");
    if (!input) return;
    const cards = [...document.querySelectorAll("#syntax-grid .syntax-card")];
    input.addEventListener("input", () => {
        const terms = input.value.toLowerCase().split(/\s+/).filter(Boolean);
        let visible = 0;
        cards.forEach(card => {
            const text = card.textContent.toLowerCase();
            const match = terms.every(t => text.includes(t));
            card.hidden = !match;
            if (match) visible++;
        });
        $("reference-empty").hidden = visible > 0;
    });
}

function initCopyButtons() {
    document.querySelectorAll("[data-copy-target]").forEach(btn => {
        btn.addEventListener("click", () => {
            const target = $(btn.getAttribute("data-copy-target"));
            if (target) copyText(target.textContent.trim(), "Command copied");
        });
    });
}

function initPipelineActions() {
    document.querySelectorAll("[data-pipeline-action]").forEach(btn => {
        btn.addEventListener("click", () => {
            navigateTo("playground");
            const target = $(btn.getAttribute("data-pipeline-action"));
            if (target) target.click();
        });
    });
}

/* ==========================================================================
   10. COMPILER PIPELINE ACTIONS & API CALLS
   ========================================================================== */
async function postJson(endpoint, body) {
    if (state.inflight) state.inflight.abort();
    const controller = new AbortController();
    state.inflight = controller;
    const timeout = setTimeout(() => controller.abort("timeout"), 30000);
    try {
        const res = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
            signal: controller.signal
        });
        const data = await res.json();
        return { data, status: res.status };
    } finally {
        clearTimeout(timeout);
        if (state.inflight === controller) state.inflight = null;
    }
}

function setBusy(buttonId, busy) {
    const btn = $(buttonId);
    if (!btn) return;
    btn.classList.toggle("is-loading", busy);
    btn.setAttribute("aria-busy", String(busy));
}

function isAbort(err) {
    return err === "timeout" || Boolean(err && err.name === "AbortError");
}

function reportRequestFailure(err, displayId, label) {
    // A request superseded by a newer action is aborted silently; its successor owns the UI.
    if (isAbort(err) && err !== "timeout") return;
    resetTrace();
    setStatus(err === "timeout" ? "Timed out" : "Offline", "status-error");
    if (err !== "timeout") {
        markBackend(false);
        scheduleHealthCheck(5000);
    }
    $(displayId).innerHTML = `<span class="terminal-err">[OFFLINE] ${label}</span>\n${escapeHtml(String(err))}\n\n<span class="terminal-dim">// Start the backend server: python3 web/server.py</span>`;
}

function formatMs(ms) {
    return ms < 1000 ? `${ms.toFixed(1)} ms` : `${(ms / 1000).toFixed(2)} s`;
}

function initActionButtons() {
    const editor = $("code-editor");

    // 1. Run program
    $("btn-run").addEventListener("click", async () => {
        switchOutputTab("console");
        setStatus("Running...", "status-running");
        setBusy("btn-run", true);
        resetTrace("Execute");
        setTrace(null, null, "lexer");
        const terminal = $("terminal-display");
        terminal.innerHTML = '<span class="terminal-dim">// Executing in C-- reference interpreter...</span>';

        const startTime = performance.now();
        try {
            const { data } = await postJson("/api/run", { code: editor.value, help_enabled: true });
            const elapsed = performance.now() - startTime;
            markBackend(true);
            $("trace-meta").textContent = `run \u00b7 ${formatMs(elapsed)}`;

            if (data.success) {
                setStatus(`Exit 0 \u00b7 ${formatMs(elapsed)}`, "status-success");
                setTrace("backend");
                const output = data.output || "";
                state.outputs.console = output;
                terminal.innerHTML = `<span class="terminal-ok terminal-header">\u2713 Program exited with code 0</span>` +
                    (output ? escapeHtml(output) : '<span class="terminal-dim">(no output)</span>');
                applyDiagnostics([]);
            } else {
                const failed = stageFromServer(data.stage) || "backend";
                setStatus(`Exit ${data.exit_code || 1} \u00b7 ${data.stage || "error"}`, "status-error");
                setTrace(previousStage(failed), failed);
                state.outputs.console = data.error || "";
                terminal.innerHTML = `<span class="terminal-err terminal-header">\u2717 Failed during ${escapeHtml(data.stage || "compilation")}</span>${renderDiagnosticText(data.error)}`;
                applyDiagnostics(parseDiagnostics(data.error));
            }
        } catch (err) {
            reportRequestFailure(err, "terminal-display", "Compiler server unreachable");
        } finally {
            setBusy("btn-run", false);
        }
    });

    // 2. Transpile to C99
    $("btn-transpile").addEventListener("click", async () => {
        switchOutputTab("c99");
        setStatus("Transpiling...", "status-running");
        setBusy("btn-transpile", true);
        resetTrace("Codegen");
        setTrace(null, null, "lexer");
        const cDisplay = $("c99-display");
        cDisplay.innerHTML = '<span class="terminal-dim">// Lowering AST to ISO C99...</span>';

        const startTime = performance.now();
        try {
            const { data } = await postJson("/api/transpile", { code: editor.value, help_enabled: true });
            const elapsed = performance.now() - startTime;
            markBackend(true);
            $("trace-meta").textContent = `transpile \u00b7 ${formatMs(elapsed)}`;

            if (data.success) {
                const lines = data.c_code.split("\n").length;
                setStatus(`C99 \u00b7 ${lines} lines`, "status-success");
                setTrace("backend");
                state.outputs.c99 = data.c_code;
                state.c99Ready = true;
                cDisplay.innerHTML = highlight(data.c_code, "c");
                applyDiagnostics([]);
            } else {
                const failed = stageFromServer(data.stage) || "backend";
                setStatus("Transpile error", "status-error");
                setTrace(previousStage(failed), failed);
                state.outputs.c99 = data.error || "";
                state.c99Ready = false;
                cDisplay.innerHTML = `<span class="terminal-err terminal-header">\u2717 C99 code generation failed</span>${renderDiagnosticText(data.error)}`;
                applyDiagnostics(parseDiagnostics(data.error));
            }
        } catch (err) {
            reportRequestFailure(err, "c99-display", "Transpiler request failed");
        } finally {
            setBusy("btn-transpile", false);
        }
    });

    // 3. Type check (static front-end only; falls back to /api/run on older servers)
    $("btn-check").addEventListener("click", async () => {
        switchOutputTab("console");
        setStatus("Checking...", "status-running");
        resetTrace("Execute");
        setTrace(null, null, "lexer");
        const terminal = $("terminal-display");

        const startTime = performance.now();
        try {
            const data = await requestCheck(editor.value);
            const elapsed = performance.now() - startTime;
            markBackend(true);
            $("trace-meta").textContent = `check \u00b7 ${formatMs(elapsed)}`;

            if (data.stage === "lexer" || data.stage === "parser" || data.stage === "analyzer") {
                if (data.success === false) {
                    setStatus("Type error", "status-error");
                    setTrace(previousStage(data.stage), data.stage);
                    state.outputs.console = data.error || "";
                    terminal.innerHTML = `<span class="terminal-err terminal-header">\u2717 Static verification failed (${escapeHtml(data.stage)})</span>${renderDiagnosticText(data.error)}`;
                    applyDiagnostics(parseDiagnostics(data.error));
                    return;
                }
            }
            setStatus("Verified", "status-success");
            setTrace("analyzer");
            state.outputs.console = "Lexical, syntactic, and semantic checks succeeded.\nNo type or scope violations detected.";
            terminal.innerHTML = `<span class="terminal-ok terminal-header">\u2713 Lexical, syntactic, and semantic checks succeeded.</span>No type or scope violations detected.`;
            applyDiagnostics([]);
        } catch (err) {
            reportRequestFailure(err, "terminal-display", "Verification request failed");
        }
    });

    // 4. Inspect AST
    $("btn-ast").addEventListener("click", async () => {
        switchOutputTab("ast");
        setStatus("Parsing...", "status-running");
        resetTrace();
        setTrace(null, null, "lexer");
        const astDisplay = $("ast-display");
        astDisplay.innerHTML = '<span class="terminal-dim">// Constructing Abstract Syntax Tree...</span>';

        try {
            const { data } = await postJson("/api/ast", { code: editor.value });
            markBackend(true);
            if (data.success) {
                setStatus("AST ready", "status-success");
                setTrace("parser");
                state.outputs.ast = data.ast;
                astDisplay.innerHTML = renderAst(data.ast);
            } else {
                const diags = parseDiagnostics(data.error);
                const failed = stageFromDiagnostics(diags);
                setStatus("Parse error", "status-error");
                setTrace(previousStage(failed), failed);
                state.outputs.ast = data.error || "";
                astDisplay.innerHTML = `<span class="terminal-err terminal-header">\u2717 AST construction failed</span>${renderDiagnosticText(data.error)}`;
                applyDiagnostics(diags);
            }
        } catch (err) {
            reportRequestFailure(err, "ast-display", "AST request failed");
        }
    });

    // 5. Inspect tokens
    $("btn-tokens").addEventListener("click", async () => {
        switchOutputTab("tokens");
        setStatus("Tokenizing...", "status-running");
        resetTrace();
        setTrace(null, null, "lexer");
        const tokensDisplay = $("tokens-display");
        tokensDisplay.innerHTML = '<span class="terminal-dim">// Scanning lexical token stream...</span>';

        try {
            const { data } = await postJson("/api/tokens", { code: editor.value });
            markBackend(true);
            if (data.success) {
                setStatus("Tokens ready", "status-success");
                setTrace("lexer");
                state.outputs.tokens = data.tokens;
                tokensDisplay.innerHTML = renderTokens(data.tokens);
            } else {
                setStatus("Lex error", "status-error");
                setTrace(null, "lexer");
                state.outputs.tokens = data.error || "";
                tokensDisplay.innerHTML = `<span class="terminal-err terminal-header">\u2717 Lexical analysis failed</span>${renderDiagnosticText(data.error)}`;
                applyDiagnostics(parseDiagnostics(data.error));
            }
        } catch (err) {
            reportRequestFailure(err, "tokens-display", "Token request failed");
        }
    });

    $("tokens-display").addEventListener("click", (e) => {
        const row = e.target.closest("tr[data-line]");
        if (row) editorApi.goTo(Number(row.dataset.line), Number(row.dataset.col), Number(row.dataset.len));
    });

    // 6. Utilities
    $("btn-share").addEventListener("click", shareLink);
    $("btn-download").addEventListener("click", () => {
        downloadFile("playground.cmm", editor.value);
        showToast("Downloaded playground.cmm");
    });
}

async function requestCheck(code, { live = false } = {}) {
    if (state.checkEndpoint) {
        const { data, status } = live
            ? await fetch("/api/check", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code, help_enabled: true })
            }).then(async r => ({ data: await r.json(), status: r.status }))
            : await postJson("/api/check", { code, help_enabled: true });
        if (status !== 404) return data;
        state.checkEndpoint = false;
    }
    if (live) return null;
    const { data } = await postJson("/api/run", { code, help_enabled: true });
    return data;
}

function scheduleLiveCheck() {
    clearTimeout(state.liveCheck);
    if (!state.backendOnline) return;
    state.liveCheck = setTimeout(async () => {
        const editor = $("code-editor");
        const snapshot = editor.value;
        try {
            const data = await requestCheck(snapshot, { live: true });
            if (!data || editor.value !== snapshot) return;
            applyDiagnostics(data.success === false ? parseDiagnostics(data.error) : []);
        } catch { /* live diagnostics are best-effort */ }
    }, 650);
}

function shareLink() {
    const code = $("code-editor").value;
    const url = `${location.origin}${location.pathname}?code=${encodeShare(code)}#playground`;
    if (url.length > 8000) {
        showToast("Program is too large to share as a link", "error");
        return;
    }
    copyText(url, "Shareable link copied");
}

const TOKEN_KEYWORDS = new Set(["MODULE", "FN", "MAIN", "LET", "MUT", "IF", "ELSE", "WHILE", "DO", "FOR", "PRINT",
    "TRUE", "FALSE", "RETURN", "SWITCH", "CASE", "DEFAULT"]);

function renderTokens(raw) {
    const rows = raw.split("\n").filter(Boolean).map(line => {
        const first = line.indexOf("\t");
        const second = line.indexOf("\t", first + 1);
        const pos = line.slice(0, first);
        const type = second === -1 ? line.slice(first + 1) : line.slice(first + 1, second);
        const lexeme = second === -1 ? "" : line.slice(second + 1);
        const [ln, col] = pos.split(":").map(Number);
        let kind = "";
        if (TOKEN_KEYWORDS.has(type)) kind = "kw";
        else if (type.startsWith("KW_")) kind = "type";
        else if (type === "STRING") kind = "str";
        else if (type === "INT" || type === "FLOAT") kind = "num";
        const len = type === "STRING" ? 0 : lexeme.length;
        return `<tr class="tk-kind-${kind || "plain"}" data-line="${ln}" data-col="${col}" data-len="${len}" title="Locate in editor">` +
            `<td class="tk-pos">${escapeHtml(pos)}</td><td class="tk-type">${escapeHtml(type)}</td><td class="tk-lex">${escapeHtml(lexeme)}</td></tr>`;
    });
    return `<div class="token-summary">${rows.length} tokens \u00b7 click a row to locate it in the editor</div>` +
        `<table class="token-table"><thead><tr><th>Pos</th><th>Type</th><th>Lexeme</th></tr></thead><tbody>${rows.join("")}</tbody></table>`;
}

function renderAst(raw) {
    return raw.split("\n").map(line => {
        const m = line.match(/^(\s*)(?:([a-z_]+): )?([A-Za-z_]\w*)(.*)$/);
        if (!m) return escapeHtml(line);
        const [, indent, field, node, rest] = m;
        const restHtml = escapeHtml(rest)
            .replace(/(&quot;.*?&quot;)/g, '<span class="token-str">$1</span>')
            .replace(/=(-?\d+(?:\.\d+)?)/g, '=<span class="token-num">$1</span>');
        return `${indent}${field ? `<span class="ast-field">${escapeHtml(field)}:</span> ` : ""}<span class="ast-node">${escapeHtml(node)}</span>${restHtml}`;
    }).join("\n");
}

/* ==========================================================================
   11. COMMAND PALETTE
   ========================================================================== */
function buildCommands() {
    const commands = [
        { group: "Actions", label: "Run program", hint: modLabel("\u21b5"), run: () => clickAction("btn-run") },
        { group: "Actions", label: "Transpile to ISO C99", hint: modLabel("\u21e7\u21b5"), run: () => clickAction("btn-transpile") },
        { group: "Actions", label: "Type check", run: () => clickAction("btn-check") },
        { group: "Actions", label: "Inspect AST", run: () => clickAction("btn-ast") },
        { group: "Actions", label: "Inspect tokens", run: () => clickAction("btn-tokens") },
        { group: "Actions", label: "Copy shareable link", run: shareLink },
        { group: "Actions", label: "Download source (.cmm)", run: () => $("btn-download").click() },
        { group: "Actions", label: "Download C99 output (.c)", run: () => {
            if (!state.c99Ready) {
                showToast("Transpile the program first", "error");
                return;
            }
            downloadFile("playground.c", state.outputs.c99);
            showToast("Downloaded playground.c");
        } },
        { group: "Actions", label: "Reset editor to example", run: () => $("btn-reset").click() },
        { group: "Actions", label: "Clear console", run: clearOutput },
        { group: "Actions", label: "Toggle color theme", run: toggleTheme },
        { group: "Actions", label: "Show keyboard shortcuts", hint: "?", run: openShortcuts }
    ];
    TAB_IDS.forEach((tab, i) => commands.push({ group: "Navigate", label: `Go to ${TAB_LABELS[tab]}`, hint: `Alt ${i + 1}`, run: () => navigateTo(tab) }));
    Object.keys(FALLBACK_PRESETS).forEach(key => {
        commands.push({ group: "Examples", label: FALLBACK_PRESETS[key].title, run: () => { navigateTo("playground"); loadPreset(key); } });
    });
    commands.push(
        { group: "Links", label: "Open language specification (PDF)", run: () => window.open("/document/C_Minus_Minus_Language_Specification_and_Compiler_Report.pdf", "_blank", "noopener") },
        { group: "Links", label: "Open GitHub repository", run: () => window.open("https://github.com/ronitmexson2924/C--", "_blank", "noopener") }
    );
    return commands;
}

function clickAction(id) {
    navigateTo("playground");
    $(id).click();
}

function fuzzyScore(query, text) {
    if (!query) return { score: 0, indices: [] };
    const q = query.toLowerCase();
    const t = text.toLowerCase();
    const direct = t.indexOf(q);
    if (direct !== -1) {
        return { score: 1000 - direct * 2 - t.length * 0.1, indices: Array.from({ length: q.length }, (_, i) => direct + i) };
    }
    const indices = [];
    let ti = 0;
    for (const ch of q) {
        if (ch === " ") continue;
        ti = t.indexOf(ch, ti);
        if (ti === -1) return null;
        indices.push(ti++);
    }
    const spread = indices[indices.length - 1] - indices[0];
    return { score: 500 - spread - t.length * 0.1, indices };
}

function markMatches(text, indices) {
    if (!indices.length) return escapeHtml(text);
    const set = new Set(indices);
    return [...text].map((ch, i) => set.has(i) ? `<mark>${escapeHtml(ch)}</mark>` : escapeHtml(ch)).join("");
}

let paletteApi = { open() {}, close() {} };

function initCommandPalette() {
    const backdrop = $("command-palette");
    const input = $("cmdk-input");
    const list = $("cmdk-list");
    const commands = buildCommands();
    let results = [];
    let selected = 0;
    let lastFocus = null;

    function renderList() {
        const query = input.value.trim();
        results = commands
            .map(cmd => ({ cmd, match: fuzzyScore(query, `${cmd.label}`) }))
            .filter(r => r.match)
            .sort((a, b) => query ? b.match.score - a.match.score : 0);
        selected = Math.min(selected, Math.max(0, results.length - 1));

        if (!results.length) {
            list.innerHTML = `<li class="cmdk-empty">No commands match \u201c${escapeHtml(query)}\u201d</li>`;
            return;
        }
        let html = "";
        let group = null;
        results.forEach((r, i) => {
            if (!query && r.cmd.group !== group) {
                group = r.cmd.group;
                html += `<li class="cmdk-group" role="presentation">${escapeHtml(group)}</li>`;
            }
            html += `<li class="cmdk-item${i === selected ? " selected" : ""}" role="option" id="cmdk-opt-${i}" data-index="${i}" aria-selected="${i === selected}">` +
                `<span class="cmdk-item-label">${markMatches(r.cmd.label, r.match.indices)}</span>` +
                (r.cmd.hint ? `<span class="cmdk-item-hint">${escapeHtml(r.cmd.hint)}</span>` : "") + "</li>";
        });
        list.innerHTML = html;
        input.setAttribute("aria-activedescendant", `cmdk-opt-${selected}`);
        const el = list.querySelector(".cmdk-item.selected");
        if (el) el.scrollIntoView({ block: "nearest" });
    }

    function open() {
        lastFocus = document.activeElement;
        backdrop.hidden = false;
        input.value = "";
        selected = 0;
        renderList();
        input.focus();
    }

    function close(restoreFocus = true) {
        if (backdrop.hidden) return;
        backdrop.hidden = true;
        if (restoreFocus && lastFocus && lastFocus.focus) lastFocus.focus();
    }

    function execute(index) {
        const r = results[index];
        if (!r) return;
        close(false);
        r.cmd.run();
    }

    input.addEventListener("input", () => { selected = 0; renderList(); });
    input.addEventListener("keydown", (e) => {
        if (e.key === "ArrowDown") { e.preventDefault(); selected = (selected + 1) % Math.max(1, results.length); renderList(); }
        else if (e.key === "ArrowUp") { e.preventDefault(); selected = (selected - 1 + results.length) % Math.max(1, results.length); renderList(); }
        else if (e.key === "Enter") { e.preventDefault(); execute(selected); }
        else if (e.key === "Escape") { e.preventDefault(); close(); }
    });
    list.addEventListener("mousemove", (e) => {
        const item = e.target.closest(".cmdk-item");
        if (!item || Number(item.dataset.index) === selected) return;
        selected = Number(item.dataset.index);
        list.querySelectorAll(".cmdk-item").forEach(el => el.classList.toggle("selected", el === item));
    });
    list.addEventListener("click", (e) => {
        const item = e.target.closest(".cmdk-item");
        if (item) execute(Number(item.dataset.index));
    });
    backdrop.addEventListener("mousedown", (e) => { if (e.target === backdrop) close(); });
    $("btn-command-palette").addEventListener("click", open);

    paletteApi = { open, close, isOpen: () => !backdrop.hidden };
}

/* ==========================================================================
   12. SHORTCUTS MODAL & GLOBAL KEYBOARD
   ========================================================================== */
const SHORTCUTS = [
    ["Command palette", [IS_MAC ? "\u2318" : "Ctrl", "K"]],
    ["Run program", [IS_MAC ? "\u2318" : "Ctrl", "\u21b5"]],
    ["Transpile to C99", [IS_MAC ? "\u2318" : "Ctrl", "\u21e7", "\u21b5"]],
    ["Save draft", [IS_MAC ? "\u2318" : "Ctrl", "S"]],
    ["Toggle line comment", [IS_MAC ? "\u2318" : "Ctrl", "/"]],
    ["Indent / outdent", ["Tab", "\u21e7 Tab"]],
    ["Switch section", ["Alt", "1\u20135"]],
    ["Show this dialog", ["?"]]
];

let shortcutsApi = { open() {}, close() {} };

function openShortcuts() {
    shortcutsApi.open();
}

function initShortcutsModal() {
    const backdrop = $("shortcuts-modal");
    $("shortcut-list").innerHTML = SHORTCUTS.map(([label, keys]) =>
        `<div class="shortcut-row"><dt>${escapeHtml(label)}</dt><dd>${keys.map(k => `<kbd class="kbd">${escapeHtml(k)}</kbd>`).join("")}</dd></div>`
    ).join("");

    let lastFocus = null;
    function open() {
        lastFocus = document.activeElement;
        backdrop.hidden = false;
        backdrop.querySelector("[data-close-modal]").focus();
    }
    function close() {
        if (backdrop.hidden) return;
        backdrop.hidden = true;
        if (lastFocus && lastFocus.focus) lastFocus.focus();
    }
    backdrop.addEventListener("mousedown", (e) => { if (e.target === backdrop) close(); });
    backdrop.querySelector("[data-close-modal]").addEventListener("click", close);
    $("btn-shortcuts").addEventListener("click", open);
    shortcutsApi = { open, close, isOpen: () => !backdrop.hidden };
}

function initGlobalShortcuts() {
    document.addEventListener("keydown", (e) => {
        const mod = e.ctrlKey || e.metaKey;
        const target = e.target;
        const typing = target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.tagName === "SELECT" || target.isContentEditable);

        if (mod && (e.key === "k" || e.key === "K")) {
            e.preventDefault();
            if (paletteApi.isOpen && paletteApi.isOpen()) paletteApi.close();
            else { shortcutsApi.close(); paletteApi.open(); }
            return;
        }
        if (e.key === "Escape") {
            if (shortcutsApi.isOpen && shortcutsApi.isOpen()) { e.preventDefault(); shortcutsApi.close(); }
            return;
        }
        if (e.altKey && !mod && /^Digit[1-5]$/.test(e.code)) {
            e.preventDefault();
            navigateTo(TAB_IDS[Number(e.code.slice(5)) - 1]);
            return;
        }
        if (!typing && !mod && e.key === "?") {
            e.preventDefault();
            openShortcuts();
            return;
        }
        if (!typing && mod && e.key === "Enter" && tabFromHash() === "playground") {
            e.preventDefault();
            $(e.shiftKey ? "btn-transpile" : "btn-run").click();
        }
    });

    // Keep focus inside an open modal
    document.addEventListener("focusin", (e) => {
        const openModal = document.querySelector(".modal-backdrop:not([hidden]) .modal");
        if (openModal && !openModal.contains(e.target)) {
            const focusable = openModal.querySelector("input, button");
            if (focusable) focusable.focus();
        }
    });
}

/* ==========================================================================
   13. SERVER HEALTH CHECK
   ========================================================================== */
function markBackend(online) {
    state.backendOnline = online;
    const statusLabel = $("status-label");
    const statusDot = document.querySelector(".status-dot");
    statusLabel.textContent = online ? "Online" : "Offline";
    statusDot.className = `status-dot ${online ? "online" : "offline"}`;
    $("connection-status").title = online
        ? "Compiler backend online"
        : "Compiler backend unreachable (static mode). Start it with: python3 web/server.py";
}

async function checkBackendHealth() {
    try {
        const res = await fetch("/api/presets", { cache: "no-store" });
        if (!res.ok) throw new Error("Bad response");
        activePresets = await res.json();
        markBackend(true);
        scheduleLiveCheck();
    } catch {
        markBackend(false);
        scheduleHealthCheck(15000);
    }
}

function scheduleHealthCheck(delay) {
    clearTimeout(state.healthTimer);
    state.healthTimer = setTimeout(checkBackendHealth, delay);
}
