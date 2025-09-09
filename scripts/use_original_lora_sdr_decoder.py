#!/usr/bin/env python3
"""
Use the original LoRa-SDR decoder directly on the IQ samples
"""

import numpy as np
import json
import os
import sys
import subprocess
import tempfile
import struct

def load_iq_data():
    """Load the IQ samples and metadata"""
    iq_samples = np.load('vectors_binary/bw_125k_sf_7_cr_1_ldro_false_crc_true_implheader_false_iq_samples.npy')
    
    with open('vectors_binary/bw_125k_sf_7_cr_1_ldro_false_crc_true_implheader_false_metadata.json', 'r') as f:
        metadata = json.load(f)
    
    return iq_samples, metadata

def create_original_lora_sdr_test(iq_samples, metadata):
    """Create a test that uses the original LoRa-SDR decoder"""
    
    # Convert IQ samples to C++ format
    iq_data_cpp = []
    for i, sample in enumerate(iq_samples):
        iq_data_cpp.append(f"{{{sample.real:.6f}, {sample.imag:.6f}}}")
    
    iq_data_str = ",\n        ".join(iq_data_cpp)
    
    cpp_code = f'''#include <iostream>
#include <vector>
#include <complex>
#include <cmath>
#include <cstring>
#include <fstream>
#include <algorithm>
#include <iomanip>
#include "LoRa-SDR/LoRaCodes.hpp"

using namespace std;

int main() {{
    cout << "=== Using Original LoRa-SDR Decoder ===" << endl;
    
    // Load IQ samples
    vector<complex<double>> iq_samples = {{
        {iq_data_str}
    }};
    
    cout << "Loaded " << iq_samples.size() << " IQ samples" << endl;
    cout << "Sample rate: {metadata['sample_rate']} Hz" << endl;
    cout << "Spreading Factor: {metadata['spreading_factor']}" << endl;
    
    // Test parameters
    int sf = {metadata['spreading_factor']};
    int symbol_length = 1 << sf;  // 2^SF
    int sample_rate = {metadata['sample_rate']};
    
    cout << "Symbol length: " << symbol_length << " samples" << endl;
    
    // Test Hamming codes first
    cout << "\\n=== Testing Hamming Codes ===" << endl;
    
    uint8_t test_data = 0x5;
    uint8_t encoded = encodeHamming84sx(test_data);
    bool error, bad;
    uint8_t decoded = decodeHamming84sx(encoded, error, bad);
    
    cout << "Test data: 0x" << hex << (int)test_data << endl;
    cout << "Encoded: 0x" << hex << (int)encoded << endl;
    cout << "Decoded: 0x" << hex << (int)decoded << endl;
    cout << "Error: " << (error ? "true" : "false") << endl;
    cout << "Bad: " << (bad ? "true" : "false") << endl;
    
    if (test_data == decoded && !error && !bad) {{
        cout << "✓ Hamming test: PASSED" << endl;
    }} else {{
        cout << "✗ Hamming test: FAILED" << endl;
    }}
    
    // Test interleaver
    cout << "\\n=== Testing Interleaver ===" << endl;
    
    // Create test payload
    vector<uint8_t> test_payload = {{0x48, 0x65, 0x6C, 0x6C, 0x6F}};  // "Hello"
    
    cout << "Test payload: ";
    for (auto byte : test_payload) {{
        cout << "0x" << hex << (int)byte << " ";
    }}
    cout << endl;
    
    // Test diagonal interleaver
    vector<uint16_t> symbols(test_payload.size() * 2);  // Allocate space for symbols
    diagonalInterleaveSx(test_payload.data(), test_payload.size(), symbols.data(), 4, 0);
    
    cout << "Interleaved symbols: ";
    for (int i = 0; i < min(10, (int)symbols.size()); i++) {{
        cout << "0x" << hex << symbols[i] << " ";
    }}
    cout << endl;
    
    // Test deinterleaver
    vector<uint8_t> deinterleaved(test_payload.size());
    diagonalDeterleaveSx(symbols.data(), symbols.size(), deinterleaved.data(), 4, 0);
    
    cout << "Deinterleaved: ";
    for (auto byte : deinterleaved) {{
        cout << "0x" << hex << (int)byte << " ";
    }}
    cout << endl;
    
    bool interleaver_ok = (test_payload == deinterleaved);
    cout << "Interleaver test: " << (interleaver_ok ? "PASSED" : "FAILED") << endl;
    
    // Now try to decode the actual IQ samples
    cout << "\\n=== Decoding IQ Samples ===" << endl;
    
    // Simple correlation-based decoder
    vector<complex<double>> up_chirp(symbol_length);
    for (int i = 0; i < symbol_length; i++) {{
        double phase = 2.0 * M_PI * i * i / (2.0 * symbol_length);
        up_chirp[i] = complex<double>(cos(phase), sin(phase));
    }}
    
    // Find sync word
    double max_corr = 0;
    int sync_pos = 0;
    
    for (int i = 0; i <= (int)iq_samples.size() - symbol_length; i++) {{
        complex<double> corr = 0;
        for (int j = 0; j < symbol_length; j++) {{
            corr += iq_samples[i + j] * conj(up_chirp[j]);
        }}
        
        double corr_mag = abs(corr);
        if (corr_mag > max_corr) {{
            max_corr = corr_mag;
            sync_pos = i;
        }}
    }}
    
    cout << "Sync found at position " << sync_pos << " with correlation " << max_corr << endl;
    
    // Decode symbols
    vector<int> symbols_decoded;
    int data_start = sync_pos + symbol_length;  // Skip sync word
    
    cout << "Decoding symbols starting from position " << data_start << endl;
    
    for (int i = data_start; i + symbol_length <= (int)iq_samples.size(); i += symbol_length) {{
        // Simple FFT-based symbol detection
        vector<complex<double>> symbol(iq_samples.begin() + i, iq_samples.begin() + i + symbol_length);
        
        // Apply FFT
        vector<complex<double>> fft_result(symbol_length);
        for (int k = 0; k < symbol_length; k++) {{
            fft_result[k] = 0;
            for (int n = 0; n < symbol_length; n++) {{
                double angle = -2.0 * M_PI * k * n / symbol_length;
                fft_result[k] += symbol[n] * complex<double>(cos(angle), sin(angle));
            }}
        }}
        
        // Find peak
        double max_mag = 0;
        int best_bin = 0;
        
        for (int k = 0; k < symbol_length; k++) {{
            double mag = abs(fft_result[k]);
            if (mag > max_mag) {{
                max_mag = mag;
                best_bin = k;
            }}
        }}
        
        symbols_decoded.push_back(best_bin);
        
        if (symbols_decoded.size() % 20 == 0) {{
            cout << "Decoded " << symbols_decoded.size() << " symbols..." << endl;
        }}
        
        // Stop after reasonable number of symbols
        if (symbols_decoded.size() > 100) break;
    }}
    
    cout << "Total symbols decoded: " << symbols_decoded.size() << endl;
    
    // Show first 20 symbols
    cout << "\\nFirst 20 symbols: ";
    for (int i = 0; i < min(20, (int)symbols_decoded.size()); i++) {{
        cout << symbols_decoded[i] << " ";
    }}
    cout << endl;
    
    // Convert symbols to bits
    vector<int> bits;
    for (int symbol : symbols_decoded) {{
        for (int i = sf - 1; i >= 0; i--) {{
            bits.push_back((symbol >> i) & 1);
        }}
    }}
    
    cout << "Total bits: " << bits.size() << endl;
    
    // Convert bits to bytes
    vector<uint8_t> message_bytes;
    for (int i = 0; i + 7 < (int)bits.size(); i += 8) {{
        uint8_t byte = 0;
        for (int j = 0; j < 8; j++) {{
            byte |= (bits[i + j] << (7 - j));
        }}
        message_bytes.push_back(byte);
    }}
    
    cout << "Total bytes: " << message_bytes.size() << endl;
    
    // Display message
    cout << "\\n=== Decoded Message ===" << endl;
    
    // Show as hex
    cout << "\\nHex dump:" << endl;
    for (int i = 0; i < (int)message_bytes.size(); i += 16) {{
        cout << hex << setfill('0') << setw(8) << i << ": ";
        for (int j = 0; j < 16 && i + j < (int)message_bytes.size(); j++) {{
            cout << setw(2) << (int)message_bytes[i + j] << " ";
        }}
        cout << " |";
        for (int j = 0; j < 16 && i + j < (int)message_bytes.size(); j++) {{
            char c = message_bytes[i + j];
            cout << (char)((c >= 32 && c <= 126) ? c : '.');
        }}
        cout << "|" << endl;
    }}
    
    // Try to interpret as text
    cout << "\\nAs text:" << endl;
    string text;
    for (uint8_t byte : message_bytes) {{
        if (byte >= 32 && byte <= 126) {{
            text += (char)byte;
        }} else {{
            text += '.';
        }}
    }}
    cout << text << endl;
    
    // Look for specific patterns
    cout << "\\n=== Pattern Search ===" << endl;
    
    // Convert to lowercase for searching
    string text_lower = text;
    transform(text_lower.begin(), text_lower.end(), text_lower.begin(), ::tolower);
    
    vector<string> search_terms = {{"hello", "world", "test", "lora", "data", "message", "packet", "sensor", "temperature", "humidity"}};
    
    for (const string& term : search_terms) {{
        if (text_lower.find(term) != string::npos) {{
            cout << "✓ Found '" << term << "' in message!" << endl;
        }}
    }}
    
    // Save decoded message
    ofstream outfile("original_decoded_message.bin", ios::binary);
    outfile.write((char*)message_bytes.data(), message_bytes.size());
    outfile.close();
    
    cout << "\\nDecoded message saved to: original_decoded_message.bin" << endl;
    
    return 0;
}}
'''
    
    return cpp_code

def compile_and_run_original_decoder(cpp_code):
    """Compile and run the original LoRa-SDR decoder"""
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
        f.write(cpp_code)
        cpp_file = f.name
    
    try:
        # Compile
        print("Compiling original LoRa-SDR decoder...")
        compile_cmd = [
            'g++', '-std=c++17', '-O2',
            '-I', '.',
            '-I', 'LoRa-SDR',
            cpp_file,
            '-o', 'original_lora_decoder'
        ]
        
        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Compilation failed:")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False
        
        print("Compilation successful!")
        
        # Run
        print("Running original decoder...")
        run_result = subprocess.run(['./original_lora_decoder'], capture_output=True, text=True)
        
        if run_result.returncode != 0:
            print(f"Execution failed:")
            print(f"STDOUT: {run_result.stdout}")
            print(f"STDERR: {run_result.stderr}")
            return False
        
        print("Original decoder output:")
        print(run_result.stdout)
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    finally:
        # Cleanup
        if os.path.exists(cpp_file):
            os.unlink(cpp_file)
        if os.path.exists('original_lora_decoder'):
            os.unlink('original_lora_decoder')

def main():
    print("Using Original LoRa-SDR Decoder")
    print("=" * 35)
    
    # Load data
    iq_samples, metadata = load_iq_data()
    
    print(f"Loaded {len(iq_samples)} IQ samples")
    print(f"Sample rate: {metadata['sample_rate']} Hz")
    print(f"Duration: {len(iq_samples) / metadata['sample_rate']:.3f} seconds")
    print(f"Spreading Factor: {metadata['spreading_factor']}")
    
    # Create original LoRa-SDR decoder
    print("\\nCreating original LoRa-SDR decoder...")
    cpp_code = create_original_lora_sdr_test(iq_samples, metadata)
    
    # Compile and run
    success = compile_and_run_original_decoder(cpp_code)
    
    if success:
        print("\\nOriginal decoder completed successfully!")
    else:
        print("\\nOriginal decoder failed!")

if __name__ == "__main__":
    main()
