# Stage E: Embedded ARM Cortex-M4 Firmware Architecture

**Project Title:** Empirical Migration Feasibility Analysis of Post-Quantum Cryptography for Resource-Constrained Systems  
**Module:** `stage_e_embedded/firmware`  

---

## 1. Overview & Embedded Target Architecture

This module specifies and houses the embedded firmware harness for evaluating Post-Quantum Cryptography on 32-bit resource-constrained microcontrollers:
- **Target MCU:** STMicroelectronics STM32F407VG (ARM Cortex-M4 with single-precision FPU)
- **Target Board:** STM32F407G-DISC1 / STM32F4 Discovery
- **Instruction Set:** ARMv7E-M with Thumb-2 instruction set and DSP instructions
- **Core Clock:** Configurable up to 168 MHz (verified via PLL clock configuration)
- **Memory Limits:**
  - 192 KiB internal SRAM (128 KiB continuous system RAM + 64 KiB CCM data RAM)
  - 1024 KiB Flash memory for firmware and read-only tables

---

## 2. Hardware Cycle Counting & Timing Discipline

### 2.1 ARM Cortex-M4 DWT Cycle Counter
Timing on Cortex-M4 is measured in clock cycles using the Data Watchpoint and Trace (DWT) cycle counter:
```c
#include <stdint.h>
#include "core_cm4.h"

static inline void cycle_counter_init(void) {
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk; // Enable trace subsystem
    DWT->CYCCNT = 0;                                // Reset cycle counter
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;           // Enable cycle counter
}

static inline uint32_t measure_start(void) {
    __DSB(); // Data Synchronization Barrier
    __ISB(); // Instruction Synchronization Barrier
    return DWT->CYCCNT;
}

static inline uint32_t measure_end(uint32_t start) {
    __DSB();
    __ISB();
    return (uint32_t)(DWT->CYCCNT - start);
}
```

### 2.2 Microsecond Latency Derivation
Elapsed microsecond time is derived from empirical cycle counts ($C$) and verified system clock frequency ($f_\text{Hz}$):
$$t_{\mu s} = \frac{C}{f_\text{Hz}} \times 10^6$$
*Example:* At 168 MHz, 1,000,000 cycles = $\frac{10^6}{168 \times 10^6} \times 10^6 \approx 5,952.4\text{ }\mu\text{s}$ (5.95 ms).

---

## 3. Dynamic Stack Usage Profiling (Stack Painting)

To establish exact SRAM stack requirements without dynamic heap overhead:
1. The stack area is pre-filled with a known sentinel byte pattern (`0x5A5A5A5A`) before calling the target function.
2. The target cryptographic operation is executed.
3. The stack memory is inspected from bottom to top to identify the lowest untouched sentinel byte (high-watermark method).
4. Peak stack consumption = $\text{Stack Base} - \text{Lowest Untouched Sentinel Address}$.

---

## 4. Toolchain & Flashing Requirements

- **Cross Compiler:** `arm-none-eabi-gcc` (version 10.3+ or 12.3+)
- **Size Utility:** `arm-none-eabi-size`
- **Flashing / Debugging:** OpenOCD or `st-flash` (ST-Link v2 / v2-1)
- **Serial Telemetry:** USART2 (115200 baud, 8N1) via PA2 (TX) and PA3 (RX)

---

## 5. Physical vs. Simulated Measurement Rules

1. **Physical Hardware:** Measurements collected from a physical board are saved to `stage_e_embedded/results/stm32f4_physical/`.
2. **Emulated Execution:** In the absence of physical hardware, builds validated via QEMU (`mps2-an386`) are saved to `stage_e_embedded/results/stm32f4_emulated/` and explicitly labelled as simulated.
3. Under no circumstances are emulator results presented as physical hardware measurements.
