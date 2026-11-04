# M1-16 — one consolidated materials list for the school (design note; step 1: goal, failing tests, design, cost)

**Gate:** W2, step N4 (files added to the step, as M1-10; no thirteenth step). `workflows.json` changes in the first commit of the build. Goal: `goals/m1-16-materials-consolidated.yaml`. **No code, no migration, no model call, no spend in this step.** Depends on M1-10 (merged) and M1-11 (merged). Card and decisions D-071, D-072, D-074 are the orchestrator's relay; teacher-os was not readable here.

## What is reused (checked in the repository today)
- M1-10's per-class lists, with their edits and sources (`materials_list`, `materials_line`, `materials_line_edit`, `materials_line_source`), `materials_text` (checklist, wa.me link) and the send pattern of `materials_send`.
- `llm.generate`: the prompt is a row, takes images, checks its JSON schema, leaves a `flow_run` with its cost. `llm_budget`: a campaign (`llm.campaigns`) refuses a call before it is made once its cap less margin is spent. `llm.prices`: Haiku 4.5 is ₹88 in / ₹440 out per million tokens.
- Not reusable as is: `materials_send` (it points at one class's list); the campaign cap (it adds up spend over all time, not a month).

## What gets built (after a go)
1. **Consolidation** (`materials_consolidate`, code only): for a month, every class's live lines (not removed, needed in the month) summed per catalogue item and unit; each line keeps which classes, activities and quantities it comes from. If any class gives no quantity the total is unknown and says "quantity to confirm", never a smaller number. Each build is kept; the next build against the last gives the **changes** (quantity changed, line added, line removed), who and when from `materials_line_edit`.
2. **Reading a free-text or photographed request** (`materials_intake`): the model gets the note and the catalogue (code, name, unit) and nothing else, and answers `{people_visible, readings:[{text, item_code, quantity, unit}]}`. **Code decides.** A reading is confirmed only if: the item code is in the catalogue; the quantity is a number above zero **that appears in the note's own text** (so "2 dozen" read as 24 is not confirmed: code does not convert); the unit is the catalogue's unit (code does not convert). Anything else goes to a person (`materials_note_review`, state `needs_person`) and never into the list. A confirmed reading becomes a line on that class's list through the existing `add`, so it is kept as her change.
3. **Send to the one inventory person** (`materials_inventory`): a structured checklist, one line per item with total, unit and where from; a line changed since the last send says "changed: was 2, now 6". The link opens WhatsApp to the number in the setting `materials.inventory_whatsapp_to` (empty until named); `materials_consolidated_send` records the text, who and when (append-only). Delivery cannot be known (D-071).
4. **A monthly cap**: `llm_budget` learns `"window": "month"` on a campaign row (the school's calendar month), so `llm.campaigns` gets `m1-16` with purpose `materials_read` and a cap that is a setting. This touches shared code, so it is its own small change with the tests in `test_llm_budget_monthly.py`.
5. Migration (one, additive, after 20270102090000): `materials_consolidated`, `…_line`, `…_line_source`, `…_change`, `materials_consolidated_send`, `materials_note_review`. Prompt row `materials_read`, inactive until `engine eval materials_read` meets a bar fixed before the first run (rules 2 and 7); model class: the cheapest that passes it (Haiku-class to start).

## Photographs: what I can and cannot guarantee
I **cannot** guarantee no child is ever in a photo; no software can. What the design does: (1) the picture goes in through the educator's own materials page, labelled as a note of materials; (2) the model sees the image and the catalogue only, never a name (rule 6; tested: the call's variables are exactly `note` and `catalogue`); (3) the same call must say whether any person is visible; if it says yes, or does not say, nothing is read and the whole note goes to a person (tested); (4) **the picture is read in memory during the request and never written to disk, a log or git**, so there is nothing to keep, leak or delete later; a failed read means she sends it again. Residual risk: the model misses a person. The person who reviews the page is the last check.

## Cost per month (an ESTIMATE; every token count is an assumption, none measured)
Prices from `llm.prices` (Haiku 4.5, ₹88/₹440 per million, ₹88 to the dollar). Per call I assumed 600 tokens of instructions, 100 for the note, 12 per catalogue item, 1,500 for one photo, 150 out for text and 250 for a photo, 25% of notes photographed, 1.3× for retries.
| Case | Notes a month | Catalogue items | Tokens in / out | Cost |
|---|---|---|---|---|
| low | 20 | 150 | 75,000 / 4,600 | ₹9 (≈ $0.10) |
| middle | 40 | 300 | 243,000 / 9,100 | ₹25 (≈ $0.29) |
| high | 80 | 600 | 861,000 / 18,200 | ₹84 (≈ $0.95) |
The catalogue in the prompt is nearly all of the input; nothing here uses prompt caching. One-off eval (about 200 note-sized calls over two runs): ₹127 (≈ $1.44), its own stage. **Proposed monthly cap: $2 (₹176)**, above the high case; the figure is Nimish's to set, in the config row. Not known: how many notes a month, the real catalogue size, real token counts. They are measured on the first 20 real notes before the cap is trusted.

## What I need from people (real data, D-028; nothing is invented)
1. Two or more classes' real materials requests for one month, **including one handwritten note photographed** (a staff note, no child in it).
2. The inventory person's own list for the same month, written by hand before the system's is shown.
3. The inventory person's WhatsApp number, for `materials.inventory_whatsapp_to`.
4. A person to mark about 100 note lines (item, quantity, unit) as the gold set for `engine eval materials_read`.
5. Nimish: the monthly cap; and yes or no to "the photograph is never stored".
6. Where the free text is typed (4b's page): a box under the class's list, and a photo button.

## Open / not verified
- The tests are a specification and **fail until the code exists** (three modules are missing; the monthly window is not built). `test_llm_budget_monthly.py` fails on one test now, for the right reason (last month's spend counts); its other two pass today as guards.
- Nothing about real notes, real catalogue size or real tokens has been measured. No model was called.
- A month's consolidated list needs the classes' lists to exist; today only a class that built one has one (M1-06's loader, M1-05's mapping).

## Verified
- `bin/engine promises` → `every promise has its command`. `bin/check` → `34 passed` (with the goal file and the failing tests present).
- The new tests fail as specified: `test_materials_consolidate.py`, `test_materials_intake.py` and `test_materials_inventory.py` stop at `ImportError: cannot import name 'materials_…'`; `test_llm_budget_monthly.py` → `1 failed, 2 passed` (`Refused … $5.68 spent` on last month's call). Ruff clean.

## Handoff
- Next on a go: workflows.json step, then the code to make the tests pass, the migration, the prompt row and eval, in that order. Branch `m1-16-materials-consolidated`, local until the orchestrator says push.
