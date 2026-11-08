import sys, io, json
sys.setrecursionlimit(100000)
exec(open(__file__.replace("repair_inner.py", "inner.py")).read().split("base = []")[0])

base = [sum(VAL[k] for _, k, _ in t if k != "?") for t in tokens]
base[44] = 100
D0, D1 = 95, 334
NPIX = 72 * 51
MINC = 2
NCOLORS = 2  # global palette has only 2 entries


def decode(data):
    """Return (ok_bits, pixels, done). ok_bits = bits consumed without error."""
    clear, eoi = 1 << MINC, (1 << MINC) + 1
    nbits = len(data) * 8
    pos, size = 0, MINC + 1
    d = [[k] if k < NCOLORS else None for k in range(clear)] + [None, None]
    prev, out = None, []
    while pos + size <= nbits:
        code = 0
        for k in range(size):
            code |= ((data[(pos + k) >> 3] >> ((pos + k) & 7)) & 1) << k
        if code == clear:
            d = [[k] if k < NCOLORS else None for k in range(clear)] + [None, None]
            pos += size
            size, prev = MINC + 1, None
            continue
        if code == eoi:
            return pos, out, len(out) == NPIX
        if prev is None:
            if code >= NCOLORS:
                return pos, out, False
            entry = d[code]
        elif code < len(d) and d[code] is not None:
            entry = d[code]
        elif code == len(d):
            entry = d[prev] + [d[prev][0]]
        else:
            return pos, out, False
        if len(out) + len(entry) > NPIX:
            return pos, out, False
        if prev is not None:
            d.append(d[prev] + [entry[0]])
        out.extend(entry)
        pos += size
        if prev is not None and len(d) == (1 << size) and size < 12:
            size += 1
        prev = code
    return pos, out, None


cands = [[base[i]] + [v for v in options(tokens[i]) if v != base[i]] for i in range(D0, D1)]
data = [base[i] for i in range(D0, D1)]
fixes = {}
nodes = 0


def dfs(k):
    """Bytes < k are chosen; check decode, extend."""
    global nodes
    nodes += 1
    if nodes > 2_000_000:
        raise RuntimeError("too many nodes")
    pos, out, done = decode(bytes(data[:k]))
    if done is False:
        return False
    if k == len(data):
        return done is True or (done is None and len(out) == NPIX)
    for v in cands[k]:
        data[k] = v
        if dfs(k + 1):
            return True
    data[k] = cands[k][0]
    return False


ok = dfs(0)
print("ok", ok, "nodes", nodes)
pos, out, done = decode(bytes(data))
print("pixels", len(out), done)
changes = [(D0 + i, base[D0 + i], data[i], [k for _, k, _ in tokens[D0 + i]]) for i in range(len(data)) if data[i] != base[D0 + i]]
print(changes)
full = list(base)
full[D0:D1] = data
open(ROOT / "inner_fixed.gif", "wb").write(bytes(full))
