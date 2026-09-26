import json
D="data/"; meta={m["id"]:m for m in json.load(open(D+"meta.json"))}; gold=json.load(open(D+"gold.json"))
tr=json.load(open(D+"trocr.json")); pd=json.load(open(D+"paddle.json")); mn=json.load(open(D+"mnist.json"))
ids=[i for i,g in gold.items() if g not in ("?","")]
R={}
R["Textract (production path)"]={i:(meta[i]["textract"]["digits"],meta[i]["textract"]["confidence"]/100) for i in ids}
R["TrOCR base-handwritten"]={i:(tr[i]["digits"],tr[i]["confidence"]) for i in ids}
R["PaddleOCR det+rec"]={i:(pd[i]["pipeline"]["digits"],pd[i]["pipeline"]["confidence"]) for i in ids}
R["PaddleOCR rec only"]={i:(pd[i]["rec"]["digits"],pd[i]["rec"]["confidence"]) for i in ids}
R["EMNIST CNN, per box"]={i:(mn["emnist_cnn"][i]["digits"],mn["emnist_cnn"][i]["confidence"]) for i in ids}
R["ViT-MNIST (hub), per box"]={i:(mn["vit_mnist"][i]["digits"],mn["vit_mnist"][i]["confidence"]) for i in ids}
def agree(a,b):
    out={}
    for i in ids:
        (da,ca),(db,cb)=R[a][i],R[b][i]
        out[i]=(da, min(ca,cb)) if da==db else (da,0.0)
    return out
tx=json.load(open(D+"textract_raw.json")); pr=json.load(open(D+"paddle_raw.json")); trr=json.load(open(D+"trocr_raw.json"))
R["RAW Textract"]={i:(tx[i]["digits"],tx[i]["confidence"]) for i in ids}
R["RAW PaddleOCR det+rec"]={i:(pr[i]["pipeline"]["digits"],pr[i]["pipeline"]["confidence"]) for i in ids}
R["RAW PaddleOCR rec only"]={i:(pr[i]["rec"]["digits"],pr[i]["rec"]["confidence"]) for i in ids}
R["RAW TrOCR"]={i:(trr[i]["digits"],trr[i]["confidence"]) for i in ids}
R["RAW Paddle det+rec AND RAW Textract"]=agree("RAW PaddleOCR det+rec","RAW Textract")
R["Paddle det+rec AND Textract agree"]=agree("PaddleOCR det+rec","Textract (production path)")
R["Paddle rec AND Paddle det+rec agree"]=agree("PaddleOCR rec only","PaddleOCR det+rec")
n=len(ids); print(f"{n} answers with a sure gold (of 168; 27 unsure, 8 blank left out)\n")
print(f"{'reader':38} {'exact':>9} | {'floor .70: stands / wrong':>26} | {'floor .90: stands / wrong':>26} | zero-wrong best (tuned on test)")
rows=[]
for name,r in R.items():
    ex=sum(r[i][0]==gold[i] for i in ids)
    cols=[]
    for f in (0.70,0.90):
        st=[i for i in ids if len(r[i][0])==meta[i]["inked"] and r[i][1]>=f]
        wr=[i for i in st if r[i][0]!=gold[i]]
        cols.append((len(st),len(wr),wr))
    # tuned: highest count standing with no wrong, over thresholds = each item's confidence
    best=0
    for t in sorted({r[i][1] for i in ids}):
        st=[i for i in ids if len(r[i][0])==meta[i]["inked"] and r[i][1]>=t]
        if st and all(r[i][0]==gold[i] for i in st): best=max(best,len(st))
    rows.append((name,ex,cols,best))
    print(f"{name:38} {ex:3}/{n} {100*ex/n:4.0f}% | {cols[0][0]:3} stand, {cols[0][1]:2} wrong ({100*cols[0][0]/n:3.0f}%) | {cols[1][0]:3} stand, {cols[1][1]:2} wrong ({100*cols[1][0]/n:3.0f}%) | {best}")
print()
for name,ex,cols,best in rows:
    if cols[0][2]: print(name, "wrong it stood behind @.70:", [(i, R[name][i][0], gold[i]) for i in cols[0][2]])
