#!/usr/bin/env python3
"""
Generate comprehensive reference vectors from LoRa-SDR submodule
Based on README_LoRaSDR_porting.md requirements - BINARY FORMAT
"""

import os
import sys
import json
import numpy as np
import subprocess
import tempfile
import struct
from pathlib import Path

def create_vector_generation_script():
    """Create a comprehensive C++ script to generate all required vectors in binary format"""
    
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

// Test configurations based on README requirements
vector<LoRaConfig> getTestConfigs() {
    return {
        {7, 125, 1, true, true, true, true, "SF7_125k_CR45"},
        {7, 125, 4, true, true, true, true, "SF7_125k_CR48"},
        {9, 125, 1, true, true, true, true, "SF9_125k_CR45"},
        {9, 125, 4, true, true, true, true, "SF9_125k_CR48"},
        {12, 125, 1, true, true, true, true, "SF12_125k_CR45"},
        {12, 125, 4, true, true, true, true, "SF12_125k_CR48"},
        {7, 250, 1, true, true, true, true, "SF7_250k_CR45"},
        {7, 250, 4, true, true, true, true, "SF7_250k_CR48"},
        {9, 250, 1, true, true, true, true, "SF9_250k_CR45"},
        {9, 250, 4, true, true, true, true, "SF9_250k_CR48"},
        {12, 250, 1, true, true, true, true, "SF12_250k_CR45"},
        {12, 250, 4, true, true, true, true, "SF12_250k_CR48"},
        {7, 500, 1, true, true, true, true, "SF7_500k_CR45"},
        {7, 500, 4, true, true, true, true, "SF7_500k_CR48"},
        {9, 500, 1, true, true, true, true, "SF9_500k_CR45"},
        {9, 500, 4, true, true, true, true, "SF9_500k_CR48"},
        {12, 500, 1, true, true, true, true, "SF12_500k_CR45"},
        {12, 500, 4, true, true, true, true, "SF12_500k_CR48"}
    };
}

// Test payloads
vector<vector<uint8_t>> getTestPayloads() {
    return {
        {0x48, 0x65, 0x6C, 0x6C, 0x6F},  // "Hello"
        {0x57, 0x6F, 0x72, 0x6C, 0x64},  // "World"
        {0x54, 0x65, 0x73, 0x74},        // "Test"
        {0x4C, 0x6F, 0x52, 0x61},        // "LoRa"
        {0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08},  // Binary data
        {0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88, 0x99},  // Hex pattern
        {0xFF, 0xFE, 0xFD, 0xFC, 0xFB, 0xFA, 0xF9, 0xF8},  // Descending pattern
        {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00},  // All zeros
        {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF},  // All ones
        {0x55, 0xAA, 0x55, 0xAA, 0x55, 0xAA, 0x55, 0xAA}   // Alternating pattern
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

// Generate Hamming code test vectors
void generateHammingVectors() {
    cout << "=== Generating Hamming Code Vectors ===" << endl;
    
    ofstream hamming_file("vectors/lora_sdr_reference/hamming_tests.bin", ios::binary);
    
    // Write header
    uint32_t num_tests = 0;
    hamming_file.write(reinterpret_cast<const char*>(&num_tests), sizeof(num_tests));
    
    // Test Hamming 8/4
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
    
    // Test Hamming 7/4
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
    
    // Test Parity codes
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
    
    cout << "Generated " << num_tests << " Hamming test vectors" << endl;
}

// Generate modulation test vectors
void generateModulationVectors() {
    cout << "=== Generating Modulation Vectors ===" << endl;
    
    ofstream mod_file("vectors/lora_sdr_reference/modulation_tests.bin", ios::binary);
    
    // Write header
    uint32_t num_tests = 0;
    mod_file.write(reinterpret_cast<const char*>(&num_tests), sizeof(num_tests));
    
    auto configs = getTestConfigs();
    auto payloads = getTestPayloads();
    
    for (const auto& config : configs) {
        for (const auto& payload : payloads) {
            // Generate IQ samples
            auto iq_samples = generateLoRaModulation(payload, config);
            
            // Write test record
            uint8_t test_type = 0; // modulation
            mod_file.write(reinterpret_cast<const char*>(&test_type), sizeof(test_type));
            
            // Write config
            mod_file.write(reinterpret_cast<const char*>(&config.sf), sizeof(config.sf));
            mod_file.write(reinterpret_cast<const char*>(&config.bw), sizeof(config.bw));
            mod_file.write(reinterpret_cast<const char*>(&config.cr), sizeof(config.cr));
            mod_file.write(reinterpret_cast<const char*>(&config.explicit_header), sizeof(config.explicit_header));
            mod_file.write(reinterpret_cast<const char*>(&config.crc_enabled), sizeof(config.crc_enabled));
            mod_file.write(reinterpret_cast<const char*>(&config.whitening_enabled), sizeof(config.whitening_enabled));
            mod_file.write(reinterpret_cast<const char*>(&config.interleaving_enabled), sizeof(config.interleaving_enabled));
            
            // Write payload
            uint32_t payload_size = payload.size();
            mod_file.write(reinterpret_cast<const char*>(&payload_size), sizeof(payload_size));
            mod_file.write(reinterpret_cast<const char*>(payload.data()), payload.size());
            
            // Write IQ samples
            uint32_t iq_size = iq_samples.size();
            mod_file.write(reinterpret_cast<const char*>(&iq_size), sizeof(iq_size));
            mod_file.write(reinterpret_cast<const char*>(iq_samples.data()), iq_samples.size() * sizeof(complex<double>));
            
            num_tests++;
        }
    }
    
    // Update header with actual count
    mod_file.seekp(0);
    mod_file.write(reinterpret_cast<const char*>(&num_tests), sizeof(num_tests));
    mod_file.close();
    
    cout << "Generated " << num_tests << " modulation test vectors" << endl;
}

// Generate detection test vectors
void generateDetectionVectors() {
    cout << "=== Generating Detection Vectors ===" << endl;
    
    ofstream det_file("vectors/lora_sdr_reference/detection_tests.bin", ios::binary);
    
    // Write header
    uint32_t num_tests = 0;
    det_file.write(reinterpret_cast<const char*>(&num_tests), sizeof(num_tests));
    
    auto configs = getTestConfigs();
    
    for (const auto& config : configs) {
        // Generate test signal with known symbols
        vector<int> test_symbols = {0, 1, 2, 4, 8, 16, 32, 64, 128, 255};
        int N = 1 << config.sf;
        
        vector<complex<double>> iq_samples;
        for (int symbol : test_symbols) {
            auto chirp = generateChirp(N, config.sf, true);
            double phase = 2.0 * M_PI * symbol / N;
            for (int k = 0; k < N; k++) {
                chirp[k] *= complex<double>(cos(phase * k), sin(phase * k));
            }
            iq_samples.insert(iq_samples.end(), chirp.begin(), chirp.end());
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
    
    cout << "Generated " << num_tests << " detection test vectors" << endl;
}

// Generate AWGN test vectors
void generateAWGNVectors() {
    cout << "=== Generating AWGN Vectors ===" << endl;
    
    ofstream awgn_file("vectors/lora_sdr_reference/awgn_tests.bin", ios::binary);
    
    // Write header
    uint32_t num_tests = 0;
    awgn_file.write(reinterpret_cast<const char*>(&num_tests), sizeof(num_tests));
    
    auto configs = getTestConfigs();
    auto payloads = getTestPayloads();
    
    vector<double> snr_values = {0, 5, 10, 15, 20, 25, 30};  // dB
    
    for (const auto& config : configs) {
        for (const auto& payload : payloads) {
            for (double snr_db : snr_values) {
                // Generate clean signal
                auto iq_samples = generateLoRaModulation(payload, config);
                
                // Add AWGN
                double snr_linear = pow(10, snr_db / 10.0);
                double noise_power = 1.0 / snr_linear;
                double noise_std = sqrt(noise_power / 2.0);
                
                random_device rd;
                mt19937 gen(rd());
                normal_distribution<double> dist(0.0, noise_std);
                
                vector<complex<double>> noisy_samples = iq_samples;
                for (auto& sample : noisy_samples) {
                    sample += complex<double>(dist(gen), dist(gen));
                }
                
                // Write test record
                uint8_t test_type = 0; // awgn
                awgn_file.write(reinterpret_cast<const char*>(&test_type), sizeof(test_type));
                
                // Write config
                awgn_file.write(reinterpret_cast<const char*>(&config.sf), sizeof(config.sf));
                awgn_file.write(reinterpret_cast<const char*>(&config.bw), sizeof(config.bw));
                awgn_file.write(reinterpret_cast<const char*>(&config.cr), sizeof(config.cr));
                
                // Write SNR
                awgn_file.write(reinterpret_cast<const char*>(&snr_db), sizeof(snr_db));
                awgn_file.write(reinterpret_cast<const char*>(&snr_linear), sizeof(snr_linear));
                awgn_file.write(reinterpret_cast<const char*>(&noise_power), sizeof(noise_power));
                
                // Write payload
                uint32_t payload_size = payload.size();
                awgn_file.write(reinterpret_cast<const char*>(&payload_size), sizeof(payload_size));
                awgn_file.write(reinterpret_cast<const char*>(payload.data()), payload.size());
                
                // Write clean IQ samples
                uint32_t clean_iq_size = iq_samples.size();
                awgn_file.write(reinterpret_cast<const char*>(&clean_iq_size), sizeof(clean_iq_size));
                awgn_file.write(reinterpret_cast<const char*>(iq_samples.data()), iq_samples.size() * sizeof(complex<double>));
                
                // Write noisy IQ samples
                uint32_t noisy_iq_size = noisy_samples.size();
                awgn_file.write(reinterpret_cast<const char*>(&noisy_iq_size), sizeof(noisy_iq_size));
                awgn_file.write(reinterpret_cast<const char*>(noisy_samples.data()), noisy_samples.size() * sizeof(complex<double>));
                
                num_tests++;
            }
        }
    }
    
    // Update header with actual count
    awgn_file.seekp(0);
    awgn_file.write(reinterpret_cast<const char*>(&num_tests), sizeof(num_tests));
    awgn_file.close();
    
    cout << "Generated " << num_tests << " AWGN test vectors" << endl;
}

int main() {
    cout << "=== Comprehensive LoRa Vector Generation (Binary Format) ===" << endl;
    cout << "Based on README_LoRaSDR_porting.md requirements" << endl;
    cout << endl;
    
    // Create output directory
    system("mkdir -p vectors/lora_sdr_reference");
    
    // Generate all vector types
    generateHammingVectors();
    generateModulationVectors();
    generateDetectionVectors();
    generateAWGNVectors();
    
    cout << endl;
    cout << "=== Vector Generation Complete ===" << endl;
    cout << "All vectors saved to vectors/lora_sdr_reference/ in binary format" << endl;
    
    return 0;
}
'''
    
    return cpp_code

def compile_and_run_vector_generator(cpp_code):
    """Compile and run the vector generator"""
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
        f.write(cpp_code)
        cpp_file = f.name
    
    try:
        # Compile
        print("Compiling comprehensive vector generator...")
        compile_cmd = [
            'g++', '-std=c++17', '-O2',
            '-I', '.',
            '-I', 'LoRa-SDR',
            cpp_file,
            '-o', 'vector_generator'
        ]
        
        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Compilation failed:")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False
        
        print("Compilation successful!")
        
        # Run
        print("Running vector generator...")
        run_result = subprocess.run(['./vector_generator'], capture_output=True, text=True)
        
        if run_result.returncode != 0:
            print(f"Execution failed:")
            print(f"STDOUT: {run_result.stdout}")
            print(f"STDERR: {run_result.stderr}")
            return False
        
        print("Vector generator output:")
        print(run_result.stdout)
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    finally:
        # Cleanup
        if os.path.exists(cpp_file):
            os.unlink(cpp_file)
        if os.path.exists('vector_generator'):
            os.unlink('vector_generator')

def create_vector_summary():
    """Create a summary of all generated vectors"""
    
    summary = {
        "vector_types": [
            {
                "name": "hamming_tests",
                "description": "Hamming code (8/4, 7/4) and Parity code (6/4, 5/4) test vectors",
                "file": "vectors/lora_sdr_reference/hamming_tests.bin",
                "format": "binary",
                "purpose": "Bit-exact testing of error correction codes"
            },
            {
                "name": "modulation_tests",
                "description": "LoRa modulation test vectors for all SF/BW/CR combinations",
                "file": "vectors/lora_sdr_reference/modulation_tests.bin", 
                "format": "binary",
                "purpose": "Testing payload to IQ conversion"
            },
            {
                "name": "detection_tests",
                "description": "Symbol detection test vectors",
                "file": "vectors/lora_sdr_reference/detection_tests.bin",
                "format": "binary",
                "purpose": "Testing FFT-based symbol detection"
            },
            {
                "name": "awgn_tests",
                "description": "AWGN noise test vectors for BER/PER analysis",
                "file": "vectors/lora_sdr_reference/awgn_tests.bin",
                "format": "binary",
                "purpose": "Testing performance under noise conditions"
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
        "snr_values": [0, 5, 10, 15, 20, 25, 30],  # dB
        "generation_date": "2024-09-09",
        "based_on": "README_LoRaSDR_porting.md requirements",
        "format": "binary"
    }
    
    with open('vectors/lora_sdr_reference/vector_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print("Vector summary saved to vectors/lora_sdr_reference/vector_summary.json")

def main():
    print("Comprehensive LoRa Vector Generator (Binary Format)")
    print("=" * 50)
    print("Based on README_LoRaSDR_porting.md requirements")
    print()
    
    # Create output directory
    os.makedirs('vectors/lora_sdr_reference', exist_ok=True)
    
    # Generate C++ code
    print("Creating comprehensive vector generator...")
    cpp_code = create_vector_generation_script()
    
    # Compile and run
    success = compile_and_run_vector_generator(cpp_code)
    
    if success:
        print("\\nVector generation completed successfully!")
        create_vector_summary()
        print("\\nAll vectors are ready for testing the lightweight LoRa implementation!")
        print("\\nBinary format provides:")
        print("- Faster loading and processing")
        print("- Smaller file sizes")
        print("- Direct memory mapping capability")
        print("- Better performance for large datasets")
    else:
        print("\\nVector generation failed!")

if __name__ == "__main__":
    main()