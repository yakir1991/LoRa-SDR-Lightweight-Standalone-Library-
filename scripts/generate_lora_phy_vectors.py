#!/usr/bin/env python3
"""Generate reference vectors using the new lora_phy library.

The script runs a small CLI that exercises the lora_phy library and
writes deterministic payloads, symbols and IQ samples.  A manifest file
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
    seed: int
    bytes: int
    files: List[FileRecord]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate vectors via lora_phy")
    parser.add_argument("--sf", type=int, required=True, help="Spreading factor")
    parser.add_argument("--seed", type=int, default=0, help="Random seed")
    parser.add_argument("--bytes", type=int, default=16, help="Number of payload bytes")
    parser.add_argument(
        "--out",
        required=True,
        help="Output subdirectory name under vectors/lora_phy",
    )
    parser.add_argument(
        "--binary",
        default=os.environ.get("LORAPHY_VECTOR_BIN", "build/lora_phy_vector_dump"),
        help="Path to the lora_phy_vector_dump binary",
    )
    args = parser.parse_args()

    vector_bin = pathlib.Path(args.binary).resolve()
    if not vector_bin.is_file():
        parser.error(f"Vector dump binary not found: {vector_bin}")

    base_dir = pathlib.Path("vectors/lora_phy")
    out_dir = base_dir / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(vector_bin),
        f"--sf={args.sf}",
        f"--seed={args.seed}",
        f"--bytes={args.bytes}",
        f"--out={out_dir}",
    ]
    run(cmd)

    files: List[FileRecord] = []
    for path in sorted(out_dir.glob("*")):
        if path.name == "manifest.json":
            continue
        files.append(FileRecord(path.name, compute_checksum(path)))

    manifest = Manifest(args.sf, args.seed, args.bytes, files)
    with (out_dir / "manifest.json").open("w") as handle:
        json.dump(asdict(manifest), handle, indent=2)


if __name__ == "__main__":
    main()
