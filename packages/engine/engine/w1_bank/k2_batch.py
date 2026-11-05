"""Several K2 pages in one model call, judged page by page (goals/m1-11-k2-complete-v1.yaml, task M1-11).

Batching keeps the drafting run inside Nimish's $25 (the instructions and the school's method are paid for once a call,
not once a page). The price of batching is that one bad page must not spoil the others, so code looks at every item of a
reply on its own: the good ones are kept, and only the bad or missing ones are asked for again. Pure, no database and no
model: `call` is whatever answers for the keys it is given (the adapter, in the run; a stand-in, in a test).
"""

import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field


class Stop(Exception):
    """The money for this run is spent, or cannot be counted: end it cleanly, keep what is good."""


@dataclass
class Done:
    good: dict[str, dict] = field(default_factory=dict)
    bad: dict[str, str] = field(default_factory=dict)  # page key → why it is still bad
    calls: int = 0
    stopped: str = ""
    faults: Counter[str] = field(default_factory=Counter)  # rule broken → times, over every ask
    stuck: dict[str, str] = field(
        default_factory=dict
    )  # page key → the rule it broke twice in a row: not asked again


# What a judge says when a page breaks a rule, in order, each with the name the run log and the replay count it under.
# The wordings are the ones k2_format and judge_pages make; a test pins that every one of them is named here.
RULES = (
    (r"^steps must be a list", "steps_not_list"),
    (r"^steps is empty", "steps_empty"),
    (r"^steps has \d+ lines", "steps_too_many"),
    (r"^steps line \d+ has \d+ words", "step_too_long"),
    (r"^slips: ", "slips_count"),
    (r"^slips item \d+ is not", "slip_shape"),
    (r"^slips item \d+ keyword must be", "keyword_length"),
    (r"^slips item \d+ spot must be", "spot_length"),
    (r"^idea is empty", "idea_empty"),
    (r"^idea has \d+ words", "idea_too_long"),
    (r"^uses '.*': not in the school's materials", "uses_unlisted"),
    (r"^steps line \d+ uses '", "step_word_unlisted"),
    (r"^answered twice", "answered_twice"),
    (r"^missing from the reply", "missing"),
    (r" is empty$", "part_empty"),
    (r"say the same thing$", "levels_alike"),
    (r"a draft says \"the child\", never he or she$", "gendered"),
    (r"a draft never sets one child against another$", "compares"),
)


def rule_of(why: str) -> str:
    """The name of the rule a failure in words broke ("other" for a wording nobody named)."""
    return next((name for pattern, name in RULES if re.search(pattern, why)), "other")


def line_of(faults: Counter[str]) -> str:
    """The run log's line: each rule and how many times a page broke it, most first."""
    return ", ".join(f"{r} {n}" for r, n in faults.most_common()) or "no failures"


def items(reply, name: str) -> list:
    """The list of items in a reply: the list itself, or the list under `name`; anything else is no items."""
    if isinstance(reply, dict) and isinstance(reply.get(name), list):
        return reply[name]
    return reply if isinstance(reply, list) else []


def _same(a: str, b: str) -> bool:
    flat = lambda t: re.sub(r"[\W_]+", " ", t).strip().casefold()  # noqa: E731
    return flat(a) == flat(b)


def _by_key(got, want) -> tuple[dict[str, dict], set[str]]:
    seen: dict[str, dict] = {}
    twice: set[str] = set()
    for it in got if isinstance(got, list) else []:
        key = it.get("key") if isinstance(it, dict) else None
        if not isinstance(key, str) or key not in want:
            continue
        if key in seen:
            twice.add(key)
        else:
            seen[key] = it
    return seen, twice


def normalise_steps(text: str) -> str:
    """Drafted steps as the school writes its own: one "• " line for each step, whatever numbering or dashes the model
    put in front of it."""
    lines = (re.sub(r"^\s*(?:\d+[.)]|[-*\u2022])\s*", "", ln).strip() for ln in text.splitlines())
    return "\n".join(f"\u2022 {ln}" for ln in lines if ln)


def house_rules(parts: dict[str, str], rules: dict | None) -> str:
    """The first rule a drafted part breaks, in words, or "". The rules are a config row (k2.draft_rules)."""
    if not rules:
        return ""
    gendered = "|".join(re.escape(w) for w in rules.get("gendered", []))
    for part, text in parts.items():
        if gendered and (hit := re.search(rf"\b({gendered})\b", text, re.I)):
            return f"{part} says '{hit.group(1)}': a draft says \"the child\", never he or she"
        for pattern in rules.get("compare", []):
            if hit := re.search(pattern, text, re.I):
                return f"{part} compares children ('{hit.group(0)}'): a draft never sets one child against another"
    return ""


def judge_pages(
    got, want: dict[str, list[str]], rules: dict | None = None
) -> tuple[dict[str, dict], dict[str, str]]:
    """→ the good pages (only the parts asked for) and why each other asked-for page is bad. `rules` (k2.draft_rules)
    are read on the drafted parts only; the steps are put in the school's own form."""
    seen, twice = _by_key(got, want)
    good: dict[str, dict] = {}
    bad: dict[str, str] = {}
    for key, parts in want.items():
        it = seen.get(key)
        if key in twice:
            bad[key] = "answered twice"
        elif it is None:
            bad[key] = "missing from the reply"
        elif empty := [p for p in parts if not (isinstance(it.get(p), str) and it[p].strip())]:
            bad[key] = f"{empty[0]} is empty"
        elif same := _first_pair_alike([p for p in parts if p.startswith("level_")], it):
            bad[key] = f"{same[0]} and {same[1]} say the same thing"
        elif broken := house_rules({p: it[p].strip() for p in parts}, rules):
            bad[key] = broken
        else:
            good[key] = {p: it[p].strip() for p in parts}
            if "steps" in good[key]:
                good[key]["steps"] = normalise_steps(good[key]["steps"])
    return good, bad


def _first_pair_alike(levels: list[str], it: dict) -> tuple[str, str] | None:
    for i, a in enumerate(levels):
        for b in levels[i + 1 :]:
            if _same(it[a], it[b]):
                return a, b
    return None


def judge_verdicts(got, keys: list[str]) -> tuple[dict[str, tuple[str, str]], dict[str, str]]:
    seen, twice = _by_key(got, set(keys))
    good: dict[str, tuple[str, str]] = {}
    bad: dict[str, str] = {}
    for key in keys:
        it = seen.get(key)
        if key in twice:
            bad[key] = "answered twice"
        elif it is None:
            bad[key] = "missing from the reply"
        elif it.get("verdict") not in ("agree", "disagree") or not isinstance(it.get("why"), str):
            bad[key] = "verdict is not agree or disagree"
        else:
            good[key] = (it["verdict"], it["why"])
    return good, bad


def _stem(word: str) -> str:
    """One word for a thing, whether it is one or many ("boxes" and "box", "berries" and "berry") and whether it is
    written in British or American spelling ("colour" and "color"). A word ending in "ss" is not a plural."""
    if len(word) > 3:
        if word.endswith("ies"):
            word = word[:-3] + "y"
        elif word.endswith(("sses", "xes", "zes", "ches", "shes")):
            word = word[:-2]
        elif word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]
    if len(word) > 5 and word.endswith("our"):
        word = word[:-3] + "or"
    return word


def _tokens(text: str) -> list[str]:
    return [_stem(w) for w in re.findall(r"[a-z0-9]+", text.casefold())]


def pieces_of(text: str) -> list[str]:
    """The things a materials text lists: split at a comma, a semicolon or a new line that is not inside brackets
    ("Crayons (red, blue)" is one thing)."""
    out: list[str] = []
    depth, start = 0, 0
    for i, ch in enumerate(text or ""):
        depth += (ch == "(") - (ch == ")" and depth > 0)
        if ch in ",;\n" and depth == 0:
            out.append(text[start:i])
            start = i + 1
    out.append((text or "")[start:])
    return [p for p in out if p.strip()]


def _segment_with(pieces: list[list[str]], phrase: list[str]) -> list[str] | None:
    """The piece of the text (already split and tokenised) that holds the phrase whole and in order."""
    for toks in pieces:
        if any(toks[i : i + len(phrase)] == phrase for i in range(len(toks) - len(phrase) + 1)):
            return toks
    return None


def judge_materials(got: object, text: str) -> tuple[list[dict], list[str]]:
    """Each line must name something the school's own text names as a phrase, in one piece of it; a quantity must be a
    number above 0 that stands in that same piece (or be empty), and a unit other than "piece" must stand there too."""
    good: list[dict] = []
    bad: list[str] = []
    pieces = [_tokens(piece) for piece in pieces_of(text)]  # once per text, not once per line
    for it in got if isinstance(got, list) else []:
        name = str(it.get("name") or "") if isinstance(it, dict) else ""
        phrase = _tokens(re.sub(r"[^A-Za-z ]", " ", name))
        qty, unit = (it.get("quantity"), it.get("unit")) if isinstance(it, dict) else (None, None)
        piece = _segment_with(pieces, phrase) if phrase else None
        if piece is None:
            bad.append(f"{name}: not in the school's text")
        elif qty is not None and (isinstance(qty, bool) or not isinstance(qty, int | float) or qty <= 0):
            bad.append(f"{name}: quantity must be a number above 0, or empty")
        elif qty is not None and str(int(qty)) not in piece:
            bad.append(f"{name}: quantity {qty} is not beside it in the school's text")
        elif not (isinstance(unit, str) and unit.strip()):
            bad.append(f"{name}: unit is empty")
        elif unit.strip().casefold() != "piece" and _stem(unit.strip().casefold()) not in piece:
            bad.append(f"{name}: unit {unit.strip()} is not in the school's text")
        else:
            good.append({"name": name.strip(), "quantity": qty, "unit": unit.strip()})
    return good, bad


def run(
    want: dict[str, list[str]],
    call: Callable[[list[str]], object],
    size: int,
    rounds: int,
    rules: dict | None = None,
    judge: Callable[[object, dict[str, list[str]]], tuple[dict[str, dict], dict[str, str]]] | None = None,
) -> Done:
    """Ask for every page in batches of `size`; then up to `rounds` more times for only the pages still bad or missing.
    `judge` reads a reply (default: the parts as text, with `rules`); the drafted pages' own judge reads lists."""
    done = Done()
    pending = list(want)
    last: dict[str, str] = {}  # the rule each page broke on its latest ask
    for attempt in range(rounds + 1):
        if not pending:
            break
        for i in range(0, len(pending), size):
            keys = pending[i : i + size]
            try:
                reply = call(keys)
            except Stop as e:
                done.stopped = str(e)
                for k in pending:
                    if k not in done.good:
                        done.bad.setdefault(k, "not asked: the run stopped")
                return done
            done.calls += 1
            good, bad = (judge or (lambda r, w: judge_pages(r, w, rules)))(reply, {k: want[k] for k in keys})
            done.good |= good
            done.bad = {k: v for k, v in done.bad.items() if k not in good} | bad
        pending = [k for k in pending if k not in done.good]
        for k in pending:
            rule = rule_of(done.bad.get(k, ""))
            done.faults[rule] += 1
            if last.get(k) == rule:
                done.stuck[k] = rule  # the same failure twice: another ask would pay for it a third time
            last[k] = rule
        pending = [k for k in pending if k not in done.stuck]
    return done
