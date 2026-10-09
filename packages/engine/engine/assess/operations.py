"""The four operations, and what each computes (goals/md0b-division-is-an-operation.yaml). Pure: numbers in, numbers out.

One owner for what an operation is. Everything that reads one — the predictors, the verifier, the skill reader, an old
paper's printed sum, an equation, a mistake's name — folds however it is written to one sign here (`sign`), and every
answer is computed here (`compute`). A kind of question that makes only some operations says so with `require`, which
refuses in a sentence: before it, eleven kinds handed ÷ made a subtraction, several of them printing "+".

Division is exact or it is two answers. 84 ÷ 4 is 21; 85 ÷ 4 is 21 remainder 1, and a question asking for it asks for
both (`divide`). Asked for one answer, `compute` refuses rather than round down (ADR 0047, A3).
"""

# however a book, a model or a child writes an operation → the one sign the rules use
SIGNS = {
    "+": "+",
    "-": "-",
    "−": "-",
    "–": "-",
    "×": "×",
    "x": "×",
    "X": "×",
    "*": "×",
    "÷": "÷",
    "/": "÷",
    ":": "÷",
}
# the signs a paper prints: an old paper's sum (`legacy._EXPR`) and an equation (`equation`) read these, never "*",
# "/" or ":", which on paper may be a footnote, a fraction or a time
PRINTED_SIGNS = ("+", "-", "−", "–", "×", "x", "÷")
# the name the taxonomy gives each (`case_dimension` "operation")
NAMES = {"+": "ADD", "-": "SUB", "×": "MUL", "÷": "DIV"}
# the sign printed on a child's paper
PRINTED = {"+": "+", "-": "−", "×": "×", "÷": "÷"}


class CannotMake(ValueError):
    """A kind of question asked for an operation it does not make. Not a draw to try again: the bank retries a
    `RuntimeError` (numbers that did not fit), and this is the rule asking for something no draw can give."""


def sign(op: object) -> str | None:
    """The one sign for however `op` is written; None when it is no operation (or not text: a rule's list of them)."""
    return SIGNS.get(op.strip()) if isinstance(op, str) else None


def require(kind: str, op: str | None, makes: tuple[str, ...] = ("+", "-")) -> str:
    """`op` as one sign when `kind` makes it; else `CannotMake`, saying which kind and which operation."""
    one = sign(op)
    if one not in makes:
        raise CannotMake(f"{kind} makes {' and '.join(PRINTED[m] for m in makes)} questions, not {op}")
    return one


def divide(a: int, b: int) -> tuple[int, int]:
    """(quotient, remainder): 85 ÷ 4 → (21, 1)."""
    if b == 0:
        raise ValueError(f"{a} ÷ 0: nothing divides by 0")
    return a // b, a % b


def compute(op: str | None, a: int, b: int) -> int:
    """The one answer `a op b` has. A division that leaves a remainder has two, and is refused here."""
    one = sign(op)
    if one == "+":
        return a + b
    if one == "-":
        return a - b
    if one == "×":
        return a * b
    if one == "÷":
        q, r = divide(a, b)
        if r:
            raise ValueError(f"{a} ÷ {b} is {q} r {r}: two answers, the quotient and the remainder")
        return q
    raise ValueError(f"{op!r} is not an operation")


def times_columns(a: int, d: int) -> list[dict[str, int]]:
    """`a` times one digit `d` in columns, from the ones: each column's digit, its product, the carry it takes in, its
    value and the carry it sends on. 56 × 3: 6 × 3 = 18 sends 1; 5 × 3 + 1 = 16, the answer's lead."""
    cols: list[dict[str, int]] = []
    carry = 0
    for x in reversed(str(a)):
        value = int(x) * d + carry
        cols.append(
            {
                "digit": int(x),
                "product": int(x) * d,
                "carry_in": carry,
                "value": value,
                "carry_out": value // 10,
            }
        )
        carry = value // 10
    return cols


def rows(a: int, b: int) -> list[int]:
    """Long multiplication's rows, one for each digit of `b` from its ones, each moved its place along; a 0 digit
    writes no row. 68 × 17 → [476, 680]."""
    return [a * int(x) * 10**i for i, x in enumerate(reversed(str(b))) if x != "0"]


def short_division(n: int, d: int) -> list[dict[str, int]]:
    """`n` ÷ `d` left to right, as short division is written: each digit, the value it makes with the remainder
    exchanged into it, that step's quotient digit and the remainder it exchanges on. 72 ÷ 4: 7 → 1 r 3; 32 → 8 r 0."""
    steps: list[dict[str, int]] = []
    r = 0
    for x in str(n):
        value = r * 10 + int(x)
        steps.append({"digit": int(x), "value": value, "q": value // d, "r": value % d})
        r = value % d
    return steps


def chain(op: str, numbers: list[int]) -> int:
    """The answer to a question with however many numbers it has, read left to right: `8000 - 25 - 40` is 7935, not
    7975. A budget question is a chain, and reading only its first two numbers is how a proposal about one came to be
    thrown away for arithmetic that was never wrong."""
    total = numbers[0]
    for n in numbers[1:]:
        total = compute(op, total, n)
    return total
