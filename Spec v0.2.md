# C-- v0.2.0 — Specification Addendum

**Amends:** `docs/SPEC.md` (v0.1.0). **Target version:** 0.2.0.
**Status:** Normative. Where this addendum and `SPEC.md` disagree, this addendum wins. Prompt P1 merges this text into `docs/SPEC.md`; after that merge, `docs/SPEC.md` is again the single source of truth.
**The "Rule Against Assumptions" of SPEC §1.5 remains in force.** Every message, code, position and format below is normative character for character. If anything is unclear, STOP and ask.

> **Editorial note on completion.** Sections **A1–A6** are the original text, unchanged. Sections **A7–A13** were written to complete the addendum. Because `SPEC.md` (v0.1.0) was not available while writing, every item in A7–A13 that is not derivable from A1–A6 is marked **[PROPOSED]**. Under the Rule Against Assumptions, a **[PROPOSED]** item is *not* normative until confirmed. The open points are collected in **§A13**.

---

## A1. Scope of v0.2.0

### A1.1 New features
1. **Input:** the built-in functions `input`, `parse_int`, `parse_float` (§A6.2).
2. **String literals** in single quotes `'...'`, double quotes `"..."` and triple quotes `'''...'''` / `"""..."""` (§A3.3).
3. **String indexing** `s[i]` and `s.len()` (§A6.3).
4. **User-defined functions** with parameters, return values, `return` and recursion (§A6.1).
5. **`switch` / `case` / `default`** without fall-through (§A6.5).
6. **Data structures:** `array<T>`, `list<T>`, `stack<T>`, `queue<T>` (§A6.4).
7. **Web app** (online compiler/playground) with documentation (§A11).

### A1.2 Still NOT in the language (do not implement)
String concatenation or any string operator except `==`/`!=`; `break`/`continue`; nested collections (`array<array<int>>`); maps/sets; global variables or constants; nested functions; first-class functions or function pointers; function overloading (except the built-in `input`); default or variadic parameters; a character type; `switch` on `float`/`bool`; `for-each` loops; casts; `str()`; formatted printing; negative indexing; slicing; unsigned integers; structs/enums/`Option`/`Result`/ownership.

---

## A2. Changes to v0.1.0 behaviour (breaking, intentional)

| # | Change |
|---|--------|
| 1 | Words that were **reserved** become **active keywords**: `return int float bool string`. New active keywords: `switch case default array list stack queue`. Programs that used them as identifiers must be renamed. All other reserved words stay reserved. |
| 2 | **Program structure** (SPEC §5.1) becomes `module <name>;` followed by **one or more** function definitions, in any order. Exactly one must be named `main`, with no parameters and no return type. |
| 3 | **S002** (`unexpected <Y> after end of program`) is **retired**. At the top level the parser accepts only `fn` or `EOF`; any other token → S001 with `<X>` = `'fn'`. |
| 4 | The characters `'`, `[`, `]`, `,`, `:`, `.` are no longer lexical error L001; they start strings or are tokens (§A3). A `.` directly after digits is still handled by the number-lexing algorithm (`1.` stays L007). |
| 5 | **Expression statements** remain forbidden, **except** call statements and method-call statements (§A5). |
| 6 | Version strings: `cmm --version` prints `cmm 0.2.0`; `cmm.__version__ == "0.2.0"`; `pyproject.toml` version `0.2.0`. |
| 7 | The C backend supports only the v0.1 feature subset (+ phase 2 if P8 is run). See §A10. |
| 8 | **Existing tests/examples affected** (the agent must update them deliberately and report each change in a table `old expectation → new expectation → reason`): reserved-word lexer tests; the L001 test that uses `'`; S001/S002 parser tests (top-level tokens, `assignment operator` position); example `syntax_text_after_main`; `--version` tests; any test that lists all keywords. |

---

## A3. Lexical Changes

### A3.1 New and changed tokens
Add these token types (names exact): `ARROW` (`->`), `COMMA` (`,`), `COLON` (`:`), `DOT` (`.`), `LBRACKET` (`[`), `RBRACKET` (`]`).
Keyword token types: `RETURN SWITCH CASE DEFAULT KW_INT KW_FLOAT KW_BOOL KW_STRING KW_ARRAY KW_LIST KW_STACK KW_QUEUE`.
Updated lists:
* Active keywords: `module fn main let mut if else while do for print true false return switch case default int float bool string array list stack queue`
* Reserved words: `break continue struct enum match import null defer loop in as const var type`

`->` is lexed by longest match (`-` followed by `>`). `--` is still L010 (so `-->` is L010).

### A3.2 Built-in names
`input`, `parse_int`, `parse_float` are **ordinary identifiers** to the lexer. They are predefined functions (§A6.2) that user code may not redefine (E010).

### A3.3 String literals (replaces SPEC §3.5 "String literal")
There are four forms; all produce the token type `STRING` with the processed value:

| Form | Delimiter | Spans lines? | Notes |
|------|-----------|--------------|-------|
| single-quoted | `'...'` | no | A `"` inside needs no escape. |
| double-quoted | `"..."` | no | A `'` inside needs no escape. |
| triple single | `'''...'''` | yes | |
| triple double | `"""..."""` | yes | |

Rules (exact):
1. When the lexer meets a quote character `q` (`'` or `"`): if the next two characters are also `q`, a **triple-quoted** string starts; otherwise a **single-line** string starts. Therefore `""` and `''` are empty strings only when not followed by a third `q`.
2. **Single-line:** ends at the next unescaped `q`. A raw newline or end of file first → **L002** at the opening quote.
3. **Triple-quoted:** ends at the **first** unescaped run of three consecutive `q` characters. The content may contain newlines (already normalized to `\n`), the other quote character, and one or two consecutive `q`. End of file first → **L002** at the opening quotes. There is no stripping of a leading newline and no indentation processing. To end a triple-quoted string with a quote character, escape it (`\"`).
4. **Escapes** (all four forms; no others): `\n` `\t` `\r` `\"` `\'` `\\`. Any other character after a backslash → **L003**, `<c>` shown as the character itself (a newline is shown as `U+000A`). A backslash at end of file → L002.
5. Strings may contain any Unicode character except where stated above.
6. Strings printed **inside collections** are always shown in double quotes (§A6.7).

### A3.4 Impact on other lexical errors
L001 no longer applies to `' [ ] , : .`. All other lexical rules and codes (L001–L012) are unchanged.

---

## A4. Types

Types are `int`, `float`, `bool`, `string` and the composite types
`array<T>`, `list<T>`, `stack<T>`, `queue<T>` with `T` ∈ {`int`, `float`, `bool`, `string`} (no nesting).
Type names in messages are written exactly like that (e.g. `array<int>`, `stack<string>`).
Composite types are equal only if both the collection kind and `T` are equal. The **length of an array is not part of its type**.
**Defaults:** there are no implicit default values anywhere; constructors always state their initial contents (§A6.4).
**No operators** apply to composite types (including `==`/`!=`). They may be assigned, passed, returned, printed, indexed (array/list) and used through methods.

---

## A5. Complete Grammar (replaces SPEC §5.2; EBNF)

```
program      = "module" IDENT ";" function { function } EOF ;

function     = "fn" ( IDENT | "main" ) "(" [ param { "," param } ] ")" [ "->" type ] block ;
param        = IDENT ":" type ;
type         = "int" | "float" | "bool" | "string" | collType ;
collType     = ( "array" | "list" | "stack" | "queue" ) "<" elemType ">" ;
elemType     = "int" | "float" | "bool" | "string" ;

block        = "{" { statement } "}" ;
statement    = varDecl | assignStmt | callStmt | printStmt | returnStmt
             | ifStmt | whileStmt | doWhileStmt | forStmt | switchStmt | block ;

varDecl      = ( "let" | "mut" ) IDENT "=" expr ";" ;
assignStmt   = assignment ";" ;
assignment   = IDENT [ "[" expr "]" ] assignOp expr ;
assignOp     = "=" | "+=" | "-=" | "*=" | "/=" | "%=" ;
callStmt     = ( call | methodCall ) ";" ;
printStmt    = "print" "(" expr ")" ";" ;
returnStmt   = "return" [ expr ] ";" ;

ifStmt       = "if" "(" expr ")" block [ "else" ( ifStmt | block ) ] ;
whileStmt    = "while" "(" expr ")" block ;
doWhileStmt  = "do" block "while" "(" expr ")" ";" ;
forStmt      = "for" "(" forInit [ expr ] ";" [ assignment ] ")" block ;
forInit      = varDecl | assignStmt | ";" ;

switchStmt   = "switch" "(" expr ")" "{" caseClause { caseClause } [ defaultClause ] "}" ;
caseClause   = "case" caseValue { "," caseValue } ":" block ;
defaultClause= "default" ":" block ;
caseValue    = INT | "-" INT | STRING ;

expr         = or ;  (* or, and, equality, comparison, term, factor: unchanged from SPEC §5.2 *)
unary        = ( "!" | "-" ) unary | postfix ;
postfix      = primary { "[" expr "]" } ;
primary      = INT | FLOAT | STRING | "true" | "false"
             | arrayLiteral | newCollection | call | methodCall | IDENT | "(" expr ")" ;
arrayLiteral = "[" expr { "," expr } "]" ;
newCollection= ( "array" | "list" | "stack" | "queue" ) "<" elemType ">" "(" [ args ] ")" ;
call         = ( IDENT | "main" ) "(" [ args ] ")" ;
methodCall   = IDENT "." IDENT "(" [ args ] ")" ;
args         = expr { "," expr } ;
```

Notes (normative):
1. A statement that starts with `IDENT` is classified by its **next token**: `(` → call statement; `.` → method-call statement; `[` or an assignment operator → assignment. Anything else → S001 with `<X>` = `assignment, call or method call`.
2. Methods can be called only on **variables** (`IDENT "." IDENT ...`), never on literals, calls or other expressions.
3. Indexing (`[ ]`) chains: `s[0][0]` is syntactically valid.
4. Precedence (SPEC §5.3) gains a new top level: **postfix** (`[ ]`, calls, method calls) binds tighter than prefix `!`/`-`. So `-a[0]` is `-(a[0])`.
5. In `for`, the update is an `assignment` (an element target `a[i] += 1` is allowed); calls are not allowed there.
6. Nesting limit 200 (S004) now also counts `switch` bodies, call arguments, array literals and index expressions.
7. `case` values must be literals (`INT`, `-` `INT`, or `STRING`); no expressions, no ranges.
8. `<` and `>` in `array<int>` appear only right after `array/list/stack/queue`; the parser always knows they delimit a type there. `>>` never occurs (no nesting).

---

## A6. Semantics

### A6.1 Functions
1. All functions are defined at the top level, in any order; calls to functions defined later are valid (the analyzer collects all signatures first). There are no nested functions.
2. Syntax: `fn name(p1: T1, p2: T2) -> R { ... }`. `-> R` is optional; without it the function **returns nothing** (a *void* function). `main` must have no parameters and no `-> R` (E017).
3. **Parameters** are immutable bindings (as if declared with `let`) living in a scope that **encloses** the body block, so the body may shadow a parameter name. Duplicate parameter names → E031.
4. **Function names and variable names are separate namespaces.** `f` as an expression always means a variable; `f(...)` always means a function. Two functions with the same name → E009. Defining a function named like a built-in → E010. Calling an undefined function → E008. Calling `main` → E019.
5. **Calls:** arguments are evaluated left to right in the caller's scope; each argument's type must **exactly equal** the parameter's type (no implicit `int`→`float`). A call to a function with a return type is an expression; a call to a void function may only appear as a call statement (E020 otherwise). A call statement may call any function; a returned value is discarded.
6. **Pass and return by value:** every argument and returned value is copied (collections are copied, §A6.6). A callee can never change a caller's variable.
7. **Return rules:** in a function with return type `R`, `return expr;` requires `type(expr) == R` (E016) and bare `return;` is E015. In a void function `return;` is allowed and `return expr;` is E014. Executing `return` ends the function immediately.
8. **Every path must return** (E013) in a function with a return type, using this conservative rule *"definitely returns"*:
   * `return ...;` definitely returns.
   * A block definitely returns if **any** of its statements definitely returns.
   * `if ... else ...` (with a final `else`) definitely returns if **all** branches do; an `if` without a final `else` does not.
   * `switch` definitely returns if it has a `default` and **all** case bodies and the default body definitely return.
   * `while`, `for` do not (even `while (true)`). `do { A } while (c);` definitely returns if `A` does.
   * All other statements do not.
9. **Execution:** each call creates a fresh environment containing only its parameters (no access to the caller's variables; there are no globals). **Call depth limit: 1000** nested calls (`main` is depth 0); exceeding it is runtime error **R007**. The implementation MUST make this limit work identically on Windows, macOS and Linux (for Python: raise `sys.setrecursionlimit` appropriately and run the interpreter in a thread created after `threading.stack_size(<large>)`, e.g. 256 MB) and MUST have a test where unbounded recursion yields R007, not a crash. If the limit cannot be met on some platform, STOP and ask; do not lower it silently.
10. **Recursion** (direct and mutual) is allowed.

### A6.2 Built-in functions and input
Built-ins live in the function namespace and cannot be redefined. Their signatures (data, not scattered `if`s, in `cmm/builtins.py`):

| Call | Result | Behaviour |
|------|--------|-----------|
| `input()` | `string` | Reads one line from standard input. |
| `input(prompt)` | `string` | `prompt` must be `string`. Writes it to stdout **without** a newline, **flushes stdout**, then reads one line. |
| `parse_int(s)` | `int` | `s` must be `string`. |
| `parse_float(s)` | `float` | `s` must be `string`. |

**`input` reading rules (exact):**
* Standard input is read as bytes, one line at a time (so interactive use works), decoded as **strict UTF-8** (invalid → **R011**).
* The line ends at `\n`. One trailing `\n` is removed, then one trailing `\r` if present. Nothing else is trimmed. A final line without a newline is returned as is. A line that is empty after removal returns `""`.
* If end of input is reached **before any byte** is read → **R008**.

**`parse_int(s)`:** strip leading/trailing spaces and tabs; then the text must match `[+-]?[0-9]+` (decimal digits only, leading zeros allowed, no underscores) and fit in 64-bit signed range; otherwise **R009** (the message shows the original, unstripped text).
**`parse_float(s)`:** strip leading/trailing spaces and tabs; text must match `[+-]?[0-9]+(\.[0-9]+)?([eE][+-]?[0-9]+)?`; the value is converted with correct rounding; if infinite → **R010**; any mismatch → **R010**. `inf`, `nan`, hex and underscores are rejected.

### A6.3 String indexing and length
* `s[i]`: `s` is a `string` (variable, literal or any expression), `i` is an `int` (else E025). The result is a `string` of **exactly one Unicode code point**. Indexing is **zero-based** by code point. An index `< 0` or `>= length` → **R006** (negative indices do not wrap).
* `s.len()` returns the number of code points as `int`.
* Strings are immutable: `s[i] = x;` → E030.
* Indexing a non-indexable type (`int`, `float`, `bool`, `stack<T>`, `queue<T>`) → E024.

### A6.4 Collections
**Creation (exact forms):**

| Expression | Type | Meaning |
|------------|------|---------|
| `[e1, e2, …, en]` | `array<T>` | `n ≥ 1`; all `ei` must have the **same** type `T`, one of the four primitives (else E027). No empty array literal, no trailing comma. |
| `array<T>(n, fill)` | `array<T>` | `n` is an `int` (negative → R014; above 10 000 000 → R013); `fill` has type `T`; the array has `n` copies of `fill`. |
| `list<T>()` | `list<T>` | empty list |
| `stack<T>()` | `stack<T>` | empty stack |
| `queue<T>()` | `queue<T>` | empty queue |

Wrong argument count/type for a constructor uses E011/E012 with `<kind>` = `constructor` and the name `array`, `list`, `stack` or `queue`.

**Element access:** `a[i]` for `array<T>` and `list<T>` returns `T`. Index must be `int` (E025). Out of range → **R006** (`index out of range (index <i>, length <n>)`). Assignment `a[i] = v;` and `a[i] op= v;` require `a` to be a **`mut`** array/list (E029 otherwise), `type(v)` to match `T` exactly for `=`, and for `op=` the operation `T op type(v)` must be valid with result type `T` (same E006/E007 rules as SPEC §6.3).

**Methods** (called as `name.method(args)`; a method not in the table → E026; wrong arity → E011; wrong argument types → E012):

| Receiver | Method | Parameters | Result | Mutates | Runtime errors |
|----------|--------|-----------|--------|---------|----------------|
| `string` | `len` | – | `int` | no | – |
| `array<T>` | `len` | – | `int` | no | – |
| `list<T>` | `len` | – | `int` | no | – |
| `list<T>` | `is_empty` | – | `bool` | no | – |
| `list<T>` | `contains` | `T` | `bool` | no | – |
| `list<T>` | `push` | `T` | none | yes | R013 if length would exceed the limit |
| `list<T>` | `pop` | – | `T` | yes | R012 if empty (removes and returns the **last** element) |
| `list<T>` | `insert` | `int, T` | none | yes | R006 unless `0 ≤ index ≤ length`; R013 |
| `list<T>` | `remove` | `int` | `T` | yes | R006 unless `0 ≤ index < length` |
| `list<T>` | `clear` | – | none | yes | – |
| `stack<T>` | `push` | `T` | none | yes | R013 |
| `stack<T>` | `pop` | – | `T` | yes | R012 if empty (LIFO) |
| `stack<T>` | `peek` | – | `T` | no | R012 if empty |
| `stack<T>` | `len` / `is_empty` / `clear` | – | `int` / `bool` / none | no / no / yes | – |
| `queue<T>` | `enqueue` | `T` | none | yes | R013 |
| `queue<T>` | `dequeue` | – | `T` | yes | R012 if empty (FIFO, removes the **front**) |
| `queue<T>` | `peek` | – | `T` | no | R012 if empty (returns the front) |
| `queue<T>` | `len` / `is_empty` / `clear` | – | `int` / `bool` / none | no / no / yes | – |

A **mutating** method on a variable declared `let` → E028. A method returning "none" is void: used as a call statement only (E020-style rule applies: `method '<name>' returns no value and cannot be used in an expression`, reported as E020 with `method` instead of `function`). `contains` compares with `==` semantics of `T`.
**Size limit:** a collection can hold at most **10 000 000** elements (R013).

### A6.5 `switch`
```
switch (selector) {
    case 1, 2: { ... }
    case 3:    { ... }
    default:   { ... }
}
```
* The selector is evaluated **once**; its type must be `int` or `string` (E021).
* Every case value must be a literal of the **same type** as the selector (E022; `-5` counts as an int literal). The same value twice anywhere in the switch → E023.
* Execution: compare the selector with the case values in source order using `==`. The **first** matching clause's block executes, then the switch ends. **There is no fall-through and no `break`.** If nothing matches, the `default` block runs if present; otherwise nothing happens.
* At least one `case` is required; `default` is optional, must be last, and appears at most once. Every body is a block (own scope).
* `return` inside a case body returns from the function.

### A6.6 Value semantics and mutability of collections
* Assigning (`let b = a;`, `x = a;`), passing as an argument and returning a collection **copies** it. Two variables never share a collection. (Implementations may use copy-on-write or lazy copying only if the observable behaviour is identical.)
* `let` makes the variable **deeply immutable**: no element assignment, no mutating methods (E028/E029). `mut` allows both.
* Strings are immutable values.

### A6.7 Printing (extends SPEC §9)
| Type | Text |
|------|------|
| `array<T>`, `list<T>` | `[` + elements separated by `, ` + `]`; empty → `[]` |
| `stack<T>` | `stack[` + elements from **bottom to top**, separated by `, ` + `]` |
| `queue<T>` | `queue[` + elements from **front to back**, separated by `, ` + `]` |

Elements use the primitive formats of SPEC §9, except that **strings are shown in double quotes** with `\n \t \r \" \\` escaped (a `'` is not escaped).

---

## A7. Diagnostics catalog for v0.2.0 **[PROPOSED]**

Codes and triggers below are taken from A2–A6. The **message templates and reported positions are proposed**, because SPEC §7 (the v0.1.0 message format) was not available. Confirm against SPEC §7 before merging. The positional convention assumed is "line:column of the token named in the *Position* column".

### A7.1 Semantic errors (E)

| Code | Trigger (source) | Proposed message | Position |
|------|------------------|------------------|----------|
| E008 | Call to an undefined function (§A6.1.4) | `undefined function '<name>'` | the function name |
| E009 | Two functions with the same name (§A6.1.4) | `function '<name>' is already defined` | the second definition's name |
| E010 | Function named like a built-in (§A6.1.4, §A3.2) | `cannot redefine built-in function '<name>'` | the function name in the definition |
| E011 | Wrong argument count (calls, methods, constructors, built-ins) | `<kind> '<name>' expects <n> argument(s), got <m>` | the call's name (or the method name) |
| E012 | Wrong argument type | `argument <k> of <kind> '<name>' must be <T>, got <U>` | the offending argument |
| E013 | A path does not return (§A6.1.8) | `function '<name>' does not return a value on all paths` | the function name |
| E014 | `return expr;` in a void function | `void function '<name>' cannot return a value` | the `return` token |
| E015 | Bare `return;` in a function with a return type | `function '<name>' must return a value of type <R>` | the `return` token |
| E016 | `return expr;` with the wrong type | `cannot return <U> from function '<name>' declared to return <R>` | the returned expression |
| E017 | `main` has parameters or `-> R` | `'main' must have no parameters and no return type` | the `main` name |
| E019 | Call to `main` | `'main' cannot be called` | the call's name |
| E020 | Void function/method used as a value | `<kind> '<name>' returns no value and cannot be used in an expression` (`<kind>` = `function` or `method`) | the call |
| E021 | `switch` selector not `int`/`string` | `switch selector must be int or string, got <T>` | the selector expression |
| E022 | Case value type ≠ selector type | `case value of type <U> does not match switch selector of type <T>` | the case value |
| E023 | Duplicate case value | `duplicate case value <v>` | the second occurrence |
| E024 | Indexing a non-indexable type | `type <T> cannot be indexed` | the `[` token |
| E025 | Index is not `int` | `index must be int, got <T>` | the index expression |
| E026 | Unknown method for the receiver type | `type <T> has no method '<name>'` | the method name |
| E027 | Array literal with mixed or non-primitive element types | `array literal elements must all have the same primitive type` | the first offending element |
| E028 | Mutating method on a `let` variable | `cannot call mutating method '<name>' on immutable variable '<v>'` | the method name |
| E029 | Element assignment on a non-`mut` array/list | `cannot assign to element of immutable variable '<v>'` | the variable |
| E030 | Assignment to a string element | `strings are immutable; cannot assign to an element` | the variable |
| E031 | Duplicate parameter name | `duplicate parameter '<name>'` | the second parameter |

`E018` is **not referenced anywhere in this addendum** (see §A13, question 1). Do not assign it silently.

### A7.2 Runtime errors (R)

| Code | Trigger (source) | Proposed message |
|------|------------------|------------------|
| R006 | Index out of range (§A6.3, §A6.4) | `index out of range (index <i>, length <n>)` **(exact, given in §A6.4)** |
| R007 | Call depth > 1000 (§A6.1.9) | `call depth limit exceeded (1000)` |
| R008 | End of input before any byte (§A6.2) | `end of input` |
| R009 | `parse_int` failure | `cannot convert '<original text>' to int` |
| R010 | `parse_float` failure or infinity | `cannot convert '<original text>' to float` |
| R011 | Invalid UTF-8 on stdin | `standard input is not valid UTF-8` |
| R012 | `pop`/`peek`/`dequeue` on an empty collection | `<method> on empty <kind>` (e.g. `pop on empty stack`) |
| R013 | Collection would exceed 10 000 000 elements | `collection size limit exceeded (10000000)` |
| R014 | `array<T>(n, fill)` with `n < 0` | `array size must not be negative (got <n>)` |

### A7.3 Syntax errors (S) affected
* **S001** is the only top-level syntax error; at top level `<X>` = `'fn'` (A2 #3).
* **S001** for a statement starting with an identifier followed by an unexpected token uses `<X>` = `assignment, call or method call` (A5 note 1).
* **S002** is retired and must not be emitted. The code number must not be reused.
* **S004** (nesting limit 200) now also counts `switch` bodies, call arguments, array literals and index expressions (A5 note 6).

---

## A8. Implementation structure **[PROPOSED]**

### A8.1 Modules
| Module | Responsibility |
|--------|----------------|
| `cmm/lexer.py` | Token types of §A3.1; string rules of §A3.3. |
| `cmm/parser.py` | Grammar of §A5; produces the AST below. |
| `cmm/ast.py` | AST node classes. |
| `cmm/types.py` | Type representation (`Prim`, `Coll(kind, elem)`), equality, name formatting (§A4). |
| `cmm/builtins.py` | Table of built-in signatures (§A6.2) and **method table** (§A6.4) as data. |
| `cmm/analyzer.py` | Pass 1: collect all function signatures. Pass 2: check each body. |
| `cmm/interpreter.py` | Evaluation, environments, call stack, collections, runtime errors. |
| `cmm/runtime_io.py` | Byte-wise line reader for `input` (§A6.2), stdout flushing. |
| `cmm/cli.py` | `cmm --version` → `cmm 0.2.0`; existing subcommands unchanged. |

### A8.2 New AST nodes
`FunctionDef(name, params, ret_type|None, body)`, `Param(name, type)`, `Call(name, args)`, `MethodCall(receiver_name, method, args)`, `Index(target, index)`, `ArrayLiteral(elements)`, `NewCollection(kind, elem, args)`, `ReturnStmt(expr|None)`, `SwitchStmt(selector, cases, default|None)`, `CaseClause(values, block)`, `IndexAssign(name, index, op, expr)`.
Every node carries line and column of its first token.

### A8.3 Analyzer algorithm
1. **Pass 1:** for each `FunctionDef`, in source order, register `name → signature`. Report E009 (duplicate), E010 (built-in name). Verify `main` exists and has no params/return type (E017). *(What happens when `main` is missing is defined by SPEC v0.1.0; keep that behaviour — see §A13, question 3.)*
2. **Pass 2:** for each function, create a scope with its parameters (E031 on duplicates, all immutable), then check the body block in a child scope so shadowing a parameter is allowed.
3. Track per-variable `(type, mutable)`. Element assignment and mutating methods require `mutable` (E029/E028).
4. Check calls against the function table or the built-in table; calls to void functions are legal only as statements (E020).
5. After checking a function with return type `R`, apply the *definitely returns* rule of §A6.1.8 (E013).
6. Check `switch` per §A6.5 (E021–E023 and the at-least-one-case rule, which is a parse rule: S001).

### A8.4 Interpreter notes
* One **environment per call**, containing only parameters; no access to the caller's environment.
* **Return** is implemented with an internal control-flow signal, not a Python exception visible to the user.
* **Depth counter:** `main` at depth 0; entering a call at depth 1000 → R007. Python: `sys.setrecursionlimit` large enough for 1000 C-- frames plus nested expression evaluation, interpreter in a thread created after `threading.stack_size(256 * 1024 * 1024)`. Must behave identically on Windows, macOS and Linux (§A6.1.9).
* **Collections:** value semantics (§A6.6). Recommended: copy on assignment/pass/return; optimisation by copy-on-write is allowed only if unobservable.
* **Strings:** index and length by code point (Python `str` indexing satisfies this; do not use bytes).
* **`input`:** read from `sys.stdin.buffer` byte by byte until `\n` or EOF; decode strict UTF-8 once per line; flush stdout before reading when a prompt is given.

---

## A9. Required tests **[PROPOSED]**

Each item must have at least one automated test. Each error code in §A7 needs at least one test that checks code, message and position.

1. **Lexer:** all four string forms; `""` vs `""""""`; escapes (`\n \t \r \" \' \\`); L002 (newline in single-line string, EOF in triple, backslash at EOF); L003 (bad escape, newline shown as `U+000A`); `->`, `-->` (L010), `.` after digits (`1.` → L007); every new keyword and reserved word.
2. **Parser:** top-level `fn`/EOF only; statement classification by next token; chained indexing `s[0][0]`; `-a[0]`; `for` with element-target update; `case` with `-INT` and STRING; nesting limit 200 through each newly counted construct (switch, call args, array literal, index).
3. **Analyzer:** one test per code E008–E031 (except E018); definitely-returns rule for every case listed in §A6.1.8; parameter shadowing; separate function/variable namespaces; forward calls and mutual recursion.
4. **Interpreter:** value semantics (mutating a copy does not change the original, through assign, pass, return); R006 for negative index; every method in the table including its R012/R013 behaviour; `switch` with no fall-through and `default`; `return` inside `switch`; printing format for all composite types with strings inside.
5. **Input:** `\n`, `\r\n`, final line without newline, empty line, EOF → R008, invalid UTF-8 → R011, prompt flush order; `parse_int` (spaces/tabs, `+`/`-`, leading zeros, 64-bit boundaries, overflow, underscores, empty) and `parse_float` (exponent, `inf`/`nan`/hex rejected, overflow → R010).
6. **Recursion:** unbounded recursion yields **R007**, not a crash, on all three platforms (CI matrix: Windows, macOS, Linux).
7. **Regression:** every changed v0.1.0 test, listed in the table required by §A2 #8 (`old expectation → new expectation → reason`).
8. **Examples:** `examples/` gains at least one program per feature (input, strings, functions, recursion, switch, each collection) with expected output files, plus negative examples for the main error classes.

---

## A10. C backend **[PROPOSED]**

* The C backend supports only the **v0.1 feature subset**. Because v0.1.0 programs had no functions, a v0.1-style program must be expressible as `module m; fn main() { ... }`; the backend compiles exactly that shape.
* A program that uses any v0.2 feature (user functions other than `main`, strings beyond what v0.1 supported, `input`, `switch`, collections, indexing) must be **rejected by the C backend before any C is generated**, with a clear error that names the unsupported feature and exits non-zero. The exact code and text are an open point (§A13, question 4).
* Phase 2 (P8), if run, may add features; it must extend this section first.

---

## A11. Web app (online compiler / playground) **[PROPOSED]**

### A11.1 Goals
Let a visitor write C-- source, run it, see output and diagnostics, supply stdin, and read the language documentation, with no local install.

### A11.2 Architecture
* **Backend** (Python, reuses the `cmm` package unchanged): `POST /api/run` and `POST /api/check`, JSON in and out.
  * Request: `{"source": "<text>", "stdin": "<text>"}` (`stdin` optional, default empty).
  * Response: `{"ok": bool, "stdout": "<text>", "diagnostics": [{"code": "E013", "message": "...", "line": 3, "column": 5}], "runtime_error": null | {"code": "R006", "message": "...", "line": 7, "column": 9}}`.
* **Frontend:** a static single-page app with a code editor, an stdin box, a Run button, an output panel and a diagnostics list (clicking one jumps to its line:column). Works on a phone-sized viewport.
* **Documentation pages:** generated from the merged `docs/SPEC.md` plus a short tutorial and one runnable example per feature (each with an "Open in playground" button).

### A11.3 Execution safety (mandatory)
Run each program in a **separate process** with: wall-clock limit **5 s**; output cap **1 MB** (truncate with a visible notice); memory limit **256 MB**; no network and no file access; one run at a time per client, with rate limiting. Source size limit **100 KB**, stdin limit **100 KB**.

### A11.4 Input behaviour
Interactive prompting is not available in the browser; the program reads from the supplied stdin text, line by line. When the supplied text is exhausted, `input` raises R008 as in the CLI.

### A11.5 Versions
The footer and `/api/version` report `0.2.0`.

---

## A12. Versioning, migration and acceptance **[PROPOSED]**

1. **Version strings** exactly as in §A2 #6.
2. **Merge:** after P1, `docs/SPEC.md` contains this text integrated; this addendum file is then removed or marked superseded.
3. **Migration note** (in `CHANGELOG.md` and the docs): list the words that became keywords (`return int float bool string switch case default array list stack queue`), the new program structure (`module` + `fn main()`), and the retirement of S002.
4. **Acceptance checklist:**
   * [ ] All tests of §A9 pass on Windows, macOS and Linux.
   * [ ] The §A2 #8 change table is delivered.
   * [ ] `cmm --version` prints `cmm 0.2.0`.
   * [ ] Unbounded recursion → R007 on all platforms.
   * [ ] C backend rejects v0.2-only programs cleanly (§A10).
   * [ ] Web app runs with the limits of §A11.3.
   * [ ] No feature of §A1.2 has been implemented.

---

## A13. Open points to confirm (Rule Against Assumptions)

1. **E018** is skipped between E017 and E019 and is not used anywhere in this addendum. Is it already assigned in SPEC v0.1.0, intentionally reserved, or missing?
2. **Message texts and positions** for E008–E031 and R007–R014 (except R006, whose text is given in §A6.4): confirm or replace the proposals of §A7 against SPEC §7.
3. **Missing `main`:** which code and message apply when no function named `main` exists? (The addendum says only "exactly one must be named `main`".) Same question for two functions named `main` (E009 presumably).
4. **C backend rejection:** which error code/text is emitted when a v0.2-only feature reaches the C backend (§A10)?
5. **`input` with wrong arguments:** `input(1, 2)` or `input(5)` — presumably E011/E012 with `<kind>` = `function`; confirm.
6. **Array methods:** `array<T>` has only `len` in §A6.4 (no `contains`, `is_empty`). Intentional?
7. **Printing a `string` that contains a non-BMP or control character** inside a collection: only `\n \t \r \" \\` are escaped per §A6.7. Confirm that other control characters are printed raw.
8. **`for` header:** `forInit` already ends with `;` for `varDecl`/`assignStmt`, and `";"` alone is allowed as an empty init. Confirm that `for (;;)` and `for (let i = 0; i < n; i += 1)` are both intended to parse under the given EBNF.
9. **Web app hosting target** (single VM, container, serverless) and whether the 5 s / 256 MB / 1 MB limits of §A11.3 are acceptable.