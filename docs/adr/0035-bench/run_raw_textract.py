import json, os, sys, boto3
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "packages/engine"))  # the engine beside this ADR
from engine.adapters import ocr
from engine.w3_read import boxes
D="data/"; meta=json.load(open(D+"meta.json")); cli=boto3.client("textract", region_name=os.environ.get("AWS_REGION","ap-south-1"))
out={}
for m in meta:
    if not m["inked"]: continue
    b=open(D+f"crops/{m['id']}_raw.png","rb").read()
    words=sorted(ocr.read(b,cli)["words"], key=lambda w:w["x"])
    d,c,doubt=boxes.decide(words,m["inked"],70.0)
    out[m["id"]]={"digits":d,"confidence":c/100,"doubt":doubt,"words":[w["text"] for w in words]}
json.dump(out,open(D+"textract_raw.json","w"),indent=1); print(len(out))
