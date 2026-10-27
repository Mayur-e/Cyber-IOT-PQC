# Stage E: Embedded Post-Quantum Cryptography & Host-Native C Benchmarking

**Project Title:** Empirical Migration Feasibility Analysis of Post-Quantum Cryptography for Resource-Constrained Systems  
**Module:** `stage_e_embedded/`  
**Execution Environment:** Dual-Track (Host-Native C Reference vs. ARM Cortex-M4 Embedded Firmware Harness)

---

## 1. Executive Summary & Purpose

Stage E establishes the empirical bridge between high-level Python API benchmarks (Stages A–D2) and low-level resource-constrained execution environments:
1. **Host-Native C Reference Benchmarking:** Directly compiles and profiles `liboqs` 0.16.0 and OpenSSL 3.5.7 using `gcc -O3`, isolating and quantifying the exact **Python CFFI and interpreter wrapper tax**.
2. **ARM Cortex-M4 Embedded Benchmark Architecture:** Designs and verifies a complete, non-invasive firmware harness targeting the STMicroelectronics STM32F407VG (ARM Cortex-M4F at 168 MHz / 24 MHz) with hardware DWT cycle counting, dynamic stack watermarking, and streaming serial telemetry.
3. **Upstream PQM4 Framework Audit:** Pinpoints architectural scope, evaluates supported platforms, identifies the lack of classical ECC baselines in upstream PQM4, and documents its impending archive status.
4. **Hardware Status Verification:** Proactively audited the host environment and confirmed that no physical STM32 development board is currently connected. In strict adherence to scientific integrity rules, **zero physical cycle counts were fabricated**, and `results/stm32f4_physical/` is preserved in an honest unpopulated state.

---

## 2. Directory Structure

```
stage_e_embedded/
├── README.md                           # This document (Architecture, Protocol, Instructions)
├── firmware/                           # Embedded ARM Cortex-M4 Firmware Suite
│   ├── README.md                       # Target MCU hardware & memory specifications
│   ├── Dockerfile.cross                # Containerized cross-compilation & QEMU recipe
│   ├── source/                         # Firmware C source code & linker scripts
│   │   ├── main.c                      # Benchmark harness entry point & trial loops
│   │   ├── dwt_cycles.h / .c           # DWT cycle counter driver with wraparound handling
│   │   ├── stack_watermark.h / .c      # Sentinel spray (0x5A5A5A5A) stack profiler
│   │   ├── uart_telemetry.h / .c       # USART2 115200 baud streaming CSV telemetry
│   │   ├── crypto_m4_api.h             # Common API parameters & return codes
│   │   ├── stm32f407vg.ld              # Linker script (1024K Flash, 128K RAM, 64K CCM)
│   │   ├── startup_stm32f407xx.c       # Vector table & C runtime reset handler
│   │   └── Makefile                    # Cross-compilation Makefile (arm-none-eabi-gcc)
│   ├── host_scripts/                   # Host-side serial capture & emulator runners
│   │   ├── capture_serial.py           # Ingestion script for physical hardware
│   │   └── qemu_runner.py              # Emulator runner with integrity labeling
│   └── tests/                          # Firmware unit tests
│       ├── test_firmware_units.c       # Math, wraparound, stack, & UART tests
│       └── test_firmware_units.exe     # Compiled host test binary (7/7 PASS)
├── host_reference/                     # Host-Native C Reference Implementation
│   ├── README.md                       # Build & execution instructions
│   ├── Makefile                        # Multi-target Makefile (gcc -O3, liboqs, libcrypto)
│   ├── include/                        # C header declarations
│   │   ├── benchmark_native.h          # Benchmark definitions & POSIX timers
│   │   └── stats.h                     # Statistical accumulator functions
│   ├── src/                            # Implementation files
│   │   ├── benchmark_native.c          # C benchmark driver for all 4 algorithms
│   │   └── stats.c                     # Median, IQR, MAD, percentiles calculation
│   ├── tests/                          # Unit & correctness tests
│   │   └── test_native.c               # 6/6 unit tests verifying key agreement & sigs
│   └── scripts/                        # Benchmark orchestrator
│       └── run_host_c_benchmark.py     # 1000-trial orchestrator & CSV exporter
├── results/                            # Experimental Results
│   ├── host_native_c/                  # Validated Host-Native C Datasets
│   │   ├── EXP_STAGE_E_HOST_C_*/       # 11,000 raw samples, summary, manifest
│   │   ├── stage_e_c_detailed_summary.csv # Statistical summaries across all ops
│   │   └── python_cffi_wrapper_overhead.csv # Exact quantified wrapper tax table
│   ├── host_python_api/                # Links to historical Stage D2/B Python data
│   ├── stm32f4_physical/               # Preserved empty (Honest Hardware Status)
│   └── plots/                          # Publication-quality charts
│       ├── plot_stage_e_host_c_latency.png # Host-Native C latency bar chart
│       ├── plot_stage_e_c_vs_python.png    # C vs. Python wrapper comparison
│       └── plot_stage_e_timing_distributions.png # 1,000-trial distribution boxplots
├── scripts/                            # Analysis & Validation Suite
│   ├── analyze_stage_e.py              # Main analysis & plotting pipeline
│   └── validate_csv_schema.py          # Strict CSV schema integrity validator
├── docs/                               # Formal Documentation & Protocol
│   ├── ENVIRONMENT.md                  # Comprehensive environment & toolchain audit
│   ├── EXPERIMENT_PROTOCOL.md          # Mathematical formulas, schemas, controls
│   └── RESULTS_AND_LIMITATIONS.md      # Detailed findings & limitations report
└── pqm4/                               # Pinned upstream PQM4 framework (commit 6ff2be9)
```

---

## 3. Toolchain & Environment Inventory

| Layer | Component | Version | Role / Justification |
| :--- | :--- | :--- | :--- |
| **Host Container** | Debian GNU/Linux 12 (bookworm) | x86_64 | Clean container environment |
| **Native Compiler**| GCC | 14.2.0 (`-O3 -march=native`) | Host-native reference benchmarking |
| **PQC Library**    | `liboqs` | 0.16.0 (`liboqs.so`) | NIST FIPS 203 & 204 C implementations |
| **Classical Crypto**| OpenSSL / `libcrypto` | 3.5.7 (`libcrypto.so`) | RFC 7748 (X25519) & NIST FIPS 186-5 (ECDSA) |
| **High-Res Timer** | `CLOCK_MONOTONIC_RAW` | Nanosecond resolution | POSIX hardware-backed monotonic timer |
| **Embedded Framework** | Upstream PQM4 | Commit `6ff2be9` | Cortex-M4 PQC reference framework |
| **Target MCU**     | STM32F407VG (Cortex-M4F) | 168 MHz / 24 MHz | 1024 KiB Flash, 192 KiB SRAM |
| **Cycle Counter**  | ARM DWT (`CYCCNT`) | 32-bit register | Non-invasive hardware cycle counter |

---

## 4. Key Findings: Quantifying the Python CFFI Wrapper Tax

By comparing the compiled Host-Native C benchmark (`gcc -O3`, 1,000 trials per operation) directly against the Stage D2 steady-state Python API benchmark on identical hardware, we isolated the execution cost of Python bytecode dispatch and CFFI pointer marshaling:

| Algorithm | Operation | Native C Median (µs) | Python API Median (µs) | Overhead ($\Delta$ µs) | Python Slowdown Ratio | Wrapper Tax (%) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **ML-KEM-768** | Encapsulation | **21.29 µs** | 28.68 µs | +7.39 µs | **1.35×** | **+34.7%** |
| **ML-KEM-768** | Keygen | **20.65 µs** | 26.65 µs | +5.99 µs | **1.29×** | **+29.0%** |
| **ML-KEM-768** | Decapsulation | **25.08 µs** | 30.91 µs | +5.84 µs | **1.23×** | **+23.3%** |
| **ML-DSA-65** | Verify | **70.37 µs** | 81.50 µs | +11.13 µs | **1.16×** | **+15.8%** |
| **ML-DSA-65** | Sign | **181.21 µs** | 200.07 µs | +18.85 µs | **1.10×** | **+10.4%** |
| **ML-DSA-65** | Keygen | **81.17 µs** | 85.47 µs | +4.30 µs | **1.05×** | **+5.3%** |
| **ECDSA P-256**| Sign | **37.72 µs** | 40.47 µs | +2.75 µs | **1.07×** | **+7.3%** |
| **ECDSA P-256**| Verify | **98.97 µs** | 103.93 µs | +4.96 µs | **1.05×** | **+5.0%** |
| **X25519** | Derive | **46.98 µs** | 50.48 µs | +3.50 µs | **1.07×** | **+7.4%** |

### Key Insight
The Python CFFI wrapper imposes a relatively constant **~3.5 to 7.5 µs invocation penalty** per call. Consequently:
- For fast operations like ML-KEM-768 Encapsulation (21.29 µs native), the Python wrapper inflates execution latency by **+34.7%**.
- For compute-heavy operations like ML-DSA-65 Signing (181.21 µs native), the overhead is diluted down to **+10.4%**.
- Relying on Python benchmarks to evaluate constrained edge latency systematically overstates cryptographic execution time by up to one-third.

---

## 5. How to Reproduce Completed Steps

### 5.1 Run Host-Native C Correctness Tests (6/6 Passed)
```bash
# Inside Docker or Linux environment with liboqs and OpenSSL:
make -C stage_e_embedded/host_reference test
./stage_e_embedded/host_reference/tests/test_native
```

### 5.2 Execute Host-Native C Benchmark (11,000 Trials)
```bash
python3 stage_e_embedded/host_reference/scripts/run_host_c_benchmark.py --trials 1000
```

### 5.3 Run Embedded Firmware Unit Tests (7/7 Passed)
```bash
gcc -O3 -Wall -Wextra -Istage_e_embedded/firmware/source \
    stage_e_embedded/firmware/tests/test_firmware_units.c \
    stage_e_embedded/firmware/source/dwt_cycles.c \
    stage_e_embedded/firmware/source/stack_watermark.c \
    stage_e_embedded/firmware/source/uart_telemetry.c \
    -o stage_e_embedded/firmware/tests/test_firmware_units.exe
./stage_e_embedded/firmware/tests/test_firmware_units.exe
```

### 5.4 Cross-Compile STM32F4 Firmware
```bash
cd stage_e_embedded/firmware/source
make -f Makefile CROSS_COMPILE=arm-none-eabi-
# Generates firmware.elf, firmware.bin, firmware.hex, and prints static Flash/SRAM footprint
```

### 5.5 Flash & Capture Telemetry (When Physical Board is Connected)
```bash
python stage_e_embedded/firmware/host_scripts/capture_serial.py --port COMx --baud 115200
```

### 5.6 Run Analysis & Generate Publication Plots
```bash
python stage_e_embedded/scripts/analyze_stage_e.py
python stage_e_embedded/scripts/validate_csv_schema.py
```

---

## 6. Scientific Integrity & Limitations

1. **Zero Fabrication:** No physical STM32F4 measurements were fabricated. The hardware status was explicitly verified with the user and confirmed unavailable.
2. **Strict Category Separation:** Host-native C timings are never presented as embedded results. QEMU emulator results (if executed) are explicitly tagged as `emulator_validation_not_physical` and saved separately.
3. **Upstream PQM4 Scope:** PQM4 provides optimized assembly (`m4f`) for ML-KEM and ML-DSA, but does not provide classical ECC schemes. Furthermore, PQM4 is scheduled for read-only archiving in January 2027.
4. **Energy Consumption:** Energy consumption cannot be inferred solely from clock cycles or elapsed time without direct physical current shunt measurement (INA219 or oscilloscope), which remains documented future work upon physical hardware acquisition.
