"""A list answer read off a printed paper (goals/md4c-multiples-and-factors.yaml): the multiples of 6 up to 60, the
factors of 12, the factor pairs of 24. It prints as groups of boxes, two more than the list holds, each group its own
run in the paper's geometry — `list#3` for the third number, `list#3.1` and `list#3.2` for the third pair's two
(`straight_pages.multiples`). `boxes.read_page` reads each group as it reads any number, by the same rules for ink, the
floor and doubt; here a list's groups are found, and what they hold is joined into the one answer marking marks as a
whole (`multiples.judge`), in the order written, the empty groups left out.

A group the reader doubts makes the whole list a person's, what was read the guess. No group's crop is kept for the
reader to learn from (`crops`): what a person types for a list is the whole list, not the number in any one group."""

# The kinds of answer the reader reads in their boxes; any other (a tick, a sentence) is a person's to read.
READ = ("digits", "list")
GROUP = "#"
HALF = "a pair with one of its two numbers written"


def _place(resp):
    """`list#3.1` → (3, 1): the group's number in the list, and its part."""
    return tuple(int(x) for x in resp.split(GROUP, 1)[1].split("."))


def expand(wanted, runs, keep):
    """`wanted` ({slot: (item_key, rid)}) with each list's groups in its place, the crop keeper keeping none of theirs,
    and {slot: [(the group's slot, its number in the list)]} for `join`. A list is an answer with no run of boxes of its
    own and groups `rid#…` in the paper's geometry (`runs`, `geometry.cells_of`)."""
    out, lists = {}, {}
    for slot, (key, rid) in wanted.items():
        groups = sorted((r for k, r in runs if k == key and r.startswith(rid + GROUP)), key=_place)
        if (key, rid) in runs or not groups:
            out[slot] = (key, rid)
            continue
        lists[slot] = [(f"{slot}{GROUP}{r}", _place(r)[0]) for r in groups]
        out |= {f"{slot}{GROUP}{r}": (key, r) for r in groups}
    theirs = {g for groups in lists.values() for g, _ in groups}
    kept = keep and (lambda slot, png: None if slot in theirs else keep(slot, png))
    return out, kept, lists


def join(out, lists):
    """The page's readings (`boxes.read_page`) with each list's groups joined into its one reading (`expand`)."""
    for slot, groups in lists.items():
        reads = [(out.pop(g), member) for g, member in groups if g in out]
        if reads:
            out[slot] = _joined(reads)
    return out


def _joined(reads):
    """One list's reading from its groups' readings, in order: its members as written, `, ` between them and ` × `
    inside a pair; blank when every group is; a person's when a group's print was not found, a group is doubted, or a
    pair has one number written."""
    members = {}
    for r, member in reads:
        members.setdefault(member, []).append(r)
    written = [rs for rs in members.values() if any(r["answer_state"] != "blank" for r in rs)]
    text = ", ".join(" × ".join(r["child_answer"] or r.get("guess") or "" for r in rs) for rs in written)
    lost = next((r for r, _ in reads if r["answer_state"] == "not_found"), None)
    doubts = [f"group {m}: {r['why']}" for r, m in reads if r["answer_state"] == "illegible"]
    blank = [[r["answer_state"] == "blank" for r in rs] for rs in members.values()]
    doubts += [f"group {m}: {HALF}" for m, b in zip(members, blank, strict=True) if any(b) and not all(b)]
    boxes = [r["box"] for r, _ in reads]
    out = {
        "working_shown": "partial" if any(r["working_shown"] == "partial" for r, _ in reads) else "none",
        "box": [
            min(b[0] for b in boxes),
            min(b[1] for b in boxes),
            max(b[2] for b in boxes),
            max(b[3] for b in boxes),
        ],
        "boxes": sum(r["boxes"] for r, _ in reads),
        "inked": sum(r["inked"] for r, _ in reads),
        "seen": [s for r, _ in reads for s in r["seen"]],
        "confidence": min((r["confidence"] for rs in written for r in rs), default=100.0),
    }
    if lost:
        return {**out, "child_answer": "", "answer_state": "not_found", "why": lost["why"], "guess": ""}
    if doubts:
        return {
            **out,
            "child_answer": "",
            "answer_state": "illegible",
            "why": "; ".join(doubts),
            "guess": text,
        }
    if not written:
        return {**out, "child_answer": "", "answer_state": "blank", "why": "", "guess": ""}
    return {**out, "child_answer": text, "answer_state": "written", "why": "", "guess": ""}
