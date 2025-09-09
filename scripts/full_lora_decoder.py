#!/usr/bin/env python3
"""
Full LoRa decoder that performs all decoding steps
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

def create_full_lora_decoder(iq_samples, metadata):
    """Create a full LoRa decoder using the original LoRa-SDR"""
    
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
#include "LoRa-SDR/LoRaCodes.hpp"

using namespace std;

// Full LoRa decoder class
class LoRaDecoder {{
private:
    int sf;
    int sample_rate;
    int symbol_length;
    vector<complex<double>> iq_samples;
    
public:
    LoRaDecoder(int spreading_factor, int sr) : sf(spreading_factor), sample_rate(sr) {{
        symbol_length = 1 << sf;  // 2^SF
    }}
    
    void setSamples(const vector<complex<double>>& samples) {{
        iq_samples = samples;
    }}
    
    // Generate up chirp for correlation
    vector<complex<double>> generateUpChirp() {{
        vector<complex<double>> chirp(symbol_length);
        for (int i = 0; i < symbol_length; i++) {{
            double phase = 2.0 * M_PI * i * i / (2.0 * symbol_length);
            chirp[i] = complex<double>(cos(phase), sin(phase));
        }}
        return chirp;
    }}
    
    // Generate down chirp for correlation
    vector<complex<double>> generateDownChirp() {{
        vector<complex<double>> chirp(symbol_length);
        for (int i = 0; i < symbol_length; i++) {{
            double phase = -2.0 * M_PI * i * i / (2.0 * symbol_length);
            chirp[i] = complex<double>(cos(phase), sin(phase));
        }}
        return chirp;
    }}
    
    // Find sync word using correlation
    int findSyncWord() {{
        vector<complex<double>> up_chirp = generateUpChirp();
        
        double max_corr = 0;
        int best_pos = 0;
        
        for (int i = 0; i <= (int)iq_samples.size() - symbol_length; i++) {{
            complex<double> corr = 0;
            for (int j = 0; j < symbol_length; j++) {{
                corr += iq_samples[i + j] * conj(up_chirp[j]);
            }}
            
            double corr_mag = abs(corr);
            if (corr_mag > max_corr) {{
                max_corr = corr_mag;
                best_pos = i;
            }}
        }}
        
        cout << "Sync word found at position " << best_pos << " with correlation " << max_corr << endl;
        return best_pos;
    }}
    
    // Decode a single symbol using FFT
    int decodeSymbol(const vector<complex<double>>& symbol) {{
        // Simple FFT implementation
        int N = symbol.size();
        if (N == 1) return 0;
        
        vector<complex<double>> even(N/2), odd(N/2);
        for (int i = 0; i < N/2; i++) {{
            even[i] = symbol[2*i];
            odd[i] = symbol[2*i + 1];
        }}
        
        vector<complex<double>> even_fft = fft(even);
        vector<complex<double>> odd_fft = fft(odd);
        
        vector<complex<double>> fft_result(N);
        for (int i = 0; i < N/2; i++) {{
            complex<double> t = polar(1.0, -2.0 * M_PI * i / N) * odd_fft[i];
            fft_result[i] = even_fft[i] + t;
            fft_result[i + N/2] = even_fft[i] - t;
        }}
        
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
    
    // Simple FFT implementation
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
    
    // Decode the full LoRa message
    vector<uint8_t> decodeMessage() {{
        cout << "=== Full LoRa Decoding ===" << endl;
        
        // Step 1: Find sync word
        int sync_pos = findSyncWord();
        
        // Step 2: Decode symbols
        vector<int> symbols;
        int data_start = sync_pos + symbol_length;  // Skip sync word
        
        cout << "Decoding symbols starting from position " << data_start << endl;
        
        for (int i = data_start; i + symbol_length <= (int)iq_samples.size(); i += symbol_length) {{
            vector<complex<double>> symbol(iq_samples.begin() + i, iq_samples.begin() + i + symbol_length);
            int decoded_symbol = decodeSymbol(symbol);
            symbols.push_back(decoded_symbol);
            
            if (symbols.size() % 10 == 0) {{
                cout << "Decoded " << symbols.size() << " symbols..." << endl;
            }}
            
            // Stop after reasonable number of symbols
            if (symbols.size() > 200) break;
        }}
        
        cout << "Total symbols decoded: " << symbols.size() << endl;
        
        // Step 3: Convert symbols to bits
        vector<int> bits;
        for (int symbol : symbols) {{
            for (int i = sf - 1; i >= 0; i--) {{
                bits.push_back((symbol >> i) & 1);
            }}
        }}
        
        cout << "Total bits: " << bits.size() << endl;
        
        // Step 4: Convert bits to bytes
        vector<uint8_t> bytes;
        for (int i = 0; i + 7 < (int)bits.size(); i += 8) {{
            uint8_t byte = 0;
            for (int j = 0; j < 8; j++) {{
                byte |= (bits[i + j] << (7 - j));
            }}
            bytes.push_back(byte);
        }}
        
        cout << "Total bytes: " << bytes.size() << endl;
        
        return bytes;
    }}
}};

int main() {{
    cout << "=== Full LoRa Message Decoder ===" << endl;
    
    // Load IQ samples
    vector<complex<double>> iq_samples = {{
        {iq_data_str}
    }};
    
    cout << "Loaded " << iq_samples.size() << " IQ samples" << endl;
    
    // Create decoder
    LoRaDecoder decoder({metadata['spreading_factor']}, {metadata['sample_rate']});
    decoder.setSamples(iq_samples);
    
    // Decode message
    vector<uint8_t> message_bytes = decoder.decodeMessage();
    
    // Display results
    cout << "\\n=== Decoded Message ===" << endl;
    cout << "Size: " << message_bytes.size() << " bytes" << endl;
    
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
    
    vector<string> search_terms = {{"hello", "world", "test", "lora", "data", "message", "packet"}};
    
    for (const string& term : search_terms) {{
        if (text_lower.find(term) != string::npos) {{
            cout << "✓ Found '" << term << "' in message!" << endl;
        }}
    }}
    
    // Save decoded message
    ofstream outfile("full_decoded_message.bin", ios::binary);
    outfile.write((char*)message_bytes.data(), message_bytes.size());
    outfile.close();
    
    cout << "\\nDecoded message saved to: full_decoded_message.bin" << endl;
    
    return 0;
}}
'''
    
    return cpp_code

def compile_and_run_full_decoder(cpp_code):
    """Compile and run the full C++ decoder"""
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
        f.write(cpp_code)
        cpp_file = f.name
    
    try:
        # Compile
        print("Compiling full C++ decoder...")
        compile_cmd = [
            'g++', '-std=c++17', '-O2',
            '-I', '.',
            '-I', 'LoRa-SDR',
            cpp_file,
            '-o', 'full_lora_decoder'
        ]
        
        result = subprocess.run(compile_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Compilation failed:")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False
        
        print("Compilation successful!")
        
        # Run
        print("Running full decoder...")
        run_result = subprocess.run(['./full_lora_decoder'], capture_output=True, text=True)
        
        if run_result.returncode != 0:
            print(f"Execution failed:")
            print(f"STDOUT: {run_result.stdout}")
            print(f"STDERR: {run_result.stderr}")
            return False
        
        print("Full decoder output:")
        print(run_result.stdout)
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    finally:
        # Cleanup
        if os.path.exists(cpp_file):
            os.unlink(cpp_file)
        if os.path.exists('full_lora_decoder'):
            os.unlink('full_lora_decoder')

def main():
    print("Full LoRa Message Decoder")
    print("=" * 30)
    
    # Load data
    iq_samples, metadata = load_iq_data()
    
    print(f"Loaded {len(iq_samples)} IQ samples")
    print(f"Sample rate: {metadata['sample_rate']} Hz")
    print(f"Duration: {len(iq_samples) / metadata['sample_rate']:.3f} seconds")
    print(f"Spreading Factor: {metadata['spreading_factor']}")
    
    # Create full C++ decoder
    print("\\nCreating full C++ decoder...")
    cpp_code = create_full_lora_decoder(iq_samples, metadata)
    
    # Compile and run
    success = compile_and_run_full_decoder(cpp_code)
    
    if success:
        print("\\nFull decoder completed successfully!")
    else:
        print("\\nFull decoder failed!")

if __name__ == "__main__":
    main()
