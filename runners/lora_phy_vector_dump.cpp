#include <lora_phy/phy.hpp>
#include <lora_phy/LoRaCodes.hpp>
#include <vector>
#include <complex>
#include <fstream>
#include <random>
#include <iostream>
#include <cstdint>
#include <cstring>
#include <set>
#include <string>

/*
 * Dump internal LoRa PHY vectors for use in tests.
 *
 * Supported dump states and their file formats:
 *   payload          -> payload.bin (raw bytes)
 *   pre_interleave   -> pre_interleave.csv (decimal codewords per line)
 *   post_interleave  -> post_interleave.csv (decimal symbols per line)
 *   iq               -> iq_samples.csv ("real,imag" per line)
 *   demod            -> demod_symbols.csv (decimal symbols per line)
 *   deinterleave     -> deinterleave.csv (decimal codewords per line)
 *   decoded          -> decoded.bin (raw bytes)
 */
int main(int argc, char** argv) {
    unsigned sf = 7;
    unsigned seed = 0;
    size_t byte_count = 16;
    const char* out_dir = nullptr;
    std::set<std::string> dumps;

    for (int i = 1; i < argc; ++i) {
        const char* arg = argv[i];
        if (std::strncmp(arg, "--sf=", 5) == 0) sf = std::stoul(arg + 5);
        else if (std::strncmp(arg, "--seed=", 7) == 0) seed = std::stoul(arg + 7);
        else if (std::strncmp(arg, "--bytes=", 8) == 0) byte_count = std::stoul(arg + 8);
        else if (std::strncmp(arg, "--out=", 6) == 0) out_dir = arg + 6;
        else if (std::strncmp(arg, "--dump=", 7) == 0) dumps.insert(arg + 7);
        else {
            std::cerr << "Unknown argument: " << arg << std::endl;
            return 1;
        }
    }

    if (!out_dir) {
        std::cerr << "--out argument is required" << std::endl;
        return 1;
    }

    if (dumps.empty()) {
        dumps.insert("payload");
        dumps.insert("pre_interleave");
        dumps.insert("post_interleave");
        dumps.insert("iq");
        dumps.insert("demod");
        dumps.insert("deinterleave");
        dumps.insert("decoded");
    }

    std::mt19937 rng(seed);
    std::uniform_int_distribution<int> dist(0, 255);
    std::vector<uint8_t> payload(byte_count);
    for (size_t i = 0; i < byte_count; i++) payload[i] = static_cast<uint8_t>(dist(rng));

    // Encode into codewords (pre-interleave)
    const size_t nibble_count = byte_count * 2;
    const size_t cw_count = ((nibble_count + sf - 1) / sf) * sf; // round up to multiple of sf
    std::vector<uint8_t> pre_interleave(cw_count, 0);
    for (size_t i = 0; i < nibble_count; i++) {
        const uint8_t byte = payload[i / 2];
        const uint8_t nibble = (i & 1) ? (byte & 0x0f) : (byte >> 4);
        pre_interleave[i] = encodeHamming84sx(nibble);
    }

    // Interleave into symbols
    const size_t rdd = 4; // typical redundancy
    const size_t blocks = cw_count / sf;
    const size_t symbol_count = blocks * (4 + rdd);
    std::vector<uint16_t> post_interleave(symbol_count, 0);
    diagonalInterleaveSx(pre_interleave.data(), cw_count, post_interleave.data(), sf, rdd);

    const size_t samples_per_symbol = 1u << sf;
    std::vector<std::complex<float>> samples(symbol_count * samples_per_symbol);
    size_t sample_count = lora_phy::lora_modulate(post_interleave.data(), symbol_count, samples.data(), sf);

    std::vector<uint16_t> demod(symbol_count);
    lora_phy::lora_demod_workspace demod_ws{};
    lora_phy::lora_demod_init(&demod_ws, sf);
    lora_phy::lora_demodulate(&demod_ws, samples.data(), sample_count, demod.data());
    lora_phy::lora_demod_free(&demod_ws);

    // Deinterleave and decode
    std::vector<uint8_t> deinterleave(cw_count, 0);
    diagonalDeterleaveSx(demod.data(), symbol_count, deinterleave.data(), sf, rdd);

    std::vector<uint8_t> decoded(byte_count);
    for (size_t i = 0; i < byte_count; i++) {
        bool err = false, bad = false;
        uint8_t hi = decodeHamming84sx(deinterleave[2 * i], err, bad) & 0x0f;
        err = bad = false;
        uint8_t lo = decodeHamming84sx(deinterleave[2 * i + 1], err, bad) & 0x0f;
        decoded[i] = static_cast<uint8_t>((hi << 4) | lo);
    }

    std::string base(out_dir);
    std::ofstream f;

    if (dumps.count("payload")) {
        f.open(base + "/payload.bin", std::ios::binary);
        f.write(reinterpret_cast<const char*>(payload.data()), payload.size());
        f.close();
    }

    if (dumps.count("pre_interleave")) {
        f.open(base + "/pre_interleave.csv");
        for (size_t i = 0; i < cw_count; i++) f << static_cast<unsigned>(pre_interleave[i]) << "\n";
        f.close();
    }

    if (dumps.count("post_interleave")) {
        f.open(base + "/post_interleave.csv");
        for (size_t i = 0; i < symbol_count; i++) f << post_interleave[i] << "\n";
        f.close();
    }

    if (dumps.count("iq")) {
        f.open(base + "/iq_samples.csv");
        for (size_t i = 0; i < sample_count; i++)
            f << samples[i].real() << "," << samples[i].imag() << "\n";
        f.close();
    }

    if (dumps.count("demod")) {
        f.open(base + "/demod_symbols.csv");
        for (size_t i = 0; i < symbol_count; i++) f << demod[i] << "\n";
        f.close();
    }

    if (dumps.count("deinterleave")) {
        f.open(base + "/deinterleave.csv");
        for (size_t i = 0; i < cw_count; i++) f << static_cast<unsigned>(deinterleave[i]) << "\n";
        f.close();
    }

    if (dumps.count("decoded")) {
        f.open(base + "/decoded.bin", std::ios::binary);
        f.write(reinterpret_cast<const char*>(decoded.data()), decoded.size());
        f.close();
    }

    return 0;
}

