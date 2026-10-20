# C-- Diagnostic Reference Guide

This guide documents all active compiler and runtime diagnostic codes in C-- v0.2.0,
including plain-language explanations and recommended fix actions.

## Diagnostic Codes Index

| Code | Category | Plain Explanation Summary | Example Available |
| :--- | :--- | :--- | :---: |
| `E001` | Semantic | '<name>' has not been declared in this scope. | Yes |
| `E002` | Semantic | A variable named '<name>' already exists in this scope. | Yes |
| `E003` | Semantic | In C--, variables declared with 'let' cannot be changed. | Yes |
| `E004` | Semantic | Conditions in 'if' and loops must evaluate to true or false, but go... | Yes |
| `E005` | Semantic | The '<op>' operator cannot be used on a value of type <type>. | No |
| `E006` | Semantic | The '<op>' operator cannot combine values of type <ltype> and <rtype>. | No |
| `E007` | Semantic | The variable '<name>' holds <ltype>, but the new value is <rtype>. | No |
| `E008` | Semantic | '<name>' is not a function that exists. | Yes |
| `E009` | Semantic | There is already a function named '<name>'. | No |
| `E010` | Semantic | '<name>' is a built-in function that already exists, so you cannot ... | Yes |
| `E011` | Semantic | <kind> '<name>' requires <expected_count> argument(s), but received... | No |
| `E012` | Semantic | Argument <arg_idx> of <kind> '<name>' requires a <expected_type>, b... | No |
| `E013` | Semantic | The function '<name>' promises to give back a <ret>, but in some ca... | Yes |
| `E014` | Semantic | The function '<name>' has no return type, so it cannot return a value. | Yes |
| `E015` | Semantic | The function '<name>' promises to return a <ret>, but 'return;' pro... | Yes |
| `E016` | Semantic | The function '<name>' is declared to return <expected_ret>, but thi... | Yes |
| `E017` | Semantic | The 'main' function is the entry point and must take no parameters ... | Yes |
| `E019` | Semantic | 'main' starts the program and cannot be called from other code. | No |
| `E020` | Semantic | '<name>' does not give back a value, so it cannot be used inside an... | Yes |
| `E021` | Semantic | The value in 'switch (...)' must be an int or string, but got <type>. | Yes |
| `E022` | Semantic | The case value has type <case_type>, but the switch is checking a <... | No |
| `E023` | Semantic | The case value <val> appears more than once in this switch. | No |
| `E024` | Semantic | Values of type <type> cannot be accessed with '[...]'. | No |
| `E025` | Semantic | Positions inside '[...]' must be integers, but got <type>. | Yes |
| `E026` | Semantic | Values of type <type> do not have a method named '<name>'. | No |
| `E027` | Semantic | Every item in an array literal '[...]' must have the same primitive... | Yes |
| `E028` | Semantic | The method '<name>' changes the collection, but '<v>' is an immutab... | Yes |
| `E029` | Semantic | Elements of '<v>' cannot be modified because it was declared with '... | Yes |
| `E030` | Semantic | Text cannot be changed letter by letter in C--. | No |
| `E031` | Semantic | The parameter '<name>' is listed more than once in this function's ... | No |
| `L001` | Lexical | The character '<formatted_char>' is not recognized in C-- code. | No |
| `L002` | Lexical | This text starts with a quote but never ends. | Yes |
| `L003` | Lexical | A backslash must be followed by one of the allowed letters, and '\<... | Yes |
| `L004` | Lexical | A multi-line comment starts with '/*' here, but never reaches a clo... | Yes |
| `L005` | Lexical | This integer number is too large to fit in a 64-bit signed integer. | Yes |
| `L006` | Lexical | This decimal number is too large to fit in a 64-bit floating point ... | Yes |
| `L007` | Lexical | This number is malformed. | Yes |
| `L008` | Lexical | Numbers cannot start with extra zeros. | Yes |
| `L009` | Lexical | C-- does not have a '++' operator. | Yes |
| `L010` | Lexical | C-- does not have a '--' operator. | Yes |
| `L011` | Lexical | C-- does not have a single '&' symbol. | Yes |
| `L012` | Lexical | C-- does not have a single '|' symbol. | Yes |
| `R001` | Runtime | The arithmetic calculation produced an integer too large to fit in ... | No |
| `R002` | Runtime | The program attempted to divide a number by zero. | Yes |
| `R003` | Runtime | The program attempted to compute remainder ('%') with a divisor of ... | Yes |
| `R004` | Runtime | The floating point calculation produced a number too large to repre... | No |
| `R005` | Runtime | The program ran more steps than allowed by the --max-steps limit. | No |
| `R006` | Runtime | You asked for position <index>, but the <kind> only has <length> it... | Yes |
| `R007` | Runtime | The function called itself (or others) more than 1000 levels deep. | No |
| `R008` | Runtime | The program asked for input, but there is no more input. | No |
| `R009` | Runtime | The text '<text>' could not be converted to an integer. | Yes |
| `R010` | Runtime | The text '<text>' could not be converted to a decimal number. | Yes |
| `R011` | Runtime | The input received contains bytes that are not valid UTF-8 text. | No |
| `R012` | Runtime | You tried to take from an empty <kind>. | Yes |
| `R013` | Runtime | A collection grew beyond the limit of 10,000,000 elements. | No |
| `R014` | Runtime | An array was created with a negative size of <size>. | Yes |
| `S001` | Syntax | At this spot C-- expected <expected>, but found <found>. | Yes |
| `S003` | Syntax | '<word>' is a reserved word saved for future versions of C--. | No |
| `S004` | Syntax | The code is nested more than 200 levels deep. | No |
| `T001` | Transpilation | The C backend only supports the v0.1 feature subset and cannot comp... | No |

## Semantic Diagnostics (E001 – E031)

### `E001`

**What went wrong:**  
'<name>' has not been declared in this scope.

**How to fix:**  
Declare '<name>' before using it, with 'let <name> = ...;' or 'mut <name> = ...;'.

**Example:**
```cmm
let x = 0;
```

### `E002`

**What went wrong:**  
A variable named '<name>' already exists in this scope.

**How to fix:**  
Choose a different name for this variable, or assign to the existing one without 'let' or 'mut'.

**Example:**
```cmm
x = 0;
```

### `E003`

**What went wrong:**  
In C--, variables declared with 'let' cannot be changed.

**How to fix:**  
Declare '<name>' with 'mut' instead if you need to reassign it.

**Example:**
```cmm
mut x = 0;
```

### `E004`

**What went wrong:**  
Conditions in 'if' and loops must evaluate to true or false, but got <type>.

**How to fix:**  
Use a comparison such as '==', '!=', or '<', or a boolean variable.

**Example:**
```cmm
x > 0
```

### `E005`

**What went wrong:**  
The '<op>' operator cannot be used on a value of type <type>.

**How to fix:**  
Apply '<op>' to compatible types (for example '-' on numbers, or '!' on bool).

### `E006`

**What went wrong:**  
The '<op>' operator cannot combine values of type <ltype> and <rtype>.

**How to fix:**  
Make sure both sides have matching compatible types. C-- never converts types automatically.

### `E007`

**What went wrong:**  
The variable '<name>' holds <ltype>, but the new value is <rtype>.

**How to fix:**  
Provide a value of type <ltype>, or change the variable's initial type when declared.

### `E008`

**What went wrong:**  
'<name>' is not a function that exists.

**How to fix:**  
Check the spelling or define it with 'fn <name>(...) {{ ... }}'.

**Example:**
```cmm
fn foo() {}
```

### `E009`

**What went wrong:**  
There is already a function named '<name>'.

**How to fix:**  
Give this function a unique name or remove the duplicate definition.

### `E010`

**What went wrong:**  
'<name>' is a built-in function that already exists, so you cannot define your own with that name.

**How to fix:**  
Pick another name, for example '<name>_value'.

**Example:**
```cmm
fn custom_value() {}
```

### `E011`

**What went wrong:**  
<kind> '<name>' requires <expected_count> argument(s), but received <got_count>.

**How to fix:**  
Provide the expected number of arguments in the call.

### `E012`

**What went wrong:**  
Argument <arg_idx> of <kind> '<name>' requires a <expected_type>, but received a <got_type>.

**How to fix:**  
Pass a value of type <expected_type> for argument <arg_idx>. C-- does not convert types automatically.

### `E013`

**What went wrong:**  
The function '<name>' promises to give back a <ret>, but in some cases it reaches the end without giving anything back.

**How to fix:**  
Make sure every possible path ends with 'return <<ret> value>;'. For example add this as the last line of the function:

**Example:**
```cmm
return 0;
```

### `E014`

**What went wrong:**  
The function '<name>' has no return type, so it cannot return a value.

**How to fix:**  
Use a bare 'return;' without a value, or declare a return type with '-> <type>'.

**Example:**
```cmm
return;
```

### `E015`

**What went wrong:**  
The function '<name>' promises to return a <ret>, but 'return;' provides no value.

**How to fix:**  
Provide a value of type <ret> with 'return <value>;'.

**Example:**
```cmm
return 0;
```

### `E016`

**What went wrong:**  
The function '<name>' is declared to return <expected_ret>, but this line returns <got_ret>.

**How to fix:**  
Return a value of type <expected_ret>, or change the function's return type.

**Example:**
```cmm
return 0;
```

### `E017`

**What went wrong:**  
The 'main' function is the entry point and must take no parameters and return nothing.

**How to fix:**  
Declare it as 'fn main() { ... }'.

**Example:**
```cmm
fn main() {
}
```

### `E019`

**What went wrong:**  
'main' starts the program and cannot be called from other code.

**How to fix:**  
Remove the call to 'main'. Put shared code into a helper function and call that instead.

### `E020`

**What went wrong:**  
'<name>' does not give back a value, so it cannot be used inside an expression.

**How to fix:**  
Call it on its own line: '<name>(...);'.

**Example:**
```cmm
action();
```

### `E021`

**What went wrong:**  
The value in 'switch (...)' must be an int or string, but got <type>.

**How to fix:**  
Switch on an integer or text value, or use 'if'/'else' for other types.

**Example:**
```cmm
switch (x) {
      case 1: {}
      default: {}
}
```

### `E022`

**What went wrong:**  
The case value has type <case_type>, but the switch is checking a <selector_type>.

**How to fix:**  
Make sure all case values have the same type as the switch value (<selector_type>).

### `E023`

**What went wrong:**  
The case value <val> appears more than once in this switch.

**How to fix:**  
Remove the duplicate case or change its value.

### `E024`

**What went wrong:**  
Values of type <type> cannot be accessed with '[...]'.

**How to fix:**  
Only strings, arrays, and lists can be indexed with '[position]'.

### `E025`

**What went wrong:**  
Positions inside '[...]' must be integers, but got <type>.

**How to fix:**  
Use an integer value or expression for indexing.

**Example:**
```cmm
items[0]
```

### `E026`

**What went wrong:**  
Values of type <type> do not have a method named '<name>'.

**How to fix:**  
Use one of the supported methods for None: len.

### `E027`

**What went wrong:**  
Every item in an array literal '[...]' must have the same primitive type.

**How to fix:**  
Make sure all elements have matching types, for example all int or all string.

**Example:**
```cmm
[1, 2, 3]
```

### `E028`

**What went wrong:**  
The method '<name>' changes the collection, but '<v>' is an immutable 'let' variable.

**How to fix:**  
Declare '<v>' with 'mut' instead: 'mut <v> = ...;'.

**Example:**
```cmm
mut items = list<int>();
```

### `E029`

**What went wrong:**  
Elements of '<v>' cannot be modified because it was declared with 'let'.

**How to fix:**  
Declare '<v>' with 'mut' instead to allow element assignments.

**Example:**
```cmm
mut items = [1, 2];
```

### `E030`

**What went wrong:**  
Text cannot be changed letter by letter in C--.

**How to fix:**  
Build the result another way, for example with a list<string> or by creating a new string.

### `E031`

**What went wrong:**  
The parameter '<name>' is listed more than once in this function's parameters.

**How to fix:**  
Give each parameter a distinct name.

## Lexical Diagnostics (L001 – L012)

### `L001`

**What went wrong:**  
The character '<formatted_char>' is not recognized in C-- code.

**How to fix:**  
Remove this character or replace it with valid C-- code.

### `L002`

**What went wrong:**  
This text starts with a quote but never ends.

**How to fix:**  
Add the closing quote on the same line. For text over several lines use triple quotes """...""" or '''...'''.

**Example:**
```cmm
"""multi-line text"""
```

### `L003`

**What went wrong:**  
A backslash must be followed by one of the allowed letters, and '\<esc_display>' is not one.

**How to fix:**  
Use one of \n, \t, \r, \", \', \\. To write a real backslash type '\\'.

**Example:**
```cmm
"first line\nsecond line"
```

### `L004`

**What went wrong:**  
A multi-line comment starts with '/*' here, but never reaches a closing '*/'.

**How to fix:**  
Add '*/' where the comment should end.

**Example:**
```cmm
/* comment */
```

### `L005`

**What went wrong:**  
This integer number is too large to fit in a 64-bit signed integer.

**How to fix:**  
Use an integer between -9223372036854775808 and 9223372036854775807.

**Example:**
```cmm
9223372036854775807
```

### `L006`

**What went wrong:**  
This decimal number is too large to fit in a 64-bit floating point number.

**How to fix:**  
Use a smaller number or adjust the exponent.

**Example:**
```cmm
1.0e100
```

### `L007`

**What went wrong:**  
This number is malformed.

**How to fix:**  
Write digits after the dot (for example '1.0' instead of '1.') or check the exponent format.

**Example:**
```cmm
1.0
```

### `L008`

**What went wrong:**  
Numbers cannot start with extra zeros.

**How to fix:**  
Remove the leading zero from the number.

**Example:**
```cmm
7
```

### `L009`

**What went wrong:**  
C-- does not have a '++' operator.

**How to fix:**  
Use '+= 1' to increase the value by one.

**Example:**
```cmm
x += 1;
```

### `L010`

**What went wrong:**  
C-- does not have a '--' operator.

**How to fix:**  
Use '-= 1' to decrease the value by one.

**Example:**
```cmm
x -= 1;
```

### `L011`

**What went wrong:**  
C-- does not have a single '&' symbol.

**How to fix:**  
Use '&&' for logical AND.

**Example:**
```cmm
a && b
```

### `L012`

**What went wrong:**  
C-- does not have a single '|' symbol.

**How to fix:**  
Use '||' for logical OR.

**Example:**
```cmm
a || b
```

## Runtime Diagnostics (R001 – R014)

### `R001`

**What went wrong:**  
The arithmetic calculation produced an integer too large to fit in 64 bits.

**How to fix:**  
Check the numbers being computed to prevent exceeding integer limits.

### `R002`

**What went wrong:**  
The program attempted to divide a number by zero.

**How to fix:**  
Check that the divisor is not zero before dividing.

**Example:**
```cmm
if (divisor != 0) {
      let q = n / divisor;
}
```

### `R003`

**What went wrong:**  
The program attempted to compute remainder ('%') with a divisor of zero.

**How to fix:**  
Check that the second number is not zero before using '%'.

**Example:**
```cmm
if (b != 0) {
      let r = a % b;
}
```

### `R004`

**What went wrong:**  
The floating point calculation produced a number too large to represent.

**How to fix:**  
Check your numbers to keep values within standard 64-bit float limits.

### `R005`

**What went wrong:**  
The program ran more steps than allowed by the --max-steps limit.

**How to fix:**  
Increase the --max-steps limit or check that your loops terminate.

### `R006`

**What went wrong:**  
You asked for position <index>, but the <kind> only has <length> items (valid positions are 0 to <max_index>). Positions start at 0 and cannot be negative.

**How to fix:**  
Check that your position is less than the collection length before indexing.

**Example:**
```cmm
if (i < items.len()) {
      print(items[i]);
}
```

### `R007`

**What went wrong:**  
The function called itself (or others) more than 1000 levels deep.

**How to fix:**  
Check that your recursion has a base case that stops it.

### `R008`

**What went wrong:**  
The program asked for input, but there is no more input.

**How to fix:**  
Provide another line of input, or check how many times the program reads.

### `R009`

**What went wrong:**  
The text '<text>' could not be converted to an integer.

**How to fix:**  
Provide an integer such as '42' or '-7'. Spaces at the ends are allowed, but letters, underscores, and decimals are not.

**Example:**
```cmm
parse_int("42")
```

### `R010`

**What went wrong:**  
The text '<text>' could not be converted to a decimal number.

**How to fix:**  
Provide a valid number such as '3.14' or '1e5'. Words like 'inf' or 'nan' are not allowed.

**Example:**
```cmm
parse_float("3.14")
```

### `R011`

**What went wrong:**  
The input received contains bytes that are not valid UTF-8 text.

**How to fix:**  
Ensure standard input is encoded as UTF-8 text.

### `R012`

**What went wrong:**  
You tried to take from an empty <kind>.

**How to fix:**  
Check collection.is_empty() or collection.len() > 0 before taking an item.

**Example:**
```cmm
if (!items.is_empty()) {
      items.pop();
}
```

### `R013`

**What went wrong:**  
A collection grew beyond the limit of 10,000,000 elements.

**How to fix:**  
Ensure the collection stays within the 10,000,000 element limit.

### `R014`

**What went wrong:**  
An array was created with a negative size of <size>.

**How to fix:**  
Provide a non-negative size (0 or greater) when creating an array.

**Example:**
```cmm
array<int>(5, 0)
```

## Syntax Diagnostics (S001 – S004)

### `S001`

**What went wrong:**  
At this spot C-- expected <expected>, but found <found>.

**How to fix:**  
Replace  with .

### `S003`

**What went wrong:**  
'<word>' is a reserved word saved for future versions of C--.

**How to fix:**  
Rename this to a different name, for example '<word>_val'.

### `S004`

**What went wrong:**  
The code is nested more than 200 levels deep.

**How to fix:**  
Split the inner part into a separate function.

## Transpilation Diagnostics (T001)

### `T001`

**What went wrong:**  
The C backend only supports the v0.1 feature subset and cannot compile <feature>.

**How to fix:**  
Use the reference interpreter ('cmm run') to run programs using v0.2 features.
