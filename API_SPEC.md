# API Specification

## Workspace and Memory Policy
- All blocks use the [Pothos](https://github.com/pothosware/PothosCore) runtime.
- Input and output buffers are managed by `Pothos::BufferManager` and are
  reference-counted. Callers must not free returned buffers.
- Each block allocates internal tables proportional to the spread factor `sf`
  (`N = 1 << sf`). No global state is shared between instances.

## Entry Points

### `/lora/lora_encoder`
- **Factory**: `Pothos::Block* LoRaEncoder::make(void)`
- **Parameters**
  - `sf` – spread factor (bits per symbol).
  - `ppm` – symbol size (≤ `sf`).
  - `cr` – coding rate (`"4/4"`…`"4/8"`).
  - `explicit` – enable explicit header mode.
  - `crc` – append CRC.
  - `whitening` – apply whitening.
- **Buffers**: accepts packet payload of `uint8_t` bytes and produces
  `uint16_t` symbols. Buffers are owned by the runtime.
- **Errors**: invalid coding rate raises `Pothos::InvalidArgumentException`;
  other setters are silent.

### `/lora/lora_mod`
- **Factory**: `Pothos::Block* LoRaMod::make(size_t sf)`
- **Parameters**
  - `sync` – two‑symbol sync word.
  - `padding` – number of zero symbols appended after payload.
  - `ampl` – transmit amplitude.
  - `ovs` – oversampling ratio.
- **Buffers**: consumes packet of `uint16_t` symbols and outputs complex
  samples. Output buffers sized `N * ovs` samples and owned by the runtime.
- **Errors**: `setOvs()` throws `Pothos::InvalidArgumentException` when the
  oversampling ratio is outside `[1,256]`.

### `/lora/lora_demod`
- **Factory**: `Pothos::Block* LoRaDemod::make(size_t sf)`
- **Parameters**
  - `sync` – two‑symbol sync word to match.
  - `thresh` – detector threshold in dB.
  - `mtu` – maximum number of symbols emitted per packet.
- **Buffers**: consumes complex samples and produces packets of demodulated
  `uint16_t` symbols. Additional debug ports (`raw`, `dec`, `fft`) provide
  complex sample buffers for inspection. All buffers are runtime‑owned.
- **Errors**: demodulator emits an `error` signal when synchronization or
  detection fails.

### `/lora/lora_decoder`
- **Factory**: `Pothos::Block* LoRaDecoder::make(void)`
- **Parameters**
  - `sf` – spread factor (bits per symbol).
  - `ppm` – symbol size (≤ `sf`).
  - `cr` – coding rate.
  - `explicit`, `hdr`, `dataLength`, `crcc`, `whitening`, `interleaving`,
    `errorCheck` – control header handling and error checks.
- **Buffers**: accepts packets of `uint16_t` symbols and outputs packets of
  decoded `uint8_t` bytes. Buffers remain owned by the runtime.
- **Errors**: unknown coding rates or failed parameter checks throw
  `Pothos::InvalidArgumentException`. Runtime decoding problems increment the
  dropped‑packet counter and emit a `dropped` signal.

## Supporting Functions

### `LoRaDetector::detect`
`size_t detect(Type &power, Type &powerAvg, Type &fIndex,
               std::complex<Type> *fftOutput = nullptr)`
- Runs an FFT over fed samples and returns the index of the strongest bin.
- `power`, `powerAvg`, and `fIndex` are output parameters.
- When `fftOutput` is `nullptr`, an internal buffer is used.
- No explicit error code; `fIndex` is set to zero when the denominator is
  zero.

## Return Codes and Error Semantics
- Factory functions return a valid `Pothos::Block*` on success.
- Parameter setters return `void`; invalid arguments raise
  `Pothos::InvalidArgumentException`.
- Runtime failures are reported through registered signals (`error`,
  `dropped`).
- The API does not use numeric return codes for errors.

## Buffer Ownership
- Input buffers are consumed by the block; callers should not read after
  consumption.
- Output buffers and packet payloads are owned by the Pothos framework and are
  valid until the next work call posts new data.
- No functions transfer ownership of raw pointers to the caller.
