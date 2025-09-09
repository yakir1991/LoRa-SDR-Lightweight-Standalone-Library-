# Test Vectors

This directory holds generated test vectors used for regression
checking and validation of the lightweight LoRa implementation.

## Vector Structure

The directory contains several subdirectories with different types of test vectors:

* `lora_sdr_reference/` – Comprehensive test vectors extracted from the LoRa-SDR submodule
  * `hamming_test_vectors.json` – Hamming code test cases (8/4, 7/4, parity)
  * `interleaver_test_vectors.json` – Interleaver test cases (PPM 7-12, RDD 0-4)
  * `modulation_test_vectors.json` – Modulation test cases (SF 7-12, CR 1-4, BW 125K-500K)
  * `detection_test_vectors.json` – Detection test cases (SNR levels, frequency offsets)

* `lora_sdr_extracted/` – Specific test vectors extracted from LoRa-SDR test code
  * `hamming_tests.json` – Hamming code tests from TestCodesSx.cpp
  * `interleaver_tests.json` – Interleaver tests from TestCodesSx.cpp
  * `loopback_tests.json` – Loopback tests from TestLoopback.cpp
  * `encoder_decoder_tests.json` – Encoder/decoder tests from TestLoopback.cpp
  * `validation_tests.json` – Basic validation test cases

* `lora_phy/` – Vectors produced by this standalone library (generated during testing)

## Vector Validation

All vectors have been validated against the original LoRa-SDR implementation to ensure correctness:

```bash
# Validate vectors against LoRa-SDR submodule
python3 scripts/validate_vectors_with_sublmodule.py

# Validate modulation vectors
python3 scripts/validate_modulation_vectors.py

# Run lightweight implementation tests
python3 scripts/test_lightweight_lora.py
```

## Usage

The vectors are used by the test suite to validate the lightweight implementation:

```bash
# Generate reference vectors (if needed)
python3 scripts/extract_lora_sdr_vectors.py
python3 scripts/extract_specific_vectors.py

# Run tests with vectors
python3 scripts/test_lightweight_lora.py
```

## File Formats

* `.json` files contain structured test data with parameters and expected outputs
* Each vector file includes a `manifest.json` with SHA256 checksums
* Test cases include input data, expected outputs, and validation parameters
