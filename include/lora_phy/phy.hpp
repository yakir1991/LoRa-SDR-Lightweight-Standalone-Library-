#pragma once
#include <cstddef>
#include <cstdint>
#include <complex>

namespace lora_phy {

// Modulate an array of symbols into complex baseband samples.
// samples_per_symbol = 1 << sf
size_t lora_modulate(const uint16_t* symbols, size_t symbol_count,
                     std::complex<float>* out_samples, unsigned sf,
                     float amplitude = 1.0f);

// Demodulate complex samples into symbol indices.
size_t lora_demodulate(const std::complex<float>* samples, size_t sample_count,
                       uint16_t* out_symbols, unsigned sf);

// Simple Hamming(8,4) based encoder. Each input byte becomes two symbols.
size_t lora_encode(const uint8_t* bytes, size_t byte_count,
                   uint16_t* out_symbols, unsigned sf);

// Decode symbols produced by lora_encode back into bytes.
size_t lora_decode(const uint16_t* symbols, size_t symbol_count,
                   uint8_t* out_bytes);

} // namespace lora_phy

