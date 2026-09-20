"""Ring C — the transcription layer. One external service named in one file (CLAUDE.md's organism).

ADR 0019: what reads a child's handwriting must not know arithmetic. A vision model does, and it
filled faint pencil with the answer it could compute — `425 − 38` came back `387` where the child
had written `397`, turning the most valuable observation on the page into a silent "correct". An OCR
engine has no idea that 425 − 38 is 387, so it cannot make that error at all.

Measured on the page a person read by eye: 17 of 17 of the child's real answers found verbatim, none
of them replaced by the computed answer, and the hardest mark on the page (a `374` that two model
versions read as `375` and `874`) came back correct at 62.3% confidence — read right, and flagged.

That confidence is the second reason for being here. It is calibrated and per-word, which is what
ADR 0018 established a model cannot report about itself, and it is what routes a doubtful answer to
a teacher instead of into a child's graph.
"""

import re

import boto3

PROFILE = "cornerstone"
REGION = "ap-south-1"
_NUM = re.compile(r"-?\d[\d,]*")


def client(profile=PROFILE, region=REGION):
    return boto3.Session(profile_name=profile, region_name=region).client("textract")


def _box(b):
    g = b["Geometry"]["BoundingBox"]
    return {
        "text": b["Text"],
        "confidence": b["Confidence"],
        "hand": b.get("TextType") == "HANDWRITING",
        "x": g["Left"],
        "y": g["Top"],
        "w": g["Width"],
        "h": g["Height"],
    }


def read(image_bytes, cli=None):
    """One page image → {"lines": [...], "words": [...]}.

    Every word carries `hand`: Textract labels each one HANDWRITING or PRINTED, and that single flag
    does what no amount of prompting could. A printed `452` inside "452 = 400 + [ ] + 12" can never
    again be mistaken for the child's answer, because the child's answer is the handwriting and
    nothing else is. Lines are kept for anchoring: a printed question is found as a line, and the
    answer is found as handwriting near it.

    `x` and `y` are fractions of the page, so the same rules hold on a 200-dpi render and a photo.
    """
    cli = cli or client()
    r = cli.detect_document_text(Document={"Bytes": image_bytes})
    return {
        "lines": [_box(b) for b in r["Blocks"] if b["BlockType"] == "LINE"],
        "words": [_box(b) for b in r["Blocks"] if b["BlockType"] == "WORD"],
    }


def _norm(s):
    """Compare printed text by its digits and letters alone: OCR renders '148 + 7 =' as '148 +7 =',
    and spacing around operators is the first thing to differ."""
    return re.sub(r"[^0-9a-z]", "", s.lower())


def find_question(lines, question, min_overlap=0.7):
    """Where a printed question sits on the page, or None.

    Matched on the question's leading run of characters rather than the whole string: a word problem
    wraps over several lines, and only its first line carries a position worth having.
    """
    want = _norm(question)[:24]
    if not want:
        return None
    best, score = None, 0.0
    for ln in lines:
        got = _norm(ln["text"])
        if not got:
            continue
        hit = len(want) if want in got else _prefix_overlap(want, got)
        ratio = hit / len(want)
        if ratio > score:
            best, score = ln, ratio
    return best if score >= min_overlap else None


def _prefix_overlap(a, b):
    n = 0
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            break
        n += 1
    return n


def _in_region(word, anchor, max_drop, column):
    """Is this word an answer to the question anchored here?

    The region is as wide as the question itself. A grid question — "236 + 9 =" in one of four boxes
    across the page — is narrow, so its region stays narrow and cannot reach the neighbouring box's
    answer, which is how 245 once became 155. A question printed across the page with fill-in boxes
    along it is wide, so its region is wide, which is the only way to reach boxes sitting 0.12 to the
    right of where the question starts.

    Using one fixed column for both is what made Q5's three boxes unreadable while a wider one made
    every grid answer ambiguous. The page already says which kind it is: the printed line's width.
    """
    dy = word["y"] - anchor["y"]
    if not -anchor["h"] <= dy <= max_drop:
        return False
    return anchor["x"] - column <= word["x"] <= anchor["x"] + max(anchor["w"], column)


def _handwriting_near(page, anchor, max_drop=0.095, column=0.085):
    """Every handwritten number in a question's region, in reading order.

    Handwriting only, which is the whole reason for being here: a printed `452` inside
    "452 = 400 + [ ] + 12" is not the child's answer and can no longer be taken for one, because
    Textract says which words are printed and which are written by hand.

    `column` is deliberately narrow. These papers print four boxes across a page, so their centres
    sit about 0.19 of the page apart, and a tolerance of half that reaches into the neighbour: at
    0.13 the answer to question 1a was a candidate for 1b and won on a rounding tie.

    A labelled "Answer:" box wins when the paper prints one — that is what the paper itself calls
    the final answer, and it is not the same as the last number left lying in the working. Where a
    paper prints its boxes inline instead, the child's digits sit on the question's own line and the
    same region search finds them.
    """
    hand = [w for w in page["words"] if w["hand"] and _NUM.fullmatch(w["text"].strip())
            and _in_region(w, anchor, max_drop, column)]
    label = next(
        (
            ln
            for ln in page["lines"]
            if "answer" in ln["text"].lower()
            and 0 < ln["y"] - anchor["y"] <= max_drop
            and abs(ln["x"] - anchor["x"]) <= column
        ),
        None,
    )
    if label:
        on_label = [w for w in hand if abs(w["y"] - label["y"]) <= label["h"]]
        if on_label:
            hand = on_label
    return sorted(hand, key=lambda w: (round(w["y"], 2), w["x"]))


def answers_for(page, slots):
    """{slot: printed question} → {slot: reading}. Every slot gets an entry; one that cannot be
    located comes back `not_found` rather than silently missing (the defect that lost three answers
    per child on every sheet of one paper)."""
    out, groups = {}, {}
    for slot, question in slots.items():
        anchor = find_question(page["lines"], question)
        groups.setdefault(id(anchor) if anchor else slot, (anchor, []))[1].append(slot)

    for anchor, members in groups.values():
        # Several slots can share one anchor: "452 = 400 + [ ] + [ ]" then "= [ ]" is three answers
        # printed on one line, and each asked on its own would take the same first number. Slots that
        # share a line take the handwriting in reading order — left to right, then down — which is
        # the order they are printed in and the order the child filled them.
        members.sort()
        candidates = _handwriting_near(page, anchor) if anchor else []
        # Reading order only holds when the region offers exactly as many numbers as the page prints
        # boxes. Q5 of the Cambridge paper prints three fill-in boxes INSIDE a line of printed
        # arithmetic, and the child's digits sit among printed ones — a count that does not line up
        # means the region was not understood, and assigning positionally would hand a child's graph
        # an answer chosen by an off-by-one. Those go to a person instead. This is the whole point of
        # `silently_wrong_at_most`: a flagged unknown costs a glance, a confident guess costs trust.
        if anchor and len(candidates) != len(members):
            for slot in members:
                out[slot] = {"child_answer": "", "answer_state": "illegible", "confidence": 0.0}
            continue
        for i, slot in enumerate(members):
            pick = candidates[i] if i < len(candidates) else None
            if pick is None:
                out[slot] = {
                    "child_answer": "",
                    "answer_state": "not_found" if not anchor else "blank",
                    "confidence": 0.0,
                }
            else:
                out[slot] = {
                    "child_answer": pick["text"].replace(",", ""),
                    "answer_state": "written",
                    "confidence": pick["confidence"],
                }
    return out
