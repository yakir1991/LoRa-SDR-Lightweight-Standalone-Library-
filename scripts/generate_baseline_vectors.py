#!/usr/bin/env python3
"""Generate baseline vectors using the original LoRa-SDR binary.

The script runs the ``lora_awgn_sim`` example from the reference
implementation for a single set of parameters and stores the resulting
files under ``legacy_vectors/lorasdr_baseline``.  A ``manifest.json`` file
with SHA256 checksums is written so downstream tests can verify the data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
from dataclasses import asdict, dataclass
from typing import List


def run(cmd: List[str]) -> None:
    """Run ``cmd`` and raise if it exits with a non-zero status."""

    print(f"[run] {' '.join(cmd)}", file=sys.stderr)
    subprocess.run(cmd, check=True)


def compute_checksum(path: pathlib.Path) -> str:
    """Return the SHA256 checksum for ``path``."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class FileRecord:
    name: str
    sha256: str


@dataclass
class Manifest:
    sf: int
    cr: str
    snr: float
    seed: int
    files: List[FileRecord]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate baseline vectors via LoRa-SDR")
    parser.add_argument("--sf", type=int, required=True, help="Spreading factor")
    parser.add_argument("--cr", required=True, help="Coding rate, e.g. 4/5")
    parser.add_argument("--snr", type=float, required=True, help="SNR in dB")
    parser.add_argument(
        "--out",
        required=True,
        help="Output subdirectory name under legacy_vectors/lorasdr_baseline",
    )
    parser.add_argument("--seed", type=int, default=0, help="Random seed")
    parser.add_argument(
        "--binary",
        default=os.environ.get("LORASDR_AWGN_BIN", "external/lorasdr_orig/build/lora_awgn_sim"),
        help="Path to the lora_awgn_sim binary",
    )
    args = parser.parse_args()

    awgn_bin = pathlib.Path(args.binary).resolve()
    if not awgn_bin.is_file():
        parser.error(f"AWGN simulation binary not found: {awgn_bin}")

    base_dir = pathlib.Path("legacy_vectors/lorasdr_baseline")
    out_dir = base_dir / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(awgn_bin),
        f"--sf={args.sf}",
        f"--cr={args.cr}",
        f"--snr={args.snr}",
        f"--seed={args.seed}",
        f"--out={out_dir}",
    ]
    run(cmd)

    files: List[FileRecord] = []
    for path in sorted(out_dir.glob("*")):
        if path.name == "manifest.json":
            continue
        files.append(FileRecord(path.name, compute_checksum(path)))

    manifest = Manifest(args.sf, args.cr, args.snr, args.seed, files)
    with (out_dir / "manifest.json").open("w") as handle:
        json.dump(asdict(manifest), handle, indent=2)


if __name__ == "__main__":
    main()

