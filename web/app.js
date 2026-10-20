/**
 * C-- Interactive Compiler Explorer & Language Specification
 * Client Controller & Compiler Pipeline API Client
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

document.addEventListener("DOMContentLoaded", () => {
    initThemeToggle();
    initNavigationTabs();
    initCodeEditor();
    initSplitResizer();
    initOutputTabs();
    initPresets();
    initReferenceLoaders();
    initActionButtons();
    checkBackendHealth();
});

/* ==========================================================================
   1. THEME TOGGLE (DARK / LIGHT)
   ========================================================================== */
function initThemeToggle() {
    const toggleBtn = document.getElementById("btn-theme-toggle");
    if (!toggleBtn) return;

    const savedTheme = localStorage.getItem("cmm-theme");
    if (savedTheme === "light") {
        document.body.classList.remove("dark-theme");
        document.body.classList.add("light-theme");
    }

    toggleBtn.addEventListener("click", () => {
        const isLight = document.body.classList.contains("light-theme");
        if (isLight) {
            document.body.classList.remove("light-theme");
            document.body.classList.add("dark-theme");
            localStorage.setItem("cmm-theme", "dark");
        } else {
            document.body.classList.remove("dark-theme");
            document.body.classList.add("light-theme");
            localStorage.setItem("cmm-theme", "light");
        }
    });
}

/* ==========================================================================
   2. NAVIGATION TABS (TOP BAR)
   ========================================================================== */
function initNavigationTabs() {
    const tabButtons = document.querySelectorAll(".nav-tab");
    const tabViews = document.querySelectorAll(".tab-view");

    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");

            tabButtons.forEach(b => b.classList.remove("active"));
            tabViews.forEach(v => v.classList.remove("active"));

            btn.classList.add("active");
            const targetView = document.getElementById(`view-${targetTab}`);
            if (targetView) {
                targetView.classList.add("active");
            }
        });
    });
}

/* ==========================================================================
   3. CODE EDITOR & LINE GUTTER SYNCHRONIZATION
   ========================================================================== */
function initCodeEditor() {
    const editor = document.getElementById("code-editor");
    const gutter = document.getElementById("line-gutter");
    const lineColIndicator = document.getElementById("editor-line-col");
    const charCountIndicator = document.getElementById("editor-char-count");
    const copySourceBtn = document.getElementById("btn-copy-source");

    function updateLineNumbers() {
        const lines = editor.value.split("\n");
        const lineCount = lines.length;
        gutter.innerHTML = Array.from({ length: lineCount }, (_, i) => i + 1).join("<br>");
        charCountIndicator.textContent = `${editor.value.length} chars`;
    }

    function updateCursorPosition() {
        const pos = editor.selectionStart;
        const textBefore = editor.value.substring(0, pos);
        const lines = textBefore.split("\n");
        const currentLine = lines.length;
        const currentCol = lines[lines.length - 1].length + 1;
        lineColIndicator.textContent = `Ln ${currentLine}, Col ${currentCol}`;
    }

    editor.addEventListener("scroll", () => {
        gutter.scrollTop = editor.scrollTop;
    });

    editor.addEventListener("input", () => {
        updateLineNumbers();
        updateCursorPosition();
    });

    editor.addEventListener("click", updateCursorPosition);
    editor.addEventListener("keyup", updateCursorPosition);

    editor.addEventListener("keydown", (e) => {
        if (e.key === "Tab") {
            e.preventDefault();
            const start = editor.selectionStart;
            const end = editor.selectionEnd;
            editor.value = editor.value.substring(0, start) + "    " + editor.value.substring(end);
            editor.selectionStart = editor.selectionEnd = start + 4;
            updateLineNumbers();
            updateCursorPosition();
        } else if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === "Enter") {
            e.preventDefault();
            document.getElementById("btn-transpile").click();
        } else if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
            e.preventDefault();
            document.getElementById("btn-run").click();
        }
    });

    if (copySourceBtn) {
        copySourceBtn.addEventListener("click", () => {
            navigator.clipboard.writeText(editor.value).then(() => {
                const prev = copySourceBtn.textContent;
                copySourceBtn.textContent = "Copied";
                setTimeout(() => {
                    copySourceBtn.textContent = prev;
                }, 1400);
            });
        });
    }

    editor.value = FALLBACK_PRESETS["factorial"].code;
    updateLineNumbers();
    updateCursorPosition();
}

/* ==========================================================================
   4. INTERACTIVE SPLIT PANE RESIZER
   ========================================================================== */
function initSplitResizer() {
    const splitPane = document.getElementById("studio-split-pane");
    const resizer = document.getElementById("pane-resizer");
    if (!splitPane || !resizer) return;

    let isDragging = false;

    resizer.addEventListener("mousedown", (e) => {
        e.preventDefault();
        isDragging = true;
        resizer.classList.add("dragging");
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
    });

    window.addEventListener("mousemove", (e) => {
        if (!isDragging) return;
        const rect = splitPane.getBoundingClientRect();
        const offsetX = e.clientX - rect.left;
        const minWidth = 280;
        const maxWidth = rect.width - minWidth;
        const clamped = Math.max(minWidth, Math.min(maxWidth, offsetX));
        const pct = ((clamped / rect.width) * 100).toFixed(2);
        splitPane.style.setProperty("--left-pane-width", `${pct}%`);
    });

    window.addEventListener("mouseup", () => {
        if (!isDragging) return;
        isDragging = false;
        resizer.classList.remove("dragging");
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
    });

    resizer.addEventListener("dblclick", () => {
        splitPane.style.setProperty("--left-pane-width", "1fr");
    });
}

/* ==========================================================================
   5. OUTPUT TABS CONTROLLER
   ========================================================================== */
function initOutputTabs() {
    const outputTabs = document.querySelectorAll(".output-tab");

    outputTabs.forEach(tab => {
        tab.addEventListener("click", () => {
            const target = tab.getAttribute("data-output");
            switchOutputTab(target);
        });
    });

    document.getElementById("btn-copy-output").addEventListener("click", () => {
        const activeView = document.querySelector(".output-view.active pre");
        if (activeView) {
            navigator.clipboard.writeText(activeView.textContent).then(() => {
                const btn = document.getElementById("btn-copy-output");
                const oldText = btn.textContent;
                btn.textContent = "Copied";
                setTimeout(() => {
                    btn.textContent = oldText;
                }, 1400);
            });
        }
    });

    document.getElementById("btn-clear-output").addEventListener("click", () => {
        document.getElementById("terminal-display").innerHTML = '<span class="terminal-dim">// Console cleared.</span>';
        setStatus("Ready", "status-ready");
    });
}

function switchOutputTab(tabName) {
    const outputTabs = document.querySelectorAll(".output-tab");
    const outputViews = document.querySelectorAll(".output-view");

    outputTabs.forEach(t => {
        t.classList.toggle("active", t.getAttribute("data-output") === tabName);
    });

    outputViews.forEach(v => {
        v.classList.toggle("active", v.id === `output-view-${tabName}`);
    });
}

function setStatus(text, className) {
    const pill = document.getElementById("execution-status-pill");
    pill.textContent = text;
    pill.className = `status-pill ${className}`;
}

/* ==========================================================================
   6. PRESETS & REFERENCE SNIPPET LOADERS
   ========================================================================== */
function initPresets() {
    const select = document.getElementById("preset-select");
    const hint = document.getElementById("preset-hint");
    const editor = document.getElementById("code-editor");

    select.addEventListener("change", () => {
        const val = select.value;
        const preset = activePresets[val] || FALLBACK_PRESETS[val];
        if (preset) {
            editor.value = preset.code;
            hint.textContent = preset.description;
            editor.dispatchEvent(new Event("input"));
            setStatus("Ready", "status-ready");
        }
    });

    document.getElementById("btn-reset").addEventListener("click", () => {
        const val = select.value;
        const preset = activePresets[val] || FALLBACK_PRESETS[val];
        if (preset) {
            editor.value = preset.code;
            editor.dispatchEvent(new Event("input"));
            setStatus("Reset", "status-ready");
        }
    });
}

function initReferenceLoaders() {
    const buttons = document.querySelectorAll(".btn-load-snippet");
    const editor = document.getElementById("code-editor");
    const playgroundTabBtn = document.getElementById("tab-btn-playground");

    buttons.forEach(btn => {
        btn.addEventListener("click", () => {
            const key = btn.getAttribute("data-snippet");
            const preset = activePresets[key] || FALLBACK_PRESETS[key];
            const code = preset ? preset.code : REFERENCE_SNIPPETS[key];
            if (code) {
                editor.value = code;
                editor.dispatchEvent(new Event("input"));
                setStatus("Ready", "status-ready");
                if (playgroundTabBtn) {
                    playgroundTabBtn.click();
                }
            }
        });
    });
}

/* ==========================================================================
   7. COMPILER PIPELINE ACTIONS & API CALLS
   ========================================================================== */
function initActionButtons() {
    const editor = document.getElementById("code-editor");

    // 1. Run Program
    document.getElementById("btn-run").addEventListener("click", async () => {
        switchOutputTab("console");
        setStatus("Running...", "status-running");
        const terminal = document.getElementById("terminal-display");
        terminal.innerHTML = '<span class="terminal-dim">// Executing in C-- reference interpreter...</span>';

        const startTime = performance.now();
        try {
            const res = await fetch("/api/run", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code: editor.value, help_enabled: true })
            });
            const data = await res.json();
            const elapsedMs = (performance.now() - startTime).toFixed(1);

            if (data.success) {
                setStatus(`EXIT 0 · ${elapsedMs}ms`, "status-success");
                terminal.innerHTML = `<span class="terminal-ok">[OK] Execution completed (exit 0, ${elapsedMs}ms)</span>\n\n${escapeHtml(data.output)}`;
            } else {
                setStatus(`EXIT ${data.exit_code || 1} · ${data.stage || "error"}`, "status-error");
                terminal.innerHTML = `<span class="terminal-err">[ERROR] Stage: ${data.stage || "compiler"}</span>\n\n${escapeHtml(data.error)}`;
            }
        } catch (err) {
            setStatus("Offline", "status-error");
            terminal.innerHTML = `<span class="terminal-err">[OFFLINE] Compiler server unreachable</span>\n${escapeHtml(String(err))}\n\n<span class="terminal-dim">// Start the backend server: python3 web/server.py</span>`;
        }
    });

    // 2. Transpile to C99
    document.getElementById("btn-transpile").addEventListener("click", async () => {
        switchOutputTab("c99");
        setStatus("Transpiling...", "status-running");
        const cDisplay = document.getElementById("c99-display");
        cDisplay.innerHTML = '<span class="terminal-dim">// Lowering AST to ISO C99...</span>';

        try {
            const res = await fetch("/api/transpile", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code: editor.value, help_enabled: true })
            });
            const data = await res.json();

            if (data.success) {
                setStatus("ISO C99 Ready", "status-success");
                cDisplay.textContent = data.c_code;
            } else {
                setStatus("Transpile Error", "status-error");
                cDisplay.innerHTML = `<span class="terminal-err">[ERROR] C99 code generation failed</span>\n\n${escapeHtml(data.error)}`;
            }
        } catch (err) {
            setStatus("Server Error", "status-error");
            cDisplay.innerHTML = `<span class="terminal-err">[ERROR] Transpiler request failed</span>\n${escapeHtml(String(err))}`;
        }
    });

    // 3. Type Check
    document.getElementById("btn-check").addEventListener("click", async () => {
        switchOutputTab("console");
        setStatus("Checking...", "status-running");
        const terminal = document.getElementById("terminal-display");

        try {
            const res = await fetch("/api/run", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code: editor.value, help_enabled: true })
            });
            const data = await res.json();

            if (data.stage === "lexer" || data.stage === "parser" || data.stage === "analyzer") {
                setStatus("Type Error", "status-error");
                terminal.innerHTML = `<span class="terminal-err">[FAIL] Static verification failed (${data.stage})</span>\n\n${escapeHtml(data.error)}`;
            } else {
                setStatus("Verified", "status-success");
                terminal.innerHTML = `<span class="terminal-ok">[PASS] Lexical, syntactic, and semantic checks succeeded.</span>\nNo type or scope violations detected.`;
            }
        } catch (err) {
            terminal.innerHTML = `<span class="terminal-err">[ERROR] Verification request failed: ${escapeHtml(String(err))}</span>`;
        }
    });

    // 4. Inspect AST
    document.getElementById("btn-ast").addEventListener("click", async () => {
        switchOutputTab("ast");
        setStatus("Parsing AST...", "status-running");
        const astDisplay = document.getElementById("ast-display");
        astDisplay.innerHTML = '<span class="terminal-dim">// Constructing Abstract Syntax Tree...</span>';

        try {
            const res = await fetch("/api/ast", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code: editor.value })
            });
            const data = await res.json();
            if (data.success) {
                setStatus("AST Ready", "status-success");
                astDisplay.textContent = data.ast;
            } else {
                setStatus("Parse Error", "status-error");
                astDisplay.innerHTML = `<span class="terminal-err">[ERROR] AST construction failed</span>\n\n${escapeHtml(data.error)}`;
            }
        } catch (err) {
            astDisplay.innerHTML = `<span class="terminal-err">[ERROR] Request failed: ${escapeHtml(String(err))}</span>`;
        }
    });

    // 5. Inspect Tokens
    document.getElementById("btn-tokens").addEventListener("click", async () => {
        switchOutputTab("tokens");
        setStatus("Tokenizing...", "status-running");
        const tokensDisplay = document.getElementById("tokens-display");
        tokensDisplay.innerHTML = '<span class="terminal-dim">// Scanning lexical token stream...</span>';

        try {
            const res = await fetch("/api/tokens", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code: editor.value })
            });
            const data = await res.json();
            if (data.success) {
                setStatus("Tokens Ready", "status-success");
                tokensDisplay.textContent = data.tokens;
            } else {
                setStatus("Lex Error", "status-error");
                tokensDisplay.innerHTML = `<span class="terminal-err">[ERROR] Lexical analysis failed</span>\n\n${escapeHtml(data.error)}`;
            }
        } catch (err) {
            tokensDisplay.innerHTML = `<span class="terminal-err">[ERROR] Request failed: ${escapeHtml(String(err))}</span>`;
        }
    });
}

/* ==========================================================================
   8. SERVER HEALTH CHECK
   ========================================================================== */
async function checkBackendHealth() {
    const statusLabel = document.getElementById("status-label");
    const statusDot = document.querySelector(".status-dot");

    try {
        const res = await fetch("/api/presets");
        if (res.ok) {
            const data = await res.json();
            activePresets = data;
            statusLabel.textContent = "Server Online";
            statusDot.className = "status-dot online";
        } else {
            throw new Error("Bad response");
        }
    } catch {
        statusLabel.textContent = "Offline (Static)";
        statusDot.className = "status-dot offline";
    }
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