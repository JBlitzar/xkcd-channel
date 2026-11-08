# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "numpy",
#     "scipy",
# ]
# ///

# usage: 02_transcribe_frames.py <workdir>
# Reads frames.npy, classifies every frame, writes seq.json, tokens.json,
# alts.json and transcription_frames.tsv.
import json
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_dilation, label

ROOT = Path(sys.argv[1])
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


# Frame index of a clean exemplar for each glyph, picked by eye from the
# clustering montages.
EX = {"א": 1, "ב": 18, "ג": 4, "ד": 58, "ה": 86, "ו": 9, "ז": 12, "ח": 29, "ט": 283,
      "י": 63, "כ": 28, "ל": 53, "מ": 256, "נ": 8, "ס": 60, "ע": 0, "פ": 316,
      "צ": 14, "ק": 27, "ר": 35, "אפס": 20}
G = {k: clean(ink[i]) for k, i in EX.items()}

# Frames where static overlaps a letter so badly that template matching fails.
# Labels were read by eye; "?" means the letter is unreadable.
# 403 looks like static but is a noisy נ (the only "static" frame that draws ink
# inside its own frame rectangle); 954 has the open top of ט, not ס.
MANUAL = {3: "ע", 286: "ל", 287: "ב", 302: "ז", 327: "ע", 353: "ק", 380: "ל", 668: "א",
          680: "א", 728: "ה", 759: "ל", 763: "ל", 844: "ל", 874: "צ", 881: "ל", 935: "ל",
          954: "ט", 403: "נ", 304: "י", 738: "י", 133: "?", 351: "?", 645: "?", 900: "?"}

SHIFTS = [(dy, dx) for dy in range(-3, 4) for dx in range(-3, 4)]


def shifted(g):
    for dy, dx in SHIFTS:
        yield np.roll(np.roll(g, dy, 0), dx, 1)


def classify(i):
    """Best template: reward covered template pixels, penalize missing and extra ink."""
    m = ink[i]
    best = None
    for k, g0 in G.items():
        for g in shifted(g0):
            miss = (g & ~m).sum()
            s = (g & m).sum() - 2 * miss - 0.5 * (m & ~g).sum()
            if best is None or s > best[0]:
                best = (s, k, miss)
    return best


seq = []
for i in range(len(frames)):
    color = "R" if red[i].sum() > blue[i].sum() else "B"
    if i in MANUAL:
        seq.append((i, MANUAL[i], color))
        continue
    if ink[i].sum() == 0:
        seq.append((i, None, ""))
        continue
    s, k, miss = classify(i)
    if miss <= 0.1 * G[k].sum() and s > 30:
        g = G[k]
        seq.append((i, k, "R" if (red[i] & g).sum() > (blue[i] & g).sum() else "B"))
    else:
        seq.append((i, None, "sep"))  # static / remnant bars

# Letters whose leftover ink is explained by remnant static could also be a
# smaller glyph hidden underneath (mostly ט that may really be ס).
seps = [i for i, k, c in seq if c == "sep" and ink[i].sum() < 60]
overlay = binary_dilation(ink[seps].any(0), np.ones((3, 3)))
ALTS = {}
for i, k, c in seq:
    if k and k != "?" and (ink[i] & overlay).sum() > 0:
        alts = set()
        for k2, g0 in G.items():
            for g in shifted(g0):
                if (g & ~ink[i]).sum() <= 0.1 * g.sum() and (ink[i] & ~g & ~overlay).sum() <= 3:
                    alts.add(k2)
                    break
        alts.discard(k)
        if alts:
            ALTS[i] = sorted(alts)

tokens, cur = [], []
for f, k, c in seq:
    if k:
        cur.append((f, k, c))
    elif cur:
        tokens.append(cur)
        cur = []
if cur:
    tokens.append(cur)

json.dump(seq, open(ROOT / "seq.json", "w"), ensure_ascii=False)
json.dump(tokens, open(ROOT / "tokens.json", "w"), ensure_ascii=False)
json.dump(ALTS, open(ROOT / "alts.json", "w"), ensure_ascii=False)
with open(ROOT / "transcription_frames.tsv", "w") as f:
    f.write("frame\tcontent\tcolor\n")
    for i, k, c in seq:
        content = ("unreadable" if k == "?" else k) if k else ("static" if c == "sep" else "blank")
        f.write(f"{i}\t{content}\t{c if k else ''}\n")
print("frames", len(seq), "letter bursts", len(tokens), "alts", len(ALTS))
print(" ".join(k for t in tokens for _, k, _ in t))
