#!/usr/bin/env python3
"""Generate baseline vectors using the original LoRa-SDR implementation.

Prerequisites
-------------
* A C++ compiler and CMake capable of building the original LoRa-SDR repository.  The build is expected to live in ``external/lorasdr_orig``.
* Python 3.8+
* Python packages: ``numpy``, ``pandas``
* Optional package: ``pyyaml`` if YAML manifests are preferred, otherwise JSON is used.
* Environment variables:
    * ``LORASDR_ORIG`` – path to the original LoRa-SDR source tree (defaults to ``external/lorasdr_orig``).
    * ``LORASDR_BUILD`` – path to the build directory (defaults to ``<LORASDR_ORIG>/build``).

The script builds the original project if needed and runs an AWGN simulation for a matrix of spread-factors (SF7/SF9/SF12) and coding rates (CR 4/5–4/8) at a fixed SNR of 10 dB.  At each key boundary the intermediate data is written to ``.bin`` and ``.csv`` files under ``legacy_vectors/lorasdr_baseline/<sf>_<cr>_<snr>/``.  A manifest is emitted with metadata and checksums so downstream tests can verify integrity.
"""

import hashlib
import json
import os
import pathlib
import subprocess
import sys
from dataclasses import dataclass, asdict
from typing import List

import numpy as np
import pandas as pd


def run(cmd: List[str], cwd: pathlib.Path | None = None) -> None:
    """Run ``cmd`` and raise on failure."""
    print(f"[run] {' '.join(cmd)}", file=sys.stderr)
    subprocess.run(cmd, check=True, cwd=cwd)


def compute_checksum(path: pathlib.Path) -> str:
    """Return the SHA256 checksum for ``path``."""
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def ensure_build(src: pathlib.Path, build: pathlib.Path) -> None:
    """Build the original LoRa-SDR project if no build artifacts exist."""
    lib_candidate = build / 'liblora.a'
    if lib_candidate.exists():
        print(f"Found existing build at {lib_candidate}")
        return

    build.mkdir(exist_ok=True)
    run(['cmake', str(src)], cwd=build)
    run(['cmake', '--build', '.', '--', '-j4'], cwd=build)


def run_awgn_simulation(src: pathlib.Path, sf: int, cr: str, snr: float, seed: int, out_dir: pathlib.Path) -> None:
    """Invoke the original AWGN simulation.

    This function assumes that the original repository provides a binary
    called ``lora_awgn_sim`` that accepts parameters shown below and writes
    intermediate results to the supplied output directory.  The binary is
    part of LoRa-SDR's examples and is expected to be produced by the build
    step above.  If the binary is not present the function raises a
    ``RuntimeError`` with instructions for the user.
    """
    sim_bin = src / 'build' / 'lora_awgn_sim'
    if not sim_bin.exists():
        raise RuntimeError(
            f"AWGN simulation binary '{sim_bin}' not found. Ensure the original project is built and provides this tool."
        )

    cmd = [
        str(sim_bin),
        f'--sf={sf}',
        f'--cr={cr}',
        f'--snr={snr}',
        f'--seed={seed}',
        f'--out={out_dir}'
    ]
    run(cmd, cwd=src)


@dataclass
class FileRecord:
    name: str
    sha256: str


@dataclass
class VectorRecord:
    sf: int
    cr: str
    snr: float
    seed: int
    files: List[FileRecord]


def main() -> None:
    src = pathlib.Path(os.environ.get('LORASDR_ORIG', 'external/lorasdr_orig')).resolve()
    build = pathlib.Path(os.environ.get('LORASDR_BUILD', src / 'build')).resolve()

    ensure_build(src, build)

    profiles = [(sf, cr, 10.0) for sf in (7, 9, 12) for cr in ('4/5', '4/6', '4/7', '4/8')]
    seed = 0
    manifest: List[VectorRecord] = []

    base_out = pathlib.Path('legacy_vectors/lorasdr_baseline')
    base_out.mkdir(parents=True, exist_ok=True)

    for sf, cr, snr in profiles:
        subdir = base_out / f'sf{sf}_{cr.replace('/', '-')}_{int(snr)}'
        subdir.mkdir(parents=True, exist_ok=True)
        run_awgn_simulation(src, sf, cr, snr, seed, subdir)

        files = []
        for path in sorted(subdir.glob('*')):
            if path.name == 'manifest.json':
                continue
            checksum = compute_checksum(path)
            files.append(FileRecord(path.name, checksum))

        manifest.append(VectorRecord(sf, cr, snr, seed, files))

    manifest_path = base_out / 'manifest.json'
    with manifest_path.open('w') as handle:
        json.dump([asdict(m) for m in manifest], handle, indent=2)
    print(f"Wrote manifest to {manifest_path}")


if __name__ == '__main__':
    main()
