# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# usage: 04_decode_color_parity.py <workdir>
# Layer 4. The inner picture says "odd red and even blue numbers are ones":
# one bit per letter burst, 1 iff (byte odd and red) or (byte even and blue).
import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1])
tokens = json.load(open(ROOT / "tokens.json"))
values = (ROOT / "inner.gif").read_bytes()
assert len(values) == len(tokens)
assert all(len({c for _, _, c in t}) == 1 for t in tokens), "a burst mixes colors"

bits = "".join("1" if (v % 2 == 1) == (t[0][2] == "R") else "0" for v, t in zip(values, tokens))
msg = bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))
(ROOT / "layer4_message.txt").write_bytes(msg + b"\n")
print(f"layer 4 message: {msg.decode()!r}")
