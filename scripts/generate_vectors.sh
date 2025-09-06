#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

# Subdirectory name under vectors/ for this run
SUBDIR=${1:-sf7}
# Oversampling ratio
OSR=${2:-1}

# Generate vectors via the standalone library
python3 "$SCRIPT_DIR/generate_lora_phy_vectors.py" \
    --sf=7 --seed=1 --bytes=16 --osr="$OSR" --out="$SUBDIR"

# Generate matching vectors via the original LoRa-SDR
python3 "$SCRIPT_DIR/generate_baseline_vectors.py" \
    --sf=7 --cr=4/5 --snr=30 --seed=1 --out="$SUBDIR"

echo "Vectors generated under vectors/lora_phy/$SUBDIR and vectors/lorasdr/$SUBDIR"
