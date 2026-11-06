"""What the models are shown, and the code that reads what a maker wrote (goals/m1-12a-page-format.yaml; M1-12j).

A maker is shown the school's own words for a page, the parts to write and either a similar page the school wrote or, in a
revision, its own draft and the checker's faults; a checker is shown the school's words and the draft. The judge is the
format and house rules of config rows. Split from `k2_draft`, which runs the batches and records the proposals."""

from engine.core import db, settings
from engine.w1_bank import k2_check, k2_format
from engine.w1_bank.k2_gaps import PAGE_PARTS, empty_parts


def block(
    row: dict,
    parts: list[str],
    example: dict | None,
    with_draft: dict | None = None,
    revise: tuple[dict, list[dict]] | None = None,
) -> str:
    wrote = [f"  {p}: {row[p].strip()}" for p in PAGE_PARTS if (row[p] or "").strip()]
    out = [f"key: {row['code']}", f"activity: {row['name']} (section: {row['strand']})"]
    out += ["the school wrote:", *wrote] if wrote else ["the school wrote nothing else for it"]
    out.append(f"materials: {row['materials'].strip() or 'the school wrote none'}")
    if with_draft is not None:
        out += ["the draft:", k2_format.shown_draft(with_draft)]
    else:
        out.append("draft: " + ", ".join(parts))
        if revise:
            earlier, faults = revise
            out += [
                "the checker found:",
                "your earlier draft:",
                k2_format.shown_draft(earlier),
                "its faults:",
            ]
            out += [f"  {f['part']}: {f['reason']}" for f in faults]
        elif example:
            out.append(
                f"a page the school wrote for a similar activity: {example['name']}; steps: {example['steps'][:400]}"
            )
    return "\n".join(out)


def judge_for(conn: db.Conn, rows: dict) -> k2_format.Judge:
    """The code that reads a drafted page: the school's format and house rules are config rows."""
    format_row = settings.config(conn, "k2.format")
    vocab = k2_format.vocabulary(
        (r["materials"] for r in rows.values()),
        format_row.get("function_words", []),
        int(format_row.get("prop_min_pages", 3)),
        format_row.get("not_props", []),
    )
    return k2_format.judger(rows, vocab, format_row, settings.config(conn, "k2.draft_rules"))


def examples_of(rows: dict) -> dict[str, dict]:
    """For each section, its first complete page: the style and length to match. A page being drafted has a gap, so
    it is never its own example."""
    out: dict[str, dict] = {}
    for r in rows.values():
        if not empty_parts(r):
            out.setdefault(r["strand"], r)
    return out


def maker_text(rows: dict, want: dict, examples: dict, keys: list[str], revise: dict | None) -> str:
    """What the maker is shown for these pages: the school's words, the parts to write, and either a similar page or, in a
    revision, its own draft and the checker's faults."""
    parts = {k: k2_check.parts_at_fault(revise[k][1], want[k]) if revise else want[k] for k in keys}
    return "\n\n".join(
        block(rows[k], parts[k], examples.get(rows[k]["strand"]), revise=revise[k] if revise else None)
        for k in keys
    )
