#!/usr/bin/env python3
"""
Fix comprehensive vectors based on validation results
"""

import os
import sys
import json
import numpy as np
import subprocess
import tempfile
import struct
from pathlib import Path

def create_fixed_vector_generator():
    """Create a fixed C++ script to generate corrected vectors"""
    
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

// COMPREHENSIVE Test configurations - ALL SF, BW, CR combinations
vector<LoRaConfig> getComprehensiveTestConfigs() {
    vector<LoRaConfig> configs;
    
    // All spreading factors
    vector<int> sfs = {7, 8, 9, 10, 11, 12};
    // All bandwidths
    vector<int> bws = {125, 250, 500};
    // All coding rates
    vector<int> crs = {1, 2, 3, 4};  // CR 4/5, 4/6, 4/7, 4/8
    
    for (int sf : sfs) {
        for (int bw : bws) {
            for (int cr : crs) {
                string name = "SF" + to_string(sf) + "_" + to_string(bw) + "k_CR" + to_string(cr);
                configs.push_back({sf, bw, cr, true, true, true, true, name});
            }
        }
    }
    
    return configs;
}

// Comprehensive test payloads
vector<vector<uint8_t>> getComprehensiveTestPayloads() {
    return {
        // Text payloads
        {0x48, 0x65, 0x6C, 0x6C, 0x6F},  // "Hello"
        {0x57, 0x6F, 0x72, 0x6C, 0x64},  // "World"
        {0x54, 0x65, 0x73, 0x74},        // "Test"
        {0x4C, 0x6F, 0x52, 0x61},        // "LoRa"

        // Binary patterns
        {0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08},
        {0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88, 0x99},
        {0xFF, 0xFE, 0xFD, 0xFC, 0xFB, 0xFA, 0xF9, 0xF8},
        {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00},  // All zeros
        {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF},  // All ones
        {0x55, 0xAA, 0x55, 0xAA, 0x55, 0xAA, 0x55, 0xAA},  // Alternating
        
        // IoT sensor data patterns
        {0x00, 0x00, 0x00, 0x00, 0x42, 0x28, 0x00, 0x00},  // Temperature: 42.5°C
        {0x00, 0x00, 0x00, 0x01, 0x3F, 0x80, 0x00, 0x00},  // Humidity: 1.0
        {0x00, 0x00, 0x00, 0x02, 0x41, 0x20, 0x00, 0x00},  // Pressure: 10.0
        
        // GPS coordinates
        {0x00, 0x00, 0x00, 0x03, 0x40, 0x09, 0x21, 0xFB, 0x54, 0x44, 0x2D, 0x18}, // Lat: 3.14159, Lon: 2.71828
        
        // Random data
        {0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0},
        {0xAB, 0xCD, 0xEF, 0x01, 0x23, 0x45, 0x67, 0x89},
        
        // Edge cases
        {0x01},  // Single byte
        {0x00, 0x01},  // Two bytes
        {0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F}, // 16 bytes
        {0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x1B, 0x1C, 0x1D, 0x1E, 0x1F} // 32 bytes
    };
}

// Generate chirp for modulation
vector<complex<double>> generateChirp(int N, int sf, bool up, double amplitude = 1.0) {
    vector<complex<double>> chirp(N);
    for (int i = 0; i < N; i++) {
        double phase = 2.0 * M_PI * i * i / (2.0 * N);
        if (!up) phase = -phase;
        chirp[i] = amplitude * complex<double>(cos(phase), sin(phase));
    }
    return chirp;
}

// Generate LoRa modulation
vector<complex<double>> generateLoRaModulation(const vector<uint8_t>& payload, const LoRaConfig& config) {
    int N = 1 << config.sf;  // 2^SF
    vector<complex<double>> iq_samples;
    
    // Preamble (10 up chirps)
    for (int i = 0; i < 10; i++) {
        auto chirp = generateChirp(N, config.sf, true);
        iq_samples.insert(iq_samples.end(), chirp.begin(), chirp.end());
    }
    
    // Sync word (2 down chirps)
    for (int i = 0; i < 2; i++) {
        auto chirp = generateChirp(N, config.sf, false);
        iq_samples.insert(iq_samples.end(), chirp.begin(), chirp.end());
    }
    
    // Data symbols
    // Convert payload to bits
    vector<int> bits;
    for (uint8_t byte : payload) {
        for (int i = 7; i >= 0; i--) {
            bits.push_back((byte >> i) & 1);
        }
    }
    
    // Group bits into symbols
    for (int i = 0; i < bits.size(); i += config.sf) {
        int symbol = 0;
        for (int j = 0; j < config.sf && i + j < bits.size(); j++) {
            symbol |= bits[i + j] << (config.sf - 1 - j);
        }
        
        // Generate chirp for this symbol
        double phase = 2.0 * M_PI * symbol / N;
        auto chirp = generateChirp(N, config.sf, true);
        for (int k = 0; k < N; k++) {
            chirp[k] *= complex<double>(cos(phase * k), sin(phase * k));
        }
        iq_samples.insert(iq_samples.end(), chirp.begin(), chirp.end());
    }
    
    return iq_samples;
}

// Generate FIXED Hamming code test vectors
void generateFixedHammingVectors() {
    cout << "=== Generating FIXED Hamming Code Vectors ===" << endl;
    
    ofstream hamming_file("vectors/lora_sdr_reference/fixed_hamming_tests.bin", ios::binary);
    
    // Write header
    uint32_t num_tests = 0;
    hamming_file.write(reinterpret_cast<const char*>(&num_tests), sizeof(num_tests));
    
    // Test Hamming 8/4 - ALL 4-bit values
    for (int i = 0; i < 16; i++) {
        uint8_t data = i;
        uint8_t encoded = encodeHamming84sx(data);
        bool error, bad;
        uint8_t decoded = decodeHamming84sx(encoded, error, bad);
        
        // Write test record
        uint8_t test_type = 0; // hamming_84
        hamming_file.write(reinterpret_cast<const char*>(&test_type), sizeof(test_type));
        hamming_file.write(reinterpret_cast<const char*>(&data), sizeof(data));
        hamming_file.write(reinterpret_cast<const char*>(&encoded), sizeof(encoded));
        hamming_file.write(reinterpret_cast<const char*>(&decoded), sizeof(decoded));
        hamming_file.write(reinterpret_cast<const char*>(&error), sizeof(error));
        hamming_file.write(reinterpret_cast<const char*>(&bad), sizeof(bad));
        num_tests++;
    }
    
    // Test Hamming 7/4 - ALL 4-bit values
    for (int i = 0; i < 16; i++) {
        uint8_t data = i;
        uint8_t encoded = encodeHamming74sx(data);
        bool error;
        uint8_t decoded = decodeHamming74sx(encoded, error);
        
        // Write test record
        uint8_t test_type = 1; // hamming_74
        hamming_file.write(reinterpret_cast<const char*>(&test_type), sizeof(test_type));
        hamming_file.write(reinterpret_cast<const char*>(&data), sizeof(data));
        hamming_file.write(reinterpret_cast<const char*>(&encoded), sizeof(encoded));
        hamming_file.write(reinterpret_cast<const char*>(&decoded), sizeof(decoded));
        hamming_file.write(reinterpret_cast<const char*>(&error), sizeof(error));
        num_tests++;
    }
    
    // Test Parity codes - ALL 4-bit values
    for (int i = 0; i < 16; i++) {
        uint8_t data = i;
        uint8_t encoded64 = encodeParity64(data);
        uint8_t encoded54 = encodeParity54(data);
        
        bool error64, error54;
        uint8_t decoded64 = checkParity64(encoded64, error64);
        uint8_t decoded54 = checkParity54(encoded54, error54);
        
        // Write parity 6/4 test record
        uint8_t test_type = 2; // parity_64
        hamming_file.write(reinterpret_cast<const char*>(&test_type), sizeof(test_type));
        hamming_file.write(reinterpret_cast<const char*>(&data), sizeof(data));
        hamming_file.write(reinterpret_cast<const char*>(&encoded64), sizeof(encoded64));
        hamming_file.write(reinterpret_cast<const char*>(&decoded64), sizeof(decoded64));
        hamming_file.write(reinterpret_cast<const char*>(&error64), sizeof(error64));
        num_tests++;
        
        // Write parity 5/4 test record
        test_type = 3; // parity_54
        hamming_file.write(reinterpret_cast<const char*>(&test_type), sizeof(test_type));
        hamming_file.write(reinterpret_cast<const char*>(&data), sizeof(data));
        hamming_file.write(reinterpret_cast<const char*>(&encoded54), sizeof(encoded54));
        hamming_file.write(reinterpret_cast<const char*>(&decoded54), sizeof(decoded54));
        hamming_file.write(reinterpret_cast<const char*>(&error54), sizeof(error54));
        num_tests++;
    }
    
    // Update header with actual count
    hamming_file.seekp(0);
    hamming_file.write(reinterpret_cast<const char*>(&num_tests), sizeof(num_tests));
    hamming_file.close();
    
    cout << "Generated " << num_tests << " FIXED Hamming test vectors" << endl;
}

// Generate FIXED detection test vectors
void generateFixedDetectionVectors() {
    cout << "=== Generating FIXED Detection Vectors ===" << endl;
    
    ofstream det_file("vectors/lora_sdr_reference/fixed_detection_tests.bin", ios::binary);
    
    // Write header
    uint32_t num_tests = 0;
    det_file.write(reinterpret_cast<const char*>(&num_tests), sizeof(num_tests));
    
    auto configs = getComprehensiveTestConfigs();
    
    for (const auto& config : configs) {
        // Generate test signal with known symbols for each SF - FIXED RANGES
        vector<int> test_symbols;
        int max_symbol = (1 << config.sf) - 1;
        
        // FIXED: Only use symbols within valid range for each SF
        if (config.sf == 7) {
            test_symbols = {0, 1, 2, 4, 8, 16, 32, 64, 127}; // Max: 127
        } else if (config.sf == 8) {
            test_symbols = {0, 1, 2, 4, 8, 16, 32, 64, 128, 255}; // Max: 255
        } else if (config.sf == 9) {
            test_symbols = {0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 511}; // Max: 511
        } else if (config.sf == 10) {
            test_symbols = {0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1023}; // Max: 1023
        } else if (config.sf == 11) {
            test_symbols = {0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2047}; // Max: 2047
        } else if (config.sf == 12) {
            test_symbols = {0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4095}; // Max: 4095
        }
        
        int N = 1 << config.sf;
        
        vector<complex<double>> iq_samples;
        for (int symbol : test_symbols) {
            if (symbol <= max_symbol) {
                auto chirp = generateChirp(N, config.sf, true);
                double phase = 2.0 * M_PI * symbol / N;
                for (int k = 0; k < N; k++) {
                    chirp[k] *= complex<double>(cos(phase * k), sin(phase * k));
                }
                iq_samples.insert(iq_samples.end(), chirp.begin(), chirp.end());
            }
        }
        
        // Write test record
        uint8_t test_type = 0; // detection
        det_file.write(reinterpret_cast<const char*>(&test_type), sizeof(test_type));
        
        // Write config
        det_file.write(reinterpret_cast<const char*>(&config.sf), sizeof(config.sf));
        det_file.write(reinterpret_cast<const char*>(&config.bw), sizeof(config.bw));
        det_file.write(reinterpret_cast<const char*>(&config.cr), sizeof(config.cr));
        
        // Write test symbols
        uint32_t symbols_size = test_symbols.size();
        det_file.write(reinterpret_cast<const char*>(&symbols_size), sizeof(symbols_size));
        det_file.write(reinterpret_cast<const char*>(test_symbols.data()), test_symbols.size() * sizeof(int));
        
        // Write IQ samples
        uint32_t iq_size = iq_samples.size();
        det_file.write(reinterpret_cast<const char*>(&iq_size), sizeof(iq_size));
        det_file.write(reinterpret_cast<const char*>(iq_samples.data()), iq_samples.size() * sizeof(complex<double>));
        
        num_tests++;
    }
    
    // Update header with actual count
    det_file.seekp(0);
    det_file.write(reinterpret_cast<const char*>(&num_tests), sizeof(num_tests));
    det_file.close();
    
    cout << "Generated " << num_tests << " FIXED detection test vectors" << endl;
}

int main() {
    cout << "=== FIXING Comprehensive LoRa Vectors ===" << endl;
    cout << "Fixing Hamming and Detection vectors based on validation results" << endl;
    cout << endl;
    
    // Create output directory
    system("mkdir -p vectors/lora_sdr_reference");
    
    // Generate fixed vector types
    generateFixedHammingVectors();
    generateFixedDetectionVectors();
    
    cout << endl;
    cout << "=== FIXED Vector Generation Complete ===" << endl;
    cout << "Fixed vectors saved to vectors/lora_sdr_reference/" << endl;
    
    return 0;
}
'''
    
    return cpp_code

def compile_and_run_fixed_generator(cpp_code):
    """Compile and run the fixed vector generator"""
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
        f.write(cpp_code)
        cpp_file = f.name
    
    try:
        # Compile
        print("Compiling fixed vector generator...")
        compile_cmd = [
            'g++', '-std=c++17', '-O2',
            '-I', '.',
            '-I', 'LoRa-SDR',
            cpp_file,
            '-o', 'fixed_vector_generator'
        ]
        
        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Compilation failed:")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False
        
        print("Compilation successful!")
        
        # Run
        print("Running fixed vector generator...")
        run_result = subprocess.run(['./fixed_vector_generator'], capture_output=True, text=True)
        
        if run_result.returncode != 0:
            print(f"Execution failed:")
            print(f"STDOUT: {run_result.stdout}")
            print(f"STDERR: {run_result.stderr}")
            return False
        
        print("Fixed vector generator output:")
        print(run_result.stdout)
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    finally:
        # Cleanup
        if os.path.exists(cpp_file):
            os.unlink(cpp_file)
        if os.path.exists('fixed_vector_generator'):
            os.unlink('fixed_vector_generator')

def main():
    print("FIXING Comprehensive LoRa Vectors")
    print("=" * 40)
    print("Fixing Hamming and Detection vectors based on validation results")
    print()
    
    # Create output directory
    os.makedirs('vectors/lora_sdr_reference', exist_ok=True)
    
    # Generate C++ code
    print("Creating fixed vector generator...")
    cpp_code = create_fixed_vector_generator()
    
    # Compile and run
    success = compile_and_run_fixed_generator(cpp_code)
    
    if success:
        print("\\n✅ FIXED vector generation completed successfully!")
        print("\\nFixed vectors:")
        print("- fixed_hamming_tests.bin")
        print("- fixed_detection_tests.bin")
        print("\\nThese should now pass validation!")
    else:
        print("\\n❌ Fixed vector generation failed!")

if __name__ == "__main__":
    main()
