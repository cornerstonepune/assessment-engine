#!/usr/bin/env python3
"""Renders the Level 2 draft JSON as the founders' sitting document (markdown), so the two never drift.
python3 research/level2_render.py docs/school-os-level2-behaviours-draft.json docs/school-os-level2-behaviours-draft.md"""

import json
import sys

STAGE_HEAD = {
    "foundational": "Foundational · Nursery to Grade 2 · ages 3–8 · Discover",
    "preparatory": "Preparatory · Grades 3–5 · Investigate",
    "middle": "Middle · Grades 6–8 · Apply",
    "secondary": "Secondary · Grades 9–10 · Create & Question",
}
MODE = {
    "observation": "observation note",
    "artefact": "artefact",
    "audio": "audio",
    "video_clip": "video clip",
    "rubric": "rubric",
    "sheet": "sheet",
    "test": "test",
    "self_voice": "child's own voice",
    "peer_comment": "peer comment",
    "parent_voice": "parent's voice",
}
REASON = {
    "no_observable_form": "no observable form",
    "capability_too_broad": "capability too broad",
    "stage_unclear": "stage unclear",
    "other": "other",
}
WORDS = [
    (
        "capable",
        "knows things deeply and can do something with them; can find out what they do not know.",
    ),
    (
        "kind",
        "notices other people and acts for them, including when it costs something.",
    ),
    (
        "unafraid",
        "tries, asks, disagrees and shows their work in front of others, and treats a wrong answer as information.",
    ),
]


def cell(s):
    return s.replace("|", "\\|").replace("\n", " ")


def main(src, dst):
    d = json.load(open(src))
    council = d.get("council")
    L = [
        "# Level 2 draft for the founders' sitting — observable behaviours per capability per stage",
        "",
        "26 September 2026 · a draft to edit, not a decision · **no step of the build order moved — nothing built**",
        "",
        "**How this was made.** The ratified prompt (`docs/school-os-proposal-capability-behaviours.md`, §3) was run once by hand in the "
        "council session, not by the engine, and its output was checked by the proposal's validator as a script: "
        "`python3 research/level2_validate.py docs/school-os-level2-behaviours-draft.json`. First pass: 25 of 32 cells passed; the seven "
        "that failed were regenerated once with the failures named, and the second pass was 32 of 32.",
    ]
    if council:
        o = council["outcomes"]
        L += [
            "",
            f"**Then a council of four seats read every line** (educator, parent, developmental and measurement expert, child-rights and "
            f"safeguarding), each from its own life, and marked Accept, Edit or Skip with a reason. Their verdicts were reconciled by rules "
            f"(`research/level2_council.py`): {o.get('accepted', 0)} rows stand as written, {o.get('edited', 0)} were edited, "
            f"{o.get('retired', 0)} retired (struck through below, kept so you can restore them), {o.get('added', 0)} added. "
            f"The column **Council** shows each seat's verdict (E educator, P parent, D development, R rights) and what was done; every "
            f"change and its reason is in `docs/school-os-level2-council-changes.md`. This is the council's pass, not yours: your acceptance "
            f"rate is still the eval the proposal names.",
        ]
    L += [
        "",
        "**What to do.** For each behaviour, mark one of **Accept · Edit · Skip** in the last column. Edit means rewrite it in your own "
        "words on the line; Skip retires it. Add a behaviour where a cell is missing something you would look for. Your edits become the "
        "golden set. Two founders split the eight capabilities; the third settles any cell you disagree on.",
        "",
        "**The three words, in the draft meanings the tags follow** (replace with your own before the engine runs):",
        "",
    ]
    L += [f"- **{w}** — {m}" for w, m in WORDS]
    L += [
        "",
        "Every behaviour is one occasion a familiar adult could see and record, never a level, a score or a trait. The stage rises: a later "
        'behaviour grows out of a named earlier one. "Not evidence when" is the look-alike an educator should not count.',
        "",
    ]
    total = 0
    for cap in d["capabilities"]:
        L += [
            "",
            f"## {cap['name']}",
            "",
            f"*Observable at 16:* {cap['observable_at_16']}",
            "",
        ]
        for st in cap["stages"]:
            L += ["", f"### {STAGE_HEAD[st['stage_id']]}", ""]
            head = "| # | Behaviour | What the educator sees | Where · how | Words | Not evidence when | Grows from |"
            head += " Council |" if council else ""
            head += " Accept · Edit · Skip |"
            L += [head, "|---" * (9 if council else 8) + "|"]
            n = 0
            for b in st["behaviours"]:
                retired = b.get("status") == "retired"
                if not retired:
                    n += 1
                    total += 1

                def s(x):
                    return f"~~{cell(x)}~~" if retired else cell(x)

                row = [
                    str(n) if not retired else "—",
                    s(b["statement"]),
                    s(b["adult_sees"]),
                    f"{b['setting']} · {MODE.get(b['capture_mode'], b['capture_mode'])}"
                    + (f" · from age {b['from_age']}" if b.get("from_age") else ""),
                    ", ".join(b["words"]),
                    s(b["counter_example"]),
                    b["grows_from"] or "—",
                ]
                if council:
                    c = b.get("council", {})
                    seats = " ".join(
                        f"{k}:{v[0].upper()}" for k, v in c.get("seats", {}).items()
                    )
                    row.append(
                        f"{seats} → **{c.get('outcome', '')}**"
                        + (
                            f" ({c['rule']})"
                            if c.get("rule") in ("R1", "chair")
                            else ""
                        )
                    )
                row.append("")
                L.append("| " + " | ".join(row) + " |")
        if cap.get("could_not"):
            L += ["", "**What the prompt could not do here (ADR 0018):**", ""]
            L += [
                f"- *{REASON.get(e['reason'], e['reason'])}*: {e['detail']}"
                for e in cap["could_not"]
            ]
    L += [
        "",
        "---",
        "",
        f"*{total} live behaviours in 32 cells. The machine copy is `docs/school-os-level2-behaviours-draft.json`; the operations "
        "coordinator transcribes the sitting's decisions into it, and the validator re-runs on the result.*",
    ]
    open(dst, "w").write("\n".join(L) + "\n")
    print("rendered", dst, "live behaviours", total)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
