#include <lorawan/lorawan.hpp>

#include <algorithm>
#include <vector>

namespace lorawan {

namespace {
// Simple CRC32 implementation for MIC generation
static uint32_t crc32(const uint8_t* data, size_t len) {
    uint32_t crc = 0xFFFFFFFFu;
    for (size_t i = 0; i < len; ++i) {
        crc ^= data[i];
        for (int j = 0; j < 8; ++j) {
            if (crc & 1)
                crc = (crc >> 1) ^ 0xEDB88320u;
            else
                crc >>= 1;
        }
    }
    return ~crc;
}
} // namespace

uint32_t compute_mic(const uint8_t* data, size_t len) {
    return crc32(data, len);
}

ssize_t build_frame(lora_phy::lora_workspace* ws,
                    const Frame& frame,
                    uint16_t* symbols,
                    size_t symbol_cap) {
    if (!ws || !symbols) return -1;
    std::vector<uint8_t> bytes;
    bytes.reserve(16 + frame.payload.size());
    uint8_t mhdr = (static_cast<uint8_t>(frame.mhdr.mtype) << 5) |
                   (frame.mhdr.major & 0x3);
    bytes.push_back(mhdr);
    uint32_t a = frame.fhdr.devaddr;
    bytes.push_back(static_cast<uint8_t>(a & 0xFF));
    bytes.push_back(static_cast<uint8_t>((a >> 8) & 0xFF));
    bytes.push_back(static_cast<uint8_t>((a >> 16) & 0xFF));
    bytes.push_back(static_cast<uint8_t>((a >> 24) & 0xFF));
    uint8_t fctrl = (frame.fhdr.fctrl & 0xF0) |
                    (static_cast<uint8_t>(frame.fhdr.fopts.size()) & 0x0F);
    bytes.push_back(fctrl);
    bytes.push_back(static_cast<uint8_t>(frame.fhdr.fcnt & 0xFF));
    bytes.push_back(static_cast<uint8_t>((frame.fhdr.fcnt >> 8) & 0xFF));
    bytes.insert(bytes.end(), frame.fhdr.fopts.begin(), frame.fhdr.fopts.end());
    bytes.insert(bytes.end(), frame.payload.begin(), frame.payload.end());
    uint32_t mic = compute_mic(bytes.data(), bytes.size());
    bytes.push_back(static_cast<uint8_t>(mic & 0xFF));
    bytes.push_back(static_cast<uint8_t>((mic >> 8) & 0xFF));
    bytes.push_back(static_cast<uint8_t>((mic >> 16) & 0xFF));
    bytes.push_back(static_cast<uint8_t>((mic >> 24) & 0xFF));
    return lora_phy::encode(ws, bytes.data(), bytes.size(), symbols, symbol_cap);
}

ssize_t parse_frame(lora_phy::lora_workspace* ws,
                    const uint16_t* symbols,
                    size_t symbol_count,
                    Frame& out) {
    if (!ws || !symbols) return -1;
    std::vector<uint8_t> bytes(symbol_count / 2 + 8);
    ssize_t produced = lora_phy::decode(ws, symbols, symbol_count,
                                        bytes.data(), bytes.size());
    if (produced < 0) return produced;
    if (static_cast<size_t>(produced) < 1 + 4 + 1 + 2 + 4) return -1;
    size_t len = static_cast<size_t>(produced);
    uint32_t mic = bytes[len - 4] | (bytes[len - 3] << 8) |
                   (bytes[len - 2] << 16) | (bytes[len - 1] << 24);
    uint32_t calc = compute_mic(bytes.data(), len - 4);
    if (mic != calc) return -2;
    size_t idx = 0;
    uint8_t mhdr = bytes[idx++];
    out.mhdr.mtype = static_cast<MType>(mhdr >> 5);
    out.mhdr.major = mhdr & 0x3;
    out.fhdr.devaddr = bytes[idx] | (bytes[idx + 1] << 8) |
                       (bytes[idx + 2] << 16) | (bytes[idx + 3] << 24);
    idx += 4;
    out.fhdr.fctrl = bytes[idx++];
    unsigned fopts_len = out.fhdr.fctrl & 0x0F;
    out.fhdr.fcnt = bytes[idx] | (bytes[idx + 1] << 8);
    idx += 2;
    if (idx + fopts_len > len - 4) return -1;
    out.fhdr.fopts.assign(bytes.begin() + idx, bytes.begin() + idx + fopts_len);
    idx += fopts_len;
    out.payload.assign(bytes.begin() + idx, bytes.begin() + (len - 4));
    return static_cast<ssize_t>(out.payload.size());
}

} // namespace lorawan

