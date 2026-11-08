import json
from pathlib import Path

ROOT = Path("/tmp/xkcd-channel-scratchpad")
seq = json.load(open(ROOT / "seq.json"))
tokens = json.load(open(ROOT / "tokens.json"))
VAL = dict(zip("אבגדהוזחטיכלמנסעפצקר", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 200]))
VAL["אפס"] = 0
VAL["?"] = None
final = open(ROOT / "inner_fixed.gif", "rb").read()

with open(ROOT / "transcription_frames.tsv", "w") as f:
    f.write("frame\tcontent\tcolor\n")
    for i, k, c in seq:
        if k:
            content = "unreadable" if k == "?" else k
        else:
            content = "static" if c == "sep" else "blank"
        f.write(f"{i}\t{content}\t{c if k else ''}\n")

lines = []
for n, t in enumerate(tokens):
    letters = "".join(k if k != "?" else "?" for _, k, _ in t)
    colors = "".join(c for _, _, c in t)
    raw = None if any(k == "?" for _, k, _ in t) else sum(VAL[k] for _, k, _ in t)
    b = final[n]
    ch = chr(b) if 32 <= b < 127 else "."
    note = "" if raw == b else f"  (read {raw}, repaired)"
    lines.append(f"{n:3d}  frames {t[0][0]}-{t[-1][0]}  {letters:<4} {colors:<4} = {b:3d} {ch}{note}")
(ROOT / "transcription_bytes.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines[:100]))
print(" ".join(k for _, k, _ in sum(tokens, [])))
