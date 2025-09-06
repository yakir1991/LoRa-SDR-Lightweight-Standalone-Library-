#include <lora_phy/phy.hpp>
#include <lora_phy/LoRaCodes.hpp>
#include <lora_phy/LoRaDetector.hpp>
#include <lora_phy/ChirpGenerator.hpp>

#include <cmath>
#include <algorithm>

namespace lora_phy {

namespace {

static unsigned deduce_sf(const lora_workspace* ws) {
    unsigned sf = 0;
    size_t n = static_cast<size_t>(ws->plan_fwd.nfft);
    while ((size_t(1) << sf) < n) ++sf;
    return sf;
}

} // namespace

int init(lora_workspace* ws, const lora_params* cfg) {
    if (!ws || !cfg) return -1;
    const int N = 1 << cfg->sf;
    kissfft<float>::init(ws->plan_fwd, N, false);
    kissfft<float>::init(ws->plan_inv, N, true);
    ws->metrics = {};
    return 0;
}

void reset(lora_workspace* ws) {
    if (ws) ws->metrics = {};
}

ssize_t encode(lora_workspace* ws,
               const uint8_t* payload, size_t payload_len,
               uint16_t* symbols, size_t symbol_cap) {
    if (!ws || !payload || !symbols) return -1;
    unsigned sf = deduce_sf(ws);
    size_t produced = lora_encode(payload, payload_len, symbols, sf);
    if (produced > symbol_cap) return -1;
    return static_cast<ssize_t>(produced);
}

ssize_t modulate(lora_workspace* ws,
                 const uint16_t* symbols, size_t symbol_count,
                 std::complex<float>* iq, size_t iq_cap) {
    if (!ws || !symbols || !iq) return -1;
    unsigned sf = deduce_sf(ws);
    size_t produced = lora_modulate(symbols, symbol_count, iq, sf);
    if (produced > iq_cap) return -1;
    return static_cast<ssize_t>(produced);
}

void estimate_offsets(lora_workspace* ws,
                      const std::complex<float>* samples,
                      size_t sample_count) {
    if (!ws || !samples || sample_count == 0) return;
    unsigned sf = deduce_sf(ws);
    size_t N = size_t(1) << sf;
    size_t symbols = sample_count / N;
    if (symbols == 0) return;

    kissfft<float> fft(ws->plan_fwd);
    LoRaDetector<float> detector(N, ws->fft_in, ws->fft_out, fft);

    float sum_index = 0.0f;
    float phase_diff = 0.0f;
    float prev_phase = 0.0f;
    bool have_prev = false;
    for (size_t s = 0; s < symbols; ++s) {
        const std::complex<float>* sym = samples + s * N;
        for (size_t i = 0; i < N; ++i) detector.feed(i, sym[i]);
        float p, pav, findex;
        size_t idx = detector.detect(p, pav, findex);
        sum_index += static_cast<float>(idx) + findex;
        std::complex<float> bin = ws->fft_out[idx];
        float phase = std::arg(bin);
        if (have_prev) {
            float d = phase - prev_phase;
            while (d > float(M_PI)) d -= 2.0f * float(M_PI);
            while (d < -float(M_PI)) d += 2.0f * float(M_PI);
            phase_diff += d;
        }
        prev_phase = phase;
        have_prev = true;
    }

    float avg_index = sum_index / static_cast<float>(symbols);
    float cfo_coarse = avg_index / static_cast<float>(N);
    float cfo_fine = 0.0f;
    if (symbols > 1)
        cfo_fine = (phase_diff / static_cast<float>(symbols - 1)) /
                   (2.0f * float(M_PI) * static_cast<float>(N));
    ws->metrics.cfo = cfo_coarse + cfo_fine;
    float frac = avg_index - std::floor(avg_index + 0.5f);
    ws->metrics.time_offset = -frac * static_cast<float>(N);
}

void compensate_offsets(const lora_workspace* ws,
                        std::complex<float>* samples,
                        size_t sample_count) {
    if (!ws || !samples || sample_count == 0) return;
    unsigned sf = deduce_sf(ws);
    size_t N = size_t(1) << sf;
    float cfo = ws->metrics.cfo;
    float to = ws->metrics.time_offset;
    for (size_t n = 0; n < sample_count; ++n) {
        float ph = -2.0f * float(M_PI) * cfo * (static_cast<float>(n) / static_cast<float>(N));
        float cs = std::cos(ph);
        float sn = std::sin(ph);
        samples[n] *= std::complex<float>(cs, sn);
    }
    int offset = static_cast<int>(std::round(to));
    if (offset > 0 && size_t(offset) < sample_count) {
        for (size_t n = sample_count; n-- > size_t(offset);)
            samples[n] = samples[n - size_t(offset)];
        for (size_t n = 0; n < size_t(offset); ++n)
            samples[n] = std::complex<float>(0.0f, 0.0f);
    } else if (offset < 0 && size_t(-offset) < sample_count) {
        size_t off = size_t(-offset);
        for (size_t n = 0; n + off < sample_count; ++n)
            samples[n] = samples[n + off];
        for (size_t n = sample_count - off; n < sample_count; ++n)
            samples[n] = std::complex<float>(0.0f, 0.0f);
    }
}

ssize_t demodulate(lora_workspace* ws,
                   const std::complex<float>* iq, size_t sample_count,
                   uint16_t* symbols, size_t symbol_cap) {
    if (!ws || !iq || !symbols) return -1;
    unsigned sf = deduce_sf(ws);
    size_t N = size_t(1) << sf;
    if (sample_count % N != 0) return -1;
    size_t num_symbols = sample_count / N;
    if (num_symbols > symbol_cap) return -1;

    size_t est_samples = std::min(sample_count, N * size_t(2));
    estimate_offsets(ws, iq, est_samples);

    kissfft<float> fft(ws->plan_fwd);
    LoRaDetector<float> detector(N, ws->fft_in, ws->fft_out, fft);
    int t_off = static_cast<int>(std::round(ws->metrics.time_offset));
    float rate = -2.0f * float(M_PI) * ws->metrics.cfo / static_cast<float>(N);
    for (size_t s = 0; s < num_symbols; ++s) {
        float tmp = 0.0f;
        genChirp(ws->fft_out, static_cast<int>(N), 1, static_cast<int>(N),
                 0.0f, true, 1.0f, tmp);
        size_t base = s * N;
        if (t_off > 0) {
            if (base + size_t(t_off) + N <= sample_count)
                base += size_t(t_off);
        } else if (t_off < 0) {
            size_t off = size_t(-t_off);
            if (off <= base) base -= off;
        }
        const std::complex<float>* sym = iq + base;
        float start = rate * static_cast<float>(s * N);
        for (size_t i = 0; i < N; ++i) {
            float ph = start + rate * static_cast<float>(i);
            float cs = std::cos(ph);
            float sn = std::sin(ph);
            detector.feed(i, sym[i] * ws->fft_out[i] * std::complex<float>(cs, sn));
        }
        float p, pav, findex;
        size_t idx = detector.detect(p, pav, findex);
        symbols[s] = static_cast<uint16_t>(idx);
    }
    return static_cast<ssize_t>(num_symbols);
}

ssize_t decode(lora_workspace* ws,
               const uint16_t* symbols, size_t symbol_count,
               uint8_t* payload, size_t payload_cap) {
    if (!ws || !symbols || !payload) return -1;
    size_t produced = lora_decode(symbols, symbol_count, payload);
    if (produced > payload_cap) return -1;
    if (produced >= 4) {
        size_t data_len = produced - 4;
        uint16_t provided = payload[produced - 2] | (payload[produced - 1] << 8);
        uint16_t calc = sx1272DataChecksum(payload + 2, data_len);
        ws->metrics.crc_ok = (provided == calc);
    } else {
        ws->metrics.crc_ok = false;
    }
    return static_cast<ssize_t>(produced);
}

const lora_metrics* get_last_metrics(const lora_workspace* ws) {
    if (!ws) return nullptr;
    return &ws->metrics;
}

} // namespace lora_phy

