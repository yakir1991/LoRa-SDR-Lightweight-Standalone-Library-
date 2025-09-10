#include <gtest/gtest.h>
#include <lora_phy/phy.hpp>
#include <lora_phy/ChirpGenerator.hpp>
#include <complex>
#include <vector>
#include <random>
#include <fstream>
#include <string>

struct Profile {
    std::string name;
    unsigned sf{};
    unsigned bw{};
    std::string cr;
};

static std::string trim(const std::string& s) {
    const auto start = s.find_first_not_of(" \t\r\n");
    if (start == std::string::npos) return "";
    const auto end = s.find_last_not_of(" \t\r\n");
    return s.substr(start, end - start + 1);
}

static bool load_profiles(const std::string& path, std::vector<Profile>& out) {
    std::ifstream f(path);
    if (!f) return false;
    std::string line;
    Profile current;
    bool in_profile = false;
    while (std::getline(f, line)) {
        line = trim(line);
        if (line.empty() || line[0] == '#') continue;
        if (line[0] == '-') {
            if (in_profile) out.push_back(current);
            current = Profile();
            in_profile = true;
            continue;
        }
        auto colon = line.find(':');
        if (colon == std::string::npos) continue;
        std::string key = trim(line.substr(0, colon));
        std::string val = trim(line.substr(colon + 1));
        if (key == "name") current.name = val;
        else if (key == "sf") current.sf = static_cast<unsigned>(std::stoul(val));
        else if (key == "bw") current.bw = static_cast<unsigned>(std::stoul(val));
        else if (key == "cr") current.cr = val;
    }
    if (in_profile) out.push_back(current);
    return true;
}

TEST(AwgnSweep, HighSNRNoErrors) {
    std::vector<Profile> profiles;
    ASSERT_TRUE(load_profiles("tests/profiles.yaml", profiles));
    const double snr_db = 12.0;
    std::mt19937 rng(0);

    for (const auto& p : profiles) {
        const size_t payload_size = 16;
        const size_t packets = 5;
        const size_t N = size_t(1) << p.sf;

        for (size_t pkt = 0; pkt < packets; ++pkt) {
            std::vector<uint8_t> payload(payload_size);
            for (auto& b : payload) b = static_cast<uint8_t>(rng() & 0xFF);

            std::vector<uint16_t> symbols(payload_size * 2);
            size_t symbol_count = lora_phy::lora_encode(payload.data(), payload.size(),
                                                        symbols.data(), p.sf);

            size_t sample_count = (symbol_count + 2) * N;
            std::vector<std::complex<float>> samples(sample_count);
            lora_phy::lora_modulate(symbols.data(), symbol_count, samples.data(), p.sf, 1,
                                    static_cast<lora_phy::bandwidth>(p.bw), 1.0f, 0x12);

            double sigma = std::pow(10.0, -snr_db / 20.0);
            std::normal_distribution<float> noise(0.0f, static_cast<float>(sigma / std::sqrt(2.0)));
            for (auto& s : samples) {
                s += std::complex<float>(noise(rng), noise(rng));
            }

            std::vector<std::complex<float>> dechirped(sample_count);
            std::vector<std::complex<float>> down(N);
            float phase = 0.0f;
            float scale = lora_phy::bw_scale(static_cast<lora_phy::bandwidth>(p.bw));
            genChirp(down.data(), static_cast<int>(N), 1, static_cast<int>(N), 0.0f,
                     true, 1.0f, phase, scale);
            for (size_t s = 0; s < symbol_count + 2; ++s) {
                for (size_t i = 0; i < N; ++i) {
                    dechirped[s * N + i] = samples[s * N + i] * down[i];
                }
            }

            std::vector<uint16_t> demod(symbol_count);
            std::vector<std::complex<float>> scratch(sample_count);
            lora_phy::lora_demod_workspace ws{};
            lora_phy::lora_demod_init(&ws, p.sf, lora_phy::window_type::window_none,
                                      scratch.data(), scratch.size());
            lora_phy::lora_demodulate(&ws, dechirped.data(), sample_count,
                                      demod.data(), 1, nullptr);
            lora_phy::lora_demod_free(&ws);

            std::vector<uint8_t> decoded(payload_size);
            lora_phy::lora_decode(demod.data(), symbol_count, decoded.data());
            EXPECT_EQ(decoded, payload);
        }
    }
}

