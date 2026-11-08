from pathlib import Path
import json, io, itertools
import numpy as np

ROOT = Path(__file__).parent
src = open(ROOT / "classify2.py").read().split("rows = []")[0].replace('"ט": 790', '"ט": 283')
exec(src)

MANUAL = {3: "ע", 286: "ל", 287: "ב", 302: "ז", 327: "ע", 353: "ק", 380: "ל", 668: "א",
          680: "א", 728: "ה", 759: "ל", 763: "ל", 844: "ל", 874: "צ", 881: "ל", 935: "ל",
          954: "ס", 304: "י", 738: "י", 133: "?", 351: "?", 645: "?", 900: "?"}

seq = []
for i in range(len(frames)):
    if i in MANUAL:
        seq.append((i, MANUAL[i], "R" if red[i].sum() > blue[i].sum() else "B")); continue
    if ink[i].sum() == 0:
        seq.append((i, None, "")); continue
    s, k, layer, hit, miss, extra = classify(i)
    if miss <= 0.1 * G[k].sum() and s > 30:
        seq.append((i, k, "R" if (red[i] & G[k]).sum() > (blue[i] & G[k]).sum() else "B"))
    else:
        seq.append((i, None, "sep"))

from scipy.ndimage import binary_dilation

seps = [i for i, k, c in seq if c == "sep" and ink[i].sum() < 60]
overlay = binary_dilation(ink[seps].any(0), np.ones((3, 3)))


def alternatives(i):
    """Glyphs that fit frame i if leftover ink is explained by remnant bars/dots."""
    out = set()
    m = ink[i]
    for k, g0 in G.items():
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                g = np.roll(np.roll(g0, dy, 0), dx, 1)
                if (g & ~m).sum() <= 0.1 * g.sum() and not (m & ~g & ~overlay).sum() > 3:
                    out.add(k)
    return out


ALTS = {}
for i, k, c in seq:
    if k and k != "?" and (ink[i] & overlay).sum() > 0:
        a = alternatives(i) - {k}
        if a:
            ALTS[i] = sorted(a)
json.dump(ALTS, open(ROOT / "alts.json", "w"), ensure_ascii=False)

tokens, cur = [], []
for f, k, c in seq:
    if k:
        cur.append((f, k, c))
    elif cur:
        tokens.append(cur); cur = []
if cur:
    tokens.append(cur)

json.dump(seq, open(ROOT / "seq.json", "w"), ensure_ascii=False)
json.dump(tokens, open(ROOT / "tokens.json", "w"), ensure_ascii=False)


def options(tok):
    """All byte values a token can take; '?' is any letter, ה/ח are interchangeable."""
    pools = []
    for f, k, _ in tok:
        if k == "?":
            pools.append(list(VAL))
        else:
            pool = {k} | set(ALTS.get(f, ALTS.get(str(f), [])))
            if k in "הח":
                pool |= {"ה", "ח"}
            pools.append(sorted(pool))
    vals = set()
    for combo in itertools.product(*pools):
        if "אפס" in combo and len(combo) > 1:
            continue
        v = [VAL[c] for c in combo]
        if v == sorted(v, reverse=True) and len(set(v)) == len(v) and sum(v) <= 255:
            vals.add(sum(v))
    return sorted(vals)


base = []
for t in tokens:
    v = sum(VAL[k] for _, k, _ in t if k != "?")
    base.append(v)
print(len(tokens), "tokens")
print(base)
for n, t in enumerate(tokens):
    if any(k == "?" for _, k, _ in t) or base[n] > 255:
        print(n, [k for _, k, _ in t], [f for f, _, _ in t], options(t)[:20])
