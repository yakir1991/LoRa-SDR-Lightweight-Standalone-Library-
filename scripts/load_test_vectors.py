#!/usr/bin/env python3
"""
Unified vector loading system for LoRa lightweight implementation testing.
This script provides a common interface for loading all types of test vectors.
"""

import json
import base64
from pathlib import Path
from typing import Dict, List, Any, Optional

class VectorLoader:
    """Unified loader for all test vectors."""
    
    def __init__(self, project_root: Path = None):
        if project_root is None:
            project_root = Path(__file__).parent.parent
        self.project_root = project_root
        self.vectors_dir = project_root / "vectors"
    
    def load_hamming_vectors(self) -> List[Dict[str, Any]]:
        """Load Hamming code test vectors."""
        vectors = []
        
        # Load from comprehensive reference vectors
        ref_file = self.vectors_dir / "lora_sdr_reference" / "hamming_test_vectors.json"
        if ref_file.exists():
            with open(ref_file, 'r') as f:
                vectors.extend(json.load(f))
        
        # Load from extracted vectors
        ext_file = self.vectors_dir / "lora_sdr_extracted" / "hamming_tests.json"
        if ext_file.exists():
            with open(ext_file, 'r') as f:
                vectors.extend(json.load(f))
        
        return vectors
    
    def load_interleaver_vectors(self) -> List[Dict[str, Any]]:
        """Load interleaver test vectors."""
        vectors = []
        
        # Load from comprehensive reference vectors
        ref_file = self.vectors_dir / "lora_sdr_reference" / "interleaver_test_vectors.json"
        if ref_file.exists():
            with open(ref_file, 'r') as f:
                vectors.extend(json.load(f))
        
        # Load from extracted vectors
        ext_file = self.vectors_dir / "lora_sdr_extracted" / "interleaver_tests.json"
        if ext_file.exists():
            with open(ext_file, 'r') as f:
                vectors.extend(json.load(f))
        
        return vectors
    
    def load_modulation_vectors(self) -> List[Dict[str, Any]]:
        """Load modulation test vectors."""
        vectors = []
        
        # Load from comprehensive reference vectors
        ref_file = self.vectors_dir / "lora_sdr_reference" / "modulation_test_vectors.json"
        if ref_file.exists():
            with open(ref_file, 'r') as f:
                vectors.extend(json.load(f))
        
        # Load from extracted vectors
        ext_file = self.vectors_dir / "lora_sdr_extracted" / "encoder_decoder_tests.json"
        if ext_file.exists():
            with open(ext_file, 'r') as f:
                vectors.extend(json.load(f))
        
        return vectors
    
    def load_loopback_vectors(self) -> List[Dict[str, Any]]:
        """Load loopback test vectors."""
        vectors = []
        
        # Load from extracted vectors
        ext_file = self.vectors_dir / "lora_sdr_extracted" / "loopback_tests.json"
        if ext_file.exists():
            with open(ext_file, 'r') as f:
                vectors.extend(json.load(f))
        
        return vectors
    
    def load_detection_vectors(self) -> List[Dict[str, Any]]:
        """Load detection test vectors."""
        vectors = []
        
        # Load from comprehensive reference vectors
        ref_file = self.vectors_dir / "lora_sdr_reference" / "detection_test_vectors.json"
        if ref_file.exists():
            with open(ref_file, 'r') as f:
                vectors.extend(json.load(f))
        
        return vectors
    
    def load_validation_vectors(self) -> List[Dict[str, Any]]:
        """Load basic validation vectors."""
        vectors = []
        
        # Load from extracted vectors
        ext_file = self.vectors_dir / "lora_sdr_extracted" / "validation_tests.json"
        if ext_file.exists():
            with open(ext_file, 'r') as f:
                vectors.extend(json.load(f))
        
        return vectors
    
    def get_vectors_by_profile(self, sf: int, cr: str, bw: int) -> List[Dict[str, Any]]:
        """Get vectors matching specific LoRa profile."""
        all_vectors = self.load_modulation_vectors()
        matching = []
        
        for vector in all_vectors:
            if 'parameters' in vector:
                params = vector['parameters']
                if (params.get('spread_factor') == sf and 
                    params.get('coding_rate') == cr and 
                    params.get('bandwidth') == bw):
                    matching.append(vector)
        
        return matching
    
    def get_hamming_tests_by_type(self, test_type: str) -> List[Dict[str, Any]]:
        """Get Hamming tests by type (e.g., 'hamming84_no_error')."""
        all_vectors = self.load_hamming_vectors()
        matching = []
        
        for vector in all_vectors:
            if vector.get('test_type') == test_type:
                matching.append(vector)
        
        return matching
    
    def get_interleaver_tests_by_params(self, ppm: int, rdd: int) -> List[Dict[str, Any]]:
        """Get interleaver tests by PPM and RDD parameters."""
        all_vectors = self.load_interleaver_vectors()
        matching = []
        
        for vector in all_vectors:
            if (vector.get('ppm') == ppm and vector.get('rdd') == rdd):
                matching.append(vector)
        
        return matching
    
    def decode_payload(self, payload_b64: str) -> bytes:
        """Decode base64-encoded payload."""
        return base64.b64decode(payload_b64)
    
    def encode_payload(self, payload: bytes) -> str:
        """Encode payload to base64."""
        return base64.b64encode(payload).decode('ascii')
    
    def get_vector_summary(self) -> Dict[str, int]:
        """Get summary of available vectors."""
        summary = {
            'hamming': len(self.load_hamming_vectors()),
            'interleaver': len(self.load_interleaver_vectors()),
            'modulation': len(self.load_modulation_vectors()),
            'loopback': len(self.load_loopback_vectors()),
            'detection': len(self.load_detection_vectors()),
            'validation': len(self.load_validation_vectors())
        }
        summary['total'] = sum(summary.values())
        return summary

def main():
    """Test the vector loader."""
    loader = VectorLoader()
    
    print("LoRa Test Vector Loader")
    print("=" * 30)
    
    # Show summary
    summary = loader.get_vector_summary()
    print("Available vectors:")
    for category, count in summary.items():
        if category != 'total':
            print(f"  {category:12}: {count:4} vectors")
    print(f"  {'total':12}: {summary['total']:4} vectors")
    
    # Test specific loading
    print("\nTesting specific vector loading:")
    
    # Hamming vectors
    hamming_vectors = loader.load_hamming_vectors()
    print(f"Loaded {len(hamming_vectors)} Hamming vectors")
    
    # Modulation vectors for SF7
    sf7_vectors = loader.get_vectors_by_profile(7, "4/5", 125000)
    print(f"Found {len(sf7_vectors)} vectors for SF7, CR=4/5, BW=125kHz")
    
    # Hamming no-error tests
    no_error_tests = loader.get_hamming_tests_by_type("hamming84_no_error")
    print(f"Found {len(no_error_tests)} Hamming no-error tests")
    
    # Interleaver tests for PPM=7, RDD=0
    interleaver_tests = loader.get_interleaver_tests_by_params(7, 0)
    print(f"Found {len(interleaver_tests)} interleaver tests for PPM=7, RDD=0")

if __name__ == "__main__":
    main()
