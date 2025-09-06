#include <lora_phy/LoRaDetector.hpp>
#include <lora_phy/phy.hpp>

namespace lora_phy {

void lora_demod_init(lora_demod_workspace* ws, unsigned sf)
{
    ws->N = size_t(1) << sf;
    ws->fft_in = new std::complex<float>[ws->N];
    ws->fft_out = new std::complex<float>[ws->N];
    kissfft<float>::init(ws->fft_plan, ws->N, false);
    ws->fft = new kissfft<float>(ws->fft_plan);
    ws->detector = new LoRaDetector<float>(ws->N, ws->fft_in, ws->fft_out, *ws->fft);
}

void lora_demod_free(lora_demod_workspace* ws)
{
    delete ws->detector;
    delete ws->fft;
    delete[] ws->fft_in;
    delete[] ws->fft_out;
    ws->detector = nullptr;
    ws->fft = nullptr;
    ws->fft_in = nullptr;
    ws->fft_out = nullptr;
    ws->N = 0;
}

size_t lora_demodulate(lora_demod_workspace* ws,
                       const std::complex<float>* samples, size_t sample_count,
                       uint16_t* out_symbols)
{
    const size_t N = ws->N; // samples per symbol
    const size_t num_symbols = sample_count / N;

    for (size_t s = 0; s < num_symbols; ++s)
    {
        const std::complex<float>* sym_samps = samples + s * N;
        for (size_t i = 0; i < N; ++i) ws->detector->feed(i, sym_samps[i]);
        float p, pav, findex;
        size_t idx = ws->detector->detect(p, pav, findex);
        out_symbols[s] = static_cast<uint16_t>(idx);
    }

    return num_symbols;
}

} // namespace lora_phy

