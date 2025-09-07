#include <cmath>
#include <lora_phy/ChirpGenerator.hpp>
#include <lora_phy/phy.hpp>

namespace lora_phy {

size_t lora_modulate(const uint16_t* symbols, size_t symbol_count,
                     std::complex<float>* out_samples, unsigned sf, unsigned osr,
                     bandwidth bw, float amplitude)
{
    const size_t N = size_t(1) << sf; // base samples per symbol
    const size_t step = N * osr;
    float phase = 0.0f;
    const float bw_scale = lora_phy::bw_scale(bw);
    for (size_t s = 0; s < symbol_count; ++s)
    {
        const float freq = (2.0f * float(M_PI) * symbols[s] * bw_scale) /
                           (float(N) * static_cast<float>(osr));
        genChirp(out_samples + s * step, static_cast<int>(N), static_cast<int>(osr),
                 static_cast<int>(step), freq, false, amplitude, phase, bw_scale);
    }
    return symbol_count * step;
}

} // namespace lora_phy

