#include <cstdint>
#include <iostream>

#include "lora_phy/LoRaCodes.hpp"

// Place the reference LoRa-SDR implementation inside a namespace to avoid
// conflicts with the lightweight implementation symbols.
namespace lora_sdr_ref {
#include "LoRaCodes.hpp"
}

static bool verify_codeword(uint8_t val) {
    bool ok = true;

    auto lite_enc = encodeHamming84sx(val);
    auto ref_enc = lora_sdr_ref::encodeHamming84sx(val);
    if (lite_enc != ref_enc) {
        std::cerr << "Encode mismatch for value " << int(val) << "\n";
        ok = false;
    }

    bool lite_err = false, lite_bad = false;
    bool ref_err = false, ref_bad = false;
    auto lite_dec = decodeHamming84sx(lite_enc, lite_err, lite_bad);
    auto ref_dec = lora_sdr_ref::decodeHamming84sx(ref_enc, ref_err, ref_bad);
    if (lite_dec != ref_dec || lite_err != ref_err || lite_bad != ref_bad) {
        std::cerr << "Clean decode mismatch for value " << int(val) << "\n";
        ok = false;
    }

    for (int bit = 0; bit < 8; ++bit) {
        auto corrupted_lite = lite_enc ^ (1u << bit);
        auto corrupted_ref = ref_enc ^ (1u << bit);

        bool lite_err2 = false, lite_bad2 = false;
        bool ref_err2 = false, ref_bad2 = false;
        auto lite_dec2 = decodeHamming84sx(corrupted_lite, lite_err2, lite_bad2);
        auto ref_dec2 = lora_sdr_ref::decodeHamming84sx(corrupted_ref, ref_err2, ref_bad2);

        if (lite_dec2 != ref_dec2 || lite_err2 != ref_err2 || lite_bad2 != ref_bad2) {
            std::cerr << "Mismatch for value " << int(val)
                      << " with bit flip " << bit << "\n";
            ok = false;
        }
    }

    return ok;
}

int hamming_cross_check_main() {
    bool ok = true;
    for (uint8_t val = 0; val < 16; ++val) {
        ok = ok && verify_codeword(val);
    }
    return ok ? 0 : 1;
}

