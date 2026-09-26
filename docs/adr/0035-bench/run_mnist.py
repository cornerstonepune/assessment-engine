"""Per box: each inked cell (the same cleaned crop), MNIST-normalised (ink box to 20 px, centred by mass in 28x28,
white on black), classified by (a) the EMNIST-digits CNN, (b) farleyknight-org-username/vit-base-mnist from the hub.
An answer's digits are its inked cells' digits left to right; its confidence the least sure cell's."""
import json, cv2, numpy as np, torch, torch.nn.functional as F
from pathlib import Path
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForImageClassification
import importlib.util
spec = importlib.util.spec_from_file_location("t", "train_emnist.py")
src = open("train_emnist.py").read(); ns = {}
exec(src.split("torch.manual_seed")[0].split("g = \"emnist")[0] + src[src.index("class Net"):src.index("torch.manual_seed")], ns)
D = Path("data"); meta = json.load(open(D / "meta.json")); INK = 0.012
cnn = ns["Net"](); cnn.load_state_dict(torch.load("emnist_cnn.pt")); cnn.eval()
vn = "farleyknight-org-username/vit-base-mnist"
vp = AutoImageProcessor.from_pretrained(vn); vm = AutoModelForImageClassification.from_pretrained(vn).eval()
def mnistify(path):
    g = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE); a = 255 - g; a[a < 60] = 0
    ys, xs = np.nonzero(a)
    if len(xs) == 0: return None
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    s = 20 / max(a.shape); a = cv2.resize(a, (max(1, round(a.shape[1] * s)), max(1, round(a.shape[0] * s))), interpolation=cv2.INTER_AREA)
    c = np.zeros((28, 28), np.uint8); y0, x0 = (28 - a.shape[0]) // 2, (28 - a.shape[1]) // 2; c[y0:y0 + a.shape[0], x0:x0 + a.shape[1]] = a
    m = cv2.moments(c); dx, dy = (14 - m["m10"] / m["m00"], 14 - m["m01"] / m["m00"]) if m["m00"] else (0, 0)
    return cv2.warpAffine(c, np.float32([[1, 0, dx], [0, 1, dy]]), (28, 28))
out = {"emnist_cnn": {}, "vit_mnist": {}}
for m in meta:
    if not m["inked"]: continue
    res = {"emnist_cnn": [], "vit_mnist": []}
    for k, v in enumerate(m["cell_ink"]):
        if v <= INK: continue
        c = mnistify(D / "crops" / f"{m['id']}_c{k}.jpg")
        if c is None: continue
        cv2.imwrite(str(D / "crops" / f"{m['id']}_m{k}.png"), c)
        with torch.no_grad():
            p = F.softmax(cnn(((torch.tensor(c, dtype=torch.float32) / 255 - 0.1307) / 0.3081)[None, None]), 1)[0]
            res["emnist_cnn"].append((int(p.argmax()), float(p.max())))
            q = F.softmax(vm(**vp(images=Image.fromarray(c).convert("RGB"), return_tensors="pt")).logits, 1)[0]
            res["vit_mnist"].append((int(q.argmax()), float(q.max())))
    for r, cells in res.items():
        out[r][m["id"]] = {"digits": "".join(str(d) for d, _ in cells), "confidence": min((p for _, p in cells), default=0.0)}
    print(m["id"], out["emnist_cnn"][m["id"]], out["vit_mnist"][m["id"]], flush=True)
json.dump(out, open(D / "mnist.json", "w"), indent=1)
