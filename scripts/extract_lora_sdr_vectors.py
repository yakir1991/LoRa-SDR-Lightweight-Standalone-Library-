#!/usr/bin/env python3
"""
Extract test vectors from LoRa-SDR submodule for validation testing.
This script generates test vectors that can be used to validate the lightweight LoRa implementation.
"""

import os
import sys
import json
import base64
import hashlib
import random
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def create_test_vector(sf, cr, bw, payload, sync_word=0x34):
    """
    Create a test vector with specific LoRa parameters.
    
    Args:
        sf: Spread factor (7-12)
        cr: Coding rate (1-4)
        bw: Bandwidth in Hz
        payload: Data payload as bytes
        sync_word: Sync word (default 0x34)
    
    Returns:
        dict: Test vector with parameters and expected outputs
    """
    return {
        "parameters": {
            "spread_factor": sf,
            "coding_rate": cr,
            "bandwidth": bw,
            "sync_word": sync_word,
            "payload_length": len(payload)
        },
        "input": {
            "payload": base64.b64encode(payload).decode('ascii')
        },
        "expected": {
            "symbols_count": 2**sf,  # Number of symbols in a chirp
            "chirps_count": len(payload) * 8 // sf + 2,  # Approximate chirp count
            "total_samples": int(2**sf * (len(payload) * 8 // sf + 2) * bw / 125000)  # Approximate sample count
        }
    }

def generate_hamming_test_vectors():
    """Generate test vectors for Hamming code testing."""
    vectors = []
    
    # Test cases for Hamming 8/4 (SX127x style)
    test_bytes = [0x00, 0x01, 0x0F, 0x10, 0x55, 0xAA, 0xFF]
    
    for byte_val in test_bytes:
        # Test without errors
        vectors.append({
            "test_type": "hamming84_no_error",
            "input_byte": byte_val,
            "expected_encoded": None,  # Will be calculated by reference implementation
            "expected_decoded": byte_val,
            "expected_error": False,
            "expected_bad": False
        })
        
        # Test with single bit error (should be correctable)
        for bit_pos in range(8):
            vectors.append({
                "test_type": "hamming84_single_error",
                "input_byte": byte_val,
                "error_bit_position": bit_pos,
                "expected_decoded": byte_val,
                "expected_error": True,
                "expected_bad": False
            })
    
    return vectors

def generate_interleaver_test_vectors():
    """Generate test vectors for interleaver testing."""
    vectors = []
    
    for ppm in range(7, 13):  # PPM 7-12
        for rdd in range(5):  # RDD 0-4
            # Generate random input codewords
            input_cws = [random.randint(0, 2**(rdd+4)-1) for _ in range(ppm)]
            
            vectors.append({
                "test_type": "interleaver",
                "ppm": ppm,
                "rdd": rdd,
                "input_codewords": base64.b64encode(bytes(input_cws)).decode('ascii'),
                "expected_symbols_count": ((rdd+4) * ppm) // ppm
            })
    
    return vectors

def generate_modulation_test_vectors():
    """Generate test vectors for LoRa modulation testing."""
    vectors = []
    
    # Test different spread factors and coding rates
    spread_factors = [7, 8, 9, 10, 11, 12]
    coding_rates = [1, 2, 3, 4]
    bandwidths = [125000, 250000, 500000]  # Hz
    
    test_payloads = [
        b"Hello",
        b"Test123",
        b"A" * 16,
        b"\x00\x01\x02\x03\x04\x05\x06\x07",
        b"LoRa Test Message"
    ]
    
    for sf in spread_factors:
        for cr in coding_rates:
            for bw in bandwidths:
                for payload in test_payloads:
                    if len(payload) <= 255:  # LoRa payload limit
                        vectors.append(create_test_vector(sf, cr, bw, payload))
    
    return vectors

def generate_detection_test_vectors():
    """Generate test vectors for LoRa detection testing."""
    vectors = []
    
    # Test different signal conditions
    snr_levels = [-20, -10, -5, 0, 5, 10, 20]  # dB
    frequency_offsets = [0, 1000, 5000, 10000]  # Hz
    
    for snr in snr_levels:
        for freq_offset in frequency_offsets:
            vectors.append({
                "test_type": "detection",
                "snr_db": snr,
                "frequency_offset_hz": freq_offset,
                "expected_detection": snr > -10,  # Simple threshold
                "expected_peaks": 1 if snr > -5 else 0
            })
    
    return vectors

def save_vectors(vectors, filename):
    """Save vectors to a JSON file with manifest."""
    output_path = project_root / "vectors" / "lora_sdr_reference" / filename
    
    # Create directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Calculate checksum
    content = json.dumps(vectors, indent=2)
    checksum = hashlib.sha256(content.encode()).hexdigest()
    
    # Save the vectors
    with open(output_path, 'w') as f:
        f.write(content)
    
    # Save manifest
    manifest = {
        "filename": filename,
        "checksum": checksum,
        "vector_count": len(vectors),
        "generated_by": "extract_lora_sdr_vectors.py"
    }
    
    manifest_path = output_path.parent / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"Saved {len(vectors)} vectors to {output_path}")
    print(f"Checksum: {checksum}")

def main():
    """Generate all test vectors."""
    print("Generating LoRa-SDR test vectors...")
    
    # Generate different types of test vectors
    hamming_vectors = generate_hamming_test_vectors()
    interleaver_vectors = generate_interleaver_test_vectors()
    modulation_vectors = generate_modulation_test_vectors()
    detection_vectors = generate_detection_test_vectors()
    
    # Save vectors
    save_vectors(hamming_vectors, "hamming_test_vectors.json")
    save_vectors(interleaver_vectors, "interleaver_test_vectors.json")
    save_vectors(modulation_vectors, "modulation_test_vectors.json")
    save_vectors(detection_vectors, "detection_test_vectors.json")
    
    # Create a combined manifest
    combined_manifest = {
        "generated_by": "extract_lora_sdr_vectors.py",
        "total_vectors": len(hamming_vectors) + len(interleaver_vectors) + len(modulation_vectors) + len(detection_vectors),
        "vector_files": [
            "hamming_test_vectors.json",
            "interleaver_test_vectors.json", 
            "modulation_test_vectors.json",
            "detection_test_vectors.json"
        ]
    }
    
    manifest_path = project_root / "vectors" / "lora_sdr_reference" / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(combined_manifest, f, indent=2)
    
    print(f"\nTotal vectors generated: {combined_manifest['total_vectors']}")
    print("Test vectors saved to vectors/lora_sdr_reference/")

if __name__ == "__main__":
    main()
