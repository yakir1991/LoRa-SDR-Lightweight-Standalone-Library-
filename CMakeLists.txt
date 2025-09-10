cmake_minimum_required(VERSION 3.5)
project(lora_phy LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_compile_options(-Wall -Wextra -Wpedantic -O2)

option(BUILD_TESTS "Build tests" ON)
option(BUILD_RUNNERS "Build runners" ON)

file(GLOB LORA_PHY_SOURCES CONFIGURE_DEPENDS src/phy/*.cpp)

add_library(lora_phy STATIC ${LORA_PHY_SOURCES})

target_include_directories(lora_phy PUBLIC include)

  # ensure headers like kissfft.hh are part of the target for IDEs
  target_sources(lora_phy PUBLIC
      ${CMAKE_CURRENT_SOURCE_DIR}/include/lora_phy/kissfft.hh
  )

# LoRaWAN helper library
file(GLOB LORAWAN_SOURCES CONFIGURE_DEPENDS src/lorawan/*.cpp)
add_library(lorawan STATIC ${LORAWAN_SOURCES})
target_link_libraries(lorawan PUBLIC lora_phy)
target_include_directories(lorawan PUBLIC include)

if(BUILD_RUNNERS)
    add_executable(lora_phy_vector_dump runners/lora_phy_vector_dump.cpp)
    target_link_libraries(lora_phy_vector_dump PRIVATE lora_phy)

    # Transmit runner producing IQ samples from a hex payload
    add_executable(tx_runner runners/tx_runner.cpp)
    target_link_libraries(tx_runner PRIVATE lora_phy)

    # Receive runner converting IQ samples back into payload bytes
    add_executable(rx_runner runners/rx_runner.cpp)
    target_link_libraries(rx_runner PRIVATE lora_phy)

endif()

if(BUILD_TESTS)
    enable_testing()
    include(FetchContent)
    FetchContent_Declare(
      googletest
      URL https://github.com/google/googletest/archive/refs/tags/v1.14.0.zip
    )
    FetchContent_MakeAvailable(googletest)

    file(GLOB TEST_SOURCES CONFIGURE_DEPENDS tests/*.cpp)
    list(REMOVE_ITEM TEST_SOURCES ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_main.cpp)
    list(REMOVE_ITEM TEST_SOURCES ${CMAKE_CURRENT_SOURCE_DIR}/tests/performance_test.cpp)
    list(REMOVE_ITEM TEST_SOURCES ${CMAKE_CURRENT_SOURCE_DIR}/tests/awgn_sweep_gtest.cpp)
    list(REMOVE_ITEM TEST_SOURCES ${CMAKE_CURRENT_SOURCE_DIR}/tests/lorawan_roundtrip_gtest.cpp)

    add_executable(lora_phy_tests tests/test_main.cpp ${TEST_SOURCES})
    target_link_libraries(lora_phy_tests PRIVATE lora_phy)

    foreach(test_src ${TEST_SOURCES})
        get_filename_component(test_name ${test_src} NAME_WE)
        set_source_files_properties(${test_src} PROPERTIES COMPILE_DEFINITIONS "main=${test_name}_main")
    endforeach()

    add_test(NAME lora_phy_tests COMMAND lora_phy_tests)
    set_tests_properties(lora_phy_tests PROPERTIES WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})

    # GoogleTest based tests mirroring Python scripts
    add_executable(lora_gtests
        tests/awgn_sweep_gtest.cpp
        tests/lorawan_roundtrip_gtest.cpp
    )
    target_link_libraries(lora_gtests PRIVATE gtest_main lora_phy lorawan)
    add_test(NAME lora_gtests COMMAND lora_gtests)
    set_tests_properties(lora_gtests PROPERTIES WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})
endif()
