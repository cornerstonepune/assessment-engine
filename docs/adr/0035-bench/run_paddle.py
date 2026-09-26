"""PaddleOCR 3.x, off the shelf, on the same cleaned strip: (a) the full pipeline (detect + recognise), (b) the
recogniser alone on the whole strip."""
import json, re, sys
from pathlib import Path
from paddleocr import PaddleOCR, TextRecognition

D = Path(__file__).parent / "data"
meta = json.load(open(D / "meta.json"))
pipe = PaddleOCR(use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False, lang="en", enable_mkldnn=False)
rec = TextRecognition(enable_mkldnn=False)
out = {}
for m in meta:
    if not m["inked"]:
        continue
    p = str(D / "crops" / f"{m['id']}_strip.jpg")
    r = pipe.predict(p)[0]
    polys = r["rec_polys"]; texts = r["rec_texts"]; scores = r["rec_scores"]
    order = sorted(range(len(texts)), key=lambda i: float(min(pt[0] for pt in polys[i])))
    ptext = " ".join(texts[i] for i in order)
    pconf = float(min((scores[i] for i in order), default=0.0))
    q = rec.predict(p)[0]
    out[m["id"]] = {
        "pipeline": {"text": ptext, "digits": re.sub(r"\D", "", ptext), "confidence": pconf},
        "rec": {"text": q["rec_text"], "digits": re.sub(r"\D", "", q["rec_text"]), "confidence": float(q["rec_score"])},
    }
    print(m["id"], out[m["id"]], flush=True)
json.dump(out, open(D / "paddle.json", "w"), indent=1)
