#!/bin/sh
# Full pipeline: channel.txt -> outer GIF -> letter transcription -> inner GIF.
# usage: repro/run.sh [workdir]   (default: results/)
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
TOP=$(dirname "$HERE")
OUT=${1:-"$TOP/results"}
uv run --script "$HERE/01_decode_outer.py" "$TOP/input/channel.txt" "$OUT"
uv run --script "$HERE/02_transcribe_frames.py" "$OUT"
uv run --script "$HERE/03_decode_inner.py" "$OUT"
