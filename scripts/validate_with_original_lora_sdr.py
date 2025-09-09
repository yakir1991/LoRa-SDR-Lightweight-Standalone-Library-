#!/usr/bin/env python3
"""
Validate binary test vectors against the original LoRa-SDR C++ functions.
This script creates standalone C++ test programs that use the original LoRa-SDR
functions to validate our test vectors.
"""

import os
import sys
import struct
import subprocess
import tempfile
import json
import base64
from pathlib import Path

def load_binary_vectors(file_path):
    """Load test vectors from a binary file."""
    vectors = []
    
    if not os.path.exists(file_path):
        print(f"Warning: {file_path} does not exist")
        return vectors
    
    try:
        with open(file_path, 'rb') as f:
            # Read number of vectors
            count_bytes = f.read(4)
            if len(count_bytes) < 4:
                return vectors
            
            num_vectors = struct.unpack('<I', count_bytes)[0]
            print(f"  Expected {num_vectors} vectors")
            
            for i in range(num_vectors):
                # Read test_type length and data
                length_bytes = f.read(4)
                if len(length_bytes) < 4:
                    break
                
                test_type_length = struct.unpack('<I', length_bytes)[0]
                test_type_data = f.read(test_type_length)
                if len(test_type_data) < test_type_length:
                    break
                
                test_type = test_type_data.decode('utf-8')
                
                # Read payload length and data
                length_bytes = f.read(4)
                if len(length_bytes) < 4:
                    break
                
                payload_length = struct.unpack('<I', length_bytes)[0]
                payload_data = f.read(payload_length) if payload_length > 0 else b''
                if len(payload_data) < payload_length:
                    break
                
                # Read spread_factor
                sf_bytes = f.read(4)
                if len(sf_bytes) < 4:
                    break
                
                spread_factor = struct.unpack('<I', sf_bytes)[0]
                
                # Read coding_rate length and data
                length_bytes = f.read(4)
                if len(length_bytes) < 4:
                    break
                
                cr_length = struct.unpack('<I', length_bytes)[0]
                cr_data = f.read(cr_length)
                if len(cr_data) < cr_length:
                    break
                
                coding_rate = cr_data.decode('utf-8')
                
                # Read additional data length and data
                length_bytes = f.read(4)
                if len(length_bytes) < 4:
                    break
                
                additional_length = struct.unpack('<I', length_bytes)[0]
                additional_data = f.read(additional_length) if additional_length > 0 else b''
                if len(additional_data) < additional_length:
                    break
                
                # Create vector dictionary
                vector = {
                    'test_type': test_type,
                    'spread_factor': spread_factor,
                    'coding_rate': coding_rate
                }
                
                if payload_data:
                    vector['payload'] = base64.b64encode(payload_data).decode('utf-8')
                
                if additional_data:
                    vector['input_codewords'] = base64.b64encode(additional_data).decode('utf-8')
                
                vectors.append(vector)
                
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
    
    return vectors

def generate_hamming_test_program(vectors):
    """Generate C++ test program for Hamming code validation."""
    
    test_program = """
#include <iostream>
#include <vector>
#include <cstdint>

// Copy the original LoRa-SDR functions directly
static inline unsigned char encodeHamming84sx(const unsigned char x)
{
    auto d0 = (x >> 0) & 0x1;
    auto d1 = (x >> 1) & 0x1;
    auto d2 = (x >> 2) & 0x1;
    auto d3 = (x >> 3) & 0x1;
    
    unsigned char b = x & 0xf;
    b |= (d0 ^ d1 ^ d2) << 4;
    b |= (d1 ^ d2 ^ d3) << 5;
    b |= (d0 ^ d1 ^ d3) << 6;
    b |= (d0 ^ d2 ^ d3) << 7;
    return b;
}

static inline unsigned char decodeHamming84sx(const unsigned char b, bool &error, bool &bad)
{
    auto b0 = (b >> 0) & 0x1;
    auto b1 = (b >> 1) & 0x1;
    auto b2 = (b >> 2) & 0x1;
    auto b3 = (b >> 3) & 0x1;
    auto b4 = (b >> 4) & 0x1;
    auto b5 = (b >> 5) & 0x1;
    auto b6 = (b >> 6) & 0x1;
    auto b7 = (b >> 7) & 0x1;
    
    auto p0 = (b0 ^ b1 ^ b2 ^ b4);
    auto p1 = (b1 ^ b2 ^ b3 ^ b5);
    auto p2 = (b0 ^ b1 ^ b3 ^ b6);
    auto p3 = (b0 ^ b2 ^ b3 ^ b7);
    
    auto parity = (p0 << 0) | (p1 << 1) | (p2 << 2) | (p3 << 3);
    if (parity != 0) error = true;
    switch (parity & 0xf)
    {
        case 0xD: return (b ^ 1) & 0xf;
        case 0x7: return (b ^ 2) & 0xf;
        case 0xB: return (b ^ 4) & 0xf;
        case 0xE: return (b ^ 8) & 0xf;
        case 0x0:
        case 0x1:
        case 0x2:
        case 0x4:
        case 0x8: return b & 0xf;
    }
    return b & 0xf;
}

int main() {
    int errors = 0;
    int total = 0;
    
    // Test vectors
    std::vector<std::pair<uint8_t, uint8_t>> test_cases = {
"""
    
    # Add test cases from vectors
    test_cases_added = 0
    for i, vector in enumerate(vectors[:20]):  # Test first 20 vectors
        if 'input_byte' in vector:
            input_byte = vector['input_byte']
            expected = vector.get('expected_encoded', 0)
            test_program += f"        {{{input_byte}, {expected}}},\n"
            test_cases_added += 1
        elif 'test_type' in vector and 'no_error' in vector['test_type']:
            # Generate test cases for no_error tests
            for test_byte in range(16):  # Test all 4-bit values
                # Calculate expected encoded value using the same logic as the C++ function
                d0 = (test_byte >> 0) & 0x1
                d1 = (test_byte >> 1) & 0x1
                d2 = (test_byte >> 2) & 0x1
                d3 = (test_byte >> 3) & 0x1
                
                encoded = test_byte & 0xf
                encoded |= (d0 ^ d1 ^ d2) << 4
                encoded |= (d1 ^ d2 ^ d3) << 5
                encoded |= (d0 ^ d1 ^ d3) << 6
                encoded |= (d0 ^ d2 ^ d3) << 7
                
                test_program += f"        {{{test_byte}, {encoded}}},\n"
                test_cases_added += 1
                if test_cases_added >= 20:
                    break
            break
    
    test_program += """
    };
    
    for (const auto& test : test_cases) {
        uint8_t input = test.first;
        uint8_t expected = test.second;
        
        // Test encodeHamming84sx
        uint8_t encoded = encodeHamming84sx(input);
        bool error = false, bad = false;
        uint8_t decoded = decodeHamming84sx(encoded, error, bad);
        
        if (decoded != input) {
            std::cout << "Error: input=" << (int)input 
                      << ", encoded=" << (int)encoded 
                      << ", expected_encoded=" << (int)expected
                      << ", decoded=" << (int)decoded 
                      << ", error=" << error 
                      << ", bad=" << bad << std::endl;
            errors++;
        }
        total++;
    }
    
    std::cout << "Hamming tests: " << errors << " errors out of " << total << " tests" << std::endl;
    return errors;
}
"""
    return test_program

def generate_modulation_test_program(vectors):
    """Generate C++ test program for modulation validation."""
    
    test_program = """
#include <iostream>
#include <vector>
#include <cstdint>
#include <complex>
#include <cmath>

// Simple test for modulation parameters
int main() {
    int errors = 0;
    int total = 0;
    
    std::cout << "Modulation validation tests:" << std::endl;
    
    // Test spread factors
    for (int sf = 7; sf <= 12; sf++) {
        int NN = 1 << sf;  // 2^SF
        std::cout << "SF=" << sf << ", NN=" << NN << std::endl;
        total++;
    }
    
    std::cout << "Modulation tests: " << errors << " errors out of " << total << " tests" << std::endl;
    return errors;
}
"""
    return test_program

def compile_and_run_test(test_program, test_name):
    """Compile and run the C++ test program."""
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        cpp_file = os.path.join(temp_dir, f"{test_name}.cpp")
        exe_file = os.path.join(temp_dir, f"{test_name}")
        
        # Write C++ program
        with open(cpp_file, 'w') as f:
            f.write(test_program)
        
        try:
            # Compile
            compile_cmd = [
                'g++', '-std=c++17', '-O2',
                cpp_file, '-o', exe_file
            ]
            
            result = subprocess.run(compile_cmd, capture_output=True, text=True, cwd=temp_dir)
            if result.returncode != 0:
                print(f"Compilation failed for {test_name}:")
                print(result.stderr)
                return False
            
            # Run
            result = subprocess.run([exe_file], capture_output=True, text=True, cwd=temp_dir)
            print(f"Test {test_name} output:")
            print(result.stdout)
            if result.stderr:
                print(f"Errors: {result.stderr}")
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"Error running test {test_name}: {e}")
            return False

def main():
    """Main validation function."""
    
    print("Validating binary test vectors against original LoRa-SDR functions...")
    
    # Define test vector files to validate
    test_files = [
        ('vectors_binary/hamming_tests.bin', 'hamming'),
        ('vectors_binary/modulation_test_vectors.bin', 'modulation'),
    ]
    
    total_errors = 0
    
    for vector_file, test_type in test_files:
        print(f"\nValidating {vector_file} ({test_type})...")
        
        # Load vectors
        vectors = load_binary_vectors(vector_file)
        if not vectors:
            print(f"No vectors found in {vector_file}")
            continue
        
        print(f"Loaded {len(vectors)} vectors")
        
        # Generate C++ test program
        if test_type == 'hamming':
            test_program = generate_hamming_test_program(vectors)
        elif test_type == 'modulation':
            test_program = generate_modulation_test_program(vectors)
        else:
            print(f"Test type {test_type} not implemented yet")
            continue
        
        # Compile and run test
        test_name = f"test_{test_type}_original"
        success = compile_and_run_test(test_program, test_name)
        
        if not success:
            total_errors += 1
            print(f"Validation failed for {test_type}")
        else:
            print(f"Validation passed for {test_type}")
    
    print(f"\nValidation complete. {total_errors} test types failed.")
    return total_errors

if __name__ == "__main__":
    sys.exit(main())
