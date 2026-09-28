#!/usr/bin/env python3
"""The official numbers behind the indicative timetable (docs/brainstorms/2026-09-28-indicative-timetable.html). Each
number is quoted from its document and the quote is looked up, word for word, on the page it cites. The official
outcome counts per grade and subject come from docs/spine/sources/, which research/spine_verify.py has checked. The
result is written into the page's data block. The timetable itself is the school's proposal and lives in the page.
No model is called.

python3 research/timetable_data.py      # fetches NCF-SE if needed; exit 1 if any quote is not on its page
"""

import collections
import json
import re
import sys
from pathlib import Path

import pymupdf
from spine_sources import DATA, fetch
from spine_verify import norm

R = Path(__file__).resolve().parents[1]
PAGE = R / "docs/brainstorms/2026-09-28-indicative-timetable.html"
ROWS = R / "docs/spine/sources"
PROFILE = R / "docs/sources/cornerstone-graduate-profile.pdf"
TITLES = {
    "ncf": "NCF-SE 2023 (NCERT), Part A, Chapter 4",
    "elementary": "NCERT, Learning Outcomes at the Elementary Stage (2017)",
    "profile": "Cornerstone graduate profile (the school's own design document, September 2026)",
}
PRINTED = {
    "ncf": -14,
    "elementary": None,
    "profile": None,
}  # NCF-SE Part A prints page = PDF page - 14


def table(rows):
    """A table's rows as the words the PDF prints: name, annual hours, annual periods."""
    return " ".join(f"{name} {hours} {periods}" for name, _, hours, periods in rows)


PREP = [
    ("R1+Library", "R1", 180, "270"),
    ("R2", "R2", 190, "285"),
    ("Mathematics (Maths)", "Maths", 185, "277.5"),
    ("The World Around Us (TWAU)", "TWAU", 200, "300"),
    ("Art Education (Art)", "Art", 100, "150"),
    ("Physical Education (PE)", "PE", 100, "150"),
]
MIDDLE = [
    ("R1+Library", "R1", 65, "97.5"),
    ("R2", "R2", 70, "105"),
    ("R3", "R3", 75, "112.5"),
    ("Mathematics (Maths)", "Maths", 115, "172.5"),
    ("Science", "Science", 160, "240"),
    ("Social Science (SS)", "SS", 160, "240"),
    ("Art Education (Art)", "Art", 100, "150"),
    ("Physical Education (PE)", "PE", 100, "150"),
    ("Vocational Education (VE)", "VE", 110, "165"),
]
# key, document, PDF page, the words, and the numbers the page takes from them
OFFICIAL = [
    (
        "illustrative",
        "ncf",
        126,
        "The specific time allocations described in this section must be seen as illustrative, and the actual time allocations must be conducted by schools, in accordance with their contexts",
        {},
    ),
    (
        "hours_are_schools_call",
        "ncf",
        127,
        "The actual decision on the exact number of working hours would be taken by schools or school systems, and the proportion and rhythm of the illustrative timetable in the NCF could still be held",
        {},
    ),
    (
        "art_pe_ve_need_time",
        "ncf",
        127,
        "In this NCF, they need explicit and significant time allocation",
        {},
    ),
    (
        "foundational_minutes",
        "ncf",
        129,
        "R1 would need 90 minutes every day and R2 would need 60 minutes. Mathematics and numeracy would require 60 minutes a day",
        {"R1": 90, "R2": 60, "Maths": 60},
    ),
    (
        "working_days",
        "ncf",
        130,
        "The annual working year, for schools, has 220 instruction or school-going days after taking into consideration national holidays, term breaks and vacations",
        {"days": 220},
    ),
    (
        "assessment_days",
        "ncf",
        130,
        "Of these 220 days, around 20 days may be considered for assessments and other assessment-related activities across stages",
        {"days": 20},
    ),
    (
        "event_days",
        "ncf",
        130,
        "Another 20 days may be set aside for school events and other similar activities",
        {"days": 20},
    ),
    (
        "instruction_days",
        "ncf",
        131,
        "a safe estimate can be of 180 days of instruction time across these three stages at school",
        {"days": 180},
    ),
    (
        "saturdays",
        "ncf",
        131,
        "the model here has considered five and a half days of school every alternate week only",
        {},
    ),
    (
        "weeks_hours",
        "ncf",
        131,
        "a working school year would have around 34 working weeks of around 29 hours of instruction hours every week",
        {"weeks": 34, "hours_per_week": 29},
    ),
    (
        "period_minutes",
        "ncf",
        131,
        "Class time for all subjects is 40 minutes. Some subjects will require a block period of 80 minutes",
        {"period": 40, "block": 80},
    ),
    (
        "breaks",
        "ncf",
        131,
        "A snack break of 15 minutes and a lunch break of 45 minutes has been built in",
        {"snack": 15, "lunch": 45},
    ),
    (
        "r1_across_subjects",
        "ncf",
        131,
        "all other Curricular Areas are taught in the language of R1 and so add to the learning of R1",
        {},
    ),
    (
        "prep_hours",
        "ncf",
        132,
        table(PREP),
        {short: hours for _, short, hours, _ in PREP},
    ),
    (
        "middle_hours",
        "ncf",
        134,
        table(MIDDLE),
        {short: hours for _, short, hours, _ in MIDDLE},
    ),
    (
        "bagless_days",
        "ncf",
        135,
        "provisions be made in the annual calendar of schools for ten bagless days in the Middle and Secondary Stages",
        {"days": 10},
    ),
    (
        "no_science_grades_1_2",
        "elementary",
        93,
        "in classes III to V, it is introduced as a separate curricular area and in I and II, the related concerns are integrated with language and mathematics",
        {},
    ),
    (
        "periods_projects",
        "profile",
        3,
        "Periods build capability. Projects integrate capability.",
        {},
    ),
    (
        "mastery_time",
        "profile",
        3,
        "protect dedicated mastery time for mathematics, sciences, languages, literature, history, geography and other required disciplines while deliberately creating time for interdisciplinary application",
        {},
    ),
    (
        "arc_1_2",
        "profile",
        3,
        "Grades 1–2 — DISCOVER: curiosity, language, numeracy, observation, imagination, physical and social foundations",
        {},
    ),
    (
        "arc_3_5",
        "profile",
        3,
        "Grades 3–5 — INVESTIGATE: research, measurement, evidence, structured writing, experimentation and collaboration",
        {},
    ),
    (
        "arc_6_8",
        "profile",
        3,
        "Grades 6–8 — APPLY: deeper disciplines plus coding, AI literacy, design, economics, debate and increasingly ambiguous real-world problems",
        {},
    ),
]


def counts():
    lo = json.load(open(ROWS / "ncert_learning_outcomes.json"))
    per = collections.defaultdict(dict)
    for (subject, grade), n in collections.Counter(
        (r["subject"], r["class"]) for r in lo
    ).items():
        if grade <= 7:
            per[grade][subject] = n
    ncf = json.load(open(ROWS / "ncf_se_2023_competencies.json"))
    comp = collections.Counter(
        (e["stage"], e["subject"]) for e in ncf if e["kind"] == "C"
    )
    stages = collections.defaultdict(dict)
    for (stage, subject), n in comp.items():
        if stage in ("foundational", "preparatory", "middle"):
            stages[stage][subject] = n
    return {
        "ncert_outcomes": {
            str(g): dict(sorted(v.items())) for g, v in sorted(per.items())
        },
        "ncf_competencies": stages,
    }


def verified():
    """The official numbers whose quotes are found on their cited page, and the keys of any that are not."""
    paths = fetch()
    docs = {
        "ncf": pymupdf.open(DATA / "ncf.pdf"),
        "elementary": pymupdf.open(paths["elementary"]),
        "profile": pymupdf.open(PROFILE),
    }
    official, missing = [], []
    for key, doc, page, quote, value in OFFICIAL:
        if norm(quote) not in norm(docs[doc][page - 1].get_text()):
            missing.append(key)
            continue
        shift = PRINTED[doc]
        official.append(
            {
                "key": key,
                "doc": TITLES[doc],
                "pdf_page": page,
                "printed_page": page + shift if shift else None,
                "quote": quote,
                "value": value,
            }
        )
    return {o["key"]: o for o in official}, missing


def main():
    official, missing = verified()
    out = {
        "official": official,
        "counts": counts(),
        "checked": f"{len(official)}/{len(OFFICIAL)} quotes found word for word on their cited page",
    }
    print(out["checked"])
    for key in missing:
        print("   not found:", key)
    html = PAGE.read_text(encoding="utf-8")
    block = json.dumps(out, ensure_ascii=False, indent=1).replace("</", "<\\/")
    html, n = re.subn(
        r'(<script id="official" type="application/json">).*?(</script>)',
        lambda m: m.group(1) + "\n" + block + "\n" + m.group(2),
        html,
        flags=re.S,
    )
    if n != 1:
        raise SystemExit(f"{PAGE.name} has no official data block")
    PAGE.write_text(html, encoding="utf-8")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
