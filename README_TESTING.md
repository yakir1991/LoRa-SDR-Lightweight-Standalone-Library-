# Testing Guide

## Purpose and Scope
The test suite validates the LoRa PHY library for bit accuracy, end-to-end modulation/demodulation, error-rate behaviour and performance.  It ensures typical LoRa profiles work and checks for dynamic allocations.

## Prerequisites
Ensure the following tools and libraries are available before running the tests:

* A C++11 compiler and [CMake](https://cmake.org) 3.5 or later.
* Python 3 with the `numpy` and `matplotlib` packages for running the AWGN sweep script.
* Generated reference vectors (see below) for the bit-exact regression test.

## Generating Reference Vectors
Deterministic vectors are required for regression tests.  Generate them after
building the project:

```bash
scripts/generate_vectors.sh vectors/my_run
```

The script invokes `lora_phy_vector_dump` with typical parameters (SF7,
16 payload bytes, seed 1) and writes the selected internal states to the
provided directory as base64-encoded `.b64` files. Raw binaries are
removed after encoding. Generated files include:

* `payload.bin.b64` – base64-encoded payload bytes
* `pre_interleave.csv.b64` – base64-encoded Hamming encoded codewords (decimal per line)
* `post_interleave.csv.b64` – base64-encoded symbols after the diagonal interleaver
* `iq_samples.csv.b64` – base64-encoded complex samples as `real,imag`
* `demod_symbols.csv.b64` – base64-encoded demodulated symbols
* `deinterleave.csv.b64` – base64-encoded codewords after deinterleaving
* `decoded.bin.b64` – base64-encoded final decoded payload

## Running Tests
Build the test executables:

```bash
cmake -B build -S .
cmake --build build
```

### Bit-exact Regression
Compares demodulated output against golden vectors listed in `tests/profiles.yaml`.

```bash
./build/bit_exact_test
```

### End-to-End Chain
Runs encode → modulate → demodulate → decode and verifies the payload round-trips.

```bash
./build/e2e_chain_test
```

### Zero-allocation Check
Verifies that modulation and demodulation routines do not allocate memory at runtime.

```bash
./build/no_alloc_test
```

### AWGN Sweep
Simulates transmission over an AWGN channel for the profiles matrix.

```bash
python tests/awgn_sweep.py --packets 100 --snr-start 0 --snr-stop 12 --snr-step 0.5 --out logs/awgn_sweep
```

### Performance Metrics
Records throughput and cycle counts for each profile.

```bash
./build/performance_test
```

All tests iterate over the profile matrix defined in `tests/profiles.yaml`.  Extend this file to expand coverage across spreading factors, bandwidths and coding rates.

## Interpreting Results
* **Bit-exact / E2E** – Successful profiles print `passed`; mismatches list offending bytes.
* **AWGN sweep** – `awgn_sweep.csv` contains `ber` and `per` versus SNR for each profile.  Generated PNGs plot these curves.
* **Performance test** – `logs/performance.csv` reports packets per second and cycles per symbol.
* **Zero-allocation** – Prints `No allocations detected` when the check passes.

Use these logs to track regressions and performance across the supported profile matrix.

