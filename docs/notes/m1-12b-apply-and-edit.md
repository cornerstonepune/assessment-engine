# m1-12b: apply a re-draft, keep the lists, and the staff routes (W1, gate N1)

## Verified
- `su postgres -c "… pytest -q tests/test_k2_page.py tests/api/test_k2_page_routes.py tests/test_k2_review.py tests/test_k2_draft.py"` against the local copy → all pass (the copy has the new migration applied by hand). Nothing is applied live; no model call.

## What changed
- Migration `20270106090000_k2_part_lists.sql` (additive): `activity.steps_list` (jsonb array) and `activity.thinking_doc` (jsonb object). The text columns are unchanged and are what the lists read as; a list is used only while it renders to its text.
- `apply` writes a drafted part where it is empty OR where a machine drafted it earlier (never the school's, never a person's), with its list. A page's older draft waiting for a person is set aside (a `rejected` row: "superseded by a newer draft of this page") and never written over a newer one. `revert` and a person's reject empty the lists too.
- `k2_review.change` takes text, a list (steps) or an idea with slips (thinking); the text beside is written from it.
- Routes (staff only, engine key + the signed-in email as `actor`): `POST /curriculum/page/read | confirm | revert | edit`. Contract regenerated.

## The data shape the screens read (POST /curriculum/page/read {actor, code})
```
{ code, name, section,
  parts: [ { part: objective|steps|thinking|level_0..level_3,
             kind: "bullets" (steps) | "thinking" | "text",
             source: "school" | "drafted" | "person" | ""  (empty when the part has no words),
             check_me: bool,           // true while a draft awaits a person
             text: str,                // always the column's words, for a plain view or an editor
             items: [str],             // steps only: one bullet each (also for the school's own steps)
             idea: str | null,         // thinking only, when a draft's list is current; null for the school's prose
             slips: [ {keyword, spot} ] } ],   // keyword is highlighted; spot is how to see it
  materials: { text: str,              // the school's own words
               items: [ {name, quantity|null, unit} ] },   // once the materials stage has run
  draft: null | { maker, checker, verdict: "agree"|"disagree"|"", reason, status, history: [ {round, verdict, faults:[{part, reason}]} | {round, note} ] } }
```
Answers: `confirm {actor, code, part}` and `revert {actor, code, part}` return the same page; `edit {actor, code, part, text | items | idea+slips}` too. 409 "not a drafted part" (the school's or a person's words), 422 a malformed edit, 403 not on the staff list, 404 no such activity.

## Apply, per part (orchestrator, 2026-11-05)
- `apply` decides what is newer for each PART of each page, not for the page. A draft that is not the newest for any of its parts is set aside (a `rejected` row: "every part of it is covered by a newer draft of this page, or by a part a person approved"); one that is newest for some writes only those parts. A draft a person turned down, or that is applied or taken back, is not newer. A draft a person approved is not buried by a newer one nobody has read: the approved part is written, and the newer draft writes the parts it alone covers.

## Switches
- The page routes do not look at the educator or voice switches. Acceptable for now: they are behind the engine key and a signed-in staff check. They go behind the shared `educator.preview_roles` helper when the 4b session lands it.

## Handoff
- Not mine: the bullets-with-highlights screen and the offered-skills review screen (the orchestrator asked for the data shape only).
- Next: a measured forecast command; skill links with offered skills; then the dispatches are the orchestrator's.
