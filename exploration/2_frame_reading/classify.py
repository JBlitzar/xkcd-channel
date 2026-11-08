from pathlib import Path
import json
import numpy as np

ROOT = Path(__file__).parent
frames = np.load(ROOT / "frames.npy").astype(int)
bg = np.array([255, 225, 255])
red = (frames[..., 0] > 200) & (frames[..., 1] < 120)
blue = (frames[..., 2] > 200) & (frames[..., 0] < 120)
ink = red | blue

TEMPL = {0: "ע", 1: "א", 2: "ג", 3: "נ", 4: "ו", 5: "ז", 6: "צ", 7: "ב", 8: "אפס",
         9: "ק", 10: "כ", 11: "ח", 12: "ר", 13: "ל", 14: "ד", 15: "ס", 16: "י",
         18: "מ", 26: "ה", 29: "פ", 62: "ט"}
clusters = json.load(open(ROOT / "clusters2.json"))


def clean(m):
    from scipy.ndimage import label
    lab, n = label(m)
    out = np.zeros_like(m)
    for k in range(1, n + 1):
        b = lab == k
        if b.sum() >= 10:
            out |= b
    return out


cm = np.array([clean(m) for m in ink])
temps = {TEMPL[i]: cm[clusters[i]["rep"]] for i in TEMPL}


def dist(a, b):
    best = 9
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            s = np.roll(np.roll(a, dy, 0), dx, 1)
            d = (s ^ b).sum() / max(1, (s | b).sum())
            best = min(best, d)
    return best


rows = []
for i in range(len(frames)):
    n = cm[i].sum()
    raw = ink[i].sum()
    if raw == 0:
        rows.append((i, "blank", "", 0, 0)); continue
    col = "R" if red[i].sum() > blue[i].sum() else "B"
    both = red[i].sum() > 5 and blue[i].sum() > 5
    if n < 15:
        rows.append((i, "dots" if raw <= 16 else "fragment", col, raw, 0)); continue
    scored = sorted((dist(cm[i], t), k) for k, t in temps.items())
    d, k = scored[0]
    kind = k if d < 0.2 else "?" + k
    if both:
        col = "R+B"
    rows.append((i, kind, col, raw, round(d, 3)))

with open(ROOT / "frames_classified.tsv", "w") as f:
    f.write("frame\tsymbol\tcolor\tinkpx\tdist\n")
    for r in rows:
        f.write("\t".join(map(str, r)) + "\n")
from collections import Counter
print(Counter(r[1] for r in rows).most_common())
