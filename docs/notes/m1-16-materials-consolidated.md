# M1-16 — one consolidated materials list for the school (design note and build record)

**Gate:** W2, step N4 (files added to the step in `workflows.json`, as M1-10; no thirteenth step). Goal: `goals/m1-16-materials-consolidated.yaml`. **Built 4 Nov after the orchestrator's go; no model call and no spend.** Depends on M1-10 (merged) and M1-11 (merged). Card and decisions D-071, D-072, D-074 are the orchestrator's relay; teacher-os was not readable here.

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
I **cannot** guarantee no child is ever in a photo; no software can. What is built: (1) the picture goes in through the educator's own materials page; that page must tell staff to **photograph the note only** (4b's, in a later PR); (2) the model sees the image and the catalogue only, never a name (rule 6; tested: the call's variables are exactly `note` and `catalogue`); (3) the same call must say whether any person is visible; **a "yes" or a missing answer sends the whole note to a person** and nothing is read (tested both ways); (4) the picture is re-encoded to a plain JPEG at a size from a setting (`materials.photo_max_side`), which also drops its location and other embedded data, **read in memory and never written to disk, a log or git** (the route holds it only for the request); a failed read means she sends it again. **The model's own answer about people is a second safety, not a guarantee: its reliability is unverified and is to be checked on the gold set** before the prompt is made active. Residual risk: the model misses a person; the person who reviews is the last check.
**A weaker check for photographs, plainly.** For a typed note code checks the quantity against the staff's own words. A photograph has no typed words, so the number is checked only against the model's own copy of what it read: a misread "10" as "40" passes that check. The gold set and the review are what catch it, and `confirmed_wrong` is the measure that matters.

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

## Settings added (rows in `supabase/seed/config.json`)
`materials.inventory_whatsapp_to` (empty until named), `materials.consolidate_roles` (coordinator, head), `materials.photo_max_side` (1600), `materials.photo_max_bytes` (10,000,000), and the campaign `m1-16` in `llm.campaigns` (purpose `materials_read`, cap $2, margin $0.25, `"window": "month"`). The eval's spend counts inside the month's cap, so run it in a month with room or raise the cap for it by a pull request.

## The eval and its bars (on record as rows; PROPOSED, to be confirmed or changed before the first run)
`engine eval materials_read` runs the model on marked cases and passes each answer through the same check the engine uses (one `ask_model` for both). Measures and the rows in `supabase/seed/thresholds.json`: `confirmed_wrong_at_most` **0** (a count: readings code confirmed that a person did not mark; nothing wrong may go into a list), `found` at least **0.80** (of the items a person marked, the share confirmed), `held_back_right` at least **0.95** (of the cases that should go to a person, the share where nothing was confirmed). The repo requires every eval to have bars on record, so I wrote them as the builder's proposal and said so in each row's description; the orchestrator and Nimish confirm or change them in a pull request before the first run. With an empty gold set the eval refuses before any model call.

## Open / not verified
- **No model has been called and nothing has been spent**; every test uses a fake. The prompt `materials_read` v1 is **inactive**. Nothing about real notes, the real catalogue size or real token counts is measured.
- **No page exists** for the free-text box, the photo button, the coordinator's list or the review of `materials_note_review` rows: a row waiting for a person has nowhere to be cleared yet (4b, next).
- The scenario S-M1-16 (a real month, one handwritten note, the inventory person's own list) needs real data from people and has not been run.
- The photo route takes the file through the site, which has about a 4.5 MB limit through Vercel; a phone photo may need shrinking in the browser first (the engine accepts up to the setting above).
- A month's list needs the classes' lists to exist; today only a class that built one has one (M1-06's loader, M1-05's mapping).
- Two lists of one class that overlap (a week inside a fortnight) are not both counted: the widest is kept and the skipped ones are named in the result.

## Verified
- The specification tests now pass: consolidation (6), reading checked by code (including a person visible, and a missing answer), the send (3), the monthly window (3), the eval (2), the routes (7). `bin/check` → `34 passed`. Ruff and pyright clean. The existing `llm_budget` tests still pass (48 with `test_llm`).
- Whole suite in 12 shards: see the end of this section once run (not claimed yet).

## Handoff
- **Migration `20270104090000_materials_consolidated.sql`: do not push until the orchestrator says main has M1-15's `20270103090000`.** Then rebase, regenerate `rules.json` and `apps/web/lib/engine-routes.ts` on top, re-run the 12 shards, rehearse-update-live on the pushed branch.
- Needs from people: see "What I need from people" above. Next: 4b's page, the gold set, then `engine eval materials_read`, then a go to make the prompt active.
