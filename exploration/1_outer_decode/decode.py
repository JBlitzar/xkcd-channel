from pathlib import Path
from collections import Counter
import math

ROOT = Path(__file__).parent
raw = (ROOT / "channel.txt").read_bytes()
forms = "〇一二三四五六七八九零壹贰叁肆伍陆柒捌玖"
digits = [(c.encode(), str(i % 10), c) for i, c in enumerate(forms)]


def nearest(chunk):
    scores = [
        (sum((a - b) ** 2 for a, b in zip(chunk, encoded)), digit, char)
        for encoded, digit, char in digits
    ]
    return sorted(scores)


# All numeral encodings occupy three bytes; separators occupy one.
tokens = []
current = ""
distances = Counter()
ambiguous = []
i = 0
while i < len(raw):
    if raw[i] < 64:
        if current:
            tokens.append(current)
            current = ""
        i += 1
        continue
    chunk = raw[i:i + 3]
    assert len(chunk) == 3
    choices = nearest(chunk)
    score, digit, char = choices[0]
    tied = {d for s, d, c in choices if s == score}
    if len(tied) > 1:
        ambiguous.append((i, chunk.hex(), choices[:3]))
    distances[score] += 1
    current += digit
    i += 3
if current:
    tokens.append(current)

print("First tokens:", tokens[:50])
print("Token lengths:", Counter(map(len, tokens)))
print("Squared distances:", distances)
print("Ambiguous:", len(ambiguous), ambiguous[:10])
numbers = [int(t) for t in tokens]
print("Numbers:", len(numbers), "range:", min(numbers), max(numbers))
(ROOT / "numbers.txt").write_text(" ".join(tokens) + "\n")
assert all(0 <= n <= 255 for n in numbers)
decoded = bytes(numbers)
print("Header:", decoded[:100])
(ROOT / "decoded.gif").write_bytes(decoded)
