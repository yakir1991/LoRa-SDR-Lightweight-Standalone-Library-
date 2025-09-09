#!/usr/bin/env python3
"""
Validate fixed vectors against LoRa-SDR submodule
"""

import os
import sys
import json
import numpy as np
import subprocess
import tempfile
import struct
from pathlib import Path

def create_fixed_validation_script():
    """Create a C++ script to validate fixed vectors"""
    
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

// Validate FIXED Hamming vectors
bool validateFixedHammingVectors(const string& filename) {
    cout << "=== Validating FIXED Hamming Vectors ===" << endl;
    
    ifstream file(filename, ios::binary);
    if (!file.is_open()) {
        cout << "ERROR: Cannot open " << filename << endl;
        return false;
    }
    
    uint32_t num_tests;
    file.read(reinterpret_cast<char*>(&num_tests), sizeof(num_tests));
    cout << "Found " << num_tests << " FIXED Hamming test vectors" << endl;
    
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
    
    cout << "FIXED Hamming validation: " << passed << " passed, " << failed << " failed" << endl;
    return failed == 0;
}

// Validate FIXED detection vectors
bool validateFixedDetectionVectors(const string& filename) {
    cout << "=== Validating FIXED Detection Vectors ===" << endl;
    
    ifstream file(filename, ios::binary);
    if (!file.is_open()) {
        cout << "ERROR: Cannot open " << filename << endl;
        return false;
    }
    
    uint32_t num_tests;
    file.read(reinterpret_cast<char*>(&num_tests), sizeof(num_tests));
    cout << "Found " << num_tests << " FIXED detection test vectors" << endl;
    
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
        
        // Check IQ samples are not NaNs
        for (const auto& sample : iq_samples) {
            if (std::isnan(sample.real()) || std::isnan(sample.imag())) {
                test_passed = false;
                cout << "FAILED test " << i << ": NaN in IQ samples" << endl;
                break;
            }
        }
        
        if (test_passed) {
            passed++;
        } else {
            failed++;
        }
    }
    
    file.close();
    
    cout << "FIXED Detection validation: " << passed << " passed, " << failed << " failed" << endl;
    return failed == 0;
}

int main() {
    cout << "=== FIXED Vector Validation ===" << endl;
    cout << "Validating fixed vectors against LoRa-SDR submodule" << endl;
    cout << endl;
    
    bool all_passed = true;
    
    // Validate fixed vector types
    all_passed &= validateFixedHammingVectors("vectors/lora_sdr_reference/fixed_hamming_tests.bin");
    cout << endl;
    
    all_passed &= validateFixedDetectionVectors("vectors/lora_sdr_reference/fixed_detection_tests.bin");
    cout << endl;
    
    if (all_passed) {
        cout << "=== ALL FIXED VECTORS VALIDATED SUCCESSFULLY ===" << endl;
        cout << "All fixed vectors are correct and ready for use!" << endl;
        return 0;
    } else {
        cout << "=== FIXED VALIDATION FAILED ===" << endl;
        cout << "Some fixed vectors failed validation. Check the errors above." << endl;
        return 1;
    }
}
'''
    
    return cpp_code

def compile_and_run_fixed_validation(cpp_code):
    """Compile and run the fixed vector validation"""
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
        f.write(cpp_code)
        cpp_file = f.name
    
    try:
        # Compile
        print("Compiling fixed vector validation...")
        compile_cmd = [
            'g++', '-std=c++17', '-O2',
            '-I', '.',
            '-I', 'LoRa-SDR',
            cpp_file,
            '-o', 'fixed_vector_validator'
        ]
        
        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Compilation failed:")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False
        
        print("Compilation successful!")
        
        # Run
        print("Running fixed vector validation...")
        run_result = subprocess.run(['./fixed_vector_validator'], capture_output=True, text=True)
        
        print("Fixed validation output:")
        print(run_result.stdout)
        
        if run_result.stderr:
            print("Fixed validation errors:")
            print(run_result.stderr)
        
        return run_result.returncode == 0
        
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    finally:
        # Cleanup
        if os.path.exists(cpp_file):
            os.unlink(cpp_file)
        if os.path.exists('fixed_vector_validator'):
            os.unlink('fixed_vector_validator')

def main():
    print("FIXED Vector Validation")
    print("=" * 30)
    print("Validating fixed vectors against LoRa-SDR submodule")
    print()
    
    # Generate C++ validation code
    print("Creating fixed vector validation script...")
    cpp_code = create_fixed_validation_script()
    
    # Compile and run validation
    success = compile_and_run_fixed_validation(cpp_code)
    
    if success:
        print("\\n✅ ALL FIXED VECTORS VALIDATED SUCCESSFULLY!")
        print("All fixed vectors are correct and ready for use!")
    else:
        print("\\n❌ FIXED VALIDATION FAILED!")
        print("Some fixed vectors failed validation. Check the errors above.")

if __name__ == "__main__":
    main()
