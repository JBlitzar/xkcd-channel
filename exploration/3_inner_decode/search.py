import sys, json
sys.setrecursionlimit(100000)
__file__ = "/tmp/xkcd-channel-scratchpad/repair_inner.py"
exec(open(__file__).read().split("cands = ")[0])

CLEAR, EOI = 1 << MINC, (1 << MINC) + 1
UNK = {i for i in range(D0, D1) if any(x[1] == "?" for x in tokens[i])}
cands = []
for i in range(D0, D1):
    opts = options(tokens[i])
    if i in UNK:
        cands.append([(v, 0) for v in opts])
    else:
        cands.append([(base[i], 0)] + [(v, 1) for v in opts if v != base[i]])

# append-only dictionary: first pixel and length of each code's string
first, length = [], []


def reset():
    del first[:], length[:]
    for k in range(CLEAR + 2):
        first.append(k if k < NCOLORS else -1)
        length.append(1 if k < NCOLORS else 0)


def feed(st, byte):
    """Consume one byte. st=(acc,nacc,size,prev,outlen,ended). Returns new st or None if invalid."""
    acc, nacc, size, prev, outlen, ended = st
    if ended:
        return None if byte else st  # only zero padding after EOI
    acc |= byte << nacc
    nacc += 8
    while nacc >= size:
        code = acc & ((1 << size) - 1)
        acc >>= size
        nacc -= size
        if code == CLEAR:
            if outlen:  # mid-stream clear never needed for this tiny image
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
            f, l = first[code], 1
        elif code < n and length[code] > 0:
            f, l = first[code], length[code]
        elif code == n:
            f, l = first[prev], length[prev] + 1
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


reset()
data = [c[0][0] for c in cands]
sols = []
LIMIT = 200


def dfs(k, st, budget):
    if len(sols) >= LIMIT:
        return
    if k == len(data):
        if st[5] or st[4] == NPIX:  # EOI seen, or full image with EOI cut off by deferred bump
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


start = (0, 0, MINC + 1, None, 0, False)
for B in range(0, 6):
    sols = []
    reset()
    dfs(0, start, B)
    print("budget", B, "solutions", len(sols), flush=True)
    if sols:
        break
json.dump(sols, open(ROOT / "sols.json", "w"))
from collections import Counter
diff = Counter()
for s in sols:
    for i, v in enumerate(s):
        if v != base[D0 + i]:
            diff[(D0 + i, base[D0 + i], v)] += 1
print(diff.most_common(40))
