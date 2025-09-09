#!/usr/bin/env python3
"""
Search for text patterns in the decoded LoRa message
"""

def search_text_patterns():
    """Search for various text patterns in the decoded message"""
    
    # Read the decoded message
    with open('decoded_message.bin', 'rb') as f:
        data = f.read()
    
    print("=== Text Pattern Search in LoRa Message ===")
    print(f"Total size: {len(data)} bytes")
    print()
    
    # Convert to different text encodings
    print("=== Different Text Encodings ===")
    
    # UTF-8
    try:
        utf8_text = data.decode('utf-8', errors='ignore')
        print(f"UTF-8: {repr(utf8_text)}")
    except:
        print("UTF-8: Failed to decode")
    
    # ASCII
    try:
        ascii_text = data.decode('ascii', errors='ignore')
        print(f"ASCII: {repr(ascii_text)}")
    except:
        print("ASCII: Failed to decode")
    
    # Latin-1
    try:
        latin1_text = data.decode('latin-1', errors='ignore')
        print(f"Latin-1: {repr(latin1_text)}")
    except:
        print("Latin-1: Failed to decode")
    
    print()
    
    # Search for specific patterns
    print("=== Pattern Search ===")
    
    # Convert to lowercase for case-insensitive search
    text_lower = utf8_text.lower()
    
    # Common words to search for
    search_patterns = [
        'hello',
        'world',
        'hello world',
        'test',
        'lora',
        'data',
        'message',
        'packet',
        'sensor',
        'temperature',
        'humidity',
        'gps',
        'location',
        'status',
        'error',
        'ok',
        'success',
        'fail',
        'debug',
        'info',
        'warning',
        'device',
        'node',
        'gateway',
        'network',
        'signal',
        'power',
        'battery',
        'voltage',
        'current',
        'time',
        'date',
        'timestamp',
        'id',
        'name',
        'value',
        'reading',
        'measurement',
        'sensor_data',
        'telemetry'
    ]
    
    found_patterns = []
    for pattern in search_patterns:
        if pattern in text_lower:
            # Find all occurrences
            positions = []
            start = 0
            while True:
                pos = text_lower.find(pattern, start)
                if pos == -1:
                    break
                positions.append(pos)
                start = pos + 1
            
            found_patterns.append((pattern, positions))
            print(f"✓ Found '{pattern}' at positions: {positions}")
    
    if not found_patterns:
        print("✗ No common text patterns found")
    
    print()
    
    # Search for hex patterns that might be text
    print("=== Hex Pattern Analysis ===")
    
    # Look for printable ASCII in hex
    printable_hex = []
    for i in range(0, len(data), 2):
        if i + 1 < len(data):
            byte1 = data[i]
            byte2 = data[i + 1]
            
            # Check if this could be ASCII
            if 32 <= byte1 <= 126 and 32 <= byte2 <= 126:
                char1 = chr(byte1)
                char2 = chr(byte2)
                printable_hex.append((i, char1 + char2))
    
    if printable_hex:
        print("Potential ASCII pairs in hex:")
        for pos, chars in printable_hex[:20]:  # Show first 20
            print(f"  Position {pos}: '{chars}'")
    else:
        print("No obvious ASCII patterns found in hex")
    
    print()
    
    # Try different byte interpretations
    print("=== Byte Interpretation Analysis ===")
    
    # Try interpreting as different data types
    print("As 16-bit values:")
    for i in range(0, min(20, len(data) - 1), 2):
        val = int.from_bytes(data[i:i+2], 'little')
        if 32 <= val <= 126:  # Printable ASCII
            print(f"  Position {i}: {val} = '{chr(val)}'")
    
    print()
    print("As 32-bit values (little endian):")
    for i in range(0, min(20, len(data) - 3), 4):
        val = int.from_bytes(data[i:i+4], 'little')
        if 32 <= val <= 126:  # Printable ASCII
            print(f"  Position {i}: {val} = '{chr(val)}'")
    
    print()
    
    # Look for repeated patterns that might be text
    print("=== Repeated Pattern Analysis ===")
    
    # Find all 2-byte patterns
    patterns = {}
    for i in range(len(data) - 1):
        pattern = data[i:i+2]
        if pattern in patterns:
            patterns[pattern].append(i)
        else:
            patterns[pattern] = [i]
    
    # Show most common patterns
    common_patterns = sorted(patterns.items(), key=lambda x: len(x[1]), reverse=True)
    print("Most common 2-byte patterns:")
    for pattern, positions in common_patterns[:10]:
        if len(positions) > 1:
            hex_str = ' '.join(f'{b:02x}' for b in pattern)
            ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in pattern)
            print(f"  {hex_str} ('{ascii_str}') appears {len(positions)} times at {positions[:5]}{'...' if len(positions) > 5 else ''}")
    
    print()
    
    # Try to find any readable text by looking at different offsets
    print("=== Offset Analysis ===")
    
    for offset in range(8):
        print(f"Starting at offset {offset}:")
        offset_data = data[offset:]
        try:
            text = offset_data.decode('utf-8', errors='ignore')
            # Look for any readable words
            words = text.split()
            readable_words = [word for word in words if all(32 <= ord(c) <= 126 for c in word) and len(word) > 2]
            if readable_words:
                print(f"  Readable words: {readable_words[:10]}")
            else:
                print(f"  No readable words found")
        except:
            print(f"  Failed to decode at offset {offset}")

def main():
    search_text_patterns()

if __name__ == "__main__":
    main()
