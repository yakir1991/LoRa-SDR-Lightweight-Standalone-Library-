#include <lora_phy/LoRaDetector.hpp>
#include <lora_phy/phy.hpp>

namespace lora_phy {

size_t lora_demodulate(const std::complex<float>* samples, size_t sample_count,
                       uint16_t* out_symbols, unsigned sf)
{
    const size_t N = size_t(1) << sf; // samples per symbol
    const size_t num_symbols = sample_count / N;
    auto fft_in = new std::complex<float>[N];
    auto fft_out = new std::complex<float>[N];
    kissfft<float> fft(N, false);

    {
        LoRaDetector<float> detector(N, fft_in, fft_out, fft);

        for (size_t s = 0; s < num_symbols; ++s)
        {
            const std::complex<float>* sym_samps = samples + s * N;
            for (size_t i = 0; i < N; ++i) detector.feed(i, sym_samps[i]);
            float p, pav, findex;
            size_t idx = detector.detect(p, pav, findex);
            out_symbols[s] = static_cast<uint16_t>(idx);
        }
    }

    delete[] fft_in;
    delete[] fft_out;
    return num_symbols;
}

} // namespace lora_phy

