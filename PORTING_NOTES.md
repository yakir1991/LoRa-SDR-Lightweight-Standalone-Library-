# Porting Notes

This document summarizes core functions, dependencies, and allocation models for selected modules in the LoRa SDR lightweight library.

| Module | Core Functions | Dependencies | Allocation Model | Notes |
| --- | --- | --- | --- | --- |
| `LoRaMod.cpp` | `LoRaMod::work` | Pothos framework (`Pothos::Block`, `Pothos::BufferChunk`, labels) | Uses `Pothos::BufferChunk` for payload; generates chirps in-place | Pothos block wrapper; no Poco/JSON |
| `LoRaDemod.cpp` | `LoRaDemod::work` | Pothos framework, `LoRaDetector` (FFT via kissfft) | Output via `Pothos::BufferChunk`; uses `std::vector` for chirp tables | Pothos block wrapper; no Poco/JSON |
| `LoRaEncoder.cpp` | `LoRaEncoder::work`, `encodeFec` | Pothos framework, `LoRaCodes.hpp` utilities | `std::vector` for data and symbols; output `Pothos::BufferChunk` | Pothos block wrapper; no Poco/JSON |
| `LoRaDecoder.cpp` | `LoRaDecoder::work`, `drop` | Pothos framework, `LoRaCodes.hpp` | `std::vector` for buffers; output `Pothos::BufferChunk` | Pothos block wrapper; no Poco/JSON |
| `ChirpGenerator.hpp` | `genChirp` | `<complex>`, `<cmath>` (includes `Pothos/Config.hpp` for macros) | Writes to caller-provided buffer; no dynamic allocation | Independent; remove Pothos include if unused |
| `LoRaDetector.hpp` | `feed`, `detect` | `kissfft.hh`, `<vector>` | Internal `std::vector` buffers for FFT | Independent; no external framework |

# Module Inventory

| Module | Files |
| --- | --- |
| Encoder/Decoder | `LoRaEncoder.cpp`, `LoRaDecoder.cpp`, `LoRaCodes.hpp` |
| Mod/Demod | `LoRaMod.cpp`, `LoRaDemod.cpp` |
| Chirp/Detector | `ChirpGenerator.hpp`, `LoRaDetector.hpp` |
| Utilities | `BlockGen.cpp`, `TestCodesSx.cpp`, `TestDetector.cpp`, `TestGen.cpp`, `TestHamming.cpp`, `TestLoopback.cpp` |
| FFT | `kissfft.hh` |

