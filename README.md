# xkcd.com/channel.html, decoded

## Note

From what I can find online[^1], previous people have determined that it carries information (follows Zipf's law), and is encoded in some weird way, but not more than that. Others[^2] tried to translate the Chinese to no avail.

Did I use AI? Yeah, I used AI. I still think it's worth reading. I might try to clean it up later. Feel free to submit a PR.

[^1]: https://www.explainxkcd.com/wiki/index.php/explain_xkcd:xkcd_explains , https://www.explainxkcd.com/wiki/index.php/Category:Extra_pages
[^2]: https://web.archive.org/web/20151206001238/http://forums.xkcd.com/viewtopic.php?f=2&t=110093

## Result

The page is a five-layer puzzle. Each layer hides the next, and three of them shout "red herring" along the way.

| Layer | Carrier | Hidden content |
|---|---|---|
| 1 | Chinese numerals on the page, one decimal byte per number | A 40×40 animated GIF of flashing red and blue Hebrew letters |
| 2 | Hebrew letters as numerals, one byte per burst of letters | A 72×51 GIF with the comment `redherring` ×6 |
| 3 | That GIF's picture | "odd red and even blue numbers are ones" |
| 4 | Letter color + odd/even byte, one bit per burst | "even financial and odd normal numerals = 1" |
| 5 | Numeral style + odd/even number, one bit per number on the page | A 95×93 grayscale GIF of the *Harry Potter and the Order of the Phoenix* cover, comment `REDHERRINGREDHERR` |

Layer 1 animation, layer 3 picture, layer 5 picture:

![](results/decoded_fixed.gif) ![](results/inner_x8.png) ![](results/layer5_x6.png)

Whether there is a layer 6 is open.

Source: <https://web.archive.org/web/20141011002528/https://xkcd.com/channel.html> (`input/channel.html` and `input/channel.txt` are byte-identical). A 2014 forum post reports `Last-Modified: Sun, 15 Jan 2012` for both files, so the page likely dates from January 2012.

## Reproduce

Requires [`uv`](https://docs.astral.sh/uv/). Each script declares its own dependencies. Takes about 40 seconds.

```bash
./repro/run.sh            # writes to results/
./repro/run.sh /tmp/out   # or to any other folder
```

Run a single stage:

```bash
uv run --script repro/04_decode_color_parity.py results/
```

| Script | Layer | Input → output |
|---|---|---|
| `repro/01_decode_outer.py` | 1 | `channel.txt` → `decoded_fixed.gif` (1119 frames), `frames.npy`, `fixes.json`, `chain.json` |
| `repro/02_transcribe_frames.py` | 2 | `frames.npy` → `transcription_frames.tsv`, `seq.json`, `tokens.json`, `alts.json` |
| `repro/03_decode_inner.py` | 2–3 | `tokens.json` → `inner.gif`, `inner_x8.png`, `transcription_bytes.txt`, `inner_solutions.json`, `inner_candidates.png` |
| `repro/04_decode_color_parity.py` | 4 | `tokens.json` + `inner.gif` → `layer4_message.txt` |
| `repro/05_decode_numeral_forms.py` | 5 | `channel.txt` → `layer5.gif`, `layer5_x6.png` |

## Layout

| Path | Contents |
|---|---|
| `input/` | The original page (`channel.txt` = `channel.html`, sha256 `355d8e9e…0915`). |
| `repro/` | The pipeline: `run.sh` plus one script per stage. |
| `results/` | Output of `repro/run.sh`. |
| `exploration/` | The first session's working scripts and images (layers 1–2), kept for reference. They assume an old flat folder layout and will not run as-is. |

## Layer 1: page text → animated GIF

**How it works**
- The "garbled Chinese" is a list of decimal numbers 0–255, one per byte of a hidden file, separated by single low bytes (a space with ±1–2 of noise).
- Each digit is a Chinese numeral, in either the normal form (`〇一二三四五六七八九`) or the financial form (`零壹贰叁肆伍陆柒捌玖`). The form looks random here. It matters in layer 5.
- Every UTF-8 byte has ±1 noise. Decoding each 3-byte character to the nearest numeral recovers most digits. Two pairs stay confusable: 二/伍 (2/5) and 六/八 (6/8). The 2/5 mix-ups are silent, so every digit within the noise radius stays a candidate (3668 ambiguous bytes).
- The bytes start with `GIF89a`: a 40×40 animated GIF, 4-color palette, 1119 frames.
- `01_decode_outer.py` walks the GIF block structure. It backtracks over ambiguous bytes and accepts a frame only if its LZW data decodes exactly. Result: 2240 blocks, 1119 frames, 1106 byte repairs, and every frame loads in Pillow.

**What didn't work, and the gotchas**
- A plain nearest-numeral decode (`exploration/1_outer_decode/decode.py`) breaks after a few frames.
- A greedy repair (`exploration/1_outer_decode/solve.py`) chose wrong digits early and could not recover. The backtracking solver replaced it.
- The encoder uses the classic deferred code-width increase. The end-of-data code can sit exactly at the last bit, so the decoder must allow zero-filled reads past the end.
- Validate each frame on a canvas the size of the frame. A full 40×40 canvas makes Pillow report the wrong pixel count.
- Where the GIF structure can't tell 2 from 5 (palette bytes, for example), the solver picks the lower digit. That is sometimes wrong. The red in the palette is probably 255, not 252. It doesn't affect any later layer.

## Layer 2: Hebrew letters → second GIF

**How it works**
- Each frame is blank, a "static" leftover, one Hebrew letter, or the word `אפס` ("zero"). Letters are red or blue.
- `02_transcribe_frames.py` matches each frame against one clean example per glyph (±3 px shift; rewards covered template pixels, penalizes missing and extra ink). It knows 20 letters, א through ר, plus `אפס`.
- 24 frames where leftover static covers the letter were labeled by eye (the `MANUAL` table). Four are unreadable (`?`).
- Blank or static frames separate bursts. There are **336 bursts**, and each one is a byte in Hebrew numerals: א=1 … ט=9, י=10 … צ=90, ק=100, ר=200, `אפס`=0. For example, `קיד` = 100+10+4 = 114 = `r`.
- The bytes form a GIF89a: 72×51, 2-color palette, comment `redherring` ×6, one image with a single 239-byte LZW chunk. The sizes add up to exactly 336 bytes, which confirms the burst count.
- Burst 44 is unreadable, but it sits inside the sixth `redherring`, so it must be `d`.

**What didn't work, and the gotchas**
- Shape clustering (`exploration/2_frame_reading/clusters*.png`) helped find the glyphs but mixed letters with static, so it couldn't serve as the transcription.
- A classifier without shift tolerance mislabeled frames (י vs. ט).
- The "static" is not noise. Frames are never fully erased, so parts of earlier letters stay on screen. This makes ט/ס and ה/ח hard to tell apart, so the next stage treats those as candidate sets.
- Two misreads hid the picture for a long time:
  - **Frame 403** looked like static but is a noisy נ. It is the only "static" frame that draws ink inside its own frame rectangle. Burst 128 is נה = 55, not ה = 5.
  - **Frame 954** has the open top of ט, not ס. Burst 288 is כט = 29. The old reading, כס = 80, also broke the largest-first rule of Hebrew numerals.

## Layer 3: the second GIF's picture

**How it works**
- With those two fixes, the LZW data decodes with **no letter changes**. Three valid streams remain, which differ only in the unreadable bursts.
- A greedy LZW encoder never emits a code when a longer match is already in its dictionary. Pillow's encoder follows this rule, and so do 1101 of the 1119 layer-1 frames. The other 18 probably contain wrong layer-1 repairs. Exactly one stream follows it (violations: 0, 2, 3), and it is the one `03_decode_inner.py` keeps.
- The picture reads: **"odd red and / even blue / numbers are / ones"** (`results/inner_x8.png`).

**What didn't work**
- Before the two transcription fixes, the minimal-change search needed 2 changes and found 50 streams. All of them looked like random dots. That led to the wrong early conclusion that the picture was filler.
- Earlier decoders had bugs (bit accounting on the reset code, allowing palette indices 2–3 in a 2-color image). They produced plausible-looking but invalid images (`exploration/3_inner_decode/inner_idx.png` and similar).
- Blurring, dilating, other widths, transposing and periodicity checks on the wrong candidates found nothing, because there was nothing to find.

## Layer 4: letter color + odd/even

**How it works**
- One bit per burst: 1 if the byte is odd and the letters are red, or even and blue. Every burst is a single color.
- The 336 bits are 42 bytes of ASCII: **`even financial and odd normal numerals = 1`** (`results/layer4_message.txt`).
- This also confirms the unreadable burst 198 is `e` (101): the other valid stream spells "nmrmal".

**What didn't work**
- Color on its own looks random: 167 of 336 bursts are red, with no structure in runs, autocorrelation or byte packings. It only carries data combined with odd/even.

## Layer 5: numeral style + odd/even

**How it works**
- One bit per number on the original page, from its **last** numeral: 1 if that digit is even and financial, or odd and normal.
- 73,808 numbers give exactly 9,226 bytes: a GIF89a, 95×93, 256-level grayscale palette, comment `REDHERRINGREDHERR` (17 characters, cut off), showing the *Harry Potter and the Order of the Phoenix* cover (`results/layer5.gif`).
- It needs no repair. The noise confusions keep the bit: 二 (2, normal) and 伍 (5, financial) both give 0, and so do 六 and 八 (6 and 8, both normal). That looks deliberate.

**What didn't work**
- Taking the form from the **first** numeral gives the right header but a broken image. Repaired 2↔5 digits flip the parity bit, and in 61 numbers the forms differ between digits.
- Packing the forms of all numerals, or of the first or middle numeral, gives random-looking bits.

## Other dead ends

- **GIF metadata:** every frame of the layer-1 animation has the same delay (10) and disposal (1). There are no local palettes or interlacing. The only extensions are the standard loop block and a one-space comment. Frame rectangles are just the bounding boxes of changed pixels.
- **Timing and position:** every letter is shown for one frame, gaps are one frame, and each glyph is always drawn at the same spot.
- **Noise and separators:** the ±1 noise is flat and uncorrelated across the file. The separator bytes look random.
- **Sibling hidden pages** (`cyborg.txt`, `me.txt`, `why.txt`) are unrelated.

## Open questions

- **Layer 6?** Every layer so far hid an instruction for the next. The cover may too. Bit planes and palette usage show nothing obvious yet. The comment is cut off at 17 characters.
- **Why Order of the Phoenix?** It is book 5, and this is layer 5. That may be a coincidence.
- **The January 2012 date** was the weekend of the MIT Mystery Hunt and right before the SOPA blackout. No connection has been found.
- A web search found no earlier published decode.
