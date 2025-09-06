# Porting Plan: LoRa-SDR (MyriadRF) → Lightweight Standalone Library (KISS-FFT)

> **Goal**: Extract the **LoRa PHY core** from LoRa-SDR (originally implemented as **Pothos** blocks) and turn it into a **standalone C/C++ library**, with **KISS-FFT** as the sole FFT backend (as in the original), and **no runtime allocations** in hot paths (init-only).
>
> **Status**: Planning document (no code). Designed for VS Code + WSL2 Ubuntu 22.04 or equivalent Linux environment.

---

## 0) Objectives & Success Criteria

### In Scope (MVP)
- **Modulation / Demodulation** pipeline: **dechirp → FFT → symbol decision**.
- **Coding Layer**: data whitening, interleaving, Hamming (CR 4/5–4/8), Gray mapping, header/payload CRC, sync-word handling.
- **Parameters**: SF7..SF12, BW = 125 kHz (initially), CR = 4/5..4/8, explicit header.

### Success Criteria
- **One library target** with **KISS-FFT only** as dependency.
- **Zero allocations** in hot path (all buffers allocated in **init**).
- **Bit-exact** conformance against reference vectors; BER/PER reports for selected operating points.
- **Small CLI runners** for generating IQ and decoding captured IQ.

---

## 1) Fast Repository Mapping (Scout Pass)

**Goal**: separate core algorithms from Pothos wrappers.

- Identify logical modules:
  - **Encoder / Decoder**, **Mod / Demod**, **Chirp / Detector**, **Utilities** (CRC / Gray / Interleave / Whitening), **FFT** (KISS).
- Tag files that are **Pothos::Block-only** (ports, topology, settings) → **leave behind**.
- Document in `PORTING_NOTES.md` a table: *module → key functions → dependencies → allocation model*.

**Deliverable**: short mapping note + list of files to extract as the new **core**.

---

## 2) Run the Original to Produce Baselines (Behavioral Reference)

**Goal**: preserve a behavioral ground truth.

- Build LoRa-SDR as-is and run the **LoRa simulation** (AWGN).
- Export **vectors** at key boundaries:
  - Symbols after FFT (argmax),
  - Bits after de-interleave/decoding,
  - Payload after de-whitening.
- Freeze runs for configurations such as: **SF7 / SF9 / SF12 × CR 4/5..4/8 × SNR = 10 dB** (example).
- Store outputs under `legacy_vectors/lorasdr_baseline/` with parameter manifests.

**Deliverable**: a signed set of `.bin`/`.csv` vectors + per-vector parameter docs.

---

## 3) Library API Design (No Code)

**Goal**: a **narrow, embedded-friendly** API.

- **Parameter structs**: SF, BW, CR, sync-word, preamble length, OSR (phase 1: OSR = 1).
- **Workspace**: pointers and sizes for internal buffers (chirp tables, windowing tables, FFT plan, scratch for interleaver/coding).
- **Core entry points** (names indicative):
  - `init` (one-time allocation), `reset`,
  - `encode` / `decode` (format-level bits),
  - `modulate` (payload → IQ),
  - `demodulate` (IQ → symbols → bits → payload),
  - `get_last_metrics` (CFO/TO/CRC counters).
- **Memory policy**: all buffers are **caller-provided** or owned by the **workspace**; **no new/malloc** in `modulate` / `demodulate`.

**Deliverable**: `API_SPEC.md` describing function signatures in prose, arguments, buffers, return statuses, and error semantics.

---

## 4) Extract the Core & Remove Pothos Dependencies

**Goal**: decouple logic from graph/plumbing.

- Move algorithms (**mod/demod/coding/chirp/detector**) into `src/phy/` (new library).
- Replace Pothos ports/messages with **flat buffer** APIs and explicit size contracts.
- Keep **KISS-FFT** as the single backend (header-only and/or minimal sources included).

**Deliverable**: a minimal source tree containing only logical modules (no Pothos / Poco / JSON).

---

## 5) Enforce “No Runtime Allocations”

**Goal**: fit embedded/performance constraints.

- Systematic sweep for `new/malloc/resize/push_back` within extracted modules.
- Parameterize sizes in **init** (e.g., `N = 2^SF`, LUT lengths for Gray/Interleave/Hamming).
- Build **immutable** tables once in `init` (e.g., base chirp), keep them in the workspace.

**Deliverable**: a “zero-alloc” checklist + a short PR-style change log of all sites that were modified.

---

## 6) Numeric & Semantic Compatibility

**Goal**: bit-for-bit agreement with the baseline.

- **IQ convention**: amplitude range, order (I,Q), rounding/scaling.
- **Symbol length**: exactly **2^SF** samples per symbol; avoid drift.
- **Dechirp**: verify chirp phase (up/down, start phase) and FFT window placement.
- **Argmax**: define a deterministic tie-break policy.
- **Gray / Interleave / Whitening**: confirm bit mapping (LSB/MSB), chip bit order, whitening polynomial & seed.
- **CRC**: polynomial, endian, initialization.
- **Sync-word**: masking and header mapping exactly as required.

**Deliverable**: “semantic decisions” table + vector updates if any convention is adjusted.

---

## 7) Testing & Verification (Design Only)

**Goal**: a clear and pragmatic test matrix.

- **Bit-exact**: `IQ → payload` comparison vs. LoRa-SDR vectors (for several profiles).
- **E2E Chain**: `payload → IQ → payload` identity in clean conditions (SNR = ∞).
- **BER/PER**: AWGN sweeps for **SF7 / SF9 / SF12** and **CR 4/5, 4/8** (threshold curves).
- **Param coverage**: a minimal but meaningful matrix across **SF / BW / CR**.
- **No-alloc assertions**: logical check (allocator hook/counter) proving **0 allocations** in `modulate` / `demodulate`.
- **Performance logs**: packets-per-second and approximate cycles per symbol; explicit `N = 2^SF` trace.

**Deliverable**: `TEST_PLAN.md` + an automated test scaffold (later), keeping this document code-free.

---

## 8) Small Daily Runners (Spec Only)

**Goal**: practical day-to-day use.

- **tx_runner**: accepts payload (hex) + params; writes float32 IQ file and/or pipes to stdout.
- **rx_runner**: reads IQ (file/pipe); decodes and reports header/payload/CRC/CFO/TO.
- **vector_dump**: utility to export internal states (symbols, pre/post interleave, etc.) for debugging.

**Deliverable**: CLI specifications and file formats (no implementation here).

---

## 9) Project Layout & Build Targets

**Goal**: clearly separate legacy and the new core.

- `external/lorasdr_orig/` — **unmodified** upstream source for reference runs only.
- `src/phy/` — extracted algorithmic core.
- `include/lora_phy/` — public API headers.
- `runners/` — small CLIs.
- `tests/` — tests, vectors, harness scripts.
- `vectors/` — signed inputs/outputs (frozen baselines).
- **CMake**: one static library target, one test target, runner targets.

**Deliverable**: directory layout description, build targets, and compile flags (documented here; no code yet).

---

## 10) Optional RF/DSP Topics (Post-MVP)

- **CFO/TO**: add coarse/fine estimation & compensation (phasor/time-shift) if required.
- **OSR > 1**: oversampling and FFT window alignment.
- **Windows/Filters**: lightweight time-domain window pre-FFT if beneficial.
- **Additional BW**: 250/500 kHz support.
- **LoRaWAN**: use the PHY as a base for LoRaWAN frame building/parsing later on.

---

## 11) Licensing & Code Hygiene

- Confirm KISS-FFT and any included sources are **license-compatible** (e.g., BSD/MIT/Apache) with your project.
- Keep the original LoRa-SDR code under `external/` **untouched**.
- Provide clear credits/origins/changes in `THIRD_PARTY.md`.

**Deliverable**: a green licensing review.

---

## 12) Risks & Pitfalls (Mitigation Upfront)

- **Gray / Interleave bit-ordering** — classic source of 1–2 bit drift under noise.
- **Whitening polynomial/seed** — tiny differences break CRC silently.
- **Windowing / FFT-bin ties** — define a consistent policy for ties.
- **Sync-word endian** — beware LSB-first vs MSB-first conventions.
- **Hidden allocations** — vectors/strings/IO abstractions sneaking into hot paths.
- **IQ normalization** — inconsistent float scaling degrades sensitivity.

---

## 13) Definition of Done (Per Milestone)

- **Baseline**: LoRa-SDR runs archived as signed vectors.
- **Core extracted**: logical modules stand alone; build as a library; no Pothos.
- **No-alloc**: proven sweep—zero allocations in hot paths.
- **Correctness**: bit-exact vs. vectors in ≥ 3 profiles (SF7/9/12 × CR 4/5, 4/8).
- **Performance**: PPS / per-symbol metrics collected; no regressions across runs.
- **Docs**: `API_SPEC.md`, `TEST_PLAN.md`, `PORTING_NOTES.md`, `THIRD_PARTY.md` all completed.

---

### Notes
- “LoRa” is a registered trademark of Semtech. This document refers to interoperable PHY techniques and public research implementations.
- This plan is intentionally **code-free**. It specifies deliverables, structure, and verification gates to keep the port focused and auditable.
