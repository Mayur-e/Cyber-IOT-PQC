#ifndef DWT_CYCLES_H
#define DWT_CYCLES_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Initialize the Cortex-M4 DWT (Data Watchpoint and Trace) cycle counter.
 * Enables trace subsystem in CoreDebug and cycle counter in DWT->CTRL.
 */
void dwt_init(void);

/**
 * @brief Capture current cycle counter with instruction & data synchronization barriers.
 * @return uint32_t current DWT->CYCCNT value.
 */
uint32_t dwt_get_cycles(void);

/**
 * @brief Calculate elapsed cycles between start and end, accounting for 32-bit unsigned wraparound.
 * @param start Cycle count at start.
 * @param end Cycle count at end.
 * @return uint32_t elapsed cycles (modulo 2^32).
 */
uint32_t dwt_elapsed_cycles(uint32_t start, uint32_t end);

/**
 * @brief Convert cycle count to elapsed microseconds using verified clock frequency.
 * Formula: t_us = (cycles / clock_hz) * 1e6
 * @param cycles Number of clock cycles.
 * @param clock_hz System clock frequency in Hertz (e.g., 168000000 or 24000000).
 * @return double elapsed microseconds.
 */
double dwt_cycles_to_us(uint32_t cycles, uint32_t clock_hz);

/**
 * @brief Measure the baseline overhead of calling dwt_get_cycles() twice in sequence.
 * @return uint32_t baseline timer overhead in cycles.
 */
uint32_t dwt_measure_overhead(void);

#ifdef __cplusplus
}
#endif

#endif /* DWT_CYCLES_H */
