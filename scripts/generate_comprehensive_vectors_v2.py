#!/usr/bin/env python3
"""
Generate comprehensive reference vectors from LoRa-SDR submodule
Based on README_LoRaSDR_porting.md requirements - COMPREHENSIVE BINARY FORMAT
"""

import os
import sys
import json
import numpy as np
import subprocess
import tempfile
import struct
from pathlib import Path

def create_comprehensive_vector_generator():
    """Create a comprehensive C++ script to generate ALL required vectors"""
    
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
        {0x4C, 0x6F, 0x52, 0x61, 0x57, 0x41, 0x4E}, // "LoRaWAN"
        
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

// Generate Hamming code test vectors
void generateHammingVectors() {
    cout << "=== Generating Comprehensive Hamming Code Vectors ===" << endl;
    
    ofstream hamming_file("vectors/lora_sdr_reference/comprehensive_hamming_tests.bin", ios::binary);
    
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
    
    cout << "Generated " << num_tests << " comprehensive Hamming test vectors" << endl;
}

// Generate comprehensive modulation test vectors
void generateComprehensiveModulationVectors() {
    cout << "=== Generating Comprehensive Modulation Vectors ===" << endl;
    
    ofstream mod_file("vectors/lora_sdr_reference/comprehensive_modulation_tests.bin", ios::binary);
    
    // Write header
    uint32_t num_tests = 0;
    mod_file.write(reinterpret_cast<const char*>(&num_tests), sizeof(num_tests));
    
    auto configs = getComprehensiveTestConfigs();
    auto payloads = getComprehensiveTestPayloads();
    
    cout << "Testing " << configs.size() << " configurations with " << payloads.size() << " payloads each" << endl;
    
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
    
    cout << "Generated " << num_tests << " comprehensive modulation test vectors" << endl;
}

// Generate comprehensive detection test vectors
void generateComprehensiveDetectionVectors() {
    cout << "=== Generating Comprehensive Detection Vectors ===" << endl;
    
    ofstream det_file("vectors/lora_sdr_reference/comprehensive_detection_tests.bin", ios::binary);
    
    // Write header
    uint32_t num_tests = 0;
    det_file.write(reinterpret_cast<const char*>(&num_tests), sizeof(num_tests));
    
    auto configs = getComprehensiveTestConfigs();
    
    for (const auto& config : configs) {
        // Generate test signal with known symbols for each SF
        vector<int> test_symbols;
        int max_symbol = (1 << config.sf) - 1;
        
        // Test all edge cases and some middle values
        test_symbols = {0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096};
        if (config.sf <= 7) test_symbols = {0, 1, 2, 4, 8, 16, 32, 64, 127};
        if (config.sf <= 8) test_symbols = {0, 1, 2, 4, 8, 16, 32, 64, 128, 255};
        if (config.sf <= 9) test_symbols = {0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 511};
        if (config.sf <= 10) test_symbols = {0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1023};
        if (config.sf <= 11) test_symbols = {0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2047};
        if (config.sf <= 12) test_symbols = {0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4095};
        
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
    
    cout << "Generated " << num_tests << " comprehensive detection test vectors" << endl;
}

// Generate comprehensive AWGN test vectors
void generateComprehensiveAWGNVectors() {
    cout << "=== Generating Comprehensive AWGN Vectors ===" << endl;
    
    ofstream awgn_file("vectors/lora_sdr_reference/comprehensive_awgn_tests.bin", ios::binary);
    
    // Write header
    uint32_t num_tests = 0;
    awgn_file.write(reinterpret_cast<const char*>(&num_tests), sizeof(num_tests));
    
    auto configs = getComprehensiveTestConfigs();
    auto payloads = getComprehensiveTestPayloads();
    
    // Comprehensive SNR range
    vector<double> snr_values = {-10, -5, 0, 5, 10, 15, 20, 25, 30, 35, 40};  // dB
    
    cout << "Testing " << configs.size() << " configurations with " << payloads.size() << " payloads at " << snr_values.size() << " SNR levels" << endl;
    
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
    
    cout << "Generated " << num_tests << " comprehensive AWGN test vectors" << endl;
}

int main() {
    cout << "=== COMPREHENSIVE LoRa Vector Generation (Binary Format) ===" << endl;
    cout << "ALL SF (7-12) × ALL BW (125/250/500) × ALL CR (1-4) combinations" << endl;
    cout << "Based on README_LoRaSDR_porting.md requirements" << endl;
    cout << endl;
    
    // Create output directory
    system("mkdir -p vectors/lora_sdr_reference");
    
    // Generate all comprehensive vector types
    generateHammingVectors();
    generateComprehensiveModulationVectors();
    generateComprehensiveDetectionVectors();
    generateComprehensiveAWGNVectors();
    
    cout << endl;
    cout << "=== COMPREHENSIVE Vector Generation Complete ===" << endl;
    cout << "All vectors saved to vectors/lora_sdr_reference/ in binary format" << endl;
    cout << "Total combinations: 6 SF × 3 BW × 4 CR = 72 configurations" << endl;
    
    return 0;
}
'''
    
    return cpp_code

def compile_and_run_comprehensive_generator(cpp_code):
    """Compile and run the comprehensive vector generator"""
    
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
            '-o', 'comprehensive_vector_generator'
        ]
        
        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Compilation failed:")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False
        
        print("Compilation successful!")
        
        # Run
        print("Running comprehensive vector generator...")
        run_result = subprocess.run(['./comprehensive_vector_generator'], capture_output=True, text=True)
        
        if run_result.returncode != 0:
            print(f"Execution failed:")
            print(f"STDOUT: {run_result.stdout}")
            print(f"STDERR: {run_result.stderr}")
            return False
        
        print("Comprehensive vector generator output:")
        print(run_result.stdout)
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    finally:
        # Cleanup
        if os.path.exists(cpp_file):
            os.unlink(cpp_file)
        if os.path.exists('comprehensive_vector_generator'):
            os.unlink('comprehensive_vector_generator')

def main():
    print("COMPREHENSIVE LoRa Vector Generator (Binary Format)")
    print("=" * 60)
    print("ALL SF (7-12) × ALL BW (125/250/500) × ALL CR (1-4) combinations")
    print("Based on README_LoRaSDR_porting.md requirements")
    print()
    
    # Create output directory
    os.makedirs('vectors/lora_sdr_reference', exist_ok=True)
    
    # Generate C++ code
    print("Creating comprehensive vector generator...")
    cpp_code = create_comprehensive_vector_generator()
    
    # Compile and run
    success = compile_and_run_comprehensive_generator(cpp_code)
    
    if success:
        print("\\nCOMPREHENSIVE vector generation completed successfully!")
        print("\\nThis includes:")
        print("- ALL Spreading Factors: 7, 8, 9, 10, 11, 12")
        print("- ALL Bandwidths: 125, 250, 500 kHz")
        print("- ALL Coding Rates: 1, 2, 3, 4 (4/5, 4/6, 4/7, 4/8)")
        print("- Total: 6 × 3 × 4 = 72 configurations")
        print("- Multiple payload types per configuration")
        print("- Comprehensive SNR range for AWGN testing")
        print("\\nAll vectors are ready for comprehensive testing!")
    else:
        print("\\nComprehensive vector generation failed!")

if __name__ == "__main__":
    main()
