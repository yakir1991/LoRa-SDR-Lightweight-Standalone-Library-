#include <lora_phy/phy.hpp>
#include <lora_phy/LoRaCodes.hpp>
#include <vector>
#include <complex>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <fstream>
#include <iomanip>
#include <string>

struct lora_params {
    unsigned sf = 7;
    unsigned bw = 0;
    unsigned cr = 0;
};

struct lora_metrics {
    bool crc_ok{};
    float cfo{};
    float time_offset{};
};

struct lora_workspace {
    uint16_t* symbol_buf{};
    std::complex<float>* fft_in{};
    std::complex<float>* fft_out{};
    lora_params params{};
    lora_metrics metrics{};
};

static int init(struct lora_workspace* ws, const struct lora_params* cfg) {
    if (!ws || !cfg) return -1;
    ws->params = *cfg;
    ws->metrics = {};
    return 0;
}

static ssize_t demodulate(struct lora_workspace* ws,
                          const std::complex<float>* iq, size_t sample_count,
                          uint16_t* symbols, size_t symbol_cap) {
    if (!ws || !iq || !symbols) return -1;
    size_t N = size_t(1) << ws->params.sf;
    if (sample_count % N != 0) return -1;
    size_t expected = sample_count / N;
    if (expected > symbol_cap) return -1;
    lora_phy::lora_demod_workspace demod_ws{};
    lora_phy::lora_demod_init(&demod_ws, ws->params.sf);
    size_t produced = lora_phy::lora_demodulate(&demod_ws, iq, sample_count, symbols);
    lora_phy::lora_demod_free(&demod_ws);
    ws->metrics.cfo = 0.0f;
    ws->metrics.time_offset = 0.0f;
    return static_cast<ssize_t>(produced);
}

static ssize_t decode(struct lora_workspace* ws,
                      const uint16_t* symbols, size_t symbol_count,
                      uint8_t* payload, size_t payload_cap) {
    if (!ws || !symbols || !payload) return -1;
    size_t produced = lora_phy::lora_decode(symbols, symbol_count, payload);
    if (produced > payload_cap) return -1;
    // compute CRC if possible: expect last two bytes to contain CRC
    if (produced >= 4) {
        size_t data_len = produced - 4; // exclude header(2) and crc(2)
        uint16_t provided_crc = payload[produced - 2] | (payload[produced - 1] << 8);
        uint16_t calc_crc = sx1272DataChecksum(payload + 2, data_len);
        ws->metrics.crc_ok = (provided_crc == calc_crc);
    } else {
        ws->metrics.crc_ok = false;
    }
    return static_cast<ssize_t>(produced);
}

static const lora_metrics* get_last_metrics(const lora_workspace* ws) {
    if (!ws) return nullptr;
    return &ws->metrics;
}

int main(int argc, char** argv) {
    const char* in_path = nullptr;
    lora_params params{};

    for (int i = 1; i < argc; ++i) {
        const char* arg = argv[i];
        if (std::strncmp(arg, "--in=", 5) == 0) in_path = arg + 5;
        else if (std::strncmp(arg, "--sf=", 5) == 0) params.sf = std::stoul(arg + 5);
        else if (std::strncmp(arg, "--bw=", 5) == 0) params.bw = std::stoul(arg + 5);
        else if (std::strncmp(arg, "--cr=", 5) == 0) params.cr = std::stoul(arg + 5);
        else {
            std::cerr << "Unknown argument: " << arg << std::endl;
            return 1;
        }
    }

    std::istream* in_stream = nullptr;
    std::ifstream file_stream;
    if (in_path) {
        file_stream.open(in_path, std::ios::binary);
        if (!file_stream) {
            std::cerr << "Failed to open input file" << std::endl;
            return 1;
        }
        in_stream = &file_stream;
    } else {
        in_stream = &std::cin;
    }

    std::vector<std::complex<float>> samples;
    float re = 0.0f, im = 0.0f;
    while (in_stream->read(reinterpret_cast<char*>(&re), sizeof(float))) {
        if (!in_stream->read(reinterpret_cast<char*>(&im), sizeof(float))) break;
        samples.emplace_back(re, im);
    }

    if (samples.empty()) {
        std::cerr << "No samples read" << std::endl;
        return 1;
    }

    size_t N = size_t(1) << params.sf;
    if (samples.size() % N != 0) {
        std::cerr << "Sample count not multiple of symbol size" << std::endl;
        return 1;
    }
    size_t symbol_count = samples.size() / N;

    std::vector<uint16_t> symbols(symbol_count);
    std::vector<std::complex<float>> fft_in(N);
    std::vector<std::complex<float>> fft_out(N);

    lora_workspace ws{};
    ws.symbol_buf = symbols.data();
    ws.fft_in = fft_in.data();
    ws.fft_out = fft_out.data();

    if (init(&ws, &params) != 0) {
        std::cerr << "init failed" << std::endl;
        return 1;
    }

    ssize_t demod_syms = demodulate(&ws, samples.data(), samples.size(), ws.symbol_buf, symbol_count);
    if (demod_syms < 0) {
        std::cerr << "demodulate failed" << std::endl;
        return 1;
    }

    std::vector<uint8_t> decoded(symbol_count / 2);
    ssize_t decoded_bytes = decode(&ws, ws.symbol_buf, demod_syms, decoded.data(), decoded.size());
    if (decoded_bytes < 0) {
        std::cerr << "decode failed" << std::endl;
        return 1;
    }

    const lora_metrics* m = get_last_metrics(&ws);

    if (decoded_bytes >= 2) {
        uint8_t length_field = decoded[0];
        uint8_t header_field = decoded[1];
        std::cout << "Header length=" << static_cast<unsigned>(length_field)
                  << " header=" << static_cast<unsigned>(header_field) << std::endl;
        std::cout << "Payload: ";
        for (ssize_t i = 2; i < decoded_bytes - 2; ++i) {
            std::cout << std::hex << std::setw(2) << std::setfill('0')
                      << static_cast<unsigned>(decoded[i]);
        }
        std::cout << std::dec << std::endl;
    } else {
        std::cout << "Decoded payload too short" << std::endl;
    }

    if (m) {
        std::cout << "CRC OK: " << (m->crc_ok ? "yes" : "no") << std::endl;
        std::cout << "CFO: " << m->cfo << std::endl;
        std::cout << "Time offset: " << m->time_offset << std::endl;
    }

    return 0;
}

