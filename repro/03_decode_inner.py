# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "numpy",
#     "pillow",
# ]
# ///

# usage: 03_decode_inner.py <workdir>
# Layers 2-3. Turns letter bursts into bytes (gematria), repairs the inner GIF's
# LZW data with a minimal-change search, keeps the one stream a greedy LZW
# encoder could have produced, and writes inner.gif + transcription_bytes.txt.
import itertools
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.setrecursionlimit(100000)
ROOT = Path(sys.argv[1])
tokens = json.load(open(ROOT / "tokens.json"))
ALTS = {int(k): v for k, v in json.load(open(ROOT / "alts.json")).items()}

VAL = dict(zip("אבגדהוזחטיכלמנסעפצקר", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 200]))
VAL["אפס"] = 0


def options(tok):
    """Byte values a burst can take: '?' is any letter, ה/ח are confusable, plus ALTS."""
    pools = []
    for f, k, _ in tok:
        if k == "?":
            pools.append(list(VAL))
            continue
        pool = {k} | set(ALTS.get(f, []))
        if k in "הח":
            pool |= {"ה", "ח"}
        pools.append(sorted(pool))
    vals = set()
    for combo in itertools.product(*pools):
        if "אפס" in combo and len(combo) > 1:
            continue
        v = [VAL[c] for c in combo]
        # Hebrew numerals are written largest-first with no repeats
        if v == sorted(v, reverse=True) and len(set(v)) == len(v) and sum(v) <= 255:
            vals.add(sum(v))
    return sorted(vals)


base = [sum(VAL[k] for _, k, _ in t if k != "?") for t in tokens]
assert len(base) == 336, len(base)
assert bytes(base[22:82]) == b"redherring" * 6
assert bytes(base[:6]) == b"GIF89a"
assert base[93] == 2 and base[94] == 239 and base[-1] == 0x3B

D0, D1 = 95, 95 + 239  # the single LZW data sub-block
W, H = base[6] | base[7] << 8, base[8] | base[9] << 8
NPIX, MINC, NCOLORS = W * H, base[93], 2
CLEAR, EOI = 1 << MINC, (1 << MINC) + 1

first, length = [], []


def reset():
    del first[:], length[:]
    for k in range(CLEAR + 2):
        first.append(k if k < NCOLORS else -1)
        length.append(1 if k < NCOLORS else 0)


def feed(st, byte):
    """Incremental strict LZW check. Returns new state, or None if the byte breaks the stream."""
    acc, nacc, size, prev, outlen, ended = st
    if ended:
        return None if byte else st
    acc |= byte << nacc
    nacc += 8
    while nacc >= size:
        code = acc & ((1 << size) - 1)
        acc >>= size
        nacc -= size
        if code == CLEAR:
            if outlen:
                return None
            reset()
            size, prev = MINC + 1, None
            continue
        if code == EOI:
            if outlen != NPIX or acc:
                return None
            return (0, 0, size, prev, outlen, True)
        n = len(first)
        if prev is None:
            if code >= NCOLORS:
                return None
            l = 1
        elif code < n and length[code] > 0:
            l = length[code]
        elif code == n:
            l = length[prev] + 1
        else:
            return None
        if outlen + l > NPIX:
            return None
        if prev is not None:
            first.append(first[prev])
            length.append(length[prev] + 1)
            if len(first) == (1 << size) and size < 12:
                size += 1
        outlen += l
        prev = code
    return (acc, nacc, size, prev, outlen, False)


UNK = {i for i in range(D0, D1) if any(k == "?" for _, k, _ in tokens[i])}
cands = []
for i in range(D0, D1):
    opts = options(tokens[i])
    if i in UNK:
        cands.append([(v, 0) for v in opts])
    else:
        cands.append([(base[i], 0)] + [(v, 1) for v in opts if v != base[i]])

data = [c[0][0] for c in cands]
sols = []
LIMIT = 200


def dfs(k, st, budget):
    if len(sols) >= LIMIT:
        return
    if k == len(data):
        if st[5] or st[4] == NPIX:
            sols.append(list(data))
        return
    n = len(first)
    for v, c in cands[k]:
        if c > budget:
            continue
        ns = feed(st, v)
        if ns is not None:
            data[k] = v
            dfs(k + 1, ns, budget - c)
        del first[n:], length[n:]
    data[k] = cands[k][0][0]


for budget in range(6):
    sols = []
    reset()
    dfs(0, (0, 0, MINC + 1, None, 0, False), budget)
    print("changed letters allowed:", budget, "valid streams found:", len(sols), flush=True)
    if sols:
        break


def greedy_violations(stream):
    """Times a code was emitted although a longer match (prev + next pixel) was
    already in the dictionary. A greedy encoder (Pillow, and this file's author,
    across the outer GIF) never does this."""
    table = [bytes([k]) for k in range(CLEAR)] + [b"", b""]
    known = {t: k for k, t in enumerate(table[:CLEAR])}
    acc = nb = v = 0
    size, prev = MINC + 1, None
    for byte in stream:
        acc |= byte << nb
        nb += 8
        while nb >= size:
            code = acc & ((1 << size) - 1)
            acc >>= size
            nb -= size
            if code == CLEAR:
                continue
            if code == EOI:
                return v
            e = table[code] if code < len(table) else prev + prev[:1]
            if prev is not None:
                new = prev + e[:1]
                v += new in known
                known.setdefault(new, len(table))
                table.append(new)
                if len(table) == 1 << size and size < 12:
                    size += 1
            prev = e
    return v


viol = [greedy_violations(bytes(s)) for s in sols]
print("greedy-LZW violations per stream:", viol)
sols = [s for _, s in sorted(zip(viol, sols), key=lambda p: p[0])]
assert sorted(viol)[0] == 0 and sorted(viol)[1:2] != [0], "expected exactly one greedy stream"
json.dump(sols, open(ROOT / "inner_solutions.json", "w"))

full = list(base)
full[D0:D1] = sols[0]
gif = bytes(full)
(ROOT / "inner.gif").write_bytes(gif)
im = Image.open(ROOT / "inner.gif")
im.load()
print("inner.gif:", im.size, "comment:", im.info.get("comment"))
im.convert("L").resize((im.width * 8, im.height * 8), Image.Resampling.NEAREST).save(ROOT / "inner_x8.png")

sheet = Image.new("RGB", (4 * 300, 2 * 230), "white")
dr = ImageDraw.Draw(sheet)
pick = list(range(0, len(sols), max(1, len(sols) // 8)))[:8]
for j, s in enumerate(pick):
    full[D0:D1] = sols[s]
    a = np.array(Image.open(__import__("io").BytesIO(bytes(full))).convert("L"))
    x, y = (j % 4) * 300, (j // 4) * 230
    sheet.paste(Image.fromarray(a).resize((288, 204), Image.Resampling.NEAREST), (x, y))
    dr.text((x, y + 208), f"candidate {s}", fill="red")
sheet.save(ROOT / "inner_candidates.png")

lines = []
for n, t in enumerate(tokens):
    letters = "".join(k for _, k, _ in t)
    colors = "".join(c for _, _, c in t)
    raw = None if n in UNK or n == 44 else sum(VAL[k] for _, k, _ in t)
    b = gif[n]
    ch = chr(b) if 32 <= b < 127 else "."
    note = "" if raw == b else f"  (read {raw}, repaired)"
    lines.append(f"{n:3d}  frames {t[0][0]}-{t[-1][0]}  {letters:<4} {colors:<4} = {b:3d} {ch}{note}")
(ROOT / "transcription_bytes.txt").write_text("\n".join(lines) + "\n")
print("wrote inner.gif, inner_candidates.png, transcription_bytes.txt")
