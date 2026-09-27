#!/usr/bin/env python3
"""Writes the council's change log (markdown) for research/level2_council.py: the numbers, what each seat
would say across the table, what the chair still owes, what the seats say the cells lack, and every row that
changed or was questioned, with the seats' reasons. No model is called."""

SEATS = ["rights", "development", "educator", "parent"]


def write_log(
    path,
    doc,
    seats,
    log,
    needs,
    dangling,
    missing,
    duplicates,
    could_not,
    objections,
    notes_to_founders,
    added_reviews=(),
):
    L = [
        "# The council's changes to the Level 2 draft",
        "",
        "26 September 2026 · four seats (educator, parent, developmental and measurement expert, child-rights and safeguarding) · "
        "reconciled by `research/level2_council.py`; the rules are in its docstring · the seats' full verdicts are in `research/level2_council/`",
        "",
    ]
    c = doc["council"]
    L += [
        "## Numbers",
        "",
        "| Seat | Accepted as written | Edited | Skipped |",
        "|---|---|---|---|",
    ]
    for s in SEATS:
        if s in c["per_seat"]:
            k = c["per_seat"][s]
            n = sum(k.values())
            L.append(
                f"| {s} | {k.get('accept', 0)} ({100 * k.get('accept', 0) / n:.0f}%) | {k.get('edit', 0)} | {k.get('skip', 0)} |"
            )
    L += [
        "",
        "Outcome after the rules: "
        + ", ".join(f"{v} {k}" for k, v in sorted(c["outcomes"].items()))
        + ".",
        "",
    ]
    L += ["## What each seat would say across the table", ""]
    for s in SEATS:
        if s in notes_to_founders:
            L += [f"**{s}.** {notes_to_founders[s]}", ""]
            for o in objections.get(s, []):
                L.append(f"- {o}")
            L.append("")
    if needs:
        L += [
            "## For the chair: one seat skipped, or two seats edited the same field",
            "",
        ]
        for cap, st, i, rule, notes in needs:
            L.append(f"- `{cap}/{st}/{i}` ({rule}): " + " · ".join(notes))
        L.append("")
    if dangling:
        L += ["## For the chair: grows_from naming a retired row", ""]
        L += [f"- `{cap}/{st}/{i}` grew from `{g}`" for cap, st, i, g in dangling] + [
            ""
        ]
    if missing:
        L += ["## What the seats say the cells lack (not added by the script)", ""]
        for s, cap, st, m in missing:
            L.append(
                f"- **{s}** · `{cap}/{st}`: {m['statement']} — *{m.get('why', '')}*"
            )
        L.append("")
    if duplicates:
        L += ["## Pairs a seat says record the same evidence", ""]
        L += [f"- **{s}**: `{p[0]}` and `{p[1]}`" for s, p in duplicates] + [""]
    if could_not:
        L += ["## The draft's own could_not entries, judged", ""]
        L += [
            f"- **{s}** · `{cn.get('capability_id')}`: {cn.get('verdict')} — {cn.get('reason', '')}"
            for s, cn in could_not
        ] + [""]
    if added_reviews:
        L += ["## The added rows, checked again by two seats", ""]
        for r in added_reviews:
            for v in r["verdicts"]:
                if v["verdict"] != "accept":
                    L.append(
                        f"- **{r['seat']}** · `{v['id']}` → {v['verdict']}: {v.get('reason', '')}"
                    )
            L.append(
                f"- **{r['seat']}**: accepted {sum(1 for v in r['verdicts'] if v['verdict'] == 'accept')} of {len(r['verdicts'])} added rows as written"
            )
        L.append("")
    L += [
        "## Every row that changed, or that a seat questioned",
        "",
        "Seats: E educator, P parent, D development, R rights. Rule numbers are in the script's docstring.",
        "",
    ]
    cur = None
    for cap, st, i, outcome, rule, before, b, notes in log:
        if (cap, st) != cur:
            cur = (cap, st)
            L += [f"### {cap} · {st}", ""]
        L.append(f"- **`{i}`** → {outcome} ({rule}). " + " · ".join(notes))
        for f, old in before.items():
            L.append(f"  - {f}: ~~{old}~~ → {b.get(f)}")
    open(path, "w").write("\n".join(L) + "\n")
