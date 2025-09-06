# Test Vectors

This directory holds generated test vectors used for regression
checking.  Large binaries are not versioned in Git.  Instead, run the
script `scripts/generate_vectors.sh` to recreate the data when needed.

The script produces two subdirectories:

* `lorasdr/` – vectors produced by the original LoRa-SDR reference
  implementation.
* `lora_phy/` – vectors produced by this standalone library.

Each run writes the raw data files alongside a `manifest.json` file with
SHA256 checksums so changes can be detected without storing the binary
files in the repository.
