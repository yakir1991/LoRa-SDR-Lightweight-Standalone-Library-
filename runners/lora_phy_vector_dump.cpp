#include <lora_phy/phy.hpp>
#include <vector>
#include <complex>
#include <fstream>
#include <random>
#include <iostream>
#include <cstdint>
#include <cstring>

int main(int argc, char** argv) {
    unsigned sf = 7;
    unsigned seed = 0;
    size_t byte_count = 16;
    const char* out_dir = nullptr;

    for (int i = 1; i < argc; ++i) {
        const char* arg = argv[i];
        if (std::strncmp(arg, "--sf=", 5) == 0) sf = std::stoul(arg + 5);
        else if (std::strncmp(arg, "--seed=", 7) == 0) seed = std::stoul(arg + 7);
        else if (std::strncmp(arg, "--bytes=", 8) == 0) byte_count = std::stoul(arg + 8);
        else if (std::strncmp(arg, "--out=", 6) == 0) out_dir = arg + 6;
        else {
            std::cerr << "Unknown argument: " << arg << std::endl;
            return 1;
        }
    }

    if (!out_dir) {
        std::cerr << "--out argument is required" << std::endl;
        return 1;
    }

    std::mt19937 rng(seed);
    std::uniform_int_distribution<int> dist(0, 255);
    std::vector<uint8_t> payload(byte_count);
    for (size_t i = 0; i < byte_count; i++) payload[i] = static_cast<uint8_t>(dist(rng));

    std::vector<uint16_t> symbols(byte_count * 2);
    size_t symbol_count = lora_phy::lora_encode(payload.data(), byte_count, symbols.data(), sf);

    const size_t samples_per_symbol = 1u << sf;
    std::vector<std::complex<float>> samples(symbol_count * samples_per_symbol);
    size_t sample_count = lora_phy::lora_modulate(symbols.data(), symbol_count, samples.data(), sf);

    std::vector<uint16_t> demod(symbol_count);
    lora_phy::lora_demod_workspace demod_ws{};
    lora_phy::lora_demod_init(&demod_ws, sf);
    lora_phy::lora_demodulate(&demod_ws, samples.data(), sample_count, demod.data());
    lora_phy::lora_demod_free(&demod_ws);

    std::vector<uint8_t> decoded(byte_count);
    lora_phy::lora_decode(demod.data(), symbol_count, decoded.data());

    std::string base(out_dir);

    std::ofstream f;
    f.open(base + "/payload.bin", std::ios::binary);
    f.write(reinterpret_cast<const char*>(payload.data()), payload.size());
    f.close();

    f.open(base + "/symbols.csv");
    for (size_t i = 0; i < symbol_count; i++) f << symbols[i] << "\n";
    f.close();

    f.open(base + "/iq_samples.csv");
    for (size_t i = 0; i < sample_count; i++)
        f << samples[i].real() << "," << samples[i].imag() << "\n";
    f.close();

    f.open(base + "/demod_symbols.csv");
    for (size_t i = 0; i < symbol_count; i++) f << demod[i] << "\n";
    f.close();

    f.open(base + "/decoded.bin", std::ios::binary);
    f.write(reinterpret_cast<const char*>(decoded.data()), decoded.size());
    f.close();

    return 0;
}

