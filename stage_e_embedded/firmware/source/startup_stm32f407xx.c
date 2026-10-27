#include <stdint.h>

extern uint32_t _estack;
extern uint32_t _sidata;
extern uint32_t _sdata;
extern uint32_t _edata;
extern uint32_t _sbss;
extern uint32_t _ebss;

extern int main(void);

void Reset_Handler(void);
void Default_Handler(void) {
    while (1);
}

/* Cortex-M4 Core Exception Handlers (weak aliases) */
void NMI_Handler(void)        __attribute__((weak, alias("Default_Handler")));
void HardFault_Handler(void)  __attribute__((weak, alias("Default_Handler")));
void MemManage_Handler(void)  __attribute__((weak, alias("Default_Handler")));
void BusFault_Handler(void)   __attribute__((weak, alias("Default_Handler")));
void UsageFault_Handler(void) __attribute__((weak, alias("Default_Handler")));
void SVC_Handler(void)        __attribute__((weak, alias("Default_Handler")));
void DebugMon_Handler(void)   __attribute__((weak, alias("Default_Handler")));
void PendSV_Handler(void)     __attribute__((weak, alias("Default_Handler")));
void SysTick_Handler(void)    __attribute__((weak, alias("Default_Handler")));

/* Vector table placed into .isr_vector section */
__attribute__((section(".isr_vector"), used))
const uint32_t *g_pfnVectors[] = {
    &_estack,
    (uint32_t *)Reset_Handler,
    (uint32_t *)NMI_Handler,
    (uint32_t *)HardFault_Handler,
    (uint32_t *)MemManage_Handler,
    (uint32_t *)BusFault_Handler,
    (uint32_t *)UsageFault_Handler,
    0, 0, 0, 0,
    (uint32_t *)SVC_Handler,
    (uint32_t *)DebugMon_Handler,
    0,
    (uint32_t *)PendSV_Handler,
    (uint32_t *)SysTick_Handler,
};

void Reset_Handler(void) {
    /* Copy data segment initializers from Flash to SRAM */
    uint32_t *src = &_sidata;
    uint32_t *dst = &_sdata;
    while (dst < &_edata) {
        *dst++ = *src++;
    }

    /* Zero-fill BSS segment in SRAM */
    dst = &_sbss;
    while (dst < &_ebss) {
        *dst++ = 0;
    }

    /* Enable FPU coprocessor on Cortex-M4F (CP10 and CP11 Full Access) */
    #define SCB_CPACR (*((volatile uint32_t *)0xE000ED88UL))
    SCB_CPACR |= ((3UL << (10 * 2)) | (3UL << (11 * 2)));
    __asm__ volatile ("dsb 0xf" ::: "memory");
    __asm__ volatile ("isb 0xf" ::: "memory");

    /* Call application main */
    main();

    /* Infinite loop if main ever returns */
    while (1);
}
