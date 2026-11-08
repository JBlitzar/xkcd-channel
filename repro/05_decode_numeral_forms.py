# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
# usage: 05_decode_numeral_forms.py <channel.txt> <workdir>
# Layer 5. Layer 4 says "even financial and odd normal numerals = 1": one bit
# per number on the page, from the LAST numeral of the number: 1 iff
# (digit even and financial form) or (digit odd and normal form).
# The noise confusions (二 even/normal vs 伍 odd/financial, 六 vs 八) give the
# same bit, so no repair is needed.
import sys
from pathlib import Path

from PIL import Image

SRC, ROOT = Path(sys.argv[1]), Path(sys.argv[2])
raw = SRC.read_bytes()
forms = "〇一二三四五六七八九零壹贰叁肆伍陆柒捌玖"
enc = [(c.encode(), i % 10, i >= 10) for i, c in enumerate(forms)]


def nearest(chunk):
    return min(enc, key=lambda e: sum((a - b) ** 2 for a, b in zip(chunk, e[0])))


bits, last, i = [], None, 0
while i <= len(raw):
    if i == len(raw) or raw[i] < 64:
        if last:
            _, digit, financial = last
            bits.append(int((digit % 2 == 0) == financial))
            last = None
        i += 1
        continue
    last = nearest(raw[i:i + 3])
    i += 3

assert len(bits) % 8 == 0, len(bits)
data = bytes(int("".join(map(str, bits[k:k + 8])), 2) for k in range(0, len(bits), 8))
(ROOT / "layer5.gif").write_bytes(data)
im = Image.open(ROOT / "layer5.gif")
im.load()
print(f"numbers: {len(bits)}, bytes: {len(data)}, image: {im.size}, comment: {im.info.get('comment')!r}")
im.convert("L").resize((im.width * 6, im.height * 6), Image.Resampling.NEAREST).save(ROOT / "layer5_x6.png")
print("wrote layer5.gif and layer5_x6.png")
