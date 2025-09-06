# API Specification

## Workspace

The runtime operates on a caller supplied `lora_workspace` structure.  The
workspace owns all scratch buffers and FFT plans required by the modem.  Buffers
are allocated by the caller before `init()` and handed to the workspace; the
library never performs dynamic memory allocation after initialization.  Typical
fields include symbol and sample buffers, FFT input/output arrays and the
KISS‑FFT plans reused by `demodulate()`.

```
struct lora_workspace {
    /* preallocated by caller */
    uint16_t     *symbol_buf;    /* N entries */
    float complex *fft_in;       /* N samples */
    float complex *fft_out;      /* N samples */

    /* initialized by init() */
    kissfft_plan  plan_fwd;
    kissfft_plan  plan_inv;

    struct lora_metrics metrics; /* updated by processing functions */
};
```

The caller retains ownership of the workspace and the memory referenced by its
pointers.  The library never frees or reallocates these buffers.

## Functions

All routines return `0` on success or a negative error code (`-EINVAL`,
`-ERANGE`, …) on failure unless noted otherwise.  Output functions return the
number of elements written when successful.

### `int init(struct lora_workspace *ws, const struct lora_params *cfg);`
Initializes the workspace for a given set of parameters.

* `ws` – workspace to populate. Must reference valid buffers.
* `cfg` – modulation and coding parameters (spread factor, coding rate, etc.).
* Returns `0` on success or `-EINVAL` if parameters are invalid.

### `void reset(struct lora_workspace *ws);`
Clears runtime counters and metric fields inside `ws` without touching the
preallocated buffers or FFT plans.

### `ssize_t encode(struct lora_workspace *ws,
                     const uint8_t *payload, size_t payload_len,
                     uint16_t *symbols, size_t symbol_cap);`
Encodes a payload into LoRa symbols.

* `payload` – input bytes; caller retains ownership.
* `symbols` – caller provided output buffer with capacity `symbol_cap`.
* Returns number of symbols produced or `-ERANGE` if `symbol_cap` is too small.

### `ssize_t decode(struct lora_workspace *ws,
                     const uint16_t *symbols, size_t symbol_count,
                     uint8_t *payload, size_t payload_cap);`
Decodes a block of symbols into payload bytes.

* `symbols` – input symbol buffer owned by caller.
* `payload` – output buffer supplied by caller.
* Returns number of bytes written or a negative error code on CRC/format error.

### `ssize_t modulate(struct lora_workspace *ws,
                       const uint16_t *symbols, size_t symbol_count,
                       float complex *iq, size_t iq_cap);`
Generates complex time‑domain samples from symbols.

* `symbols` – input symbols.
* `iq` – caller supplied buffer for `symbol_count * (1<<sf)` samples.
* Returns samples written or `-ERANGE` if the buffer is insufficient.

### `ssize_t demodulate(struct lora_workspace *ws,
                         const float complex *iq, size_t sample_count,
                         uint16_t *symbols, size_t symbol_cap);`
Demodulates IQ samples into decided symbols using the workspace FFT plans.

* `iq` – input samples; length must be a multiple of symbol size.
* `symbols` – output buffer for decoded symbols.
* Returns number of symbols produced or negative error on invalid sizes.

### `const struct lora_metrics *get_last_metrics(const struct lora_workspace *ws);`
Returns a pointer to the metrics collected during the most recent processing
call (`decode` or `demodulate`).  The caller must not free the returned pointer
and it remains valid until the next call that updates the metrics.

## Buffer Ownership and Error Handling

All input and output buffers are owned by the caller.  The library reads from or
writes to them only for the duration of the call.  No asynchronous callbacks are
involved; errors are reported solely through return codes.

