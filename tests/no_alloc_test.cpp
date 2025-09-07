#include "alloc_tracker.h"
#include <lora_phy/phy.hpp>
#include <complex>
#include <cstdint>
#include <iostream>
#include <vector>

int main() {
    const unsigned sf = 7;
    const size_t symbol_count = 4;
    const size_t samples_per_symbol = size_t(1) << sf;
    const size_t sample_count = symbol_count * samples_per_symbol;

    std::vector<uint16_t> symbols(symbol_count, 0);
    std::vector<std::complex<float>> samples(sample_count);

    {
        alloc_tracker::Guard guard;
        lora_phy::lora_modulate(symbols.data(), symbol_count, samples.data(), sf, 1,
                                lora_phy::bandwidth::bw_125);
        if (guard.count() != 0) {
            std::cerr << "Allocation occurred in modulate" << std::endl;
            return 1;
        }
    }

    lora_phy::lora_demod_workspace ws{};
    lora_phy::lora_demod_init(&ws, sf);
    std::vector<uint16_t> demod(symbol_count);

    {
        alloc_tracker::Guard guard;
        lora_phy::lora_demodulate(&ws, samples.data(), sample_count, demod.data(), 1);
        if (guard.count() != 0) {
            std::cerr << "Allocation occurred in demodulate" << std::endl;
            lora_phy::lora_demod_free(&ws);
            return 1;
        }
    }

    lora_phy::lora_demod_free(&ws);
    std::cout << "No allocations detected" << std::endl;
    return 0;
}
