#include <lora_phy/phy.hpp>
#include <lora_phy/LoRaCodes.hpp>
#include <lora_phy/LoRaDetector.hpp>
#include <lora_phy/ChirpGenerator.hpp>

#include <cmath>

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

ssize_t demodulate(lora_workspace* ws,
                   const std::complex<float>* iq, size_t sample_count,
                   uint16_t* symbols, size_t symbol_cap) {
    if (!ws || !iq || !symbols) return -1;
    unsigned sf = deduce_sf(ws);
    size_t N = size_t(1) << sf;
    if (sample_count % N != 0) return -1;
    size_t num_symbols = sample_count / N;
    if (num_symbols > symbol_cap) return -1;

    kissfft<float> fft(ws->plan_fwd);
    LoRaDetector<float> detector(N, ws->fft_in, ws->fft_out, fft);
    for (size_t s = 0; s < num_symbols; ++s) {
        float phase = 0.0f;
        genChirp(ws->fft_out, static_cast<int>(N), 1, static_cast<int>(N),
                 0.0f, true, 1.0f, phase);
        const std::complex<float>* sym = iq + s * N;
        for (size_t i = 0; i < N; ++i)
            detector.feed(i, sym[i] * ws->fft_out[i]);
        float p, pav, findex;
        size_t idx = detector.detect(p, pav, findex);
        symbols[s] = static_cast<uint16_t>(idx);
    }
    ws->metrics.cfo = 0.0f;
    ws->metrics.time_offset = 0.0f;
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

