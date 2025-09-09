#!/usr/bin/env python3
"""
Decode the LoRa message from the unknown file using the original LoRa-SDR
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

def create_advanced_cpp_decoder(iq_samples, metadata):
    """Create an advanced C++ decoder using the original LoRa-SDR"""
    
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
#include "LoRa-SDR/LoRaCodes.hpp"

using namespace std;

// Simple FFT implementation for symbol detection
vector<complex<double>> fft(const vector<complex<double>>& input) {{
    int N = input.size();
    if (N == 1) return input;
    
    vector<complex<double>> even(N/2), odd(N/2);
    for (int i = 0; i < N/2; i++) {{
        even[i] = input[2*i];
        odd[i] = input[2*i + 1];
    }}
    
    vector<complex<double>> even_fft = fft(even);
    vector<complex<double>> odd_fft = fft(odd);
    
    vector<complex<double>> result(N);
    for (int i = 0; i < N/2; i++) {{
        complex<double> t = polar(1.0, -2.0 * M_PI * i / N) * odd_fft[i];
        result[i] = even_fft[i] + t;
        result[i + N/2] = even_fft[i] - t;
    }}
    
    return result;
}}

// Generate up chirp for correlation
vector<complex<double>> generateUpChirp(int N, int sf) {{
    vector<complex<double>> chirp(N);
    for (int i = 0; i < N; i++) {{
        double phase = 2.0 * M_PI * i * i / (2.0 * N);
        chirp[i] = complex<double>(cos(phase), sin(phase));
    }}
    return chirp;
}}

// Generate down chirp for correlation
vector<complex<double>> generateDownChirp(int N, int sf) {{
    vector<complex<double>> chirp(N);
    for (int i = 0; i < N; i++) {{
        double phase = -2.0 * M_PI * i * i / (2.0 * N);
        chirp[i] = complex<double>(cos(phase), sin(phase));
    }}
    return chirp;
}}

// Find sync word using correlation
int findSyncWord(const vector<complex<double>>& signal, int N) {{
    vector<complex<double>> up_chirp = generateUpChirp(N, 7);
    
    double max_corr = 0;
    int best_pos = 0;
    
    for (int i = 0; i <= (int)signal.size() - N; i++) {{
        complex<double> corr = 0;
        for (int j = 0; j < N; j++) {{
            corr += signal[i + j] * conj(up_chirp[j]);
        }}
        
        double corr_mag = abs(corr);
        if (corr_mag > max_corr) {{
            max_corr = corr_mag;
            best_pos = i;
        }}
    }}
    
    cout << "Max correlation: " << max_corr << " at position " << best_pos << endl;
    return best_pos;
}}

// Decode a single symbol using FFT
int decodeSymbol(const vector<complex<double>>& symbol, int N) {{
    vector<complex<double>> fft_result = fft(symbol);
    
    double max_mag = 0;
    int best_bin = 0;
    
    for (int i = 0; i < N; i++) {{
        double mag = abs(fft_result[i]);
        if (mag > max_mag) {{
            max_mag = mag;
            best_bin = i;
        }}
    }}
    
    return best_bin;
}}

// Decode the LoRa message
vector<int> decodeLoRaMessage(const vector<complex<double>>& signal, int sf) {{
    int N = 1 << sf;  // 2^SF
    cout << "Symbol length: " << N << " samples" << endl;
    
    // Find sync word
    int sync_pos = findSyncWord(signal, N);
    cout << "Sync found at position: " << sync_pos << endl;
    
    // Skip sync word and start decoding data symbols
    int data_start = sync_pos + N;  // Skip first symbol (sync)
    vector<int> symbols;
    
    // Decode symbols
    for (int i = data_start; i + N <= (int)signal.size(); i += N) {{
        vector<complex<double>> symbol(signal.begin() + i, signal.begin() + i + N);
        int decoded_symbol = decodeSymbol(symbol, N);
        symbols.push_back(decoded_symbol);
        
        if (symbols.size() % 10 == 0) {{
            cout << "Decoded " << symbols.size() << " symbols..." << endl;
        }}
        
        // Stop after reasonable number of symbols
        if (symbols.size() > 100) break;
    }}
    
    return symbols;
}}

// Convert symbols to bytes
vector<uint8_t> symbolsToBytes(const vector<int>& symbols, int sf) {{
    vector<uint8_t> bytes;
    
    // Group symbols into bits
    vector<int> bits;
    for (int symbol : symbols) {{
        for (int i = sf - 1; i >= 0; i--) {{
            bits.push_back((symbol >> i) & 1);
        }}
    }}
    
    // Convert bits to bytes
    for (int i = 0; i + 7 < (int)bits.size(); i += 8) {{
        uint8_t byte = 0;
        for (int j = 0; j < 8; j++) {{
            byte |= (bits[i + j] << (7 - j));
        }}
        bytes.push_back(byte);
    }}
    
    return bytes;
}}

int main() {{
    cout << "=== LoRa Message Decoder ===" << endl;
    
    // Load IQ samples
    vector<complex<double>> iq_samples = {{
        {iq_data_str}
    }};
    
    cout << "Loaded " << iq_samples.size() << " IQ samples" << endl;
    
    // Decode the message
    int sf = {metadata['spreading_factor']};
    vector<int> symbols = decodeLoRaMessage(iq_samples, sf);
    
    cout << "\\nDecoded " << symbols.size() << " symbols" << endl;
    
    // Show first 20 symbols
    cout << "\\nFirst 20 symbols: ";
    for (int i = 0; i < min(20, (int)symbols.size()); i++) {{
        cout << symbols[i] << " ";
    }}
    cout << endl;
    
    // Convert to bytes
    vector<uint8_t> message_bytes = symbolsToBytes(symbols, sf);
    
    cout << "\\nDecoded " << message_bytes.size() << " bytes" << endl;
    
    // Show first 50 bytes as hex
    cout << "\\nFirst 50 bytes (hex): ";
    for (int i = 0; i < min(50, (int)message_bytes.size()); i++) {{
        cout << "0x" << hex << (int)message_bytes[i] << " ";
    }}
    cout << endl;
    
    // Try to interpret as text
    cout << "\\nAs text (first 100 chars): ";
    for (int i = 0; i < min(100, (int)message_bytes.size()); i++) {{
        char c = message_bytes[i];
        if (c >= 32 && c <= 126) {{
            cout << c;
        }} else {{
            cout << ".";
        }}
    }}
    cout << endl;
    
    // Save decoded message
    ofstream outfile("decoded_message.bin", ios::binary);
    outfile.write((char*)message_bytes.data(), message_bytes.size());
    outfile.close();
    
    cout << "\\nDecoded message saved to: decoded_message.bin" << endl;
    
    return 0;
}}
'''
    
    return cpp_code

def compile_and_run_decoder(cpp_code):
    """Compile and run the C++ decoder"""
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
        f.write(cpp_code)
        cpp_file = f.name
    
    try:
        # Compile
        print("Compiling C++ decoder...")
        compile_cmd = [
            'g++', '-std=c++17', '-O2',
            '-I', '.',
            '-I', 'LoRa-SDR',
            cpp_file,
            '-o', 'lora_decoder'
        ]
        
        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Compilation failed:")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False
        
        print("Compilation successful!")
        
        # Run
        print("Running decoder...")
        run_result = subprocess.run(['./lora_decoder'], capture_output=True, text=True)
        
        if run_result.returncode != 0:
            print(f"Execution failed:")
            print(f"STDOUT: {run_result.stdout}")
            print(f"STDERR: {run_result.stderr}")
            return False
        
        print("Decoder output:")
        print(run_result.stdout)
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    finally:
        # Cleanup
        if os.path.exists(cpp_file):
            os.unlink(cpp_file)
        if os.path.exists('lora_decoder'):
            os.unlink('lora_decoder')

def analyze_decoded_message():
    """Analyze the decoded message if it exists"""
    if os.path.exists('decoded_message.bin'):
        with open('decoded_message.bin', 'rb') as f:
            data = f.read()
        
        print(f"\\nDecoded message analysis:")
        print(f"Size: {len(data)} bytes")
        
        # Try different interpretations
        print("\\nAs hex:")
        print(data[:100].hex())
        
        print("\\nAs text:")
        text = ""
        for byte in data[:200]:
            if 32 <= byte <= 126:
                text += chr(byte)
            else:
                text += f"\\x{byte:02x}"
        print(text)
        
        # Try to find patterns
        print("\\nLooking for patterns...")
        
        # Check for common LoRa patterns
        if data.startswith(b'\\x40'):  # LoRa preamble
            print("Found LoRa preamble!")
        
        # Check for JSON
        try:
            json_data = json.loads(data.decode('utf-8'))
            print("Found valid JSON!")
            print(json.dumps(json_data, indent=2))
        except:
            pass
        
        # Check for common text patterns
        text_str = data.decode('utf-8', errors='ignore')
        if 'hello' in text_str.lower():
            print("Found 'hello' in message!")
        if 'test' in text_str.lower():
            print("Found 'test' in message!")
        if 'lora' in text_str.lower():
            print("Found 'lora' in message!")

def main():
    print("LoRa Message Decoder")
    print("=" * 30)
    
    # Load data
    iq_samples, metadata = load_iq_data()
    
    print(f"Loaded {len(iq_samples)} IQ samples")
    print(f"Sample rate: {metadata['sample_rate']} Hz")
    print(f"Duration: {len(iq_samples) / metadata['sample_rate']:.3f} seconds")
    print(f"Spreading Factor: {metadata['spreading_factor']}")
    
    # Create C++ decoder
    print("\\nCreating C++ decoder...")
    cpp_code = create_advanced_cpp_decoder(iq_samples, metadata)
    
    # Compile and run
    success = compile_and_run_decoder(cpp_code)
    
    if success:
        print("\\nDecoder completed successfully!")
        analyze_decoded_message()
    else:
        print("\\nDecoder failed!")

if __name__ == "__main__":
    main()
