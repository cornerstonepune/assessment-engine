"""`engine bank rekey`: every story stored before its shape was part of it, keyed as the bank keys it now (ADR 0053).

A story's key said only its numbers, so two shapes of one numbers pair were one question, and a level of small numbers
never held the shapes it listed last. A story's shape and operations are now in its spec, and so in its key
(`words.story_spec`). A story stored before that is matched back to the template that wrote it (`words.template_of`):
its words, numbers and answer stay as they are. Each change is a row of `item_key_change`, append-only: a review and a
gold finding follow their question in place, and what is never rewritten (a proposal in its own ledger, a gold file, a
page bookmarked) finds the question through that row (`inventory.current_key`). A rewording keeps its own key, its words
being part of it (`question.correct`), and takes the shape of the story it rewords, so a relabel no longer loses it.
Running it again changes nothing.
"""

import json
from collections import Counter
from typing import Any

from engine.assess import items
from engine.assess import words as W

NAMED_BY_KEY = (("item_review", "ref"), ("gold_finding", "item_key"))  # what follows a question in place
KINDS = {"WP1": "word_1step", "WP2": "word_2step"}
ACTOR = "engine (bank rekey)"


def _template(rows: dict[Any, dict[str, Any]], row: dict[str, Any]) -> dict[str, Any] | None:
    """The template that wrote this story's words, or the words of the story it rewords, followed back through
    `corrected_from`; None when no template wrote any of them, or wrote another operation than the stored one."""
    seen: set[Any] = set()
    at: dict[str, Any] | None = row
    while at is not None and at["id"] not in seen:
        seen.add(at["id"])
        tpl = W.template_of(at["stem"])
        if tpl:
            same = tpl["fmt"] == KINDS[row["template"]] and tpl["op"] == row["spec"].get("op", tpl["op"])
            return tpl if same else None
        at = rows.get(at["corrected_from"])
    return None


def rekey(conn) -> dict[str, Any]:
    """Key every stored story by its numbers, its shape and its operations → {keyed, reworded, duplicates, unwritten,
    followed: {table: rows}}. A story the bank already holds under its new key is the same question twice: the old row
    is retired, through the path a person's flag takes, and keeps its key. The caller commits."""
    rows = {
        r["id"]: r
        for r in conn.execute(
            "select id, tenant_id, item_key, template, stem, spec, status, corrected_from from item"
            " where template = any(%s)",
            (list(KINDS),),
        ).fetchall()
    }
    out: Counter[str] = Counter(keyed=0, reworded=0, duplicates=0, unwritten=0)
    followed: Counter[str] = Counter({table: 0 for table, _ in NAMED_BY_KEY})
    for r in rows.values():
        if "structure" in r["spec"]:
            continue
        tpl = _template(rows, r)
        if tpl is None:
            out["unwritten"] += 1
            continue
        spec = W.story_spec(tpl, **{k: r["spec"][k] for k in ("a", "b", "c") if k in r["spec"]})
        key = items._id(r["template"], spec)
        taken = (
            r["corrected_from"] is None
            and conn.execute(
                "select 1 from item where tenant_id = %s and item_key = %s", (r["tenant_id"], key)
            ).fetchone()
        )
        if r["corrected_from"] is not None or taken:
            # a rewording's key is its words' too; a duplicate keeps the key it has, retired beside the one the bank holds
            conn.execute(
                "update item set spec = %s, updated_at = now() where id = %s", (json.dumps(spec), r["id"])
            )
            if taken and r["status"] == "active":
                conn.execute(
                    "insert into item_feedback (tenant_id, item_id, actor, verdict, note) values (%s,%s,%s,'retire',%s)",
                    (
                        r["tenant_id"],
                        r["id"],
                        ACTOR,
                        f"the same story as {key}, as the bank keys a story now",
                    ),
                )
            out["duplicates" if taken else "reworded"] += 1
            continue
        conn.execute(
            "update item set item_key = %s, spec = %s, updated_at = now() where id = %s",
            (key, json.dumps(spec), r["id"]),
        )
        conn.execute(
            "insert into item_key_change (tenant_id, item_id, old_key, new_key, why) values (%s,%s,%s,%s,%s)",
            (
                r["tenant_id"],
                r["id"],
                r["item_key"],
                key,
                "a story is its numbers, its shape and its operations",
            ),
        )
        for table, column in NAMED_BY_KEY:
            followed[table] += conn.execute(
                f"update {table} set {column} = %s, updated_at = now() where tenant_id = %s and {column} = %s",
                (key, r["tenant_id"], r["item_key"]),
            ).rowcount
        out["keyed"] += 1
    return dict(out) | {"followed": dict(followed)}
