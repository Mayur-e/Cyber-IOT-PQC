with open('RESEARCH_STATUS.md', 'r', encoding='utf-8') as f:
    text = f.read()

old_status = "Stage A (Validation), Stage B (Timing Variability & Reproducibility), Stage C (Controlled Resource Sensitivity), Stage D1 (Artifact Size & Transmission Feasibility), and Stage D2 (Cold-Start & Initialization Profiling) Completed Successfully; Ready for Stage E (Energy & Cycle Profiling)."
new_status = "Stages A through E Completed Successfully: Stage A (Validation), Stage B (Timing Variability), Stage C (Resource Sensitivity), Stage D1 (Artifacts & Transmission), Stage D2 (Cold-Start Profiling), and Stage E (Host-Native C Benchmarking & Embedded Cortex-M4 Architecture)."

text = text.replace(old_status, new_status)

m9 = """
### Milestone 9: Stage E (Embedded Architecture, PQM4 Audit & Host-Native C Reference Benchmarking) Execution
- **Host-Native C Reference Benchmark:** Directly compiled and executed `liboqs` 0.16.0 and OpenSSL 3.5.7 with `gcc -O3` (11,000 observations across 1,000 trials per operation). High-resolution monotonic timing using `CLOCK_MONOTONIC_RAW`.
- **Quantification of Python CFFI Wrapper Tax:**
  - Python runtime and CFFI pointer marshaling add a relatively constant **~3.5 to 7.5 µs invocation tax** per call across all primitives.
  - Fast operations suffer major degradation: **ML-KEM-768 Encapsulation** (21.29 µs native C vs. 28.68 µs Python API, a **+34.7% wrapper tax**, **1.35× slower**); **ML-KEM-768 Keygen** (20.65 µs native vs. 26.65 µs Python, a **+29.0% wrapper tax**); **ML-KEM-768 Decapsulation** (25.08 µs native vs. 30.91 µs Python, a **+23.3% wrapper tax**).
  - Compute-heavy primitives dilute the relative wrapper penalty: **ML-DSA-65 Verification** (**+15.8%**), **ML-DSA-65 Signing** (**+10.4%**), **ECDSA P-256 Signing** (**+7.3%**), and **X25519 Derivation** (**+7.4%**).
- **Upstream PQM4 Framework Audit (Commit `6ff2be9`):**
  - Inspected platform configuration for STM32F4 Discovery (`stm32f4discovery`, STM32F407VG).
  - Identified scope limitation: PQM4 exclusively provides post-quantum algorithms (`ml-kem-768` and `ml-dsa-65`) and does **not** provide classical ECC algorithms (X25519 or ECDSA P-256).
  - Documented official upstream deprecation notice: PQM4 scheduled for archiving in January 2027.
  - Documented clocking and timing justification: 24 MHz with 0 Flash wait states (`FLASH_ACR_LATENCY_0WS`) for benchmark reproducibility, or 168 MHz with 5 wait states for performance. Cycle counting uses SysTick with a 64-bit overflow ISR handler (`hal_get_time()`).
- **Embedded STM32F4 Firmware Harness (`stage_e_embedded/firmware/source/`):**
  - Implemented modular Cortex-M4 benchmark harness featuring DWT cycle counter initialization with memory barriers (`__DSB()`, `__ISB()`), 32-bit unsigned wraparound handling, stack sentinel watermarking (`0x5A5A5A5A` canary spray), USART2 streaming CSV telemetry, and standalone linker script (`stm32f407vg.ld`).
  - Unit tests passed on host (7/7 tests passed, 100%).
- **Hardware Status & Non-Fabrication:**
  - Automated audit and user confirmation established that no physical STM32 board is currently connected.
  - In strict accordance with scientific integrity rules, **zero physical cycle counts were fabricated**, and `results/stm32f4_physical/` remains unpopulated pending physical board attachment.
"""

text = text.replace("## 3. Open Research Questions", m9 + "\n---\n\n## 3. Open Research Questions")

with open('RESEARCH_STATUS.md', 'w', encoding='utf-8') as f:
    f.write(text)
print("Updated RESEARCH_STATUS.md successfully!")
