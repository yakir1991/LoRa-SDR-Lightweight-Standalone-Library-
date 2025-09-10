#include <cstdio>

int bit_exact_test_main();
int e2e_chain_test_main();
int no_alloc_test_main();
int gr_lora_sdr_interop_main();

int main() {
    int result = 0;
    int r;
    r = bit_exact_test_main();
    result |= r;
    if (r) std::printf("bit_exact_test failed\n");
    r = e2e_chain_test_main();
    result |= r;
    if (r) std::printf("e2e_chain_test failed\n");
    r = no_alloc_test_main();
    result |= r;
    if (r) std::printf("no_alloc_test failed\n");
    r = gr_lora_sdr_interop_main();
    result |= r;
    if (r) std::printf("gr_lora_sdr_interop_test failed\n");
    if (result != 0) {
        std::printf("Some tests failed\n");
    }
    return result;
}
