cmake_minimum_required(VERSION 3.5)
project(lora_phy LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

file(GLOB LORA_PHY_SOURCES CONFIGURE_DEPENDS src/phy/*.cpp)

add_library(lora_phy STATIC ${LORA_PHY_SOURCES})

target_include_directories(lora_phy PUBLIC include)

# ensure headers like kissfft.hh are part of the target for IDEs
target_sources(lora_phy PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include/lora_phy/kissfft.hh)


add_executable(lora_phy_vector_dump runners/lora_phy_vector_dump.cpp)
target_link_libraries(lora_phy_vector_dump PRIVATE lora_phy)

# Transmit runner producing IQ samples from a hex payload
add_executable(tx_runner runners/tx_runner.cpp)
target_link_libraries(tx_runner PRIVATE lora_phy)

# Receive runner converting IQ samples back into payload bytes
add_executable(rx_runner runners/rx_runner.cpp)
target_link_libraries(rx_runner PRIVATE lora_phy)

# Bit exactness regression test
add_executable(bit_exact_test tests/bit_exact_test.cpp)
target_link_libraries(bit_exact_test PRIVATE lora_phy)

# End-to-end encode/modulate/demodulate test
add_executable(e2e_chain_test tests/e2e_chain_test.cpp)
target_link_libraries(e2e_chain_test PRIVATE lora_phy)

# Allocation tracking test for modulate/demodulate
add_executable(no_alloc_test tests/no_alloc_test.cpp)
target_link_libraries(no_alloc_test PRIVATE lora_phy)

# Performance timing test
add_executable(performance_test tests/performance_test.cpp)
target_link_libraries(performance_test PRIVATE lora_phy)
