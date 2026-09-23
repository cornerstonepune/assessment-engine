"""A taxonomy case is a combination of tags; this decides whether a question is one. Deterministic, no I/O.

The school team's taxonomy §12 advises exactly this: "store these dimensions as tags, then generate or
select question sets by combinations of tags." A case's `match` (a `taxonomy_case` row) is a dict of
conditions, or a list of dicts any one of which may hold. A condition on `fmt` reads the kind of question;
every other key reads the question's tags. A value is equality, a list is "one of", `{"gte": n}` and
`{"lte": n}` compare numbers. A tag the question does not carry fails the condition.
"""


def holds(want, got):
    if isinstance(want, dict):
        return isinstance(got, int) and got >= want.get("gte", got) and got <= want.get("lte", got)
    if isinstance(want, list):
        return got in want
    return got == want


def matches(match, fmt, tags):
    if isinstance(match, list):
        return any(matches(m, fmt, tags) for m in match)
    for key, want in match.items():
        got = fmt if key == "fmt" else tags.get(key)
        if got is None or not holds(want, got):
            return False
    return True


def within(match, shape):
    """The case on one skill's numbers: its conditions and the skill's shape (operation, digits) together.
    Where both speak of one tag the narrower wins when it satisfies the other (a skill of 4-digit numbers
    and a case of "4 digits or more"); a case the shape contradicts can never be on that skill, and says so."""
    if not shape:
        return match
    if isinstance(match, list):
        return [within(m, shape) for m in match]
    out = {**match, **shape}
    for k in shape.keys() & match.keys():
        mine, theirs = match[k], shape[k]
        if mine == theirs:
            continue
        if not isinstance(theirs, (dict, list)) and holds(mine, theirs):
            out[k] = theirs
        elif not isinstance(mine, (dict, list)) and holds(theirs, mine):
            out[k] = mine
        elif isinstance(mine, dict) and isinstance(theirs, dict) and _overlap(mine, theirs):
            out[k] = _overlap(mine, theirs)
        else:
            raise ValueError(f"the case fixes {k}={mine} against the skill's shape {shape}")
    return out


def _overlap(a, b):
    """Two ranges as one ("4 or more" inside "3 or more" is "4 or more"), or None when they share nothing."""
    lo = max((r["gte"] for r in (a, b) if "gte" in r), default=None)
    hi = min((r["lte"] for r in (a, b) if "lte" in r), default=None)
    if lo is not None and hi is not None and lo > hi:
        return None
    return {k: v for k, v in (("gte", lo), ("lte", hi)) if v is not None}


def keys(match):
    """Every tag a case reads — the sampler relaxes its defaults only for the ones a case is about."""
    if isinstance(match, list):
        return set().union(*(keys(m) for m in match))
    return set(match)
