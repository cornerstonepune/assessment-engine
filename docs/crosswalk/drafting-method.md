# The drafting method: one prompt, one way of thinking

Version 1, 28 Sep 2026. It becomes the prompt row `crosswalk_draft`, version 1, when the crosswalk's tables are
migrated (ADR 0041, CLAUDE.md rule 2). Until then it lives here. Its first output is `docs/crosswalk/drafts/`.

Nimish, 28 Sep: "no approver needs to actually write … articulate from your side and have a proper prompt that we can
align on, which creates these learning objectives in a certain way with a consistent thought process."

So nobody at school writes. The method drafts; code checks what code can; the signatory (Akanksha, for every subject,
to start) only decides each row: **Approve**, **Change** (with a comment, and the method redrafts) or **Reject**. The
first sample she approves becomes the gold set that every later draft is scored against (rule 7).

## What it is given

For one step of one strand (for example, Maths · Number · age 8, which is Grade 3):

1. The school's objectives placed on that step: code, unit and title, as the school wrote them.
2. The official statements of the same subject for that age and a year either side, word for word, each with its
   framework, code and the ages its level covers:
   - NCF-SE 2023: the stage's competencies (Preparatory is ages 8–11);
   - NCERT's learning outcomes: the class at that age (Class 3 is ages 8–9) and the classes either side;
   - Cambridge Primary: the stage at that age (Stage 4 is ages 8–9, worked out from "aged 5 to 11") and the stage
     before, because a school may teach a stage a year after Cambridge's typical age.
3. The engine's skill sets for the subject, each with its written learning objective and its four difficulties
   (Easy, Medium, Hard, Advance).
4. The graduate profile's eight capabilities.
5. The rubric scale: Beginning, Developing, Secure, Extending.

## The way of thinking, in this order, every time

1. **Read the school's objective for what a child does.** A title such as "Place value (reading/writing large
   numbers, partitioning, rounding)" names three actions: reading and writing numbers, partitioning them and
   rounding them. List them. If another objective on the same step asks for the same action, name it under
   `overlaps`: the school's map often repeats an objective in two units, and the signatory may merge them.
2. **Find what each framework asks at this age.** For each action, find the official statements that ask for it.
   Take the ones at the step's age first. Use the level either side only when the action sits there.
3. **Say how each one relates**, with one of four words and a one-line reason that quotes both sides:
   - `meets`: ours asks for what the statement asks, at this age;
   - `extends`: ours asks for more (a larger range, more independence, an explanation);
   - `partly_meets`: ours covers part of it; the reason names the part it leaves out;
   - `prepares_for`: the statement sits a year later; ours builds towards it.
   Every objective gets an NCF-SE statement and a Cambridge statement, or, for either, the reason there is none
   at this age (for example: "Roman numerals are not in Cambridge Primary Mathematics 0096"). A reason is a fact
   about the framework, never a guess about the school.
4. **Write what we say**: one sentence, the school's objective restated so that a child can be seen doing it.
   It combines the frameworks and, where the school chooses, goes further than both.
   - It begins with what the child does: a verb from the list below.
   - It states the range, taken from the statement it meets (for example, "numbers to 1000", "halves, quarters and
     thirds"). A range is never invented.
   - It names the way of working when the objective does ("using hundreds, tens and ones", "in columns and mentally").
   - It keeps what only NCF-SE asks for when that fits the objective: the Indian place value system and number
     names, the tables up to 10 × 10 (Pahade), money in ₹, daily-life problems.
   - It uses the school's words: "exchange" or "regroup", never "borrow"; "educator", never "teacher".
   - It has 35 words or fewer.
5. **Name the capability it builds**: one primary and at most one secondary, from the graduate profile's eight.
6. **Name the skill sets that test it**: the engine's skill sets whose written objective asks for the same action.
   Link none rather than a loose one.
7. **Once per step, write the outcome**: two to four sentences saying what a child at this step does across the
   strand, gathering every objective on the step. It follows the same rules as step 4.
8. **Write one rubric line per level** for that outcome. The four levels differ on the same four things every time:
   - how much help the child needs;
   - how much of the range they manage;
   - how consistent they are;
   - whether they carry it to new problems and explain it.

   | Level | Says | The engine's evidence suggests it when |
   |---|---|---|
   | Beginning | does parts of the step with help or materials, in the smaller range | right at Easy |
   | Developing | does it alone in simpler cases, with slips in harder ones | right at Medium |
   | Secure | does what the outcome says, alone and consistently: the target | right at Hard |
   | Extending | uses it in new problems, explains why it works, finds and fixes a mistake | right at Advance |

   Each line is one or two sentences of what the child does, never what they "understand". The suggestion is only
   a suggestion; the educator confirms the level.
9. **List what no objective covers.** Every official statement at the step's age that no objective meets or
   extends is listed. For each, propose one of three things: add it to an objective (`add_to`, naming which), a new
   objective (`new`, with its "what we say"), or leave it out (`leave_out`, with the reason). Leaving a statement
   out is a claim like any other, and the signatory decides it.
10. **Check before handing over.** Do not hand over a draft that would fail the checks below.

## Words

What a child does, and the words a draft may begin with: reads, writes, says, counts, compares, orders, rounds,
estimates, adds, subtracts, multiplies, divides, recalls, finds, uses, represents, shows, partitions, sorts,
explains, checks, solves, creates, describes, identifies, extends, records, measures, chooses, predicts, places,
plans. A rubric line may open with the help the child has ("With help, …", "Alone, …") and then a word from the
list.

Never, anywhere in a draft: understands, knows, learns, appreciates, is aware of, is exposed to, develops,
gets familiar with, borrow, teacher. What a child "understands" cannot be seen; what they do with it can.

## What code checks, so nobody has to

`python3 research/crosswalk_build.py` checks every draft (the checks are in `research/crosswalk_drafts.py`, and the
words above are read from this file). It refuses a draft when:
- an official statement it cites does not exist, or sits outside the step's age by more than a year;
- a relation is not one of the four, or a reason is empty;
- an objective has, for NCF-SE or for Cambridge, neither a statement nor a reason;
- a sentence begins with a word not on the list, uses a word that is never used, or is over the length;
- the outcome lacks a line for any level of the scale;
- a skill set or a capability does not exist;
- the same link appears twice;
- a Cambridge objective of the strand, at the step's age or a year younger, is neither aligned nor listed as not
  covered.

## What the signatory sees

One row per objective: the school's title, what NCF-SE, NCERT and Cambridge say (word for word, with page), the
relation and the reason, what we say, the capability and the skill sets. A decision on the row decides every claim it
shows. Then one row for the outcome, one for each rubric line, and one for each statement not covered. Her columns
are **Decision** (Approve, Change, Reject) and **Comment** (`research/crosswalk_sheet.py`, read back by
`research/crosswalk_decisions.py`). Only a person's decision makes a claim the school's word. A draft that nobody
decides counts for nothing.

## The output, exactly

```json
{
  "step": "MATH.NUMBER.8",
  "method": {"purpose": "crosswalk_draft", "version": 1},
  "objectives": [
    {
      "lo_code": "LO-G3-0930",
      "actions": ["reads and writes numbers", "partitions them", "rounds them"],
      "overlaps": ["LO-G3-0954"],
      "alignments": [
        {"framework_code": "CAM-PRI-MAT-0096", "statement_code": "3Np.01", "relation": "meets", "reason": "…"}
      ],
      "no_ncf_reason": null,
      "no_cambridge_reason": null,
      "what_we_say": "Reads, writes and …",
      "capability": {"primary": "knowledge-and-academic-mastery", "secondary": null},
      "skill_sets": []
    }
  ],
  "outcome": {"text": "…"},
  "descriptors": [{"level_code": "BEGINNING", "text": "…"}],
  "not_covered": [
    {"framework_code": "…", "statement_code": "…", "proposal": "add_to", "lo_code": "…", "reason": "…"},
    {"framework_code": "…", "statement_code": "…", "proposal": "new", "what_we_say": "…", "reason": "…"}
  ]
}
```

`proposal` is `add_to` (with the objective it joins), `new` (with the new objective's sentence) or `leave_out`
(with the reason).
