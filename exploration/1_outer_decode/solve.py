from pathlib import Path
from collections import Counter
import sys, json

sys.setrecursionlimit(100000)
ROOT = Path(__file__).parent
raw = (ROOT / "channel.txt").read_bytes()
forms = "〇一二三四五六七八九零壹贰叁肆伍陆柒捌玖"
digits = [(c.encode(), str(i % 10), c) for i, c in enumerate(forms)]

# sanity: which digit chars are confusable under +-1-per-byte noise?
encs = [(c.encode(), d) for c, d in [(c, str(i % 10)) for i, c in enumerate(forms)]]
pairs = set()
for i in range(len(encs)):
    for j in range(i + 1, len(encs)):
        a, da = encs[i]
        b, db = encs[j]
        if da != db and all(abs(x - y) <= 2 for x, y in zip(a, b)):
            pairs.add((da, db))
print("confusable digit pairs:", pairs)


def nearest(chunk):
    scores = [
        (sum((a - b) ** 2 for a, b in zip(chunk, enc)), digit)
        for enc, digit, _ in digits
    ]
    scores.sort()
    return scores


# tokenize; record ambiguous digit alternatives
tokens = []          # list of lists: digits with per-position candidate lists
current = None
i = 0
n_amb_tokens = 0
while i < len(raw):
    if raw[i] < 64:
        if current:
            tokens.append(current)
            current = None
        i += 1
        continue
    chunk = raw[i:i + 3]
    ch = nearest(chunk)
    best = ch[0][0]
    opts = [d for s, d in ch if s == best]
    if current is None:
        current = []
    current.append(opts)
    i += 3
if current:
    tokens.append(current)

nums = []
alts = {}  # byte index -> alternative value
for t in tokens:
    base = "".join(o[0] for o in t)
    nums.append(int(base))
    if any(len(o) > 1 for o in t):
        assert len(t) <= 3
        # only single-digit ambiguity expected; collect alternatives
        idx = len(nums) - 1
        altvals = []
        for pos, o in enumerate(t):
            if len(o) > 1:
                assert len(o) == 2
                for d in o[1:]:
                    s = list(base)
                    s[pos] = d
                    altvals.append(int("".join(s)))
        alts[idx] = altvals
        n_amb_tokens += 1
print("bytes:", len(nums), "ambiguous bytes:", n_amb_tokens)

fixed = {}  # byte index -> corrected value (committed repairs)


def val(i):
    return fixed.get(i, nums[i])


def cand(i):
    out = [val(i)]
    if i not in fixed:
        out += alts.get(i, [])
    return out


def lzw_decode(data, mincode):
    """Return pixel list or None."""
    clear = 1 << mincode
    eoi = clear + 1
    # bit reader LSB-first
    bits = []
    for byte in data:
        for k in range(8):
            bits.append((byte >> k) & 1)
    pos = 0
    size = mincode + 1
    dict_ = {i: [i] for i in range(clear)}
    dict_[clear] = None
    dict_[eoi] = None
    nextcode = eoi + 1
    prev = None
    out = []
    while True:
        if pos + size > len(bits):
            return None
        code = 0
        for k in range(size):
            code |= bits[pos + k] << k
        pos += size
        if code == clear:
            dict_ = {i: [i] for i in range(clear)}
            dict_[clear] = None
            dict_[eoi] = None
            nextcode = eoi + 1
            size = mincode + 1
            prev = None
            continue
        if code == eoi:
            return out
        if prev is None:
            if code >= clear:
                return None
            entry = dict_[code]
            out.extend(entry)
            prev = code
            continue
        if code in dict_ and dict_[code] is not None:
            entry = dict_[code]
        elif code == nextcode:
            entry = dict_[prev] + [dict_[prev][0]]
        else:
            return None
        out.extend(entry)
        dict_[nextcode] = dict_[prev] + [entry[0]]
        nextcode += 1
        if nextcode == (1 << size) and size < 12:
            size += 1
        prev = code
        if len(out) > 5000:
            return None


def lzw_with_repairs(data_indices, mincode, npix):
    """data_indices: byte indices of image data. Try committed/base values,
    then single/double flips of ambiguous bytes. Return fixed dict or None."""
    def attempt():
        data = [val(i) for i in data_indices]
        px = lzw_decode(data, mincode)
        return px is not None and len(px) == npix

    if attempt():
        return {}
    amb = [i for i in data_indices if i in alts and i not in fixed]
    for i in amb:
        for v in alts[i]:
            fixed[i] = v
            if attempt():
                return {i: v}
            del fixed[i]
    for a in range(len(amb)):
        for va in alts[amb[a]]:
            fixed[amb[a]] = va
            for b in range(a + 1, len(amb)):
                for vb in alts[amb[b]]:
                    fixed[amb[b]] = vb
                    if attempt():
                        return {amb[a]: va, amb[b]: vb}
                    del fixed[amb[b]]
            del fixed[amb[a]]
    return None


frames = []
repairs = {}
pos = 13 + 12  # header+LSD (packed 0xf1) + GCT 4 colors
assert bytes(nums[0:6]) == b"GIF89a"
npos = 6
w = val(6) | val(7) << 8
h = val(8) | val(9) << 8
packed = val(10)
npos = 13 + 3 * (2 ** ((packed & 7) + 1))
pos = npos
print("canvas", w, h)
nrep = 0
while pos < len(nums):
    b = val(pos)
    if b == 0x3B:
        print("trailer at", pos)
        break
    if b == 0x21:
        label = val(pos + 1)
        pos += 2
        if label == 0xF9:
            assert val(pos) == 4
            delay = val(pos + 2) | val(pos + 3) << 8
            gce = {"delay": delay, "packed": val(pos + 1)}
            assert val(pos + 5) == 0
            pos += 6
            pending_gce = gce
            continue
        if label == 0xFF:
            sz = val(pos)
            app = bytes(val(pos + 1 + k) for k in range(sz))
            pos += 1 + sz
        elif label in (0xFE, 0x01):
            pass
        else:
            raise ValueError(f"ext label {hex(label)} at {pos}")
        while True:
            sz = val(pos)
            pos += 1
            if sz == 0:
                break
            pos += sz
        continue
    if b == 0x2C:
        start = pos
        left = val(pos + 1) | val(pos + 2) << 8
        top = val(pos + 3) | val(pos + 4) << 8
        iw = val(pos + 5) | val(pos + 6) << 8
        ih = val(pos + 7) | val(pos + 8) << 8
        ipacked = val(pos + 9)
        assert not (ipacked & 0x80), "no LCT expected"
        mincode = val(pos + 10)
        dpos = pos + 11
        # walk sub-blocks, allowing length-byte repair by LZW validation
        data_idx = []
        p = dpos
        while True:
            sz = val(p)
            if sz == 0:
                p += 1
                break
            data_idx.extend(range(p + 1, p + 1 + sz))
            p += 1 + sz
        npix = iw * ih
        rep = lzw_with_repairs(data_idx, mincode, npix)
        tried_len_repair = False
        while rep is None:
            # maybe a length/descriptor byte is wrong; try flipping ambiguous
            # bytes in [pos, dpos+1] plus the first/last sub-block length bytes
            region = list(range(pos, dpos + 1)) + [dpos]
            candidates = [i for i in range(start, p) if i in alts and i not in fixed]
            done = False
            for i in candidates:
                for v in alts[i]:
                    fixed[i] = v
                    # re-walk sub-blocks
                    iw2 = val(start + 5) | val(start + 6) << 8
                    ih2 = val(start + 7) | val(start + 8) << 8
                    mc2 = val(start + 10)
                    dpos2 = start + 11
                    data2 = []
                    p2 = dpos2
                    ok = True
                    while True:
                        sz = val(p2)
                        if sz == 0:
                            p2 += 1
                            break
                        data2.extend(range(p2 + 1, p2 + 1 + sz))
                        p2 += 1 + sz
                        if p2 > len(nums) or len(data2) > 3000:
                            ok = False
                            break
                    if ok:
                        r2 = lzw_with_repairs(data2, mc2, iw2 * ih2)
                        if r2 is not None:
                            rep = r2
                            left = val(start + 1) | val(start + 2) << 8
                            top = val(start + 3) | val(start + 4) << 8
                            iw, ih, mincode = iw2, ih2, mc2
                            p = p2
                            done = True
                            break
                    del fixed[i]
                if done:
                    break
            if not done:
                print("FAILED frame at", start, "around", pos)
                print("context", [val(k) for k in range(start - 4, start + 20)])
                sys.exit(1)
        repairs.update(rep)
        nrep += len(rep)
        frames.append({"left": left, "top": top, "w": iw, "h": ih,
                       "data": [val(i) for i in (range(start + 11, p))],
                       "mincode": mincode,
                       "delay": pending_gce.get("delay", 10)})
        pos = p
        if len(frames) % 100 == 0:
            print("frame", len(frames), "pos", pos, "repairs so far", nrep)
        continue
    print("UNKNOWN", hex(b), "at", pos)
    sys.exit(1)

print("frames:", len(frames), "repairs:", nrep, "end pos", pos, "of", len(nums))
(ROOT / "frames.json").write_text(json.dumps({
    "w": w, "h": h, "frames": frames,
    "palette": [val(13 + i) for i in range(12)],
}))
(ROOT / "repairs.json").write_text(json.dumps({str(k): v for k, v in sorted(repairs.items())}))
out = bytes(fixed.get(i, nums[i]) for i in range(len(nums)))
(ROOT / "decoded_fixed.gif").write_bytes(out)
print("wrote decoded_fixed.gif")
