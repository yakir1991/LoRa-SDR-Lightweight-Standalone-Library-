#pragma once
#include <cstddef>
#include <cstdint>
#include <complex>
#include <lora_phy/kissfft.hh>

template <typename T> class LoRaDetector;

namespace lora_phy {

// Workspace used by the demodulator to hold FFT buffers and detector instance.
struct lora_demod_workspace {
    size_t N{};
    std::complex<float>* fft_in{};
    std::complex<float>* fft_out{};
    kissfft<float>* fft{};
    LoRaDetector<float>* detector{};
};

// Initialize and clean up the demodulator workspace.
void lora_demod_init(lora_demod_workspace* ws, unsigned sf);
void lora_demod_free(lora_demod_workspace* ws);

// Modulate an array of symbols into complex baseband samples.
// samples_per_symbol = 1 << sf
size_t lora_modulate(const uint16_t* symbols, size_t symbol_count,
                     std::complex<float>* out_samples, unsigned sf,
                     float amplitude = 1.0f);

// Demodulate complex samples into symbol indices using a prepared workspace.
size_t lora_demodulate(lora_demod_workspace* ws,
                       const std::complex<float>* samples, size_t sample_count,
                       uint16_t* out_symbols);

// Simple Hamming(8,4) based encoder. Each input byte becomes two symbols.
size_t lora_encode(const uint8_t* bytes, size_t byte_count,
                   uint16_t* out_symbols, unsigned sf);

// Decode symbols produced by lora_encode back into bytes.
size_t lora_decode(const uint16_t* symbols, size_t symbol_count,
                   uint8_t* out_bytes);

} // namespace lora_phy

