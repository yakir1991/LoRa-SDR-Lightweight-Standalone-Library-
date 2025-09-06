#include <cmath>
#include <lora_phy/ChirpGenerator.hpp>
#include <lora_phy/phy.hpp>

namespace lora_phy {

size_t lora_modulate(const uint16_t* symbols, size_t symbol_count,
                     std::complex<float>* out_samples, unsigned sf,
                     float amplitude)
{
    const size_t N = size_t(1) << sf; // samples per symbol
    float phase = 0.0f;
    for (size_t s = 0; s < symbol_count; ++s)
    {
        const float freq = (2.0f * float(M_PI) * symbols[s]) / float(N);
        genChirp(out_samples + s * N, N, 1, N, freq, false, amplitude, phase);
    }
    return symbol_count * N;
}

} // namespace lora_phy

