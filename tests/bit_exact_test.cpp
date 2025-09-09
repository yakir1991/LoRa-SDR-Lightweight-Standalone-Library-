#include <lora_phy/phy.hpp>
#include <cstdint>
#include <vector>

int bit_exact_test_main() {
    // Simple encode/decode regression using a fixed payload
    const std::vector<uint8_t> payload = {0xDE, 0xAD, 0xBE, 0xEF};
    std::vector<uint16_t> symbols(payload.size() * 2);
    const size_t symbol_count =
        lora_phy::lora_encode(payload.data(), payload.size(), symbols.data(), 7);
    std::vector<uint8_t> decoded(payload.size());
    lora_phy::lora_decode(symbols.data(), symbol_count, decoded.data());
    return decoded == payload ? 0 : 1;
}
