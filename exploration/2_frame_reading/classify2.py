from pathlib import Path
import json
import numpy as np
from scipy.ndimage import label

ROOT = Path(__file__).parent
frames = np.load(ROOT / "frames.npy").astype(int)
red = (frames[..., 0] > 200) & (frames[..., 1] < 120)
blue = (frames[..., 2] > 200) & (frames[..., 0] < 120)
ink = red | blue


def clean(m):
    lab, n = label(m)
    out = np.zeros_like(m)
    for k in range(1, n + 1):
        if (lab == k).sum() >= 10:
            out |= lab == k
    return out


# clean exemplar frames for each glyph (value = gematria; אפס = 0)
EX = {"א": 1, "ב": 18, "ג": 4, "ד": 58, "ה": 86, "ו": 9, "ז": 12, "ח": 29, "ט": 790,
      "י": 63, "כ": 28, "ל": 53, "מ": 256, "נ": 8, "ס": 60, "ע": 0, "פ": 316,
      "צ": 14, "ק": 27, "ר": 35, "אפס": 20}
VAL = dict(zip("אבגדהוזחטיכלמנסעפצקר", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 200]))
VAL["אפס"] = 0
G = {k: clean(ink[i]) for k, i in EX.items()}


def classify(i):
    best = None
    layer, m = "RB", ink[i]
    for k, g0 in G.items():
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                g = np.roll(np.roll(g0, dy, 0), dx, 1)
                hit = (g & m).sum()
                miss = (g & ~m).sum()
                s = hit - 2 * miss - 0.5 * (m & ~g).sum()
                if best is None or s > best[0]:
                    best = (s, k, layer, hit, miss, (m & ~g).sum())
    return best


rows = []
for i in range(len(frames)):
    n = ink[i].sum()
    if n == 0:
        rows.append(dict(f=i, kind="blank")); continue
    if clean(ink[i]).sum() < 15:
        rows.append(dict(f=i, kind="dots", px=int(n))); continue
    s, k, layer, hit, miss, extra = classify(i)
    ok = miss <= 0.1 * G[k].sum() and s > 30
    rows.append(dict(f=i, kind="glyph" if ok else "static", sym=k, color=layer,
                     miss=int(miss), extra=int(extra), size=int(G[k].sum())))

json.dump(rows, open(ROOT / "frames2.json", "w"), ensure_ascii=False)

tokens, cur = [], []
for r in rows:
    if r["kind"] == "glyph":
        cur.append(r)
    else:
        if cur:
            tokens.append(cur)
        cur = []
if cur:
    tokens.append(cur)
vals = [sum(VAL[r["sym"]] for r in t) for t in tokens]
print("tokens", len(tokens), "static frames", sum(r["kind"] == "static" for r in rows))
print(vals)
json.dump([[r["f"] for r in t] for t in tokens], open(ROOT / "tokens.json", "w"))
open(ROOT / "inner.bin", "wb").write(bytes(min(v, 255) for v in vals))
print("over255", [(i, v) for i, v in enumerate(vals) if v > 255])
