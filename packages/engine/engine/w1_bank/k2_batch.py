"""Several K2 pages in one model call, judged page by page (goals/m1-11-k2-complete-v1.yaml, task M1-11).

Batching keeps the drafting run inside Nimish's $25 (the instructions and the school's method are paid for once a call,
not once a page). The price of batching is that one bad page must not spoil the others, so code looks at every item of a
reply on its own: the good ones are kept, and only the bad or missing ones are asked for again. Pure, no database and no
model: `call` is whatever answers for the keys it is given (the adapter, in the run; a stand-in, in a test).
"""

import re
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


def judge_pages(got, want: dict[str, list[str]]) -> tuple[dict[str, dict], dict[str, str]]:
    """→ the good pages (only the parts asked for) and why each other asked-for page is bad."""
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
        else:
            good[key] = {p: it[p].strip() for p in parts}
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
    return word[:-1] if word.endswith("s") and len(word) > 3 else word


def _tokens(text: str) -> list[str]:
    return [_stem(w) for w in re.findall(r"[a-z0-9]+", text.casefold())]


def _segment_with(text: str, phrase: list[str]) -> list[str] | None:
    """The comma-, semicolon- or line-separated piece of the text that holds the phrase whole and in order."""
    for piece in re.split(r"[,;\n]+", text):
        toks = _tokens(piece)
        if any(toks[i : i + len(phrase)] == phrase for i in range(len(toks) - len(phrase) + 1)):
            return toks
    return None


def judge_materials(got: object, text: str) -> tuple[list[dict], list[str]]:
    """Each line must name something the school's own text names as a phrase, in one piece of it; a quantity must be a
    number above 0 that stands in that same piece (or be empty), and a unit other than "piece" must stand there too."""
    good: list[dict] = []
    bad: list[str] = []
    for it in got if isinstance(got, list) else []:
        name = str(it.get("name") or "") if isinstance(it, dict) else ""
        phrase = _tokens(re.sub(r"[^A-Za-z ]", " ", name))
        qty, unit = (it.get("quantity"), it.get("unit")) if isinstance(it, dict) else (None, None)
        piece = _segment_with(text, phrase) if phrase else None
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


def run(want: dict[str, list[str]], call: Callable[[list[str]], object], size: int, rounds: int) -> Done:
    """Ask for every page in batches of `size`; then up to `rounds` more times for only the pages still bad or missing."""
    done = Done()
    pending = list(want)
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
            good, bad = judge_pages(reply, {k: want[k] for k in keys})
            done.good |= good
            done.bad = {k: v for k, v in done.bad.items() if k not in good} | bad
        pending = [k for k in pending if k not in done.good]
    return done
