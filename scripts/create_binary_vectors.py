#!/usr/bin/env python3
"""
Create binary test vectors for better performance
"""

import json
import base64
import struct
import os
from pathlib import Path

def create_binary_vectors():
    """Convert JSON vectors to binary format for better performance"""
    
    vectors_dir = Path("vectors")
    binary_dir = Path("vectors_binary")
    binary_dir.mkdir(exist_ok=True)
    
    # Process each JSON vector file
    for json_file in vectors_dir.rglob("*.json"):
        if "manifest" in json_file.name:
            continue
            
        print(f"Processing {json_file}")
        
        # Load JSON data
        with open(json_file, 'r') as f:
            vectors = json.load(f)
        
        # Create binary file
        binary_file = binary_dir / (json_file.stem + ".bin")
        
        with open(binary_file, 'wb') as f:
            # Write header: number of vectors
            f.write(struct.pack('<I', len(vectors)))
            
            for vector in vectors:
                # Write vector type
                test_type = vector.get('test_type', 'unknown').encode('utf-8')
                f.write(struct.pack('<I', len(test_type)))
                f.write(test_type)
                
                # Write payload if exists
                if 'payload' in vector:
                    payload = base64.b64decode(vector['payload'])
                    f.write(struct.pack('<I', len(payload)))
                    f.write(payload)
                else:
                    f.write(struct.pack('<I', 0))
                
                # Write parameters
                sf = vector.get('spread_factor', 0)
                cr = vector.get('coding_rate', '4/5')
                f.write(struct.pack('<I', sf))
                
                # Write coding rate as string
                if isinstance(cr, int):
                    cr = str(cr)
                cr_bytes = cr.encode('utf-8')
                f.write(struct.pack('<I', len(cr_bytes)))
                f.write(cr_bytes)
                
                # Write additional data if exists
                if 'input_codewords' in vector:
                    codewords = base64.b64decode(vector['input_codewords'])
                    f.write(struct.pack('<I', len(codewords)))
                    f.write(codewords)
                else:
                    f.write(struct.pack('<I', 0))
        
        print(f"  Created {binary_file} with {len(vectors)} vectors")

def load_binary_vectors(binary_file):
    """Load vectors from binary file"""
    vectors = []
    
    with open(binary_file, 'rb') as f:
        # Read number of vectors
        num_vectors = struct.unpack('<I', f.read(4))[0]
        
        for _ in range(num_vectors):
            vector = {}
            
            # Read test type
            type_len = struct.unpack('<I', f.read(4))[0]
            vector['test_type'] = f.read(type_len).decode('utf-8')
            
            # Read payload
            payload_len = struct.unpack('<I', f.read(4))[0]
            if payload_len > 0:
                payload = f.read(payload_len)
                vector['payload'] = base64.b64encode(payload).decode('utf-8')
            
            # Read parameters
            vector['spread_factor'] = struct.unpack('<I', f.read(4))[0]
            
            cr_len = struct.unpack('<I', f.read(4))[0]
            vector['coding_rate'] = f.read(cr_len).decode('utf-8')
            
            # Read additional data
            extra_len = struct.unpack('<I', f.read(4))[0]
            if extra_len > 0:
                extra_data = f.read(extra_len)
                vector['input_codewords'] = base64.b64encode(extra_data).decode('utf-8')
            
            vectors.append(vector)
    
    return vectors

def test_binary_vectors():
    """Test binary vector loading"""
    print("Testing binary vector loading...")
    
    binary_dir = Path("vectors_binary")
    if not binary_dir.exists():
        print("Binary vectors not found. Run create_binary_vectors() first.")
        return
    
    # Test loading a binary file
    for binary_file in binary_dir.glob("*.bin"):
        print(f"Loading {binary_file}")
        vectors = load_binary_vectors(binary_file)
        print(f"  Loaded {len(vectors)} vectors")
        
        # Show first vector
        if vectors:
            print(f"  First vector: {vectors[0]}")

if __name__ == "__main__":
    print("Creating binary test vectors...")
    create_binary_vectors()
    
    print("\nTesting binary vector loading...")
    test_binary_vectors()
    
    print("\nBinary vector creation completed!")
