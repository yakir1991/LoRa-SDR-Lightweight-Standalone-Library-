#!/usr/bin/env python3
"""
Create a clean repository with only essential files and golden vectors
"""

import os
import sys
import shutil
import json
import subprocess
from pathlib import Path

def create_clean_repo_structure():
    """Create a clean repository structure with only essential files"""
    
    print("Creating clean repository structure...")
    
    # Create clean repo directory
    clean_repo_dir = "LoRa-SDR-Lightweight-Clean"
    os.makedirs(clean_repo_dir, exist_ok=True)
    
    # Essential directories
    essential_dirs = [
        "src/phy",
        "include/lora_phy", 
        "include/lorawan",
        "runners",
        "tests",
        "scripts",
        "vectors/golden",
        "examples",
        "docs"
    ]
    
    for dir_path in essential_dirs:
        os.makedirs(os.path.join(clean_repo_dir, dir_path), exist_ok=True)
    
    return clean_repo_dir

def copy_essential_files(clean_repo_dir):
    """Copy only essential files to clean repo"""
    
    print("Copying essential files...")
    
    # Essential files to copy
    essential_files = [
        "CMakeLists.txt",
        "README.md",
        "API_SPEC.md",
        "PORTING_NOTES.md",
        "SEMANTIC_COMPATIBILITY.md",
        "TEST_PLAN.md",
        "THIRD_PARTY.md"
    ]
    
    for file_path in essential_files:
        if os.path.exists(file_path):
            shutil.copy2(file_path, clean_repo_dir)
            print(f"Copied: {file_path}")
    
    # Copy source files
    src_files = [
        "src/phy/LoRaDecoder.cpp",
        "src/phy/LoRaDemod.cpp", 
        "src/phy/LoRaEncoder.cpp",
        "src/phy/LoRaMod.cpp",
        "src/phy/phy.cpp",
        "src/lorawan/lorawan.cpp"
    ]
    
    for file_path in src_files:
        if os.path.exists(file_path):
            dest_path = os.path.join(clean_repo_dir, file_path)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(file_path, dest_path)
            print(f"Copied: {file_path}")
    
    # Copy header files
    header_files = [
        "include/lora_phy/ChirpGenerator.hpp",
        "include/lora_phy/kissfft.hh",
        "include/lora_phy/LoRaCodes.hpp",
        "include/lora_phy/LoRaDetector.hpp",
        "include/lora_phy/phy.hpp",
        "include/lorawan/lorawan.hpp"
    ]
    
    for file_path in header_files:
        if os.path.exists(file_path):
            dest_path = os.path.join(clean_repo_dir, file_path)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(file_path, dest_path)
            print(f"Copied: {file_path}")
    
    # Copy runner files
    runner_files = [
        "runners/lora_phy_vector_dump.cpp",
        "runners/lorawan_roundtrip.cpp",
        "runners/rx_runner.cpp",
        "runners/tx_runner.cpp"
    ]
    
    for file_path in runner_files:
        if os.path.exists(file_path):
            dest_path = os.path.join(clean_repo_dir, file_path)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(file_path, dest_path)
            print(f"Copied: {file_path}")
    
    # Copy test files
    test_files = [
        "tests/bit_exact_test.cpp",
        "tests/e2e_chain_test.cpp",
        "tests/equal_power_bin_test.cpp",
        "tests/lorawan_roundtrip.py",
        "tests/no_alloc_test.cpp",
        "tests/performance_test.cpp",
        "tests/roundtrip_test.cpp",
        "tests/sync_word_test.cpp",
        "tests/test_main.cpp",
        "tests/whitening_test.cpp",
        "tests/profiles.yaml"
    ]
    
    for file_path in test_files:
        if os.path.exists(file_path):
            dest_path = os.path.join(clean_repo_dir, file_path)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(file_path, dest_path)
            print(f"Copied: {file_path}")
    
    # Copy essential scripts
    script_files = [
        "scripts/compare_perf.py",
        "scripts/compare_vectors.py",
        "scripts/generate_baseline_vectors.py",
        "scripts/generate_lora_phy_vectors.py",
        "scripts/generate_vectors.sh",
        "scripts/scan_allocs.sh"
    ]
    
    for file_path in script_files:
        if os.path.exists(file_path):
            dest_path = os.path.join(clean_repo_dir, file_path)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(file_path, dest_path)
            print(f"Copied: {file_path}")

def create_golden_vectors(clean_repo_dir):
    """Create golden vectors - only the most important ones"""
    
    print("Creating golden vectors...")
    
    golden_vectors_dir = os.path.join(clean_repo_dir, "vectors/golden")
    os.makedirs(golden_vectors_dir, exist_ok=True)
    
    # Copy the working comprehensive vectors as golden vectors
    source_vectors = [
        "vectors/lora_sdr_reference/comprehensive_modulation_tests.bin",
        "vectors/lora_sdr_reference/fixed_detection_tests.bin",
        "vectors/lora_sdr_reference/comprehensive_hamming_tests.bin"
    ]
    
    golden_names = [
        "modulation_tests.bin",
        "detection_tests.bin", 
        "hamming_tests.bin"
    ]
    
    for source, golden in zip(source_vectors, golden_names):
        if os.path.exists(source):
            dest_path = os.path.join(golden_vectors_dir, golden)
            shutil.copy2(source, dest_path)
            print(f"Copied golden vector: {golden}")
        else:
            print(f"Warning: Source vector not found: {source}")
    
    # Create golden vector summary
    golden_summary = {
        "vector_types": [
            {
                "name": "hamming_tests",
                "description": "Hamming code test vectors (8/4, 7/4, Parity 6/4, 5/4)",
                "file": "vectors/golden/hamming_tests.bin",
                "format": "binary",
                "purpose": "Bit-exact testing of error correction codes"
            },
            {
                "name": "modulation_tests",
                "description": "LoRa modulation test vectors for key SF/BW/CR combinations",
                "file": "vectors/golden/modulation_tests.bin", 
                "format": "binary",
                "purpose": "Testing payload to IQ conversion"
            },
            {
                "name": "detection_tests",
                "description": "Symbol detection test vectors",
                "file": "vectors/golden/detection_tests.bin",
                "format": "binary",
                "purpose": "Testing FFT-based symbol detection"
            }
        ],
        "test_configurations": [
            "SF7/9/12 × BW 125/250/500 kHz × CR 4/5, 4/8",
            "Explicit header mode",
            "CRC enabled/disabled",
            "Whitening enabled/disabled", 
            "Interleaving enabled/disabled"
        ],
        "test_payloads": [
            "Text payloads: 'Hello', 'World', 'Test', 'LoRa'",
            "Binary patterns: 0x01-0x08, 0x00-0x99, 0xFF-0xF8",
            "Edge cases: all zeros, all ones, alternating pattern"
        ],
        "generation_date": "2024-09-09",
        "based_on": "LoRa-SDR submodule reference implementation",
        "format": "binary",
        "size": "Optimized for essential testing only"
    }
    
    with open(os.path.join(golden_vectors_dir, "golden_summary.json"), 'w') as f:
        json.dump(golden_summary, f, indent=2)
    
    print("Created golden vector summary")

def create_clean_readme(clean_repo_dir):
    """Create a clean README for the new repo"""
    
    readme_content = """# LoRa-SDR Lightweight Standalone Library

A lightweight, standalone implementation of LoRa PHY layer based on the original LoRa-SDR (MyriadRF) with KISS-FFT as the sole FFT backend.

## Features

- **Zero Runtime Allocations**: All buffers allocated during initialization
- **KISS-FFT Only**: Single FFT dependency for embedded compatibility
- **Bit-Exact Compatibility**: Matches original LoRa-SDR behavior
- **Comprehensive Testing**: Golden vectors for validation

## Supported Parameters

- **Spreading Factors**: 7, 8, 9, 10, 11, 12
- **Bandwidths**: 125, 250, 500 kHz
- **Coding Rates**: 4/5, 4/6, 4/7, 4/8
- **Header Mode**: Explicit header
- **Error Correction**: Hamming codes (8/4, 7/4), Parity codes (6/4, 5/4)

## Quick Start

### Building

```bash
mkdir build && cd build
cmake ..
make
```

### Running Tests

```bash
# Run tests with golden vectors
./test_runner
```

### Using the Library

```cpp
#include "lora_phy/phy.hpp"

// Initialize LoRa parameters
LoRaParams params = {
    .sf = 7,
    .bw = 125000,
    .cr = 1,
    .explicit_header = true,
    .crc_enabled = true
};

// Initialize PHY
LoRaPHY phy(params);

// Modulate payload
std::vector<uint8_t> payload = {0x48, 0x65, 0x6C, 0x6C, 0x6F}; // "Hello"
auto iq_samples = phy.modulate(payload);

// Demodulate IQ samples
auto decoded_payload = phy.demodulate(iq_samples);
```

## Project Structure

```
├── src/phy/           # Core PHY implementation
├── include/lora_phy/  # Public headers
├── runners/           # CLI utilities
├── tests/             # Test suite
├── vectors/golden/    # Golden test vectors
└── scripts/           # Build and test scripts
```

## Golden Vectors

The `vectors/golden/` directory contains essential test vectors:

- `hamming_tests.bin`: Hamming code test vectors
- `modulation_tests.bin`: Modulation test vectors  
- `detection_tests.bin`: Symbol detection test vectors

These vectors are generated from the original LoRa-SDR submodule and provide bit-exact validation.

## Testing

The library includes comprehensive tests:

- **Bit-Exact Tests**: Compare against golden vectors
- **End-to-End Tests**: Full modulation/demodulation chain
- **Performance Tests**: Timing and memory usage
- **No-Allocation Tests**: Verify zero runtime allocations

## Dependencies

- **KISS-FFT**: Header-only FFT library (included)
- **C++17**: Modern C++ features
- **CMake**: Build system

## License

This project is based on the original LoRa-SDR implementation by MyriadRF.
See THIRD_PARTY.md for licensing details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## References

- [LoRa-SDR Original Implementation](https://github.com/myriadrf/LoRa-SDR)
- [KISS-FFT](https://github.com/mborgerding/kissfft)
- [LoRaWAN Specification](https://lora-alliance.org/resource_hub/lorawan-specification-v1-0-3/)
"""
    
    with open(os.path.join(clean_repo_dir, "README.md"), 'w') as f:
        f.write(readme_content)
    
    print("Created clean README")

def create_gitignore(clean_repo_dir):
    """Create .gitignore for the clean repo"""
    
    gitignore_content = """# Build directories
build/
cmake-build-*/

# Generated files
*.o
*.so
*.a
*.exe
*.dll
*.dylib

# IDE files
.vscode/
.idea/
*.swp
*.swo
*~

# OS files
.DS_Store
Thumbs.db

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/

# Test outputs
test_results/
*.log

# Large vector files (not golden vectors)
vectors/lora_sdr_reference/
vectors_binary/
*.bin
!vectors/golden/*.bin

# Temporary files
*.tmp
*.temp
"""
    
    with open(os.path.join(clean_repo_dir, ".gitignore"), 'w') as f:
        f.write(gitignore_content)
    
    print("Created .gitignore")

def main():
    print("Creating Clean LoRa-SDR Repository")
    print("=" * 40)
    print("Creating repository with only essential files and golden vectors")
    print()
    
    # Create clean repo structure
    clean_repo_dir = create_clean_repo_structure()
    
    # Copy essential files
    copy_essential_files(clean_repo_dir)
    
    # Create golden vectors
    create_golden_vectors(clean_repo_dir)
    
    # Create clean README
    create_clean_readme(clean_repo_dir)
    
    # Create .gitignore
    create_gitignore(clean_repo_dir)
    
    print(f"\\n✅ Clean repository created: {clean_repo_dir}")
    print("\\nRepository includes:")
    print("- Essential source files only")
    print("- Golden vectors (essential test cases)")
    print("- Clean documentation")
    print("- Proper .gitignore")
    print("\\nReady for Git repository creation!")

if __name__ == "__main__":
    main()
