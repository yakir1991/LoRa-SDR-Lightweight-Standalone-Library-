# Testing Guide

## Purpose and Scope
The test suite validates the LoRa PHY library for bit accuracy, end-to-end modulation/demodulation, error-rate behaviour and performance.  It ensures typical LoRa profiles work and checks for dynamic allocations.

## Prerequisites
Ensure the following tools and libraries are available before running the tests:

* A C++11 compiler and [CMake](https://cmake.org) 3.5 or later.
* Python 3 with the `numpy` and `matplotlib` packages for running the AWGN sweep script.
* Generated reference vectors (see below) for the bit-exact regression test.

## Generating Reference Vectors
Comprehensive test vectors have been extracted from the LoRa-SDR submodule and are available in the `vectors/` directory. These vectors have been validated against the original implementation.

### Pre-generated Vectors
The following vector sets are available and ready to use:

* `vectors/lora_sdr_reference/` – Comprehensive test vectors (481 total)
  * Hamming code tests (63 vectors)
  * Interleaver tests (30 vectors) 
  * Modulation tests (360 vectors)
  * Detection tests (28 vectors)

* `vectors/lora_sdr_extracted/` – Specific test vectors from LoRa-SDR test code (338 total)
  * Hamming tests (144 vectors)
  * Interleaver tests (30 vectors)
  * Loopback tests (10 vectors)
  * Encoder/decoder tests (150 vectors)
  * Validation tests (4 vectors)

### Generating Additional Vectors
To generate additional test vectors for specific scenarios:

```bash
# Extract comprehensive vectors from LoRa-SDR submodule
python3 scripts/extract_lora_sdr_vectors.py

# Extract specific test cases from LoRa-SDR test code
python3 scripts/extract_specific_vectors.py

# Generate vectors using the lightweight library (after building)
./build/generate_lora_phy_vectors --sf 7 --out test_run

# Generate comprehensive reference vectors
./build/generate_comprehensive_vectors --out vectors/lora_sdr_reference_cpp
```

### Vector Validation
All vectors are validated against the original LoRa-SDR implementation:

```bash
# Validate against LoRa-SDR submodule
python3 scripts/validate_vectors_with_sublmodule.py

# Validate modulation vectors
python3 scripts/validate_modulation_vectors.py
```

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

