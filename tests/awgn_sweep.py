#!/usr/bin/env python3
"""AWGN sweep for LoRa PHY.

This script runs a simple end-to-end LoRa modem simulation over an
additive white Gaussian noise (AWGN) channel.  For a range of SNR
values it transmits random payloads and records the bit error rate (BER)
and packet error rate (PER).  Results are written to a CSV file and
basic plots are emitted for convenience.

The implementation is intentionally lightweight and self contained so
that it can run as part of the repository's test suite without external
binaries.  The LoRa modulation and FEC blocks are simplified versions of
those found in the original code base but capture the key behaviour for
AWGN testing.
"""

from __future__ import annotations

import argparse
import csv
import math
import pathlib
from dataclasses import dataclass
from typing import Iterable, List, Tuple

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ---------------------------------------------------------------------------
# Profile loading
# ---------------------------------------------------------------------------


@dataclass
class Profile:
    name: str
    sf: int
    bw: int
    cr: str


def load_profiles(path: pathlib.Path) -> List[Profile]:
    profiles: List[Profile] = []
    current: dict = {}
    with path.open() as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("-"):
                if current:
                    profiles.append(
                        Profile(
                            name=current.get("name", ""),
                            sf=int(current.get("sf", 0)),
                            bw=int(current.get("bw", 0)),
                            cr=current.get("cr", ""),
                        )
                    )
                current = {}
                continue
            if ":" not in line:
                continue
            key, val = [x.strip() for x in line.split(":", 1)]
            current[key] = val
    if current:
        profiles.append(
            Profile(
                name=current.get("name", ""),
                sf=int(current.get("sf", 0)),
                bw=int(current.get("bw", 0)),
                cr=current.get("cr", ""),
            )
        )
    return profiles


# ---------------------------------------------------------------------------
# Forward error correction helpers
# ---------------------------------------------------------------------------


def encode_parity54(b: int) -> int:
    """Encode a 4-bit nibble using the LoRa 4/5 parity code.

    The implementation matches ``encodeParity54`` from the legacy C++
    code and returns a 5-bit code word packed into an ``int``.
    """

    x = b ^ (b >> 2)
    x ^= x >> 1
    return (b & 0xF) | ((x << 4) & 0x10)


def encode_hamming84(b: int) -> int:
    """Encode a 4-bit nibble using the LoRa 4/8 Hamming code."""

    d0 = (b >> 0) & 1
    d1 = (b >> 1) & 1
    d2 = (b >> 2) & 1
    d3 = (b >> 3) & 1

    code = b & 0xF
    code |= (d0 ^ d1 ^ d2) << 4
    code |= (d1 ^ d2 ^ d3) << 5
    code |= (d0 ^ d1 ^ d3) << 6
    code |= (d0 ^ d2 ^ d3) << 7
    return code


def decode_hamming84(code: int) -> Tuple[int, bool, bool]:
    """Decode a Hamming(8,4) code word.

    Returns a tuple ``(nibble, error, bad)`` where ``error`` is set when a
    parity error was detected and ``bad`` is set when the error could not
    be corrected (more than one bit wrong).
    """

    b0 = (code >> 0) & 1
    b1 = (code >> 1) & 1
    b2 = (code >> 2) & 1
    b3 = (code >> 3) & 1
    b4 = (code >> 4) & 1
    b5 = (code >> 5) & 1
    b6 = (code >> 6) & 1
    b7 = (code >> 7) & 1

    p0 = b0 ^ b1 ^ b2 ^ b4
    p1 = b1 ^ b2 ^ b3 ^ b5
    p2 = b0 ^ b1 ^ b3 ^ b6
    p3 = b0 ^ b2 ^ b3 ^ b7

    parity = (p0 << 0) | (p1 << 1) | (p2 << 2) | (p3 << 3)
    error = parity != 0
    bad = False
    if parity == 0xD:
        code ^= 1
    elif parity == 0x7:
        code ^= 2
    elif parity == 0xB:
        code ^= 4
    elif parity == 0xE:
        code ^= 8
    elif parity in (0x0, 0x1, 0x2, 0x4, 0x8):
        pass
    else:
        bad = True
    return code & 0xF, error, bad


# ---------------------------------------------------------------------------
# Bit/byte helpers
# ---------------------------------------------------------------------------


def encode_payload(payload: bytes, cr: str) -> List[int]:
    """Encode ``payload`` into a list of bits according to ``cr``."""

    bits: List[int] = []
    for byte in payload:
        for nibble in ((byte >> 4) & 0xF, byte & 0xF):
            if cr == "4/5":
                cw = encode_parity54(nibble)
                width = 5
            elif cr == "4/8":
                cw = encode_hamming84(nibble)
                width = 8
            else:
                raise ValueError(f"Unsupported coding rate: {cr}")
            bits.extend((cw >> i) & 1 for i in range(width))
    return bits


def decode_payload(bits: List[int], cr: str, num_bytes: int) -> List[int]:
    """Decode a bit stream created by :func:`encode_payload`."""

    nibbles: List[int] = []
    idx = 0
    for _ in range(num_bytes * 2):
        if cr == "4/5":
            cw = 0
            for i in range(5):
                cw |= (bits[idx + i] & 1) << i
            idx += 5
            nib = cw & 0xF
        elif cr == "4/8":
            cw = 0
            for i in range(8):
                cw |= (bits[idx + i] & 1) << i
            idx += 8
            nib, _, _ = decode_hamming84(cw)
        else:
            raise ValueError(f"Unsupported coding rate: {cr}")
        nibbles.append(nib)

    out: List[int] = []
    for i in range(0, len(nibbles), 2):
        out.append(((nibbles[i] & 0xF) << 4) | (nibbles[i + 1] & 0xF))
    return out


def bits_to_symbols(bits: List[int], sf: int) -> List[int]:
    """Pack a list of bits into ``sf``-bit symbol values."""

    symbols: List[int] = []
    for i in range(0, len(bits), sf):
        val = 0
        for j in range(sf):
            if i + j < len(bits):
                val |= (bits[i + j] & 1) << j
        symbols.append(val)
    return symbols


def symbols_to_bits(symbols: Iterable[int], sf: int, bit_len: int) -> List[int]:
    """Unpack symbols into a bit list of length ``bit_len``."""

    bits: List[int] = []
    for sym in symbols:
        for i in range(sf):
            bits.append((sym >> i) & 1)
    return bits[:bit_len]


# ---------------------------------------------------------------------------
# LoRa modulation helpers
# ---------------------------------------------------------------------------


def make_chirps(sf: int) -> Tuple[np.ndarray, np.ndarray]:
    """Return the base up-chirp and down-chirp for ``sf``."""

    N = 1 << sf
    n = np.arange(N, dtype=float)
    phase = -math.pi + (2 * math.pi * n) / N
    accum = np.cumsum(phase)
    up = np.exp(1j * accum)
    down = np.conj(up)
    return up, down


def simulate(sf: int, cr: str, snr_db: float, packets: int, payload_len: int,
             up: np.ndarray, down: np.ndarray) -> Tuple[float, float]:
    """Run the AWGN simulation and return ``(ber, per)``."""

    N = len(up)
    n = np.arange(N)
    sigma = 10 ** (-snr_db / 20.0)
    bit_errors = 0
    packet_errors = 0
    total_bits = 0

    for _ in range(packets):
        payload = np.random.randint(0, 256, payload_len, dtype=np.uint8)
        tx_bits = encode_payload(payload.tobytes(), cr)
        symbols = bits_to_symbols(tx_bits, sf)

        rx_syms: List[int] = []
        for sym in symbols:
            # Modulate and add noise
            shift = np.exp(1j * 2 * math.pi * sym * n / N)
            tx = up * shift
            noise = (np.random.normal(size=N) + 1j * np.random.normal(size=N))
            noise *= sigma / math.sqrt(2.0)
            r = tx + noise

            # Demodulate
            dechirped = r * down
            spec = np.fft.fft(dechirped)
            rx_syms.append(int(np.argmax(np.abs(spec))))

        rx_bits = symbols_to_bits(rx_syms, sf, len(tx_bits))
        rx_payload = decode_payload(rx_bits, cr, payload_len)

        bit_errors += sum(bin(int(a) ^ int(b)).count("1") for a, b in zip(payload, rx_payload))
        total_bits += payload_len * 8
        if any(int(a) != int(b) for a, b in zip(payload, rx_payload)):
            packet_errors += 1

    ber = bit_errors / total_bits if total_bits else 0.0
    per = packet_errors / packets if packets else 0.0
    return ber, per


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="LoRa AWGN sweep")
    parser.add_argument("--out", default="awgn_sweep", help="Output directory")
    parser.add_argument("--packets", type=int, default=100, help="Packets per SNR point")
    parser.add_argument("--payload-bytes", type=int, default=16, help="Payload size in bytes")
    parser.add_argument("--snr-start", type=float, default=0.0, help="Start SNR in dB")
    parser.add_argument("--snr-stop", type=float, default=12.0, help="Stop SNR in dB")
    parser.add_argument("--snr-step", type=float, default=0.5, help="SNR step in dB")
    args = parser.parse_args()

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    profiles = load_profiles(pathlib.Path(__file__).resolve().parent / "profiles.yaml")

    fieldnames = ["sf", "bw", "cr", "snr_db", "ber", "per"]
    rows: List[dict] = []

    for p in profiles:
        up, down = make_chirps(p.sf)
        snrs = np.arange(args.snr_start, args.snr_stop + 1e-9, args.snr_step)
        bers: List[float] = []
        pers: List[float] = []
        for snr in snrs:
            ber, per = simulate(p.sf, p.cr, snr, args.packets, args.payload_bytes, up, down)
            rows.append({"sf": p.sf, "bw": p.bw, "cr": p.cr, "snr_db": snr, "ber": ber, "per": per})
            bers.append(ber)
            pers.append(per)

        # Emit plot for this configuration
        plt.figure()
        plt.semilogy(snrs, bers, label="BER")
        plt.semilogy(snrs, pers, label="PER")
        plt.xlabel("SNR (dB)")
        plt.ylabel("Error rate")
        plt.title(f"SF{p.sf} BW{p.bw/1000:.0f}k CR{p.cr}")
        plt.grid(True, which="both")
        plt.legend()
        plt.tight_layout()
        plt.savefig(out_dir / f"{p.name}.png")
        plt.close()

    # Write CSV
    csv_path = out_dir / "awgn_sweep.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


if __name__ == "__main__":
    main()
