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
import cv2
import numpy as np

# Textract's synchronous call refuses an image over 5 MB with `UnsupportedDocumentException`, which
# names neither the size nor the limit. Rendering a page at 250 dpi crosses it. The adapter keeps
# itself inside the limit rather than leaving every caller to discover it: re-encode at falling
# quality, then scale down, so a higher-resolution render degrades instead of failing.
MAX_BYTES = 5_000_000
# Textract also caps the pixel dimensions, and the error names neither the limit nor which of the
# two was exceeded. A WhatsApp scan is already a 4,575 x 6,782 photograph before any render, so a
# higher-dpi render of one crosses this long before it crosses the byte limit.
MAX_SIDE = 10_000

PROFILE = "cornerstone"
REGION = "ap-south-1"
_NUM = re.compile(r"-?\d[\d,]*")
# What the child wrote, as a number: "ans=43" -> "43", "43." -> "43", "1,264" -> "1264". A child
# labels their own answer as often as a paper does, and rejecting anything that is not purely
# numeric threw away every one of those and fell back to the column working above it.
# No minus. Every answer on these papers is a count — apples, birds, marbles — and primary
# addition and subtraction is set so the answer is never negative. A leading "-" is therefore a
# stray pencil mark or an operator from the working alongside, and it was exactly that: a child's
# "64" came back "-64", the only reading in a 45-response gold set that was wrong while claiming to
# be right. This is a property of the PAPER, not of the sum, so reading it off does not smuggle
# arithmetic back into the transcriber (ADR 0019). A paper that can produce negative answers must
# say so before this holds.
# The LAST number in what was read, not the number the text happens to END with. The child's
# answer to "find the mistake" came back as "412-" — the printed answer line runs into the digits
# and Textract reads the stroke as part of the word — and an end-anchored match found no number at
# all there, so a page holding a correct answer was recorded as blank.
_VALUE = re.compile(r"(\d[\d,]*)(?!.*\d)", re.S)
_LABEL = re.compile(r"ans|answer", re.I)
_WORDS = re.compile(r"[A-Za-z]{3,}")


def value_of(text):
    m = _VALUE.search(text.strip().rstrip("."))
    return m.group(1).replace(",", "") if m else None


def client(profile=PROFILE, region=REGION):
    return boto3.Session(profile_name=profile, region_name=region).client("textract")


# How the transcriber finds an answer on a page. Every one of these was tuned against a hand-read
# page, and every one describes how a PAPER is laid out rather than how the code works — the next
# paper will want them different. Rule 1: that is a row to edit, not a Python file to change.
# Defaults here are the measured values, so the module still works against a database that has not
# been loaded yet; `settings(conn)` is what the engine actually uses.
DEFAULTS = {
    "min_confidence": 70.0,  # below this the engine does not stand behind the reading
    "answer_column": 0.085,  # how far either side of a question its answer may sit
    "answer_drop": 0.095,  # how far below, when no following question bounds the region
    "row_band": 0.02,  # answers within this vertically are one row, read left to right
    "first_page_mask": 0.34,  # name band painted out before anything is sent (rule 6)
}


def settings(conn=None):
    """The geometry, from `threshold` rows. Falls back to the measured defaults where a row is
    absent, so a fresh database reads the same way a loaded one does."""
    if conn is None:
        return dict(DEFAULTS)
    rows = conn.execute("select key, value from threshold where key like 'ocr.%%'").fetchall()
    got = {r["key"].split(".", 1)[1]: float(r["value"]) for r in rows}
    return {**DEFAULTS, **{k: v for k, v in got.items() if k in DEFAULTS}}


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
    r = cli.detect_document_text(Document={"Bytes": fit(image_bytes)})
    return assemble(r["Blocks"])


def fit(image_bytes, limit=MAX_BYTES, max_side=MAX_SIDE):
    """An image Textract will accept, losing as little of it as possible."""
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    side = max(img.shape[:2])
    if side > max_side:
        img = cv2.resize(img, None, fx=max_side / side, fy=max_side / side, interpolation=cv2.INTER_AREA)
        image_bytes = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])[1].tobytes()
    if len(image_bytes) <= limit:
        return image_bytes
    for quality in (85, 70, 55):
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if ok and buf.nbytes <= limit:
            return buf.tobytes()
    scale = (limit / buf.nbytes) ** 0.5
    small = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 70])[1].tobytes()


def assemble(blocks):
    """Textract blocks → {"lines", "words"}, each word knowing the line it belongs to.

    The line membership comes from Textract's own Relationships, not from comparing y values: a
    child's digit sits a little above or below the printed text it is squeezed between, and matching
    by position gets that wrong exactly where it matters most.
    """
    by_id = {b["Id"]: b for b in blocks}
    words, lines = [], []
    for b in blocks:
        if b["BlockType"] != "LINE":
            continue
        line = _box(b)
        kids = [
            by_id[i]
            for rel in b.get("Relationships", [])
            if rel["Type"] == "CHILD"
            for i in rel["Ids"]
            if by_id[i]["BlockType"] == "WORD"
        ]
        # A line holding BOTH printed and handwritten words is the paper's own text with the child's
        # writing inserted into it — a fill-in box, or an "Answer:" label with a number after it.
        # A line that is handwriting alone is the child's working, written in blank space. That one
        # distinction separates an answer from rough work, on every layout, without knowing which
        # layout it is.
        line["mixed"] = any(w.get("TextType") == "PRINTED" for w in kids) and any(
            w.get("TextType") == "HANDWRITING" for w in kids
        )
        lines.append(line)
        for k in kids:
            word = _box(k)
            word["mixed_line"] = line["mixed"]
            word["line_text"] = line["text"]
            words.append(word)
    return {"lines": lines, "words": words}


def _norm(s):
    """Compare printed text by its digits and letters alone: OCR renders '148 + 7 =' as '148 +7 =',
    and spacing around operators is the first thing to differ."""
    return re.sub(r"[^0-9a-z]", "", s.lower())


_PLACEHOLDER = re.compile(r"\[\s*\]|□|_{2,}")


def find_question(lines, question, min_overlap=0.6):
    """Where a printed question sits on the page, or None.

    Matched on the question's tokens appearing in order, not on a contiguous string. Two reasons,
    both met on real pages: a question with a fill-in box is no longer contiguous once a child fills
    it — "250 + [ ] = 300" is printed on the page as "250 + 150 = 300" and never matched at all —
    and a word problem wraps, so only its opening survives on any one line.
    """
    want = [tok for tok in _tokens(_PLACEHOLDER.sub(" ", question)) if tok][:8]
    if not want:
        return None
    best, score = None, 0.0
    for ln in lines:
        ratio = _in_order(want, _tokens(ln["text"])) / len(want)
        if ratio > score:
            best, score = ln, ratio
    return best if score >= min_overlap else None


def _tokens(s):
    return re.findall(r"[0-9]+|[a-z]+", s.lower())


def _in_order(want, got):
    """How many of `want` appear in `got` in order, allowing gaps on BOTH sides.

    The child's own digits sitting between the question's tokens never broke the match. A token the
    page itself lost did: scanning once and advancing only on a hit means the first token that never
    turns up stops the count dead. On a Grade 3 photograph Textract read "234 + 178" as "234 + 78" —
    the child's answer loops over the 1 — and question 15 scored 3 of 8 instead of 7 of 8, so it
    never anchored and every answer on that page went to a person. A longest-common-subsequence
    count is the same measure without that cliff, and it can only ever score a line higher.
    """
    row = [0] * (len(want) + 1)
    for tok in got:
        prev = row[:]
        for i, w in enumerate(want, 1):
            row[i] = prev[i - 1] + 1 if tok == w else max(row[i - 1], prev[i])
    return row[-1]


def _in_box(word, box):
    """Is this word inside a question's region?

    The region spans all of a question's parts. A grid question prints four boxes side by side
    across the page, so anchoring on one of them and looking down its column finds a quarter of the
    answers and flags the rest — which is what happened when grouping moved to question numbers.
    """
    return box["top"] <= word["y"] < box["bottom"] and box["left"] <= word["x"] <= box["right"]


def _in_region(word, anchor, max_drop, column, bottom=None):
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
    limit = (bottom - anchor["y"]) if bottom is not None else max_drop
    if not -anchor["h"] <= dy < limit:
        return False
    return anchor["x"] - column <= word["x"] <= anchor["x"] + max(anchor["w"], column)


def _all_handwriting(page, box):
    """Every handwritten number in a question's region, answer and working alike.

    What separates them is which is the answer; what they have in common is that the child wrote
    them. The count of the rest is the third signal — rule 5 keeps "wrong" and "wrong with working
    shown" apart everywhere, because a child who reached a wrong answer through a visible method is
    telling a teacher something a bare wrong answer does not.
    """
    return [w for w in page["words"] if w["hand"] and value_of(w["text"]) and _in_box(w, box)]


def _handwriting_near(page, box, cfg=None):
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
    hand = _all_handwriting(page, box)

    # Ranked, not filtered — each rule applies only where the page offers it.
    #
    # 1. A LABELLED answer wins outright. The paper prints "Answer:" beside a box; a child writes
    #    "ans=43" beside their working. Same statement — this is my final answer — whoever wrote it.
    # 2. Then a number sitting in a SENTENCE. One child answers every question in words — "Simran
    #    took 43 total apples." — with no label anywhere, and scored 0 of 6 until this rule existed.
    #    A child writing prose is declaring an answer; digits stacked in a column are working. The
    #    page says which is which, by whether the line has words on it.
    # 3. Then a line mixing print and handwriting: a fill-in box rather than the scribbles beside it.
    # 4. Failing all three, the region is a free-response box and the handwriting in it is the answer.
    labelled = [w for w in hand if _LABEL.search(w.get("line_text") or "")]
    worded = [w for w in hand if _WORDS.search(w.get("line_text") or "")]
    mixed = [w for w in hand if w.get("mixed_line")]
    hand = labelled or worded or mixed or hand
    return _reading_order(hand, (cfg or DEFAULTS)["row_band"])


def _working_shown(found, answers):
    """How much method the child showed: everything they wrote here beyond the answers themselves.

    "none" and "partial" only — a page cannot say whether a method is complete, and claiming "full"
    would be a judgement the transcriber is not entitled to make.
    """
    return "partial" if found > answers else "none"


def _dedupe(words):
    """Collapse neighbouring candidates that say the same thing.

    Textract merges a child's answer sentence with the working beside it — "Simran took 43 total
    apples- 43" is one line holding two 43s — and two candidates where one answer is expected reads
    as a region not understood, so it went to a person. Two readings that AGREE are not ambiguity;
    two that disagree still are, and those still go to a person.
    """
    out = []
    for w in words:
        if not out or value_of(out[-1]["text"]) != value_of(w["text"]):
            out.append(w)
    return out


def _reading_order(words, row):
    """Words in the order a person reads them: across each row, then down.

    Rows are clustered rather than rounded. These pages are scanned by hand and sit a degree or two
    off square, so four answers printed on one line came back at y = 0.302, 0.306, 0.310 and 0.313 —
    and rounding to two decimals split them across two "rows", putting the rightmost answer first.
    Every child then got their neighbour's answer, confidently and silently.
    """
    out, rest = [], sorted(words, key=lambda w: w["y"])
    while rest:
        top = rest[0]["y"]
        line = [w for w in rest if w["y"] - top <= row]
        rest = rest[len(line) :]
        out.extend(sorted(line, key=lambda w: w["x"]))
    return out


def _number(slot):
    return int("".join(c for c in slot if c.isdigit()) or 0)


def answers_for(page, slots, cfg=None, symbolic=()):
    """{slot: printed question} → {slot: reading}, one entry per slot, never silently missing.

    Grouped by QUESTION NUMBER rather than by the line each part happened to match. Question 5 of
    the Cambridge paper prints three fill-in boxes across three lines, and its parts match each
    other's lines: "452 − 236 = [ ]" matches the line that begins "452 − 236 Regroup…" just as well
    as its own. Matching each part separately therefore put two parts on one anchor and left the
    counts unable to line up, so all three went to a person.

    A question's answers lie between that question and the next one. That is true of every paper
    ever printed, and it needs no per-paper configuration.
    """
    cfg = cfg or DEFAULTS
    anchors = {slot: find_question(page["lines"], q) for slot, q in slots.items()}
    groups = {}
    for slot in slots:
        groups.setdefault(_number(slot), []).append(slot)

    tops = {
        n: min((anchors[s]["y"] for s in members if anchors[s]), default=None)
        for n, members in groups.items()
    }
    ordered = sorted((y, n) for n, y in tops.items() if y is not None)

    out = {}
    for n, members in groups.items():
        members.sort()
        anchor = min((anchors[s] for s in members if anchors[s]), key=lambda a: a["y"], default=None)
        if anchor is None:
            for slot in members:
                out[slot] = {"child_answer": "", "answer_state": "not_found", "confidence": 0.0}
            continue
        below = next((y for y, other in ordered if y > anchor["y"] + 1e-9), None)
        mine = [anchors[s] for s in members if anchors[s]]
        box = {
            # A hair above the question's own line, never a whole line-height above it. A word
            # problem wraps, so its bounding box is two lines tall, and subtracting that height made
            # every region reach up into the one before — question 2 then held question 1's answer
            # as well as its own, and one child who writes her answers as sentences between the
            # questions scored 0 of 6 because every region held two answers and none could be told
            # apart from the other.
            "top": anchor["y"] - 0.005,
            "bottom": below if below is not None else anchor["y"] + cfg["answer_drop"],
            "left": min(a["x"] for a in mine) - cfg["answer_column"],
            "right": max(a["x"] + max(a["w"], cfg["answer_column"]) for a in mine) + cfg["answer_column"],
        }
        working = _working_shown(len(_all_handwriting(page, box)), len(members))
        # Where on the page this answer was read from, as fractions of the page. The approval screen
        # shows a person this patch of the photograph beside what the reader made of it: a teacher
        # who has to hunt down the question on a whole page will not check eighteen of them.
        where = [round(box["left"], 4), round(box["top"], 4), round(box["right"], 4), round(box["bottom"], 4)]
        candidates = _dedupe(_handwriting_near(page, box, cfg))
        if not candidates:
            # The question is on the page and there is no handwriting in its region: the child wrote
            # nothing. That is BLANK, and it is not the same fact as "there is writing I cannot make
            # out" — rule 5 keeps those apart everywhere, and a blank never counts as an attempt.
            # Reporting a blank as unreadable sends a teacher to look at an empty box, and quietly
            # turns "did not answer" into "could not be read".
            for slot in members:
                out[slot] = {
                    "child_answer": "",
                    "answer_state": "blank",
                    "confidence": 0.0,
                    "working_shown": working,
                    "box": where,
                }
            continue
        if len(members) == 1 and len(candidates) > 1:
            # One answer asked for, several numbers in the region: the child's working and then
            # their answer. A child writes the answer AFTER the working, so the last number in
            # reading order is the one they stood behind. Only for a single-answer question —
            # where a question prints several boxes, position decides and guessing is not allowed.
            candidates = candidates[-1:]
        if len(candidates) != len(members):
            # The region was not understood. Assigning positionally would hand a child's graph an
            # answer chosen by an off-by-one, so these go to a person: a flagged unknown costs a
            # glance, a confident guess costs trust.
            for slot in members:
                out[slot] = {
                    "child_answer": "",
                    "answer_state": "illegible",
                    "confidence": 0.0,
                    "working_shown": working,
                    "box": where,
                }
            continue
        for slot, pick in zip(members, candidates):
            sure = pick["confidence"] >= cfg["min_confidence"]
            out[slot] = {
                "child_answer": value_of(pick["text"]) if sure else "",
                "answer_state": "written" if sure else "illegible",
                "confidence": pick["confidence"],
                "working_shown": working,
                "box": where,
            }

    # A slot whose answer is not a number at all — "Compare using >, <, or =: 456 [ ] 465". This
    # reader reads numbers (`value_of`), so it cannot tell a child who wrote "<" from one who wrote
    # nothing, and "blank" is not a flag but a claim: the child did not attempt this skill. That
    # claim went into a Grade 3 graph on a question the child got right. Whatever else is true here,
    # this reader is not entitled to an opinion, so the answer goes to a person.
    for slot in symbolic:
        if slot in out:
            out[slot] = {
                "child_answer": "",
                "answer_state": "illegible",
                "confidence": 0.0,
                "working_shown": out[slot].get("working_shown", "none"),
                "box": out[slot].get("box"),
            }
    return out
