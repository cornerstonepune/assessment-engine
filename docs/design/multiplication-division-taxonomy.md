# Multiplication & Division Assessment Skill Taxonomy

Engine draft v0.1, 2026-10-09, for Achal to correct. It follows the Addition & Subtraction taxonomy's rule: a case is distinct whenever a child can make a different kind of mistake. Every example was computed and checked by `research/md_taxonomy.py`, not typed.

## Assumptions

Twelve decisions the engine took so the build need not wait. Each is a row or a case to change, not code.

| # | Assumed | What it means | Why |
| --- | --- | --- | --- |
| A1 | Every method is a case. | Straight levels (Easy to Hard) print each calculation in every written method this document lists for its shape, in fair shares: in a line, in columns, expanded, partitioning, grid, and lattice for 2-digit × 2-digit; for division, in a line, short division, long division, partitioning the number and chunking. Pictures (groups, arrays, number lines) belong to the concept skills. | Nimish, 2026-10-09: "consider all of the methods for now". A level's methods are a row, so a grade that teaches one method narrows it without code. |
| A2 | Division prints in a line by default. | "85 ÷ 4 = □ r □"; short division (bus stop), long division (quotient on top) and chunking are presentations of the same numbers. | The school's July papers write "144 ÷ 12 =". If the school writes the older "4 ) 85 ( 21" layout, it is one more presentation. |
| A3 | A remainder is written "r" and is its own answer. | The quotient and the remainder each get their own boxes and are marked separately. | One box holding "21 r 1" cannot be read digit by digit, and a wrong remainder with a right quotient is a different mistake from the reverse. |
| A4 | Tables run from 0 to 12. | ×11 and ×12 appear only at Advance: a fact that needs the 11 or 12 tables, either way round (3 × 12, 12 × 7), is no Easy, Medium or Hard question, and the tables' Advance holds every table. 12 × 0 and 11 × 1 are the facts of 0 and 1. | The school's 24 Jul quiz asks 11 × 4 and 12 × 5; the Grade 4 paper asks 144 ÷ 12. |
| A5 | The school's words. | "Regroup" for a multiplication carry, "exchange" when a remainder moves to the next digit, never "borrow". "Product, factor, dividend, divisor, quotient, remainder" from Grade 3; "times, groups of, shared equally, left over" before it. | CLAUDE.md: "exchange / regroup", never "borrow". |
| A6 | Grades come from the school's own objectives. | Registry LO-G1-0046 to 0055, LO-G2-0492 to 0498 and 0527 to 0530, LO-G3-0942 to 0944 and 0956 to 0959, LO-G4-1339 to 1356, and the July papers. 4-digit × 1-digit, 3-digit × 2-digit and division by a 2-digit number beyond ÷12 are in no G1 to G4 objective: they are here, placed in no grade. Where the lists disagree (one "Extended & Application" unit is repeated in G2, G3 and G4), a level goes to the earliest grade whose objective names it, except Grade 1, which is exactly what its educator taught to the end of September (2026-10-06): equal groups by adding again. A level the objectives put in Grade 1 sits in Grade 2 until the Grade 1 educator says it is taught. | A level's grade is a row (`skill_set.level_band`); Achal moves it. |
| A7 | Taught stays the educator's word. | Every case is built and checked; nothing reaches a child's paper until the grade declares it taught. | The Grade 1 rule of 2026-10-06. |
| A8 | Out of scope. | Remainders as fractions or decimals. Division by zero appears only as a true-or-false statement, never as a sum. | No G1 to G4 objective names them. |
| A9 | Stories fit their numbers. | Each story template carries the range its numbers may take, so no box holds 933 pencils. | Today's multiplication bank prints "Each box has 933 pencils". |
| A10 | Both orders. | "4 × 36" and "36 × 4" are both asked, as addition prints the shorter number first. | A child who knows 3 × 8 from the 3 table may not know 8 × 3. |
| A11 | What a mistake charges. | A slip adding the partial products counts against addition, not multiplication; the table of what each mistake charges waits for one approval, as addition's did. | ADR 0023. |
| A12 | Lattice is included. | Because every method is; it leaves by taking its cases out of the levels. | Not named in the school's objectives. |

## How to read this

A case is distinct when a child can make a different mistake on it. A question carries several tags at once; its case is the combination.

| Dimension | Typical values | Why it matters |
| --- | --- | --- |
| Operation | Multiplication / Division | Inverse of each other; different mistakes and layouts. |
| Digits in each number | 1 / 2 / 3 / 4 / N; for ÷ the number divided and the divisor | Sets the number of columns, partial products and steps. |
| Fact group | 0-1 / 2-5-10 / 3-4 / 6-9 / 11-12 | Tables are learned in groups; a child can know ×5 and not ×7. |
| Place-value factor | none / ×10 / ×100 / ×1000 / a multiple of ten (one or both numbers) | Zeros counted, dropped or doubled are their own mistakes. |
| Method | in a line, columns, expanded, partitioning, grid, lattice, repeated addition, skip counting, number line, array, groups; sharing, grouping, repeated subtraction, chunking, short division, long division | Each method has mistakes the others cannot make. |
| Regrouping (×) | none / one column / several; where: ones / tens / hundreds | A child may carry from the ones and not from the tens. |
| Carry size (×) | none / always 1 / more than 1 | Adding two numbers only ever carries 1; multiplication carries up to 8. |
| Knock-on (×) | a carry that takes a column to ten or more | The column regroups only because of the carry. |
| Partial products (×) | 1 / 2 / 3 rows; their sum with or without a carry | The placeholder zero and the adding of rows are separate skills. |
| Exchange (÷) | none / one step / several | A remainder moving to the next digit is the heart of short division. |
| First digit smaller (÷) | yes / no | The quotient has one digit fewer; children skip or write a zero. |
| Zero in the quotient (÷) | none / in the middle / at the end | The most dropped digit in division. |
| Remainder (÷) | none / some / largest possible (divisor − 1) / number smaller than the divisor | Separates exact division from division with a remainder, and tests remainder < divisor. |
| Zeros in the numbers | none / in the middle / at the end / in the multiplier / a zero only in the answer | Zeros change what is written in a column. |
| Answer size | the most digits possible / one fewer | Magnitude awareness. |
| Unknown | none / a factor / the dividend / the divisor / a digit / the remainder / the sign | Reverse reasoning, separately from calculation. |
| Question type | direct / missing / balance / true-false / compare / find the mistake / estimate / story | Calculation, reasoning and application measured apart. |
| Story structure | equal groups, sharing, grouping, array, rate, times as many, combinations, area, two steps | Same numbers, different difficulty. |
| Remainder in a story | dropped / rounded up / the answer itself / both asked | 26 children in rickshaws of 4 need 7 rickshaws, not 6. |

## Multiplication facts and place value

Facts are grouped as tables are learned; ×10, ×100 and multiples of ten are their own cases because the mistakes are about zeros, not tables.

| ID | Case | Example | Answer |
| --- | --- | --- | --- |
| TF01 | ×0: anything times zero | 7 × 0 | 0 |
| TF02 | ×1: anything times one | 1 × 8 | 8 |
| TF03 | The 2 table | 2 × 7 | 14 |
| TF04 | The 5 table | 5 × 6 | 30 |
| TF05 | The 10 table | 10 × 4 | 40 |
| TF06 | The 3 table | 3 × 8 | 24 |
| TF07 | The 4 table | 4 × 7 | 28 |
| TF08 | The 6 table | 6 × 7 | 42 |
| TF09 | The 7 table | 7 × 8 | 56 |
| TF10 | The 8 table | 8 × 6 | 48 |
| TF11 | The 9 table | 9 × 6 | 54 |
| TF12 | A square fact | 7 × 7 | 49 |
| TF13 | The 11 table | 11 × 4 | 44 |
| TF14 | The 12 table | 12 × 5 | 60 |
| TF15 | The table number second (the 3 table read the other way) | 8 × 3 | 24 |
| TF16 | A fact in columns | 7 over 6 in columns, × | 42 |
| TF17 | A cell of the multiplication square | row 6, column 9 | 54 |
| TP01 | ×10 | 45 × 10 | 450 |
| TP02 | ×100 | 45 × 100 | 4500 |
| TP03 | ×1000 | 7 × 1000 | 7000 |
| TP04 | ×10 of a number already ending in zero | 30 × 10 | 300 |
| TP05 | ×100 of a number with a zero inside | 405 × 100 | 40500 |
| TP06 | A multiple of ten × 1 digit | 30 × 4 | 120 |
| TP07 | A multiple of ten × a multiple of ten | 20 × 40 | 800 |
| TP08 | A multiple of a hundred × 1 digit | 300 × 6 | 1800 |
| TP09 | The fact makes its own zero | 50 × 4 | 200 |
| TP10 | 2 digits × a multiple of ten | 23 × 30 | 690 |
| TP11 | ×100 of a number already ending in zero | 30 × 100 | 3000 |

## Multiplication by digit shape

One case per shape and per thing that changes the working; the next section crosses the carries and zeros in full.

| ID | Case | Example | Answer |
| --- | --- | --- | --- |
| T01 | 2 × 1 digits, no regrouping | 23 × 3 | 69 |
| T02 | 2 × 1 digits in a line | 32 × 3 (in a line) | 96 |
| T03 | The 1-digit number first | 3 × 21 | 63 |
| T04 | Regroup from the ones, carry 1, 2-digit answer | 13 × 4 | 52 |
| T05 | Regroup from the ones, carry more than 1, 2-digit answer | 19 × 5 | 95 |
| T06 | No regrouping, but the answer grows to 3 digits | 42 × 3 | 126 |
| T07 | Regroup from the ones and the answer grows (the quiz's 56 × 3) | 56 × 3 | 168 |
| T08 | The carry takes the tens to ten (knock-on): a zero only in the answer | 18 × 6 | 108 |
| T09 | Regroup and the ones write 0 | 48 × 5 | 240 |
| T10 | The largest carry: 99 × 9 | 99 × 9 | 891 |
| T11 | 3 × 1 digits, no regrouping | 213 × 3 | 639 |
| T12 | 3 × 1 digits with regrouping (every pattern in the next section) | 357 × 4 | 1428 |
| T13 | 3 × 1 digits, the 1-digit number first, in a line | 6 × 125 (in a line) | 750 |
| T14 | 3 × 1 digits in a line | 785 × 4 (in a line) | 3140 |
| T15 | 4 × 1 digits, no regrouping | 2312 × 3 | 6936 |
| T16 | 4 × 1 digits with regrouping | 3476 × 6 | 20856 |
| T17 | 2 × 2 digits, no regrouping anywhere, a 3-digit answer | 21 × 13 | 273 |
| T18 | 2 × 2 digits, one row regroups, a 3-digit answer | 16 × 12 | 192 |
| T19 | 2 × 2 digits, both rows regroup, a 3-digit answer | 36 × 24 | 864 |
| T20 | 2 × 2 digits, both rows regroup and adding the rows carries into a 4th digit | 47 × 23 | 1081 |
| T21 | 2 × 2 digits, a 4-digit answer with no carry in adding the rows | 52 × 34 | 1768 |
| T22 | 2 × 2 digits in a line | 34 × 26 (in a line) | 884 |
| T23 | 3 × 2 digits | 234 × 12 | 2808 |
| T24 | 3 × 2 digits with regrouping in every row | 476 × 38 | 18088 |
| T25 | N × 1 digits (scales on) | 52341 × 7 | 366387 |
| T26 | 3 × 3 digits with a zero in the middle of the multiplier | 213 × 102 | 21726 |
| T27 | 2 × 2 digits, adding the rows carries, a 3-digit answer | 19 × 14 | 266 |
| T28 | 2 × 2 digits, one row or none regroups and adding the rows carries into a 4th digit | 68 × 17 | 1156 |

## Multiplication carries and zeros

The carry matrix for 3-digit × 1-digit (no zeros), then carry sizes, then every place a zero can sit.

| ID | Case | Example | Answer |
| --- | --- | --- | --- |
| TC01 | Regroup from the ones: no · from the tens: no · answer grows to 4 digits: no | 434 × 2 | 868 |
| TC02 | Regroup from the ones: no · from the tens: no · answer grows to 4 digits: yes | 412 × 3 | 1236 |
| TC03 | Regroup from the ones: no · from the tens: yes · answer grows to 4 digits: no | 374 × 2 | 748 |
| TC04 | Regroup from the ones: no · from the tens: yes · answer grows to 4 digits: yes | 931 × 4 | 3724 |
| TC05 | Regroup from the ones: yes · from the tens: no · answer grows to 4 digits: no | 119 × 4 | 476 |
| TC06 | Regroup from the ones: yes · from the tens: no · answer grows to 4 digits: yes | 416 × 6 | 2496 |
| TC07 | Regroup from the ones: yes · from the tens: yes · answer grows to 4 digits: no | 487 × 2 | 974 |
| TC08 | Regroup from the ones: yes · from the tens: yes · answer grows to 4 digits: yes | 194 × 6 | 1164 |
| TC09 | A carry bigger than 1 | 28 × 7 | 196 |
| TC10 | 3 × 1 digits, a carry takes a column to ten (knock-on) | 125 × 4 | 500 |
| TC11 | Every column regroups, the answer full of zeros | 667 × 3 | 2001 |
| TZ01 | A zero at the end of the larger number | 230 × 4 | 920 |
| TZ02 | A zero in the middle, no carry reaches it | 302 × 3 | 906 |
| TZ03 | A zero in the middle that a carry lands on | 506 × 7 | 3542 |
| TZ04 | Two zeros in the larger number | 1008 × 6 | 6048 |
| TZ05 | A zero only in the answer | 25 × 4 | 100 |
| TZ06 | The answer is a round number | 125 × 8 | 1000 |
| TZ07 | A 2-digit multiplier ending in zero: one row | 23 × 40 | 920 |
| TZ08 | Both numbers end in zero | 120 × 30 | 3600 |
| TZ09 | A zero in the middle, no carry reaches it, the answer grows to 4 digits | 401 × 3 | 1203 |

## Division facts and place value

The tables read backwards, then ÷10, ÷100 and multiples of ten.

| ID | Case | Example | Answer |
| --- | --- | --- | --- |
| DF01 | ÷1 | 8 ÷ 1 | 8 |
| DF02 | A number divided by itself | 7 ÷ 7 | 1 |
| DF03 | Zero divided | 0 ÷ 5 | 0 |
| DF04 | The 2 table backwards | 14 ÷ 2 | 7 |
| DF05 | The 5 table backwards | 35 ÷ 5 | 7 |
| DF06 | The 10 table backwards | 60 ÷ 10 | 6 |
| DF07 | The 3 table backwards | 27 ÷ 3 | 9 |
| DF08 | The 4 table backwards | 32 ÷ 4 | 8 |
| DF09 | The 6 table backwards | 42 ÷ 6 | 7 |
| DF10 | The 7 table backwards | 56 ÷ 7 | 8 |
| DF11 | The 8 table backwards | 48 ÷ 8 | 6 |
| DF12 | The 9 table backwards | 81 ÷ 9 | 9 |
| DF13 | The 11 table backwards | 44 ÷ 11 | 4 |
| DF14 | The 12 table backwards (the Grade 4 paper's 144 ÷ 12) | 144 ÷ 12 | 12 |
| DF15 | How many groups: "how many 6s make 42?" | How many 6s make 42? | 7 |
| DF16 | A 2-digit divisor, 1-digit quotient | 84 ÷ 12 | 7 |
| DP01 | ÷10 | 450 ÷ 10 | 45 |
| DP02 | ÷100 | 4500 ÷ 100 | 45 |
| DP03 | ÷1000 | 7000 ÷ 1000 | 7 |
| DP04 | A multiple of ten ÷ 1 digit | 120 ÷ 4 | 30 |
| DP05 | A multiple of ten ÷ a multiple of ten | 800 ÷ 40 | 20 |
| DP06 | The fact uses one of the zeros (20 ÷ 4 = 5) | 200 ÷ 4 | 50 |
| DP07 | A multiple of a hundred ÷ 1 digit | 3600 ÷ 6 | 600 |

## Division by digit shape

Short division read left to right: where a remainder is exchanged, whether the first digit is smaller than the divisor, and where the quotient has a zero.

| ID | Case | Example | Answer |
| --- | --- | --- | --- |
| D01 | 2 ÷ 1 digits, every digit divides, in the division layout | 84 ÷ 4 (division layout) | 21 |
| D02 | 2 ÷ 1 digits, every digit divides, in a line | 69 ÷ 3 | 23 |
| D03 | 2 ÷ 1 digits, one exchange from the tens, by 2, 3, 4 or 5 | 72 ÷ 4 | 18 |
| D04 | 2 ÷ 1 digits, one exchange from the tens, by 6, 7, 8 or 9 | 91 ÷ 7 | 13 |
| D05 | 3 ÷ 1 digits, no exchange | 936 ÷ 3 | 312 |
| D06 | 3 ÷ 1 digits: exchange after the hundreds: no · after the tens: yes | 476 ÷ 2 | 238 |
| D07 | 3 ÷ 1 digits: exchange after the hundreds: yes · after the tens: no | 786 ÷ 6 | 131 |
| D08 | 3 ÷ 1 digits: exchange after the hundreds: yes · after the tens: yes | 588 ÷ 3 | 196 |
| D09 | 3 ÷ 1 digits: first digit smaller than the divisor, so the hundreds join the tens · after the tens: no | 279 ÷ 3 | 93 |
| D10 | 3 ÷ 1 digits: first digit smaller than the divisor, so the hundreds join the tens · after the tens: yes | 141 ÷ 3 | 47 |
| D11 | 4 ÷ 1 digits, no exchange | 4862 ÷ 2 | 2431 |
| D12 | 4 ÷ 1 digits, first digit smaller, exchanges | 5172 ÷ 6 | 862 |
| D13 | 3 ÷ 2 digits, 2-digit quotient | 408 ÷ 12 | 34 |
| D14 | 3 ÷ 2 digits where the first estimate must be corrected | 162 ÷ 18 (rounding 18 to 20 suggests 8; 8 × 18 = 144 leaves 18, so 9) | 9 |
| DZ01 | A zero in the number divided gives a zero in the quotient | 804 ÷ 4 | 201 |
| DZ02 | A zero at the end of the quotient | 840 ÷ 4 | 210 |
| DZ03 | A zero in the quotient from a digit smaller than the divisor | 618 ÷ 6 | 103 |
| DZ04 | A zero in the number divided, none in the quotient | 702 ÷ 6 | 117 |
| DZ05 | Two zeros in the quotient | 8016 ÷ 8 | 1002 |
| DZ06 | First digit smaller and a zero in the quotient | 3015 ÷ 5 | 603 |
| DZ07 | A zero at the end of the quotient from a last digit smaller than the divisor | 62 ÷ 3 | 20 r 2 |

## Remainders

A remainder is its own answer: from a table fact up to 3 digits, smallest to largest.

| ID | Case | Example | Answer |
| --- | --- | --- | --- |
| DR01 | A table fact with a remainder | 17 ÷ 5 | 3 r 2 |
| DR02 | The largest remainder (divisor − 1) | 47 ÷ 6 | 7 r 5 |
| DR03 | The number divided is smaller than the divisor | 3 ÷ 5 | 0 r 3 |
| DR04 | 2 ÷ 1 digits, no exchange, a remainder | 85 ÷ 4 | 21 r 1 |
| DR05 | 2 ÷ 1 digits, an exchange and a remainder | 75 ÷ 4 | 18 r 3 |
| DR06 | 3 ÷ 1 digits with a remainder | 457 ÷ 3 | 152 r 1 |
| DR07 | A remainder and a zero in the quotient | 613 ÷ 6 | 102 r 1 |
| DR08 | First digit smaller and a remainder | 157 ÷ 4 | 39 r 1 |
| DR09 | Checking a remainder: quotient × divisor + remainder | 21 × 4 + 1 = □ (is 85 ÷ 4 = 21 r 1?) | 85 |
| DR10 | ÷10, 100 or 1000 with a remainder | 457 ÷ 10 | 45 r 7 |

## Methods and pictures

Every way the school's objectives name, and the standard ones, each worked through on its own example.

| ID | Case | Example | Answer |
| --- | --- | --- | --- |
| G01 | Equal groups (a picture) | 3 groups of 4 dots: how many dots? | 12 |
| G02 | Repeated addition | 4 + 4 + 4 = 3 × □ = □ | 4 and 12 |
| G03 | Skip counting | 5, 10, 15, 20, □ | 25 |
| G04 | Jumps on a number line | 4 jumps of 3 from 0 land on □ | 12 |
| G05 | An array | 3 rows of 5 stars: □ × □ = □ | 3 × 5 = 15 (5 × 3 = 15 is right too) |
| G06 | Doubling (×2, ×4 = double double, ×8) | 14 × 4: double 14 = 28, double 28 = □ | 56 |
| G07 | Partitioning, in a line | 23 × 4 = 20 × 4 + 3 × 4 = 80 + 12 = □ | 92 |
| G08 | Grid (area) method, 2 × 1 digits | 23 × 4: cells 20 × 4 = 80 and 3 × 4 = 12 | 92 |
| G09 | Grid (area) method, 2 × 2 digits | 34 × 26: cells 600, 180, 80, 24 | 884 |
| G10 | Expanded columns: each product written in full | 34 × 6: 4 × 6 = 24, 30 × 6 = 180, 24 + 180 = □ | 204 |
| G11 | Compact columns (the carry written small) | 34 × 6 in columns | 204 |
| G12 | Long multiplication: a row per digit, the second row moved a place (the zero kept) | 68 × 17: 476 + 680 = □ | 1156 |
| G13 | Lattice (gelosia) method | 47 × 23 in a 2 × 2 lattice: cells 08, 14 / 12, 21, added along the diagonals | 1081 |
| G14 | Swap the order to use a known table | 9 × 2 = 2 × 9 = □ | 18 |
| G15 | Equal sharing (a picture): how many each | 12 laddoos shared equally on 3 plates: how many on each? | 4 |
| G16 | Equal grouping (a picture): how many groups | 12 laddoos, 4 on each plate: how many plates? | 3 |
| G17 | Repeated subtraction | 15 − 3 − 3 − 3 − 3 − 3 = 0: how many 3s? | 5 |
| G18 | Jumps back on a number line | From 20, jumps of 4 back to 0: how many jumps? | 5 |
| G19 | An array, divided | 20 stars in 4 equal rows: how many in each row? | 5 |
| G20 | The table backwards (inverse) | 42 ÷ 6 = □ because 6 × □ = 42 | 7 |
| G21 | Partitioning the number divided | 72 ÷ 4 = 40 ÷ 4 + 32 ÷ 4 = 10 + 8 = □ | 18 |
| G22 | Chunking: take away ten lots of the divisor, then the rest | 96 ÷ 4: take 10 × 4, take 10 × 4, take 4 × 4 → 10 + 10 + 4 = □ | 24 |
| G23 | Short division (bus stop): the exchange written small | 72 ÷ 4: 7 ÷ 4 = 1 r 3, exchange → 32 ÷ 4 = 8 | 18 |
| G24 | Long division: divide, multiply, take away, bring down | 516 ÷ 4: 5 ÷ 4 = 1, 5 − 4 = 1, bring down 1 → 11; 11 ÷ 4 = 2, 11 − 8 = 3, bring down 6 → 36; 36 ÷ 4 = 9, 36 − 36 = 0 | 129 |
| G25 | Halving (÷2, ÷4 = halve twice) | 96 ÷ 4: halve 96 = 48, halve 48 = □ | 24 |

## Missing numbers and missing digits

Reverse reasoning. Every missing digit below has exactly one answer, checked by trying all ten.

| ID | Case | Example | Answer |
| --- | --- | --- | --- |
| Q01 | A missing factor (the quiz's own) | 8 × □ = 72 | 9 |
| Q02 | The first factor missing | □ × 6 = 42 | 7 |
| Q03 | The number divided missing | □ ÷ 4 = 7 | 28 |
| Q04 | The divisor missing | 56 ÷ □ = 8 | 7 |
| Q05 | The box first | □ = 63 ÷ 9 | 7 |
| Q06 | The same number in both boxes | □ × □ = 49 | 7 |
| Q07 | A missing digit in the larger number | 2□ × 4 = 92 | 3 |
| Q08 | A missing digit in the answer | 47 × 3 = 1□1 | 4 |
| Q09 | A missing digit in the number divided | 7□ ÷ 4 = 18 | 2 |
| Q10 | A missing digit in the quotient | 936 ÷ 3 = 3□2 | 1 |
| Q11 | Two missing digits (Olympiad style) | □7 × 6 = 3□2 | 5 and 4 |
| Q12 | The remainder missing | 38 ÷ 5 = 7 r □ | 3 |
| Q13 | The divisor missing, with a remainder | 38 ÷ □ = 7 r 3 | 5 |
| Q14 | The place-value factor missing | 45 × □ = 4500 | 100 |
| Q15 | A missing row of a long multiplication | 34 × 26 = 204 + □ | 680 |
| Q16 | A missing digit in a 3-digit number | 3□4 × 2 = 708 | 5 |

## Equality, inverse and properties; multiples and factors

What × and ÷ are, beyond working them out: the rules they keep, how they undo each other, and what a multiple and a factor are.

| ID | Case | Example | Answer |
| --- | --- | --- | --- |
| Y01 | Order does not change a product | 6 × 8 = 8 × □ | 6 |
| Y02 | Three numbers, grouped either way | (2 × 7) × 5 = 2 × (7 × 5) = □ | 70 |
| Y03 | Partitioning a factor (distributive) | 7 × 12 = 7 × 10 + 7 × □ | 2 |
| Y04 | Anything × 0 | 456 × 0 | 0 |
| Y05 | × 1 and ÷ 1 leave a number unchanged | 37 × 1 and 37 ÷ 1 | 37 and 37 |
| Y06 | A number ÷ itself, and 0 ÷ a number | 9 ÷ 9 and 0 ÷ 9 | 1 and 0 |
| Y07 | True or false: 9 ÷ 0 = 0 | 9 ÷ 0 = 0 | false: there is no answer |
| Y08 | True or false: 12 ÷ 3 = 3 ÷ 12 | 12 ÷ 3 = 3 ÷ 12 | false: division cannot be turned round |
| Y09 | A fact family | 4, 7, 28: write the four facts | 4 × 7 = 28, 7 × 4 = 28, 28 ÷ 4 = 7, 28 ÷ 7 = 4 |
| Y10 | Check a division by multiplying | 96 ÷ 4 = 24? 24 × 4 = □ | 96 |
| Y11 | Balance: × against − | 3 × 8 = 30 − □ | 6 |
| Y12 | Balance: × against ÷ | 6 × 4 = 48 ÷ □ | 2 |
| Y13 | The missing sign | 6 □ 3 = 18 and 18 □ 3 = 6 | × and ÷ |
| Y14 | Compare without working | 25 × 4 ○ 25 × 5 and 48 ÷ 6 ○ 48 ÷ 8 | < and > |
| Y15 | Double a factor, double the product | 12 × 5 = 60, so 12 × 10 = □ | 120 |
| Y16 | True or false: 7 × 6 = 6 × 7 | 7 × 6 = 6 × 7 | true |
| F01 | Multiples of a number | The multiples of 6 up to 60 | 6, 12, 18, 24, 30, 36, 42, 48, 54, 60 |
| F02 | Is it a multiple? | Is 45 a multiple of 5? | yes |
| F03 | All the factors of a number | The factors of 12 | 1, 2, 3, 4, 6, 12 |
| F04 | Factor pairs | The factor pairs of 24 | 1 × 24, 2 × 12, 3 × 8, 4 × 6 |
| F05 | A common multiple | Common multiples of 3 and 4 below 30 | 12, 24 |
| F06 | Divisible by 2, 5 and 10, from the last digit | Is 340 divisible by 2, 5 and 10? | yes, all three |
| F07 | Divisible by 3, from the sum of the digits | Is 117 divisible by 3? (1 + 1 + 7 = 9) | yes |
| F08 | Even and odd products | Is 6 × 7 even or odd? | even |

## Efficient and mental strategies

Ways round the written method, each worked on its own numbers.

| ID | Case | Example | Answer |
| --- | --- | --- | --- |
| H01 | ×5 as ×10 then halve | 46 × 5 = 460 ÷ 2 = □ | 230 |
| H02 | ×9 as ×10 take away one group | 23 × 9 = 230 − 23 = □ | 207 |
| H03 | ×11 as ×10 and one more group | 14 × 11 = 140 + 14 = □ | 154 |
| H04 | Double one, halve the other | 16 × 5 = 8 × 10 = □; 35 × 4 = 70 × 2 = □ | 80 and 140 |
| H05 | ×8 as double three times | 13 × 8: 26, 52, □ | 104 |
| H06 | ×25 as ×100 ÷ 4 | 24 × 25 = 2400 ÷ 4 = □ | 600 |
| H07 | Near a round number (compensation) | 19 × 6 = 20 × 6 − 6 = □ | 114 |
| H08 | A fact from a known fact | 7 × 8 = 56, so 7 × 9 = 56 + 7 = □ | 63 |
| H09 | ÷5 as ÷10 then double | 240 ÷ 5 = 24 × 2 = □ | 48 |
| H10 | A fact scaled by ten | 6 × 7 = 42, so 60 × 7 = □ and 600 × 7 = □ | 420 and 4200 |

## Estimating and judging an answer

Is it about right, and can it be right at all?

| ID | Case | Example | Answer |
| --- | --- | --- | --- |
| V01 | Round the larger number to the ten, then multiply | 48 × 6 ≈ 50 × 6 = □ (exact 288) | 300 |
| V02 | Round both numbers | 38 × 21 ≈ 40 × 20 = □ (exact 798) | 800 |
| V03 | How many digits will the product have? | 67 × 75 and 31 × 22 | 4 and 3 |
| V04 | How many digits will the quotient have? | 156 ÷ 4 and 456 ÷ 4 | 2 and 3 |
| V05 | Is this answer possible? | 23 × 4 = 812 | no: 23 × 4 is less than 25 × 4 = 100 |
| V06 | Odd or even, without working | 7 × 9 and 6 × 13 | odd and even |
| V07 | The last digit, without working | 47 × 3 ends in □ | 1 |
| V08 | The closest estimate | 52 × 9 is closest to 400, 450 or 500? | 450 |
| V09 | A remainder bigger than the divisor is wrong | 47 ÷ 6 = 6 r 11: possible? | no: 11 is more than 6 |
| V10 | Estimate a quotient | 412 ÷ 8 ≈ 400 ÷ 8 = □ (exact 51 r 4) | 50 |

## Word problems

One-step structures first (the same numbers are harder in some), then remainders in a story, two steps, and the language that misleads.

| ID | Case | Example | Answer |
| --- | --- | --- | --- |
| B01 | Equal groups, how many in all | 4 plates with 6 laddoos on each. How many laddoos in all? | 24 |
| B02 | Sharing: how many in each group | 24 laddoos shared equally on 4 plates. How many on each plate? | 6 |
| B03 | Grouping: how many groups | 24 laddoos, 6 on each plate. How many plates? | 4 |
| B04 | An array: how many in all | 5 rows of 7 chairs. How many chairs? | 35 |
| B05 | An array: how many in a row | 35 chairs in 5 equal rows. How many in each row? | 7 |
| B06 | Price: the cost of many | One pencil costs ₹6. What do 8 pencils cost? | ₹48 |
| B07 | Price: the cost of one | 8 pencils cost ₹48. What does one cost? | ₹6 |
| B08 | Times as many: the larger | Riya has 4 stickers. Dev has 3 times as many. How many has Dev? | 12 |
| B09 | Times as many: the smaller | Dev has 12 stickers, 3 times as many as Riya. How many has Riya? | 4 |
| B10 | Times as many: how many times | Dev has 12 stickers and Riya has 4. How many times as many stickers as Riya does Dev have? | 3 |
| B11 | Twice as many | Aman read 15 pages. Meera read twice as many. How many did Meera read? | 30 |
| B12 | Combinations | 3 shirts and 4 shorts. How many different outfits? | 12 |
| B13 | Area in squares | A rectangle 6 squares long and 4 squares wide. How many squares? | 24 |
| B14 | A remainder dropped (full boxes) | 26 laddoos, 4 in each box. How many full boxes? | 6 |
| B15 | A remainder rounded up | 26 children, 4 in each rickshaw. How many rickshaws are needed? | 7 |
| B16 | The remainder is the answer | 26 laddoos, 4 in each box. How many are left over? | 2 |
| B17 | Both asked | 26 laddoos into boxes of 4: how many boxes, how many left? | 6 boxes, 2 left |
| B18 | Two steps: ×, then + | 3 boxes of 12 pencils and 5 loose pencils. How many pencils? | 41 |
| B19 | Two steps: ×, then − | Sara has ₹100 and buys 4 pens at ₹15 each. How much is left? | ₹40 |
| B20 | Two steps: ÷, then × | 12 pencils cost ₹36. What do 5 pencils cost? | ₹15 |
| B21 | Two steps: two products added | 4 packets of 6 and 3 packets of 8. How many in all? | 48 |
| B22 | Two steps: +, then ÷ | 18 red and 14 blue balloons shared equally by 4 children. How many each? | 8 |
| B23 | A bar model: one part is times another | Ria and Sam have 32 marbles. Sam has 3 times as many as Ria. How many has Ria? | 8 |
| B24 | "Each" that means ÷ | 30 stickers, 5 for each child. How many children? | 6 |
| B25 | A number the question does not need | A van carries 8 boxes of 9 mangoes and 3 drivers. How many mangoes? | 72 |
| B26 | Read from a price list | Price list: pen ₹15, eraser ₹5. What do 3 pens cost? | ₹45 |
| B27 | Half as many | Meera read 30 pages. Aman read half as many. How many did Aman read? | 15 |

## Error diagnosis

Every wrong answer below is computed by a predictor from its example's own numbers. A blank box is the blank signal, never a named mistake (rule 5). Then the find-the-mistake cases that ask the child to spot one.

| Mistake | Op | What the child does | Example | Right | Wrong (computed) | Seen in | Counts against |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M_MUL_NO_CARRY | × | Writes each column's product without its carry | 34 × 6 | 204 | 84 | answer | the skill |
| M_MUL_CONCAT | × | Writes each digit's product side by side (Aseem's 56 × 3) | 56 × 3 | 168 | 1518 | answer | the skill |
| M_MUL_CARRY_FIRST | × | Adds the carry before multiplying | 34 × 6 | 204 | 304 | answer | the skill |
| M_MUL_ONES_ONLY | × | Multiplies only the ones | 34 × 6 | 204 | 24 | answer | the skill |
| M_MUL_UNITS_REVERSED | × | Writes only each product's units digit, ones first | 56 × 3 | 168 | 85 | answer | the skill |
| M_MUL_ROW_OUT | × | Answers the row next to it in the table (one group fewer) | 7 × 8 | 56 | 49 | answer | the facts |
| M_GROUP_MISSED | × | Adds one group fewer than there are | 3 groups of 4 | 12 | 8 | answer | the skill |
| M_ONE_GROUP | × | Writes how many are in one group | 3 groups of 4 | 12 | 4 | answer | the skill |
| M_WRONG_OP | × | Adds the numbers | 34 × 6 | 204 | 40 | answer | the skill |
| M_ZERO_AS_ONE | × | Treats × 0 as leaving the number | 7 × 0 | 0 | 7 | answer | the facts |
| M_ONE_ADDED | × | Treats × 1 as adding one | 7 × 1 | 7 | 8 | answer | the facts |
| M_TENS_ZERO_DROPPED | × | Writes one zero fewer when multiplying by 10, 100 or a multiple of ten | 45 × 100 | 4500 | 450 | answer | the skill |
| M_PARTITION_TENS_AS_ONES (new) | × | Partitions but multiplies the tens digit as ones | 23 × 4 | 92 | 20 | answer | the skill |
| M_MUL_CARRY_ONTO_ZERO_LOST | × | Forgets a carry that lands on a zero | 506 × 7 | 3542 | 3502 | answer | the skill |
| M_MUL_PLACEHOLDER | × | Second row not moved a place (the zero left out) | 68 × 17 | 1156 | 544 | answer | the skill |
| M_MUL_COLUMNWISE | × | Multiplies tens by tens and ones by ones | 68 × 17 | 1156 | 656 | answer | the skill |
| M_MUL_ONE_ROW | × | Multiplies by the ones of the multiplier only | 68 × 17 | 1156 | 476 | answer | the skill |
| M_MUL_STALE_CARRY | × | Adds the first row's carry again in the second row | 47 × 23 | 1081 | 1281 | answer | the skill |
| M_NOCARRY on the rows (existing, addition) | × | Adds the two rows without carrying | 19 × 14 | 266 | 166 | answer | addition |
| M_GRID_CELL_DROPPED (new) | × | Leaves the ones-by-ones cell out when adding a grid | 34 × 26 | 884 | 860 | working | the skill |
| M_DIV_QUOTIENT_ZERO_DROPPED (new) | ÷ | Leaves the zero out of the quotient | 804 ÷ 4 | 201 | 21 | answer | the skill |
| M_DIV_EXCHANGE_LOST (new) | ÷ | Divides each digit alone; the remainder is never exchanged | 72 ÷ 4 | 18 | 10 | answer | the skill |
| M_DIV_REMAINDER_ADDED (new) | ÷ | Adds the remainder to the next digit instead of making it tens | 72 ÷ 4 | 18 | 11 r 1 | answer | the skill |
| M_DIV_LEAD_DROPPED (new) | ÷ | Skips a first digit smaller than the divisor | 156 ÷ 4 | 39 | 14 | answer | the skill |
| M_DIV_BRING_DOWN_MISSED (new) | ÷ | Stops before bringing down the last digit | 516 ÷ 4 | 129 | 12 r 3 | answer | the skill |
| M_DIV_REMAINDER_TOO_BIG (new) | ÷ | Stops one group short: the remainder is not less than the divisor | 85 ÷ 4 | 21 r 1 | 20 r 5 | answer | the skill |
| M_DIV_REMAINDER_AS_DIGIT (new) | ÷ | Writes the remainder as the quotient's next digit | 85 ÷ 4 | 21 r 1 | 211 | answer | the skill |
| M_DIV_SWAPPED (new) | ÷ | Writes the quotient and the remainder the wrong way round | 17 ÷ 5 | 3 r 2 | 2 r 3 | answer | the skill |
| M_DIV_BIGGER_BY_SMALLER (new) | ÷ | Divides the bigger number by the smaller whichever comes first | 3 ÷ 5 | 0 r 3 | 1 r 2 | answer | the skill |
| M_DIV_SELF_AS_ZERO (new) | ÷ | Treats a number ÷ itself as nothing left | 7 ÷ 7 | 1 | 0 | answer | the facts |
| M_DIV_ZERO_DIVIDED (new) | ÷ | Answers the divisor when zero is divided | 0 ÷ 5 | 0 | 5 | answer | the facts |
| M_DIV_TENS_ZERO_LEFT (new) | ÷ | Takes away one zero fewer when dividing by 10 or 100 | 4500 ÷ 100 | 45 | 450 | answer | the skill |
| M_DIV_TENS_ZERO_EXTRA (new) | ÷ | Uses a zero for the fact, then writes every zero back | 200 ÷ 4 | 50 | 500 | answer | the skill |
| M_WRONG_OP (÷) | ÷ | Multiplies instead of dividing | 84 ÷ 4 | 21 | 336 | answer | the skill |
| M_DIV_SUBTRACTED (new) | ÷ | Takes the divisor away once | 84 ÷ 4 | 21 | 80 | answer | the skill |
| M_DIV_ALL_COUNTED (new) | ÷ | Counts them all, not one share or the groups | 12 dots shared into 3 rings | 4 | 12 | answer | the skill |
| M_DIV_GROUPS_FOR_SIZE (new) | ÷ | Writes the number the question gives for the one it asks: the rings for how many in each | 12 dots shared into 3 rings | 4 | 3 | answer | the skill |
| M_DIV_START_COUNTED (new) | ÷ | Counts the number it starts from as one more jump | from 20 back to 0 in jumps of 4 | 5 | 6 | answer | the skill |
| M_REMAINDER_NOT_ROUNDED_UP (new) | ÷ | Drops the remainder when the story needs one more | 26 children, 4 to a rickshaw | 7 | 6 | answer | word problems |
| M_TIMES_AS_MORE (new) | × | Reads "3 times as many" as "3 more" | 4 stickers, 3 times as many | 12 | 7 | answer | word problems |
| M_KEYWORD_OVERGENERALISED (existing) | ÷ | Multiplies because the story says "each" | 30 stickers, 5 for each child | 6 | 150 | answer | word problems |

| ID | Case | Example | Answer |
| --- | --- | --- | --- |
| C01 | Find the mistake: products side by side | 56 × 3 = 1518 | M_MUL_CONCAT |
| C02 | Find the mistake: carries left out | 34 × 6 = 84 | M_MUL_NO_CARRY |
| C03 | Find the mistake: the second row not moved | 68 × 17 = 544 | M_MUL_PLACEHOLDER |
| C04 | Find the mistake: the zero left out of the quotient | 612 ÷ 6 = 12 | M_DIV_QUOTIENT_ZERO_DROPPED |
| C05 | Find the mistake: a remainder too big | 85 ÷ 4 = 20 r 5 | M_DIV_REMAINDER_TOO_BIG |
| C06 | Find the mistake: partitioning, tens taken as ones | 23 × 4 = 2 × 4 + 3 × 4 = 20 | M_PARTITION_TENS_AS_ONES |
| C07 | Say which step of a long division went wrong | 516 ÷ 4 = 12 r 3 | M_DIV_BRING_DOWN_MISSED: the 6 was never brought down |
| C08 | Explain, by multiplying back, why an answer cannot be right | 804 ÷ 4 = 21 | 21 × 4 = 84, not 804 |
| C09 | Find the mistake: the carry onto the zero left out | 506 × 7 = 3502 | M_MUL_CARRY_ONTO_ZERO_LOST: the tens are 0 × 7 + 4 = 4 |

## Master tagging matrix

Every tag a multiplication or division case reads, as its `case_dimension` row says it. Code measures each from the question's numbers, or reads what the kind that made it states (the method it prints, a story's shape, what a remainder is for); none is typed by a person.

| Tag | Allowed values | Why it matters |
| --- | --- | --- |
| operation | ADD / SUB / MUL / DIV | Different inverse relationships and regrouping logic; multiplying and dividing undo each other as adding and taking away do. |
| operand_1_digits | 1 / 2 / 3 / 4 / 5 / 6 | Controls magnitude and place-value complexity. |
| operand_2_digits | 1 / 2 / 3 / 4 / 5 / 6 | Unequal lengths create alignment errors. |
| operand_order | LONGER_FIRST / SHORTER_FIRST / EQUAL_LENGTH / MIXED | For addition, commutativity does not remove the diagnostic value of order. |
| regrouping | NONE / SINGLE / MULTIPLE | Separates basic calculation from regrouping: carrying, and exchanging. |
| zero_pattern | NONE / INTERNAL / TRAILING / INTERNAL+TRAILING / MULTIPLE / ANSWER_ZERO | Zeros change what carrying and exchanging demand: where the zeros of the number worked on sit (inside 302, at the end of 230, both in 4050), or none there but one in the answer (25 × 4 = 100). Addition and subtraction say MULTIPLE where a number has two. |
| zero_count | 0 / 1 / 2 / 3 / 4 / 5 / 6 | How many zeros the number worked on has: 1008 has two, and each one a carry or an exchange can pass. |
| answer_digit_change | SAME / +1 / -1 / -MULTIPLE / ZERO / FULL / ONE_FEWER | Tests whether the learner anticipates magnitude changes. |
| unknown_position | FIRST_OPERAND / SECOND_OPERAND / RESULT / MULTIPLE / REMAINDER | Where the blank sits changes the reasoning demand: a missing difference is direct calculation, a missing subtrahend or minuend is inverse reasoning. |
| reasoning_type | DIRECT / INVERSE / BALANCE / CONSTRAINT / ERROR_DIAGNOSIS | Measures calculation, application and reasoning separately. |
| strategy | STANDARD / MENTAL / COMPENSATION / ESTIMATION / TIMES_TEN_THEN_HALVE / TIMES_TEN_LESS_A_GROUP / TIMES_TEN_AND_A_GROUP / DOUBLE_ONE_HALVE_THE_OTHER / DOUBLE_THREE_TIMES / TIMES_HUNDRED_THEN_QUARTER / FACT_DERIVED / DIVIDE_BY_TEN_THEN_DOUBLE / SCALED_FACT / SWAP | Measures strategy choice, not only whether the final answer is correct. |
| context | BARE_NUMBER / WORD_PROBLEM / TABLE_OR_CHART | Application and operation selection: the operation must be inferred from the situation, not from one keyword. |
| taxonomy | ADD_SUB / MUL_DIV | Which of the school's two documents a question is a case of: multiplication and division's when any of its operations is × or ÷. A case names its own, so neither document's case holds the other's question. |
| digits_max | 1 / 2 / 3 / 4 / 5 / 6 | The longest number's digits. |
| digits_min | 1 / 2 / 3 / 4 / 5 / 6 | The shortest number's digits. |
| answer_digits | 1 / 2 / 3 / 4 / 5 / 6 / 7 | How many digits the answer has. |
| answer_zeros | NONE / INTERNAL / TRAILING / INTERNAL+TRAILING | Where the answer's zeros sit: a zero inside an answer (108) is forgotten where one at its end (240) is not. |
| answer_round | YES / NO | An answer that is one digit and zeros (100, 1000): every column but the first writes 0. |
| answer_first | YES / NO | The answer written before the sum (□ = 63 ÷ 9): the equals sign read both ways. |
| carry_into_zero | YES / NO | A carry lands on a column where a number shows 0 (208 + 96; 506 × 7). |
| carry_max | 0 / 1 / 2 / 3 / 4 / 5 / 6 / 7 / 8 | The largest carry a column sends on: 3 when four 1-digit numbers are added, 8 in 99 × 9. |
| carry_size | NONE / ONE / MORE_THAN_ONE | A multiplication's carry of 1, or of more: a carry of 4 is the one a child adds as 1. |
| divisor_group | 0-1 / 2-5-10 / 3-4 / 6-9 / 11-12 | The fact group a 1-digit divisor's table is in: each step of a division is read from that table. |
| equal_operands | YES / NO | The same number twice: a square fact (7 × 7), a number divided by itself (7 ÷ 7). |
| estimate_corrected | YES / NO | A 2-digit divisor whose first estimate, rounded to its ten, must be put right (162 ÷ 18: 20 suggests 8, the answer is 9). |
| fact | YES / NO | A table fact: two numbers to 12 multiplied, or one read backwards with nothing left over. |
| fact_table | 0 / 1 / 2 / 3 / 4 / 5 / 6 / 7 / 8 / 9 / 10 / 11 / 12 | The table a fact is read from: its first number's, or the divisor's. |
| fact_group | 0-1 / 2-5-10 / 3-4 / 6-9 / 11-12 | The easiest table holding a fact in its first ten rows: the groups the tables are taught in. |
| fact_swapped | YES / NO | A fact whose second number's table is the easier one: the table read the other way (8 × 3). |
| fact_zero | YES / NO | A scaled fact whose own product ends in 0 (50 × 4: 5 × 4 = 20), or a division whose fact uses one of the zeros (200 ÷ 4: 20 ÷ 4). |
| first_digit_smaller | YES / NO | The first digit (or digits) smaller than the divisor, so they join the next: the quotient is a digit shorter. |
| knock_on | YES / NO | A carry or exchange that makes the next column need one it would not otherwise have (342 − 148; 18 × 6). |
| method | LINE / COLUMNS / EXPANDED / PARTITIONING / GRID / LATTICE / LONG_MULTIPLICATION / REPEATED_ADDITION / SKIP_COUNTING / NUMBER_LINE / ARRAY / GROUPS / DOUBLING / SHARING / GROUPING / REPEATED_SUBTRACTION / PARTITION_DIVIDEND / CHUNKING / SHORT_DIVISION / LONG_DIVISION / HALVING | The way a multiplication or division is worked on the page: the standard ones in a line and in columns, and every method the school's objectives name. |
| missing_count | 1 / 2 / 3 / 4 | How many digits are missing. |
| missing_in | FIRST / SECOND / RESULT / FIRST+SECOND / FIRST+RESULT / SECOND+RESULT / FIRST+SECOND+RESULT | Which numbers have a missing digit. |
| multiplier_zero | NONE / TRAILING / INTERNAL | A zero in the multiplier: one at its end writes no row (23 × 40), one inside writes none for that place (213 × 102). |
| one_operand | NONE / FIRST / SECOND / BOTH | A 1 among the numbers: × 1 and ÷ 1 leave a number unchanged. |
| partial_products | 1 / 2 / 3 / 4 | How many rows a long multiplication writes: one for each digit of the multiplier that is not 0. |
| partial_sum_regrouping | NONE / SINGLE / MULTIPLE | Whether adding a long multiplication's rows carries, once or more. |
| place_value_factor | NONE / X10 / X100 / X1000 / MULTIPLE_OF_TEN_ONE / MULTIPLE_OF_HUNDRED_ONE / MULTIPLE_OF_TEN_BOTH | By 10, 100 or 1000; or a round number, one or both, whose zeros are placed after the fact. |
| planted | M_ALIGN_LEFT / M_H2V_SHIFT / M_NOCARRY / M_CARRY_SKIP / M_CARRY_ALWAYS_1 / M_DROP_CARRYOUT / M_SMALL_FROM_LARGE / M_NO_DECREMENT / M_EXCHANGE_WRONG_PLACE / M_ZERO_LENDER / M_ZERO_NOT_NINE / M_ZERO_DROPPED / M_SUB_INSTEAD / M_MISSING_DIGIT_LOCAL / M_EQUALS_MEANS_ANSWER / M_MUL_CONCAT / M_MUL_NO_CARRY / M_MUL_PLACEHOLDER / M_DIV_QUOTIENT_ZERO_DROPPED / M_DIV_REMAINDER_TOO_BIG / M_PARTITION_TENS_AS_ONES / M_DIV_BRING_DOWN_MISSED / M_MUL_CARRY_ONTO_ZERO_LOST | The mistake a find-the-mistake question shows, as its misconception code. |
| quotient_zero | NONE / MIDDLE / END / MULTIPLE | Where the quotient has a zero: the one a child leaves out (612 ÷ 6 = 12). |
| regroup_at | NONE, or any of ONES / TENS / HUNDREDS / THOUSANDS / TEN_THOUSANDS, joined from the ones up | Which places carry or exchange, named from the ones up and joined: ONES+TENS, TENS+HUNDREDS. |
| remainder | NONE / SOME / LARGEST / DIVIDEND_SMALLER | What is left over: nothing, some, the most a divisor allows, or the whole of a number smaller than the divisor. |
| remainder_use | NONE / ROUND_DOWN / ROUND_UP / REMAINDER_ASKED / BOTH_ASKED | What a story does with a remainder: drops it, rounds up, asks for it, or asks for both. |
| row_regrouping | NONE / SOME / ALL | Whether a long multiplication's rows carry: none, some or all of them. |
| scaled_fact | YES / NO | A round number's sum that is a table fact once its zeros are off (30 × 4 is 3 × 4). |
| shape | SAME_LETTER / INEQUALITY / MISSING_SIGN / MISSING_SIGNS / FROM_ADDITION / FROM_SUBTRACTION / BALANCE_SAME_OP / BALANCE_TWO_OPS / SAME_BOTH_SIDES / TRUE_FALSE / COMPARE / FRIENDLY_PAIRS / JUDGED / HOW_MANY_GROUPS / SWAP_TO_A_KNOWN_TABLE / MISSING_ROW / ORDER / GROUPED_EITHER_WAY / PARTITION_A_FACTOR / BY_ONE / BY_ITSELF_AND_OF_ZERO / TRUE_FALSE_DIVIDE_BY_ZERO / TRUE_FALSE_DIVISION_ORDER / FROM_MULTIPLICATION / TABLE_BACKWARDS / BALANCE_TIMES_AND_MINUS / BALANCE_TIMES_AND_DIVIDE / DOUBLE_A_FACTOR / TRUE_FALSE_ORDER / MULTIPLES / IS_A_MULTIPLE / FACTORS / FACTOR_PAIRS / COMMON_MULTIPLES / DIVISIBLE_BY_2_5_10 / DIVISIBLE_BY_3 / PARITY_OF_A_PRODUCT / ROUND_ONE / ROUND_BOTH / ANSWER_DIGITS / LAST_DIGIT / PICTURE / SUM / STORY / ARRAY | The shape a kind of question states it printed: an equation's, an estimate's, a fact family's, a multiples question's, equal groups as a picture, a sum or a story. |
| structure | JOIN_RESULT / JOIN_CHANGE / JOIN_START / SEPARATE_RESULT / SEPARATE_CHANGE / SEPARATE_START / PPW_WHOLE / PPW_PART / COMPARE_DIFFERENCE / COMPARE_LARGER / COMPARE_SMALLER / EXTRA_INFORMATION / ADD_ADD / SUB_SUB / SUB_ADD / ADD_SUB / UNKNOWN_FIRST / CONSTRAINT / EQUAL_GROUPS / SHARING / GROUPING / ARRAY / RATE_TOTAL / RATE_UNIT / TIMES_AS_MANY_LARGER / TIMES_AS_MANY_SMALLER / HOW_MANY_TIMES / TWICE_AS_MANY / COMBINATIONS / AREA / MULTIPLY_THEN_ADD / MULTIPLY_THEN_SUBTRACT / DIVIDE_THEN_MULTIPLY / TWO_PRODUCTS_ADDED / ADD_THEN_DIVIDE / BAR_MODEL_TIMES_AS_MANY / GROUPING_BY_EACH / HALF_AS_MANY | A story's shape, as its template declares it: who joins, shares, groups or compares, and in how many steps. |
| zero_operand | NONE / FIRST / SECOND / BOTH | A 0 among the numbers. |

## Suggested progression and the skills it becomes

17 skills, every one of the 251 cases placed in a level or listed as unplaced. Easy to Hard are straight calculation; Advance mixes the hardest straight cases with missing numbers, stories, finding the mistake and estimating. A question has one home: every round-number multiplication that is not a table fact is MUL.TENS's, so a 3-digit number ending in zero (TZ01) and a multiplier ending in zero (TZ07) sit at its Advance with TP10, which holds the same questions. Grades are assumed (A6) and move as rows.

| Skill | Can do | Grade by level | Easy | Medium | Hard | Advance | Methods printed at Easy to Hard |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MUL.GROUPS | Finds how many in equal groups by adding the same number again (exists, unchanged) | E:G1 M:G1 A:G1 | G01, G02 | G01, G02 | – | B01 | – |
| MUL.MODELS | Shows multiplication as skip counting, arrays, jumps on a number line and the multiplication square | E:G2 M:G2 H:G2 A:G2 | G03, G05 | G04 | G14, TF17 | B04, B11, B13 | – |
| MUL.FACTS | Recalls multiplication facts to 10 × 10, then ×11 and ×12, in either order | E:G2 M:G2 H:G2 A:G3 | TF03, TF04, TF05 | TF01, TF02, TF06, TF07, TF15 | TF08, TF09, TF10, TF11, TF12, TF16 | TF13, TF14, Q01, Q02, Q06, Y09, H08 | – |
| MUL.TENS | Multiplies by 10, 100 and 1000 and by multiples of ten, placing the zeros | E:G3 M:G3 H:G4 A:G4 | TP01, TP04 | TP02, TP03, TP05, TP11 | TP06, TP07, TP08, TP09 | TP10, Q14, H10, TZ08, TZ01, TZ07 | – |
| MUL.2D1D | Multiplies a 2-digit number by a 1-digit number, regrouping when a column makes ten or more | E:G2 M:G2 H:G3 A:G3 | T01, T03 | T04, T05, T06 | T07, T08, T09, T10, TC09, TZ05 | Q07, Q08, Q11, C01, C02, C06, V01, V07, B06, B08, H01, H07 | T02, G07, G08, G10, G11 |
| MUL.3D1D | Multiplies a 3-digit number by a 1-digit number, regrouping in any column and onto a zero | E:G4 M:G4 H:G4 A:G4 | T11, TC01, TZ02 | TC02, TC03, TC05, TZ09 | T12, TC04, TC06, TC07, TC08, TC10, TC11, TZ03, TZ06 | Q16, C09 | T13, T14, G10, G11 |
| MUL.2D2D | Multiplies two 2-digit numbers, a row for each digit with the second row moved a place | E:G4 M:G4 H:G4 A:G4 | T17 | T18 | T19, T20, T21, T27, T28 | C03, V02, V03, Q15, B12 | T22, G09, G12, G13 |
| DIV.GROUPS | Divides by sharing equally and by making equal groups, with pictures, arrays and jumps back | E:G2 M:G2 H:G2 A:G2 | G15, G16 | G17, G19 | G18 | B02, B03, B05, B24 | – |
| DIV.FACTS | Recalls division facts as the tables backwards, with a remainder when one is left | E:G2 M:G2 H:G2 A:G3 | DF04, DF05, DF06 | DF01, DF02, DF03, DF07, DF08, DF15 | DF09, DF10, DF11, DF12 | DF13, DF14, DF16, DR01, DR02, DR03, Q03, Q04, Q05, G20, B07 | – |
| DIV.TENS | Divides by 10, 100 and 1000 and by multiples of ten | E:G4 M:G4 H:G4 A:G4 | DP01 | DP02, DP03 | DP04, DP05, DP06, DP07 | DR10 | – |
| DIV.2D1D | Divides a 2-digit number by a 1-digit number, exchanging a remainder into the next digit | E:G2 M:G2 H:G3 A:G3 | D01, D02 | D03, D04 | DR04, DR05, DZ07 | Q09, Q12, Q13, C05, V09, B14, B15, B16, B17, Y10 | D02, G21, G22, G23, G25 |
| DIV.3D1D | Divides a 3-digit number by a 1-digit number, with zeros and remainders in the quotient | E:G4 M:G4 H:G4 A:G4 | D05 | D06, D07 | D08, D09, D10, DZ01, DZ02, DZ03, DZ04, DR06, DR07, DR08 | Q10, C04, C07, V04, V10, H09 | G22, G23, G24 |
| MD.WORD | Solves one- and two-step stories with × and ÷, choosing the operation and using a remainder as the story needs | E:G2 M:G2 H:G3 A:G4 | B01, B02, B03, B06 | B04, B05, B07, B11, B27 | B08, B09, B10, B14, B15, B16, B17 | B12, B13, B18, B19, B20, B21, B22, B23, B25, B26 | – |
| MD.MENTAL | Multiplies and divides in the head by doubling, halving, tens and known facts | E:G2 M:G3 H:G3 A:G4 | G06, H10 | H01, H04, H08 | H02, H03, H05, H07, H09, G25 | H06 | – |
| MD.MULTIPLES | Finds multiples and factors and tells divisibility by 2, 3, 5 and 10 | E:G3 M:G3 H:G4 A:G4 | F01, F02, F06 | F03, F04, F08 | F05 | F07 | – |
| MD.EQUALITY | Uses × and ÷ as inverses, keeps a balance true and knows the rules of 0 and 1 | E:G3 M:G3 H:G4 A:G4 | Y01, Y04, Y05, Y06, Y16 | Y02, Y09, Y10, Y15 | Y03, Y11, Y12, Y13, Y14 | Y07, Y08, DR09, C08 | – |
| MD.ESTIMATE | Estimates products and quotients and judges whether an answer can be right | E:G4 M:G4 H:G4 A:G4 | V06, V07 | V01, V03, V04 | V02, V08, V10 | V05, V09 | – |

Unplaced until a grade claims them: T15, T16, T23, T24, T25, T26, D11, D12, D13, D14, DZ05, DZ06, TZ04.
