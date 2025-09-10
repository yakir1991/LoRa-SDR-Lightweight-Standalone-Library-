#include <gtest/gtest.h>
#include <lorawan/lorawan.hpp>
#include <lora_phy/phy.hpp>
#include <vector>
#include <random>

static bool run_roundtrip(const std::vector<uint8_t>& payload) {
    lora_phy::lora_workspace ws{};
    lora_phy::lora_params params{};
    params.sf = 7;
    params.cr = 1;
    params.bw = lora_phy::bandwidth::bw_125;
    lora_phy::init(&ws, &params);

    lorawan::MHDR mhdr;
    mhdr.mtype = lorawan::MType::UnconfirmedDataUp;
    mhdr.major = 0;
    lorawan::FHDR fhdr;
    fhdr.devaddr = 0x01020304u;
    fhdr.fctrl = 0x00u;
    fhdr.fcnt = 1u;
    lorawan::Frame frame;
    frame.mhdr = mhdr;
    frame.fhdr = fhdr;
    frame.payload = payload;

    std::vector<uint16_t> symbols(payload.size() * 2 + 32);
    std::vector<uint8_t> tmp(symbols.size() / 2 + 8);

    ssize_t sc = lorawan::build_frame(&ws, frame, symbols.data(), symbols.size(),
                                      tmp.data(), tmp.size());
    if (sc < 0) return false;

    lorawan::Frame parsed;
    ssize_t pc = lorawan::parse_frame(&ws, symbols.data(), static_cast<size_t>(sc),
                                      parsed, tmp.data(), tmp.size());
    if (pc < 0) return false;

    return parsed.payload == payload;
}

TEST(LorawanRoundTrip, RandomPayloads) {
    std::mt19937 rng(0);
    std::uniform_int_distribution<int> dist(0, 255);
    for (int i = 0; i < 5; ++i) {
        std::vector<uint8_t> payload(8);
        for (auto& b : payload) b = static_cast<uint8_t>(dist(rng));
        EXPECT_TRUE(run_roundtrip(payload));
    }
}

