"""A taxonomy case is a combination of tags; this decides whether a question is one. Deterministic, no I/O.

The school team's taxonomy §12 advises exactly this: "store these dimensions as tags, then generate or
select question sets by combinations of tags." A case's `match` (a `taxonomy_case` row) is a dict of
conditions, or a list of dicts any one of which may hold. A condition on `fmt` reads the kind of question;
every other key reads the question's tags. A value is equality, a list is "one of", `{"gte": n}` and
`{"lte": n}` compare numbers. A tag the question does not carry fails the condition.
"""


def _holds(want, got):
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
        if got is None or not _holds(want, got):
            return False
    return True


def keys(match):
    """Every tag a case reads — the sampler relaxes its defaults only for the ones a case is about."""
    if isinstance(match, list):
        return set().union(*(keys(m) for m in match))
    return set(match)
