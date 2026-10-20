"""Lexer and source text normalization for C-- v0.2.0."""

import math
from cmm.errors import LexError
from cmm.tokens import KEYWORDS, RESERVED_WORDS, Token, TokenType


def normalize_source(text: str) -> str:
    """Normalize source text per Section 2 of SPEC.md.

    1. Removes leading U+FEFF (BOM) if present (§2.3).
    2. Converts '\r\n' and lone '\r' to '\n' (§2.4).

    Args:
        text: Raw source code string.

    Returns:
        Normalized source string containing only '\n' line endings.
    """
    if text.startswith("\ufeff"):
        text = text[1:]
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _format_char_for_l001(c: str) -> str:
    """Format a character for error L001.

    Printable characters appear as themselves; control characters and
    characters with no visible glyph appear as 'U+XXXX'.
    """
    if ord(c) < 32 or (127 <= ord(c) <= 159) or not c.isprintable():
        return f"U+{ord(c):04X}"
    return c


def tokenize(source: str) -> list[Token]:
    """Tokenize normalized source code into a list of tokens.

    Assumes source text has already been normalized via normalize_source().
    Stops at the first lexical error and raises LexError.
    Always appends an EOF token as the final token.

    Args:
        source: Normalized source code.

    Returns:
        List of Token instances ending with TokenType.EOF.

    Raises:
        LexError: Upon encountering any lexical error (L001-L012).
    """
    tokens: list[Token] = []
    pos = 0
    line = 1
    col = 1
    length = len(source)

    def advance() -> str:
        nonlocal pos, line, col
        c = source[pos]
        pos += 1
        if c == "\n":
            line += 1
            col = 1
        else:
            col += 1
        return c

    while pos < length:
        # 1. Whitespace handling (§3.1)
        c = source[pos]
        if c in (" ", "\t", "\n"):
            advance()
            continue

        # 2. Comments (§3.2)
        if c == "/" and pos + 1 < length:
            next_c = source[pos + 1]
            if next_c == "/":
                # Line comment: runs to end of line, newline is not part of comment
                advance()  # consume first '/'
                advance()  # consume second '/'
                while pos < length and source[pos] != "\n":
                    advance()
                continue
            elif next_c == "*":
                # Block comment: runs until '*/', does not nest (§3.2)
                start_comment_line = line
                start_comment_col = col
                advance()  # consume '/'
                advance()  # consume '*'
                closed = False
                while pos < length:
                    if source[pos] == "*" and pos + 1 < length and source[pos + 1] == "/":
                        advance()  # consume '*'
                        advance()  # consume '/'
                        closed = True
                        break
                    advance()
                if not closed:
                    raise LexError("L004", "unterminated block comment", start_comment_line, start_comment_col)
                continue

        # Record start position of the next token
        start_line = line
        start_col = col
        start_pos = pos

        # 3. Identifiers and Keywords (§3.3, §3.4, §A3.1)
        if c.isascii() and (c.isalpha() or c == "_"):
            while pos < length and source[pos].isascii() and (source[pos].isalnum() or source[pos] == "_"):
                advance()
            lexeme = source[start_pos:pos]
            if lexeme in KEYWORDS:
                tokens.append(Token(KEYWORDS[lexeme], lexeme, None, start_line, start_col))
            elif lexeme in RESERVED_WORDS:
                tokens.append(Token(TokenType.RESERVED, lexeme, None, start_line, start_col))
            else:
                tokens.append(Token(TokenType.IDENT, lexeme, None, start_line, start_col))
            continue

        # 4. Numbers (§3.5)
        if "0" <= c <= "9":
            # Step 1: Read maximal run of digits -> D
            while pos < length and "0" <= source[pos] <= "9":
                advance()
            d_part = source[start_pos:pos]
            if len(d_part) > 1 and d_part.startswith("0"):
                raise LexError("L008", "leading zeros are not allowed in number literals", start_line, start_col)

            is_float = False

            # Step 2: Check for '.'
            if pos < length and source[pos] == ".":
                if pos + 1 < length and "0" <= source[pos + 1] <= "9":
                    is_float = True
                    advance()  # consume '.'
                    while pos < length and "0" <= source[pos] <= "9":
                        advance()
                else:
                    raise LexError("L007", "invalid number literal", start_line, start_col)

            # Step 3 & 4: Check for exponent 'e' or 'E'
            if is_float and pos < length and source[pos] in ("e", "E"):
                idx = pos + 1
                if idx < length and source[idx] in ("+", "-"):
                    idx += 1
                if idx < length and "0" <= source[idx] <= "9":
                    advance()  # consume 'e' or 'E'
                    if pos < length and source[pos] in ("+", "-"):
                        advance()  # consume '+' or '-'
                    while pos < length and "0" <= source[pos] <= "9":
                        advance()
                else:
                    raise LexError("L007", "invalid number literal", start_line, start_col)
            elif not is_float and pos < length and source[pos] in ("e", "E"):
                raise LexError("L007", "invalid number literal", start_line, start_col)

            # Step 5: Check character immediately after literal
            if pos < length:
                next_c = source[pos]
                if next_c.isalpha() or next_c.isdigit() or next_c == "_":
                    raise LexError("L007", "invalid number literal", start_line, start_col)

            # Step 6: Range checks
            lexeme = source[start_pos:pos]
            if not is_float:
                int_val = int(lexeme)
                if int_val > 9223372036854775807:
                    raise LexError("L005", "integer literal out of range", start_line, start_col)
                tokens.append(Token(TokenType.INT, lexeme, int_val, start_line, start_col))
            else:
                try:
                    float_val = float(lexeme)
                    if math.isinf(float_val):
                        raise LexError("L006", "float literal out of range", start_line, start_col)
                except OverflowError:
                    raise LexError("L006", "float literal out of range", start_line, start_col)
                tokens.append(Token(TokenType.FLOAT, lexeme, float_val, start_line, start_col))
            continue


        # 5. Strings (§3.5 & §A3.3)
        if c in ('"', "'"):
            q = c
            is_triple = False
            if pos + 2 < length and source[pos + 1] == q and source[pos + 2] == q:
                is_triple = True
                advance()  # 1st quote
                advance()  # 2nd quote
                advance()  # 3rd quote
            else:
                advance()  # single quote

            chars: list[str] = []
            closed = False
            while pos < length:
                if is_triple:
                    if source[pos] == q and pos + 2 < length and source[pos + 1] == q and source[pos + 2] == q:
                        advance()
                        advance()
                        advance()
                        closed = True
                        break
                    sc = source[pos]
                    if sc == "\\":
                        esc_line = line
                        esc_col = col
                        advance()  # consume '\'
                        if pos >= length:
                            raise LexError("L002", "unterminated string literal", start_line, start_col)
                        esc_c = source[pos]
                        advance()  # consume escaped char
                        if esc_c == "n":
                            chars.append("\n")
                        elif esc_c == "t":
                            chars.append("\t")
                        elif esc_c == "r":
                            chars.append("\r")
                        elif esc_c == '"':
                            chars.append('"')
                        elif esc_c == "'":
                            chars.append("'")
                        elif esc_c == "\\":
                            chars.append("\\")
                        else:
                            esc_display = "U+000A" if esc_c == "\n" else esc_c
                            raise LexError("L003", f"invalid escape sequence '\\{esc_display}'", esc_line, esc_col)
                    else:
                        chars.append(advance())
                else:
                    sc = source[pos]
                    if sc == "\n":
                        raise LexError("L002", "unterminated string literal", start_line, start_col)
                    if sc == q:
                        advance()  # consume closing quote
                        closed = True
                        break
                    if sc == "\\":
                        esc_line = line
                        esc_col = col
                        advance()  # consume '\'
                        if pos >= length or source[pos] == "\n":
                            raise LexError("L002", "unterminated string literal", start_line, start_col)
                        esc_c = source[pos]
                        advance()  # consume escaped char
                        if esc_c == "n":
                            chars.append("\n")
                        elif esc_c == "t":
                            chars.append("\t")
                        elif esc_c == "r":
                            chars.append("\r")
                        elif esc_c == '"':
                            chars.append('"')
                        elif esc_c == "'":
                            chars.append("'")
                        elif esc_c == "\\":
                            chars.append("\\")
                        else:
                            esc_display = "U+000A" if esc_c == "\n" else esc_c
                            raise LexError("L003", f"invalid escape sequence '\\{esc_display}'", esc_line, esc_col)
                    else:
                        chars.append(advance())

            if not closed:
                raise LexError("L002", "unterminated string literal", start_line, start_col)

            lexeme = source[start_pos:pos]
            tokens.append(Token(TokenType.STRING, lexeme, "".join(chars), start_line, start_col))
            continue

        # 6. Operators and Punctuation (§3.6 & §A3.1)
        if c == "+":
            advance()
            if pos < length and source[pos] == "+":
                raise LexError("L009", "'++' is not supported; use '+= 1'", start_line, start_col)
            if pos < length and source[pos] == "=":
                advance()
                tokens.append(Token(TokenType.PLUSEQ, "+=", None, start_line, start_col))
            else:
                tokens.append(Token(TokenType.PLUS, "+", None, start_line, start_col))
            continue

        if c == "-":
            advance()
            if pos < length and source[pos] == "-":
                raise LexError("L010", "'--' is not supported; use '-= 1'", start_line, start_col)
            if pos < length and source[pos] == "=":
                advance()
                tokens.append(Token(TokenType.MINUSEQ, "-=", None, start_line, start_col))
            elif pos < length and source[pos] == ">":
                advance()
                tokens.append(Token(TokenType.ARROW, "->", None, start_line, start_col))
            else:
                tokens.append(Token(TokenType.MINUS, "-", None, start_line, start_col))
            continue

        if c == "*":
            advance()
            if pos < length and source[pos] == "=":
                advance()
                tokens.append(Token(TokenType.STAREQ, "*=", None, start_line, start_col))
            else:
                tokens.append(Token(TokenType.STAR, "*", None, start_line, start_col))
            continue

        if c == "/":
            advance()
            if pos < length and source[pos] == "=":
                advance()
                tokens.append(Token(TokenType.SLASHEQ, "/=", None, start_line, start_col))
            else:
                tokens.append(Token(TokenType.SLASH, "/", None, start_line, start_col))
            continue

        if c == "%":
            advance()
            if pos < length and source[pos] == "=":
                advance()
                tokens.append(Token(TokenType.PERCENTEQ, "%=", None, start_line, start_col))
            else:
                tokens.append(Token(TokenType.PERCENT, "%", None, start_line, start_col))
            continue

        if c == "=":
            advance()
            if pos < length and source[pos] == "=":
                advance()
                tokens.append(Token(TokenType.EQEQ, "==", None, start_line, start_col))
            else:
                tokens.append(Token(TokenType.EQ, "=", None, start_line, start_col))
            continue

        if c == "!":
            advance()
            if pos < length and source[pos] == "=":
                advance()
                tokens.append(Token(TokenType.BANGEQ, "!=", None, start_line, start_col))
            else:
                tokens.append(Token(TokenType.BANG, "!", None, start_line, start_col))
            continue

        if c == "<":
            advance()
            if pos < length and source[pos] == "=":
                advance()
                tokens.append(Token(TokenType.LTEQ, "<=", None, start_line, start_col))
            else:
                tokens.append(Token(TokenType.LT, "<", None, start_line, start_col))
            continue

        if c == ">":
            advance()
            if pos < length and source[pos] == "=":
                advance()
                tokens.append(Token(TokenType.GTEQ, ">=", None, start_line, start_col))
            else:
                tokens.append(Token(TokenType.GT, ">", None, start_line, start_col))
            continue

        if c == "&":
            advance()
            if pos < length and source[pos] == "&":
                advance()
                tokens.append(Token(TokenType.ANDAND, "&&", None, start_line, start_col))
            else:
                raise LexError("L011", "single '&' is not supported; did you mean '&&'?", start_line, start_col)
            continue

        if c == "|":
            advance()
            if pos < length and source[pos] == "|":
                advance()
                tokens.append(Token(TokenType.OROR, "||", None, start_line, start_col))
            else:
                raise LexError("L012", "single '|' is not supported; did you mean '||'?", start_line, start_col)
            continue

        if c == "(":
            advance()
            tokens.append(Token(TokenType.LPAREN, "(", None, start_line, start_col))
            continue

        if c == ")":
            advance()
            tokens.append(Token(TokenType.RPAREN, ")", None, start_line, start_col))
            continue

        if c == "{":
            advance()
            tokens.append(Token(TokenType.LBRACE, "{", None, start_line, start_col))
            continue

        if c == "}":
            advance()
            tokens.append(Token(TokenType.RBRACE, "}", None, start_line, start_col))
            continue

        if c == "[":
            advance()
            tokens.append(Token(TokenType.LBRACKET, "[", None, start_line, start_col))
            continue

        if c == "]":
            advance()
            tokens.append(Token(TokenType.RBRACKET, "]", None, start_line, start_col))
            continue

        if c == ",":
            advance()
            tokens.append(Token(TokenType.COMMA, ",", None, start_line, start_col))
            continue

        if c == ":":
            advance()
            tokens.append(Token(TokenType.COLON, ":", None, start_line, start_col))
            continue

        if c == ".":
            advance()
            tokens.append(Token(TokenType.DOT, ".", None, start_line, start_col))
            continue

        if c == ";":
            advance()
            tokens.append(Token(TokenType.SEMI, ";", None, start_line, start_col))
            continue

        # 7. Any other character -> L001 (§3.1, §3.6)
        formatted_char = _format_char_for_l001(c)
        raise LexError("L001", f"unexpected character '{formatted_char}'", start_line, start_col)

    # Append EOF token (§2.6)
    tokens.append(Token(TokenType.EOF, "", None, line, col))
    return tokens
