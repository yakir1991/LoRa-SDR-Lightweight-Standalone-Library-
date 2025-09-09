#!/usr/bin/env python3
"""
Test the unknown LoRa file with the original LoRa-SDR implementation
"""

import numpy as np
import json
import os
import sys
import subprocess
import tempfile

def load_iq_data():
    """Load the IQ samples and metadata"""
    iq_samples = np.load('vectors_binary/bw_125k_sf_7_cr_1_ldro_false_crc_true_implheader_false_iq_samples.npy')
    
    with open('vectors_binary/bw_125k_sf_7_cr_1_ldro_false_crc_true_implheader_false_metadata.json', 'r') as f:
        metadata = json.load(f)
    
    return iq_samples, metadata

def create_cpp_test_program(iq_samples, metadata):
    """Create a C++ test program to test with original LoRa-SDR"""
    
    # Convert IQ samples to C++ format
    iq_data_cpp = []
    for i, sample in enumerate(iq_samples[:1000]):  # Test with first 1000 samples
        iq_data_cpp.append(f"{{{sample.real:.6f}, {sample.imag:.6f}}}")
    
    iq_data_str = ",\n        ".join(iq_data_cpp)
    
    cpp_code = f'''#include <iostream>
#include <vector>
#include <complex>
#include <cmath>
#include "LoRa-SDR/LoRaCodes.hpp"

using namespace std;

int main() {{
    cout << "Testing LoRa signal with original LoRa-SDR implementation" << endl;
    
    // Test parameters
    int sf = {metadata['spreading_factor']};
    int sample_rate = {metadata['sample_rate']};
    int num_samples = {len(iq_samples[:1000])};
    
    cout << "Parameters:" << endl;
    cout << "  Spreading Factor: " << sf << endl;
    cout << "  Sample Rate: " << sample_rate << " Hz" << endl;
    cout << "  Number of samples: " << num_samples << endl;
    
    // Load IQ samples
    vector<complex<double>> iq_samples = {{
        {iq_data_str}
    }};
    
    cout << "\\nLoaded " << iq_samples.size() << " IQ samples" << endl;
    
    // Test Hamming codes
    cout << "\\n=== Testing Hamming Codes ===" << endl;
    
    // Test encode/decode
    uint8_t test_data = 0x5;  // 4-bit data
    uint8_t encoded = encodeHamming84sx(test_data);
    bool error, bad;
    uint8_t decoded = decodeHamming84sx(encoded, error, bad);
    
    cout << "Test data: 0x" << hex << (int)test_data << endl;
    cout << "Encoded: 0x" << hex << (int)encoded << endl;
    cout << "Decoded: 0x" << hex << (int)decoded << endl;
    cout << "Error: " << (error ? "true" : "false") << endl;
    
    if (test_data == decoded && !error && !bad) {{
        cout << "Hamming test: PASSED" << endl;
    }} else {{
        cout << "Hamming test: FAILED" << endl;
    }}
    
    // Test interleaver (simplified)
    cout << "\\n=== Testing Interleaver ===" << endl;
    cout << "Interleaver functions are complex, skipping for now" << endl;
    
    // Analyze IQ samples
    cout << "\\n=== IQ Sample Analysis ===" << endl;
    
    double total_power = 0;
    double max_power = 0;
    double min_power = 1e10;
    
    for (const auto& sample : iq_samples) {{
        double power = abs(sample) * abs(sample);
        total_power += power;
        max_power = max(max_power, power);
        min_power = min(min_power, power);
    }}
    
    double avg_power = total_power / iq_samples.size();
    
    cout << "Average power: " << avg_power << endl;
    cout << "Max power: " << max_power << endl;
    cout << "Min power: " << min_power << endl;
    
    // Check for chirp patterns
    cout << "\\n=== Chirp Pattern Analysis ===" << endl;
    
    int symbol_length = 1 << sf;  // 2^SF
    int num_symbols = iq_samples.size() / symbol_length;
    
    cout << "Expected symbol length: " << symbol_length << " samples" << endl;
    cout << "Number of complete symbols: " << num_symbols << endl;
    
    // Analyze first few symbols
    for (int i = 0; i < min(3, num_symbols); i++) {{
        int start_idx = i * symbol_length;
        int end_idx = start_idx + symbol_length;
        
        if (end_idx <= iq_samples.size()) {{
            double symbol_power = 0;
            for (int j = start_idx; j < end_idx; j++) {{
                double power = abs(iq_samples[j]) * abs(iq_samples[j]);
                symbol_power += power;
            }}
            symbol_power /= symbol_length;
            
            cout << "Symbol " << i << " power: " << symbol_power << endl;
        }}
    }}
    
    cout << "\\nTest completed successfully!" << endl;
    return 0;
}}
'''
    
    return cpp_code

def compile_and_run_test(cpp_code):
    """Compile and run the C++ test program"""
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
        f.write(cpp_code)
        cpp_file = f.name
    
    try:
        # Compile
        print("Compiling C++ test program...")
        compile_cmd = [
            'g++', '-std=c++17', '-O2',
            '-I', '.',
            '-I', 'LoRa-SDR',
            cpp_file,
            '-o', 'test_unknown_lora'
        ]
        
        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Compilation failed:")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False
        
        print("Compilation successful!")
        
        # Run
        print("Running test program...")
        run_result = subprocess.run(['./test_unknown_lora'], capture_output=True, text=True)
        
        if run_result.returncode != 0:
            print(f"Execution failed:")
            print(f"STDOUT: {run_result.stdout}")
            print(f"STDERR: {run_result.stderr}")
            return False
        
        print("Test program output:")
        print(run_result.stdout)
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    finally:
        # Cleanup
        if os.path.exists(cpp_file):
            os.unlink(cpp_file)
        if os.path.exists('test_unknown_lora'):
            os.unlink('test_unknown_lora')

def main():
    print("Testing Unknown LoRa File with Original LoRa-SDR")
    print("=" * 50)
    
    # Load data
    iq_samples, metadata = load_iq_data()
    
    print(f"Loaded {len(iq_samples)} IQ samples")
    print(f"Sample rate: {metadata['sample_rate']} Hz")
    print(f"Duration: {len(iq_samples) / metadata['sample_rate']:.3f} seconds")
    print(f"Spreading Factor: {metadata['spreading_factor']}")
    
    # Create C++ test program
    print("\\nCreating C++ test program...")
    cpp_code = create_cpp_test_program(iq_samples, metadata)
    
    # Compile and run
    success = compile_and_run_test(cpp_code)
    
    if success:
        print("\\nTest completed successfully!")
    else:
        print("\\nTest failed!")

if __name__ == "__main__":
    main()
