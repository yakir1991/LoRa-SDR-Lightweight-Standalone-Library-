cmake_minimum_required(VERSION 3.5)
project(lora_phy CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(lora_phy
    src/phy/LoRaMod.cpp
    src/phy/LoRaDemod.cpp
    src/phy/LoRaEncoder.cpp
    src/phy/LoRaDecoder.cpp
)

target_include_directories(lora_phy PUBLIC include)

