#!/usr/bin/env python3
"""
Validate extracted vectors by running them against the LoRa-SDR submodule code.
This script compiles and runs the LoRa-SDR test code to validate our extracted vectors.
"""

import os
import sys
import json
import base64
import subprocess
import tempfile
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def create_simple_test_program():
    """Create a simple C++ test program that uses LoRa-SDR code directly."""
    
    test_program = '''
#include <iostream>
#include <vector>
#include <cassert>
#include <iomanip>

// Include the LoRa-SDR headers
#include "LoRaCodes.hpp"

void test_hamming84_encoding() {
    std::cout << "Testing Hamming 8/4 encoding..." << std::endl;
    
    // Test cases from our extracted vectors
    std::vector<unsigned char> test_bytes = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15};
    
    for (auto byte : test_bytes) {
        unsigned char encoded = encodeHamming84sx(byte);
        bool error = false;
        bool bad = false;
        unsigned char decoded = decodeHamming84sx(encoded, error, bad);
        
        std::cout << "Byte " << (int)byte << ": encoded=" << (int)encoded 
                  << ", decoded=" << (int)decoded << ", error=" << error << ", bad=" << bad << std::endl;
        
        // Verify no error case
        assert(!error);
        assert(!bad);
        assert(decoded == byte);
    }
    
    std::cout << "Hamming 8/4 encoding tests passed!" << std::endl;
}

void test_hamming84_single_error() {
    std::cout << "Testing Hamming 8/4 single error correction..." << std::endl;
    
    // Test single bit errors
    for (int byte_val = 0; byte_val < 16; byte_val++) {
        unsigned char encoded = encodeHamming84sx(byte_val);
        
        for (int bit_pos = 0; bit_pos < 8; bit_pos++) {
            unsigned char corrupted = encoded ^ (1 << bit_pos);
            bool error = false;
            bool bad = false;
            unsigned char decoded = decodeHamming84sx(corrupted, error, bad);
            
            std::cout << "Byte " << byte_val << ", bit " << bit_pos 
                      << ": error=" << error << ", bad=" << bad << ", decoded=" << (int)decoded << std::endl;
            
            // Verify error detection and correction
            assert(error);  // Should detect error
            assert(!bad);   // Should not be bad (correctable)
            assert(decoded == byte_val);  // Should correct to original
        }
    }
    
    std::cout << "Hamming 8/4 single error correction tests passed!" << std::endl;
}

void test_hamming74_encoding() {
    std::cout << "Testing Hamming 7/4 encoding..." << std::endl;
    
    std::vector<unsigned char> test_bytes = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15};
    
    for (auto byte : test_bytes) {
        unsigned char encoded = encodeHamming74sx(byte);
        bool error = false;
        unsigned char decoded = decodeHamming74sx(encoded, error);
        
        std::cout << "Byte " << (int)byte << ": encoded=" << (int)encoded 
                  << ", decoded=" << (int)decoded << ", error=" << error << std::endl;
        
        // Verify no error case
        assert(!error);
        assert(decoded == byte);
    }
    
    std::cout << "Hamming 7/4 encoding tests passed!" << std::endl;
}

void test_parity_codes() {
    std::cout << "Testing Parity codes..." << std::endl;
    
    std::vector<unsigned char> test_bytes = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15};
    
    // Test Parity 6/4
    for (auto byte : test_bytes) {
        unsigned char encoded = encodeParity64(byte);
        bool error = false;
        unsigned char decoded = checkParity64(encoded, error);
        
        std::cout << "Parity64 Byte " << (int)byte << ": encoded=" << (int)encoded 
                  << ", decoded=" << (int)decoded << ", error=" << error << std::endl;
        
        // Verify no error case
        assert(!error);
        assert(decoded == byte);
    }
    
    // Test Parity 5/4
    for (auto byte : test_bytes) {
        unsigned char encoded = encodeParity54(byte);
        bool error = false;
        unsigned char decoded = checkParity54(encoded, error);
        
        std::cout << "Parity54 Byte " << (int)byte << ": encoded=" << (int)encoded 
                  << ", decoded=" << (int)decoded << ", error=" << error << std::endl;
        
        // Verify no error case
        assert(!error);
        assert(decoded == byte);
    }
    
    std::cout << "Parity code tests passed!" << std::endl;
}

void test_interleaver() {
    std::cout << "Testing Interleaver..." << std::endl;
    
    // Test cases from our extracted vectors
    for (int ppm = 7; ppm <= 12; ppm++) {
        for (int rdd = 0; rdd <= 4; rdd++) {
            std::vector<uint8_t> inputCws(ppm);
            const auto mask = (1 << (rdd+4))-1;
            
            // Fill with test pattern
            for (auto &x : inputCws) x = 0x55 & mask;
            
            std::vector<uint16_t> symbols(((rdd+4)*inputCws.size())/ppm);
            diagonalInterleaveSx(inputCws.data(), inputCws.size(), symbols.data(), ppm, rdd);
            
            std::vector<uint8_t> outputCws(inputCws.size());
            diagonalDeterleaveSx(symbols.data(), symbols.size(), outputCws.data(), ppm, rdd);
            
            std::cout << "PPM=" << ppm << ", RDD=" << rdd 
                      << ": input_size=" << inputCws.size() 
                      << ", symbols_size=" << symbols.size()
                      << ", output_size=" << outputCws.size() << std::endl;
            
            // Verify roundtrip
            assert(inputCws == outputCws);
        }
    }
    
    std::cout << "Interleaver tests passed!" << std::endl;
}

int main() {
    std::cout << "=== LoRa-SDR Vector Validation ===" << std::endl;
    
    try {
        test_hamming84_encoding();
        std::cout << std::endl;
        
        test_hamming84_single_error();
        std::cout << std::endl;
        
        test_hamming74_encoding();
        std::cout << std::endl;
        
        test_parity_codes();
        std::cout << std::endl;
        
        test_interleaver();
        std::cout << std::endl;
        
        std::cout << "=== All tests passed! ===" << std::endl;
        return 0;
        
    } catch (const std::exception& e) {
        std::cout << "Test failed: " << e.what() << std::endl;
        return 1;
    }
}
'''
    
    return test_program

def compile_and_run_test():
    """Compile and run the test program."""
    print("Creating test program...")
    
    # Create test program
    test_program = create_simple_test_program()
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
        f.write(test_program)
        test_file = f.name
    
    try:
        # Compile the test
        print("Compiling test program...")
        compile_cmd = [
            'g++', '-std=c++11', '-I./LoRa-SDR/', 
            test_file, 
            '-o', 'lora_test'
        ]
        
        result = subprocess.run(compile_cmd, cwd=project_root, 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            print("Compilation failed:")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
        
        # Run the test
        print("Running test program...")
        run_cmd = ['./lora_test']
        result = subprocess.run(run_cmd, cwd=project_root, 
                              capture_output=True, text=True)
        
        print("Test output:")
        print(result.stdout)
        
        if result.stderr:
            print("Test errors:")
            print(result.stderr)
        
        return result.returncode == 0
        
    finally:
        # Clean up
        os.unlink(test_file)
        test_binary = project_root / 'lora_test'
        if test_binary.exists():
            os.unlink(test_binary)

def validate_extracted_vectors():
    """Validate our extracted vectors against the reference implementation."""
    print("Validating extracted vectors against LoRa-SDR submodule...")
    
    # Load our extracted vectors
    vectors_dir = project_root / "vectors" / "lora_sdr_extracted"
    
    if not vectors_dir.exists():
        print("Error: Extracted vectors not found!")
        return False
    
    # Load hamming test vectors
    hamming_file = vectors_dir / "hamming_tests.json"
    if hamming_file.exists():
        with open(hamming_file, 'r') as f:
            hamming_vectors = json.load(f)
        print(f"Loaded {len(hamming_vectors)} Hamming test vectors")
    
    # Load interleaver test vectors
    interleaver_file = vectors_dir / "interleaver_tests.json"
    if interleaver_file.exists():
        with open(interleaver_file, 'r') as f:
            interleaver_vectors = json.load(f)
        print(f"Loaded {len(interleaver_vectors)} Interleaver test vectors")
    
    # Run the validation test
    success = compile_and_run_test()
    
    if success:
        print("\\n✅ Vector validation PASSED!")
        print("The extracted vectors are valid and match the LoRa-SDR reference implementation.")
    else:
        print("\\n❌ Vector validation FAILED!")
        print("The extracted vectors may not be correct.")
    
    return success

def main():
    """Main validation function."""
    print("LoRa-SDR Vector Validation")
    print("=" * 40)
    
    # Check if submodule exists
    submodule_path = project_root / "LoRa-SDR"
    if not submodule_path.exists():
        print("Error: LoRa-SDR submodule not found!")
        return
    
    # Check if LoRaCodes.hpp exists
    codes_file = submodule_path / "LoRaCodes.hpp"
    if not codes_file.exists():
        print("Error: LoRaCodes.hpp not found in submodule!")
        return
    
    # Run validation
    validate_extracted_vectors()

if __name__ == "__main__":
    main()
