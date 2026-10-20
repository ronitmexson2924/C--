# C-- (C Minus Minus) — Language & Implementation Specification

**Language version:** 0.1.0 ("C-- Basic")
**File extension:** `.cmm`
**Reference implementation language:** Python 3.10+ (standard library only)
**Status:** Normative. This document is the single source of truth.

---

## 1. Purpose, Scope, and Rules for the Implementer

### 1.1 What C-- is
C-- is a small, statically checked, C-like programming language built on the principle **"safety by removal"**: dangerous features of C/C++ are removed instead of being patched. Variables are immutable by default, there is no null, no pointer arithmetic, and **no undefined behaviour**: every situation either has a precisely defined result or produces a precisely defined error.

### 1.2 What is IN this version (0.1.0)
1. Basic operators (arithmetic, comparison, logical, assignment, compound assignment).
2. Variables (`let` = immutable, `mut` = mutable) with type inference.
3. `if` / `else if` / `else`.
4. `for`, `while`, and `do-while` loops.
5. A `print` statement (required so programs can produce output).
6. Types: `int`, `float`, `bool`, `string`.
7. Program structure: `module <name>;` followed by exactly one function `fn main() { ... }`.

### 1.3 What is NOT in this version (do not implement any of it)
Functions other than `main`, parameters, return values, `return`, `break`, `continue`, arrays, structs, enums, pointers, references, ownership/borrowing, `Option`, `Result`, `defer`, imports/modules beyond the single `module` line, user input, file I/O, type annotations, type casts, `++`/`--`, the ternary operator `?:`, bitwise operators, string concatenation or any other string operator besides `==` and `!=`, global variables, constants, comments nesting, hexadecimal/binary/octal/underscored numeric literals, scientific notation without a fractional part, character literals, `switch`/`match`.

### 1.4 Keywords used in this document
The words **MUST**, **MUST NOT**, **SHOULD**, **MAY** have their RFC 2119 meaning. Text in `code font` and every message string quoted in this document is normative and must be reproduced **character for character**.

### 1.5 THE RULE AGAINST ASSUMPTIONS (highest priority)
1. Implement exactly what this document says. Do not add features, keywords, operators, CLI flags, error messages, files, or behaviours that are not described here.
2. If something seems unspecified, ambiguous, or contradictory, **STOP and ask the project owner** instead of guessing. Do not "fix" the specification silently.
3. Do not change any normative text, message, exit code, or output format because another convention seems nicer.
4. Where the host language (Python) behaves differently from this specification (for example `//` and `%` on negative numbers, unbounded integers, `repr()` of floats, `True == 1`), **this specification wins** and the behaviour must be implemented explicitly.

---

## 2. Source Files and Text Handling

| # | Rule |
|---|------|
| 2.1 | Source files use the extension `.cmm` by convention. The CLI MUST NOT refuse files with another extension. |
| 2.2 | Source files are read as **bytes** and decoded as **strict UTF-8**. Invalid UTF-8 is an I/O error (exit code 3, see §11.4), not a lexical error. |
| 2.3 | If the decoded text begins with a single U+FEFF (byte-order mark), it is removed before any other processing and does not count toward columns. |
| 2.4 | Line terminators: `\r\n` and a lone `\r` are both converted to `\n` **before** lexing. After that, only `\n` ends a line. The number of lines is unchanged by this conversion. |
| 2.5 | **Positions** are `(line, column)`, both **1-based**. The column is the count of Unicode code points from the start of the line, plus one. A tab counts as exactly **1** column. |
| 2.6 | The position of the `EOF` token is the position immediately after the last character of the (normalized) text. If the text ends with `\n`, that is column 1 of the next line. For an empty file it is `1:1`. |
| 2.7 | A trailing newline at the end of the file is optional. |
| 2.8 | All program output is encoded as **UTF-8** and every output line ends with `\n` on **every** platform (the implementation MUST NOT emit `\r\n` on Windows). |

---

## 3. Lexical Structure

The lexer converts the normalized text into a list of tokens, ending with one `EOF` token. The lexer processes the **whole file** before parsing starts. It stops at the **first** lexical error.

### 3.1 Whitespace
Only space (U+0020), tab (U+0009) and newline (U+000A) are whitespace. Whitespace separates tokens and is otherwise ignored. Any other character outside a string literal or comment that does not start a valid token is error **L001**.

### 3.2 Comments
* `//` starts a line comment that runs to the end of the line (the newline is not part of the comment).
* `/*` starts a block comment that ends at the first following `*/`. Block comments **do not nest**. The two characters of `/*` cannot be reused as part of the closing `*/` (so `/*/` is not a complete comment). Block comments may span lines. An unterminated block comment is error **L004** positioned at the opening `/*`.
* Comments may contain any characters.
* Comments are treated as whitespace.

### 3.3 Identifiers
`IDENT = [A-Za-z_][A-Za-z0-9_]*` — **ASCII only**, case-sensitive, any length. `_` alone is a valid identifier. The lexer reads the longest possible run of identifier characters and then checks whether it is a keyword (§3.4).

### 3.4 Keywords
**Active keywords** (each has its own token type, see §3.8):
`module  fn  main  let  mut  if  else  while  do  for  print  true  false`

**Reserved words** (token type `RESERVED`; they can never be used as identifiers and have no meaning in version 0.1.0):
`break  continue  return  struct  enum  match  import  null  defer  loop  in  as  const  var  type  int  float  bool  string`

`main` is a keyword; it cannot be used as a variable name.

### 3.5 Literals
**Integer literal (`INT`):** `0` or a non-zero digit followed by digits: `0 | [1-9][0-9]*`. Decimal only. Maximum value `9223372036854775807`. Negative numbers are written with the unary `-` operator, so `-9223372036854775808` cannot be written directly; write `-9223372036854775807 - 1`.

**Float literal (`FLOAT`):** `digits "." digits [ ("e"|"E") ["+"|"-"] digits ]`, where `digits` follows the integer rule above for the integer part (no leading zeros except a single `0`) and the fractional part is **one or more** digits (leading zeros allowed there, e.g. `0.05`). Examples: `0.5`, `3.14`, `2.0`, `1.5e10`, `2.0E-3`. The value is converted with correct rounding to the nearest IEEE-754 binary64 (round-half-to-even). If the result would be infinite, error **L006**.

**Number lexing algorithm (exact):** when the lexer sees a digit:
1. Read the maximal run of digits → `D`. If `D` has length > 1 and starts with `0` → error **L008**.
2. If the next char is `.`: if the char after it is a digit, consume `.` and the maximal run of digits (this is a float); otherwise → error **L007**.
3. If a float was started and the next char is `e` or `E`: look ahead for an optional `+`/`-` followed by at least one digit; if present consume them all, otherwise → error **L007**.
4. If no `.` was seen and the next char is `e` or `E` → error **L007** (exponent without fraction is not supported).
5. If the character immediately after the literal is a letter, digit or `_` → error **L007**.
6. Range checks: integer > `9223372036854775807` → **L005**; float overflow to infinity → **L006**.
All number errors are positioned at the **first digit** of the literal.

**String literal (`STRING`):** starts and ends with `"` on a single line. May contain any Unicode character except an unescaped newline. Escape sequences (and no others): `\n` newline, `\t` tab, `\r` carriage return, `\"` double quote, `\\` backslash. The token's value is the string after escape processing. A newline or end of file before the closing quote → **L002** (positioned at the opening quote). A backslash followed by any other character → **L003** (positioned at the backslash); a backslash immediately followed by a newline or end of file → **L002**.

**Boolean literals:** the keywords `true` and `false`.

### 3.6 Operators and punctuation
The lexer uses **longest match**. Complete list:

`+  -  *  /  %  =  ==  !  !=  <  <=  >  >=  &&  ||  +=  -=  *=  /=  %=  (  )  {  }  ;`

Special cases:
* `/` followed by `/` or `*` starts a comment (§3.2). `/` followed by `=` is `/=`.
* `++` → error **L009**; `--` → error **L010** (positioned at the first character). Double negation must be written `- -x` or `-(-x)`.
* A single `&` → error **L011**; a single `|` → error **L012**.
* Any other unlisted character (for example `.`, `,`, `[`, `]`, `?`, `:`, `^`, `~`, `#`, `@`, `$`, `'`, backtick, `\`, any non-ASCII character outside strings/comments, any control character) → **L001**.

### 3.7 Token structure
Each token has: `type`, `lexeme` (exact source text; empty for `EOF`), `value` (parsed value for INT/FLOAT/STRING; `None` otherwise), `line`, `col`.

### 3.8 Token type names (exact)
Keywords: `MODULE FN MAIN LET MUT IF ELSE WHILE DO FOR PRINT TRUE FALSE`
Other: `IDENT RESERVED INT FLOAT STRING`
Operators: `PLUS MINUS STAR SLASH PERCENT EQ EQEQ BANG BANGEQ LT LTEQ GT GTEQ ANDAND OROR PLUSEQ MINUSEQ STAREQ SLASHEQ PERCENTEQ`
Punctuation: `LPAREN RPAREN LBRACE RBRACE SEMI`
End: `EOF`

---

## 4. Types and Values

C-- has exactly four types. Types are **inferred** from the initializer of a variable; there are no type annotations and no casts.

| Type | Values | Details |
|------|--------|---------|
| `int` | signed 64-bit integers | Range `-9223372036854775808` … `9223372036854775807`. Any operation whose mathematical result is outside this range is runtime error **R001**. |
| `float` | IEEE-754 binary64 | Round-to-nearest, ties-to-even. **Infinity and NaN can never exist**: any operation that would produce them is a runtime error (R002/R004). Negative zero (`-0.0`) can exist; `-0.0 == 0.0` is `true`. |
| `bool` | `true`, `false` | Never implicitly converted to or from any other type. |
| `string` | sequence of Unicode code points | Immutable. Only `==`, `!=`, assignment and `print` apply. Equality compares code-point sequences exactly (no normalization, no case folding). The empty string `""` is valid. |

**Type of a literal:** `INT`→`int`, `FLOAT`→`float`, `STRING`→`string`, `true`/`false`→`bool`.

**int → float conversion** (used only by mixed arithmetic/comparison, §7): the int value is converted to the nearest float (ties-to-even). There is **no** implicit conversion in any other place; in particular, assignment never converts (§6.5).

There is **no truthiness**: conditions must be of type `bool` (§8).

---

## 5. Program Structure and Grammar

### 5.1 Structure
A program is exactly:

```
module <name>;
fn main() { <statements> }
```

* `<name>` is any `IDENT` (not a keyword/reserved word). It has no further meaning in this version.
* `main` takes no parameters and has no return type (`fn main() -> int` is a syntax error).
* After the closing `}` of `main`, only whitespace and comments may follow (error **S002** otherwise).
* Executing a program means executing the statements of `main` in order. After the last statement, the program ends with exit code 0.

### 5.2 Grammar (EBNF, normative)
`{ x }` = zero or more, `[ x ]` = optional, `( a | b )` = choice, quoted text = token.

```
program     = "module" IDENT ";" "fn" "main" "(" ")" block EOF ;

block       = "{" { statement } "}" ;

statement   = varDecl
            | assignStmt
            | printStmt
            | ifStmt
            | whileStmt
            | doWhileStmt
            | forStmt
            | block ;

varDecl     = ( "let" | "mut" ) IDENT "=" expr ";" ;
assignStmt  = assignment ";" ;
assignment  = IDENT assignOp expr ;
assignOp    = "=" | "+=" | "-=" | "*=" | "/=" | "%=" ;

printStmt   = "print" "(" expr ")" ";" ;

ifStmt      = "if" "(" expr ")" block [ "else" ( ifStmt | block ) ] ;
whileStmt   = "while" "(" expr ")" block ;
doWhileStmt = "do" block "while" "(" expr ")" ";" ;

forStmt     = "for" "(" forInit [ expr ] ";" [ assignment ] ")" block ;
forInit     = varDecl | assignStmt | ";" ;

expr        = or ;
or          = and { "||" and } ;
and         = equality { "&&" equality } ;
equality    = comparison { ( "==" | "!=" ) comparison } ;
comparison  = term { ( "<" | ">" | "<=" | ">=" ) term } ;
term        = factor { ( "+" | "-" ) factor } ;
factor      = unary { ( "*" | "/" | "%" ) unary } ;
unary       = ( "!" | "-" ) unary | primary ;
primary     = INT | FLOAT | STRING | "true" | "false" | IDENT | "(" expr ")" ;
```

Notes (normative):
1. Braces are **mandatory** for all `if`/`else`/`while`/`do`/`for` bodies. There is no dangling-else problem.
2. Assignment is a **statement**, not an expression. `a = b = 1;`, `if (x = 1)` and `x++` are syntax errors.
3. An expression is **not** a statement: `x + 1;`, `5;`, `x;` are syntax errors. A lone `;` is a syntax error (except as part of a `for` header).
4. `forInit` consumes its own `;` (a `varDecl` or `assignStmt` already ends with `;`; the third alternative is a bare `;`).
5. All binary operators are **left-associative**. There are no right-associative operators except the prefix operators `!` and `-`.
6. Comparison operators are in a single level and left-associative; `a < b < c` parses as `(a < b) < c` and is rejected later by type checking (`bool < int`).
7. Nesting limit: blocks, parenthesized expressions and chained prefix operators may be nested at most **200** levels combined; deeper nesting → error **S004**. A chain of at least 1000 binary operators at the same precedence level MUST still work (set the recursion limit high enough, e.g. ≥ 10000).

### 5.3 Operator precedence (high → low)
| Level | Operators | Associativity |
|------:|-----------|---------------|
| 1 | `!`  `-` (unary, prefix) | right |
| 2 | `*`  `/`  `%` | left |
| 3 | `+`  `-` | left |
| 4 | `<`  `>`  `<=`  `>=` | left |
| 5 | `==`  `!=` | left |
| 6 | `&&` | left |
| 7 | `\|\|` | left |

Assignment operators (`=`, `+=`, …) are statement-level only and have no precedence.

---

## 6. Declarations, Scope, and Mutability

### 6.1 Declarations
* `let name = expr;` declares an **immutable** variable. It can never be assigned again.
* `mut name = expr;` declares a **mutable** variable.
* Every variable **must** be initialized in its declaration. There is no uninitialized state.
* The variable's type is the type of `expr` and **never changes**.
* Variable names are case-sensitive. `x` and `X` are different.

### 6.2 Scopes
* The body block of `main` is the outermost scope. There are **no global variables**.
* Every `{ ... }` block creates a new scope. A variable is visible from the end of its declaration statement to the end of the enclosing block.
* A variable is **not** visible inside its own initializer: in `let x = x + 1;` the `x` on the right refers to an outer `x` if one exists, otherwise it is error E001.
* **Redeclaring** a name already declared **in the same scope** is error **E002**.
* **Shadowing** a name from an **enclosing** scope is allowed; the inner declaration may have a different type and a different mutability. After the inner block ends, the outer variable is visible again, unchanged.
* A `for` statement creates its own **loop scope** that holds the variable declared in `forInit` (if any). The loop body block is a separate, nested scope inside the loop scope, so a body may shadow the loop variable.
* The body block of a loop gets a **fresh scope on every iteration**; variables declared in a body do not survive to the next iteration.
* In `do { A } while (cond);` the condition is **outside** the body scope: variables declared inside `A` are not visible in `cond`.
* The `if`/`else if`/`else` blocks are ordinary blocks. A variable declared in a block is not visible in a different branch.
* Unused variables are not an error and produce no warning.

### 6.3 Assignment
`name op= expr;`
* `name` must be declared (else E001) and must be `mut` (else E003).
* `x = e;` requires `type(e)` **exactly equal** to `type(x)` (else E007). There is no implicit conversion: `mut f = 1.0; f = 2;` is error E007.
* `x op= e;` (for `+= -= *= /= %=`) is defined as `x = x op e;` (`x` evaluated once; it is just a variable). It is type-checked as the binary operation `op` on `(type(x), type(e))` (E006 if the operation is invalid, reported with the compound operator token, e.g. `'+='`); if valid, the result type must equal `type(x)` (else E007). Example: `mut i = 1; i += 0.5;` → result `float` ≠ `int` → E007. `mut f = 1.0; f += 1;` is valid (result `float`).

---

## 7. Expressions and Operators

### 7.1 Evaluation order
Expressions are evaluated **left to right**. For a binary operator, the left operand is evaluated fully before the right operand. If evaluating an operand causes a runtime error, that error is reported and nothing else is evaluated. `&&` and `||` **short-circuit** (§7.4). There are no assignments, function calls, or other side effects inside expressions, so order only affects which runtime error is reported first.

### 7.2 Operator typing table (normative)

**Binary arithmetic**

| Operator | Allowed operand types | Result type |
|----------|-----------------------|-------------|
| `+` `-` `*` `/` | `(int,int)` | `int` |
| `+` `-` `*` `/` | `(float,float)`, `(int,float)`, `(float,int)` | `float` (int operand converted first) |
| `%` | `(int,int)` only | `int` |

**Comparison**

| Operator | Allowed operand types | Result |
|----------|-----------------------|--------|
| `<` `>` `<=` `>=` | any two numeric types (`int`/`float`, mixed allowed) | `bool` |
| `==` `!=` | two numeric types (mixed allowed), or `(bool,bool)`, or `(string,string)` | `bool` |

For mixed `int`/`float` comparison, the `int` is converted to `float` **first** and then compared (this can lose precision for ints larger than 2^53; this is intended and must be implemented explicitly, e.g. `float(a) == b`, not by Python's exact int/float comparison).

**Logical**

| Operator | Allowed operand types | Result |
|----------|-----------------------|--------|
| `&&` `\|\|` | `(bool,bool)` | `bool` |
| `!` | `bool` | `bool` |

**Unary minus** `-`: `int → int`, `float → float`.

Any combination not listed is a semantic error (E005 for unary, E006 for binary).

### 7.3 Arithmetic semantics (exact)

**Integer `+ - *`:** exact mathematical result; if outside the 64-bit signed range → **R001** `integer overflow`.

**Integer unary `-`:** `-x` ; if `x == -9223372036854775808` → R001.

**Integer `/`:** quotient **truncated toward zero** (like C99). `7/2 = 3`, `-7/2 = -3`, `7/-2 = -3`, `-7/-2 = 3`. Divisor `0` → **R002** `division by zero`. `-9223372036854775808 / -1` → R001 (the result is out of range).

**Integer `%`:** `a % b = a - (a / b) * b` using the truncating `/` above, so the result has the **sign of the dividend**. `7%3=1`, `-7%3=-1`, `7%-3=1`, `-7%-3=-1`. Divisor `0` → **R003** `modulo by zero`. `-9223372036854775808 % -1` is defined as `0` (no error).

**Float `+ - * /`:** IEEE-754 binary64 with round-to-nearest-even. After computing, if the result is infinite → **R004** `float overflow`. Division where the divisor is `0.0` or `-0.0` (even if the dividend is `0.0`) → **R002** `division by zero` (checked *before* dividing, so NaN never appears).

**Float unary `-`:** negates the sign bit (`-0.0` is possible).

**Python warning (normative):** Python's `//` and `%` floor toward negative infinity and Python ints are unbounded. They must not be used directly for C-- semantics. Implement truncating division/modulo explicitly and check the 64-bit range after every integer operation.

### 7.4 Logical semantics
* `a && b`: evaluate `a`; if `false`, the result is `false` and `b` is **not** evaluated; otherwise the result is `b`.
* `a || b`: evaluate `a`; if `true`, the result is `true` and `b` is **not** evaluated; otherwise the result is `b`.
* The analyzer still type-checks both operands even though one may not be evaluated at run time.

### 7.5 No constant folding
The analyzer does **not** evaluate expressions. `1 / 0` is accepted by the analyzer and fails at run time with R002 when (and only if) it is executed.

---

## 8. Statements and Execution Semantics

Execution is sequential. Every statement is executed exactly as described below.

| Statement | Semantics |
|-----------|-----------|
| `let x = e;` / `mut x = e;` | Evaluate `e`, then declare `x` in the **current** scope with that value. |
| `x = e;` | Evaluate `e`, store in `x`. |
| `x op= e;` | Evaluate `x op e` per §6.3/§7, store in `x`. |
| `print(e);` | Evaluate `e`, convert to text per §9, write it followed by `\n` to standard output. |
| `{ ... }` | Push a new scope, execute the statements in order, pop the scope. |
| `if (c) A else if (d) B else C` | Evaluate `c`; if `true` execute `A` and skip the rest. Otherwise (if an else-part exists) execute the else-part, which is either a nested `if` (evaluated the same way) or a block. If all conditions are `false` and there is no final `else`, nothing happens. |
| `while (c) A` | Repeat: evaluate `c`; if `false` stop; otherwise execute block `A`. |
| `do A while (c);` | Repeat: execute block `A`, then evaluate `c`; if `false` stop. `A` always runs **at least once**. |
| `for (init; c; upd) A` | 1) Push a **loop scope**. 2) Execute `init` if present (a declaration puts its variable in the loop scope). 3) If `c` is present evaluate it; if it is `false` go to step 7; if `c` is absent it counts as `true`. 4) Execute block `A` (fresh scope). 5) Execute `upd` if present. 6) Go to step 3. 7) Pop the loop scope. |

Further rules:
1. Conditions in `if`, `while`, `do-while`, `for` MUST have type `bool` (checked statically, E004). No runtime conversion exists.
2. There is **no** `break` or `continue`. Infinite loops such as `while (true) { }` or `for (;;) { }` are legal programs.
3. `for (let i = 0; ...)` is legal syntax, but `i` is immutable so an update such as `i += 1` is error E003.
4. In `for (init; c; upd)`, `upd` is **one** assignment without a trailing `;`. Comma-separated updates are not supported.
5. A statement that is a bare block `{ ... }` is allowed anywhere a statement is allowed.

---

## 9. Output Formatting (`print`)

`print(e);` writes the text below followed by exactly one `\n`.

| Type | Text |
|------|------|
| `int` | Base-10 digits, a leading `-` for negatives, no `+`, no separators, no leading zeros. `0` prints `0`. |
| `bool` | `true` or `false` (lowercase). |
| `string` | The characters of the string, unquoted, with escapes already resolved (a `\n` in the string produces an actual line break). |
| `float` | See §9.1. |

### 9.1 Float formatting (exact algorithm)
1. If the value is zero: print `0.0`, or `-0.0` for negative zero.
2. Otherwise let `D` be the **shortest** string of decimal digits `d1 d2 … dn` (no trailing zeros, `n ≥ 1`) such that the number `d1.d2…dn × 10^E` converts back to exactly the same float (round-trip). If several shortest digit strings exist, use the one closest to the exact value (this is what Python's `repr`, JavaScript, and Ryu produce). Let `E` be the decimal exponent of that scientific form. Remember the sign.
3. If `-4 ≤ E < 16` print **positional** notation:
   * `E ≥ 0`: integer part = the first `E+1` digits of `D` (pad with zeros on the right if `D` is shorter); fractional part = the remaining digits of `D`, or `0` if there are none. Output `<int>.<frac>`.
   * `E < 0`: output `0.` followed by `(-E-1)` zeros followed by `D`.
4. Otherwise print **scientific** notation: `d1.` + (`d2…dn`, or `0` if `n = 1`) + `e` + sign (`+` or `-`, always present) + the absolute value of `E` with **at least two digits**.
5. Prepend `-` for negative numbers.

| Value | Output |
|-------|--------|
| `2.0` | `2.0` |
| `0.5` | `0.5` |
| `100.0` | `100.0` |
| `0.1 + 0.2` | `0.30000000000000004` |
| `1.0 / 3.0` | `0.3333333333333333` |
| `1234567.891` | `1234567.891` |
| `1e15` (written `1.0e15`) | `1000000000000000.0` |
| `1e16` | `1.0e+16` |
| `1.5e300` | `1.5e+300` |
| `0.0001` | `0.0001` |
| `0.00001` | `1.0e-05` |
| `123456789012345680.0` | `1.2345678901234568e+17` |
| `-0.0` | `-0.0` |
| `-2.5` | `-2.5` |

---

## 10. Errors

### 10.1 Categories and exact output format
There are four error kinds: `lexical`, `syntax`, `semantic`, `runtime`. Every error is printed to **standard error** as three lines:

```
<path>:<line>:<col>: <kind> error: <message>
    <source line>
    <caret line>
```

* `<path>` is the file path **exactly as given** on the command line (no normalization).
* Line 2 is four spaces followed by the text of line `<line>` of the normalized source (no line terminator). If that line does not exist (end of file after a trailing newline), the text is empty.
* Line 3 is four spaces, then for each of the first `<col>-1` code points of the source line: a **tab** if that code point is a tab, otherwise a **space**; then a single `^`.
* When several errors are printed (semantic errors only), the three-line blocks follow one another with no blank lines and no summary line.

### 10.2 Phases and what stops what
1. **Lexical errors:** the lexer stops at the first one. Because lexing finishes before parsing, a lexical error anywhere in the file is reported instead of a syntax error earlier in the file.
2. **Syntax errors:** the parser stops at the first one (no recovery).
3. **Semantic errors:** the analyzer reports **all** errors it finds, sorted by `(line, col)`; ties keep discovery order.
4. **Runtime errors:** execution stops at the first one. Everything printed by the program before the error stays on standard output; standard output is flushed **before** the error is written to standard error.
A program with lexical, syntax or semantic errors is **never executed**.

### 10.3 Lexical error catalog (position = where stated in §3)
| Code | Message |
|------|---------|
| L001 | `unexpected character '<c>'` — `<c>` is the character itself; for control characters or characters with no visible glyph use `U+XXXX` (uppercase hex, at least 4 digits) instead, e.g. `unexpected character 'U+0000'`. |
| L002 | `unterminated string literal` |
| L003 | `invalid escape sequence '\<c>'` (`<c>` = the character after the backslash) |
| L004 | `unterminated block comment` |
| L005 | `integer literal out of range` |
| L006 | `float literal out of range` |
| L007 | `invalid number literal` |
| L008 | `leading zeros are not allowed in number literals` |
| L009 | `'++' is not supported; use '+= 1'` |
| L010 | `'--' is not supported; use '-= 1'` |
| L011 | `single '&' is not supported; did you mean '&&'?` |
| L012 | the message given in the note below this table |

Message for L012 (shown here outside the table because it contains pipe characters): ``single '|' is not supported; did you mean '||'?``

### 10.4 Syntax error catalog
Position of every syntax error = the **offending token** (the token that was found).

**Token description `<Y>` ("found" text):** `end of file` for `EOF`; `string literal` for `STRING`; otherwise the token's lexeme in single quotes, e.g. `'print'`, `'42'`, `')'`, `'foo'`.

| Code | Message |
|------|---------|
| S001 | `expected <X>, found <Y>` |
| S002 | `unexpected <Y> after end of program` |
| S003 | `'<word>' is reserved for future use and cannot be used in this version` |
| S004 | `program is nested too deeply (limit 200)` |

**Rule for S003:** whenever the parser would report **any** syntax error at a `RESERVED` token, it reports S003 instead.

**The only allowed values for `<X>` in S001 (exhaustive):**

| `<X>` | Where it is used |
|-------|------------------|
| `'module'` | first token of the program |
| `identifier` | after `module`; after `let`/`mut` |
| `';'` | after module name; after a declaration/assignment/`print(...)`/`do-while` statement; after the `for` condition |
| `'fn'`, `'main'`, `'('`, `')'` | in `fn main ( )` and in `print`, `if`, `while`, `for`, `do-while` conditions, and to close a parenthesized expression |
| `'{'` | before any block (function body, `if`, `else`, loops, `do`) |
| `'}'` | inside a block when the end of file is reached |
| `statement` | inside a block when the token cannot start a statement (statement starters: `let mut if while do for print {` and an identifier) |
| `'='` | after the name in `let`/`mut` |
| `expression` | wherever an expression is required and the token cannot start one (expression starters: INT FLOAT STRING `true` `false` IDENT `(` `!` `-`) |
| `assignment operator` | after an identifier that starts a statement or a `for` update |
| `'if' or '{'` | after `else` |
| `'while'` | after the body block of `do` |
| `variable declaration, assignment or ';'` | first position inside `for (` |
| `assignment or ')'` | the update position of `for` (after the second `;`) |

S002 applies when anything other than `EOF` follows the closing `}` of `main`.

### 10.5 Semantic error catalog
Position is given per entry. Types are written `int`, `float`, `bool`, `string`.

| Code | Message | Position |
|------|---------|----------|
| E001 | `undeclared variable '<name>'` | the identifier (use or assignment target) |
| E002 | `variable '<name>' is already declared in this scope (at line <L>, column <C>)` | the name in the new declaration; `<L>,<C>` = position of the name in the earlier declaration |
| E003 | `cannot assign to immutable variable '<name>' (declared with 'let' at line <L>, column <C>); declare it with 'mut' to allow assignment` | the assignment target identifier; `<L>,<C>` = position of the name in its declaration |
| E004 | `condition must be of type bool, found <type>` | the **first token** of the condition expression (including a leading `(`) |
| E005 | `operator '<op>' cannot be applied to <type>` | the operator token |
| E006 | `operator '<op>' cannot be applied to <ltype> and <rtype>` | the operator token (for compound assignment, the compound operator token, with `<op>` such as `+=`) |
| E007 | `cannot assign value of type <rtype> to variable '<name>' of type <ltype>` | the assignment target identifier |

**Cascade suppression (normative):** if an expression contains an error, its type becomes the internal type `invalid`. Any operator, condition check, or assignment involving an `invalid` operand reports **no further error** and yields `invalid`. A variable declared with an `invalid` initializer gets type `invalid`, which suppresses later errors that involve it. An undeclared variable use is `invalid` after E001.

**Analyzer order rules:**
* For a declaration the initializer is analyzed **before** the name is added to the scope.
* If E002 occurs, the earlier declaration remains in effect; the new initializer is still analyzed.
* If an assignment target is undeclared (E001) the right-hand side is still analyzed.
* Both operands of every binary operator are analyzed even when one is erroneous.
* E004 is checked for `if`, `else if`, `while`, `do-while`, and a present `for` condition.

### 10.6 Runtime error catalog
| Code | Message | Position |
|------|---------|----------|
| R001 | `integer overflow` | the operator token (`+ - * /`, unary `-`, or a compound operator like `*=`) |
| R002 | `division by zero` | the operator token (`/` or `/=`, for int and float) |
| R003 | `modulo by zero` | the operator token (`%` or `%=`) |
| R004 | `float overflow` | the operator token |
| R005 | `step limit exceeded (<N> steps)` | the first token of the statement about to execute |

**Step counting (only when `--max-steps N` is given):** the counter increases by 1 immediately **before** each execution of a `VarDecl`, `Assign`, `Print`, `If`, `While`, `DoWhile`, `For` or `Block` node (this includes a `for` init, a `for` update and every loop-body block execution), and by 1 each time a loop condition is evaluated. If the counter would exceed `N`, R005 is raised. Without the option there is no limit and no counting.

---

## 11. Command-Line Interface

### 11.1 Invocation
`cmm <command> [options] <file>` — and `python -m cmm ...` must behave identically.

| Command | Behaviour |
|---------|-----------|
| `run <file> [--max-steps N]` | Read, lex, parse, analyze, execute. `N` must be a positive integer. |
| `check <file>` | Read, lex, parse, analyze. On success print `<path>: OK` to stdout. |
| `tokens <file>` | Read, lex, print the token list (§11.6). |
| `ast <file>` | Read, lex, parse (no analysis), print the AST (§11.6). |
| `--version` | Print `cmm 0.1.0` to stdout, exit 0. |
| `--help`, `-h` | Print usage to stdout, exit 0 (exact wording not specified). |

No other commands or options exist.

### 11.2 Exit codes
| Code | Meaning |
|-----:|---------|
| 0 | Success |
| 1 | Lexical, syntax or semantic error(s) |
| 2 | Runtime error |
| 3 | I/O error (file missing/unreadable/not UTF-8) |
| 4 | Command-line usage error |
| 70 | Internal error (a bug in the implementation) |

### 11.3 Streams
Program output → **stdout**. All errors → **stderr**. Output MUST be UTF-8 with `\n` line endings on all platforms (configure the streams explicitly, e.g. `sys.stdout.reconfigure(encoding="utf-8", newline="\n")`). Output may be buffered but MUST be flushed before the process exits and before any error text is written.

### 11.4 I/O errors
stderr: `cmm: error: cannot read '<path>': <reason>` where `<reason>` is exactly one of `file not found`, `is a directory`, `permission denied`, `not valid UTF-8`, or the operating system's message for any other failure. Exit code 3.

### 11.5 Usage and internal errors
* Usage errors (unknown command, missing file, bad `--max-steps`): print the usage line(s) and then `cmm: error: <message>` to stderr, exit code 4. (Override `argparse`'s default exit code 2.)
* Internal error (any unexpected exception): stderr `cmm: internal error: <exception type>: <message>`, exit code 70. A Python traceback MUST NOT be shown unless the environment variable `CMM_DEBUG=1` is set.

### 11.6 Debug output formats
**`tokens`:** one line per token, in order, including `EOF`: `<line>:<col>` TAB `<TYPE>` TAB `<lexeme>`.
```
1:1	MODULE	module
1:8	IDENT	main
1:12	SEMI	;
```
**`ast`:** an indented tree, 2 spaces per level. Each node line is `<role>: <NodeName>(<field>=<value>, ...)`, where only non-node fields appear in parentheses (omit the parentheses if there are none); the root has no role prefix. Strings are shown in double quotes with `\n \t \r \" \\` escaped; bools as `true`/`false`; floats per §9.1; `type=` shows `int`/`float`/`bool`/`string`. Children appear in source order. Block children use the role `stmt`. Absent optional children are omitted. Roles: `Program`: `body`; `VarDecl`: `init`; `Assign`: `value`; `Print`: `expr`; `If`: `cond`, `then`, `else`; `While`: `cond`, `body`; `DoWhile`: `body`, `cond`; `For`: `init`, `cond`, `update`, `body`; `BinaryOp`: `left`, `right`; `UnaryOp`: `operand`. Fields: `Program(module=...)`, `VarDecl(mutable=..., name=...)`, `Assign(name=..., op=...)`, `BinaryOp(op=...)`, `UnaryOp(op=...)`, `Literal(type=..., value=...)`, `Variable(name=...)`.
```
Program(module="main")
  body: Block
    stmt: VarDecl(mutable=false, name="x")
      init: BinaryOp(op="+")
        left: Literal(type=int, value=1)
        right: Literal(type=int, value=2)
```

---

## 12. Reference Implementation Architecture

### 12.1 Project layout (exact)
```
cmm-lang/
├── pyproject.toml
├── README.md
├── LICENSE                      (MIT)
├── .gitignore
├── .dockerignore
├── Dockerfile
├── .github/workflows/ci.yml
├── docs/SPEC.md                 (this file; never modified by the implementer)
├── cmm/
│   ├── __init__.py              (defines __version__ = "0.1.0")
│   ├── __main__.py              (calls cmm.cli.main and exits with its return value)
│   ├── tokens.py
│   ├── errors.py
│   ├── lexer.py
│   ├── ast_nodes.py
│   ├── parser.py
│   ├── types.py                 (Type enum and operator typing tables)
│   ├── analyzer.py
│   ├── formatting.py            (float/value formatting, §9)
│   ├── interpreter.py
│   ├── astprint.py              (debug printing for `tokens` and `ast`)
│   └── cli.py
├── examples/                    (.cmm programs with .out expected output; see §17)
│   └── errors/                  (.cmm programs with .err expected stderr and .code expected exit code)
├── scripts/
│   ├── entry.py                 (entry point for PyInstaller)
│   └── build_executable.py
└── tests/
```
The optional C backend (§16) adds `cmm/codegen_c.py` only if explicitly requested.

### 12.2 Errors (`errors.py`)
```python
class CmmError(Exception):            # base class
    kind: str                         # "lexical" | "syntax" | "semantic" | "runtime"
    code: str                         # "L001", "S001", "E003", "R002", ...
    message: str
    line: int
    col: int
class LexError(CmmError): ...
class ParseError(CmmError): ...       # do NOT name it SyntaxError (shadows the builtin)
class SemanticError(CmmError): ...
class CmmRuntimeError(CmmError): ...  # do NOT name it RuntimeError
def format_error(err: CmmError, path: str, source_lines: list[str]) -> str:
    """Return the exact 3-line text of §10.1 (including the final newline)."""
```

### 12.3 Public functions
```python
# lexer.py
def normalize_source(text: str) -> str: ...        # BOM removal + newline normalization (§2)
def tokenize(source: str) -> list[Token]: ...      # source already normalized; raises LexError
# parser.py
def parse(tokens: list[Token]) -> Program: ...     # raises ParseError
# analyzer.py
def analyze(program: Program) -> list[SemanticError]: ...   # [] means valid; sorted per §10.2
# interpreter.py
def run(program: Program, out: TextIO, max_steps: int | None = None) -> None: ...  # raises CmmRuntimeError
# formatting.py
def format_float(x: float) -> str: ...
def format_value(v: int | float | bool | str) -> str: ...
# cli.py
def main(argv: list[str] | None = None) -> int: ...  # returns the exit code
```

### 12.4 Token (`tokens.py`)
A frozen dataclass `Token(type: TokenType, lexeme: str, value: object, line: int, col: int)` and an `Enum` `TokenType` with exactly the names listed in §3.8. A dictionary maps each keyword and reserved word to its token type.

### 12.5 AST nodes (`ast_nodes.py`)
Use `@dataclass` classes. Every node has `line: int` and `col: int`. **Position meaning:** `Literal`/`Variable` → their token; `UnaryOp`/`BinaryOp` → the **operator** token; statements → their first token (`let`, `mut`, `print`, `if`, `while`, `do`, `for`, `{`, or the target identifier of an assignment); `Program` → the `module` token.
Every **expression** node additionally has `start_line` and `start_col` = position of its **first token**, including a leading `(` when the expression was parenthesized (the parser sets this on the inner node when it consumes the parentheses). E004 uses `start_*`.

| Node | Fields |
|------|--------|
| `Program` | `module_name: str`, `body: Block` |
| `Block` | `statements: list` |
| `VarDecl` | `mutable: bool`, `name: str`, `name_line`, `name_col`, `init: Expr` |
| `Assign` | `name: str`, `op: str` (one of `= += -= *= /= %=`), `op_line`, `op_col`, `value: Expr` (line/col = the target identifier) |
| `Print` | `expr: Expr` |
| `If` | `cond: Expr`, `then_block: Block`, `else_branch: Block \| If \| None` |
| `While` | `cond: Expr`, `body: Block` |
| `DoWhile` | `body: Block`, `cond: Expr` |
| `For` | `init: VarDecl \| Assign \| None`, `cond: Expr \| None`, `update: Assign \| None`, `body: Block` |
| `Literal` | `type: str` (`"int"`, `"float"`, `"bool"`, `"string"`), `value` |
| `Variable` | `name: str` |
| `UnaryOp` | `op: str` (`"-"` or `"!"`), `operand: Expr` |
| `BinaryOp` | `op: str`, `left: Expr`, `right: Expr` |

### 12.6 Analyzer (`analyzer.py`, `types.py`)
* `Type` enum: `INT`, `FLOAT`, `BOOL`, `STRING`, `INVALID` (internal only; its name in messages never appears because `INVALID` suppresses errors).
* Symbol table: a stack of dictionaries `name → Symbol(type, mutable, decl_line, decl_col)`.
* The operator typing table of §7.2 lives in `types.py` as data (a dictionary), not scattered `if` chains.
* The analyzer never evaluates expressions and never modifies the AST.

### 12.7 Interpreter (`interpreter.py`)
* Tree-walking, using a stack of environments (dictionaries) that mirrors §6.2.
* Values are Python `int`, `float`, `bool`, `str`. **Pitfall:** Python's `bool` is a subclass of `int`; the interpreter MUST dispatch on the static node types / `type(v) is bool` so that a `bool` can never take part in arithmetic and `True == 1` can never occur.
* Integer operations use the explicit helpers required by §7.3 and a range check after each operation (`-2**63 <= r <= 2**63-1`).
* Mixed `int`/`float` operations convert the `int` with `float(...)` first (§7.2).
* Float results are checked for infinity (R004) after each operation; float division checks the divisor for zero first (R002).
* The interpreter may assume the program passed analysis, but it MUST raise an internal error (not silently continue) if an impossible state is met.
* Writes program output to the `out` stream passed to `run`, using `format_value` and `"\n"`.

### 12.8 Style requirements
Type hints on every function, a docstring on every module/class/public function, no global mutable state, no third-party runtime imports, no `print` debugging left in, no `exec`/`eval`.

---

## 13. Platform Independence Requirements (Windows, macOS, Linux)

1. Only the Python standard library at run time. Supported Python versions: **3.10, 3.11, 3.12** (and newer if they pass the tests).
2. Use `pathlib` for paths. No hard-coded path separators or absolute paths. No `os.system`, `subprocess` in the language implementation itself (tests may use `subprocess`).
3. Read source with `Path.read_bytes()` and decode with `"utf-8"` strict. Never rely on the default locale encoding.
4. Normalize line endings per §2.4. A source file with `\r\n` endings MUST give byte-identical output to the same file with `\n` endings (positions in error messages identical too).
5. Write output as UTF-8 with `\n` endings on all platforms (§11.3). Windows consoles whose code page is not UTF-8 must not cause crashes (use `reconfigure(encoding="utf-8", errors="strict")` and, if reconfiguring is impossible, wrap `sys.stdout.buffer`).
6. No behaviour may depend on locale, time zone, hash randomization, dictionary ordering of unordered data, or the current working directory.
7. Number semantics come from this specification (§4, §7, §9), not from the host: 64-bit integer range checks, truncating division, shortest round-trip float formatting implemented explicitly (§9.1).
8. Set `sys.setrecursionlimit` to at least 10000 at start-up of the CLI (never lower an existing larger value).
9. Tests MUST pass on Linux, macOS and Windows (enforced in CI, §15.3).

---

## 14. Testing Requirements

Framework: `pytest` (development dependency only). Tests live in `tests/` and MUST NOT depend on the current working directory (locate files with `Path(__file__).parent`). Tests that run the CLI use `subprocess.run([sys.executable, "-m", "cmm", ...])`.

| File | Minimum number of test cases | Must cover |
|------|-----------------------------:|------------|
| `tests/test_lexer.py` | 30 | every token type, keywords vs reserved words, all literal forms, every escape, both comment kinds, position tracking incl. tabs and `\r\n`, BOM, every lexical error L001–L012 |
| `tests/test_parser.py` | 35 | every statement and expression form, precedence and associativity of every level, `else if` chains, `for` with all optional parts empty/present, every S001 `<X>` value, S002, S003, S004 |
| `tests/test_analyzer.py` | 40 | every row of the §7.2 table (valid and invalid), E001–E007 with exact messages and positions, shadowing, scope exit, loop-variable scope, `do-while` condition scope, cascade suppression, multiple errors sorted |
| `tests/test_formatting.py` | 20 | every row of the §9.1 table plus additional boundary values (`1e15`, `1e16`, `1e-4`, `1e-5`, `5e-324`, `1.7976931348623157e308`) |
| `tests/test_interpreter.py` | 50 | every operator, int/float mixing, truncating `/` and `%` for all four sign combinations, overflow at both ends of the range (`+`, `-`, `*`, unary `-`, `MIN / -1`, `MIN % -1 = 0`), R001–R005, short-circuit (right side must not run: prove it with a side that would raise a runtime error), all three loop types, `do-while` runs once, `for` with empty parts, scopes per iteration, `bool` never behaving as `int` |
| `tests/test_cli.py` | 20 | every command, every exit code of §11.2, I/O errors, usage errors, `--max-steps`, UTF-8 output of non-ASCII strings, CRLF/BOM files, `CMM_DEBUG` |
| `tests/test_examples.py` | all examples | Runs every program in `examples/` and `examples/errors/` through the CLI and compares **exact** stdout/stderr and exit code with the expected files |

All tests MUST pass with `python -m pytest -q` from the project root.

---

## 15. Packaging, CI, Docker, Executables

### 15.1 `pyproject.toml`
* `[build-system]`: `setuptools>=61`, `build-backend = "setuptools.build_meta"`.
* `[project]`: `name = "cmm-lang"`, `version = "0.1.0"`, `requires-python = ">=3.10"`, `dependencies = []`, `license = {text = "MIT"}`, `readme = "README.md"`.
* `[project.optional-dependencies]`: `dev = ["pytest>=7"]`.
* `[project.scripts]`: `cmm = "cmm.cli:main"`.
* `[tool.setuptools.packages.find]`: include `cmm*`.
* `[tool.pytest.ini_options]`: `testpaths = ["tests"]`.
`pip install -e .` MUST make the command `cmm` available.

### 15.2 README.md (required sections)
1. What C-- is (3–5 lines). 2. Requirements (Python 3.10+). 3. Install (`pip install -e .` and, alternatively, running with `python -m cmm` without installing). 4. Usage for **Windows (PowerShell/cmd)**, **macOS**, **Linux**, with exact commands (note `py` / `python` / `python3` differences). 5. The language at a glance (a short example and a table of operators). 6. Error format and exit codes. 7. Running the tests. 8. Building a standalone executable. 9. Docker usage. 10. Link to `docs/SPEC.md`.

### 15.3 GitHub Actions (`.github/workflows/ci.yml`)
Trigger on `push` and `pull_request`. One job with matrix `os: [ubuntu-latest, windows-latest, macos-latest]` × `python-version: ["3.10", "3.11", "3.12"]`. Steps: checkout, `actions/setup-python`, `pip install -e ".[dev]"`, `python -m pytest -q`, then a smoke test `cmm run examples/hello.cmm`.

### 15.4 Docker
`Dockerfile`: base `python:3.12-slim`, `WORKDIR /app`, copy the project, `pip install --no-cache-dir .`, `ENTRYPOINT ["cmm"]`. Usage: `docker run --rm -v "$PWD":/work -w /work cmm-lang run examples/hello.cmm`. `.dockerignore` excludes `.git`, `__pycache__`, `.pytest_cache`, `*.egg-info`, `dist`, `build`.

### 15.5 Standalone executables
`scripts/entry.py` contains exactly: `from cmm.cli import main` / `raise SystemExit(main())`. `scripts/build_executable.py` runs PyInstaller (`--onefile --name cmm scripts/entry.py`) and prints where the binary is. PyInstaller is **not** a dependency of the project; the script prints an install hint if it is missing. Documentation MUST state that each operating system must build its own binary.

---

## 16. Optional: C Backend (implement ONLY when explicitly requested)

Command: `cmm transpile <file> -o <out.c>` (adds one command to §11.1 only in that case).
* Output is standard **C99**; allowed headers: `<stdint.h> <stdio.h> <stdlib.h> <string.h> <stdbool.h> <float.h> <inttypes.h>`. No OS-specific calls, no compiler extensions (`__builtin_*` forbidden).
* Types: `int`→`int64_t`, `float`→`double`, `bool`→`bool`, `string`→`const char *` (UTF-8 literal using `\xNN` escapes).
* `let` variables are declared `const`.
* C99 `/` and `%` already truncate toward zero with the sign of the dividend, matching §7.3. Overflow and zero checks are generated as small `static` helper functions (`cmm_add`, `cmm_sub`, `cmm_mul`, `cmm_div`, `cmm_mod`, `cmm_neg`, `cmm_fadd`, …) written with standard comparisons only; float overflow is tested with `r > DBL_MAX || r < -DBL_MAX`.
* Runtime errors print to stderr **exactly** the 3-line format of §10.1 (path and source lines embedded in the generated code as string literals) and exit with code 2.
* `print` of a float must follow §9.1: find the smallest precision `p` in `1..17` such that `%.{p-1}e` round-trips through `strtod`, then re-format the digits per §9.1.
* The generated program's stdout MUST equal the interpreter's stdout for every program in `examples/`. Tests compile with `cc`/`gcc`/`clang` if found and are skipped otherwise.

---

## 17. Normative Examples

Each example is a complete test case. Expected stdout is shown after the program; empty stdout is stated explicitly.

### 17.1 Programs that run (`examples/*.cmm` + `*.out`)

**hello.cmm**
```
module main;
fn main() {
    print("Hello, C--!");
}
```
stdout:
```
Hello, C--!
```

**operators.cmm**
```
module main;
fn main() {
    print(7 + 3);
    print(7 - 10);
    print(7 * 3);
    print(7 / 2);
    print(-7 / 2);
    print(7 % 3);
    print(-7 % 3);
    print(7 % -3);
    print(7.0 / 2.0);
    print(1 + 2.5);
    print(10 / 4.0);
    print(3 < 4);
    print(3 == 3.0);
    print("a" == "b");
    print(!true);
    print(true && false);
    print(true || false);
    print(-(2 + 3) * 2);
}
```
stdout:
```
10
-3
21
3
-3
1
-1
1
3.5
3.5
2.5
true
true
false
false
false
true
-10
```

**variables.cmm**
```
module main;
fn main() {
    let a = 5;
    mut b = a;
    b = b + 1;
    print(a);
    print(b);
    {
        let a = "inner";
        print(a);
    }
    print(a);
    let s = "hi";
    print(s == "hi");
    print(s != "ho");
}
```
stdout:
```
5
6
inner
5
true
true
```

**scoping.cmm** (initializer sees the outer variable)
```
module main;
fn main() {
    let x = 1;
    {
        let x = x + 1;
        print(x);
    }
    print(x);
}
```
stdout:
```
2
1
```

**ifelse.cmm**
```
module main;
fn main() {
    mut n = 15;
    if (n % 15 == 0) {
        print("FizzBuzz");
    } else if (n % 3 == 0) {
        print("Fizz");
    } else if (n % 5 == 0) {
        print("Buzz");
    } else {
        print(n);
    }
}
```
stdout:
```
FizzBuzz
```

**loops.cmm**
```
module main;
fn main() {
    mut sum = 0;
    for (mut i = 1; i <= 5; i += 1) {
        sum += i;
    }
    print(sum);

    mut n = 3;
    while (n > 0) {
        print(n);
        n -= 1;
    }

    mut k = 10;
    do {
        print(k);
        k += 1;
    } while (k < 10);
}
```
stdout:
```
15
3
2
1
10
```

**prime_check.cmm**
```
module main;
fn main() {
    for (mut n = 2; n <= 20; n += 1) {
        mut is_prime = true;
        mut d = 2;
        while (d * d <= n) {
            if (n % d == 0) {
                is_prime = false;
            }
            d += 1;
        }
        if (is_prime) {
            print(n);
        }
    }
}
```
stdout: the numbers `2 3 5 7 11 13 17 19`, one per line.

**fibonacci.cmm** — prints the first 10 Fibonacci numbers (`0 1 1 2 3 5 8 13 21 34`, one per line):
```
module main;
fn main() {
    mut a = 0;
    mut b = 1;
    for (mut i = 0; i < 10; i += 1) {
        print(a);
        let next = a + b;
        a = b;
        b = next;
    }
}
```

**factorial.cmm** — prints `2432902008176640000` (20!):
```
module main;
fn main() {
    mut f = 1;
    for (mut i = 1; i <= 20; i += 1) {
        f *= i;
    }
    print(f);
}
```

**floats.cmm**
```
module main;
fn main() {
    print(2.0);
    print(0.1 + 0.2);
    print(1.0 / 3.0);
    print(1000000.0 * 10000000000.0);
    print(0.00001);
    print(-0.0);
    print(5 / 2.0);
    print(100.0);
}
```
stdout:
```
2.0
0.30000000000000004
0.3333333333333333
1.0e+16
1.0e-05
-0.0
2.5
100.0
```

**boundaries.cmm**
```
module main;
fn main() {
    print(9223372036854775807);
    print(-9223372036854775807 - 1);
    print(-7 / 2);
}
```
stdout:
```
9223372036854775807
-9223372036854775808
-3
```

### 17.2 Programs that fail (`examples/errors/*.cmm` + `*.err` + `*.code`)
In every case the file is invoked as `cmm run <name>.cmm` from the directory containing it, so `<path>` is just the file name. Stdout is empty unless stated.

**syntax_missing_semicolon.cmm** — exit code 1
```
module main;
fn main() {
    let x = 1
    print(x);
}
```
stderr:
```
syntax_missing_semicolon.cmm:4:5: syntax error: expected ';', found 'print'
        print(x);
        ^
```

**lexical_unterminated_string.cmm** — exit code 1
```
module main;
fn main() {
    print("oops);
}
```
stderr:
```
lexical_unterminated_string.cmm:3:11: lexical error: unterminated string literal
        print("oops);
              ^
```

**semantic_multiple.cmm** — exit code 1
```
module main;
fn main() {
    let a = 1;
    a = 2;
    b = 3;
    let c = a + "x";
}
```
stderr:
```
semantic_multiple.cmm:4:5: semantic error: cannot assign to immutable variable 'a' (declared with 'let' at line 3, column 9); declare it with 'mut' to allow assignment
        a = 2;
        ^
semantic_multiple.cmm:5:5: semantic error: undeclared variable 'b'
        b = 3;
        ^
semantic_multiple.cmm:6:15: semantic error: operator '+' cannot be applied to int and string
        let c = a + "x";
                  ^
```

**semantic_condition.cmm** — exit code 1
```
module main;
fn main() {
    mut i = 0;
    while (i) {
        i = 0;
    }
}
```
stderr:
```
semantic_condition.cmm:4:12: semantic error: condition must be of type bool, found int
        while (i) {
               ^
```

**runtime_overflow.cmm** — exit code 2, stdout empty
```
module main;
fn main() {
    mut f = 1;
    for (mut i = 1; i <= 21; i += 1) {
        f *= i;
    }
    print(f);
}
```
stderr:
```
runtime_overflow.cmm:5:11: runtime error: integer overflow
            f *= i;
              ^
```

**runtime_div_zero.cmm** — exit code 2, stdout empty
```
module main;
fn main() {
    let d = 0;
    print(10 / d);
}
```
stderr:
```
runtime_div_zero.cmm:4:14: runtime error: division by zero
        print(10 / d);
                 ^
```

The remaining error examples to include (one file each, messages from §10): assignment of wrong type (E007, e.g. `mut i = 1; i += 0.5;`), redeclaration in the same scope (E002), use of a reserved word as a variable name (`let break = 1;` → S003), missing closing brace at end of file (S001 `'}'`, found `end of file`), `x++;` (L009), `%` applied to floats (E006), `if (1) {}` (E004), text after the end of the program (S002), modulo by zero (R003), float overflow (R004, e.g. multiplying `1.0e308 * 10.0`), and `--max-steps` (R005) with a `while (true) { }` program.

---

## 18. Acceptance Checklist
The project is complete only when **all** of the following are true:

- [ ] `docs/SPEC.md` is present and unchanged.
- [ ] All files of §12.1 exist; no extra source modules were added.
- [ ] Every token, keyword, operator and literal form of §3 is implemented; every lexical error L001–L012 is reachable and tested.
- [ ] The parser implements exactly the grammar of §5.2 with the precedence of §5.3, reports only the S001 `<X>` values of §10.4, and implements S002–S004.
- [ ] The analyzer enforces §4, §6, §7.2 and reports E001–E007 with the exact messages, positions, cascade suppression and ordering of §10.5.
- [ ] The interpreter implements §7.3, §7.4, §8 exactly (truncating `/` and `%`, 64-bit overflow, float checks, short-circuit, scopes, all loop forms) and R001–R005.
- [ ] `print` output matches §9 including every row of the float table.
- [ ] The CLI offers exactly the commands and exit codes of §11, and the `tokens`/`ast` formats of §11.6.
- [ ] Error output matches §10.1 character for character, including tab handling in the caret line.
- [ ] All examples of §17 produce exactly the stated output and exit code.
- [ ] `python -m pytest -q` passes with at least the number of tests of §14.
- [ ] CI configuration, `Dockerfile`, `scripts/` and the README of §15 exist.
- [ ] Output is identical for LF, CRLF and BOM variants of the same source.
- [ ] No third-party runtime dependency. No feature outside this specification was added.
- [ ] Every place where the specification was unclear was **reported to the project owner**, not guessed.