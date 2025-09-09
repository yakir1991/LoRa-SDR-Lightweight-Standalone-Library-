#!/usr/bin/env python3
"""
Fix vector generation with correct LoRa parameters
"""

import os
import struct
import tempfile
import subprocess
from pathlib import Path

def create_fixed_vector_generator():
    """Create a fixed C++ script to generate correct vectors"""
    
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

// Configuration parameters
struct LoRaConfig {
    int sf;
    int bw;
    int cr;
    bool explicit_header;
    bool crc_enabled;
    bool whitening_enabled;
    bool interleaving_enabled;
    string name;
};

// FIXED Test configurations with correct LoRa parameters
vector<LoRaConfig> getFixedTestConfigs() {
    vector<LoRaConfig> configs;
    
    // Correct spreading factors
    vector<int> sfs = {7, 8, 9, 10, 11, 12};
    // Correct bandwidths (in Hz)
    vector<int> bws = {125000, 250000, 500000};
    // Correct coding rates
    vector<int> crs = {1, 2, 3, 4};  // CR 4/5, 4/6, 4/7, 4/8
    
    for (int sf : sfs) {
        for (int bw : bws) {
            for (int cr : crs) {
                string name = "SF" + to_string(sf) + "_BW" + to_string(bw) + "_CR" + to_string(cr);
                configs.push_back({sf, bw, cr, true, true, true, true, name});
            }
        }
    }
    
    return configs;
}

// Generate FIXED Hamming vectors
void generateFixedHammingVectors() {
    cout << "=== Generating FIXED Hamming Code Vectors ===" << endl;
    
    ofstream hamming_file("vectors/lora_sdr_reference/fixed_hamming_tests_v2.bin", ios::binary);
    
    uint32_t num_tests = 0;
    hamming_file.write(reinterpret_cast<const char*>(&num_tests), sizeof(num_tests));
    
    // Test Hamming 8/4 - ALL 4-bit values
    for (int i = 0; i < 16; i++) {
        uint8_t data = i;
        uint8_t encoded = encodeHamming84sx(data);
        bool error = false, bad = false;
        uint8_t decoded = decodeHamming84sx(encoded, error, bad);
        
        uint8_t test_type = 0; // hamming_84
        hamming_file.write(reinterpret_cast<const char*>(&test_type), sizeof(test_type));
        hamming_file.write(reinterpret_cast<const char*>(&data), sizeof(data));
        hamming_file.write(reinterpret_cast<const char*>(&encoded), sizeof(encoded));
        hamming_file.write(reinterpret_cast<const char*>(&decoded), sizeof(decoded));
        hamming_file.write(reinterpret_cast<const char*>(&error), sizeof(error));
        hamming_file.write(reinterpret_cast<const char*>(&bad), sizeof(bad));
        num_tests++;
    }
    
    // Update header
    hamming_file.seekp(0);
    hamming_file.write(reinterpret_cast<const char*>(&num_tests), sizeof(num_tests));
    hamming_file.close();
    
    cout << "Generated " << num_tests << " FIXED Hamming test vectors" << endl;
}

int main() {
    cout << "=== FIXED Vector Generation ===" << endl;
    
    // Create output directory
    system("mkdir -p vectors/lora_sdr_reference");
    
    // Generate fixed vectors
    generateFixedHammingVectors();
    
    cout << "=== FIXED Vector Generation Complete ===" << endl;
    return 0;
}
'''
    
    return cpp_code

def generate_fixed_vectors():
    """Generate fixed vectors with correct parameters"""
    
    cpp_code = create_fixed_vector_generator()
    
    # Write C++ file
    with open('temp_fixed_vector_generator.cpp', 'w') as f:
        f.write(cpp_code)
    
    # Compile and run
    try:
        print("Compiling fixed vector generator...")
        subprocess.run(['g++', '-o', 'temp_fixed_vector_generator', 'temp_fixed_vector_generator.cpp'], check=True)
        
        print("Generating fixed vectors...")
        result = subprocess.run(['./temp_fixed_vector_generator'], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
            
    except subprocess.CalledProcessError as e:
        print(f"Compilation failed: {e}")
        return False
    finally:
        # Cleanup
        for file in ['temp_fixed_vector_generator.cpp', 'temp_fixed_vector_generator']:
            if os.path.exists(file):
                os.remove(file)
    
    return True

if __name__ == "__main__":
    print("=== FIXING VECTOR GENERATION ===")
    
    if generate_fixed_vectors():
        print("\\n✅ Fixed vectors generated successfully!")
        
        # Test the fixed vectors
        print("\\n=== Testing Fixed Vectors ===")
        try:
            with open('vectors/lora_sdr_reference/fixed_hamming_tests_v2.bin', 'rb') as f:
                data = f.read()
            
            num_tests = struct.unpack('<I', data[:4])[0]
            print(f"Fixed Hamming tests: {num_tests}")
            
            # Test first few
            offset = 4
            for i in range(min(5, num_tests)):
                if offset + 6 <= len(data):
                    test_type = data[offset]
                    data_val = data[offset + 1]
                    encoded = data[offset + 2]
                    decoded = data[offset + 3]
                    error = data[offset + 4]
                    bad = data[offset + 5]
                    
                    print(f"  Test {i+1}: data={data_val:02x}, encoded={encoded:02x}, decoded={decoded:02x}, error={error}, bad={bad}")
                    offset += 6
                    
        except Exception as e:
            print(f"Error testing fixed vectors: {e}")
    else:
        print("❌ Failed to generate fixed vectors")
