"""W3 — a paper that is not on the add/sub ladder, placed against the skill registry.

Nimish, 2026-09-20: "I don't want us to move outside of the skill framework. For Olympiad questions
or any such external questions that come in, the nature of the question will map itself to a skill
70%, 80%, or 90% of the time. If it doesn't, we need to have an engine that builds a skill out of
it." The percentage was a guess and this module exists to replace it with a measurement: the
registry holds 244 skills, the corpus holds real Olympiad papers, and the mapping rate is countable
rather than arguable.

Two stages on purpose. Reading a printed page is vision and expensive; matching a described question
to a 244-row taxonomy is text and cheap. Splitting them means the registry can grow and the match
re-runs for nothing, without re-reading a single page (ADR 0017's whole point: naming a skill later
must place evidence already held).

Nothing here writes evidence or invents a skill. It reads printed questions and reports where they
land, which is the input to a person's decision, not a substitute for it.
"""

import hashlib
import json

from engine import db, render_pdf
from engine.adapters import llm
from engine.legacy import _jpeg, mask_name_band

CONFIDENCE = ("clear", "arguable", "none")


def registry(conn):
    """Every skill the school has a name for, as the matcher sees it."""
    return conn.execute(
        "select s.code, s.name, s.domain, s.strand, d.name as domain_name"
        " from skill s left join domain d on d.code = s.domain order by s.code"
    ).fetchall()


def _registry_text(rows):
    return "\n".join(f"{r['code']} | {r['domain_name'] or r['domain']} | {r['name']}" for r in rows)


# A paper's name band sits on its first page, so that is the page masked by default. Measured on the
# SOF booklets: the cover carries the child's handwritten name, the roll number and the educator's
# score in the top third, and nothing else — no printed question is lost to the mask. Masking is a
# default rather than a flag because the first run of this module sent a cover unmasked and put a
# child's name in front of a model, which rule 6 forbids. A caller who genuinely wants the whole page
# passes mask=0 and says so.
FIRST_PAGE_MASK = 0.34


def extract_questions(conn, path, pages=None, mask=None):
    """One paper → its printed questions, page by page. No child's answer and no educator's mark is
    read, so one booklet stands for every child who sat that form.

    Returns (questions, conflicts). A conflict is the same (n, part) read from two different pages —
    which means one of the two is invented, and the run says so rather than quietly keeping both.
    A cover page that yields a question is exactly this, and it is not detectable any other way.
    """
    mask = FIRST_PAGE_MASK if mask is None else mask
    by_page = {}
    images = render_pdf.render(path) if str(path).lower().endswith(".pdf") else []
    for page_no, image in enumerate(images, 1):
        if pages and page_no not in pages:
            continue
        jpeg = mask_name_band(_jpeg(image), mask if page_no == 1 else 0)
        got = llm.generate(conn, "question_extract", {}, images=[jpeg])
        by_page[page_no] = got["questions"]

    return resolve(by_page)


def resolve(by_page):
    """{page: [question]} → (questions, conflicts), with each (n, part) kept once.

    A page that holds real questions holds a run of them. Measured on both SOF forms: the cover
    yields exactly one spurious question — invented outright, on a page whose only text is a title
    and a name band — while every question page yields three to nine. So when one (n, part) is read
    from two pages, the page with more questions on it is the one that actually prints it. Keeping
    the *first* occurrence instead, which is the obvious thing, threw away the real question 18 and
    kept the cover's invention.
    """
    kept, seen, conflicts = [], {}, []
    for page_no in sorted(by_page, key=lambda p: (-len(by_page[p]), p)):
        for q in by_page[page_no]:
            key = (q["n"], q.get("part", ""))
            if key in seen:
                conflicts.append(
                    {"n": q["n"], "part": q.get("part", ""), "kept": seen[key], "dropped": page_no}
                )
                continue
            seen[key] = page_no
            kept.append({**q, "page": page_no})   # the dict key is the authority, never a caller's field
    kept.sort(key=lambda q: (q["page"], q["n"], q.get("part", "")))
    return kept, conflicts


def match_skills(conn, questions, chunk=25):
    """Described questions → registry codes. Text only, so re-running after the registry grows costs
    a fraction of a rupee and no page is read again."""
    skills = _registry_text(registry(conn))
    matches = []
    for i in range(0, len(questions), chunk):
        batch = questions[i : i + chunk]
        asked = json.dumps(
            [
                {
                    "n": f"{q['n']}{q.get('part', '')}",
                    "question": q["question_as_printed"],
                    "tests": q["what_it_tests"],
                }
                for q in batch
            ],
            ensure_ascii=False,
        )
        got = llm.generate(conn, "skill_match", {"skills": skills, "questions": asked})
        matches.extend(got["matches"])
    return matches


def rate(matches):
    """The number the whole module exists for: how much of a paper the registry already covers."""
    n = len(matches) or 1
    counts = {c: sum(1 for m in matches if m["confidence"] == c) for c in CONFIDENCE}
    return {
        **counts,
        "total": len(matches),
        "mapped": round((counts["clear"] + counts["arguable"]) / n, 3),
        "clear_only": round(counts["clear"] / n, 3),
    }


def unmatched_groups(matches):
    """What the registry is missing, grouped by the name the engine proposed — one cluster is a
    candidate skill, a single stray is not (a skill per question would split a child's evidence
    across near-duplicates until none of them reaches `state.min_events`)."""
    groups = {}
    for m in matches:
        if m["confidence"] != "none":
            continue
        groups.setdefault((m.get("proposed_skill") or "unnamed").strip().lower(), []).append(m["n"])
    return sorted(groups.items(), key=lambda kv: -len(kv[1]))


def run(conn, path, pages=None, mask=None):
    questions, conflicts = extract_questions(conn, path, pages, mask)
    matches = match_skills(conn, questions) if questions else []
    by_n = {f"{q['n']}{q.get('part', '')}": q for q in questions}
    return questions, matches, rate(matches), unmatched_groups(matches), by_n, conflicts


def spend_today(conn):
    return conn.execute(
        "select coalesce(sum(f.cost_inr), 0) as n from flow_run f join tenant t on t.id = f.tenant_id"
        " where t.slug = %s and f.started_at::date = current_date",
        (db.tenant_slug(),),
    ).fetchone()["n"]


def fingerprint(matches):
    """A response's identity, for telling independent samples from one cached answer replayed.

    Five runs of the matcher once came back byte-identical, billed at three input tokens for half
    the cost of five real calls, and the stability command called that 100% stable. Perfect
    agreement across runs is the symptom of a cache hit long before it is evidence of a steady model.
    """
    return hashlib.sha256(
        json.dumps(sorted((m["n"], m["skill_code"], m["confidence"]) for m in matches)).encode()
    ).hexdigest()
