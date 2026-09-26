"""TrOCR (microsoft/trocr-base-handwritten) on the same cleaned strip Textract sees. Off the shelf: no fine-tuning."""
import json, re
from pathlib import Path

import torch
from PIL import Image
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

D = Path(__file__).parent / "data"
meta = json.load(open(D / "meta.json"))
name = "microsoft/trocr-base-handwritten"
proc = TrOCRProcessor.from_pretrained(name)
model = VisionEncoderDecoderModel.from_pretrained(name).eval()
out = {}
for m in meta:
    if not m["inked"]:
        continue
    img = Image.open(D / "crops" / f"{m['id']}_strip.jpg").convert("RGB")
    px = proc(images=img, return_tensors="pt").pixel_values
    with torch.no_grad():
        g = model.generate(px, max_new_tokens=16, num_beams=1, output_scores=True, return_dict_in_generate=True)
    text = proc.batch_decode(g.sequences, skip_special_tokens=True)[0]
    lp = model.compute_transition_scores(g.sequences, g.scores, normalize_logits=True)[0]
    conf = float(torch.exp(lp.sum()))  # probability of the whole sequence, greedy
    out[m["id"]] = {"text": text, "digits": re.sub(r"\D", "", text), "confidence": conf}
    print(m["id"], repr(text), round(conf, 3), flush=True)
json.dump(out, open(D / "trocr.json", "w"), indent=1)
