#!/usr/bin/env python3
"""
Interpret the decoded LoRa data as different types of information
"""

import struct
import json
import numpy as np
import math

def load_decoded_data():
    """Load the decoded message"""
    with open('original_decoded_message.bin', 'rb') as f:
        data = f.read()
    return data

def interpret_as_sensor_data(data):
    """Try to interpret as sensor data (temperature, humidity, etc.)"""
    print("=== Sensor Data Interpretation ===")
    
    if len(data) < 4:
        print("Not enough data for sensor interpretation")
        return
    
    # Try different sensor data formats
    print("\\n1. Temperature/Humidity sensors:")
    
    # Try as 16-bit integers (little endian)
    if len(data) >= 4:
        temp_raw = struct.unpack('<H', data[0:2])[0]
        hum_raw = struct.unpack('<H', data[2:4])[0]
        
        # Common temperature sensor ranges
        temp_celsius = temp_raw / 100.0  # Common scaling
        temp_fahrenheit = temp_celsius * 9/5 + 32
        humidity = hum_raw / 100.0  # Common scaling
        
        print(f"  Temperature: {temp_celsius:.2f}°C ({temp_fahrenheit:.2f}°F)")
        print(f"  Humidity: {humidity:.2f}%")
        
        # Check if values are reasonable
        if 0 <= temp_celsius <= 100 and 0 <= humidity <= 100:
            print("  ✓ Values look reasonable for temperature/humidity")
        else:
            print("  ✗ Values seem unreasonable")
    
    # Try as 32-bit float
    if len(data) >= 8:
        try:
            temp_float = struct.unpack('<f', data[0:4])[0]
            hum_float = struct.unpack('<f', data[4:8])[0]
            
            print(f"\\n2. As 32-bit floats:")
            print(f"  Value 1: {temp_float:.6f}")
            print(f"  Value 2: {hum_float:.6f}")
            
            if not math.isnan(temp_float) and not math.isnan(hum_float):
                print("  ✓ Valid float values")
            else:
                print("  ✗ Invalid float values")
        except:
            print("  ✗ Failed to interpret as floats")
    
    # Try as signed integers
    if len(data) >= 4:
        temp_signed = struct.unpack('<h', data[0:2])[0]  # signed 16-bit
        hum_signed = struct.unpack('<h', data[2:4])[0]
        
        print(f"\\n3. As signed 16-bit integers:")
        print(f"  Value 1: {temp_signed}")
        print(f"  Value 2: {hum_signed}")

def interpret_as_gps_data(data):
    """Try to interpret as GPS coordinates"""
    print("\\n=== GPS Data Interpretation ===")
    
    if len(data) < 8:
        print("Not enough data for GPS interpretation")
        return
    
    # Try as 32-bit floats (latitude, longitude)
    try:
        lat = struct.unpack('<f', data[0:4])[0]
        lon = struct.unpack('<f', data[4:8])[0]
        
        print(f"Latitude: {lat:.6f}")
        print(f"Longitude: {lon:.6f}")
        
        # Check if values are reasonable GPS coordinates
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            print("✓ Valid GPS coordinates")
            
            # Convert to degrees, minutes, seconds
            lat_deg = int(abs(lat))
            lat_min = int((abs(lat) - lat_deg) * 60)
            lat_sec = ((abs(lat) - lat_deg) * 60 - lat_min) * 60
            
            lon_deg = int(abs(lon))
            lon_min = int((abs(lon) - lon_deg) * 60)
            lon_sec = ((abs(lon) - lon_deg) * 60 - lon_min) * 60
            
            print(f"  {lat_deg}°{lat_min}'{lat_sec:.2f}\" {'N' if lat >= 0 else 'S'}")
            print(f"  {lon_deg}°{lon_min}'{lon_sec:.2f}\" {'E' if lon >= 0 else 'W'}")
        else:
            print("✗ Invalid GPS coordinates")
    except:
        print("✗ Failed to interpret as GPS data")

def interpret_as_binary_protocol(data):
    """Try to interpret as binary protocol"""
    print("\\n=== Binary Protocol Interpretation ===")
    
    print("\\n1. As 8-bit values:")
    for i in range(min(16, len(data))):
        print(f"  Byte {i:2d}: 0x{data[i]:02x} ({data[i]:3d}) {'(' + chr(data[i]) + ')' if 32 <= data[i] <= 126 else ''}")
    
    print("\\n2. As 16-bit values (little endian):")
    for i in range(0, min(16, len(data) - 1), 2):
        val = struct.unpack('<H', data[i:i+2])[0]
        print(f"  Word {i//2:2d}: 0x{val:04x} ({val:5d})")
    
    print("\\n3. As 32-bit values (little endian):")
    for i in range(0, min(16, len(data) - 3), 4):
        val = struct.unpack('<I', data[i:i+4])[0]
        print(f"  DWord {i//4:2d}: 0x{val:08x} ({val:10d})")
    
    # Look for common protocol patterns
    print("\\n4. Protocol pattern analysis:")
    
    # Check for common headers
    if data.startswith(b'\\x20\\x58'):
        print("  ✓ Starts with 0x20 0x58 (potential header)")
    
    # Check for repeated patterns
    patterns = {}
    for i in range(len(data) - 1):
        pattern = data[i:i+2]
        if pattern in patterns:
            patterns[pattern] += 1
        else:
            patterns[pattern] = 1
    
    common_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)
    print("  Most common 2-byte patterns:")
    for pattern, count in common_patterns[:5]:
        if count > 1:
            hex_str = ' '.join(f'{b:02x}' for b in pattern)
            print(f"    {hex_str}: {count} times")

def interpret_as_measurement_data(data):
    """Try to interpret as measurement data"""
    print("\\n=== Measurement Data Interpretation ===")
    
    if len(data) < 8:
        print("Not enough data for measurement interpretation")
        return
    
    # Try different measurement interpretations
    print("\\n1. As voltage/current measurements:")
    
    # Try as 16-bit ADC values
    if len(data) >= 4:
        adc1 = struct.unpack('<H', data[0:2])[0]
        adc2 = struct.unpack('<H', data[2:4])[0]
        
        # Common ADC scaling (0-4095 for 12-bit, 0-1023 for 10-bit)
        voltage_12bit = (adc1 / 4095.0) * 3.3  # Assuming 3.3V reference
        voltage_10bit = (adc1 / 1023.0) * 3.3
        current_12bit = (adc2 / 4095.0) * 3.3
        current_10bit = (adc2 / 1023.0) * 3.3
        
        print(f"  ADC1: {adc1} (12-bit: {voltage_12bit:.3f}V, 10-bit: {voltage_10bit:.3f}V)")
        print(f"  ADC2: {adc2} (12-bit: {current_12bit:.3f}V, 10-bit: {current_10bit:.3f}V)")
    
    # Try as timestamp + measurement
    if len(data) >= 8:
        timestamp = struct.unpack('<I', data[0:4])[0]
        measurement = struct.unpack('<f', data[4:8])[0]
        
        print(f"\\n2. As timestamp + measurement:")
        print(f"  Timestamp: {timestamp} ({timestamp & 0xFFFFFFFF})")
        print(f"  Measurement: {measurement:.6f}")
        
        # Check if timestamp looks reasonable (Unix timestamp)
        if 1000000000 <= timestamp <= 2000000000:  # Rough range for Unix timestamp
            import datetime
            dt = datetime.datetime.fromtimestamp(timestamp)
            print(f"  Date: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            print("  ✓ Looks like Unix timestamp")

def interpret_as_network_packet(data):
    """Try to interpret as network packet"""
    print("\\n=== Network Packet Interpretation ===")
    
    if len(data) < 8:
        print("Not enough data for network packet interpretation")
        return
    
    # Try to find packet structure
    print("\\n1. Packet structure analysis:")
    
    # Check for common packet headers
    if data[0] == 0x20:
        print("  ✓ Starts with 0x20 (potential packet type)")
    
    if data[1] == 0x58:
        print("  ✓ Second byte is 0x58 (potential sequence number)")
    
    # Look for length field
    if len(data) >= 4:
        potential_length = struct.unpack('<H', data[2:4])[0]
        print(f"  Potential length field: {potential_length}")
        
        if potential_length <= len(data):
            print("  ✓ Length field seems reasonable")
        else:
            print("  ✗ Length field too large")
    
    # Check for checksum/CRC
    if len(data) >= 4:
        # Simple checksum calculation
        checksum = 0
        for byte in data[:-2]:
            checksum ^= byte
        
        expected_checksum = struct.unpack('<H', data[-2:])[0]
        print(f"\\n2. Checksum analysis:")
        print(f"  Calculated: 0x{checksum:04x}")
        print(f"  Expected: 0x{expected_checksum:04x}")
        
        if checksum == expected_checksum:
            print("  ✓ Checksum matches")
        else:
            print("  ✗ Checksum mismatch")

def interpret_as_custom_format(data):
    """Try to interpret as custom format"""
    print("\\n=== Custom Format Interpretation ===")
    
    print("\\n1. Bit-level analysis:")
    
    # Show first 32 bits
    bits = []
    for byte in data[:4]:
        for i in range(8):
            bits.append((byte >> (7-i)) & 1)
    
    print(f"  First 32 bits: {''.join(map(str, bits))}")
    
    # Try to find patterns
    print("\\n2. Pattern analysis:")
    
    # Look for alternating patterns
    alternating = True
    for i in range(1, min(16, len(data))):
        if (data[i] & 1) == (data[i-1] & 1):
            alternating = False
            break
    
    if alternating:
        print("  ✓ Alternating bit pattern detected")
    else:
        print("  ✗ No alternating pattern")
    
    # Look for incrementing patterns
    incrementing = True
    for i in range(1, min(8, len(data))):
        if data[i] != (data[i-1] + 1) & 0xFF:
            incrementing = False
            break
    
    if incrementing:
        print("  ✓ Incrementing byte pattern detected")
    else:
        print("  ✗ No incrementing pattern")

def main():
    print("LoRa Data Interpretation Tool")
    print("=" * 35)
    
    # Load decoded data
    data = load_decoded_data()
    print(f"Loaded {len(data)} bytes of decoded data")
    print(f"Hex: {data[:32].hex()}")
    print()
    
    # Try different interpretations
    interpret_as_sensor_data(data)
    interpret_as_gps_data(data)
    interpret_as_binary_protocol(data)
    interpret_as_measurement_data(data)
    interpret_as_network_packet(data)
    interpret_as_custom_format(data)
    
    print("\\n=== Summary ===")
    print("The data appears to be binary information that could be:")
    print("- Sensor measurements (temperature, humidity, etc.)")
    print("- GPS coordinates")
    print("- Network packet data")
    print("- Custom binary protocol")
    print("- Measurement data from IoT device")
    print()
    print("To determine the exact format, you would need to know:")
    print("- The source device type")
    print("- The protocol specification")
    print("- The data format documentation")

if __name__ == "__main__":
    main()
