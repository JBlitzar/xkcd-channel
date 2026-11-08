from pathlib import Path
import csv
import json
from collections import Counter

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).parent
frames = np.load(ROOT / "frames.npy")
masks = np.any(frames != [255, 225, 255], axis=3)


def components(mask):
    seen = set()
    blobs = []
    for y, x in zip(*mask.nonzero()):
        if (y, x) in seen:
            continue
        blob = {(y, x)}
        seen.add((y, x))
        queue = [(y, x)]
        while queue:
            a, b = queue.pop()
            for c, d in ((a - 1, b), (a + 1, b), (a, b - 1), (a, b + 1)):
                if 0 <= c < 40 and 0 <= d < 40 and mask[c, d] and (c, d) not in seen:
                    seen.add((c, d))
                    blob.add((c, d))
                    queue.append((c, d))
        blobs.append(blob)
    return blobs


blobs = [components(m) for m in masks]
visible = [max(map(len, b), default=0) >= 15 for b in blobs]
runs = []
for i, v in enumerate(visible):
    if v:
        if i == 0 or not visible[i - 1]:
            runs.append([i, i])
        else:
            runs[-1][1] = i
print("runs", len(runs))
print(runs[:35])
(ROOT / "runs.json").write_text(json.dumps(runs))
for start in (0, 270, 660, 725):
    sheet = Image.new("RGB", (1200, 6 * 116), "white")
    draw = ImageDraw.Draw(sheet)
    for j, i in enumerate(range(start, min(start + 60, len(frames)))):
        x, y = (j % 10) * 120, (j // 10) * 116
        sheet.paste(Image.fromarray(frames[i]).resize((100, 100), Image.Resampling.NEAREST), (x, y))
        draw.text((x, y + 100), str(i), fill="black")
    sheet.save(ROOT / f"detail_{start}.png")
