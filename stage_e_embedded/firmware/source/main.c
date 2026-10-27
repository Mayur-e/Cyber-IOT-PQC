#include <stdio.h>
#include <string.h>
#include <stdbool.h>

#include "dwt_cycles.h"
#include "stack_watermark.h"
#include "uart_telemetry.h"
#include "crypto_m4_api.h"

/* Verified platform configuration constants */
#define SYSTEM_CLOCK_HZ        168000000UL /* 168 MHz PLL clock for STM32F407 */
#define BENCHMARK_BOARD        "STM32F407G-DISC1"
#define BENCHMARK_MCU          "STM32F407VG"
#define BENCHMARK_DEVICE       "arm_cortex_m4"
#define BENCHMARK_COMPILER     "arm-none-eabi-gcc 12.2.1"
#define BENCHMARK_OPT          "-O3"
#define BENCHMARK_METHOD       "dwt_cyccnt"
#define NUM_TRIALS             10

/* Buffer for stack watermarking (32 KiB test stack buffer) */
static uint32_t s_stack_arena[8192];

/* Static working buffers for cryptographic operations */
static uint8_t kem_pk[MLKEM768_PUBLICKEYBYTES];
static uint8_t kem_sk[MLKEM768_SECRETKEYBYTES];
static uint8_t kem_ct[MLKEM768_CIPHERTEXTBYTES];
static uint8_t kem_ss_a[MLKEM768_SSBYTES];
static uint8_t kem_ss_b[MLKEM768_SSBYTES];

static uint8_t dsa_pk[MLDSA65_PUBLICKEYBYTES];
static uint8_t dsa_sk[MLDSA65_SECRETKEYBYTES];
static uint8_t dsa_sig[MLDSA65_SIGBYTES];
static size_t  dsa_siglen = 0;

static uint8_t x25519_pk_a[X25519_KEYBYTES];
static uint8_t x25519_sk_a[X25519_KEYBYTES];
static uint8_t x25519_pk_b[X25519_KEYBYTES];
static uint8_t x25519_sk_b[X25519_KEYBYTES];
static uint8_t x25519_ss_a[X25519_SSBYTES];
static uint8_t x25519_ss_b[X25519_SSBYTES];

static uint8_t ecdsa_pk[ECDSA_P256_PUBLICKEYBYTES];
static uint8_t ecdsa_sk[ECDSA_P256_SECRETKEYBYTES];
static uint8_t ecdsa_sig[ECDSA_P256_SIGBYTES];
static size_t  ecdsa_siglen = 0;

static const uint8_t TEST_MESSAGE[] = "PQC-Benchmark-Protocol-Test-Message-Stage-E-Cortex-M4";
#define TEST_MESSAGE_LEN (sizeof(TEST_MESSAGE) - 1)

/* Weak cryptographic stubs for standalone compilation verification
 * In full build, these symbols link to pqm4 m4f assembly or mbedtls/micro-ecc */
__attribute__((weak)) int crypto_kem_keypair_mlkem768(uint8_t *pk, uint8_t *sk) {
    memset(pk, 0x11, MLKEM768_PUBLICKEYBYTES);
    memset(sk, 0x22, MLKEM768_SECRETKEYBYTES);
    return 0;
}
__attribute__((weak)) int crypto_kem_enc_mlkem768(uint8_t *ct, uint8_t *ss, const uint8_t *pk) {
    (void)pk;
    memset(ct, 0x33, MLKEM768_CIPHERTEXTBYTES);
    memset(ss, 0x44, MLKEM768_SSBYTES);
    return 0;
}
__attribute__((weak)) int crypto_kem_dec_mlkem768(uint8_t *ss, const uint8_t *ct, const uint8_t *sk) {
    (void)ct; (void)sk;
    memset(ss, 0x44, MLKEM768_SSBYTES);
    return 0;
}

__attribute__((weak)) int crypto_sign_keypair_mldsa65(uint8_t *pk, uint8_t *sk) {
    memset(pk, 0x55, MLDSA65_PUBLICKEYBYTES);
    memset(sk, 0x66, MLDSA65_SECRETKEYBYTES);
    return 0;
}
__attribute__((weak)) int crypto_sign_mldsa65(uint8_t *sig, size_t *siglen, const uint8_t *m, size_t mlen, const uint8_t *sk) {
    (void)m; (void)mlen; (void)sk;
    memset(sig, 0x77, MLDSA65_SIGBYTES);
    *siglen = MLDSA65_SIGBYTES;
    return 0;
}
__attribute__((weak)) int crypto_sign_verify_mldsa65(const uint8_t *sig, size_t siglen, const uint8_t *m, size_t mlen, const uint8_t *pk) {
    (void)sig; (void)siglen; (void)m; (void)mlen; (void)pk;
    return 0;
}

__attribute__((weak)) int crypto_x25519_keypair(uint8_t *pk, uint8_t *sk) {
    memset(pk, 0x88, X25519_KEYBYTES);
    memset(sk, 0x99, X25519_KEYBYTES);
    return 0;
}
__attribute__((weak)) int crypto_x25519_scalarmult(uint8_t *ss, const uint8_t *sk, const uint8_t *pk) {
    (void)sk; (void)pk;
    memset(ss, 0xAA, X25519_SSBYTES);
    return 0;
}

__attribute__((weak)) int crypto_ecdsa_p256_keypair(uint8_t *pk, uint8_t *sk) {
    memset(pk, 0xBB, ECDSA_P256_PUBLICKEYBYTES);
    memset(sk, 0xCC, ECDSA_P256_SECRETKEYBYTES);
    return 0;
}
__attribute__((weak)) int crypto_ecdsa_p256_sign(uint8_t *sig, size_t *siglen, const uint8_t *m, size_t mlen, const uint8_t *sk) {
    (void)m; (void)mlen; (void)sk;
    memset(sig, 0xDD, ECDSA_P256_SIGBYTES);
    *siglen = ECDSA_P256_SIGBYTES;
    return 0;
}
__attribute__((weak)) int crypto_ecdsa_p256_verify(const uint8_t *sig, size_t siglen, const uint8_t *m, size_t mlen, const uint8_t *pk) {
    (void)sig; (void)siglen; (void)m; (void)mlen; (void)pk;
    return 0;
}

static void benchmark_mlkem768(const char *run_id) {
    uint32_t t0, t1, cycles;
    size_t stack_used;
    double us;

    /* Correctness test outside timed region */
    crypto_kem_keypair_mlkem768(kem_pk, kem_sk);
    crypto_kem_enc_mlkem768(kem_ct, kem_ss_a, kem_pk);
    crypto_kem_dec_mlkem768(kem_ss_b, kem_ct, kem_sk);
    bool valid = (memcmp(kem_ss_a, kem_ss_b, MLKEM768_SSBYTES) == 0);

    /* Warmup */
    crypto_kem_keypair_mlkem768(kem_pk, kem_sk);

    for (uint32_t trial = 1; trial <= NUM_TRIALS; trial++) {
        /* Key generation */
        stack_watermark_paint();
        t0 = dwt_get_cycles();
        crypto_kem_keypair_mlkem768(kem_pk, kem_sk);
        t1 = dwt_get_cycles();
        cycles = dwt_elapsed_cycles(t0, t1);
        stack_used = stack_watermark_measure();
        us = dwt_cycles_to_us(cycles, SYSTEM_CLOCK_HZ);
        uart_emit_record(run_id, BENCHMARK_DEVICE, BENCHMARK_BOARD, BENCHMARK_MCU,
                         "ML-KEM-768", "keygen", "m4fspeed", "pqm4", "0.1",
                         BENCHMARK_COMPILER, BENCHMARK_OPT, SYSTEM_CLOCK_HZ,
                         BENCHMARK_METHOD, trial, cycles, us, "success", valid, false, stack_used, "");

        /* Encapsulation */
        stack_watermark_paint();
        t0 = dwt_get_cycles();
        crypto_kem_enc_mlkem768(kem_ct, kem_ss_a, kem_pk);
        t1 = dwt_get_cycles();
        cycles = dwt_elapsed_cycles(t0, t1);
        stack_used = stack_watermark_measure();
        us = dwt_cycles_to_us(cycles, SYSTEM_CLOCK_HZ);
        uart_emit_record(run_id, BENCHMARK_DEVICE, BENCHMARK_BOARD, BENCHMARK_MCU,
                         "ML-KEM-768", "encapsulation", "m4fspeed", "pqm4", "0.1",
                         BENCHMARK_COMPILER, BENCHMARK_OPT, SYSTEM_CLOCK_HZ,
                         BENCHMARK_METHOD, trial, cycles, us, "success", valid, false, stack_used, "");

        /* Decapsulation */
        stack_watermark_paint();
        t0 = dwt_get_cycles();
        crypto_kem_dec_mlkem768(kem_ss_b, kem_ct, kem_sk);
        t1 = dwt_get_cycles();
        cycles = dwt_elapsed_cycles(t0, t1);
        stack_used = stack_watermark_measure();
        us = dwt_cycles_to_us(cycles, SYSTEM_CLOCK_HZ);
        valid = (memcmp(kem_ss_a, kem_ss_b, MLKEM768_SSBYTES) == 0);
        uart_emit_record(run_id, BENCHMARK_DEVICE, BENCHMARK_BOARD, BENCHMARK_MCU,
                         "ML-KEM-768", "decapsulation", "m4fspeed", "pqm4", "0.1",
                         BENCHMARK_COMPILER, BENCHMARK_OPT, SYSTEM_CLOCK_HZ,
                         BENCHMARK_METHOD, trial, cycles, us, "success", valid, false, stack_used, "");
    }
}

static void benchmark_mldsa65(const char *run_id) {
    uint32_t t0, t1, cycles;
    size_t stack_used;
    double us;

    /* Correctness test */
    crypto_sign_keypair_mldsa65(dsa_pk, dsa_sk);
    crypto_sign_mldsa65(dsa_sig, &dsa_siglen, TEST_MESSAGE, TEST_MESSAGE_LEN, dsa_sk);
    bool valid = (crypto_sign_verify_mldsa65(dsa_sig, dsa_siglen, TEST_MESSAGE, TEST_MESSAGE_LEN, dsa_pk) == 0);

    /* Warmup */
    crypto_sign_keypair_mldsa65(dsa_pk, dsa_sk);

    for (uint32_t trial = 1; trial <= NUM_TRIALS; trial++) {
        /* Key generation */
        stack_watermark_paint();
        t0 = dwt_get_cycles();
        crypto_sign_keypair_mldsa65(dsa_pk, dsa_sk);
        t1 = dwt_get_cycles();
        cycles = dwt_elapsed_cycles(t0, t1);
        stack_used = stack_watermark_measure();
        us = dwt_cycles_to_us(cycles, SYSTEM_CLOCK_HZ);
        uart_emit_record(run_id, BENCHMARK_DEVICE, BENCHMARK_BOARD, BENCHMARK_MCU,
                         "ML-DSA-65", "keygen", "m4f", "pqm4", "0.1",
                         BENCHMARK_COMPILER, BENCHMARK_OPT, SYSTEM_CLOCK_HZ,
                         BENCHMARK_METHOD, trial, cycles, us, "success", valid, false, stack_used, "");

        /* Signing */
        stack_watermark_paint();
        t0 = dwt_get_cycles();
        crypto_sign_mldsa65(dsa_sig, &dsa_siglen, TEST_MESSAGE, TEST_MESSAGE_LEN, dsa_sk);
        t1 = dwt_get_cycles();
        cycles = dwt_elapsed_cycles(t0, t1);
        stack_used = stack_watermark_measure();
        us = dwt_cycles_to_us(cycles, SYSTEM_CLOCK_HZ);
        uart_emit_record(run_id, BENCHMARK_DEVICE, BENCHMARK_BOARD, BENCHMARK_MCU,
                         "ML-DSA-65", "sign", "m4f", "pqm4", "0.1",
                         BENCHMARK_COMPILER, BENCHMARK_OPT, SYSTEM_CLOCK_HZ,
                         BENCHMARK_METHOD, trial, cycles, us, "success", valid, false, stack_used, "");

        /* Verification */
        stack_watermark_paint();
        t0 = dwt_get_cycles();
        int vret = crypto_sign_verify_mldsa65(dsa_sig, dsa_siglen, TEST_MESSAGE, TEST_MESSAGE_LEN, dsa_pk);
        t1 = dwt_get_cycles();
        cycles = dwt_elapsed_cycles(t0, t1);
        stack_used = stack_watermark_measure();
        us = dwt_cycles_to_us(cycles, SYSTEM_CLOCK_HZ);
        valid = (vret == 0);
        uart_emit_record(run_id, BENCHMARK_DEVICE, BENCHMARK_BOARD, BENCHMARK_MCU,
                         "ML-DSA-65", "verify", "m4f", "pqm4", "0.1",
                         BENCHMARK_COMPILER, BENCHMARK_OPT, SYSTEM_CLOCK_HZ,
                         BENCHMARK_METHOD, trial, cycles, us, "success", valid, false, stack_used, "");
    }
}

static void benchmark_x25519(const char *run_id) {
    uint32_t t0, t1, cycles;
    size_t stack_used;
    double us;

    /* Correctness test */
    crypto_x25519_keypair(x25519_pk_a, x25519_sk_a);
    crypto_x25519_keypair(x25519_pk_b, x25519_sk_b);
    crypto_x25519_scalarmult(x25519_ss_a, x25519_sk_a, x25519_pk_b);
    crypto_x25519_scalarmult(x25519_ss_b, x25519_sk_b, x25519_pk_a);
    bool valid = (memcmp(x25519_ss_a, x25519_ss_b, X25519_SSBYTES) == 0);

    /* Warmup */
    crypto_x25519_keypair(x25519_pk_a, x25519_sk_a);

    for (uint32_t trial = 1; trial <= NUM_TRIALS; trial++) {
        /* Key generation */
        stack_watermark_paint();
        t0 = dwt_get_cycles();
        crypto_x25519_keypair(x25519_pk_a, x25519_sk_a);
        t1 = dwt_get_cycles();
        cycles = dwt_elapsed_cycles(t0, t1);
        stack_used = stack_watermark_measure();
        us = dwt_cycles_to_us(cycles, SYSTEM_CLOCK_HZ);
        uart_emit_record(run_id, BENCHMARK_DEVICE, BENCHMARK_BOARD, BENCHMARK_MCU,
                         "X25519", "keygen", "m4_asm", "cortex-m4-x25519", "1.0",
                         BENCHMARK_COMPILER, BENCHMARK_OPT, SYSTEM_CLOCK_HZ,
                         BENCHMARK_METHOD, trial, cycles, us, "success", valid, false, stack_used, "");

        /* Shared secret derivation */
        stack_watermark_paint();
        t0 = dwt_get_cycles();
        crypto_x25519_scalarmult(x25519_ss_a, x25519_sk_a, x25519_pk_b);
        t1 = dwt_get_cycles();
        cycles = dwt_elapsed_cycles(t0, t1);
        stack_used = stack_watermark_measure();
        us = dwt_cycles_to_us(cycles, SYSTEM_CLOCK_HZ);
        uart_emit_record(run_id, BENCHMARK_DEVICE, BENCHMARK_BOARD, BENCHMARK_MCU,
                         "X25519", "derive", "m4_asm", "cortex-m4-x25519", "1.0",
                         BENCHMARK_COMPILER, BENCHMARK_OPT, SYSTEM_CLOCK_HZ,
                         BENCHMARK_METHOD, trial, cycles, us, "success", valid, false, stack_used, "");
    }
}

static void benchmark_ecdsa_p256(const char *run_id) {
    uint32_t t0, t1, cycles;
    size_t stack_used;
    double us;

    /* Correctness test */
    crypto_ecdsa_p256_keypair(ecdsa_pk, ecdsa_sk);
    crypto_ecdsa_p256_sign(ecdsa_sig, &ecdsa_siglen, TEST_MESSAGE, TEST_MESSAGE_LEN, ecdsa_sk);
    bool valid = (crypto_ecdsa_p256_verify(ecdsa_sig, ecdsa_siglen, TEST_MESSAGE, TEST_MESSAGE_LEN, ecdsa_pk) == 0);

    /* Warmup */
    crypto_ecdsa_p256_keypair(ecdsa_pk, ecdsa_sk);

    for (uint32_t trial = 1; trial <= NUM_TRIALS; trial++) {
        /* Key generation */
        stack_watermark_paint();
        t0 = dwt_get_cycles();
        crypto_ecdsa_p256_keypair(ecdsa_pk, ecdsa_sk);
        t1 = dwt_get_cycles();
        cycles = dwt_elapsed_cycles(t0, t1);
        stack_used = stack_watermark_measure();
        us = dwt_cycles_to_us(cycles, SYSTEM_CLOCK_HZ);
        uart_emit_record(run_id, BENCHMARK_DEVICE, BENCHMARK_BOARD, BENCHMARK_MCU,
                         "ECDSA_P256", "keygen", "micro_ecc_m4", "micro-ecc", "1.0",
                         BENCHMARK_COMPILER, BENCHMARK_OPT, SYSTEM_CLOCK_HZ,
                         BENCHMARK_METHOD, trial, cycles, us, "success", valid, false, stack_used, "");

        /* Signing */
        stack_watermark_paint();
        t0 = dwt_get_cycles();
        crypto_ecdsa_p256_sign(ecdsa_sig, &ecdsa_siglen, TEST_MESSAGE, TEST_MESSAGE_LEN, ecdsa_sk);
        t1 = dwt_get_cycles();
        cycles = dwt_elapsed_cycles(t0, t1);
        stack_used = stack_watermark_measure();
        us = dwt_cycles_to_us(cycles, SYSTEM_CLOCK_HZ);
        uart_emit_record(run_id, BENCHMARK_DEVICE, BENCHMARK_BOARD, BENCHMARK_MCU,
                         "ECDSA_P256", "sign", "micro_ecc_m4", "micro-ecc", "1.0",
                         BENCHMARK_COMPILER, BENCHMARK_OPT, SYSTEM_CLOCK_HZ,
                         BENCHMARK_METHOD, trial, cycles, us, "success", valid, false, stack_used, "");

        /* Verification */
        stack_watermark_paint();
        t0 = dwt_get_cycles();
        int vret = crypto_ecdsa_p256_verify(ecdsa_sig, ecdsa_siglen, TEST_MESSAGE, TEST_MESSAGE_LEN, ecdsa_pk);
        t1 = dwt_get_cycles();
        cycles = dwt_elapsed_cycles(t0, t1);
        stack_used = stack_watermark_measure();
        us = dwt_cycles_to_us(cycles, SYSTEM_CLOCK_HZ);
        valid = (vret == 0);
        uart_emit_record(run_id, BENCHMARK_DEVICE, BENCHMARK_BOARD, BENCHMARK_MCU,
                         "ECDSA_P256", "verify", "micro_ecc_m4", "micro-ecc", "1.0",
                         BENCHMARK_COMPILER, BENCHMARK_OPT, SYSTEM_CLOCK_HZ,
                         BENCHMARK_METHOD, trial, cycles, us, "success", valid, false, stack_used, "");
    }
}

int main(void) {
    /* Initialize peripherals */
    uart_telemetry_init(115200);
    dwt_init();
    stack_watermark_init(s_stack_arena, sizeof(s_stack_arena));

    /* Measure and report timer overhead */
    uint32_t timer_overhead = dwt_measure_overhead();

    uart_send_str("\r\n======================================================\r\n");
    uart_send_str("STAGE E: ARM CORTEX-M4 EMBEDDED BENCHMARK HARNESS\r\n");
    uart_send_str("Target: STM32F407VG | 168 MHz | DWT Cycle Counter\r\n");
    uart_send_str("======================================================\r\n");

    char banner[128];
    snprintf(banner, sizeof(banner), "Baseline timer overhead: %lu cycles\r\n", (unsigned long)timer_overhead);
    uart_send_str(banner);

    /* Emit CSV header */
    uart_emit_csv_header();

    const char *run_id = "EXP_STAGE_E_STM32F4_SAMPLE";

    /* Run benchmarks across all four schemes */
    benchmark_mlkem768(run_id);
    benchmark_mldsa65(run_id);
    benchmark_x25519(run_id);
    benchmark_ecdsa_p256(run_id);

    uart_send_str("### BENCHMARK COMPLETE ###\r\n");

    while (1) {
        /* Idle spin */
    }

    return 0;
}
