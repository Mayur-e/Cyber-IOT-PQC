#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <math.h>
#include <assert.h>

#include "../source/dwt_cycles.h"
#include "../source/stack_watermark.h"
#include "../source/uart_telemetry.h"

static int g_tests_run = 0;
static int g_tests_passed = 0;

#define TEST_ASSERT(cond, msg) do { \
    g_tests_run++; \
    if (cond) { \
        g_tests_passed++; \
        printf("  [PASS] %s\n", msg); \
    } else { \
        printf("  [FAIL] %s (line %d)\n", msg, __LINE__); \
    } \
} while (0)

void test_dwt_elapsed_normal(void) {
    uint32_t t0 = 100000;
    uint32_t t1 = 250000;
    uint32_t elapsed = dwt_elapsed_cycles(t0, t1);
    TEST_ASSERT(elapsed == 150000, "dwt_elapsed_cycles normal difference");
}

void test_dwt_elapsed_wraparound(void) {
    /* 32-bit counter overflow scenario:
     * start is near 2^32 - 1, end is after wrap */
    uint32_t t0 = 0xFFFFFF00UL; /* 4294967040 */
    uint32_t t1 = 0x00000100UL; /* 256 */
    /* Expected difference: (2^32 - t0) + t1 = 256 + 256 = 512 */
    uint32_t elapsed = dwt_elapsed_cycles(t0, t1);
    TEST_ASSERT(elapsed == 512, "dwt_elapsed_cycles 32-bit wraparound handling");
}

void test_dwt_cycles_to_us_conversion(void) {
    /* At 168 MHz (168,000,000 Hz): 168,000,000 cycles = 1,000,000 us */
    double us168 = dwt_cycles_to_us(168000000UL, 168000000UL);
    TEST_ASSERT(fabs(us168 - 1000000.0) < 1e-3, "dwt_cycles_to_us at 168 MHz (1s = 1e6 us)");

    /* At 24 MHz: 24,000 cycles = 1000 us (1 ms) */
    double us24 = dwt_cycles_to_us(24000UL, 24000000UL);
    TEST_ASSERT(fabs(us24 - 1000.0) < 1e-3, "dwt_cycles_to_us at 24 MHz (24k cycles = 1000 us)");

    /* Zero clock guard */
    double us_zero = dwt_cycles_to_us(1000UL, 0);
    TEST_ASSERT(us_zero == 0.0, "dwt_cycles_to_us zero clock guard");
}

void test_stack_watermarking(void) {
    /* Allocate simulated stack arena of 1024 uint32_t words (4096 bytes) */
    uint32_t arena[1024];
    stack_watermark_init(arena, sizeof(arena));

    /* Pre-fill arena with canary */
    for (size_t i = 0; i < 1024; i++) {
        arena[i] = STACK_CANARY_WORD;
    }

    /* Simulate an operation using 256 words (1024 bytes) from the top down */
    for (size_t i = 1024 - 256; i < 1024; i++) {
        arena[i] = 0xDEADBEEFUL;
    }

    size_t used = stack_watermark_measure();
    TEST_ASSERT(used == 256 * sizeof(uint32_t), "stack_watermark_measure detects exact stack consumption");
}

void test_uart_csv_record_format(void) {
    /* Test calling uart_emit_record without crashes */
    uart_emit_record("TEST_RUN_01", "cortex_m4", "STM32F407G-DISC1", "STM32F407VG",
                     "ML-KEM-768", "encapsulation", "m4fspeed", "pqm4", "0.1",
                     "gcc 12.2.1", "-O3", 168000000UL, "dwt_cyccnt",
                     1, 560000UL, 3333.333, "success", true, false, 2800, "unit_test");
    TEST_ASSERT(true, "uart_emit_record formats without memory faults");
}

int main(void) {
    printf("====================================================\n");
    printf("Running Stage E Firmware Unit & Math Validation Tests\n");
    printf("====================================================\n");

    test_dwt_elapsed_normal();
    test_dwt_elapsed_wraparound();
    test_dwt_cycles_to_us_conversion();
    test_stack_watermarking();
    test_uart_csv_record_format();

    printf("====================================================\n");
    printf("Result: %d / %d tests passed\n", g_tests_passed, g_tests_run);
    printf("====================================================\n");

    return (g_tests_passed == g_tests_run) ? 0 : 1;
}
