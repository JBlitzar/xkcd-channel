#!/bin/sh
# Full pipeline: channel.txt -> outer GIF -> letter transcription -> inner GIF.
# usage: repro/run.sh [workdir]   (default: results/)
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
TOP=$(dirname "$HERE")
OUT=${1:-"$TOP/results"}
PY="uv run --no-project --with pillow --with numpy --with scipy python"

$PY "$HERE/01_decode_outer.py" "$TOP/input/channel.txt" "$OUT"
$PY "$HERE/02_transcribe_frames.py" "$OUT"
$PY "$HERE/03_decode_inner.py" "$OUT"
