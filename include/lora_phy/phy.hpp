/**
 * @file phy.hpp
 * Public facing API for the lightweight LoRa PHY.  All routines operate on a
 * caller supplied workspace that owns every buffer required by the modem.  The
 * library never allocates or frees memory on its own; callers retain ownership
 * of all buffers and plans for the duration of their use.
 */
#pragma once

#include <cstddef>
#include <cstdint>
#include <complex>
#include <sys/types.h>

#include <lora_phy/kissfft.hh>

namespace lora_phy {

// ---------------------------------------------------------------------------
// Helper structures
// ---------------------------------------------------------------------------

/**
 * Configuration parameters controlling modulation and coding options.  The
 * caller retains ownership of this structure; the library copies the values at
 * initialisation time.
 */
struct lora_params {
    unsigned sf{}; ///< Spreading factor
    unsigned bw{}; ///< Bandwidth index
    unsigned cr{}; ///< Coding rate index
};

/**
 * Metrics collected during demodulation/decoding.  The returned pointer from
 * get_last_metrics() refers to this structure inside the workspace and remains
 * valid until the next call that updates it.
 */
struct lora_metrics {
    bool  crc_ok{};      ///< true when last block passed CRC
    float cfo{};         ///< estimated carrier frequency offset
    float time_offset{}; ///< estimated timing offset
};

/**
 * Runtime workspace owned by the caller.  All buffers referenced here must be
 * preallocated by the caller before calling init().  The library reads or
 * writes to these buffers only for the duration of the call and never frees or
 * reallocates them.
 */
struct lora_workspace {
    uint16_t*            symbol_buf{}; ///< N entries
    std::complex<float>* fft_in{};     ///< N complex samples
    std::complex<float>* fft_out{};    ///< N complex samples

    kissfft_plan<float>  plan_fwd{};   ///< forward FFT plan
    kissfft_plan<float>  plan_inv{};   ///< inverse FFT plan

    lora_metrics         metrics{};    ///< updated by processing functions
};

// ---------------------------------------------------------------------------
// High level API
// ---------------------------------------------------------------------------

/** Initialise the workspace for a given parameter set.  Returns 0 on success
 * or -EINVAL when parameters are invalid.  The workspace and the buffers it
 * references are owned by the caller and must remain valid for subsequent
 * calls. */
int init(lora_workspace* ws, const lora_params* cfg);

/** Reset runtime counters and metric fields in @p ws without touching the
 * caller supplied buffers or FFT plans. */
void reset(lora_workspace* ws);

/** Encode @p payload into @p symbols.  @p symbols must point to a caller
 * provided buffer of at least @p symbol_cap entries.  Returns the number of
 * symbols written or -ERANGE if the buffer is too small. */
ssize_t encode(lora_workspace* ws,
               const uint8_t* payload, size_t payload_len,
               uint16_t* symbols, size_t symbol_cap);

/** Decode @p symbols into the caller provided @p payload buffer.  The buffer
 * must have space for @p payload_cap bytes.  Returns bytes written or a
 * negative error code on failure. */
ssize_t decode(lora_workspace* ws,
               const uint16_t* symbols, size_t symbol_count,
               uint8_t* payload, size_t payload_cap);

/** Modulate symbols into complex baseband samples.  @p iq must reference a
 * buffer with capacity for @p symbol_count * (1<<sf) samples.  The function
 * returns the number of samples produced or -ERANGE if @p iq_cap is
 * insufficient. */
ssize_t modulate(lora_workspace* ws,
                 const uint16_t* symbols, size_t symbol_count,
                 std::complex<float>* iq, size_t iq_cap);

/** Demodulate @p iq samples into @p symbols using the FFT plans inside @p ws.
 * The input length must be a multiple of the symbol size.  Returns number of
 * symbols produced or a negative error code. */
ssize_t demodulate(lora_workspace* ws,
                   const std::complex<float>* iq, size_t sample_count,
                   uint16_t* symbols, size_t symbol_cap);

/** Obtain metrics from the last decode or demodulate call.  The returned
 * pointer refers to memory inside @p ws and must not be freed by the caller. */
const lora_metrics* get_last_metrics(const lora_workspace* ws);

// ---------------------------------------------------------------------------
// Legacy helpers
// ---------------------------------------------------------------------------

} // namespace lora_phy

// Forward declaration of the legacy detector in the global namespace.
template <typename T> class LoRaDetector;

namespace lora_phy {

// Workspace used by the demodulator to hold FFT buffers and detector instance.
struct lora_demod_workspace {
    size_t N{};
    std::complex<float>* fft_in{};
    std::complex<float>* fft_out{};
    kissfft_plan<float> fft_plan{}; // preallocated plan for kissfft
    kissfft<float>* fft{};          // fft instance using the plan
    LoRaDetector<float>* detector{};
};

// Initialise and clean up the demodulator workspace.
void lora_demod_init(lora_demod_workspace* ws, unsigned sf);
void lora_demod_free(lora_demod_workspace* ws);

// Modulate an array of symbols into complex baseband samples.
// samples_per_symbol = 1 << sf
size_t lora_modulate(const uint16_t* symbols, size_t symbol_count,
                     std::complex<float>* out_samples, unsigned sf,
                     float amplitude = 1.0f);

// Demodulate complex samples into symbol indices using a prepared workspace.
size_t lora_demodulate(lora_demod_workspace* ws,
                       const std::complex<float>* samples, size_t sample_count,
                       uint16_t* out_symbols);

// Simple Hamming(8,4) based encoder. Each input byte becomes two symbols.
size_t lora_encode(const uint8_t* bytes, size_t byte_count,
                   uint16_t* out_symbols, unsigned sf);

// Decode symbols produced by lora_encode back into bytes.
size_t lora_decode(const uint16_t* symbols, size_t symbol_count,
                   uint8_t* out_bytes);

} // namespace lora_phy

