# B2–B4: what must be decided before each can be locked

## Decided — Nimish, 2026-10-21

Nimish put `scope-locked` on these drafts and chose "A": each recommendation below stands as the decision. Asked
"nothing will change for any of the past assessments, scoring etc. right?", the answer is a check, not a promise:

- **Past results are unchanged, proved at every step.** B2, B3 and B4 each carry a test, and its rehearsal on a copy of
  live, that the evidence rows (count and checksum), every child's states and every scored answer are the same before
  and after. A step whose check differs does not ship.
- **B2's approval gate never blocks a paper that can be made today.** Every format already on a paper, or already
  approved level by level, starts approved; only a new type waits for the coordinator.

| # | Decision |
|---|---|
| B2-1 | A question type is a format as ADR 0077 settled; the 33 labels are the words each type shows |
| B2-2 | B2 builds the approval table, the gate and an engine command to approve; the approval page waits (no new screen) |
| B2-3 | Achal: words for `word_budget`; whether chunking and long division are types of their own |
| B2-4 | The coordinator approves a new type |
| B3-1 | Achal checks the split of each level's examples, the 13 unclean ones first |
| B3-2 | Achal confirms or removes the 8 division mistakes, "Multiplied instead of dividing" and the 4 column ones |
| B3-3 | Prerequisites start from the ladder's order; Achal corrects them |
| B4-1 | Rename `skill_set` → `skill` and the registry's `skill` → `registry_skill`, in two deploys, registry first |
| B4-2 | Evidence keeps its column `rung_code`; no row is rewritten |
| B4-3 | "No file reads rung" means the `rung` table; the maths library's word stays |

Still open: B2-3 waits on Achal. B3-1, B3-2 and B3-3 no longer wait (Nimish, 2026-10-21: "there is NO dependency on
Achal"): each is decided by a rule a test checks, in goals/b3-samples-mistakes-prerequisites.yaml and ADR 0092; Achal
may correct the rows later.

Drafts: `b2-question-types-are-rows.yaml`, `b3-samples-mistakes-prerequisites.yaml`, `b4-the-rung-folded-in.yaml`
(this folder). Numbers measured on the seed and code on 2026-10-21; where BUILD-ORDER differs, it says so below.

## B2 — question types become rows

1. **What one question type is (Nimish).** BUILD-ORDER says "the 33 labels, the 6 card kinds and the maths library's
   types". These overlap: the 6 card kinds all sit under one of the 33 labels ("from the school's examples"), and the
   library's types are a third way of naming the same questions. Recommended: a type is a format as ADR 0077 already
   settled (the printed format where the question is only a level's numbers, else its template). Live had 74 of those.
   The 33 labels become the words each type shows.
2. **SF2a is parked, not built (Nimish).** "One approval per type (SF2a)" needs SF2a's gate, which was never built
   (its draft is in `docs/drafts/sf2a/`). Either B2 takes SF2a in whole, or B2 builds the table and the gate and
   SF2a's approval page follows. Recommended: B2 takes the gate and an engine command to approve; the page waits,
   since backend-first says no new screen.
3. **Three labels out of step (Achal).** "Budget word problem" (`word_budget`) is used by a skill but has no words;
   "chunking" and "long division" have words but no skill lists them. Give `word_budget` its words; say whether the two
   methods are types of their own or ways of working a division type.
4. **Who approves a new type (Nimish).** The coordinator alone, as SF2a says, or Achal too?

## B3 — samples, mistakes, registry links, what comes before

1. **Who checks the split of each level's examples (Nimish names the person; Achal recommended).** About 97 of the 178
   levels end in a sentence followed by examples, about 200 examples in all. At least 13 do not split cleanly: "56 × 3
   = 1518 found wrong", "21 × 4 = □, and why", "the cost of 8 boxes at ₹16". Each is a sample, part of the statement,
   or dropped; one person says which, level by level.
2. **The 8 division mistakes on Multiplication facts (Achal).** Confirm or remove each: bring-down missed, exchange
   lost, first digit dropped, quotient zero dropped, remainder added, divisor taken away once, tens zero extra, tens
   zero left. Two more he should look at while there: "Multiplied instead of dividing" is listed on a multiplication
   skill, and four column-method mistakes (carry first, tens by tens, row not moved a place, one row only) are listed
   on single-digit facts.
3. **Where prerequisites come from (Achal).** Nothing in the seed says which skill comes before which; today only the
   ladder's order does. Either Achal writes them, or they start from the ladder (each skill after the one before it in
   its topic) and he corrects them. Recommended: start from the ladder, Achal corrects. B3 cannot be locked without one.
4. **Registry links (no decision, a note).** 61 links come straight from the rungs' lists; nothing to choose.

## B4 — the rung folded into the skill

1. **The rename (Nimish; the audit's decision B1, still open).** Rename `skill_set` to `skill` and the registry's
   `skill` to `registry_skill`? If yes, do it in two deploys, registry first: a reader of `skill` left behind then
   fails loudly instead of silently reading the school's skills in place of the registry's.
2. **What the second code is called on evidence (Nimish).** Evidence keeps its rung code (R7, R36…), never rewritten.
   Keep the column's name `rung_code` on evidence, the child's map and the class card, or rename the column (no row
   changes, only its name)? Recommended: keep it; a rename touches 37 files for no change a person sees.
3. **"No file reads rung" means the table (Nimish).** 19 files read the `rung` table; those move. The maths library
   uses the word as a name in 33 files without reading the table; recommended to leave it (rule 10: extend the library,
   do not rewrite it).

## What can be built beside B1, and what must wait

- **None of B2–B4 can be built in parallel with B1.** The rule is one change to the database at a time.
  - B2's `skill_level_question_type` points at B1's `skill_level`, and the formats lists it replaces sit in the same
    level data B1 is moving.
  - B3's samples point at `skill_level`. Its mistakes, registry links and prerequisites point only at the skill, but
    they change the same seed file (`skill_sets.json`) and loader B1 is changing.
  - B4 renames the table every one of them points at, so it is last.
- **What can happen now, beside B1:** every decision above, Achal's checks (the examples split, the 9 + 4 mistakes,
  prerequisites), and measuring B2's types on a copy of live.
- **Order on the line:** B0c and B0d come before B1 in BUILD-ORDER, and neither goal file is on main yet. If B1 is
  going first, the order line should say so.

## Numbers checked against BUILD-ORDER

| BUILD-ORDER says | Measured | |
|---|---|---|
| 178 levels (B1) | 178 | same |
| 33 labels (B2) | 33 in the website; 32 in the skills' lists | the lists differ by three (B2-3) |
| 6 card kinds (B2) | 6 | same, but inside one of the 33 |
| the library's types (B2) | no list; 26 named templates in code; 74 formats on live (ADR 0077, not re-measured) | to be settled (B2-1) |
| 8 division mistakes on Multiplication facts (B3) | 8 | same; one more and four column ones to look at |
| rungs (B4) | 46, one per skill | same as the audit |

BUILD-ORDER's table is not changed: none of its numbers was wrong.
