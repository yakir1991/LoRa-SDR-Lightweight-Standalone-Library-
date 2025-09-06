#pragma once
#include <atomic>
#include <cstddef>
#include <cstdlib>
#include <new>

namespace alloc_tracker {

inline std::atomic<std::size_t>& counter() {
    static std::atomic<std::size_t> c{0};
    return c;
}

inline void reset() {
    counter().store(0, std::memory_order_relaxed);
}

inline std::size_t get() {
    return counter().load(std::memory_order_relaxed);
}

struct Guard {
    Guard() { reset(); }
    ~Guard() = default;
    std::size_t count() const { return get(); }
};

} // namespace alloc_tracker

inline void* operator new(std::size_t size) {
    alloc_tracker::counter().fetch_add(1, std::memory_order_relaxed);
    if (void* p = std::malloc(size)) return p;
    throw std::bad_alloc();
}

inline void operator delete(void* ptr) noexcept {
    std::free(ptr);
}

inline void* operator new[](std::size_t size) {
    alloc_tracker::counter().fetch_add(1, std::memory_order_relaxed);
    if (void* p = std::malloc(size)) return p;
    throw std::bad_alloc();
}

inline void operator delete[](void* ptr) noexcept {
    std::free(ptr);
}
