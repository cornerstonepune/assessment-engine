"""Cut every answer of the 24 Sep scan out exactly as the branch's box reader does, and read each with Textract
the way production does (boxes.read_page's path). Writes crops/<id>_strip.png (what Textract sees),
crops/<id>_raw.png (the settled run, nothing removed), crops/<id>_c<k>.png (one cleaned cell each) and meta.json."""

import json, os, sys, urllib.request
from pathlib import Path

import boto3, cv2, numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "packages/engine"))  # the engine beside this ADR
from engine.adapters import ocr
from engine.assess.geometry import cells_of
from engine.w3_read import boxes, render_pdf

D = Path(__file__).parent / "data"
C = D / "crops"
C.mkdir(parents=True, exist_ok=True)
URL, KEY = os.environ["ENGINE_URL"], os.environ["ENGINE_KEY"]


def get(path, out=None):
    req = urllib.request.Request(URL + path, headers={"X-Engine-Key": KEY})
    body = urllib.request.urlopen(req, timeout=60).read()
    if out:
        Path(out).write_bytes(body)
        return out
    return json.loads(body)


cli = boto3.client("textract", region_name=os.environ.get("AWS_REGION", "ap-south-1"))
copies = json.load(open(D / "copies.json"))
meta = []
for i, cp in enumerate(copies, start=1):
    code = cp["code"]
    pdf = D / f"{code}.pdf"
    if not pdf.exists():
        get(f"/worksheet/{code}.pdf", pdf)
    geom = get(f"/worksheet/{code}/geometry")["geometry"]
    img, frame = render_pdf.photo(D / "24sep.pdf", i)
    canon, M = boxes.line_up(img, pdf, 1)
    if canon is None:
        print(cp["copy"], "did not line up")
        continue
    printed = boxes.blank(str(pdf), 1)
    grey = cv2.cvtColor(canon, cv2.COLOR_BGR2GRAY)
    is_dark = boxes.dark(canon)
    runs, _ = cells_of(geom, 1)
    for q, ((item, rid), run) in enumerate(sorted(runs.items(), key=lambda kv: (kv[1][0]["y"], kv[1][0]["x"]))):
        aid = f"{cp['copy']}_q{q + 1:02d}"
        run = boxes.settle(grey, printed, run)
        inks = [boxes.ink(is_dark, printed, c) for c in run]
        inked = sum(v > boxes.INK for v in inks)
        strip = boxes.strip(canon, printed, run, is_dark)
        (C / f"{aid}_strip.jpg").write_bytes(strip)
        x0 = min(boxes._px(c)[0] for c in run) - 20
        y0 = min(boxes._px(c)[1] for c in run) - 20
        x1 = max(boxes._px(c)[2] for c in run) + 20
        y1 = max(boxes._px(c)[3] for c in run) + 20
        cv2.imwrite(str(C / f"{aid}_raw.png"), canon[y0:y1, x0:x1])
        for k, c in enumerate(run):
            (C / f"{aid}_c{k}.jpg").write_bytes(boxes.strip(canon, printed, [c], is_dark))
        rec = {"id": aid, "copy": cp["copy"], "code": code, "item": item, "boxes": len(run), "inked": inked,
               "cell_ink": [round(v, 4) for v in inks]}
        if inked:
            words = sorted(ocr.read(strip, cli)["words"], key=lambda w: w["x"])
            digits, conf, doubt = boxes.decide(words, inked, ocr.DEFAULTS["min_confidence"])
            rec["textract"] = {"words": [{k: w[k] for k in ("text", "confidence", "x", "w", "hand")} for w in words],
                               "digits": digits, "confidence": conf, "doubt": doubt}
        meta.append(rec)
    print(cp["copy"], code, len(runs), "answers", flush=True)
json.dump(meta, open(D / "meta.json", "w"), indent=1)
print(len(meta), "answers;", sum(1 for m in meta if m["inked"]), "inked")
