#!/usr/bin/env python3
"""
Analyze the decoded LoRa message in detail
"""

import struct
import json

def analyze_message():
    """Analyze the decoded message in detail"""
    
    # Read the decoded message
    with open('decoded_message.bin', 'rb') as f:
        data = f.read()
    
    print("=== Decoded LoRa Message Analysis ===")
    print(f"Total size: {len(data)} bytes")
    print()
    
    # Show hex dump
    print("Hex dump:")
    for i in range(0, len(data), 16):
        hex_part = ' '.join(f'{b:02x}' for b in data[i:i+16])
        ascii_part = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data[i:i+16])
        print(f"{i:08x}: {hex_part:<48} |{ascii_part}|")
    
    print()
    
    # Analyze different sections
    print("=== Section Analysis ===")
    
    # Section 1: First 20 bytes (likely header/payload)
    section1 = data[:20]
    print(f"Section 1 (bytes 0-19): {len(section1)} bytes")
    print(f"Hex: {' '.join(f'{b:02x}' for b in section1)}")
    print(f"ASCII: {''.join(chr(b) if 32 <= b <= 126 else '.' for b in section1)}")
    
    # Try to interpret as different data types
    print("\nTrying different interpretations:")
    
    # As 32-bit integers (little endian)
    if len(section1) >= 4:
        try:
            val1 = struct.unpack('<I', section1[:4])[0]
            val2 = struct.unpack('<I', section1[4:8])[0]
            val3 = struct.unpack('<I', section1[8:12])[0]
            val4 = struct.unpack('<I', section1[12:16])[0]
            val5 = struct.unpack('<I', section1[16:20])[0]
            print(f"  As 32-bit LE integers: {val1}, {val2}, {val3}, {val4}, {val5}")
        except:
            pass
    
    # As 32-bit integers (big endian)
    if len(section1) >= 4:
        try:
            val1 = struct.unpack('>I', section1[:4])[0]
            val2 = struct.unpack('>I', section1[4:8])[0]
            val3 = struct.unpack('>I', section1[8:12])[0]
            val4 = struct.unpack('>I', section1[12:16])[0]
            val5 = struct.unpack('>I', section1[16:20])[0]
            print(f"  As 32-bit BE integers: {val1}, {val2}, {val3}, {val4}, {val5}")
        except:
            pass
    
    # As 16-bit integers
    if len(section1) >= 2:
        try:
            vals = struct.unpack('<H' * (len(section1) // 2), section1[:len(section1)//2*2])
            print(f"  As 16-bit LE integers: {vals}")
        except:
            pass
    
    # As float32
    if len(section1) >= 4:
        try:
            val1 = struct.unpack('<f', section1[:4])[0]
            val2 = struct.unpack('<f', section1[4:8])[0]
            val3 = struct.unpack('<f', section1[8:12])[0]
            val4 = struct.unpack('<f', section1[12:16])[0]
            val5 = struct.unpack('<f', section1[16:20])[0]
            print(f"  As float32 LE: {val1:.6f}, {val2:.6f}, {val3:.6f}, {val4:.6f}, {val5:.6f}")
        except:
            pass
    
    print()
    
    # Section 2: Padding (zeros)
    section2 = data[20:48]
    print(f"Section 2 (bytes 20-47): {len(section2)} bytes")
    print(f"All zeros: {all(b == 0 for b in section2)}")
    print(f"Hex: {' '.join(f'{b:02x}' for b in section2)}")
    
    print()
    
    # Section 3: Last 40 bytes
    section3 = data[48:]
    print(f"Section 3 (bytes 48-87): {len(section3)} bytes")
    print(f"Hex: {' '.join(f'{b:02x}' for b in section3)}")
    print(f"ASCII: {''.join(chr(b) if 32 <= b <= 126 else '.' for b in section3)}")
    
    # Try to interpret section 3 as different data types
    print("\nSection 3 interpretations:")
    
    # As 32-bit integers
    if len(section3) >= 4:
        try:
            vals = struct.unpack('<I' * (len(section3) // 4), section3[:len(section3)//4*4])
            print(f"  As 32-bit LE integers: {vals}")
        except:
            pass
    
    # As float32
    if len(section3) >= 4:
        try:
            vals = struct.unpack('<f' * (len(section3) // 4), section3[:len(section3)//4*4])
            print(f"  As float32 LE: {[f'{v:.6f}' for v in vals]}")
        except:
            pass
    
    print()
    
    # Look for patterns
    print("=== Pattern Analysis ===")
    
    # Check for repeated patterns
    print("Looking for repeated patterns...")
    
    # Check for common LoRa patterns
    if data.startswith(b'\x40'):
        print("✓ Starts with LoRa preamble (0x40)")
    
    # Check for common text patterns
    text_data = data.decode('utf-8', errors='ignore')
    common_words = ['hello', 'test', 'lora', 'data', 'message', 'packet']
    for word in common_words:
        if word.lower() in text_data.lower():
            print(f"✓ Found '{word}' in message")
    
    # Check for JSON
    try:
        json_data = json.loads(text_data)
        print("✓ Valid JSON found!")
        print(json.dumps(json_data, indent=2))
    except:
        print("✗ Not valid JSON")
    
    # Check for binary patterns
    print("\nBinary pattern analysis:")
    
    # Count bit patterns
    bit_counts = [0] * 8
    for byte in data:
        for i in range(8):
            if byte & (1 << i):
                bit_counts[i] += 1
    
    print(f"Bit distribution: {bit_counts}")
    
    # Check for entropy
    byte_counts = [0] * 256
    for byte in data:
        byte_counts[byte] += 1
    
    import math
    entropy = 0
    for count in byte_counts:
        if count > 0:
            p = count / len(data)
            entropy -= p * math.log2(p)
    
    print(f"Estimated entropy: {entropy:.2f} bits per byte")
    
    # Look for specific LoRa patterns
    print("\nLoRa-specific analysis:")
    
    # Check for sync word patterns
    sync_words = [0x34, 0x44, 0x54, 0x64, 0x74, 0x84, 0x94, 0xa4, 0xb4, 0xc4, 0xd4, 0xe4, 0xf4]
    for sync in sync_words:
        if sync in data:
            print(f"✓ Found potential sync word: 0x{sync:02x}")
    
    # Check for CRC patterns
    if len(data) >= 2:
        # Simple CRC check
        crc = 0
        for byte in data[:-2]:
            crc ^= byte
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0x8408
                else:
                    crc >>= 1
        
        expected_crc = struct.unpack('<H', data[-2:])[0]
        if crc == expected_crc:
            print(f"✓ Valid CRC found: 0x{expected_crc:04x}")
        else:
            print(f"✗ CRC mismatch: calculated=0x{crc:04x}, expected=0x{expected_crc:04x}")

def main():
    analyze_message()

if __name__ == "__main__":
    main()
