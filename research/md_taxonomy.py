"""The multiplication & division taxonomy, drafted by the engine for Achal to correct (Nimish, 2026-10-09: "need a
properly drafted taxonomy by the system itself ... consider all of the methods for now").

Every example is computed here, never typed: each case states the property that makes it a case (a carry from the
ones, a zero in the quotient, a remainder of divisor - 1 ...) and that property is measured on its own numbers. Every
named mistake's wrong answer is computed by a predictor and must differ from the right answer. Every case is placed
in a skill's level or listed as unplaced. Any failure stops the run and names the case.

    packages/engine/.venv/bin/python research/md_taxonomy.py          # check, then write the two files below
    packages/engine/.venv/bin/python research/md_taxonomy.py --check  # check only

Writes docs/design/multiplication-division-taxonomy.md (the document) and docs/design/multiplication-division-cases.json
(the cases as data, for the build's taxonomy_case rows)."""

import json
import random
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "packages" / "engine"))
from engine.assess import misconceptions as M  # noqa: E402  the engine's own addition predictors, reused

PLACES = ["ONES", "TENS", "HUNDREDS", "THOUSANDS", "TEN_THOUSANDS"]
CASES, SECTIONS, FAULTS = [], [], []


# ---------------------------------------------------------------- arithmetic, measured column by column


def digits(n):
    return [int(c) for c in str(n)]


def nd(n):
    return len(str(n))


def mul1(a, d):
    """a times one digit d, from the ones: each column's digit, product, carry in, carry out."""
    cols, carry = [], 0
    for x in reversed(digits(a)):
        v = x * d + carry
        cols.append({"digit": x, "prod": x * d, "carry_in": carry, "value": v, "carry_out": v // 10})
        carry = v // 10
    return cols


def carries(a, d):
    """The carries a 1-digit multiplication writes into a next column (the last column's is the answer's lead)."""
    return [c["carry_out"] for c in mul1(a, d)[:-1]]


def regroup_at(a, d):
    return [PLACES[i] for i, c in enumerate(carries(a, d)) if c]


def grows(a, d):
    return nd(a * d) > nd(a)


def knock_on(a, d):
    """A column whose own product is under ten but the carry takes it to ten or more."""
    return any(c["prod"] < 10 <= c["value"] for c in mul1(a, d))


def carry_into_zero(a, d):
    return any(c["digit"] == 0 and c["carry_in"] for c in mul1(a, d))


def partials(a, b):
    """Long multiplication's rows, one per digit of b, each moved its place along (a zero digit writes no row)."""
    return [a * x * 10**i for i, x in enumerate(reversed(digits(b))) if x]


def add_carries(*nums):
    """How many columns carry when the numbers are added in columns."""
    width, carry, n = max(nd(x) for x in nums), 0, 0
    for i in range(width):
        carry = (sum((x // 10**i) % 10 for x in nums) + carry) // 10
        n += bool(carry)
    return n


def partial_regroups(a, b):
    """Whether each row of a long multiplication regroups, ones row first."""
    return [any(carries(a, x)) for x in reversed(digits(b)) if x]


def divide(n, d):
    """Short division, left to right: each step's value, quotient digit and remainder carried on."""
    steps, r = [], 0
    for x in digits(n):
        v = r * 10 + x
        steps.append({"digit": x, "value": v, "q": v // d, "r": v % d})
        r = v % d
    return steps


def first_smaller(n, d):
    return digits(n)[0] < d


def exchanges(n, d):
    """Places whose remainder moves to the next digit (a first digit smaller than the divisor moves whole)."""
    s = divide(n, d)
    return [PLACES[len(s) - 1 - i] for i, st in enumerate(s[:-1]) if st["r"]]


def qzero(n, d):
    q = str(n // d)
    if "0" in q[:-1]:
        return "MIDDLE"
    return "END" if q.endswith("0") and len(q) > 1 else "NONE"


def qr(n, d):
    return f"{n // d} r {n % d}"


def unique(test, space=range(10)):
    return [x for x in space if test(x)]


# ---------------------------------------------------------------- the document's grammar


def section(num, title, lead):
    SECTIONS.append({"num": num, "title": title, "lead": lead, "codes": []})


def case(code, label, example, answer, checks=(), op="×"):
    for what, ok in checks:
        if not ok:
            FAULTS.append(f"{code}: {what} does not hold for {example}")
    if any(c["code"] == code for c in CASES):
        FAULTS.append(f"{code}: twice")
    CASES.append({"code": code, "section": SECTIONS[-1]["num"], "label": label, "example": example,
                  "answer": str(answer), "op": op})
    SECTIONS[-1]["codes"].append(code)


def fact(code, label, a, b, group):
    case(code, label, f"{a} × {b}", a * b, [(f"fact group {group}", fact_group(a, b) == group)])


GROUP = {0: "0-1", 1: "0-1", 2: "2-5-10", 5: "2-5-10", 10: "2-5-10", 3: "3-4", 4: "3-4", 6: "6-9", 7: "6-9",
         8: "6-9", 9: "6-9", 11: "11-12", 12: "11-12"}
ORDER = ["0-1", "2-5-10", "3-4", "6-9", "11-12"]


def fact_group(a, b):
    """The easiest table that holds the fact within its first ten rows."""
    options = [GROUP[f] for f, other in ((a, b), (b, a)) if other <= 10]
    return min(options, key=ORDER.index) if options else "11-12"


def pick(code, pool):
    """A natural-looking example from every number that has the case's property, the same on every run."""
    if not pool:
        FAULTS.append(f"{code}: no numbers have this property")
        return (0, 1)
    return random.Random(code).choice(sorted(pool))


NO_ZERO_3D = [a for a in range(111, 1000) if "0" not in str(a)]

# ---------------------------------------------------------------- 0, 1: assumptions and dimensions (prose)

ASSUMPTIONS = [
    ("Every method is a case.", "Straight levels (Easy to Hard) print each calculation in every written method this "
     "document lists for its shape, in fair shares: in a line, in columns, expanded, partitioning, grid, and lattice "
     "for 2-digit × 2-digit; for division, in a line, short division, long division, partitioning the number and "
     "chunking. Pictures (groups, arrays, number lines) belong to the concept skills.",
     "Nimish, 2026-10-09: \"consider all of the methods for now\". A level's methods are a row, so a grade that "
     "teaches one method narrows it without code."),
    ("Division prints in a line by default.", "\"85 ÷ 4 = □ r □\"; short division (bus stop), long division (quotient "
     "on top) and chunking are presentations of the same numbers.", "The school's July papers write \"144 ÷ 12 =\". "
     "If the school writes the older \"4 ) 85 ( 21\" layout, it is one more presentation."),
    ("A remainder is written \"r\" and is its own answer.", "The quotient and the remainder each get their own boxes "
     "and are marked separately.", "One box holding \"21 r 1\" cannot be read digit by digit, and a wrong remainder "
     "with a right quotient is a different mistake from the reverse."),
    ("Tables run from 0 to 12.", "×11 and ×12 appear only at Advance: a fact that needs the 11 or 12 tables, either "
     "way round (3 × 12, 12 × 7), is no Easy, Medium or Hard question, and the tables' Advance holds every table. "
     "12 × 0 and 11 × 1 are the facts of 0 and 1.", "The school's 24 Jul quiz asks 11 × 4 and 12 × 5; the Grade 4 "
     "paper asks 144 ÷ 12."),
    ("The school's words.", "\"Regroup\" for a multiplication carry, \"exchange\" when a remainder moves to the next "
     "digit, never \"borrow\". \"Product, factor, dividend, divisor, quotient, remainder\" from Grade 3; \"times, "
     "groups of, shared equally, left over\" before it.", "CLAUDE.md: \"exchange / regroup\", never \"borrow\"."),
    ("Grades come from the school's own objectives.", "Registry LO-G1-0046 to 0055, LO-G2-0492 to 0498 and 0527 to "
     "0530, LO-G3-0942 to 0944 and 0956 to 0959, LO-G4-1339 to 1356, and the July papers. 4-digit × 1-digit, "
     "3-digit × 2-digit and division by a 2-digit number beyond ÷12 are in no G1 to G4 objective: they are here, "
     "placed in no grade. Where the lists disagree (one \"Extended & Application\" unit is repeated in G2, G3 and G4), a "
     "level goes to the earliest grade whose objective names it, except Grade 1, which is exactly what its educator "
     "taught to the end of September (2026-10-06): equal groups by adding again. A level the objectives put in Grade 1 "
     "sits in Grade 2 until the Grade 1 educator says it is taught.", "A level's grade is a row "
     "(`skill_set.level_band`); Achal moves it."),
    ("Taught stays the educator's word.", "Every case is built and checked; nothing reaches a child's paper until "
     "the grade declares it taught.", "The Grade 1 rule of 2026-10-06."),
    ("Out of scope.", "Remainders as fractions or decimals. Division by zero appears only as a true-or-false "
     "statement, never as a sum.", "No G1 to G4 objective names them."),
    ("Stories fit their numbers.", "Each story template carries the range its numbers may take, so no box holds 933 "
     "pencils.", "Today's multiplication bank prints \"Each box has 933 pencils\"."),
    ("Both orders.", "\"4 × 36\" and \"36 × 4\" are both asked, as addition prints the shorter number first.",
     "A child who knows 3 × 8 from the 3 table may not know 8 × 3."),
    ("What a mistake charges.", "A slip adding the partial products counts against addition, not multiplication; "
     "the table of what each mistake charges waits for one approval, as addition's did.", "ADR 0023."),
    ("Lattice is included.", "Because every method is; it leaves by taking its cases out of the levels.",
     "Not named in the school's objectives."),
]

DIMENSIONS = [
    ("Operation", "Multiplication / Division", "Inverse of each other; different mistakes and layouts."),
    ("Digits in each number", "1 / 2 / 3 / 4 / N; for ÷ the number divided and the divisor",
     "Sets the number of columns, partial products and steps."),
    ("Fact group", "0-1 / 2-5-10 / 3-4 / 6-9 / 11-12", "Tables are learned in groups; a child can know ×5 and not ×7."),
    ("Place-value factor", "none / ×10 / ×100 / ×1000 / a multiple of ten (one or both numbers)",
     "Zeros counted, dropped or doubled are their own mistakes."),
    ("Method", "in a line, columns, expanded, partitioning, grid, lattice, repeated addition, skip counting, number "
     "line, array, groups; sharing, grouping, repeated subtraction, chunking, short division, long division",
     "Each method has mistakes the others cannot make."),
    ("Regrouping (×)", "none / one column / several; where: ones / tens / hundreds",
     "A child may carry from the ones and not from the tens."),
    ("Carry size (×)", "none / always 1 / more than 1", "Adding two numbers only ever carries 1; multiplication carries up to 8."),
    ("Knock-on (×)", "a carry that takes a column to ten or more", "The column regroups only because of the carry."),
    ("Partial products (×)", "1 / 2 / 3 rows; their sum with or without a carry",
     "The placeholder zero and the adding of rows are separate skills."),
    ("Exchange (÷)", "none / one step / several", "A remainder moving to the next digit is the heart of short division."),
    ("First digit smaller (÷)", "yes / no", "The quotient has one digit fewer; children skip or write a zero."),
    ("Zero in the quotient (÷)", "none / in the middle / at the end", "The most dropped digit in division."),
    ("Remainder (÷)", "none / some / largest possible (divisor − 1) / number smaller than the divisor",
     "Separates exact division from division with a remainder, and tests remainder < divisor."),
    ("Zeros in the numbers", "none / in the middle / at the end / in the multiplier / a zero only in the answer",
     "Zeros change what is written in a column."),
    ("Answer size", "the most digits possible / one fewer", "Magnitude awareness."),
    ("Unknown", "none / a factor / the dividend / the divisor / a digit / the remainder / the sign",
     "Reverse reasoning, separately from calculation."),
    ("Question type", "direct / missing / balance / true-false / compare / find the mistake / estimate / story",
     "Calculation, reasoning and application measured apart."),
    ("Story structure", "equal groups, sharing, grouping, array, rate, times as many, combinations, area, two steps",
     "Same numbers, different difficulty."),
    ("Remainder in a story", "dropped / rounded up / the answer itself / both asked",
     "26 children in rickshaws of 4 need 7 rickshaws, not 6."),
]

# ---------------------------------------------------------------- 2. multiplication facts and place value

section(2, "Multiplication facts and place value",
        "Facts are grouped as tables are learned; ×10, ×100 and multiples of ten are their own cases because the "
        "mistakes are about zeros, not tables.")
fact("TF01", "×0: anything times zero", 7, 0, "0-1")
fact("TF02", "×1: anything times one", 1, 8, "0-1")
fact("TF03", "The 2 table", 2, 7, "2-5-10")
fact("TF04", "The 5 table", 5, 6, "2-5-10")
fact("TF05", "The 10 table", 10, 4, "2-5-10")
fact("TF06", "The 3 table", 3, 8, "3-4")
fact("TF07", "The 4 table", 4, 7, "3-4")
fact("TF08", "The 6 table", 6, 7, "6-9")
fact("TF09", "The 7 table", 7, 8, "6-9")
fact("TF10", "The 8 table", 8, 6, "6-9")
fact("TF11", "The 9 table", 9, 6, "6-9")
fact("TF12", "A square fact", 7, 7, "6-9")
fact("TF13", "The 11 table", 11, 4, "11-12")
fact("TF14", "The 12 table", 12, 5, "11-12")
case("TF15", "The table number second (the 3 table read the other way)", "8 × 3", 24,
     [("same as 3 × 8", 8 * 3 == 3 * 8)])
case("TF16", "A fact in columns", "7 over 6 in columns, ×", 42)
case("TF17", "A cell of the multiplication square", "row 6, column 9", 54, [("6 × 9", 6 * 9 == 54)])
case("TP01", "×10", "45 × 10", 450)
case("TP02", "×100", "45 × 100", 4500)
case("TP03", "×1000", "7 × 1000", 7000)
case("TP04", "×10 of a number already ending in zero", "30 × 10", 300)
case("TP05", "×100 of a number with a zero inside", "405 × 100", 40500, [("zero inside", "0" in str(405)[1:-1])])
case("TP06", "A multiple of ten × 1 digit", "30 × 4", 120)
case("TP07", "A multiple of ten × a multiple of ten", "20 × 40", 800)
case("TP08", "A multiple of a hundred × 1 digit", "300 × 6", 1800)
case("TP09", "The fact makes its own zero", "50 × 4", 200, [("5 × 4 ends in 0", (5 * 4) % 10 == 0)])
case("TP10", "2 digits × a multiple of ten", "23 × 30", 690)
# ×100 of a number already ending in zero, as TP04 is for ×10: no case held 30 × 100 (measured 2026-10-09)
case("TP11", "×100 of a number already ending in zero", "30 × 100", 3000)

# ---------------------------------------------------------------- 3. multiplication by digit shape

section(3, "Multiplication by digit shape",
        "One case per shape and per thing that changes the working; the next section crosses the carries and zeros in full.")


def mul(code, label, a, b, checks=(), line=False):
    shown = f"{a} × {b}" + (" (in a line)" if line else "")
    case(code, label, shown, a * b, checks)


mul("T01", "2 × 1 digits, no regrouping", 23, 3, [("no carry", not any(carries(23, 3))),
                                                             ("2-digit answer", nd(69) == 2)])
mul("T02", "2 × 1 digits in a line", 32, 3, line=True)
case("T03", "The 1-digit number first", "3 × 21", 63, [("no carry", not any(carries(21, 3)))])
mul("T04", "Regroup from the ones, carry 1, 2-digit answer", 13, 4,
    [("carry 1", carries(13, 4) == [1]), ("2-digit answer", nd(52) == 2)])
mul("T05", "Regroup from the ones, carry more than 1, 2-digit answer", 19, 5,
    [("carry 4", carries(19, 5) == [4]), ("2-digit answer", nd(95) == 2)])
mul("T06", "No regrouping, but the answer grows to 3 digits", 42, 3,
    [("no carry", not any(carries(42, 3))), ("grows", grows(42, 3))])
mul("T07", "Regroup from the ones and the answer grows (the quiz's 56 × 3)", 56, 3,
    [("carry", carries(56, 3) == [1]), ("grows", grows(56, 3))])
mul("T08", "The carry takes the tens to ten (knock-on): a zero only in the answer", 18, 6,
    [("knock-on", knock_on(18, 6)), ("zero in answer", "0" in str(18 * 6))])
mul("T09", "Regroup and the ones write 0", 48, 5, [("ones write 0", (8 * 5) % 10 == 0), ("carry", carries(48, 5) == [4])])
mul("T10", "The largest carry: 99 × 9", 99, 9, [("carry 8", carries(99, 9) == [8])])
mul("T11", "3 × 1 digits, no regrouping", 213, 3, [("no carry", not any(carries(213, 3)))])
mul("T12", "3 × 1 digits with regrouping (every pattern in the next section)", 357, 4, [("carries", all(carries(357, 4)))])
case("T13", "3 × 1 digits, the 1-digit number first, in a line", "6 × 125 (in a line)", 750)
mul("T14", "3 × 1 digits in a line", 785, 4, line=True)
mul("T15", "4 × 1 digits, no regrouping", 2312, 3, [("no carry", not any(carries(2312, 3)))])
mul("T16", "4 × 1 digits with regrouping", 3476, 6, [("carries", sum(map(bool, carries(3476, 6))) >= 2)])
mul("T17", "2 × 2 digits, no regrouping anywhere, a 3-digit answer", 21, 13,
    [("3 digits", nd(21 * 13) == 3), ("rows regroup", not any(partial_regroups(21, 13))), ("sum carries", add_carries(*partials(21, 13)) == 0)])
mul("T18", "2 × 2 digits, one row regroups, a 3-digit answer", 16, 12,
    [("3 digits", nd(16 * 12) == 3), ("rows", partial_regroups(16, 12) == [True, False]), ("sum", add_carries(*partials(16, 12)) == 0)])
mul("T19", "2 × 2 digits, both rows regroup, a 3-digit answer", 36, 24,
    [("3 digits", nd(36 * 24) == 3), ("rows", partial_regroups(36, 24) == [True, True]), ("sum", add_carries(*partials(36, 24)) == 0)])
mul("T20", "2 × 2 digits, both rows regroup and adding the rows carries into a 4th digit", 47, 23,
    [("4 digits", nd(47 * 23) == 4), ("rows", all(partial_regroups(47, 23))), ("sum carries", add_carries(*partials(47, 23)) >= 1)])
mul("T21", "2 × 2 digits, a 4-digit answer with no carry in adding the rows", 52, 34,
    [("4 digits", nd(52 * 34) == 4), ("sum", add_carries(*partials(52, 34)) == 0)])
mul("T22", "2 × 2 digits in a line", 34, 26, line=True)
mul("T23", "3 × 2 digits", 234, 12)
mul("T24", "3 × 2 digits with regrouping in every row", 476, 38, [("rows", all(partial_regroups(476, 38)))])
mul("T25", "N × 1 digits (scales on)", 52341, 7)
mul("T26", "3 × 3 digits with a zero in the middle of the multiplier", 213, 102, [("2 rows", len(partials(213, 102)) == 2)])
# Every 2 × 2 digit question is one of T17 to T21, T27 and T28 (tests/test_mul_levels.py): the rows' regrouping, the
# carry in adding them and the answer's digits, crossed. The first draft left out the two below, the error table's own
# examples among them (19 × 14, 68 × 17), so no level could print them.
mul("T27", "2 × 2 digits, adding the rows carries, a 3-digit answer", 19, 14,
    [("3 digits", nd(19 * 14) == 3), ("sum carries", add_carries(*partials(19, 14)) >= 1)])
mul("T28", "2 × 2 digits, one row or none regroups and adding the rows carries into a 4th digit", 68, 17,
    [("4 digits", nd(68 * 17) == 4), ("rows", not all(partial_regroups(68, 17))),
     ("sum carries", add_carries(*partials(68, 17)) >= 1)])

# ---------------------------------------------------------------- 4. carries and zeros

section(4, "Multiplication carries and zeros",
        "The carry matrix for 3-digit × 1-digit (no zeros), then carry sizes, then every place a zero can sit.")
n = 0
for ones in (False, True):
    for tens in (False, True):
        for grow in (False, True):
            n += 1
            code = f"TC{n:02d}"
            pool = [(a, d) for a in NO_ZERO_3D for d in range(2, 10)
                    if bool(carries(a, d)[0]) == ones and bool(carries(a, d)[1]) == tens and grows(a, d) == grow]
            a, d = pick(code, pool)
            label = (f"Regroup from the ones: {'yes' if ones else 'no'} · from the tens: {'yes' if tens else 'no'} "
                     f"· answer grows to 4 digits: {'yes' if grow else 'no'}")
            mul(code, label, a, d)
mul("TC09", "A carry bigger than 1", 28, 7, [("carry 5", carries(28, 7) == [5])])
mul("TC10", "3 × 1 digits, a carry takes a column to ten (knock-on)", 125, 4, [("knock-on", knock_on(125, 4))])
mul("TC11", "Every column regroups, the answer full of zeros", 667, 3,
    [("all carry", all(carries(667, 3))), ("zeros", str(667 * 3).count("0") >= 2)])
mul("TZ01", "A zero at the end of the larger number", 230, 4)
mul("TZ02", "A zero in the middle, no carry reaches it", 302, 3, [("no carry into zero", not carry_into_zero(302, 3)),
                                                                   ("3-digit answer", nd(302 * 3) == 3)])
mul("TZ03", "A zero in the middle that a carry lands on", 506, 7, [("carry into zero", carry_into_zero(506, 7))])
mul("TZ04", "Two zeros in the larger number", 1008, 6)
mul("TZ05", "A zero only in the answer", 25, 4, [("no zero in numbers", "0" not in f"{25}{4}"), ("zero in answer", "0" in str(25 * 4))])
mul("TZ06", "The answer is a round number", 125, 8, [("round", 125 * 8 % 1000 == 0)])
mul("TZ07", "A 2-digit multiplier ending in zero: one row", 23, 40, [("one row", len(partials(23, 40)) == 1)])
mul("TZ08", "Both numbers end in zero", 120, 30)
# TZ02 is a zero in the middle whose answer stays 3 digits (Easy); the same with the answer grown is Medium's, as TC01
# and TC02 split the questions with no zero (measured 2026-10-09: 401 × 3 had no case once TZ02 kept to its size)
mul("TZ09", "A zero in the middle, no carry reaches it, the answer grows to 4 digits", 401, 3,
    [("no carry into zero", not carry_into_zero(401, 3)), ("4-digit answer", nd(401 * 3) == 4)])

# ---------------------------------------------------------------- 5. division facts and place value

section(5, "Division facts and place value", "The tables read backwards, then ÷10, ÷100 and multiples of ten.")


def div(code, label, a, b, checks=(), shown=None):
    case(code, label, shown or f"{a} ÷ {b}", qr(a, b) if a % b else a // b, checks, op="÷")


div("DF01", "÷1", 8, 1)
div("DF02", "A number divided by itself", 7, 7)
div("DF03", "Zero divided", 0, 5)
div("DF04", "The 2 table backwards", 14, 2)
div("DF05", "The 5 table backwards", 35, 5)
div("DF06", "The 10 table backwards", 60, 10)
div("DF07", "The 3 table backwards", 27, 3)
div("DF08", "The 4 table backwards", 32, 4)
div("DF09", "The 6 table backwards", 42, 6)
div("DF10", "The 7 table backwards", 56, 7)
div("DF11", "The 8 table backwards", 48, 8)
div("DF12", "The 9 table backwards", 81, 9)
div("DF13", "The 11 table backwards", 44, 11)
div("DF14", "The 12 table backwards (the Grade 4 paper's 144 ÷ 12)", 144, 12)
div("DF15", "How many groups: \"how many 6s make 42?\"", 42, 6, shown="How many 6s make 42?")
div("DF16", "A 2-digit divisor, 1-digit quotient", 84, 12)
div("DP01", "÷10", 450, 10)
div("DP02", "÷100", 4500, 100)
div("DP03", "÷1000", 7000, 1000)
div("DP04", "A multiple of ten ÷ 1 digit", 120, 4)
div("DP05", "A multiple of ten ÷ a multiple of ten", 800, 40)
div("DP06", "The fact uses one of the zeros (20 ÷ 4 = 5)", 200, 4, [("20 ÷ 4", 20 // 4 == 5)])
div("DP07", "A multiple of a hundred ÷ 1 digit", 3600, 6)

# ---------------------------------------------------------------- 6. division by digit shape

section(6, "Division by digit shape",
        "Short division read left to right: where a remainder is exchanged, whether the first digit is smaller than "
        "the divisor, and where the quotient has a zero.")
div("D01", "2 ÷ 1 digits, every digit divides, in the division layout", 84, 4, [("no exchange", not exchanges(84, 4))],
    shown="84 ÷ 4 (division layout)")
div("D02", "2 ÷ 1 digits, every digit divides, in a line", 69, 3, [("no exchange", not exchanges(69, 3))])
div("D03", "2 ÷ 1 digits, one exchange from the tens, by 2, 3, 4 or 5", 72, 4,
    [("exchange", exchanges(72, 4) == ["TENS"]), ("an easier table", 4 in (2, 3, 4, 5))])
div("D04", "2 ÷ 1 digits, one exchange from the tens, by 6, 7, 8 or 9", 91, 7,
    [("exchange", exchanges(91, 7) == ["TENS"]), ("a harder table", 7 in (6, 7, 8, 9))])
div("D05", "3 ÷ 1 digits, no exchange", 936, 3, [("no exchange", not exchanges(936, 3))])
n = 4
for fds, h_ex, t_ex in [(False, False, True), (False, True, False), (False, True, True), (True, True, False),
                        (True, True, True)]:
    n += 1
    code = f"D{n + 1:02d}"
    pool = [(a, d) for a in NO_ZERO_3D for d in range(2, 10)
            if a % d == 0 and first_smaller(a, d) == fds and qzero(a, d) == "NONE"
            and ("HUNDREDS" in exchanges(a, d)) == h_ex and ("TENS" in exchanges(a, d)) == t_ex]
    a, d = pick(code, pool)
    label = ("first digit smaller than the divisor, so the hundreds join the tens" if fds else
             f"exchange after the hundreds: {'yes' if h_ex else 'no'}") + f" · after the tens: {'yes' if t_ex else 'no'}"
    div(code, f"3 ÷ 1 digits: {label}", a, d)
div("D11", "4 ÷ 1 digits, no exchange", 4862, 2, [("no exchange", not exchanges(4862, 2))])
div("D12", "4 ÷ 1 digits, first digit smaller, exchanges", 5172, 6, [("smaller", first_smaller(5172, 6))])
div("D13", "3 ÷ 2 digits, 2-digit quotient", 408, 12)
div("D14", "3 ÷ 2 digits where the first estimate must be corrected", 162, 18,
    [("estimate from 20 is too small", 162 // 20 < 162 // 18)],
    shown="162 ÷ 18 (rounding 18 to 20 suggests 8; 8 × 18 = 144 leaves 18, so 9)")
div("DZ01", "A zero in the number divided gives a zero in the quotient", 804, 4,
    [("middle", qzero(804, 4) == "MIDDLE"), ("no exchange", not exchanges(804, 4))])
div("DZ02", "A zero at the end of the quotient", 840, 4, [("end", qzero(840, 4) == "END")])
div("DZ03", "A zero in the quotient from a digit smaller than the divisor", 618, 6,
    [("middle", qzero(618, 6) == "MIDDLE"), ("1 < 6", 1 < 6)])
div("DZ04", "A zero in the number divided, none in the quotient", 702, 6, [("no quotient zero", qzero(702, 6) == "NONE")])
div("DZ05", "Two zeros in the quotient", 8016, 8, [("two", str(8016 // 8).count("0") == 2)])
div("DZ06", "First digit smaller and a zero in the quotient", 3015, 5,
    [("smaller", first_smaller(3015, 5)), ("middle", qzero(3015, 5) == "MIDDLE")])
div("DZ07", "A zero at the end of the quotient from a last digit smaller than the divisor", 62, 3,
    [("end", qzero(62, 3) == "END"), ("2 < 3", digits(62)[-1] < 3)])

# ---------------------------------------------------------------- 7. remainders

section(7, "Remainders", "A remainder is its own answer: from a table fact up to 3 digits, smallest to largest.")
div("DR01", "A table fact with a remainder", 17, 5)
div("DR02", "The largest remainder (divisor − 1)", 47, 6, [("r = d − 1", 47 % 6 == 5)])
div("DR03", "The number divided is smaller than the divisor", 3, 5, [("quotient 0", 3 // 5 == 0)])
div("DR04", "2 ÷ 1 digits, no exchange, a remainder", 85, 4, [("no exchange", not exchanges(85, 4))])
div("DR05", "2 ÷ 1 digits, an exchange and a remainder", 75, 4, [("exchange", exchanges(75, 4) == ["TENS"])])
div("DR06", "3 ÷ 1 digits with a remainder", 457, 3)
div("DR07", "A remainder and a zero in the quotient", 613, 6, [("middle", qzero(613, 6) == "MIDDLE")])
div("DR08", "First digit smaller and a remainder", 157, 4, [("smaller", first_smaller(157, 4))])
case("DR09", "Checking a remainder: quotient × divisor + remainder", "21 × 4 + 1 = □ (is 85 ÷ 4 = 21 r 1?)",
     21 * 4 + 1, [("85", 21 * 4 + 1 == 85)], op="÷")
div("DR10", "÷10, 100 or 1000 with a remainder", 457, 10)

# ---------------------------------------------------------------- 8. methods

section(8, "Methods and pictures",
        "Every way the school's objectives name, and the standard ones, each worked through on its own example.")
a, d = 23, 4
case("G01", "Equal groups (a picture)", "3 groups of 4 dots: how many dots?", 12)
case("G02", "Repeated addition", "4 + 4 + 4 = 3 × □ = □", "4 and 12", [("sum", 4 + 4 + 4 == 3 * 4)])
case("G03", "Skip counting", "5, 10, 15, 20, □", 25)
case("G04", "Jumps on a number line", "4 jumps of 3 from 0 land on □", 12)
case("G05", "An array", "3 rows of 5 stars: □ × □ = □", "3 × 5 = 15 (5 × 3 = 15 is right too)")
case("G06", "Doubling (×2, ×4 = double double, ×8)", "14 × 4: double 14 = 28, double 28 = □", 56,
     [("×4", 14 * 4 == 56)])
case("G07", "Partitioning, in a line", f"{a} × {d} = 20 × {d} + 3 × {d} = {20 * d} + {3 * d} = □", a * d,
     [("parts", 20 * d + 3 * d == a * d)])
case("G08", "Grid (area) method, 2 × 1 digits", f"{a} × {d}: cells 20 × {d} = {20 * d} and 3 × {d} = {3 * d}", a * d)
cells = [30 * 20, 30 * 6, 4 * 20, 4 * 6]
case("G09", "Grid (area) method, 2 × 2 digits", f"34 × 26: cells {', '.join(map(str, cells))}", sum(cells),
     [("cells", sum(cells) == 34 * 26)])
case("G10", "Expanded columns: each product written in full", "34 × 6: 4 × 6 = 24, 30 × 6 = 180, 24 + 180 = □",
     34 * 6, [("rows", 24 + 180 == 204)])
case("G11", "Compact columns (the carry written small)", "34 × 6 in columns", 204)
p = partials(68, 17)
case("G12", "Long multiplication: a row per digit, the second row moved a place (the zero kept)",
     f"68 × 17: {p[0]} + {p[1]} = □", 68 * 17, [("rows", sum(p) == 68 * 17)])


def lattice(a, b):
    """Gelosia: each cell a product split into tens and ones; diagonals added from the bottom right."""
    da, db = digits(a), digits(b)
    sums = {}
    for i, x in enumerate(da):
        for j, y in enumerate(db):
            k = (len(da) - 1 - i) + (len(db) - 1 - j)
            sums[k] = sums.get(k, 0) + (x * y) % 10
            sums[k + 1] = sums.get(k + 1, 0) + (x * y) // 10
    return sum(v * 10**k for k, v in sums.items())


case("G13", "Lattice (gelosia) method", "47 × 23 in a 2 × 2 lattice: cells 08, 14 / 12, 21, added along the diagonals",
     lattice(47, 23), [("lattice = product", lattice(47, 23) == 47 * 23)])
case("G14", "Swap the order to use a known table", "9 × 2 = 2 × 9 = □", 18)
case("G15", "Equal sharing (a picture): how many each", "12 laddoos shared equally on 3 plates: how many on each?", 4,
     op="÷")
case("G16", "Equal grouping (a picture): how many groups", "12 laddoos, 4 on each plate: how many plates?", 3, op="÷")
case("G17", "Repeated subtraction", "15 − 3 − 3 − 3 − 3 − 3 = 0: how many 3s?", 5, [("15 ÷ 3", 15 // 3 == 5)], op="÷")
case("G18", "Jumps back on a number line", "From 20, jumps of 4 back to 0: how many jumps?", 5, op="÷")
case("G19", "An array, divided", "20 stars in 4 equal rows: how many in each row?", 5, op="÷")
case("G20", "The table backwards (inverse)", "42 ÷ 6 = □ because 6 × □ = 42", 7, op="÷")
case("G21", "Partitioning the number divided", "72 ÷ 4 = 40 ÷ 4 + 32 ÷ 4 = 10 + 8 = □", 18,
     [("parts", 40 // 4 + 32 // 4 == 72 // 4)], op="÷")


def chunks(n, d):
    out, left = [], n
    while left:
        k = 10 if left >= 10 * d else left // d
        out.append(k)
        left -= k * d
    return out


ch = chunks(96, 4)
case("G22", "Chunking: take away ten lots of the divisor, then the rest",
     "96 ÷ 4: " + ", ".join(f"take {k} × 4" for k in ch) + f" → {' + '.join(map(str, ch))} = □", sum(ch),
     [("chunks", sum(ch) == 96 // 4)], op="÷")
st = divide(72, 4)
case("G23", "Short division (bus stop): the exchange written small",
     f"72 ÷ 4: 7 ÷ 4 = {st[0]['q']} r {st[0]['r']}, exchange → {st[1]['value']} ÷ 4 = {st[1]['q']}", 18, op="÷")
st = divide(516, 4)
case("G24", "Long division: divide, multiply, take away, bring down",
     "516 ÷ 4: " + "; ".join(f"{s['value']} ÷ 4 = {s['q']}, {s['value']} − {s['q'] * 4} = {s['r']}"
                             + (f", bring down {x} → {s['r'] * 10 + x}" if x is not None else "")
                             for s, x in zip(st, digits(516)[1:] + [None], strict=True)), 516 // 4, op="÷")
case("G25", "Halving (÷2, ÷4 = halve twice)", "96 ÷ 4: halve 96 = 48, halve 48 = □", 24, op="÷")

# ---------------------------------------------------------------- 9. missing numbers and digits

section(9, "Missing numbers and missing digits",
        "Reverse reasoning. Every missing digit below has exactly one answer, checked by trying all ten.")
case("Q01", "A missing factor (the quiz's own)", "8 × □ = 72", 9)
case("Q02", "The first factor missing", "□ × 6 = 42", 7)
case("Q03", "The number divided missing", "□ ÷ 4 = 7", 28, op="÷")
case("Q04", "The divisor missing", "56 ÷ □ = 8", 7, op="÷")
case("Q05", "The box first", "□ = 63 ÷ 9", 7, op="÷")
case("Q06", "The same number in both boxes", "□ × □ = 49", 7, [("one answer", unique(lambda x: x * x == 49) == [7])])
case("Q07", "A missing digit in the larger number", "2□ × 4 = 92", 3,
     [("one answer", unique(lambda x: (20 + x) * 4 == 92) == [3])])
case("Q08", "A missing digit in the answer", "47 × 3 = 1□1", 4, [("one answer", unique(lambda x: 47 * 3 == 101 + 10 * x) == [4])])
case("Q09", "A missing digit in the number divided", "7□ ÷ 4 = 18", 2,
     [("one answer", unique(lambda x: (70 + x) == 18 * 4) == [2])], op="÷")
case("Q10", "A missing digit in the quotient", "936 ÷ 3 = 3□2", 1, [("one answer", unique(lambda x: 936 // 3 == 302 + 10 * x) == [1])],
     op="÷")
two = [(x, y) for x in range(1, 10) for y in range(10) if (10 * x + 7) * 6 == 302 + 10 * y]
case("Q11", "Two missing digits (Olympiad style)", "□7 × 6 = 3□2", "5 and 4", [("one answer", two == [(5, 4)])])
case("Q12", "The remainder missing", "38 ÷ 5 = 7 r □", 3, op="÷")
case("Q13", "The divisor missing, with a remainder", "38 ÷ □ = 7 r 3", 5,
     [("one answer", unique(lambda x: x > 3 and 38 // x == 7 and 38 % x == 3, range(1, 39)) == [5])], op="÷")
case("Q14", "The place-value factor missing", "45 × □ = 4500", 100)
case("Q15", "A missing row of a long multiplication", "34 × 26 = 204 + □", 680, [("rows", 204 + 680 == 34 * 26)])
case("Q16", "A missing digit in a 3-digit number", "3□4 × 2 = 708", 5,
     [("one answer", unique(lambda x: (304 + 10 * x) * 2 == 708) == [5])])

# ---------------------------------------------------------------- 10. equality, inverse, properties

section(10, "Equality, inverse and properties; multiples and factors",
        "What × and ÷ are, beyond working them out: the rules they keep, how they undo each other, and what a "
        "multiple and a factor are.")
case("Y01", "Order does not change a product", "6 × 8 = 8 × □", 6)
case("Y02", "Three numbers, grouped either way", "(2 × 7) × 5 = 2 × (7 × 5) = □", 70,
     [("assoc", (2 * 7) * 5 == 2 * (7 * 5) == 70)])
case("Y03", "Partitioning a factor (distributive)", "7 × 12 = 7 × 10 + 7 × □", 2)
case("Y04", "Anything × 0", "456 × 0", 0)
case("Y05", "× 1 and ÷ 1 leave a number unchanged", "37 × 1 and 37 ÷ 1", "37 and 37")
case("Y06", "A number ÷ itself, and 0 ÷ a number", "9 ÷ 9 and 0 ÷ 9", "1 and 0", op="÷")
case("Y07", "True or false: 9 ÷ 0 = 0", "9 ÷ 0 = 0", "false: there is no answer", op="÷")
case("Y08", "True or false: 12 ÷ 3 = 3 ÷ 12", "12 ÷ 3 = 3 ÷ 12", "false: division cannot be turned round", op="÷")
case("Y09", "A fact family", "4, 7, 28: write the four facts", "4 × 7 = 28, 7 × 4 = 28, 28 ÷ 4 = 7, 28 ÷ 7 = 4")
case("Y10", "Check a division by multiplying", "96 ÷ 4 = 24? 24 × 4 = □", 96, op="÷")
case("Y11", "Balance: × against −", "3 × 8 = 30 − □", 6, [("24", 30 - 6 == 24)])
case("Y12", "Balance: × against ÷", "6 × 4 = 48 ÷ □", 2, [("24", 48 // 2 == 24)])
case("Y13", "The missing sign", "6 □ 3 = 18 and 18 □ 3 = 6", "× and ÷")
case("Y14", "Compare without working", "25 × 4 ○ 25 × 5 and 48 ÷ 6 ○ 48 ÷ 8", "< and >")
case("Y15", "Double a factor, double the product", "12 × 5 = 60, so 12 × 10 = □", 120)
case("Y16", "True or false: 7 × 6 = 6 × 7", "7 × 6 = 6 × 7", "true")
case("F01", "Multiples of a number", "The multiples of 6 up to 60", ", ".join(str(6 * k) for k in range(1, 11)))
case("F02", "Is it a multiple?", "Is 45 a multiple of 5?", "yes")
case("F03", "All the factors of a number", "The factors of 12", ", ".join(str(k) for k in range(1, 13) if 12 % k == 0))
case("F04", "Factor pairs", "The factor pairs of 24",
     ", ".join(f"{k} × {24 // k}" for k in range(1, 5) if 24 % k == 0))
case("F05", "A common multiple", "Common multiples of 3 and 4 below 30",
     ", ".join(str(k) for k in range(1, 30) if k % 12 == 0))
case("F06", "Divisible by 2, 5 and 10, from the last digit", "Is 340 divisible by 2, 5 and 10?", "yes, all three",
     [("all", all(340 % k == 0 for k in (2, 5, 10)))])
case("F07", "Divisible by 3, from the sum of the digits", "Is 117 divisible by 3? (1 + 1 + 7 = 9)", "yes",
     [("117", 117 % 3 == 0)])
case("F08", "Even and odd products", "Is 6 × 7 even or odd?", "even")

# ---------------------------------------------------------------- 11. efficient and mental

section(11, "Efficient and mental strategies", "Ways round the written method, each worked on its own numbers.")
case("H01", "×5 as ×10 then halve", "46 × 5 = 460 ÷ 2 = □", 230, [("same", 46 * 5 == 460 // 2)])
case("H02", "×9 as ×10 take away one group", "23 × 9 = 230 − 23 = □", 207, [("same", 23 * 9 == 230 - 23)])
case("H03", "×11 as ×10 and one more group", "14 × 11 = 140 + 14 = □", 154)
case("H04", "Double one, halve the other", "16 × 5 = 8 × 10 = □; 35 × 4 = 70 × 2 = □", "80 and 140",
     [("same", 16 * 5 == 80 and 35 * 4 == 140)])
case("H05", "×8 as double three times", "13 × 8: 26, 52, □", 104)
case("H06", "×25 as ×100 ÷ 4", "24 × 25 = 2400 ÷ 4 = □", 600)
case("H07", "Near a round number (compensation)", "19 × 6 = 20 × 6 − 6 = □", 114)
case("H08", "A fact from a known fact", "7 × 8 = 56, so 7 × 9 = 56 + 7 = □", 63)
case("H09", "÷5 as ÷10 then double", "240 ÷ 5 = 24 × 2 = □", 48, op="÷")
case("H10", "A fact scaled by ten", "6 × 7 = 42, so 60 × 7 = □ and 600 × 7 = □", "420 and 4200")

# ---------------------------------------------------------------- 12. estimating and judging

section(12, "Estimating and judging an answer", "Is it about right, and can it be right at all?")
case("V01", "Round the larger number to the ten, then multiply", "48 × 6 ≈ 50 × 6 = □ (exact 288)", 300)
case("V02", "Round both numbers", "38 × 21 ≈ 40 × 20 = □ (exact 798)", 800, [("exact", 38 * 21 == 798)])
case("V03", "How many digits will the product have?", "67 × 75 and 31 × 22", "4 and 3",
     [("digits", nd(67 * 75) == 4 and nd(31 * 22) == 3)])
case("V04", "How many digits will the quotient have?", "156 ÷ 4 and 456 ÷ 4", "2 and 3",
     [("digits", nd(156 // 4) == 2 and nd(456 // 4) == 3)], op="÷")
case("V05", "Is this answer possible?", "23 × 4 = 812", "no: 23 × 4 is less than 25 × 4 = 100")
case("V06", "Odd or even, without working", "7 × 9 and 6 × 13", "odd and even")
case("V07", "The last digit, without working", "47 × 3 ends in □", 1, [("ends", 47 * 3 % 10 == 1)])
case("V08", "The closest estimate", "52 × 9 is closest to 400, 450 or 500?", 450,
     [("closest", min((400, 450, 500), key=lambda x: abs(x - 52 * 9)) == 450)])
case("V09", "A remainder bigger than the divisor is wrong", "47 ÷ 6 = 6 r 11: possible?", "no: 11 is more than 6",
     op="÷")
case("V10", "Estimate a quotient", "412 ÷ 8 ≈ 400 ÷ 8 = □ (exact 51 r 4)", 50, [("exact", qr(412, 8) == "51 r 4")], op="÷")

# ---------------------------------------------------------------- 13. word problems

section(13, "Word problems",
        "One-step structures first (the same numbers are harder in some), then remainders in a story, two steps, "
        "and the language that misleads.")
case("B01", "Equal groups, how many in all", "4 plates with 6 laddoos on each. How many laddoos in all?", 24)
case("B02", "Sharing: how many in each group", "24 laddoos shared equally on 4 plates. How many on each plate?", 6,
     op="÷")
case("B03", "Grouping: how many groups", "24 laddoos, 6 on each plate. How many plates?", 4, op="÷")
case("B04", "An array: how many in all", "5 rows of 7 chairs. How many chairs?", 35)
case("B05", "An array: how many in a row", "35 chairs in 5 equal rows. How many in each row?", 7, op="÷")
case("B06", "Price: the cost of many", "One pencil costs ₹6. What do 8 pencils cost?", "₹48")
case("B07", "Price: the cost of one", "8 pencils cost ₹48. What does one cost?", "₹6", op="÷")
case("B08", "Times as many: the larger", "Riya has 4 stickers. Dev has 3 times as many. How many has Dev?", 12)
case("B09", "Times as many: the smaller", "Dev has 12 stickers, 3 times as many as Riya. How many has Riya?", 4, op="÷")
case("B10", "Times as many: how many times", "Dev has 12 stickers and Riya has 4. How many times as many stickers as Riya does Dev have?", 3,
     op="÷")
case("B11", "Twice as many", "Aman read 15 pages. Meera read twice as many. How many did Meera read?", 30)
case("B12", "Combinations", "3 shirts and 4 shorts. How many different outfits?", 12)
case("B13", "Area in squares", "A rectangle 6 squares long and 4 squares wide. How many squares?", 24)
case("B14", "A remainder dropped (full boxes)", "26 laddoos, 4 in each box. How many full boxes?", 6,
     [("26 ÷ 4", 26 // 4 == 6)], op="÷")
case("B15", "A remainder rounded up", "26 children, 4 in each rickshaw. How many rickshaws are needed?", 7,
     [("round up", -(-26 // 4) == 7)], op="÷")
case("B16", "The remainder is the answer", "26 laddoos, 4 in each box. How many are left over?", 2, op="÷")
case("B17", "Both asked", "26 laddoos into boxes of 4: how many boxes, how many left?", "6 boxes, 2 left", op="÷")
case("B18", "Two steps: ×, then +", "3 boxes of 12 pencils and 5 loose pencils. How many pencils?", 41,
     [("41", 3 * 12 + 5 == 41)])
case("B19", "Two steps: ×, then −", "Sara has ₹100 and buys 4 pens at ₹15 each. How much is left?", "₹40",
     [("40", 100 - 4 * 15 == 40)])
case("B20", "Two steps: ÷, then ×", "12 pencils cost ₹36. What do 5 pencils cost?", "₹15", [("15", 36 // 12 * 5 == 15)])
case("B21", "Two steps: two products added", "4 packets of 6 and 3 packets of 8. How many in all?", 48,
     [("48", 4 * 6 + 3 * 8 == 48)])
case("B22", "Two steps: +, then ÷", "18 red and 14 blue balloons shared equally by 4 children. How many each?", 8,
     [("8", (18 + 14) // 4 == 8 and (18 + 14) % 4 == 0)], op="÷")
case("B23", "A bar model: one part is times another", "Ria and Sam have 32 marbles. Sam has 3 times as many as Ria. "
     "How many has Ria?", 8, [("8", 32 // (3 + 1) == 8)], op="÷")
case("B24", "\"Each\" that means ÷", "30 stickers, 5 for each child. How many children?", 6, op="÷")
case("B25", "A number the question does not need", "A van carries 8 boxes of 9 mangoes and 3 drivers. How many "
     "mangoes?", 72)
case("B26", "Read from a price list", "Price list: pen ₹15, eraser ₹5. What do 3 pens cost?", "₹45")
case("B27", "Half as many", "Meera read 30 pages. Aman read half as many. How many did Aman read?", 15, op="÷")

# ---------------------------------------------------------------- 14. error diagnosis


def E(code, a, b):
    """An existing mistake's wrong answer, from the engine's own predictor (assess/misconceptions.py)."""
    return M.predict("×", a, b).get(code)


def concat(a, d):
    return int("".join(str(x * d) for x in digits(a)))


def no_carry(a, d):
    return int("".join(str(x * d % 10) for x in digits(a)))


def carry_first(a, d):
    out, carry = [], 0
    for x in reversed(digits(a)):
        v = (x + carry) * d
        out.append(v % 10)
        carry = v // 10
    return int(str(carry or "") + "".join(map(str, reversed(out))))


def carry_onto_zero_lost(a, d):
    """Worked apart from the engine (assess/mul_mistakes.py): the right product less every carry that lands on a zero
    digit, in that column's own place — the carry is all that column would have written, and it sends nothing on."""
    carry, lost = 0, 0
    for i, x in enumerate(reversed(str(a))):
        if x == "0" and carry:
            lost, carry = lost + carry * 10**i, 0
        else:
            carry = (int(x) * d + carry) // 10
    return a * d - lost


def placeholder(a, b):
    return sum(a * x for x in digits(b))


def columnwise(a, b):
    return int("".join(str(x * y) for x, y in zip(digits(a), digits(b), strict=True)))


def stale_carry(a, b):
    """Worked apart from the engine: the long multiplication written out, the first row's carries left above the
    columns they went into and added again in the second row's same columns."""
    top = [int(c) for c in reversed(str(a))]

    def row(d, above):
        out, carry, sent = 0, 0, {}
        for i, x in enumerate(top):
            v = x * d + carry + above.get(i, 0)
            out, carry = out + (v % 10) * 10**i, v // 10
            if carry and i + 1 < len(top):
                sent[i + 1] = carry
        return out + carry * 10 ** len(top), sent

    first, written = row(b % 10, {})
    second, _ = row(b // 10, written)
    return first + second * 10


def grid_cell_dropped(a, b):
    """A grid added without its ones-by-ones cell."""
    return a * b - (a % 10) * (b % 10)


def tens_zero_extra(n, d):
    """÷ by a 1-digit number: the fact borrows one of the zeros, then every zero is written back."""
    k = len(str(n)) - len(str(n).rstrip("0"))
    core = n // 10**k
    return (core * 10 // d if core < d else core // d) * 10**k


def drop_qzero(n, d):
    return int(str(n // d).replace("0", ""))


def digitwise(n, d):
    return int("".join(str(x // d) for x in digits(n)).lstrip("0") or "0")


def remainder_added(n, d):
    """The remainder is added to the next digit instead of becoming tens of it."""
    q, r = "", 0
    for x in digits(n):
        v = r + x
        q, r = q + str(v // d), v % d
    return f"{int(q)} r {r}"


def lead_dropped(n, d):
    return int(str(n)[1:]) // d


def bring_down_missed(n, d):
    return qr(n // 10, d)


def too_big(n, d):
    return f"{n // d - 1} r {n % d + d}"


def bigger_by_smaller(n, d):
    return qr(max(n, d), min(n, d))


MISTAKES = []


def mistake(code, op, what, example, right, wrong, seen="answer", charges="the skill"):
    """One named mistake: its wrong answer is the value a predictor computed from the example's own numbers."""
    if wrong is None or str(wrong) == str(right):
        FAULTS.append(f"{code}: its wrong answer for {example} is {wrong}, not a wrong answer")
    MISTAKES.append((code, op, what, example, right, wrong, seen, charges))


# every × mistake the engine predicts (assess/mul_mistakes.py), computed here a second way and held to the engine's
for name, mine, a, b in [("M_MUL_NO_CARRY", no_carry, 34, 6), ("M_MUL_CONCAT", concat, 56, 3),
                         ("M_MUL_CARRY_FIRST", carry_first, 34, 6),
                         ("M_MUL_CARRY_ONTO_ZERO_LOST", carry_onto_zero_lost, 506, 7),
                         ("M_MUL_PLACEHOLDER", placeholder, 68, 17), ("M_MUL_COLUMNWISE", columnwise, 68, 17),
                         ("M_MUL_STALE_CARRY", stale_carry, 47, 23), ("M_MUL_ONE_ROW", lambda a, b: a * (b % 10), 68, 17),
                         ("M_TENS_ZERO_DROPPED", lambda a, b: a * b // 10, 45, 100),
                         ("M_ZERO_AS_ONE", lambda a, b: a, 7, 0), ("M_ONE_ADDED", lambda a, b: a + 1, 7, 1)]:
    if mine(a, b) != E(name, a, b):
        FAULTS.append(f"{name}: this file computes {mine(a, b)} for {a} × {b}, the engine {E(name, a, b)}")

mistake("M_MUL_NO_CARRY", "×", "Writes each column's product without its carry", "34 × 6", 34 * 6,
        E("M_MUL_NO_CARRY", 34, 6))
mistake("M_MUL_CONCAT", "×", "Writes each digit's product side by side (Aseem's 56 × 3)", "56 × 3", 56 * 3,
        E("M_MUL_CONCAT", 56, 3))
mistake("M_MUL_CARRY_FIRST", "×", "Adds the carry before multiplying", "34 × 6", 34 * 6, E("M_MUL_CARRY_FIRST", 34, 6))
mistake("M_MUL_ONES_ONLY", "×", "Multiplies only the ones", "34 × 6", 34 * 6, E("M_MUL_ONES_ONLY", 34, 6))
mistake("M_MUL_UNITS_REVERSED", "×", "Writes only each product's units digit, ones first", "56 × 3", 56 * 3,
        E("M_MUL_UNITS_REVERSED", 56, 3))
mistake("M_MUL_ROW_OUT", "×", "Answers the row next to it in the table (one group fewer)", "7 × 8", 7 * 8,
        E("M_MUL_ROW_OUT", 7, 8), charges="the facts")
mistake("M_GROUP_MISSED", "×", "Adds one group fewer than there are", "3 groups of 4", 3 * 4, (3 - 1) * 4)
mistake("M_ONE_GROUP", "×", "Writes how many are in one group", "3 groups of 4", 3 * 4, 4)
mistake("M_WRONG_OP", "×", "Adds the numbers", "34 × 6", 34 * 6, E("M_WRONG_OP", 34, 6))
mistake("M_ZERO_AS_ONE", "×", "Treats × 0 as leaving the number", "7 × 0", 7 * 0, E("M_ZERO_AS_ONE", 7, 0),
        charges="the facts")
mistake("M_ONE_ADDED", "×", "Treats × 1 as adding one", "7 × 1", 7 * 1, E("M_ONE_ADDED", 7, 1), charges="the facts")
mistake("M_TENS_ZERO_DROPPED", "×", "Writes one zero fewer when multiplying by 10, 100 or a multiple of ten",
        "45 × 100", 45 * 100, E("M_TENS_ZERO_DROPPED", 45, 100))
mistake("M_PARTITION_TENS_AS_ONES (new)", "×", "Partitions but multiplies the tens digit as ones", "23 × 4", 23 * 4,
        sum(x * 4 for x in digits(23)))
mistake("M_MUL_CARRY_ONTO_ZERO_LOST", "×", "Forgets a carry that lands on a zero", "506 × 7", 506 * 7,
        E("M_MUL_CARRY_ONTO_ZERO_LOST", 506, 7))
mistake("M_MUL_PLACEHOLDER", "×", "Second row not moved a place (the zero left out)", "68 × 17", 68 * 17,
        E("M_MUL_PLACEHOLDER", 68, 17))
mistake("M_MUL_COLUMNWISE", "×", "Multiplies tens by tens and ones by ones", "68 × 17", 68 * 17,
        E("M_MUL_COLUMNWISE", 68, 17))
mistake("M_MUL_ONE_ROW", "×", "Multiplies by the ones of the multiplier only", "68 × 17", 68 * 17,
        E("M_MUL_ONE_ROW", 68, 17))
mistake("M_MUL_STALE_CARRY", "×", "Adds the first row's carry again in the second row", "47 × 23", 47 * 23,
        E("M_MUL_STALE_CARRY", 47, 23))
mistake("M_NOCARRY on the rows (existing, addition)", "×", "Adds the two rows without carrying", "19 × 14", 19 * 14,
        M.predict("+", *partials(19, 14)).get("M_NOCARRY"), charges="addition")
mistake("M_GRID_CELL_DROPPED (new)", "×", "Leaves the ones-by-ones cell out when adding a grid", "34 × 26", 34 * 26,
        grid_cell_dropped(34, 26), seen="working")
mistake("M_DIV_QUOTIENT_ZERO_DROPPED (new)", "÷", "Leaves the zero out of the quotient", "804 ÷ 4", 804 // 4,
        drop_qzero(804, 4))
mistake("M_DIV_EXCHANGE_LOST (new)", "÷", "Divides each digit alone; the remainder is never exchanged", "72 ÷ 4",
        72 // 4, digitwise(72, 4))
mistake("M_DIV_REMAINDER_ADDED (new)", "÷", "Adds the remainder to the next digit instead of making it tens",
        "72 ÷ 4", 72 // 4, remainder_added(72, 4))
mistake("M_DIV_LEAD_DROPPED (new)", "÷", "Skips a first digit smaller than the divisor", "156 ÷ 4", 156 // 4,
        lead_dropped(156, 4))
mistake("M_DIV_BRING_DOWN_MISSED (new)", "÷", "Stops before bringing down the last digit", "516 ÷ 4", 516 // 4,
        bring_down_missed(516, 4))
mistake("M_DIV_REMAINDER_TOO_BIG (new)", "÷", "Stops one group short: the remainder is not less than the divisor",
        "85 ÷ 4", qr(85, 4), too_big(85, 4))
mistake("M_DIV_REMAINDER_AS_DIGIT (new)", "÷", "Writes the remainder as the quotient's next digit", "85 ÷ 4", qr(85, 4),
        f"{85 // 4}{85 % 4}")
mistake("M_DIV_SWAPPED (new)", "÷", "Writes the quotient and the remainder the wrong way round", "17 ÷ 5", qr(17, 5),
        f"{17 % 5} r {17 // 5}")
mistake("M_DIV_BIGGER_BY_SMALLER (new)", "÷", "Divides the bigger number by the smaller whichever comes first",
        "3 ÷ 5", qr(3, 5), bigger_by_smaller(3, 5))
mistake("M_DIV_SELF_AS_ZERO (new)", "÷", "Treats a number ÷ itself as nothing left", "7 ÷ 7", 7 // 7, 7 - 7,
        charges="the facts")
mistake("M_DIV_ZERO_DIVIDED (new)", "÷", "Answers the divisor when zero is divided", "0 ÷ 5", 0 // 5, 5,
        charges="the facts")
mistake("M_DIV_TENS_ZERO_LEFT (new)", "÷", "Takes away one zero fewer when dividing by 10 or 100", "4500 ÷ 100",
        4500 // 100, 4500 // 100 * 10)
mistake("M_DIV_TENS_ZERO_EXTRA (new)", "÷", "Uses a zero for the fact, then writes every zero back", "200 ÷ 4",
        200 // 4, tens_zero_extra(200, 4))
mistake("M_WRONG_OP (÷)", "÷", "Multiplies instead of dividing", "84 ÷ 4", 84 // 4, 84 * 4)
mistake("M_DIV_SUBTRACTED (new)", "÷", "Takes the divisor away once", "84 ÷ 4", 84 // 4, 84 - 4)
mistake("M_REMAINDER_NOT_ROUNDED_UP (new)", "÷", "Drops the remainder when the story needs one more",
        "26 children, 4 to a rickshaw", -(-26 // 4), 26 // 4, charges="word problems")
mistake("M_TIMES_AS_MORE (new)", "×", "Reads \"3 times as many\" as \"3 more\"", "4 stickers, 3 times as many",
        4 * 3, 4 + 3, charges="word problems")
mistake("M_KEYWORD_OVERGENERALISED (existing)", "÷", "Multiplies because the story says \"each\"",
        "24 laddoos shared on 4 plates", 24 // 4, 24 * 4, charges="word problems")


section(14, "Error diagnosis",
        "Every wrong answer below is computed by a predictor from its example's own numbers. A blank box is the blank "
        "signal, never a named mistake (rule 5). Then the find-the-mistake cases that ask the child to spot one.")
case("C01", "Find the mistake: products side by side", f"56 × 3 = {concat(56, 3)}", "M_MUL_CONCAT")
case("C02", "Find the mistake: carries left out", f"34 × 6 = {no_carry(34, 6)}", "M_MUL_NO_CARRY")
case("C03", "Find the mistake: the second row not moved", f"68 × 17 = {placeholder(68, 17)}", "M_MUL_PLACEHOLDER")
case("C04", "Find the mistake: the zero left out of the quotient", f"612 ÷ 6 = {drop_qzero(612, 6)}",
     "M_DIV_QUOTIENT_ZERO_DROPPED", op="÷")
case("C05", "Find the mistake: a remainder too big", "85 ÷ 4 = 20 r 5", "M_DIV_REMAINDER_TOO_BIG", op="÷")
case("C06", "Find the mistake: partitioning, tens taken as ones", "23 × 4 = 2 × 4 + 3 × 4 = 20",
     "M_PARTITION_TENS_AS_ONES")
case("C07", "Say which step of a long division went wrong", f"516 ÷ 4 = {bring_down_missed(516, 4)}",
     "M_DIV_BRING_DOWN_MISSED: the 6 was never brought down", op="÷")
case("C08", "Explain, by multiplying back, why an answer cannot be right", "804 ÷ 4 = 21", "21 × 4 = 84, not 804",
     [("84", 21 * 4 == 84)], op="÷")
case("C09", "Find the mistake: the carry onto the zero left out", f"506 × 7 = {506 * 7 - 40}",
     "M_MUL_CARRY_ONTO_ZERO_LOST: the tens are 0 × 7 + 4 = 4", [("one carry lost", carry_onto_zero_lost(506, 7) == 3502)])

# ---------------------------------------------------------------- 16. the skills the cases become

SKILLS = [
    # code, outcome sentence, grades E/M/H/A, {level: cases}, methods at the straight levels
    ("MUL.GROUPS", "Finds how many in equal groups by adding the same number again (exists, unchanged)",
     "G1 G1 – G1", {"Easy": ["G01", "G02"], "Medium": ["G01", "G02"], "Advance": ["B01"]}, []),
    ("MUL.MODELS", "Shows multiplication as skip counting, arrays, jumps on a number line and the multiplication square",
     "G2 G2 G2 G2", {"Easy": ["G03", "G05"], "Medium": ["G04"], "Hard": ["G14", "TF17"],
                     "Advance": ["B04", "B11", "B13"]}, []),
    ("MUL.FACTS", "Recalls multiplication facts to 10 × 10, then ×11 and ×12, in either order",
     "G2 G2 G2 G3", {"Easy": ["TF03", "TF04", "TF05"], "Medium": ["TF01", "TF02", "TF06", "TF07", "TF15"],
                     "Hard": ["TF08", "TF09", "TF10", "TF11", "TF12", "TF16"],
                     "Advance": ["TF13", "TF14", "Q01", "Q02", "Q06", "Y09", "H08"]}, []),
    ("MUL.TENS", "Multiplies by 10, 100 and 1000 and by multiples of ten, placing the zeros",
     "G3 G3 G4 G4", {"Easy": ["TP01", "TP04"], "Medium": ["TP02", "TP03", "TP05", "TP11"],
                     "Hard": ["TP06", "TP07", "TP08", "TP09"],
                     "Advance": ["TP10", "Q14", "H10", "TZ08", "TZ01", "TZ07"]}, []),
    ("MUL.2D1D", "Multiplies a 2-digit number by a 1-digit number, regrouping when a column makes ten or more",
     "G2 G2 G3 G3", {"Easy": ["T01", "T03"], "Medium": ["T04", "T05", "T06"],
                     "Hard": ["T07", "T08", "T09", "T10", "TC09", "TZ05"],
                     "Advance": ["Q07", "Q08", "Q11", "C01", "C02", "C06", "V01", "V07", "B06", "B08", "H01", "H07"]},
     ["T02", "G07", "G08", "G10", "G11"]),
    ("MUL.3D1D", "Multiplies a 3-digit number by a 1-digit number, regrouping in any column and onto a zero",
     "G4 G4 G4 G4", {"Easy": ["T11", "TC01", "TZ02"], "Medium": ["TC02", "TC03", "TC05", "TZ09"],
                     "Hard": ["T12", "TC04", "TC06", "TC07", "TC08", "TC10", "TC11", "TZ03", "TZ06"],
                     "Advance": ["Q16", "C09"]}, ["T13", "T14", "G10", "G11"]),
    ("MUL.2D2D", "Multiplies two 2-digit numbers, a row for each digit with the second row moved a place",
     "G4 G4 G4 G4", {"Easy": ["T17"], "Medium": ["T18"], "Hard": ["T19", "T20", "T21", "T27", "T28"],
                     "Advance": ["C03", "V02", "V03", "Q15", "B12"]}, ["T22", "G09", "G12", "G13"]),
    ("DIV.GROUPS", "Divides by sharing equally and by making equal groups, with pictures, arrays and jumps back",
     "G2 G2 G2 G2", {"Easy": ["G15", "G16"], "Medium": ["G17", "G19"], "Hard": ["G18"],
                     "Advance": ["B02", "B03", "B05", "B24"]}, []),
    ("DIV.FACTS", "Recalls division facts as the tables backwards, with a remainder when one is left",
     "G2 G2 G2 G3", {"Easy": ["DF04", "DF05", "DF06"], "Medium": ["DF01", "DF02", "DF03", "DF07", "DF08", "DF15"],
                     "Hard": ["DF09", "DF10", "DF11", "DF12"],
                     "Advance": ["DF13", "DF14", "DF16", "DR01", "DR02", "DR03", "Q03", "Q04", "Q05", "G20", "B07"]},
     []),
    ("DIV.TENS", "Divides by 10, 100 and 1000 and by multiples of ten", "G4 G4 G4 G4",
     {"Easy": ["DP01"], "Medium": ["DP02", "DP03"], "Hard": ["DP04", "DP05", "DP06", "DP07"],
      "Advance": ["DR10"]}, []),
    ("DIV.2D1D", "Divides a 2-digit number by a 1-digit number, exchanging a remainder into the next digit",
     "G2 G2 G3 G3", {"Easy": ["D01", "D02"], "Medium": ["D03", "D04"], "Hard": ["DR04", "DR05", "DZ07"],
                     "Advance": ["Q09", "Q12", "Q13", "C05", "V09", "B14", "B15", "B16", "B17", "Y10"]},
     ["D02", "G21", "G22", "G23", "G25"]),
    ("DIV.3D1D", "Divides a 3-digit number by a 1-digit number, with zeros and remainders in the quotient",
     "G4 G4 G4 G4", {"Easy": ["D05"], "Medium": ["D06", "D07"],
                     "Hard": ["D08", "D09", "D10", "DZ01", "DZ02", "DZ03", "DZ04", "DR06", "DR07", "DR08"],
                     "Advance": ["Q10", "C04", "C07", "V04", "V10", "H09"]}, ["G22", "G23", "G24"]),
    ("MD.WORD", "Solves one- and two-step stories with × and ÷, choosing the operation and using a remainder as the "
     "story needs", "G2 G2 G3 G4", {"Easy": ["B01", "B02", "B03", "B06"], "Medium": ["B04", "B05", "B07", "B11", "B27"],
                                    "Hard": ["B08", "B09", "B10", "B14", "B15", "B16", "B17"],
                                    "Advance": ["B12", "B13", "B18", "B19", "B20", "B21", "B22", "B23", "B25", "B26"]},
     []),
    ("MD.MENTAL", "Multiplies and divides in the head by doubling, halving, tens and known facts",
     "G2 G3 G3 G4", {"Easy": ["G06", "H10"], "Medium": ["H01", "H04", "H08"],
                     "Hard": ["H02", "H03", "H05", "H07", "H09", "G25"], "Advance": ["H06"]}, []),
    ("MD.MULTIPLES", "Finds multiples and factors and tells divisibility by 2, 3, 5 and 10",
     "G3 G3 G4 G4", {"Easy": ["F01", "F02", "F06"], "Medium": ["F03", "F04", "F08"], "Hard": ["F05"],
                     "Advance": ["F07"]}, []),
    ("MD.EQUALITY", "Uses × and ÷ as inverses, keeps a balance true and knows the rules of 0 and 1",
     "G3 G3 G4 G4", {"Easy": ["Y01", "Y04", "Y05", "Y06", "Y16"], "Medium": ["Y02", "Y09", "Y10", "Y15"],
                     "Hard": ["Y03", "Y11", "Y12", "Y13", "Y14"], "Advance": ["Y07", "Y08", "DR09", "C08"]}, []),
    ("MD.ESTIMATE", "Estimates products and quotients and judges whether an answer can be right", "G4 G4 G4 G4",
     {"Easy": ["V06", "V07"], "Medium": ["V01", "V03", "V04"], "Hard": ["V02", "V08", "V10"],
      "Advance": ["V05", "V09"]}, []),
]
UNPLACED = ["T15", "T16", "T23", "T24", "T25", "T26", "D11", "D12", "D13", "D14", "DZ05", "DZ06", "TZ04"]

codes = {c["code"] for c in CASES}
placed = set()
for code, _lo, _g, levels, methods in SKILLS:
    for lv, cs in levels.items():
        missing = [c for c in cs if c not in codes]
        if missing:
            FAULTS.append(f"{code} {lv} names cases that do not exist: {missing}")
        placed |= set(cs)
    placed |= set(methods)
for c in sorted(codes - placed - set(UNPLACED)):
    FAULTS.append(f"{c}: placed in no level and not listed as unplaced")
for c in UNPLACED:
    if c in placed:
        FAULTS.append(f"{c}: listed as unplaced but placed")

# ---------------------------------------------------------------- 15. tags

MATRIX = []  # the master tagging matrix, read from the dimension rows once the cases are rows (see __main__)


def matrix(made):
    """Every tag a multiplication or division case reads, as its `case_dimension` row says it."""
    dims = json.loads((R / "supabase/seed/case_dimensions.json").read_text())["case_dimensions"]
    read = {k for r in made for k in r["match"] if k != "fmt"}
    return [(d["name"], _values(d["allowed"]), d.get("why", "")) for d in dims if d["name"] in read]


def _values(allowed):
    """A dimension's values as a reader takes them in: places joined (ONES+TENS) said once, not as every combination."""
    places = [v for v in allowed if "+" not in str(v) and v != "NONE"]
    if len(places) >= 4 and len(allowed) == 2 ** len(places):  # NONE and every combination of four or more places
        return "NONE, or any of " + " / ".join(map(str, places)) + ", joined from the ones up"
    return " / ".join(map(str, allowed))

# ---------------------------------------------------------------- the document


def cell(s):
    return str(s).replace("|", "\\|")


def table(head, rows):
    out = ["| " + " | ".join(head) + " |", "| " + " | ".join("---" for _ in head) + " |"]
    out += ["| " + " | ".join(cell(x) for x in r) + " |" for r in rows]
    return "\n".join(out)


def body(num):
    """One section's markdown (its ## heading and body), as the doc and the file both print it."""
    if num == 0:
        rows = [(f"A{i}", a, b, c) for i, (a, b, c) in enumerate(ASSUMPTIONS, 1)]
        return ("## Assumptions\n\nTwelve decisions the engine took so the build need not wait. Each is a row or a "
                "case to change, not code.\n\n" + table(["#", "Assumed", "What it means", "Why"], rows))
    if num == 1:
        return ("## How to read this\n\nA case is distinct when a child can make a different mistake on it. A "
                "question carries several tags at once; its case is the combination.\n\n"
                + table(["Dimension", "Typical values", "Why it matters"], DIMENSIONS))
    if num == 15:
        return ("## Master tagging matrix\n\nEvery tag a multiplication or division case reads, as its "
                "`case_dimension` row says it. Code measures each from the question's numbers, or reads what the kind "
                "that made it states (the method it prints, a story's shape, what a remainder is for); none is typed "
                "by a person.\n\n" + table(["Tag", "Allowed values", "Why it matters"], MATRIX))
    if num == 16:
        rows = []
        for code, lo, grades, levels, methods in SKILLS:
            g = grades.split()
            rows.append((code, lo, " ".join(f"{lv[0]}:{gr}" for lv, gr in zip(["Easy", "Medium", "Hard", "Advance"],
                                                                               g, strict=True) if gr != "–"),
                         *(", ".join(levels.get(lv, [])) or "–" for lv in ("Easy", "Medium", "Hard", "Advance")),
                         ", ".join(methods) or "–"))
        n_cases = len(CASES)
        return (f"## Suggested progression and the skills it becomes\n\n{len(SKILLS)} skills, every one of the "
                f"{n_cases} cases placed in a level or listed as unplaced. Easy to Hard are straight calculation; "
                "Advance mixes the hardest straight cases with missing numbers, stories, finding the mistake and "
                "estimating. A question has one home: every round-number multiplication that is not a table "
                "fact is MUL.TENS's, so a 3-digit number ending in zero (TZ01) and a multiplier ending in zero "
                "(TZ07) sit at its Advance with TP10, which holds the same questions. Grades are assumed "
                "(A6) and move as rows.\n\n"
                + table(["Skill", "Can do", "Grade by level", "Easy", "Medium", "Hard", "Advance",
                         "Methods printed at Easy to Hard"], rows)
                + f"\n\nUnplaced until a grade claims them: {', '.join(UNPLACED)}.")
    s = next(x for x in SECTIONS if x["num"] == num)
    rows = [(c["code"], c["label"], c["example"], c["answer"]) for c in CASES if c["section"] == num]
    out = f"## {s['title']}\n\n{s['lead']}\n\n" + table(["ID", "Case", "Example", "Answer"], rows)
    if num == 14:
        out = (f"## {s['title']}\n\n{s['lead']}\n\n"
               + table(["Mistake", "Op", "What the child does", "Example", "Right", "Wrong (computed)", "Seen in",
                        "Counts against"], [(m[0], m[1], m[2], m[3], m[4], m[5], m[6], m[7]) for m in MISTAKES])
               + "\n\n" + table(["ID", "Case", "Example", "Answer"], rows))
    return out


ORDERED = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
TITLE = "# Multiplication & Division Assessment Skill Taxonomy"
LEAD = ("Engine draft v0.1, 2026-10-09, for Achal to correct. It follows the Addition & Subtraction taxonomy's rule: "
        "a case is distinct whenever a child can make a different kind of mistake. Every example was computed and "
        "checked by `research/md_taxonomy.py`, not typed.")

if __name__ == "__main__":
    if FAULTS:
        print("\n".join(FAULTS))
        sys.exit(f"{len(FAULTS)} faults")
    import md_rows  # the cases as rows, each measured by the engine (goals/md1-taxonomy-rows.yaml)

    made = md_rows.rows(CASES, SECTIONS)
    if bad := md_rows.faults(made):
        print("\n".join(bad))
        sys.exit(f"{len(bad)} faults")
    print(f"{len(CASES)} cases in {len(SECTIONS)} sections, {len(MISTAKES)} mistakes, {len(SKILLS)} skills, "
          f"{len(made)} rows: every example recomputed and measured, every case placed or listed unplaced, 0 faults")
    MATRIX[:] = matrix(made)
    if "--check" not in sys.argv:
        md_rows.write(made)
        doc = "\n\n".join([TITLE, LEAD] + [body(n) for n in ORDERED]) + "\n"
        (R / "docs/design/multiplication-division-taxonomy.md").write_text(doc)
        placed_in = {}
        for code, _lo, _g, levels, methods in SKILLS:
            for lv, cs in levels.items():
                for c in cs:
                    placed_in.setdefault(c, []).append(f"{code}:{lv}")
            for c in methods:
                placed_in.setdefault(c, []).append(f"{code}:method")
        data = [{**c, "placed_in": placed_in.get(c["code"], [])} for c in CASES]
        (R / "docs/design/multiplication-division-cases.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=1) + "\n")
        print("wrote docs/design/multiplication-division-taxonomy.md and docs/design/multiplication-division-cases.json")
