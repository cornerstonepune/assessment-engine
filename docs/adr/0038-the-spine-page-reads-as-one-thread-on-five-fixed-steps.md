# 0038 — The spine page reads as one thread on five fixed steps

Date: 2026-09-28
Goal: goals/spine-readable.yaml
Status: **accepted** for the page; the plan it shows stays a proposal (`docs/spine/plan_design.json`).
Source: `research/spine_links.py`, `research/spine_steps.py`, `research/spine_thread.py` (the threads),
`research/plan_build.py` (the plan's numbers), `research/spine_page.py` with `research/spine_page.html`,
`research/spine_view.js` and `research/spine_plan.js` (the page).

## Context

Nimish, on the spine page: "is there a way that you can design this html better such that its more easily understood
and the connections are untuitive - i am getting lost in the artifact".

The page had four tabs over one graph of 2,504 items and 13,439 links. The Map, Tree and By grade tabs were three
ways into the same graph, and the Plan tab showed the syllabus in time. A click showed one item's direct links, as
lists named by the link's own word ("fed by", "is evidence of", "sets"). The next click replaced the whole screen. A
capability showed 337 competencies. Nothing on screen said where the reader was in the chain from the child the school
wants to a fortnight's teaching. The Plan tab was the one place that chain reached time, and it sat apart from the
graph.

## Decision

- **Five steps that never move.** Why (the capabilities, and the words they show), what NCF-SE asks (competencies
  under their curricular goals), in the grade (NCERT's outcomes and the school's units), when (the plan's fortnights)
  and how we check (the engine's skills and rungs).
- **Any item shows its thread through all five.** The item sits on its own step; everything else it reaches fills the
  others. A unit taught in several grades has a thread per grade.
- **Every group of links says where it comes from.** NCF-SE or NCERT, the school's map, a proposal nobody has signed,
  or an inference: a unit and an outcome of the same grade that serve the same competency. A path is only as strong as
  its weakest link.
- **The threads and every number are worked out in Python and tested.** That covers pacing, hours and the day by mode
  (`packages/engine/tests/test_spine_page.py`). The page's scripts only draw.
- **A grade's year is a grid of fortnights by subjects, filled with the units' own names**, not counts. Any unit in it
  opens its thread, and a thread's fortnights open the year with its units marked.
- **The school day across grades shows five parts.** They are academic, studio, arts, sport, and circle and close. The
  three parts of an academic hour have their own chart. They are the same in every grade of a stage, so repeating them
  in each grade's bar added nothing.

## Rejected

- **Keep the explorer and refine it.** A hub with its direct links cannot show a path, and a path is what Nimish was
  missing.
- **Column browsing (each column filtered by the one before).** It reads well for trees. The spine is many-to-many,
  though: an outcome serves several competencies and a competency feeds several capabilities. The columns would show
  one arbitrary path and hide the rest.
- **Working the threads out in the browser.** The page would be smaller, but the links would go untested. The page
  carries each item's place in a list instead of its id, which keeps it near its old size (2.5 MB against 2.3 MB).
- **Seven colours in the day chart.** The dark-mode palette failed the colour-vision check: arts and studio were
  ΔE 1.6 apart for deuteranopes. No three blues pass in dark mode. The fix is five parts, validated in both themes.

## Consequences

- A reader always sees where an item sits between "why" and "how we check". Its fortnights and its source are on the
  same screen.
- The page opens on one worked thread, Grade 3's addition and subtraction, which reaches all five steps. The test
  fails if that thread disappears.
- 31 of the 637 items the plan places reach no capability: 30 units and 1 NCERT outcome. All of them are routines
  or inputs, such as Home Period, Science Week, the fortnightly maths quiz and a visit to a language laboratory. Each
  thread says why, and the year shows them dashed.
