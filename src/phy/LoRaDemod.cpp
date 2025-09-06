#include <lora_phy/LoRaDetector.hpp>
#include <lora_phy/phy.hpp>

#include <algorithm>
#include <cmath>

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
                       uint16_t* out_symbols, unsigned osr)
{
    const size_t N = ws->N;                    // base samples per symbol
    const size_t step = N * osr;                // oversampled samples per symbol
    const size_t num_symbols = sample_count / step;

    const size_t est_syms = std::min(num_symbols, size_t(2));
    float sum_index = 0.0f;
    float phase_diff = 0.0f;
    float prev_phase = 0.0f;
    bool have_prev = false;
    unsigned sum_t = 0;
    for (size_t s = 0; s < est_syms; ++s) {
        const std::complex<float>* sym_base = samples + s * step;
        float best_p = -1e30f;
        size_t best_idx = 0;
        float best_fi = 0.0f;
        unsigned best_t = 0;
        std::complex<float> best_bin;
        for (unsigned t = 0; t < osr; ++t) {
            for (size_t i = 0; i < N; ++i)
                ws->detector->feed(i, sym_base[t + i * osr]);
            float p, pav, findex;
            size_t idx = ws->detector->detect(p, pav, findex);
            if (p > best_p) {
                best_p = p;
                best_idx = idx;
                best_fi = findex;
                best_t = t;
                best_bin = ws->fft_out[idx];
            }
        }
        sum_t += best_t;
        sum_index += static_cast<float>(best_idx) + best_fi;
        float phase = std::arg(best_bin);
        if (have_prev) {
            float d = phase - prev_phase;
            while (d > float(M_PI)) d -= 2.0f * float(M_PI);
            while (d < -float(M_PI)) d += 2.0f * float(M_PI);
            phase_diff += d;
        }
        prev_phase = phase;
        have_prev = true;
    }

    float avg_index = sum_index / static_cast<float>(est_syms);
    float cfo_coarse = avg_index / static_cast<float>(N);
    float cfo_fine = 0.0f;
    if (est_syms > 1)
        cfo_fine = (phase_diff / static_cast<float>(est_syms - 1)) /
                   (2.0f * float(M_PI) * static_cast<float>(N));
    ws->metrics.cfo = cfo_coarse + cfo_fine;
    float frac = avg_index - std::floor(avg_index + 0.5f);
    float avg_t = static_cast<float>(sum_t) / static_cast<float>(est_syms);
    ws->metrics.time_offset = avg_t -
                              frac * static_cast<float>(N) * static_cast<float>(osr);

    int t_off = static_cast<int>(std::round(ws->metrics.time_offset));
    float rate = -2.0f * float(M_PI) * ws->metrics.cfo / static_cast<float>(N);
    for (size_t s = 0; s < num_symbols; ++s) {
        size_t base = s * step;
        if (t_off > 0) {
            if (base + size_t(t_off) + step <= sample_count)
                base += size_t(t_off);
        } else if (t_off < 0) {
            size_t off = size_t(-t_off);
            if (off <= base) base -= off;
        }
        const std::complex<float>* sym_samps = samples + base;
        float start = rate * (static_cast<float>(s * N) +
                              static_cast<float>(t_off) / static_cast<float>(osr));
        for (size_t i = 0; i < N; ++i) {
            float ph = start + rate * static_cast<float>(i);
            float cs = std::cos(ph);
            float sn = std::sin(ph);
            ws->detector->feed(i, sym_samps[i * osr] * std::complex<float>(cs, sn));
        }
        float p, pav, findex;
        size_t idx = ws->detector->detect(p, pav, findex);
        out_symbols[s] = static_cast<uint16_t>(idx);
    }

    return num_symbols;
}

} // namespace lora_phy

