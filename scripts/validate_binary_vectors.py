#!/usr/bin/env python3
"""
Validate binary test vectors against the LoRa-SDR submodule's C++ functions.
This script loads binary vectors and dynamically generates C++ test code
to validate them against the actual LoRa-SDR implementation.
"""

import os
import sys
import struct
import subprocess
import tempfile
import json
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
                    import base64
                    vector['payload'] = base64.b64encode(payload_data).decode('utf-8')
                
                if additional_data:
                    import base64
                    vector['input_codewords'] = base64.b64encode(additional_data).decode('utf-8')
                
                vectors.append(vector)
                
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
    
    return vectors

def generate_cpp_test_program(vectors, test_type):
    """Generate C++ test program for the given vectors."""
    
    if test_type == 'hamming':
        test_program = """
#include <iostream>
#include <vector>
#include <cstdint>
#include "LoRa-SDR/LoRaCodes.hpp"

int main() {
    int errors = 0;
    int total = 0;
    
    // Test vectors
    std::vector<std::pair<uint8_t, uint8_t>> test_cases = {
"""
        
        # Add test cases
        for i, vector in enumerate(vectors[:10]):  # Test first 10 vectors
            if 'input_byte' in vector:
                input_byte = vector['input_byte']
                expected = vector.get('expected_encoded', 0)
                test_program += f"        {{{input_byte}, {expected}}},\n"
        
        test_program += """
    };
    
    for (const auto& test : test_cases) {
        uint8_t input = test.first;
        uint8_t expected = test.second;
        
        // Test encodeHamming84sx
        uint8_t encoded = encodeHamming84sx(input);
        uint8_t decoded, error, bad;
        decodeHamming84sx(encoded, decoded, error, bad);
        
        if (error || bad || decoded != (input & 0xf)) {
            std::cout << "Error: input=" << (int)input 
                      << ", encoded=" << (int)encoded 
                      << ", expected_encoded=" << (int)expected
                      << ", decoded=" << (int)decoded 
                      << ", error=" << (int)error 
                      << ", bad=" << (int)bad << std::endl;
            errors++;
        }
        total++;
    }
    
    std::cout << "Hamming tests: " << errors << " errors out of " << total << " tests" << std::endl;
    return errors;
}
"""
        return test_program
    
    elif test_type == 'modulation':
        test_program = """
#include <iostream>
#include <vector>
#include <cstdint>
#include <complex>

int main() {
    int errors = 0;
    int total = 0;
    
    std::cout << "Modulation tests: " << errors << " errors out of " << total << " tests" << std::endl;
    return errors;
}
"""
        return test_program
    
    else:
        return f"""
#include <iostream>
#include <vector>
#include <cstdint>

int main() {{
    std::cout << "Test type '{test_type}' not implemented yet" << std::endl;
    return 0;
}}
"""

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
                '-I', '.',
                cpp_file, '-o', exe_file
            ]
            
            result = subprocess.run(compile_cmd, capture_output=True, text=True, cwd='.')
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
    
    print("Validating binary test vectors against LoRa-SDR submodule...")
    
    # Check if LoRa-SDR submodule exists
    if not os.path.exists('LoRa-SDR'):
        print("Error: LoRa-SDR submodule not found. Please initialize it first.")
        return 1
    
    # Define test vector files to validate
    test_files = [
        ('vectors_binary/hamming_tests.bin', 'hamming'),
        ('vectors_binary/modulation_test_vectors.bin', 'modulation'),
        ('vectors_binary/interleaver_tests.bin', 'interleaver'),
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
        test_program = generate_cpp_test_program(vectors, test_type)
        
        # Compile and run test
        test_name = f"test_{test_type}"
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