#!/usr/bin/env python3
"""
Script to analyze and convert the unknown LoRa file to a format suitable for testing
"""

import struct
import numpy as np
import json
import os

def analyze_unknown_file(filename):
    """Analyze the unknown file and convert it to a usable format"""
    
    print(f"Analyzing file: {filename}")
    
    # Read the file
    with open(filename, 'rb') as f:
        data = f.read()
    
    print(f"File size: {len(data)} bytes")
    
    # Check if it's float32 data
    if len(data) % 4 != 0:
        print("Warning: File size is not divisible by 4, might not be float32")
        return
    
    # Convert to float32 array
    num_floats = len(data) // 4
    floats = struct.unpack(f'{num_floats}f', data)
    
    print(f"Number of float32 values: {num_floats}")
    
    # Check if it's IQ data (even number of floats)
    if num_floats % 2 != 0:
        print("Warning: Odd number of floats, might not be IQ data")
        return
    
    # Reshape to IQ samples
    iq_samples = np.array(floats).reshape(-1, 2)
    print(f"Number of IQ samples: {len(iq_samples)}")
    
    # Convert to complex
    iq_complex = iq_samples[:, 0] + 1j * iq_samples[:, 1]
    
    print(f"IQ samples shape: {iq_complex.shape}")
    print(f"First few IQ samples: {iq_complex[:10]}")
    
    # Calculate some basic statistics
    power = np.abs(iq_complex) ** 2
    print(f"Average power: {np.mean(power):.6f}")
    print(f"Max power: {np.max(power):.6f}")
    print(f"Min power: {np.min(power):.6f}")
    
    # Save as numpy array for easy loading
    output_file = filename.replace('.unknown', '_iq_samples.npy')
    np.save(output_file, iq_complex)
    print(f"Saved IQ samples to: {output_file}")
    
    # Save metadata
    metadata = {
        "filename": os.path.basename(filename),
        "file_size_bytes": len(data),
        "num_float32_values": num_floats,
        "num_iq_samples": len(iq_complex),
        "sample_rate": 250000,  # 250K SPS with oversampling of 2
        "bandwidth": 250000,    # 250K BW
        "spreading_factor": 7,
        "coding_rate": 1,
        "ldro": False,
        "crc": True,
        "impl_header": False,
        "oversampling": 2,
        "data_type": "complex64"
    }
    
    metadata_file = filename.replace('.unknown', '_metadata.json')
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved metadata to: {metadata_file}")
    
    return iq_complex, metadata

def create_test_script(iq_samples, metadata):
    """Create a test script to validate the IQ samples with LoRa-SDR"""
    
    test_script = f'''#!/usr/bin/env python3
"""
Test script for LoRa IQ samples validation
"""

import numpy as np
import json
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def load_iq_samples():
    """Load the IQ samples"""
    iq_samples = np.load('{metadata["filename"].replace(".unknown", "_iq_samples.npy")}')
    return iq_samples

def test_with_lightweight_lora(iq_samples):
    """Test with our lightweight LoRa implementation"""
    try:
        from lora_demodulation_advanced import lora_demodulate_advanced
        
        print("Testing with lightweight LoRa demodulator...")
        sf = {metadata["spreading_factor"]}
        
        # Try to demodulate
        result = lora_demodulate_advanced(iq_samples, sf)
        print(f"Demodulation result: {{result}}")
        
        return True
    except Exception as e:
        print(f"Error in lightweight demodulation: {{e}}")
        return False

def test_with_original_lora_sdr(iq_samples):
    """Test with original LoRa-SDR (if available)"""
    print("Testing with original LoRa-SDR...")
    print("Note: This requires the LoRa-SDR submodule to be compiled")
    
    # For now, just print the parameters
    print(f"Parameters:")
    print(f"  Spreading Factor: {metadata["spreading_factor"]}")
    print(f"  Bandwidth: {metadata["bandwidth"]} Hz")
    print(f"  Sample Rate: {metadata["sample_rate"]} Hz")
    print(f"  Number of samples: {len(iq_samples)}")
    
    return True

if __name__ == "__main__":
    print("Loading IQ samples...")
    iq_samples = load_iq_samples()
    
    print(f"Loaded {{len(iq_samples)}} IQ samples")
    print(f"Sample rate: {metadata["sample_rate"]} Hz")
    print(f"Duration: {len(iq_samples) / metadata['sample_rate']:.3f} seconds")
    
    # Test with lightweight implementation
    test_with_lightweight_lora(iq_samples)
    
    # Test with original LoRa-SDR
    test_with_original_lora_sdr(iq_samples)
'''
    
    test_file = metadata["filename"].replace('.unknown', '_test.py')
    with open(test_file, 'w') as f:
        f.write(test_script)
    print(f"Created test script: {test_file}")

if __name__ == "__main__":
    filename = "vectors_binary/bw_125k_sf_7_cr_1_ldro_false_crc_true_implheader_false.unknown"
    
    if not os.path.exists(filename):
        print(f"File not found: {filename}")
        sys.exit(1)
    
    iq_samples, metadata = analyze_unknown_file(filename)
    create_test_script(iq_samples, metadata)
    
    print("\\nAnalysis complete!")
    print(f"Use the generated test script to validate the IQ samples")
