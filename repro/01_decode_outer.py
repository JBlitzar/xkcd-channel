from pathlib import Path
from collections import Counter
import io, sys, json

sys.setrecursionlimit(1000000)
# usage: 01_decode_outer.py <channel.txt> <workdir>
SRC, ROOT = Path(sys.argv[1]), Path(sys.argv[2])
ROOT.mkdir(parents=True, exist_ok=True)
raw = SRC.read_bytes()
forms = "〇一二三四五六七八九零壹贰叁肆伍陆柒捌玖"
digits = [(c.encode(), str(i % 10)) for i, c in enumerate(forms)]


def nearest(chunk):
    s = [(sum((a - b) ** 2 for a, b in zip(chunk, e)), d) for e, d in digits]
    s.sort()
    return s


tokens = []
cur = None
i = 0
while i < len(raw):
    if raw[i] < 64:
        if cur:
            tokens.append(cur)
            cur = None
        i += 1
        continue
    ch = nearest(raw[i:i + 3])
    best = ch[0][0]
    # LSB-flip noise can silently move a chunk closer to the wrong digit
    # (e.g. 二 vs 伍), so keep every digit within the max noise radius.
    opts = tuple(sorted(d for s, d in ch if s <= 3))
    if cur is None:
        cur = []
    cur.append(opts)
    i += 3
if cur:
    tokens.append(cur)

import itertools as _it
nums = []
alts = {}
nbad = 0
for t in tokens:
    base = int("".join(o[0] for o in t))
    vals = sorted({int("".join(combo)) for combo in _it.product(*t)})
    valid = [v for v in vals if v <= 255]
    if base > 255:
        nbad += 1
        base = valid[0]  # nearest decode impossible for a byte; take a valid one
    nums.append(base)
    av = [v for v in valid if v != base]
    if av:
        alts[len(nums) - 1] = av
print("bytes:", len(nums), "ambiguous:", len(alts), "base>255:", nbad)

CANVAS = 40


def cand(i):
    return [nums[i]] + alts.get(i, [])


def lzw_strict(data, mincode, npix):
    """Decode GIF LZW. Return pixel list iff the stream yields exactly npix
    pixels, ends with EOI, and has only zero padding bits left."""
    clear = 1 << mincode
    eoi = clear + 1
    nbits = len(data) * 8
    pos = 0
    size = mincode + 1
    dict_ = [[k] for k in range(clear)] + [None, None]
    nextcode = eoi + 1
    prev = None
    out = []

    def read(n):
        nonlocal pos
        if pos >= nbits:
            return None
        v = 0
        over = 0
        for k in range(n):
            if pos + k < nbits:
                v |= ((data[(pos + k) >> 3] >> ((pos + k) & 7)) & 1) << k
            else:
                over += 1  # implicit zero padding past the last byte
        pos += n
        return v, over

    while True:
        r = read(size)
        if r is None:
            return None
        code, over = r
        if over and code != eoi:
            return None
        if code == clear:
            dict_ = [[k] for k in range(clear)] + [None, None]
            nextcode = eoi + 1
            size = mincode + 1
            prev = None
            continue
        if code == eoi:
            if len(out) != npix:
                return None
            # all real bits after EOI must be zero padding
            for k in range(min(pos, nbits), nbits):
                if (data[k >> 3] >> (k & 7)) & 1:
                    return None
            return out
        if prev is None:
            if code >= clear:
                return None
            entry = dict_[code]
            out.extend(entry)
            prev = code
            continue
        if code < len(dict_) and dict_[code] is not None:
            entry = dict_[code]
        elif code == nextcode:
            entry = dict_[prev] + [dict_[prev][0]]
        else:
            return None
        out.extend(entry)
        if len(out) > npix:
            return None
        dict_.append(dict_[prev] + [entry[0]])
        nextcode += 1
        if nextcode == (1 << size) and size < 12:
            size += 1
        prev = code


def pixels_ok(iw, ih, mincode, data):
    return lzw_strict(data, mincode, iw * ih) is not None


MAXCOMBO = 400000


def data_fixes(iw, ih, mincode, dbytes, didx):
    """Return list of fix-dicts that make the frame strictly decode."""
    import itertools
    if pixels_ok(iw, ih, mincode, dbytes):
        return [{}]
    amb = [(k, i) for k, i in enumerate(didx) if i in alts]
    if not amb:
        return []
    pools = [[(k, nums[i])] + [(k, v) for v in alts[i]] for k, i in amb]
    total = 1
    for p in pools:
        total *= len(p)
    out = []
    if total <= MAXCOMBO:
        combos = itertools.product(*pools)
    else:
        # too many: greedy singles only
        combos = ([(k, v)] for k, i in amb for v in alts[i])
    for combo in combos:
        d2 = dbytes[:]
        fx = {}
        for k, v in combo:
            i = didx[k]
            if v != nums[i]:
                d2[k] = v
                fx[i] = v
        if pixels_ok(iw, ih, mincode, d2):
            out.append(fx)
            if len(out) >= 8:
                break
    return out


def frame_candidates(start):
    """All (endpos, fixes, meta) for an image block at start."""
    res = []
    for b0 in cand(start):
        if b0 != 0x2C:
            continue
        desc_idx = range(start + 1, start + 11)
        # enumerate descriptor combos but prune aggressively
        import itertools
        pools = []
        for i in desc_idx:
            pools.append(cand(i))
        for combo in itertools.product(*pools):
            left = combo[0] | combo[1] << 8
            top = combo[2] | combo[3] << 8
            iw = combo[4] | combo[5] << 8
            ih = combo[6] | combo[7] << 8
            ipacked = combo[8]
            mincode = combo[9]
            if ipacked & 0xE0 or not (2 <= mincode <= 8):
                continue
            if not (1 <= iw <= CANVAS and 1 <= ih <= CANVAS):
                continue
            if left + iw > CANVAS or top + ih > CANVAS:
                continue
            descfix = {start + 1 + k: v for k, v in enumerate(combo)
                       if v != nums[start + 1 + k]}
            # sub-block walk with branching on ambiguous length bytes
            states = [(start + 11, {}, [])]  # pos, fixes, data byte indices
            while states:
                p, fx, didx = states.pop()
                if p >= len(nums):
                    continue
                for sz in cand(p):
                    if sz == 0:
                        data = [nums[i] for i in didx]
                        for dfix in data_fixes(iw, ih, mincode, data, didx):
                            allfix = dict(fx)
                            allfix.update(descfix)
                            allfix.update(dfix)
                            res.append((p + 1, allfix,
                                        {"left": left, "top": top, "w": iw,
                                         "h": ih, "mincode": mincode,
                                         "didx": didx}))
                        continue
                    if p + 1 + sz > len(nums):
                        continue
                    fx2 = dict(fx)
                    if sz != nums[p]:
                        fx2[p] = sz
                    states.append((p + 1 + sz, fx2,
                                   didx + list(range(p + 1, p + 1 + sz))))
        # data flips never change the end position; keep one fix set per end
        dedup = {}
        for endpos, fx, meta in res:
            dedup.setdefault(endpos, (endpos, fx, meta))
        return list(dedup.values())
    return []


def ext_candidates(start):
    """All (endpos, fixes, meta) for an extension block at start."""
    res = []
    for label in cand(start + 1):
        if label == 0xF9:
            ok = True
            fx = {}
            if 4 not in cand(start + 2):
                continue
            if 4 != nums[start + 2]:
                fx[start + 2] = 4
            if 0 not in cand(start + 7):
                continue
            if 0 != nums[start + 7]:
                fx[start + 7] = 0
            delay = None
            # delay bytes may be ambiguous
            import itertools
            for d0, d1 in itertools.product(cand(start + 4), cand(start + 5)):
                fx2 = dict(fx)
                if d0 != nums[start + 4]:
                    fx2[start + 4] = d0
                if d1 != nums[start + 5]:
                    fx2[start + 5] = d1
                res.append((start + 8, fx2,
                            {"type": "gce", "delay": d0 | d1 << 8,
                             "packed": nums[start + 3]}))
            return res
        if label not in (0xFF, 0xFE, 0x01):
            continue
        fx = {}
        if label != nums[start + 1]:
            fx[start + 1] = label
        p = start + 2
        if label in (0xFF, 0x01):
            szs = cand(p)
            states = []
            for sz in szs:
                fx0 = dict(fx)
                if sz != nums[p]:
                    fx0[p] = sz
                states.append((p + 1 + sz, fx0))
        else:
            states = [(p, fx)]
        while states:
            p, fx = states.pop()
            for sz in cand(p):
                if sz == 0:
                    res.append((p + 1, fx, {"type": "ext", "label": label}))
                    continue
                if p + 1 + sz > len(nums):
                    continue
                fx2 = dict(fx)
                if sz != nums[p]:
                    fx2[p] = sz
                states.append((p + 1 + sz, fx2))
        return res
    return []


dead = set()
calls = 0


def solve(pos, depth=0):
    global calls
    calls += 1
    if pos in dead:
        return None
    if pos >= len(nums):
        dead.add(pos)
        return None
    if 0x3B in cand(pos):
        if pos == len(nums) - 1:
            return (pos + 1, {}, {"type": "trailer"}, [])
    nxt = []
    if 0x2C in cand(pos):
        nxt += frame_candidates(pos)
    if 0x21 in cand(pos):
        nxt += ext_candidates(pos)
    for endpos, fixes, meta in nxt:
        r = solve(endpos, depth + 1)
        if r is not None:
            _, _, _, rest = r
            return (endpos, fixes, meta, [(endpos, fixes, meta)] + rest)
    dead.add(pos)
    if depth % 50 == 0:
        print("depth", depth, "pos", pos, "dead", len(dead), "calls", calls)
    return None


result = solve(25)  # after header(6)+LSD(7)+GCT(12)
if result is None:
    print("NO SOLUTION")
    sys.exit(1)

chain = result[3]
print("blocks:", len(chain), "calls:", calls)
frames = [m for _, _, m in chain if "w" in m]
print("frames:", len(frames))
allfix = {}
for _, fx, _ in chain:
    allfix.update(fx)
print("total fixes:", len(allfix))
out = bytes(allfix.get(i, nums[i]) for i in range(len(nums)))
(ROOT / "decoded_fixed.gif").write_bytes(out)
(ROOT / "fixes.json").write_text(json.dumps({str(k): v for k, v in sorted(allfix.items())}))
(ROOT / "chain.json").write_text(json.dumps(
    [{"pos": p, **{k: v for k, v in m.items() if k != "didx"}} for p, _, m in chain]))
(ROOT / "numbers_raw.txt").write_text(" ".join(map(str, nums)) + "\n")

import numpy as np
from PIL import Image, ImageSequence

im = Image.open(ROOT / "decoded_fixed.gif")
frames = np.array([np.array(f.convert("RGB")) for f in ImageSequence.Iterator(im)])
assert frames.shape == (1119, 40, 40, 3), frames.shape
np.save(ROOT / "frames.npy", frames)
print("wrote decoded_fixed.gif and frames.npy:", frames.shape)
