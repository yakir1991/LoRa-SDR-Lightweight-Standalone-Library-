#!/usr/bin/env bash
set -euo pipefail

BUILD_DIR=${BUILD_DIR:-build}
BIN="$BUILD_DIR/lora_phy_vector_dump"
OUT_DIR=${1:-vectors/generated}

if [ ! -x "$BIN" ]; then
    echo "Vector dump binary not found: $BIN" >&2
    echo "Build the project first (cmake --build $BUILD_DIR)." >&2
    exit 1
fi

mkdir -p "$OUT_DIR"

"$BIN" --sf=7 --seed=1 --bytes=16 --out="$OUT_DIR" \
    --dump=payload \
    --dump=pre_interleave \
    --dump=post_interleave \
    --dump=iq \
    --dump=demod \
    --dump=deinterleave \
    --dump=decoded

echo "Vectors written to $OUT_DIR"
