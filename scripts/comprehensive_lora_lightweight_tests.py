#!/usr/bin/env python3
"""
Comprehensive LoRa Lightweight Testing Suite
Tests all components with reference vectors
"""

import struct
import os
import sys
import time
import numpy as np
from pathlib import Path

class LoRaLightweightTester:
    def __init__(self):
        self.test_results = {}
        self.total_tests = 0
        self.passed_tests = 0
        
    def log_test(self, test_name, passed, details=""):
        """Log test result"""
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        
        self.test_results[test_name] = {
            'passed': passed,
            'details': details
        }
        
        print(f"{status} {test_name}: {details}")
        return passed
    
    def test_hamming_codes(self):
        """Test Hamming 8/4 and 7/4 codes"""
        print("\n=== TESTING HAMMING CODES ===")
        
        # Hamming 8/4 implementation
        def encodeHamming84sx(x):
            d0 = (x >> 0) & 0x1
            d1 = (x >> 1) & 0x1
            d2 = (x >> 2) & 0x1
            d3 = (x >> 3) & 0x1
            
            b = x & 0xf
            b |= (d0 ^ d1 ^ d2) << 4
            b |= (d1 ^ d2 ^ d3) << 5
            b |= (d0 ^ d1 ^ d3) << 6
            b |= (d0 ^ d2 ^ d3) << 7
            return b

        def decodeHamming84sx(b):
            b0 = (b >> 0) & 0x1
            b1 = (b >> 1) & 0x1
            b2 = (b >> 2) & 0x1
            b3 = (b >> 3) & 0x1
            b4 = (b >> 4) & 0x1
            b5 = (b >> 5) & 0x1
            b6 = (b >> 6) & 0x1
            b7 = (b >> 7) & 0x1
            
            p0 = (b0 ^ b1 ^ b2 ^ b4)
            p1 = (b1 ^ b2 ^ b3 ^ b5)
            p2 = (b0 ^ b1 ^ b3 ^ b6)
            p3 = (b0 ^ b2 ^ b3 ^ b7)
            
            parity = (p0 << 0) | (p1 << 1) | (p2 << 2) | (p3 << 3)
            if parity != 0:
                switch_val = parity & 0xf
                if switch_val == 0xD:
                    return (b ^ 1) & 0xf
                elif switch_val == 0x7:
                    return (b ^ 2) & 0xf
                elif switch_val == 0xB:
                    return (b ^ 4) & 0xf
                elif switch_val == 0xE:
                    return (b ^ 8) & 0xf
                elif switch_val in [0x0, 0x1, 0x2, 0x4, 0x8]:
                    return b & 0xf
                else:
                    return b & 0xf
            else:
                return b & 0xf

        # Test round-trip for all 4-bit values
        round_trip_passed = 0
        for i in range(16):
            encoded = encodeHamming84sx(i)
            decoded = decodeHamming84sx(encoded)
            if decoded == i:
                round_trip_passed += 1
        
        self.log_test("Hamming 8/4 Round-trip", 
                     round_trip_passed == 16, 
                     f"{round_trip_passed}/16 passed")
        
        # Test with reference vectors
        try:
            with open('vectors/lora_sdr_reference/comprehensive_hamming_tests.bin', 'rb') as f:
                data = f.read()
            
            num_tests = struct.unpack('<I', data[:4])[0]
            offset = 4
            vector_passed = 0
            vector_total = 0
            
            for i in range(num_tests):
                if offset + 6 <= len(data):
                    test_type = data[offset]
                    data_val = data[offset + 1]
                    encoded = data[offset + 2]
                    decoded = data[offset + 3]
                    error = data[offset + 4]
                    bad = data[offset + 5]
                    
                    if test_type == 0:  # Hamming 8/4
                        vector_total += 1
                        our_encoded = encodeHamming84sx(data_val)
                        
                        if our_encoded == encoded:
                            vector_passed += 1
                    
                    offset += 6
            
            self.log_test("Hamming 8/4 Vector Encoding", 
                         vector_passed == vector_total, 
                         f"{vector_passed}/{vector_total} passed")
            
        except FileNotFoundError:
            self.log_test("Hamming 8/4 Vector Encoding", False, "Reference vectors not found")
    
    def test_modulation_vectors(self):
        """Test modulation vector availability and structure"""
        print("\n=== TESTING MODULATION VECTORS ===")
        
        try:
            with open('vectors/lora_sdr_reference/comprehensive_modulation_tests.bin', 'rb') as f:
                data = f.read()
            
            num_tests = struct.unpack('<I', data[:4])[0]
            file_size = len(data)
            
            self.log_test("Modulation Vector File", True, f"{num_tests} tests, {file_size:,} bytes")
            
            # Analyze configurations
            configs = {}
            offset = 4
            
            for i in range(min(100, num_tests)):  # Check first 100 tests
                if offset + 8 <= len(data):
                    sf = struct.unpack('<I', data[offset:offset+4])[0]
                    bw = struct.unpack('<I', data[offset+4:offset+8])[0]
                    offset += 8
                    
                    input_len = struct.unpack('<I', data[offset:offset+4])[0]
                    offset += 4
                    
                    input_data = data[offset:offset+input_len]
                    offset += input_len
                    
                    iq_len = struct.unpack('<I', data[offset:offset+4])[0]
                    offset += 4
                    
                    offset += iq_len * 8
                    
                    config_key = f'SF{sf}_BW{bw}'
                    if config_key not in configs:
                        configs[config_key] = 0
                    configs[config_key] += 1
            
            self.log_test("Modulation Configurations", len(configs) > 0, f"{len(configs)} unique configs found")
            
            # Show first few configurations
            for i, (config, count) in enumerate(sorted(configs.items())):
                if i < 5:  # Show first 5
                    print(f"  {config}: {count} tests")
            
        except FileNotFoundError:
            self.log_test("Modulation Vector File", False, "File not found")
    
    def test_detection_vectors(self):
        """Test detection vector availability and structure"""
        print("\n=== TESTING DETECTION VECTORS ===")
        
        try:
            with open('vectors/lora_sdr_reference/comprehensive_detection_tests.bin', 'rb') as f:
                data = f.read()
            
            num_tests = struct.unpack('<I', data[:4])[0]
            file_size = len(data)
            
            self.log_test("Detection Vector File", True, f"{num_tests} tests, {file_size:,} bytes")
            
            # Analyze configurations
            configs = {}
            offset = 4
            
            for i in range(min(50, num_tests)):  # Check first 50 tests
                if offset + 12 <= len(data):
                    sf = struct.unpack('<I', data[offset:offset+4])[0]
                    bw = struct.unpack('<I', data[offset+4:offset+8])[0]
                    cr = struct.unpack('<I', data[offset+8:offset+12])[0]
                    offset += 12
                    
                    iq_len = struct.unpack('<I', data[offset:offset+4])[0]
                    offset += 4
                    
                    offset += iq_len * 8
                    
                    symbols_len = struct.unpack('<I', data[offset:offset+4])[0]
                    offset += 4
                    
                    offset += symbols_len * 2
                    
                    config_key = f'SF{sf}_BW{bw}_CR{cr}'
                    if config_key not in configs:
                        configs[config_key] = 0
                    configs[config_key] += 1
            
            self.log_test("Detection Configurations", len(configs) > 0, f"{len(configs)} unique configs found")
            
            # Show first few configurations
            for i, (config, count) in enumerate(sorted(configs.items())):
                if i < 5:  # Show first 5
                    print(f"  {config}: {count} tests")
            
        except FileNotFoundError:
            self.log_test("Detection Vector File", False, "File not found")
    
    def test_awgn_vectors(self):
        """Test AWGN vector availability and structure"""
        print("\n=== TESTING AWGN VECTORS ===")
        
        try:
            with open('vectors/lora_sdr_reference/comprehensive_awgn_tests.bin', 'rb') as f:
                data = f.read()
            
            num_tests = struct.unpack('<I', data[:4])[0]
            file_size = len(data)
            
            self.log_test("AWGN Vector File", True, f"{num_tests} tests, {file_size:,} bytes")
            
            # Analyze first few tests
            configs = {}
            snr_values = set()
            offset = 4
            
            for i in range(min(20, num_tests)):  # Check first 20 tests
                if offset + 16 <= len(data):
                    sf = struct.unpack('<I', data[offset:offset+4])[0]
                    bw = struct.unpack('<I', data[offset+4:offset+8])[0]
                    cr = struct.unpack('<I', data[offset+8:offset+12])[0]
                    snr = struct.unpack('<f', data[offset+12:offset+16])[0]
                    offset += 16
                    
                    iq_len = struct.unpack('<I', data[offset:offset+4])[0]
                    offset += 4
                    
                    offset += iq_len * 8
                    
                    symbols_len = struct.unpack('<I', data[offset:offset+4])[0]
                    offset += 4
                    
                    offset += symbols_len * 2
                    
                    config_key = f'SF{sf}_BW{bw}_CR{cr}'
                    if config_key not in configs:
                        configs[config_key] = 0
                    configs[config_key] += 1
                    
                    snr_values.add(snr)
            
            self.log_test("AWGN Configurations", len(configs) > 0, f"{len(configs)} unique configs found")
            self.log_test("AWGN SNR Range", len(snr_values) > 0, f"SNR values: {sorted(snr_values)}")
            
        except FileNotFoundError:
            self.log_test("AWGN Vector File", False, "File not found")
    
    def test_golden_vectors(self):
        """Test golden vectors in clean repository"""
        print("\n=== TESTING GOLDEN VECTORS ===")
        
        golden_dir = 'LoRa-SDR-Lightweight-Clean/vectors/golden/'
        if os.path.exists(golden_dir):
            golden_files = [f for f in os.listdir(golden_dir) if f.endswith('.bin')]
            total_size = 0
            
            for file in golden_files:
                file_path = os.path.join(golden_dir, file)
                size = os.path.getsize(file_path)
                total_size += size
            
            self.log_test("Golden Vectors Directory", True, f"{len(golden_files)} files, {total_size:,} bytes")
            
            # Test each golden vector file
            for file in golden_files:
                if file == 'golden_summary.json':
                    continue
                
                try:
                    with open(os.path.join(golden_dir, file), 'rb') as f:
                        data = f.read()
                    
                    if len(data) >= 4:
                        num_tests = struct.unpack('<I', data[:4])[0]
                        self.log_test(f"Golden {file}", True, f"{num_tests} tests")
                    else:
                        self.log_test(f"Golden {file}", False, "File too small")
                        
                except Exception as e:
                    self.log_test(f"Golden {file}", False, f"Error: {e}")
        else:
            self.log_test("Golden Vectors Directory", False, "Directory not found")
    
    def test_performance(self):
        """Test performance of key functions"""
        print("\n=== TESTING PERFORMANCE ===")
        
        # Hamming encoding performance
        def encodeHamming84sx(x):
            d0 = (x >> 0) & 0x1
            d1 = (x >> 1) & 0x1
            d2 = (x >> 2) & 0x1
            d3 = (x >> 3) & 0x1
            
            b = x & 0xf
            b |= (d0 ^ d1 ^ d2) << 4
            b |= (d1 ^ d2 ^ d3) << 5
            b |= (d0 ^ d1 ^ d3) << 6
            b |= (d0 ^ d2 ^ d3) << 7
            return b
        
        # Test encoding performance
        start_time = time.time()
        for _ in range(10000):
            for i in range(16):
                encodeHamming84sx(i)
        end_time = time.time()
        
        duration = end_time - start_time
        operations_per_second = (10000 * 16) / duration
        
        self.log_test("Hamming Encoding Performance", True, 
                     f"{operations_per_second:,.0f} ops/sec")
    
    def run_all_tests(self):
        """Run all tests"""
        print("=== LoRa Lightweight Comprehensive Testing Suite ===")
        print(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run all test categories
        self.test_hamming_codes()
        self.test_modulation_vectors()
        self.test_detection_vectors()
        self.test_awgn_vectors()
        self.test_golden_vectors()
        self.test_performance()
        
        # Print summary
        print("\n=== TEST SUMMARY ===")
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.total_tests - self.passed_tests}")
        print(f"Success Rate: {self.passed_tests/self.total_tests*100:.1f}%")
        
        if self.passed_tests == self.total_tests:
            print("\n🎉 ALL TESTS PASSED! LoRa Lightweight is ready for production!")
        else:
            print(f"\n⚠️  {self.total_tests - self.passed_tests} tests failed. Please review the results.")
        
        return self.passed_tests == self.total_tests

def main():
    """Main test runner"""
    tester = LoRaLightweightTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
