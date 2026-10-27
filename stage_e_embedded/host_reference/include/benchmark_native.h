#ifndef BENCHMARK_NATIVE_H
#define BENCHMARK_NATIVE_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <time.h>

#define BENCH_VERSION "1.0.0"
#define TEST_MSG_LEN 64

// High-resolution monotonic timing
static inline uint64_t get_time_ns(void) {
    struct timespec ts;
#if defined(CLOCK_MONOTONIC_RAW)
    clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
#else
    clock_gettime(CLOCK_MONOTONIC, &ts);
#endif
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}

#include "stats.h"

// Benchmark function declarations
int bench_mlkem768(size_t warmups, size_t trials, const char *out_csv, const char *run_id, const char *compiler_info, const char *flags_info);
int bench_mldsa65(size_t warmups, size_t trials, const char *out_csv, const char *run_id, const char *compiler_info, const char *flags_info);
int bench_x25519(size_t warmups, size_t trials, const char *out_csv, const char *run_id, const char *compiler_info, const char *flags_info);
int bench_ecdsa_p256(size_t warmups, size_t trials, const char *out_csv, const char *run_id, const char *compiler_info, const char *flags_info);

#endif // BENCHMARK_NATIVE_H
