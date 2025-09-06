#include <lora_phy/phy.hpp>
#include <vector>
#include <complex>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <fstream>
#include <string>
#include <sys/types.h>

struct lora_params {
    unsigned sf = 7;
    unsigned bw = 0;
    unsigned cr = 0;
};

struct lora_workspace {
    uint16_t* symbol_buf{};
    std::complex<float>* fft_in{};
    std::complex<float>* fft_out{};
    lora_params params{};
};

static int init(struct lora_workspace* ws, const struct lora_params* cfg) {
    if (!ws || !cfg) return -1;
    ws->params = *cfg;
    return 0;
}

static ssize_t encode(struct lora_workspace* ws,
                      const uint8_t* payload, size_t payload_len,
                      uint16_t* symbols, size_t symbol_cap) {
    if (!ws || !payload || !symbols) return -1;
    size_t produced = lora_phy::lora_encode(payload, payload_len, symbols, ws->params.sf);
    if (produced > symbol_cap) return -1;
    return static_cast<ssize_t>(produced);
}

static ssize_t modulate(struct lora_workspace* ws,
                        const uint16_t* symbols, size_t symbol_count,
                        std::complex<float>* iq, size_t iq_cap) {
    if (!ws || !symbols || !iq) return -1;
    size_t produced = lora_phy::lora_modulate(symbols, symbol_count, iq, ws->params.sf);
    if (produced > iq_cap) return -1;
    return static_cast<ssize_t>(produced);
}

int main(int argc, char** argv) {
    const char* payload_hex = nullptr;
    lora_params params{};
    const char* out_path = nullptr;
    bool to_stdout = false;

    for (int i = 1; i < argc; ++i) {
        const char* arg = argv[i];
        if (std::strncmp(arg, "--payload=", 10) == 0) payload_hex = arg + 10;
        else if (std::strncmp(arg, "--sf=", 5) == 0) params.sf = std::stoul(arg + 5);
        else if (std::strncmp(arg, "--bw=", 5) == 0) params.bw = std::stoul(arg + 5);
        else if (std::strncmp(arg, "--cr=", 5) == 0) params.cr = std::stoul(arg + 5);
        else if (std::strncmp(arg, "--out=", 6) == 0) out_path = arg + 6;
        else if (std::strcmp(arg, "--stdout") == 0) to_stdout = true;
        else {
            std::cerr << "Unknown argument: " << arg << std::endl;
            return 1;
        }
    }

    if (!payload_hex) {
        std::cerr << "--payload argument is required" << std::endl;
        return 1;
    }
    if (!to_stdout && !out_path) {
        std::cerr << "Specify --out=<path> or --stdout" << std::endl;
        return 1;
    }

    size_t hex_len = std::strlen(payload_hex);
    if (hex_len % 2 != 0) {
        std::cerr << "Payload hex must have even length" << std::endl;
        return 1;
    }

    std::vector<uint8_t> payload;
    payload.reserve(hex_len / 2);
    for (size_t i = 0; i < hex_len; i += 2) {
        std::string byte_str(payload_hex + i, 2);
        payload.push_back(static_cast<uint8_t>(std::stoul(byte_str, nullptr, 16)));
    }

    const size_t symbol_cap = payload.size() * 2; // Hamming(8,4) -> 2 symbols per byte
    const size_t N = size_t(1) << params.sf;      // samples per symbol

    std::vector<uint16_t> symbols(symbol_cap);
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

    ssize_t symbol_count = encode(&ws, payload.data(), payload.size(), ws.symbol_buf, symbol_cap);
    if (symbol_count < 0) {
        std::cerr << "encode failed" << std::endl;
        return 1;
    }

    std::vector<std::complex<float>> iq(symbol_count * N);
    ssize_t sample_count = modulate(&ws, ws.symbol_buf, symbol_count, iq.data(), iq.size());
    if (sample_count < 0) {
        std::cerr << "modulate failed" << std::endl;
        return 1;
    }

    std::ostream* out_stream = nullptr;
    std::ofstream file_stream;
    if (to_stdout) {
        out_stream = &std::cout;
    } else {
        file_stream.open(out_path, std::ios::binary);
        if (!file_stream) {
            std::cerr << "Failed to open output file" << std::endl;
            return 1;
        }
        out_stream = &file_stream;
    }

    for (ssize_t i = 0; i < sample_count; ++i) {
        float re = iq[i].real();
        float im = iq[i].imag();
        out_stream->write(reinterpret_cast<const char*>(&re), sizeof(float));
        out_stream->write(reinterpret_cast<const char*>(&im), sizeof(float));
    }

    if (file_stream) file_stream.close();
    return 0;
}

