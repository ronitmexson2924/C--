# PROMPT: Friendly Error Detection and Fix Guidance for C-- (v0.2.0)

You are working on the C-- compiler/interpreter project (`cmm` package, `docs/SPEC.md`, the v0.2.0 addendum). Read this whole prompt before touching any file.

## 0. Ground rules (read first)

1. **The "Rule Against Assumptions" of SPEC §1.5 stays in force.** If anything below is unclear, or conflicts with `SPEC.md`, STOP and ask. Do not guess.
2. **Do not change any existing diagnostic.** Error codes, message texts, line/column positions, exit codes and the order of errors are normative. Everything you add is an *additional layer on top*. All existing tests that check codes, messages and positions must still pass unchanged.
3. **Do not add language features.** This task touches diagnostics only. Do not implement anything listed in §A1.2 of the addendum.
4. Work in the existing code style. Keep rules as **data** (tables/dicts), not scattered `if` chains, the same way `cmm/builtins.py` does.

## 1. Goal

Today a user who makes a mistake sees something like:

```
error[E013] 4:4: function 'sum' does not return a value on all paths
```

That is correct but not helpful to a beginner. After this task, every error must also tell the user, **in simple everyday language**:

* **What went wrong**: what the problem is, without compiler jargon.
* **How to fix it**: a concrete action, ideally with a small corrected code example built from the user's own names.
* **Where**: the offending source line with a caret under the exact spot.

A beginner who has never studied compilers must be able to read the output and fix their program without opening the spec.

## 2. Output format

Keep the original first line exactly as it is today, then append the new blocks. Target layout (this is the required format; if it clashes with the current output format in `SPEC.md`, STOP and ask):

```
error[E013] 4:4: function 'sum' does not return a value on all paths
   |
 4 | fn sum(a: int, b: int) -> int {
   |    ^^^
what went wrong:
  The function 'sum' promises to give back an int, but in some cases it
  reaches the end without giving anything back.
how to fix:
  Make sure every possible path ends with 'return <int value>;'. For example
  add this as the last line of the function:
      return a + b;
```

Rules for the format:

* Line 1 is byte-for-byte the existing diagnostic line.
* The source snippet shows the real source line with its line number; the caret `^` run starts at the reported column and has the length of the offending token (1 if unknown). Tabs in the source line are shown as-is and the caret line must align (replace each tab before the caret by a tab, not spaces).
* If the source line is longer than 100 characters, trim it around the caret with `...` and keep the caret aligned.
* Triple-quoted strings can span lines: show only the line containing the reported position.
* Text is wrapped at **76 columns**. Code examples are indented by 6 spaces and never wrapped.
* The words `what went wrong:` and `how to fix:` are fixed English labels (no translation in this task).
* A `--no-help` CLI flag prints only the original line (old behaviour). Decide nothing else about flags; if you think another flag is needed, ask.
* Output goes to the same stream (stderr/stdout) as the original diagnostic today.
* Colour is **not** used.

## 3. Plain-language rules (very important)

Every explanation and every fix text must follow these rules:

1. **Write for a beginner.** No words like *token, lexer, parser, AST, scope resolution, operand, identifier, lvalue, arity, expression statement, symbol table*. Use: *word, symbol, name, value, number of arguments, line of code*.
2. **Two sentences maximum for "what went wrong"**, two to four short lines for "how to fix".
3. **Use the user's own names and values** (function, variable, types, numbers) through placeholders such as `{name}`, `{expected}`, `{got}`. Never print a generic text when the real name is known.
4. **Say what is wrong, then why it matters, then what to do.** Never blame the user ("you made a mistake"); describe the code ("this function never returns...").
5. **Always give an action** in "how to fix". "Fix the error" is not an action.
6. **Show a tiny corrected example** whenever one can be built safely from the user's names and types. If you cannot build a correct example reliably, show the general pattern with `<placeholders>` instead. Never show an example that would itself produce another error.
7. **Explain C--'s own rules, not another language's.** Example: for strings say "C-- has no `+` for strings", not "like in Java".
8. **Mention the language rule once**, e.g. "In C--, `let` variables cannot be changed; use `mut` if you need to change them."
9. Texts use ASCII quotes `'...'` around code names and may include `code` samples. No emoji.
10. **Consistency:** the same situation always produces the same words. Keep one place for all texts (§4).

## 4. Implementation design

### 4.1 One data module

Create `cmm/explanations.py` containing a table keyed by diagnostic code:

```python
EXPLANATIONS = {
    "E013": Explanation(
        what="The function '{name}' promises to give back a {ret}, but in some "
             "cases it reaches the end without giving anything back.",
        fix="Make sure every possible path ends with 'return <{ret} value>;'.",
        example=lambda ctx: f"return {ctx.sample_value(ctx['ret'])};",
    ),
    ...
}
```

* `ctx` is a small context object filled from the diagnostic (names, types, counts, the source line). Extend the diagnostic objects with an optional `details: dict` carrying these values **without changing** the existing message text. If a diagnostic currently has no way to carry details, add the field and fill it at the place the error is raised.
* A helper `sample_value(type)` returns a harmless literal (`0`, `0.0`, `false`, `""`, `[0]`, `list<int>()` ...) for examples.
* Missing details must never crash: if a placeholder value is missing, fall back to the generic pattern text.

### 4.2 One renderer

`cmm/diagnostic_render.py` takes (diagnostic, source text, explanation) and returns the final text of §2. The CLI, the test helpers and the web app all call this one function. No other place formats help text.

### 4.3 Data in the web app / API

For the web app (§A11), each item of `diagnostics` and `runtime_error` gains two more string fields: `explanation` and `fix` (plus `example` when present, else `null`). Existing fields stay unchanged. The playground shows them under each error and highlights the line.

## 5. Coverage: every code gets an explanation

1. First **inventory every diagnostic code that exists in the code base** (grep the lexer, parser, analyzer, interpreter, C backend, CLI) and cross-check with `SPEC.md` §7 and addendum §A7. Produce a table `code | where raised | message | has explanation`.
2. Write an explanation for **all** of them: L001–L012, S001, S003, S004 and any other S-code that exists, E001–E031 (all that exist), R001–R014 (all that exist), and any CLI/backend error. S002 is retired and must not get an entry.
3. Add a test that fails if a code raised anywhere in the project has no entry in `EXPLANATIONS`, and a test that fails if `EXPLANATIONS` contains a code that nothing raises (except explicitly listed future codes).
4. If you find a code with unclear meaning (for example E018 is not defined in the addendum), STOP and ask; do not invent an explanation.

## 6. Required explanation content (minimum quality bar)

The following show the **level of detail** required. Write all codes to the same level. Texts here are authoritative examples for tone; adapt wording to the real message placeholders.

**Lexical**
* *Unterminated string (L002):* what: "This text starts with a quote but never ends." fix: "Add the closing quote `{q}` on the same line. For text over several lines use triple quotes `'''...'''`."
* *Unknown escape (L003):* what: "A backslash must be followed by one of the allowed letters, and `\{c}` is not one." fix: "Use one of `\n \t \r \" \' \\`. To write a real backslash type `\\`."
* *Number problems (L007 etc.):* what: say exactly what is malformed (`1.` has digits missing after the dot), fix: show `1.0`.

**Syntax**
* *S001 expected X, found Y:* what: "At this spot C-- expected {X}, but found {Y}." Add a **specific hint by situation**, from a table keyed on `(X, Y)`: missing `;` at end of line (very common: show the line with `;` added), missing `)`/`}`, `=` used where `==` is meant inside `if`, a keyword used as a variable name (tell them which words are keywords), top-level text outside any function ("everything must be inside a function; start with `fn`").
* *S004 nesting too deep:* what: "The code is nested more than 200 levels deep." fix: "Split the inner part into a separate function."

**Semantic (types, names, functions, collections, switch)**
* *E008 undefined function:* what: "'{name}' is not a function that exists." fix: "Check the spelling or define it with `fn {name}(...) {...}`." Add "did you mean" (§7).
* *E010:* "'{name}' is a built-in function (it already exists) so you cannot define your own with that name. Pick another name, for example '{name}_value'."
* *E011/E012:* say the number/type expected vs given, name the parameter position, show a call with the right shape.
* *E013 / E014 / E015 / E016:* four different return problems; each says which rule was broken and shows the corrected return line.
* *E016 / type mismatches such as int vs float:* explain "C-- never converts types for you" and show the fix `parse_int(...)`/changing the declared type. Do **not** suggest casts (they do not exist).
* *E019:* "'main' starts the program and cannot be called from other code."
* *E020:* "'{name}' does not give back a value, so it cannot be used inside an expression. Call it on its own line: `{name}(...);`."
* *E021–E023 switch:* selector type, mismatching case type, duplicate case values; fix shows a corrected `case`.
* *E024/E025:* what can be indexed (string, array, list), index must be int.
* *E026 unknown method:* list the methods that **do** exist for that receiver type, taken from the method table in `cmm/builtins.py` (never retype that list).
* *E027:* array literal elements must all have the same primitive type; show a fixed literal.
* *E028/E029/E030:* mutability: "`let` variables cannot be changed. Declare it with `mut` instead: `mut {name} = ...;`." For strings: "Text cannot be changed letter by letter in C--; build the result another way, for example with a list<string>."
* *Assignment to a `let` variable / undefined variable / redeclaration / type mismatch / division by zero constant etc. (from v0.1.0 codes):* same level of detail. Read their meaning from SPEC.

**Runtime**
* *R006:* "You asked for position {i}, but the {kind} only has {n} items (valid positions are 0 to {n-1}). Positions start at 0 and cannot be negative." fix: check the loop condition, use `i < {name}.len()`.
* *R007:* "The function called itself (or others) more than 1000 levels deep." fix: "Check that your recursion has a base case that stops it."
* *R008:* "The program asked for input, but there is no more input." fix: "Provide another line of input, or check how many times the program reads."
* *R009 / R010:* show the exact text that could not be converted and the accepted forms (`42`, `-7`, `3.14`, `1e5`); note that spaces at the ends are allowed but letters, `inf`, `nan` and `1_000` are not.
* *R011:* input is not valid UTF-8; save the input as UTF-8.
* *R012:* "You tried to take from an empty {kind}." fix: "Check `{name}.is_empty()` or `{name}.len() > 0` first."
* *R013/R014:* size limits and negative size.
* Division by zero, overflow, and all other runtime codes of v0.1.0: same quality.

## 7. "Did you mean...?" suggestions

Add one helper in `cmm/suggest.py`:

* Edit-distance (Damerau-Levenshtein) based, deterministic, no external packages.
* Candidates depend on the error: undefined variable → visible variables in scope; undefined function → user functions plus built-ins; unknown method → methods of the receiver type; keyword typos (`whlie`, `fucntion`, `retrun`, `swtich`) → the active keyword list; unknown type name → the type list.
* A suggestion is shown only if distance ≤ 2 (≤ 1 for names shorter than 5 characters), and only the best one (ties: alphabetical). Add the line `did you mean '{best}'?` after "how to fix". Case-only differences count as distance 1 and are suggested (`Main` → `main`).
* Never suggest a name that would itself be invalid in that spot (for example a `let` variable where `mut` is needed).

## 8. Edge cases that must be handled

* Source with Windows line endings (`\r\n`), tabs, non-ASCII text (caret alignment is by code point; combining characters are not required to align but must not crash).
* Error at end of file (position after the last character): show the last line and put the caret after it; if the file is empty, omit the snippet.
* Several errors in one run: if the project reports more than one error today, each gets its own help block, in the same order as today. If it reports only the first, keep that. Do not change that policy; if unclear, ask.
* Very long names, very long source lines, empty details, missing source (diagnostic created from a test without source text) → fall back to the original line plus text without a snippet, never crash.
* An explanation text must never contain an unfilled `{placeholder}`; add a test that scans every rendered text for `{` `}` leftovers.

## 9. Tests (required)

1. **One golden test per diagnostic code** (all codes): a tiny failing program, the exact expected full output (original line, snippet, what, fix). Keep the programs in `tests/errors/<code>_<short_name>.cmm` with expected output next to them.
2. **Plain-language test:** a test scans all explanation texts and fails on banned jargon words (token, lexer, parser, AST, operand, identifier, arity, lvalue, symbol table, scope resolution, expression statement), on texts longer than the limits of §3, and on missing `fix`.
3. **Example validity test:** for every error whose fix includes a code example, take the user's program, apply the suggested example (where it is a mechanical replacement), re-run the compiler and assert that **that specific error is gone**. For examples that are only patterns, assert that the example text itself parses.
4. **Renderer tests:** tabs, long lines, CRLF, EOF position, non-ASCII, missing source, `--no-help`.
5. **Suggestion tests:** typos at distance 1 and 2, ties, no suggestion at distance 3, case-only difference.
6. **Compatibility test:** the first line of every diagnostic is byte-identical to the output before this task (run the old golden tests unchanged).
7. **API test:** the web app returns `explanation`, `fix`, `example` for compile errors and runtime errors.
8. **Coverage tests** of §5.

## 10. Documentation

* New page `docs/errors.md` (also shown in the web docs): one section per code with the same what/fix text, one failing example and its fix. Generate it **from `EXPLANATIONS`** with a script so it cannot drift; add a test that fails if the file is out of date.
* Update the CLI help for `--no-help`, the README and `CHANGELOG.md`.

## 11. Working method

1. Inventory all diagnostics (§5) and show me the table before writing explanations.
2. Implement the data model, renderer and suggestions with 3 codes first (E013, S001, R006). Run the tests.
3. Fill in all remaining codes.
4. Write the tests of §9, docs of §10.
5. Run the complete test suite on the existing tests: nothing that passed before may fail.

## 12. When to STOP and ask

Stop and ask me (do not choose yourself) if:
* the required output format conflicts with `SPEC.md` §7 or current output;
* a diagnostic code is unclear, missing from the spec, or has an ambiguous meaning;
* a diagnostic cannot carry the needed details without changing its existing message or position;
* you would need to change any normative message, code, position or exit code;
* you think a new CLI flag, new error code or new language feature is needed.

## 13. Definition of done and final report

Done means: every diagnostic in the project prints (1) the unchanged original line, (2) the source snippet with caret, (3) a plain-language "what went wrong", (4) a concrete "how to fix" with an example when one can be built, and (5) a "did you mean" where applicable; all tests of §9 pass; docs are generated.

Your final report must contain:
1. The table `code | message | explanation added | example type (exact/pattern/none) | suggestion type`.
2. A list of every file created or changed.
3. Test results (counts before and after).
4. Any decision you had to make, and any open question you stopped on.
5. Three sample outputs: one lexical, one semantic, one runtime error, copied from real runs.