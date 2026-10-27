# Research Status: Post-Quantum Cryptography Migration Feasibility

**Project Title:** Empirical Migration Feasibility Analysis of Post-Quantum Cryptography for Resource-Constrained Systems  
**Date:** 2026-10-26  
**Status:** Stages A through E Completed Successfully: Stage A (Validation), Stage B (Timing Variability), Stage C (Resource Sensitivity), Stage D1 (Artifacts & Transmission), Stage D2 (Cold-Start Profiling), and Stage E (Host-Native C Benchmarking & Embedded Cortex-M4 Architecture).

---

## 1. Executive Summary

This project investigates the empirical feasibility of migrating resource-constrained systems from classical public-key cryptography (X25519 key agreement, ECDSA P-256 digital signatures) to post-quantum cryptography standards (ML-KEM-768 key encapsulation, ML-DSA-65 digital signatures, standardized in NIST FIPS 203 and 204).

Execution takes place in a controlled Linux container (`pqc-bench:1.0`, Ubuntu/Debian base with liboqs 0.16.0, Python 3.12.15, cryptography 50.0.2, OpenSSL 3.5.7) hosted via Docker Desktop on Windows 11 with WSL2 (Kernel 6.6.114.1, Cgroup v2) on an AMD Ryzen 7 7435HS processor (8 physical cores, 16 logical threads, 3.1 GHz base clock).

---

## 2. Completed Milestones

### Milestone 1: Historical Data Preservation & Repository Audit
- **Integrity Inventory:** All 6 historical result sets (`results_cpu1_mem3`, `results_cpu1_mem512`, `results_cpu1_mem512_n1000_run1`, `run2`, `run3`, `results_cpu2_mem3`) were cataloged with SHA-256 hashes.
- **Data Immutability:** Strict data preservation enforced; 100% of historical files remain untouched.
- **Docker Environment Audit:** Verified `docker info`, image `pqc-bench:1.0`, and active cgroup v2 support.

### Milestone 2: Root-Cause Investigation of the ML-KEM-768 Timing Anomaly
- **Anomaly Context:** Historical Run 3 exhibited ML-KEM median timings elevated from ~26–29 µs to ~47–50 µs for 800 trials before dropping sharply to 26 µs.
- **Findings:**
  1. *Uniform Slowdown Ratio:* Keygen, encap, and decap all scaled by ~1.80×.
  2. *Discrete Transition Point:* Transition occurred between trial 794 and 815 within an 8.5 ms wall-clock window.
  3. *Cross-Algorithm Correlation:* X25519 also exhibited 1.54× slowdowns in earlier blocks, whereas ECDSA and ML-DSA were unaffected.
  4. *Inference:* Consistent with host dynamic CPU frequency scaling (AMD CPPC / Precision Boost ramp-up from power-saving P-state ~2.4 GHz to ~4.5 GHz boost) rather than algorithmic degradation.
- **Analysis Code Fix:** Fixed the off-by-one binning bug in `analyze_repeats.py` to produce exact 100-sample blocks (`0001-0100`, `0101-0200`, ..., `0901-1000`).

### Milestone 3: Hardening the Benchmark Harness (`benchmark.py`)
- Monotonic nanosecond timing isolation (`time.perf_counter_ns()`).
- Algorithm execution order controls (`fixed`, `rotate`, `random` with recorded seeds).
- Negative signature verification checks and mutual shared secret equality checks.
- Real-time resource telemetry (process peak RSS, cgroup v2 memory current/max, CFS CPU throttling stats, and system load averages).
- Comprehensive statistical summary output (`min`, `max`, `median`, `mean`, `std`, `p90`, `p95`, `p99`, `iqr`, `mad`).

### Milestone 4: Stage A (Validation) Execution
- Validated on 20 trials, 3 warm-ups (`experiments/EXP_VALIDATION_STAGE_A`).
- All 220 correctness checks passed; telemetry and summary stats independently verified.

### Milestone 5: Stage B (Timing Variability & Reproducibility Study) Execution
- Executed 5 independent container processes (1 CPU, 512 MiB RAM, 1,000 trials, 20 warm-ups per operation).
- Run-level variation was **under 1.33% CoV** for ML-KEM and **under 1.11% CoV** for X25519.
- Proved that execution order position does **not** systematically penalize median latency.
- Identified that sporadic block-level jumps (~40–49 µs) occur across multiple algorithms due to host/WSL2 virtualization scheduling events.
- All 55,000 correctness checks passed. Detailed results in `STAGE_B_REPORT.md`.

### Milestone 6: Stage C (Controlled Resource Sensitivity Study) Execution
- Executed 15 independent runs across a multi-dimensional matrix:
  - **CPU Quotas:** 0.5 CPU, 1.0 CPU, 2.0 CPUs (holding memory constant at 512 MiB).
  - **Memory Limits:** 256 MiB, 512 MiB, 1024 MiB (holding CPU constant at 1.0 CPU).
- **Outcomes:**
  1. *CPU Quota vs. Median Latency:* Median latency changed by **less than 2.4%** between 0.5 CPU and 2.0 CPUs because individual cryptographic operations complete in microseconds—far below the 50 ms CFS quota window.
  2. *CFS Throttling & Throughput:* Under 0.5 CPU, continuous looping consumed the 50 ms quota per 100 ms period, incurring **$1,181.8 \pm 36.0$ ms of throttling** across $29$ periods and increasing total wall runtime by **$1.83\times$**. Under 1.0 CPU and 2.0 CPUs, throttling was **0.0 ms across 0 periods**.
  3. *Tail Latency Spikes:* Trials straddling CFS quota boundaries registered max latencies of **~47–51 ms** exclusively under 0.5 CPU due to kernel thread suspension.
  4. *Memory Invariance:* Memory limits between 256 MiB and 1024 MiB had zero effect on latency (< 1.5% delta). Process peak RSS was constant at **$44.25 \pm 0.15$ MiB** and active container memory was **$27.2 \pm 0.3$ MiB** (0 OOM events).
  5. *Correctness:* All 165,000 checks passed. Detailed results documented in `STAGE_C_REPORT.md`.

### Milestone 7: Stage D1 (Artifact Size, Serialization, and Transmission Feasibility) Execution
- **Artifact Quantification:** 13,000 measurements across 1,000 samples per primitive.
  - ML-KEM-768 PK is 1,184 B (**37.0×** vs. X25519 32 B); CT is 1,088 B.
  - ML-DSA-65 PK is 1,952 B (**30.0×** vs. uncompressed ECDSA 65 B; **59.2×** vs. compressed 33 B).
  - ML-DSA-65 signature is 3,309 B (**46.6×** vs. ECDSA DER 71.0 B mean; **51.7×** vs. IEEE P1363 64 B).
  - Empirically characterized ECDSA DER length variance (69 to 72 bytes).
- **Message Exchange Budgets:**
  - Scenario K1 (pre-shared recipient PK): 32 B (X25519) vs. 1,088 B (ML-KEM) (**34.0×**).
  - Scenario K2 (interactive 2-way handshake): 64 B (X25519) vs. 2,272 B (ML-KEM) (**35.5×**).
  - Signed telemetry (16–32 B payload): ML-DSA introduces 10,000%–20,000% overhead.
- **Link-Layer Fragmentation:**
  - On nominal 128-byte 6LoWPAN with 48B header/security overhead (80B usable payload), ML-DSA-65 requires **42 fragments** (+60.9% transmission penalty of 2,016B in headers), whereas ECDSA fits in **1 frame**.
  - ML-KEM PK requires **15 fragments**; CT requires **14 fragments**.
- **Transport Microbenchmarks:** 2,000 loopback trials across 20 payload conditions. Transfer latency in kernel memory is ~95–105 µs, contrasting with physical low-power radio channels (~170 ms airtime on 250 kbps 802.15.4). Detailed report in `experiments/EXP_STAGE_D1_ARTIFACTS_20261025_214841/STAGE_D1_REPORT.md`.

### Milestone 8: Stage D2 (Cold-Start, Initialization & Steady-State Cryptographic Profiling) Execution
- **Process Startup & Import Hierarchy:** Minimal Python 3.12 subprocess launch requires a median parent-observed wall time of **55.59 ms** (child internal runtime: **1.70 µs**). Standard library imports add **18.06 ms**. `cryptography` import requires **63.71 ms** (peak RSS ~25.8 MiB). `oqs` import requires **207.10 ms** (**3.25× higher than `cryptography`**, peak RSS ~31.2 MiB) due to CFFI dynamic symbol resolution of AVX2/AVX512/ARMv8 vector extensions across multiple lattice schemes.
- **Algorithm-Object Construction:** Object construction is negligible across all primitives: inline for X25519 (< 1 µs), 1.26 µs for ECDSA P-256 curve selection, 49.19 µs for ML-KEM-768 KEM object allocation, and 54.40 µs for ML-DSA-65 Signer object allocation.
- **First-Operation Cold Penalties vs. Steady-State:**
  - **X25519 `keygen`:** First op median = **20,695.79 µs** (20.70 ms) vs steady-state = **51.18 µs** (Ratio = **404.36×**, Cold increase = **+40,335.7%**).
  - **ECDSA-P256 `sign`:** First op median = **17,294.83 µs** (17.29 ms) vs steady-state = **40.47 µs** (Ratio = **427.36×**, Cold increase = **+42,636.0%**).
  - **ML-KEM-768 `keygen`:** First op median = **2,442.83 µs** (2.44 ms) vs steady-state = **26.65 µs** (Ratio = **91.67×**, Cold increase = **+9,066.7%**).
  - **ML-KEM-768 `encapsulation`:** First op median = **142.78 µs** vs steady-state = **28.68 µs** (Ratio = **4.98×**, Cold increase = **+397.9%**).
  - **ML-DSA-65 `keygen`:** First op median = **2,490.42 µs** (2.49 ms) vs steady-state = **85.47 µs** (Ratio = **29.14×**, Cold increase = **+2,813.9%**).
  - **ML-DSA-65 `sign`:** First op median = **356.79 µs** vs steady-state = **200.07 µs** (Ratio = **1.78×**, Cold increase = **+78.3%**).
- **Process Independence & Variability:** 25 independent fresh processes per condition (totaling 225 processes for D2-A and 275 processes for D2-B; 27,775 total recorded operations). First-operation CoV across independent processes was 4.6% to 48.1%, while steady-state process median CoV remained under 17.7%.
- **Correctness:** 100% of cryptographic operations passed verification across all 275 fresh processes. Detailed report in `experiments/EXP_STAGE_D2_COLDSTART_20261025_221745/STAGE_D2_REPORT.md` and root `STAGE_D2_REPORT.md`.

---


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

---

## 3. Open Research Questions

1. **Cycle & Energy Dissipation on Embedded Targets:** How do memory access patterns, cache misses, and arithmetic complexity in lattice polynomial multiplication translate to CPU cycle counts and battery draw on bare-metal microcontrollers (ARM Cortex-M4, RISC-V)?
2. **Concurrent Request Throughput & Contention:** How do CPU quotas and memory limits affect multi-threaded or concurrent request throughput when multiple verification/encapsulation tasks compete for resources?
3. **TLS 1.3 Protocol-Level Integration:** How do TLS 1.3 handshake dynamics, negotiated hybrid key exchange groups (`X25519MLKEM768`), and certificate chains behave under real network constraints?

---

## 4. Next Actions (Stage E Plan)

- **Objective:** Energy and Cycle Profiling on Emulated Embedded Architectures:
  - Deploy QEMU / Renode emulators for ARM Cortex-M4 (STM32F4) target.
  - Profile cycle counts and instruction counts using hardware performance monitoring registers.
  - Model joule energy consumption and battery operational lifetime for intermittent IoT sensor nodes.

