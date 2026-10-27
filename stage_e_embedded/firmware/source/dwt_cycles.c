#include "dwt_cycles.h"

#if defined(__arm__) && (defined(__ARM_ARCH_7EM__) || defined(__ARM_ARCH_7M__))
/* CMSIS or hardware register direct access on ARM Cortex-M3/M4 */
#if __has_include("core_cm4.h")
#include "core_cm4.h"
#else
/* Direct register addresses for ARMv7E-M CoreDebug and DWT */
#define CORE_DEBUG_DEMCR (*((volatile uint32_t *)0xE000EDFCUL))
#define CORE_DEBUG_DEMCR_TRCENA (1UL << 24)

#define DWT_CTRL         (*((volatile uint32_t *)0xE0001000UL))
#define DWT_CTRL_CYCCNTENA (1UL << 0)

#define DWT_CYCCNT       (*((volatile uint32_t *)0xE0001004UL))
#endif

void dwt_init(void) {
#if defined(CoreDebug) && defined(DWT)
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CYCCNT = 0;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
#else
    CORE_DEBUG_DEMCR |= CORE_DEBUG_DEMCR_TRCENA;
    DWT_CYCCNT = 0;
    DWT_CTRL |= DWT_CTRL_CYCCNTENA;
#endif
    __asm__ volatile ("dsb 0xf" ::: "memory");
    __asm__ volatile ("isb 0xf" ::: "memory");
}

uint32_t dwt_get_cycles(void) {
    __asm__ volatile ("dsb 0xf" ::: "memory");
    __asm__ volatile ("isb 0xf" ::: "memory");
#if defined(DWT)
    return DWT->CYCCNT;
#else
    return DWT_CYCCNT;
#endif
}

#else
/* Fallback / Mock implementation for host compilation / unit testing */
static uint32_t mock_cycles = 0;

void dwt_init(void) {
    mock_cycles = 0;
}

uint32_t dwt_get_cycles(void) {
    return mock_cycles++;
}
#endif

uint32_t dwt_elapsed_cycles(uint32_t start, uint32_t end) {
    /* Unsigned subtraction inherently handles single 32-bit wrap-around correctly:
     * (end - start) mod 2^32 */
    return (uint32_t)(end - start);
}

double dwt_cycles_to_us(uint32_t cycles, uint32_t clock_hz) {
    if (clock_hz == 0) {
        return 0.0;
    }
    return ((double)cycles / (double)clock_hz) * 1.0e6;
}

uint32_t dwt_measure_overhead(void) {
    uint32_t t0 = dwt_get_cycles();
    uint32_t t1 = dwt_get_cycles();
    return dwt_elapsed_cycles(t0, t1);
}
