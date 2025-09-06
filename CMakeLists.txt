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
