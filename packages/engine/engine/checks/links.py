"""Do a skill's rows say what its lists say? `engine links check` (goals/b3-samples-mistakes-prerequisites.yaml).

B3 makes rows of four things a skill names: its levels' samples, its mistakes, its registry skills and what comes before
it. The first three are still written as lists (a level's words, a card kind's examples, `misconception_codes`, the
rung's `skill_codes`) and kept equal to their rows by triggers, so both must agree: every skill's mistakes and registry
skills the same codes, every card example a sample in its place, and every level's samples the examples its words give
by decision B3-1's rule, worked here a second time, in Python, apart from the migration's SQL. What comes before a
skill is rows only: none comes before itself. Read only; safe on a copy of live, where the rehearsal runs it.
"""

import re
from typing import Any

import typer

from engine.core import db

SIGNS = re.compile(r"[+−\-×÷=≈<>○□]")
NUMBERS = re.compile(r"[\d□]+")
ROW_OF_NUMBERS = re.compile(r"[\d□, ]+")
REMAINDER = re.compile(r"(\d) r (\d)")


def pieces(words: str | None) -> list[tuple[str, bool]]:
    """A level's examples as its words give them (decision B3-1, ADR 0092), each with whether it is a sample: the text
    after the words' last colon, to the end of that sentence, cut at ", " and "; "; numbers written in a row are one
    piece; a piece is a sample when it is written in signs, with no word but a remainder's "r"."""
    if not words or ":" not in words:
        return []
    tail = words.rsplit(":", 1)[1]
    tail = re.split(r"\.\s+(?=[A-Z])", tail)[0].strip()
    tail = re.sub(r"\.$", "", tail)
    out: list[str] = []
    for p in (p.strip() for p in re.split(r",\s+|;\s+", tail)):
        if not p:
            continue
        if NUMBERS.fullmatch(p) and out and ROW_OF_NUMBERS.fullmatch(out[-1]):
            out[-1] += ", " + p
        else:
            out.append(p)
    return [
        (p, not re.search(r"[A-Za-z]", REMAINDER.sub(r"\1 \2", p)) and bool(SIGNS.search(p))) for p in out
    ]


def samples(words: str | None) -> list[str]:
    return [p for p, sample in pieces(words) if sample]


def _lists(conn: db.Conn) -> list[str]:
    """Each skill whose mistake or registry rows are not its lists' codes, and how."""
    disagree = []
    for r in conn.execute(
        "select s.code, s.misconception_codes as listed, r.skill_codes as registry,"
        " (select coalesce(array_agg(distinct k.misconception_code), '{}') from skill_mistake k"
        "   where k.tenant_id = s.tenant_id and k.skill_code = s.code) as mistakes,"
        " (select count(*) from skill_mistake k where k.tenant_id = s.tenant_id and k.skill_code = s.code) as mistake_rows,"
        " (select count(*) from misconception m where m.tenant_id = s.tenant_id and m.code = any(s.misconception_codes))"
        "   as misconception_rows,"
        " (select coalesce(array_agg(l.registry_skill), '{}') from skill_registry_link l"
        "   where l.tenant_id = s.tenant_id and l.skill_code = s.code) as links"
        " from skill_set s join rung r on r.tenant_id = s.tenant_id and r.code = s.rung_code order by s.code"
    ):
        if set(r["listed"]) != set(r["mistakes"]) or r["mistake_rows"] != r["misconception_rows"]:
            disagree.append(
                f"{r['code']}: mistakes {sorted(r['listed'])} listed, {sorted(r['mistakes'])} in rows"
            )
        if set(r["registry"]) != set(r["links"]):
            disagree.append(
                f"{r['code']}: registry {sorted(r['registry'])} on its rung, {sorted(r['links'])} in rows"
            )
    return disagree


def _samples(conn: db.Conn) -> tuple[list[str], list[tuple[str, str, list[str]]], int]:
    """Each level whose sample rows are not its words' examples by B3-1's rule, or its card kinds' examples; the pieces
    each level keeps in its words; and how many card examples there are."""
    disagree = []
    rows: dict[tuple[str, str, str | None], list[str]] = {}
    for r in conn.execute(
        "select skill_code, difficulty, question_format, sample from skill_level_sample order by ord"
    ):
        rows.setdefault((r["skill_code"], r["difficulty"], r["question_format"]), []).append(r["sample"])
    expected: dict[tuple[str, str, str | None], list[str]] = {}
    words_left = []
    for r in conn.execute(
        "select skill_code, difficulty, looks_like from skill_level order by skill_code, difficulty"
    ):
        found = pieces(r["looks_like"])
        if any(sample for _, sample in found):
            expected[(r["skill_code"], r["difficulty"], None)] = [p for p, sample in found if sample]
        if any(not sample for _, sample in found):
            words_left.append((r["skill_code"], r["difficulty"], [p for p, sample in found if not sample]))
    cards = 0
    for r in conn.execute(
        "select f.code, f.skill_set_code, e.key as level, e.value as examples from question_format f"
        " cross join jsonb_each(case when jsonb_typeof(f.kind -> 'examples') = 'object'"
        "   then f.kind -> 'examples' else '{}' end) e"
    ):
        cards += len(r["examples"])
        if r["examples"]:
            expected[(r["skill_set_code"], r["level"], r["code"])] = list(r["examples"])
    for key in sorted(expected.keys() | rows.keys(), key=str):
        if expected.get(key, []) != rows.get(key, []):
            disagree.append(
                f"{key[0]} {key[1]} {key[2] or 'words'}: {expected.get(key)} expected, {rows.get(key)} rows"
            )
    return disagree, words_left, cards


def compare(conn: db.Conn) -> dict[str, Any]:
    """The lists against the rows. `disagree` names every skill or level where they part, and how."""
    disagree = _lists(conn)
    samples_disagree, words_left, cards = _samples(conn)
    disagree += samples_disagree
    circles = conn.execute(
        "with recursive walk(start, code) as ("
        "  select skill_code, before_code from skill_prerequisite"
        "  union select w.start, p.before_code from walk w join skill_prerequisite p on p.skill_code = w.code"
        ") select distinct start from walk where start = code"
    ).fetchall()
    disagree += [f"{c['start']} comes before itself" for c in circles]
    count = db.one(
        conn,
        "select (select count(*) from skill_set)::int as skills, (select count(*) from skill_mistake)::int as mistakes,"
        " (select count(*) from skill_registry_link)::int as links,"
        " (select count(*) from skill_prerequisite)::int as prerequisites,"
        " (select count(*) from skill_level_sample where question_format is null)::int as word_samples,"
        " (select count(*) from skill_level_sample where question_format is not null)::int as card_samples",
    )
    return {**dict(count), "card_examples": cards, "words_left": words_left, "disagree": disagree}


links_app = typer.Typer(
    help="A skill's samples, mistakes, registry links and prerequisites, as rows", no_args_is_help=True
)


@links_app.command("check")
def check_(
    words: bool = typer.Option(
        False, "--words", help="list each level's pieces left in its words, not samples"
    ),
) -> None:
    """Do the rows say what the lists say? Exits 1 if any skill or level parts."""
    with db.connect() as conn:
        r = compare(conn)
    typer.echo(
        f"  {r['skills']} skills · {r['mistakes']} mistake rows · {r['links']} registry links"
        f" · {r['prerequisites']} prerequisites"
    )
    typer.echo(
        f"  samples: {r['word_samples']} from levels' words, {r['card_samples']} of {r['card_examples']} card examples;"
        f" {len(r['words_left'])} levels keep a piece in words"
    )
    if words:
        for code, level, left in r["words_left"]:
            typer.echo(f"    {code} {level}: {' | '.join(left)}")
    for line in r["disagree"][:20]:
        typer.echo(f"  FAIL  {line}", err=True)
    if r["disagree"] or r["card_samples"] != r["card_examples"]:
        typer.echo(f"  the rows and the lists disagree in {len(r['disagree'])} places")
        raise typer.Exit(1)
    typer.echo("  the rows and the lists agree on every skill and level")
