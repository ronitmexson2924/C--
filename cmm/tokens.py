"""Token definitions and TokenType enumeration for the C-- language."""

from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    """All token types supported in C-- version 0.2.0."""

    # Keywords (Section 3.8 and §A3.1)
    MODULE = auto()
    FN = auto()
    MAIN = auto()
    LET = auto()
    MUT = auto()
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    DO = auto()
    FOR = auto()
    PRINT = auto()
    TRUE = auto()
    FALSE = auto()
    RETURN = auto()
    SWITCH = auto()
    CASE = auto()
    DEFAULT = auto()
    KW_INT = auto()
    KW_FLOAT = auto()
    KW_BOOL = auto()
    KW_STRING = auto()
    KW_ARRAY = auto()
    KW_LIST = auto()
    KW_STACK = auto()
    KW_QUEUE = auto()

    # Other literals and identifiers
    IDENT = auto()
    RESERVED = auto()
    INT = auto()
    FLOAT = auto()
    STRING = auto()

    # Operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    EQ = auto()
    EQEQ = auto()
    BANG = auto()
    BANGEQ = auto()
    LT = auto()
    LTEQ = auto()
    GT = auto()
    GTEQ = auto()
    ANDAND = auto()
    OROR = auto()
    PLUSEQ = auto()
    MINUSEQ = auto()
    STAREQ = auto()
    SLASHEQ = auto()
    PERCENTEQ = auto()
    ARROW = auto()  # ->

    # Punctuation
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()  # [
    RBRACKET = auto()  # ]
    COMMA = auto()     # ,
    COLON = auto()     # :
    DOT = auto()       # .
    SEMI = auto()

    # End of file
    EOF = auto()


@dataclass(frozen=True)
class Token:
    """Represents a lexical token in C--.

    Attributes:
        type: The category of token from TokenType.
        lexeme: The exact source text of the token (empty string for EOF).
        value: Parsed Python value for INT, FLOAT, STRING; None otherwise.
        line: 1-based line number where the token starts.
        col: 1-based column number where the token starts.
    """

    type: TokenType
    lexeme: str
    value: object
    line: int
    col: int


# Active language keywords (Section 3.4 & §A3.1)
KEYWORDS: dict[str, TokenType] = {
    "module": TokenType.MODULE,
    "fn": TokenType.FN,
    "main": TokenType.MAIN,
    "let": TokenType.LET,
    "mut": TokenType.MUT,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "do": TokenType.DO,
    "for": TokenType.FOR,
    "print": TokenType.PRINT,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "return": TokenType.RETURN,
    "switch": TokenType.SWITCH,
    "case": TokenType.CASE,
    "default": TokenType.DEFAULT,
    "int": TokenType.KW_INT,
    "float": TokenType.KW_FLOAT,
    "bool": TokenType.KW_BOOL,
    "string": TokenType.KW_STRING,
    "array": TokenType.KW_ARRAY,
    "list": TokenType.KW_LIST,
    "stack": TokenType.KW_STACK,
    "queue": TokenType.KW_QUEUE,
}

# Reserved words for future use (Section 3.4 & §A3.1)
RESERVED_WORDS: dict[str, TokenType] = {
    "break": TokenType.RESERVED,
    "continue": TokenType.RESERVED,
    "struct": TokenType.RESERVED,
    "enum": TokenType.RESERVED,
    "match": TokenType.RESERVED,
    "import": TokenType.RESERVED,
    "null": TokenType.RESERVED,
    "defer": TokenType.RESERVED,
    "loop": TokenType.RESERVED,
    "in": TokenType.RESERVED,
    "as": TokenType.RESERVED,
    "const": TokenType.RESERVED,
    "var": TokenType.RESERVED,
    "type": TokenType.RESERVED,
}

# Combined dictionary mapping keywords and reserved words
KEYWORD_AND_RESERVED: dict[str, TokenType] = {**KEYWORDS, **RESERVED_WORDS}
