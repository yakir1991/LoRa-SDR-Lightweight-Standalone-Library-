#include <cstdio>

int bit_exact_test_main();
int e2e_chain_test_main();
int no_alloc_test_main();
int performance_test_main();

int main() {
    int result = 0;
    result |= bit_exact_test_main();
    result |= e2e_chain_test_main();
    result |= no_alloc_test_main();
    result |= performance_test_main();
    if (result != 0) {
        std::printf("Some tests failed\n");
    }
    return result;
}
