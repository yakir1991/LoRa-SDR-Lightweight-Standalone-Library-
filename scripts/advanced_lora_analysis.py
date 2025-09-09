#!/usr/bin/env python3
"""
Advanced LoRa analysis script for the unknown file
"""

import numpy as np
import matplotlib.pyplot as plt
import json
import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def load_iq_data():
    """Load the IQ samples and metadata"""
    iq_samples = np.load('vectors_binary/bw_125k_sf_7_cr_1_ldro_false_crc_true_implheader_false_iq_samples.npy')
    
    with open('vectors_binary/bw_125k_sf_7_cr_1_ldro_false_crc_true_implheader_false_metadata.json', 'r') as f:
        metadata = json.load(f)
    
    return iq_samples, metadata

def analyze_signal_characteristics(iq_samples, sample_rate):
    """Analyze basic signal characteristics"""
    print("=== Signal Analysis ===")
    
    # Power analysis
    power = np.abs(iq_samples) ** 2
    print(f"Average power: {np.mean(power):.6f}")
    print(f"Max power: {np.max(power):.6f}")
    print(f"Min power: {np.min(power):.6f}")
    print(f"Power std: {np.std(power):.6f}")
    
    # Frequency analysis
    fft = np.fft.fft(iq_samples)
    freqs = np.fft.fftfreq(len(iq_samples), 1/sample_rate)
    
    # Find peak frequency
    power_spectrum = np.abs(fft) ** 2
    peak_idx = np.argmax(power_spectrum)
    peak_freq = freqs[peak_idx]
    
    print(f"Peak frequency: {peak_freq:.2f} Hz")
    print(f"Peak power: {power_spectrum[peak_idx]:.2f}")
    
    # Look for chirp patterns
    print(f"\\n=== Chirp Pattern Analysis ===")
    
    # For SF=7, each symbol should be 128 samples
    symbol_length = 128
    num_symbols = len(iq_samples) // symbol_length
    
    print(f"Expected symbol length: {symbol_length} samples")
    print(f"Number of complete symbols: {num_symbols}")
    
    # Analyze first few symbols
    for i in range(min(5, num_symbols)):
        start_idx = i * symbol_length
        end_idx = start_idx + symbol_length
        symbol = iq_samples[start_idx:end_idx]
        
        # Check if it looks like a chirp
        phase = np.angle(symbol)
        phase_diff = np.diff(phase)
        
        print(f"Symbol {i}: phase range = {np.min(phase):.3f} to {np.max(phase):.3f}")
        print(f"  Phase diff range = {np.min(phase_diff):.3f} to {np.max(phase_diff):.3f}")
        print(f"  Power = {np.mean(np.abs(symbol)**2):.6f}")

def test_demodulation_approaches(iq_samples, sf):
    """Test different demodulation approaches"""
    print(f"\\n=== Demodulation Tests ===")
    
    # Test 1: Simple correlation with known chirps
    print("Test 1: Correlation with known chirps")
    try:
        from lora_modulation_implementation import gen_chirp
        
        # Generate a known chirp for correlation
        N = 2 ** sf
        ovs = 1
        NN = N * ovs
        
        # Generate up chirp
        up_chirp = [0j] * NN
        _, _ = gen_chirp(up_chirp, N, ovs, NN, 0, True, 1.0, 0.0)
        
        # Correlate with signal
        correlation = np.correlate(iq_samples, up_chirp, mode='valid')
        max_corr_idx = np.argmax(np.abs(correlation))
        max_corr_value = correlation[max_corr_idx]
        
        print(f"Max correlation: {max_corr_value:.6f} at index {max_corr_idx}")
        
        if max_corr_idx < len(iq_samples) - len(up_chirp):
            print("Potential sync found!")
        else:
            print("No clear sync found")
            
    except Exception as e:
        print(f"Correlation test failed: {e}")
    
    # Test 2: Try different frequency offsets
    print("\\nTest 2: Frequency offset analysis")
    
    # Check for frequency offset
    phase_diff = np.diff(np.angle(iq_samples))
    freq_offset = np.mean(phase_diff) * sf / (2 * np.pi)
    
    print(f"Estimated frequency offset: {freq_offset:.2f} Hz")
    
    # Test 3: Try demodulation with frequency correction
    print("\\nTest 3: Demodulation with frequency correction")
    try:
        from lora_demodulation_advanced import LoRaDemodulator
        
        # Create demodulator
        demodulator = LoRaDemodulator(sf, sample_rate=250000)
        
        # Try to demodulate
        result = demodulator.demodulate_packet(iq_samples)
        print(f"Demodulation result: {result}")
        
    except Exception as e:
        print(f"Advanced demodulation failed: {e}")

def create_visualization(iq_samples, sample_rate):
    """Create visualization of the signal"""
    print("\\n=== Creating Visualizations ===")
    
    # Time domain plot
    plt.figure(figsize=(15, 10))
    
    # Plot 1: Time domain (first 1000 samples)
    plt.subplot(2, 2, 1)
    time_axis = np.arange(1000) / sample_rate
    plt.plot(time_axis, np.real(iq_samples[:1000]), label='I', alpha=0.7)
    plt.plot(time_axis, np.imag(iq_samples[:1000]), label='Q', alpha=0.7)
    plt.title('Time Domain (First 1000 samples)')
    plt.xlabel('Time (s)')
    plt.ylabel('Amplitude')
    plt.legend()
    plt.grid(True)
    
    # Plot 2: Power over time
    plt.subplot(2, 2, 2)
    power = np.abs(iq_samples) ** 2
    time_axis_full = np.arange(len(iq_samples)) / sample_rate
    plt.plot(time_axis_full, power)
    plt.title('Power over Time')
    plt.xlabel('Time (s)')
    plt.ylabel('Power')
    plt.grid(True)
    
    # Plot 3: Frequency spectrum
    plt.subplot(2, 2, 3)
    fft = np.fft.fft(iq_samples)
    freqs = np.fft.fftfreq(len(iq_samples), 1/sample_rate)
    power_spectrum = np.abs(fft) ** 2
    
    # Plot only positive frequencies
    positive_freqs = freqs[:len(freqs)//2]
    positive_power = power_spectrum[:len(power_spectrum)//2]
    
    plt.plot(positive_freqs, 10 * np.log10(positive_power + 1e-10))
    plt.title('Frequency Spectrum')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Power (dB)')
    plt.grid(True)
    
    # Plot 4: Phase over time
    plt.subplot(2, 2, 4)
    phase = np.angle(iq_samples)
    plt.plot(time_axis_full, phase)
    plt.title('Phase over Time')
    plt.xlabel('Time (s)')
    plt.ylabel('Phase (rad)')
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig('lora_signal_analysis.png', dpi=150, bbox_inches='tight')
    print("Saved visualization to: lora_signal_analysis.png")
    
    # Close the plot to free memory
    plt.close()

def create_signal_summary(iq_samples, sample_rate):
    """Create a text summary of the signal characteristics"""
    print("\\n=== Signal Summary ===")
    
    # Time domain analysis
    time_axis = np.arange(1000) / sample_rate
    i_real = np.real(iq_samples[:1000])
    i_imag = np.imag(iq_samples[:1000])
    
    print(f"First 10 I samples: {i_real[:10]}")
    print(f"First 10 Q samples: {i_imag[:10]}")
    print(f"I range: {np.min(i_real):.6f} to {np.max(i_real):.6f}")
    print(f"Q range: {np.min(i_imag):.6f} to {np.max(i_imag):.6f}")
    
    # Power analysis
    power = np.abs(iq_samples) ** 2
    time_axis_full = np.arange(len(iq_samples)) / sample_rate
    
    print(f"Power range: {np.min(power):.6f} to {np.max(power):.6f}")
    print(f"Power mean: {np.mean(power):.6f}")
    print(f"Power std: {np.std(power):.6f}")
    
    # Frequency analysis
    fft = np.fft.fft(iq_samples)
    freqs = np.fft.fftfreq(len(iq_samples), 1/sample_rate)
    power_spectrum = np.abs(fft) ** 2
    
    # Find peak frequency
    peak_idx = np.argmax(power_spectrum)
    peak_freq = freqs[peak_idx]
    peak_power = power_spectrum[peak_idx]
    
    print(f"Peak frequency: {peak_freq:.2f} Hz")
    print(f"Peak power: {peak_power:.2f}")
    
    # Phase analysis
    phase = np.angle(iq_samples)
    print(f"Phase range: {np.min(phase):.3f} to {np.max(phase):.3f} rad")
    print(f"Phase mean: {np.mean(phase):.3f} rad")
    
    # Save data to files for external analysis
    np.savetxt('signal_i_samples.txt', i_real[:1000], fmt='%.6f')
    np.savetxt('signal_q_samples.txt', i_imag[:1000], fmt='%.6f')
    np.savetxt('signal_power.txt', power, fmt='%.6f')
    
    print("Saved signal data to files for external analysis")

def main():
    print("Advanced LoRa Signal Analysis")
    print("=" * 40)
    
    # Load data
    iq_samples, metadata = load_iq_data()
    
    print(f"Loaded {len(iq_samples)} IQ samples")
    print(f"Sample rate: {metadata['sample_rate']} Hz")
    print(f"Duration: {len(iq_samples) / metadata['sample_rate']:.3f} seconds")
    print(f"Spreading Factor: {metadata['spreading_factor']}")
    
    # Analyze signal
    analyze_signal_characteristics(iq_samples, metadata['sample_rate'])
    
    # Test demodulation
    test_demodulation_approaches(iq_samples, metadata['spreading_factor'])
    
    # Create visualization
    create_visualization(iq_samples, metadata['sample_rate'])
    
    # Create signal summary
    create_signal_summary(iq_samples, metadata['sample_rate'])
    
    print("\\nAnalysis complete!")

if __name__ == "__main__":
    main()
