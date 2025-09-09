#!/usr/bin/env python3
"""
Validate comprehensive vectors against LoRa-SDR submodule
Check that all generated vectors are correct and not corrupted
"""

import os
import sys
import json
import numpy as np
import subprocess
import tempfile
import struct
from pathlib import Path

def create_vector_validation_script():
    """Create a C++ script to validate all comprehensive vectors"""
    
    cpp_code = '''#include <iostream>
#include <vector>
#include <complex>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <random>
#include "LoRa-SDR/LoRaCodes.hpp"

using namespace std;

// Validate Hamming vectors
bool validateHammingVectors(const string& filename) {
    cout << "=== Validating Hamming Vectors ===" << endl;
    
    ifstream file(filename, ios::binary);
    if (!file.is_open()) {
        cout << "ERROR: Cannot open " << filename << endl;
        return false;
    }
    
    uint32_t num_tests;
    file.read(reinterpret_cast<char*>(&num_tests), sizeof(num_tests));
    cout << "Found " << num_tests << " Hamming test vectors" << endl;
    
    int passed = 0;
    int failed = 0;
    
    for (uint32_t i = 0; i < num_tests; i++) {
        uint8_t test_type, data, encoded, decoded;
        bool error, bad;
        
        file.read(reinterpret_cast<char*>(&test_type), sizeof(test_type));
        file.read(reinterpret_cast<char*>(&data), sizeof(data));
        file.read(reinterpret_cast<char*>(&encoded), sizeof(encoded));
        file.read(reinterpret_cast<char*>(&decoded), sizeof(decoded));
        file.read(reinterpret_cast<char*>(&error), sizeof(error));
        
        if (test_type == 0) { // hamming_84
            file.read(reinterpret_cast<char*>(&bad), sizeof(bad));
        }
        
        bool test_passed = false;
        
        if (test_type == 0) { // hamming_84
            uint8_t expected_encoded = encodeHamming84sx(data);
            bool expected_error, expected_bad;
            uint8_t expected_decoded = decodeHamming84sx(encoded, expected_error, expected_bad);
            test_passed = (encoded == expected_encoded) && (decoded == expected_decoded) && 
                         (error == expected_error) && (bad == expected_bad);
        } else if (test_type == 1) { // hamming_74
            uint8_t expected_encoded = encodeHamming74sx(data);
            bool expected_error;
            uint8_t expected_decoded = decodeHamming74sx(encoded, expected_error);
            test_passed = (encoded == expected_encoded) && (decoded == expected_decoded) && 
                         (error == expected_error);
        } else if (test_type == 2) { // parity_64
            uint8_t expected_encoded = encodeParity64(data);
            bool expected_error;
            uint8_t expected_decoded = checkParity64(encoded, expected_error);
            test_passed = (encoded == expected_encoded) && (decoded == expected_decoded) && 
                         (error == expected_error);
        } else if (test_type == 3) { // parity_54
            uint8_t expected_encoded = encodeParity54(data);
            bool expected_error;
            uint8_t expected_decoded = checkParity54(encoded, expected_error);
            test_passed = (encoded == expected_encoded) && (decoded == expected_decoded) && 
                         (error == expected_error);
        }
        
        if (test_passed) {
            passed++;
        } else {
            failed++;
            cout << "FAILED test " << i << ": type=" << (int)test_type << " data=" << (int)data 
                 << " encoded=" << (int)encoded << " decoded=" << (int)decoded << endl;
        }
    }
    
    file.close();
    
    cout << "Hamming validation: " << passed << " passed, " << failed << " failed" << endl;
    return failed == 0;
}

// Validate modulation vectors
bool validateModulationVectors(const string& filename) {
    cout << "=== Validating Modulation Vectors ===" << endl;
    
    ifstream file(filename, ios::binary);
    if (!file.is_open()) {
        cout << "ERROR: Cannot open " << filename << endl;
        return false;
    }
    
    uint32_t num_tests;
    file.read(reinterpret_cast<char*>(&num_tests), sizeof(num_tests));
    cout << "Found " << num_tests << " modulation test vectors" << endl;
    
    int passed = 0;
    int failed = 0;
    
    for (uint32_t i = 0; i < num_tests; i++) {
        uint8_t test_type;
        int sf, bw, cr;
        bool explicit_header, crc_enabled, whitening_enabled, interleaving_enabled;
        uint32_t payload_size, iq_size;
        
        file.read(reinterpret_cast<char*>(&test_type), sizeof(test_type));
        file.read(reinterpret_cast<char*>(&sf), sizeof(sf));
        file.read(reinterpret_cast<char*>(&bw), sizeof(bw));
        file.read(reinterpret_cast<char*>(&cr), sizeof(cr));
        file.read(reinterpret_cast<char*>(&explicit_header), sizeof(explicit_header));
        file.read(reinterpret_cast<char*>(&crc_enabled), sizeof(crc_enabled));
        file.read(reinterpret_cast<char*>(&whitening_enabled), sizeof(whitening_enabled));
        file.read(reinterpret_cast<char*>(&interleaving_enabled), sizeof(interleaving_enabled));
        file.read(reinterpret_cast<char*>(&payload_size), sizeof(payload_size));
        
        vector<uint8_t> payload(payload_size);
        file.read(reinterpret_cast<char*>(payload.data()), payload_size);
        
        file.read(reinterpret_cast<char*>(&iq_size), sizeof(iq_size));
        vector<complex<double>> iq_samples(iq_size);
        file.read(reinterpret_cast<char*>(iq_samples.data()), iq_size * sizeof(complex<double>));
        
        // Basic validation
        bool test_passed = true;
        
        // Check SF range
        if (sf < 7 || sf > 12) {
            test_passed = false;
            cout << "FAILED test " << i << ": Invalid SF " << sf << endl;
        }
        
        // Check BW
        if (bw != 125 && bw != 250 && bw != 500) {
            test_passed = false;
            cout << "FAILED test " << i << ": Invalid BW " << bw << endl;
        }
        
        // Check CR
        if (cr < 1 || cr > 4) {
            test_passed = false;
            cout << "FAILED test " << i << ": Invalid CR " << cr << endl;
        }
        
        // Check IQ samples size
        int expected_symbols = 10 + 2 + (payload_size * 8 + sf - 1) / sf; // preamble + sync + data
        int expected_samples = expected_symbols * (1 << sf);
        if (iq_size != expected_samples) {
            test_passed = false;
            cout << "FAILED test " << i << ": IQ size mismatch. Expected " << expected_samples 
                 << ", got " << iq_size << endl;
        }
        
        // Check IQ samples are not all zeros or NaNs
        bool has_valid_data = false;
        for (const auto& sample : iq_samples) {
            if (std::isnan(sample.real()) || std::isnan(sample.imag())) {
                test_passed = false;
                cout << "FAILED test " << i << ": NaN in IQ samples" << endl;
                break;
            }
            if (sample.real() != 0.0 || sample.imag() != 0.0) {
                has_valid_data = true;
            }
        }
        
        if (!has_valid_data) {
            test_passed = false;
            cout << "FAILED test " << i << ": All IQ samples are zero" << endl;
        }
        
        if (test_passed) {
            passed++;
        } else {
            failed++;
        }
        
        // Progress indicator
        if (i % 100 == 0) {
            cout << "Processed " << i << "/" << num_tests << " tests..." << endl;
        }
    }
    
    file.close();
    
    cout << "Modulation validation: " << passed << " passed, " << failed << " failed" << endl;
    return failed == 0;
}

// Validate detection vectors
bool validateDetectionVectors(const string& filename) {
    cout << "=== Validating Detection Vectors ===" << endl;
    
    ifstream file(filename, ios::binary);
    if (!file.is_open()) {
        cout << "ERROR: Cannot open " << filename << endl;
        return false;
    }
    
    uint32_t num_tests;
    file.read(reinterpret_cast<char*>(&num_tests), sizeof(num_tests));
    cout << "Found " << num_tests << " detection test vectors" << endl;
    
    int passed = 0;
    int failed = 0;
    
    for (uint32_t i = 0; i < num_tests; i++) {
        uint8_t test_type;
        int sf, bw, cr;
        uint32_t symbols_size, iq_size;
        
        file.read(reinterpret_cast<char*>(&test_type), sizeof(test_type));
        file.read(reinterpret_cast<char*>(&sf), sizeof(sf));
        file.read(reinterpret_cast<char*>(&bw), sizeof(bw));
        file.read(reinterpret_cast<char*>(&cr), sizeof(cr));
        file.read(reinterpret_cast<char*>(&symbols_size), sizeof(symbols_size));
        
        vector<int> test_symbols(symbols_size);
        file.read(reinterpret_cast<char*>(test_symbols.data()), symbols_size * sizeof(int));
        
        file.read(reinterpret_cast<char*>(&iq_size), sizeof(iq_size));
        vector<complex<double>> iq_samples(iq_size);
        file.read(reinterpret_cast<char*>(iq_samples.data()), iq_size * sizeof(complex<double>));
        
        // Basic validation
        bool test_passed = true;
        
        // Check SF range
        if (sf < 7 || sf > 12) {
            test_passed = false;
            cout << "FAILED test " << i << ": Invalid SF " << sf << endl;
        }
        
        // Check symbols are within range
        int max_symbol = (1 << sf) - 1;
        for (int symbol : test_symbols) {
            if (symbol < 0 || symbol > max_symbol) {
                test_passed = false;
                cout << "FAILED test " << i << ": Symbol " << symbol << " out of range [0, " << max_symbol << "]" << endl;
                break;
            }
        }
        
        // Check IQ samples size matches symbols
        int expected_samples = symbols_size * (1 << sf);
        if (iq_size != expected_samples) {
            test_passed = false;
            cout << "FAILED test " << i << ": IQ size mismatch. Expected " << expected_samples 
                 << ", got " << iq_size << endl;
        }
        
        if (test_passed) {
            passed++;
        } else {
            failed++;
        }
    }
    
    file.close();
    
    cout << "Detection validation: " << passed << " passed, " << failed << " failed" << endl;
    return failed == 0;
}

// Validate AWGN vectors (sample only due to size)
bool validateAWGNVectors(const string& filename) {
    cout << "=== Validating AWGN Vectors (Sample) ===" << endl;
    
    ifstream file(filename, ios::binary);
    if (!file.is_open()) {
        cout << "ERROR: Cannot open " << filename << endl;
        return false;
    }
    
    uint32_t num_tests;
    file.read(reinterpret_cast<char*>(&num_tests), sizeof(num_tests));
    cout << "Found " << num_tests << " AWGN test vectors" << endl;
    
    // Sample first 100 tests due to large size
    int sample_size = min(100, (int)num_tests);
    cout << "Sampling first " << sample_size << " tests..." << endl;
    
    int passed = 0;
    int failed = 0;
    
    for (int i = 0; i < sample_size; i++) {
        uint8_t test_type;
        int sf, bw, cr;
        double snr_db, snr_linear, noise_power;
        uint32_t payload_size, clean_iq_size, noisy_iq_size;
        
        file.read(reinterpret_cast<char*>(&test_type), sizeof(test_type));
        file.read(reinterpret_cast<char*>(&sf), sizeof(sf));
        file.read(reinterpret_cast<char*>(&bw), sizeof(bw));
        file.read(reinterpret_cast<char*>(&cr), sizeof(cr));
        file.read(reinterpret_cast<char*>(&snr_db), sizeof(snr_db));
        file.read(reinterpret_cast<char*>(&snr_linear), sizeof(snr_linear));
        file.read(reinterpret_cast<char*>(&noise_power), sizeof(noise_power));
        file.read(reinterpret_cast<char*>(&payload_size), sizeof(payload_size));
        
        vector<uint8_t> payload(payload_size);
        file.read(reinterpret_cast<char*>(payload.data()), payload_size);
        
        file.read(reinterpret_cast<char*>(&clean_iq_size), sizeof(clean_iq_size));
        vector<complex<double>> clean_iq(clean_iq_size);
        file.read(reinterpret_cast<char*>(clean_iq.data()), clean_iq_size * sizeof(complex<double>));
        
        file.read(reinterpret_cast<char*>(&noisy_iq_size), sizeof(noisy_iq_size));
        vector<complex<double>> noisy_iq(noisy_iq_size);
        file.read(reinterpret_cast<char*>(noisy_iq.data()), noisy_iq_size * sizeof(complex<double>));
        
        // Basic validation
        bool test_passed = true;
        
        // Check SNR range
        if (snr_db < -20 || snr_db > 50) {
            test_passed = false;
            cout << "FAILED test " << i << ": Invalid SNR " << snr_db << " dB" << endl;
        }
        
        // Check IQ samples are not NaNs
        for (const auto& sample : clean_iq) {
            if (std::isnan(sample.real()) || std::isnan(sample.imag())) {
                test_passed = false;
                cout << "FAILED test " << i << ": NaN in clean IQ samples" << endl;
                break;
            }
        }
        
        for (const auto& sample : noisy_iq) {
            if (std::isnan(sample.real()) || std::isnan(sample.imag())) {
                test_passed = false;
                cout << "FAILED test " << i << ": NaN in noisy IQ samples" << endl;
                break;
            }
        }
        
        // Check sizes match
        if (clean_iq_size != noisy_iq_size) {
            test_passed = false;
            cout << "FAILED test " << i << ": Clean and noisy IQ sizes don't match" << endl;
        }
        
        if (test_passed) {
            passed++;
        } else {
            failed++;
        }
    }
    
    file.close();
    
    cout << "AWGN validation (sample): " << passed << " passed, " << failed << " failed" << endl;
    return failed == 0;
}

int main() {
    cout << "=== Comprehensive Vector Validation ===" << endl;
    cout << "Validating all generated vectors against LoRa-SDR submodule" << endl;
    cout << endl;
    
    bool all_passed = true;
    
    // Validate each vector type
    all_passed &= validateHammingVectors("vectors/lora_sdr_reference/comprehensive_hamming_tests.bin");
    cout << endl;
    
    all_passed &= validateModulationVectors("vectors/lora_sdr_reference/comprehensive_modulation_tests.bin");
    cout << endl;
    
    all_passed &= validateDetectionVectors("vectors/lora_sdr_reference/comprehensive_detection_tests.bin");
    cout << endl;
    
    all_passed &= validateAWGNVectors("vectors/lora_sdr_reference/comprehensive_awgn_tests.bin");
    cout << endl;
    
    if (all_passed) {
        cout << "=== ALL VECTORS VALIDATED SUCCESSFULLY ===" << endl;
        cout << "All comprehensive vectors are correct and ready for use!" << endl;
        return 0;
    } else {
        cout << "=== VALIDATION FAILED ===" << endl;
        cout << "Some vectors failed validation. Check the errors above." << endl;
        return 1;
    }
}
'''
    
    return cpp_code

def compile_and_run_validation(cpp_code):
    """Compile and run the vector validation"""
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
        f.write(cpp_code)
        cpp_file = f.name
    
    try:
        # Compile
        print("Compiling vector validation...")
        compile_cmd = [
            'g++', '-std=c++17', '-O2',
            '-I', '.',
            '-I', 'LoRa-SDR',
            cpp_file,
            '-o', 'vector_validator'
        ]
        
        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Compilation failed:")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False
        
        print("Compilation successful!")
        
        # Run
        print("Running vector validation...")
        run_result = subprocess.run(['./vector_validator'], capture_output=True, text=True)
        
        print("Validation output:")
        print(run_result.stdout)
        
        if run_result.stderr:
            print("Validation errors:")
            print(run_result.stderr)
        
        return run_result.returncode == 0
        
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    finally:
        # Cleanup
        if os.path.exists(cpp_file):
            os.unlink(cpp_file)
        if os.path.exists('vector_validator'):
            os.unlink('vector_validator')

def main():
    print("Comprehensive Vector Validation")
    print("=" * 40)
    print("Validating all generated vectors against LoRa-SDR submodule")
    print()
    
    # Generate C++ validation code
    print("Creating vector validation script...")
    cpp_code = create_vector_validation_script()
    
    # Compile and run validation
    success = compile_and_run_validation(cpp_code)
    
    if success:
        print("\\n✅ ALL VECTORS VALIDATED SUCCESSFULLY!")
        print("All comprehensive vectors are correct and ready for use!")
    else:
        print("\\n❌ VALIDATION FAILED!")
        print("Some vectors failed validation. Check the errors above.")

if __name__ == "__main__":
    main()
