# ADR 0085 — A state's rules are its columns, and the subject comes from the skill's topic

**Status:** accepted (2026-10-20).
Goal: goals/b0d-states-and-subject-from-tables.yaml

## What happened

B0a (ADR 0084) made `child_state` — each of the graph's six states with its order, words, colour and whether a next
paper works on it — and nothing read it. The states were lists in eleven website files and five engine files, and each
list was a rule: which states a next paper works on, which wait on too few answers, which are strong, how the children
table takes a skill set's worst skill, which are ready to move up, which may be nearly secure, how Friday's card groups
children, and the reason a paper prints (with "four in five" and "half" written out beside the threshold rows that say
0.8 and 0.5). Prescriptions were stamped `'NUM'`, the registry's skills filtered to `domain = 'NUM'`, and three
headings said "Maths". Nimish, 2026-10-20: "we need proper tables".

## Decision

- **Every rule about a state is a column of its row.** `child_state` gains `enough` (false for the one state of too few
  answers: a unique index allows only one), `severity` (the children table counts a skill set as its most severe
  skill), `move_up`, `nearly`, `card_group` and `why` (the reason a paper prints; `{next_sheet.promote_at}` in it is
  that threshold said in words, so "four in five" follows the row). Each was set to what the list it replaces said,
  and `tests/test_states_and_subject.py` holds those lists, copied from main, against the rows.
- **A colour's words are rows too.** `state_colour` (red, amber, green, grey) holds the words a key says
  (`words`: "got it") and a count says (`count_words`: "3 secure"); a state's colour is a key into it. The tone each
  colour is drawn in stays in `lib/rag.ts`: it is styling, and a fifth colour needs a style anyway.
- **The subject comes from the skill's topic**: skill_set → topic → subject. A prescription's strand is its skill set's
  topic's subject; the headings read `subject.label` ("Maths"; a subject without one is said by its name) of the skill
  sets the page is about; the parent letter's check allows the label's words.
- **The maths library stays pure.** `assess/focus.py` takes the lagging states in its `rule`, which `shelf.rule` reads
  from the rows, as it already took the stretch levels.
- **A test fails if any file names a state or a subject**: a state's code quoted, or (with an underscore, which no
  English word has) anywhere outside a comment; a subject's code quoted; "Maths" or "Mathematics" anywhere outside a
  comment. Tests, migrations and the seed are where the rows are written and are not scanned. The engineering map
  (`/workflows`) is exempt: it says which of the engine's steps are maths only, a fact about the code.

## Rejected

- **Deriving the rules from `ord` and `colour`.** "Severity" is not the order: the children table ranks too few answers
  between amber and green, the card and the report rank it last. And reading green as "strong" makes a display colour
  decide the engine's rules; a column says what it means.
- **Redefining B0a's `internal.school_vocabulary`** to write the new columns. B0b and B0c run beside this and may
  redefine it; whichever migration ran last would silently drop the others' change. Instead the new columns have
  defaults (Postgres checks NOT NULL before ON CONFLICT, so B0a's insert needs them), and `internal.school_states`,
  fired first by name, writes a new school's colours and whole states.
- **A subject in the parent report's facts.** The facts are the model's input; adding to them changes what the model
  is given without an eval (rule 7). The letter's page reads the subject from the skill sets the facts name instead.
