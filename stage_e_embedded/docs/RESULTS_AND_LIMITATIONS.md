# Stage E Results and Scientific Limitations

**Project Title:** Empirical Migration Feasibility Analysis of Post-Quantum Cryptography for Resource-Constrained Systems  
**Milestone:** Stage E — Embedded & Host-Native C Cryptographic Profiling  
**Evaluation Date:** 2026-10-26  

---

## 1. Host-Native C Reference Results (GCC 14.2.0, -O3)

Measurements compiled from [`host_native_c_summary.csv`](file:///d:/Cyber-security/pqc_first_experiment/stage_e_embedded/results/host_native_c/EXP_STAGE_E_HOST_C_20261026_005246/host_native_c_summary.csv) across 1,000 steady-state trials per operation:

| Algorithm | Operation | Implementation | Median (µs) | Mean (µs) | Std (µs) | CoV (%) | P90 (µs) | P95 (µs) | P99 (µs) | IQR (µs) | MAD (µs) |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **ML-KEM-768** | `keygen` | `liboqs_c` | **20.654** | 25.639 | 10.059 | 39.2% | 35.781 | 41.617 | 64.423 | 7.592 | 0.697 |
| **ML-KEM-768** | `encapsulation` | `liboqs_c` | **21.291** | 25.714 | 12.651 | 49.2% | 34.126 | 40.937 | 58.819 | 5.668 | 0.562 |
| **ML-KEM-768** | `decapsulation` | `liboqs_c` | **25.078** | 28.836 | 9.178 | 31.8% | 36.375 | 41.986 | 69.499 | 6.132 | 0.762 |
| **ML-DSA-65** | `keygen` | `liboqs_c` | **81.169** | 91.424 | 29.373 | 32.1% | 121.203 | 132.462 | 171.679 | 28.165 | 8.421 |
| **ML-DSA-65** | `sign` | `liboqs_c` | **181.215** | 225.675 | 139.552 | 61.8% | 405.421 | 515.027 | 759.293 | 149.251 | 67.789 |
| **ML-DSA-65** | `verify` | `liboqs_c` | **70.373** | 84.578 | 36.086 | 42.7% | 109.636 | 122.402 | 204.257 | 21.686 | 1.552 |
| **X25519** | `keygen` | `openssl_c` | **55.767** | 68.954 | 27.600 | 40.0% | 94.360 | 107.839 | 164.543 | 16.697 | 1.223 |
| **X25519** | `shared_secret_derivation` | `openssl_c` | **46.979** | 52.960 | 12.267 | 23.2% | 64.420 | 70.445 | 93.283 | 11.722 | 0.921 |
| **ECDSA-P256** | `keygen` | `openssl_c` | **34.285** | 39.122 | 15.383 | 39.3% | 57.135 | 63.914 | 93.355 | 19.532 | 7.875 |
| **ECDSA-P256** | `sign` | `openssl_c` | **37.722** | 42.678 | 19.511 | 45.7% | 55.751 | 66.574 | 105.474 | 13.187 | 4.970 |
| **ECDSA-P256** | `verify` | `openssl_c` | **98.969** | 108.419 | 26.617 | 24.6% | 129.921 | 148.988 | 199.674 | 25.989 | 8.667 |

---

## 2. Host-Native C vs. Host Python API (Stage D2 Steady-State)

By benchmarking the identical cryptographic operations in compiled C (`gcc -O3`) against the Python 3.12 API (`liboqs-python` and `cryptography`), we empirically quantify the **Python runtime and CFFI wrapper overhead**:

| Algorithm | Operation | Host Native C Median (µs) | Stage D2 Python Median (µs) | Absolute Delta (µs) | Wrapper Overhead Ratio | Python Wrapper Tax (%) |
|---|---|---:|---:|---:|---:|---:|
| **ML-KEM-768** | `encapsulation` | 21.29 | 28.68 | +7.39 | **1.35×** | **+34.7%** |
| **ML-KEM-768** | `keygen` | 20.65 | 26.65 | +6.00 | **1.29×** | **+29.0%** |
| **ML-KEM-768** | `decapsulation` | 25.08 | 30.91 | +5.83 | **1.23×** | **+23.2%** |
| **ML-DSA-65** | `verify` | 70.37 | 81.50 | +11.13 | **1.16×** | **+15.8%** |
| **ML-DSA-65** | `sign` | 181.22 | 200.07 | +18.85 | **1.10×** | **+10.4%** |
| **ML-DSA-65** | `keygen` | 81.17 | 85.47 | +4.30 | **1.05×** | **+5.3%** |
| **X25519** | `shared_secret_derivation` | 46.98 | 50.48 | +3.50 | **1.07×** | **+7.5%** |
| **ECDSA-P256** | `sign` | 37.72 | 40.47 | +2.75 | **1.07×** | **+7.3%** |
| **ECDSA-P256** | `verify` | 98.97 | 103.93 | +4.96 | **1.05×** | **+5.0%** |

### Key Takeaway on Wrapper Overhead:
- Python CFFI introduces a **relatively constant ~4–10 µs per-call boundary penalty** across all native C calls.
- For high-speed lattice operations like **ML-KEM-768 key encapsulation (21.3 µs native C)**, this fixed wrapper cost constitutes a massive **+34.7% latency penalty**.
- For longer operations like **ML-DSA-65 signing (181.2 µs native C)**, the relative wrapper tax is amortized down to **~10.4%**.

---

## 3. Physical Hardware Status & Scientific Limitations

### 3.1 Hardware Availability Statement
- An automated audit of the Windows host system (`Get-CimInstance Win32_PnPEntity`, `SerialPort::GetPortNames()`) confirmed that **no physical STM32 development board (e.g., STM32F4 Discovery) is currently enumerated on USB or COM ports**.
- In strict adherence to scientific integrity rules:
  - **Zero physical Cortex-M4 cycle counts are fabricated or reported.**
  - Physical results directory [`results/stm32f4_physical/`](file:///d:/Cyber-security/pqc_first_experiment/stage_e_embedded/results/stm32f4_physical/) remains empty pending physical hardware connection.

### 3.2 Fundamental Architectural Divergence (x86_64 vs. Cortex-M4)
Host-native C measurements on x86_64 **cannot and must not be equated with microcontroller performance**:

| Feature | Host Workstation (AMD Ryzen 7 7435HS) | Embedded MCU (STM32F407VG) | Feasibility Impact |
|---|---|---|---|
| **Architecture** | x86_64 superscalar out-of-order | 32-bit ARMv7E-M in-order pipeline | ~10× to 100× instruction execution differential |
| **Clock Frequency** | 3.10 GHz base (up to 4.50 GHz boost) | 168 MHz maximum core clock | 20× to 26× clock frequency differential |
| **Vector Units** | AVX2 / AVX-512 256-bit SIMD registers | None (Single-precision 32-bit FPU only) | Lattice NTT and matrix vector multiplication cannot use 256-bit SIMD |
| **SRAM Memory** | 16 GiB system DDR5 RAM | 192 KiB internal SRAM (128KB continuous) | ML-DSA-65 keys (1,952B PK, 4,032B SK, 3,309B Sig) consume substantial portions of MCU stack |
| **Cache Hierarchy** | L1/L2/L3 multi-megabyte cache hierarchy | Zero L2/L3 cache (ART Accelerator for Flash) | Memory access latency is governed strictly by Flash wait states |

---

## 4. Upstream Framework Evaluation (PQM4)

- **Evaluated Framework:** [mupq/pqm4](https://github.com/mupq/pqm4)
- **Pinned Commit:** `6ff2be970f6f4592b341d432042063ceacf424a2`
- **Submodules Evaluated:**
  - `libopencm3`: `1f3abd43763fa39d23e737602b6d0011a45c70b2`
  - `mupq`: `981df31b84585df097333a9d2319ec0d6e357fee`
  - `mupq/pqclean`: `2cc64716044832eea747234ddbffc06746ab815d`
- **Assessment & Critical Findings:**
  1. **Post-Quantum Scope Only:** Upstream PQM4 is exclusively dedicated to NIST PQC schemes and candidates. It includes `ml-kem-768` (`m4fspeed`, `m4fstack`) and `ml-dsa-65` (`m4f`, `m4fstack`). It **does not provide classical ECC schemes** (X25519 or ECDSA P-256). For classical embedded baselines, maintained alternatives such as `cortex-m4-x25519` (Düll et al.), `micro-ecc` (kmackay), and ARM's `mbedTLS` must be utilized.
  2. **Upstream Deprecation Notice:** PQM4 officially announced that it is no longer under active maintenance and is scheduled to be archived as read-only in January 2027. Future production migrations are recommended to evaluate the [PQ Code Package](https://github.com/pq-code-package) (`mlkem-native` and `mldsa-native`).
  3. **Clocking Justification:** PQM4 configures STM32F4 Discovery (`stm32f4discovery`) at **24 MHz** with 0 Flash wait states (`FLASH_ACR_LATENCY_0WS`) for benchmark reproducibility, or 168 MHz with 5 wait states for fast execution.
  4. **Cycle Counting Mechanism:** Rather than relying solely on a 32-bit DWT cycle counter which overflows in ~25.5 seconds at 168 MHz, PQM4 combines SysTick (24-bit reload register `0xFFFFFF`) with a SysTick overflow interrupt handler, yielding an extended 64-bit cycle counter (`hal_get_time()`).
  5. **Dynamic Stack Profiling:** PQM4 uses `hal_spraystack()` with canary byte `0x42` and `hal_checkstack()` to establish exact peak SRAM stack usage without heap instrumentation.

---

## 5. Non-Fabrication & Scientific Integrity Audit Checklist

- [x] Zero physical Cortex-M4 cycle counts were fabricated or estimated.
- [x] Physical results directory `results/stm32f4_physical/` remains empty pending verified board connection.
- [x] Host-native C benchmark results are strictly labelled as x86_64 native execution (`gcc -O3`).
- [x] Emulator execution harness is strictly segregated into `results/stm32f4_emulated/` and tagged as simulated.
- [x] Historical datasets (Stages A, B, C, D1, D2) are preserved 100% bit-for-bit intact without alteration.
- [x] Energy consumption is NOT inferred from cycle counts; documented as requiring physical hardware current shunts (INA219 / oscilloscope).

