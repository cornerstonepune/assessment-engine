# Brief for the crosswalk seats — the school's spine, Levels 3 to 5

Cornerstone (Pune, Nursery to Grade 10, English medium, Marathi and Hindi taught) describes its graduate in three words,
capable, kind, unafraid, and eight capabilities. Under the capabilities sit 204 observable behaviours (done). Under those,
the subject layer: the competencies India's NCF-SE 2023 sets per subject per stage, the grade-wise outcomes NCERT sets
per class, and the school's own units and skills. Your job is the connections between these, as data a program can check.

Files (JSON), all in /tmp/claude-0/-home-user-assessment-engine/d7e26dee-8cf8-540f-b08a-b0d73dec61fc/scratchpad/:

- `capabilities.json`: the eight capabilities, each with id, name and the profile's "observable at 16" sentence.
- `ncf_competencies.json`: 765 rows from NCF-SE 2023. Fields: id (e.g. `ncf.math.P.C-1.1`), kind (CG = curricular goal,
  C = competency under a goal), subject, area (R1/R2/R3 for languages; visual/theatre/music/dance for art), stage
  (foundational = Nursery to Grade 2; preparatory = Grades 3–5; middle = 6–8; secondary = 9–10), code, text, and for a C its
  parent `cg`. Read only your subject's rows.
- `ncert/ncert_lo.json`: 700-odd grade-wise learning outcomes from NCERT's two documents (Elementary Stage 2017, Classes 1–8;
  Secondary Stage 2019, Classes 9–10). Fields: id (e.g. `ncert.math.3.05`), subject (math, evs, sci, sst, eng, hpe, art),
  class (1–10), text. Read only your subject's rows.
- `school_units.json`: 439 units of the school's own learning-objective map for Grades 1–4 (fields: id, subject, unit, bands,
  n = number of objectives, samples = up to three objective titles). Read only your subject's rows.

Stages and grades: foundational → N, K1, K2, G1, G2 (the school's names: Nursery, Junior KG, Senior KG, Grade 1, Grade 2);
preparatory → G3, G4, G5; middle → G6, G7, G8; secondary → G9, G10.

## What to write, exactly

One JSON file at the path your instructions give:

```
{
 "seat": "<your subject>",
 "competency_capabilities": [ {"id": "<ncf id>", "capabilities": ["<capability id>", ...]} ],   # every C and CG row of your subject; 1 to 3 capabilities each, the first the strongest
 "competency_grades": [ {"id": "<ncf id>", "grades": ["G3", ...], "ncert": ["<ncert id>", ...]} ],   # every C row: the grades within its stage where a child would show it, and the NCERT outcomes that evidence it (may be empty)
 "ncert_competencies": [ {"id": "<ncert id>", "competencies": ["<ncf id>", ...]} ],   # every NCERT outcome of your subject: the NCF competencies (C rows) it evidences; 1 to 3; use [] only with a "why"
 "unit_competencies": [ {"id": "<unit id>", "competencies": ["<ncf id>", ...], "why": "<only when the list is empty>"} ],   # every school unit of your subject
 "notes": ["<at most five one-line notes for the founders: where the sources disagree, what is missing, what you were unsure of>"]
}
```

Rules:
- Use ids exactly as they appear in the files. A program rejects unknown ids, grades outside the row's stage, and any row of
  yours left out.
- Judge by the text, not by the number. A grade allocation says where a child would first be expected to show it, and where it
  continues; a competency may span all grades of its stage.
- For Grades 1–2 (the school's units in bands G1 and G2), the NCF rows are the foundational-stage ones (`ncf.fnd.F.*`), which
  are organised by domain (Cognitive Development, Language and Literacy Development, and so on), not by subject; use them.
- Prefer the C rows as targets; name a CG only when no C fits.
- Where a school unit is not a subject at all (a weekly routine, a field visit, a celebration), say so in "why".
- Do not invent competencies, outcomes or units. Do not modify any file under /home/user/assessment-engine or in the
  scratchpad other than your own output file.
