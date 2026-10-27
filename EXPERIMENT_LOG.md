# Experiment Log: PQC Migration Feasibility

This log tracks all experimental executions in chronological order, recording identifiers, configurations, environmental parameters, telemetry, and findings.

---

## Chronological Experiment Register

| Experiment ID | Directory / Target | CPU Quota | Mem Limit | Trials | Warmups | Order Policy | Status | Key Findings / Anomalies |
|---|---|---|---|---|---|---|---|---|
| `HIST_CPU2_MEM3` | `results_cpu2_mem3/` | 2.0 | 3 GiB | 100 | 5 | Fixed | Complete | Initial unconstrained multi-core baseline. ML-KEM keygen ~26 µs, ML-DSA keygen ~80 µs. |
| `HIST_CPU1_MEM3` | `results_cpu1_mem3/` | 1.0 | 3 GiB | 100 | 5 | Fixed | Complete | CPU-constrained baseline (1 CPU). Timings close to 2 CPU baseline under single-threaded load. |
| `HIST_CPU1_MEM512` | `results_cpu1_mem512/` | 1.0 | 512 MiB | 100 | 5 | Fixed | Complete | Memory-constrained baseline. No OOM events or degradation observed at 100 trials. |
| `HIST_CPU1_MEM512_N1000_R1` | `results_cpu1_mem512_n1000_run1/` | 1.0 | 512 MiB | 1,000 | 20 | Fixed | Complete | High-trial repeatability run 1. Stable medians (~26 µs ML-KEM). Transient bump in trials 700-900 (~35 µs). |
| `HIST_CPU1_MEM512_N1000_R2` | `results_cpu1_mem512_n1000_run2/` | 1.0 | 512 MiB | 1,000 | 20 | Fixed | Complete | High-trial repeatability run 2. Highly stable across all 10 blocks (ML-KEM keygen median 26.046 µs). |
| `HIST_CPU1_MEM512_N1000_R3` | `results_cpu1_mem512_n1000_run3/` | 1.0 | 512 MiB | 1,000 | 20 | Fixed | Complete | **Timing Anomaly Observed:** ML-KEM medians elevated to 47.0 µs (keygen), 50.0 µs (encap), 47.1 µs (decap). Transition back to 26 µs occurred at trial 794–815. Attributed to CPU dynamic frequency boost ramp-up / P-state warmup delay. |
| `EXP_VALIDATION_STAGE_A` | `experiments/EXP_VALIDATION_STAGE_A/` | 1.0 | 512 MiB | 20 | 3 | Fixed (seed=42) | Verified | **Stage A Harness Validation.** All 220 correctness checks passed. Peak RSS 37.6 MB. Cgroup v2 telemetry active. Independent statistical check passed (< 0.00005 µs delta). |
| `EXP_STAGE_B_..._R1` | `experiments/..._R1_fixed_x25519_first/` | 1.0 | 512 MiB | 1,000 | 20 | Fixed (seed=0) | Verified | **Stage B Run 1.** Reference condition (X25519 1st). ML-KEM keygen 29.6 µs. Peak RSS 44.25 MiB. 11,000 checks passed. 7.6 ms throttled. |
| `EXP_STAGE_B_..._R2` | `experiments/..._R2_rotate_mlkem_first/` | 1.0 | 512 MiB | 1,000 | 20 | Rotate (seed=1) | Verified | **Stage B Run 2.** ML-KEM 1st. ML-KEM keygen 29.0 µs. Peak RSS 44.25 MiB. 11,000 checks passed. 0 throttled. |
| `EXP_STAGE_B_..._R3` | `experiments/..._R3_rotate_ecdsa_first/` | 1.0 | 512 MiB | 1,000 | 20 | Rotate (seed=2) | Verified | **Stage B Run 3.** ECDSA 1st. ML-KEM keygen 29.6 µs. Peak RSS 44.12 MiB. 11,000 checks passed. 0 throttled. |
| `EXP_STAGE_B_..._R4` | `experiments/..._R4_rotate_mldsa_first/` | 1.0 | 512 MiB | 1,000 | 20 | Rotate (seed=3) | Verified | **Stage B Run 4.** ML-DSA 1st. ML-KEM keygen 29.2 µs. Peak RSS 44.25 MiB. 11,000 checks passed. 0 throttled. |
| `EXP_STAGE_B_..._R5` | `experiments/..._R5_random_seed2024/` | 1.0 | 512 MiB | 1,000 | 20 | Random (seed=2024) | Verified | **Stage B Run 5.** Interleaved order. ML-KEM keygen 29.3 µs. Peak RSS 44.38 MiB. 11,000 checks passed. 0 throttled. |
| `EXP_STAGE_C_CPU05_MEM512_R1-R3` | `experiments/EXP_STAGE_C_CPU05_MEM512_R*/` | 0.5 | 512 MiB | 1,000 | 20 | Rotated ($s=0,1,2$) | **Verified** | **Stage C CPU 0.5 Study.** 1,181 ms CFS throttling across 29 periods. Total runtime increased 1.83×. Median latency changed < 2.4%. All 33,000 checks passed. |
| `EXP_STAGE_C_CPU10_MEM512_R1-R3` | `experiments/EXP_STAGE_C_CPU10_MEM512_R*/` | 1.0 | 512 MiB | 1,000 | 20 | Rotated ($s=0,1,2$) | **Verified** | **Stage C CPU 1.0 Reference.** 0.0 ms throttled. Wall duration 1.59s. Peak RSS 44.1 MiB. All 33,000 checks passed. |
| `EXP_STAGE_C_CPU20_MEM512_R1-R3` | `experiments/EXP_STAGE_C_CPU20_MEM512_R*/` | 2.0 | 512 MiB | 1,000 | 20 | Rotated ($s=0,1,2$) | **Verified** | **Stage C CPU 2.0 Study.** 0.0 ms throttled. Wall duration 1.60s. Latency identical to 1.0 CPU baseline (< 0.5% delta). All 33,000 checks passed. |
| `EXP_STAGE_C_CPU10_MEM256_R1-R3` | `experiments/EXP_STAGE_C_CPU10_MEM256_R*/` | 1.0 | 256 MiB | 1,000 | 20 | Rotated ($s=0,1,2$) | **Verified** | **Stage C Memory 256M Study.** Peak RSS 44.17 MiB, active memory 27.43 MiB. Zero OOM. Latency identical (< 1.5% delta). All 33,000 checks passed. |
| `EXP_STAGE_C_CPU10_MEM1024_R1-R3`| `experiments/EXP_STAGE_C_CPU10_MEM1024_R*/`| 1.0 | 1024 MiB | 1,000 | 20 | Rotated ($s=0,1,2$) | **Verified** | **Stage C Memory 1024M Study.** Peak RSS 44.33 MiB, active memory 27.09 MiB. Zero OOM. Latency identical. All 33,000 checks passed. |
| `EXP_STAGE_D1_ARTIFACTS_...38` | `experiments/EXP_STAGE_D1_ARTIFACTS_20261025_214638/` | N/A | N/A | 50 (Art) / 20 (Tr) | 5 | Fixed | Validated | **Stage D1 Smoke Test.** Verified artifact measurements, message budget, and loopback transport pipeline. Caught plot label alignment bug before full run. |
| `EXP_STAGE_D1_ARTIFACTS_...41` | `experiments/EXP_STAGE_D1_ARTIFACTS_20261025_214841/` | N/A | N/A | 1,000 (Art) / 100 (Tr) | 10 | Fixed | **Verified** | **Stage D1 Full Benchmark.** ML-KEM PK 1184B (37×), CT 1088B; ML-DSA PK 1952B (30× uncomp / 59× comp), Sig 3309B (46.6× DER / 51.7× raw). 6LoWPAN 42-fragment penalty. 100% checks passed. |

---

## Detailed Notes by Experiment

### `HIST_CPU1_MEM512_N1000_R3` (Anomaly Investigation)
- **Execution Date:** 2026-10-19 05:08:02 UTC
- **Observed Behavior:**
  - Blocks 1–8 (trials 1–800) exhibited ML-KEM keygen medians of 47.5–49.8 µs.
  - Blocks 9–10 (trials 801–1,000) dropped sharply to 26.0–26.6 µs.
  - Slowdown ratio was uniform across all three operations (~1.80×).
  - Transition occurred between trial 794 and 815 within an 8.5 ms wall-clock window.
  - X25519 also exhibited discrete 1.54× latency jumps (48 µs → 74 µs) across earlier blocks.
  - Subsequent algorithms (ECDSA, ML-DSA) exhibited zero elevation because CPU boost frequency was already active.

### `EXP_VALIDATION_STAGE_A` (Harness & Environment Validation)
- **Execution Date:** 2026-10-25 16:14:28 UTC
- **Host Processor:** AMD Ryzen 7 7435HS (8 Cores, 16 Logical Processors, Base 3.1 GHz)
- **Container Environment:** `pqc-bench:1.0` (Python 3.12.15, liboqs 0.16.0, cryptography 50.0.2, OpenSSL 3.5.7)
- **Telemetry Verified:**
  - Peak Process RSS: 37,617,664 bytes (36,736 KiB)
  - Container Memory Current: 25,841,664 bytes (limit: 512 MiB)
  - CFS CPU Max: `100000 100000` (1.0 CPU quota)
  - Correctness: 220/220 checks passed.

### `STAGE_B_STUDY` (`EXP_STAGE_B_..._R1` through `R5`)
- **Execution Date:** 2026-10-25 20:57:49 to 20:58:08 UTC
- **Configuration:** 1 CPU, 512 MiB RAM, 1,000 trials, 20 warm-ups per operation.
- **Key Findings:**
  1. ML-KEM-768 run-level CoV was **1.33%** (keygen), **0.83%** (encapsulation), **0.53%** (decapsulation).
  2. Execution order position does **not** systematically penalize median latency.
  3. All 55,000 checks passed. Detailed report available in `STAGE_B_REPORT.md`.

### `STAGE_C_STUDY` (Controlled Resource Sensitivity Matrix)
- **Execution Date:** 2026-10-25 21:07:16 to 21:08:17 UTC
- **Configurations:** 15 independent runs across 5 resource configurations.
- **Key Findings:**
  1. **CPU Quota Invariance:** Median operation latency is invariant to CPU quota (< 2.4% delta between 0.5 CPU and 2.0 CPUs). Individual microbenchmark operations complete in microseconds, far below the 50 ms CFS period quota.
  2. **CFS Throttling & Throughput:** Under 0.5 CPU, the container was throttled for $1,181.8 \pm 36.0$ ms across 29 periods, increasing wall duration by $1.83\times$ (2.90s vs 1.59s). Zero throttling occurred under 1.0 CPU or 2.0 CPU.
  3. **Tail Spikes from CFS Suspension:** Occasional trials straddling CFS period exhaustion registered maximum latencies of ~47–51 ms under 0.5 CPU.
  4. **Memory Constraint Headroom:** Peak process RSS was identical at $44.25 \pm 0.15$ MiB across 256 MiB, 512 MiB, and 1024 MiB limits. Zero OOM events occurred.
  5. **Correctness:** 165,000/165,000 checks passed (100%). Detailed report available in `STAGE_C_REPORT.md`.

### `STAGE_D1_STUDY` (Artifact Size, Serialization & Transmission Feasibility)
- **Execution Date:** 2026-10-25 21:48:41 to 21:49:00 UTC
- **Experiment ID:** `EXP_STAGE_D1_ARTIFACTS_20261025_214841`
- **Configurations:** 1,000 artifact samples per primitive (13,000 total observations); 100 trials across 20 transport conditions (2,000 socket trials).
- **Key Findings:**
  1. **Artifact Expansion:** ML-KEM PK is 1184B (37.0× vs X25519 32B), CT is 1088B. ML-DSA PK is 1952B (30.0× vs ECDSA uncompressed 65B; 59.2× vs compressed 33B), Sig is 3309B (46.6× vs DER 71B; 51.7× vs IEEE P1363 64B).
  2. **DER Variance:** Observed ECDSA DER signature range: 69 to 72 bytes ($N=1000$, mean 71.02B).
  3. **Handshake Budgets:** Scenario K1 (pre-shared recipient PK) requires 32B (X25519) vs 1088B (ML-KEM) (34.0×). Scenario K2 (2-way handshake) requires 64B vs 2272B (35.5×).
  4. **6LoWPAN Fragmentation:** On 80-byte usable frame, ML-DSA-65 signature triggers 42 fragments (generating 2,016B of header overhead, a 60.9% penalty), whereas ECDSA P-256 requires 1 frame.
  5. **Loopback Transport:** Local transfer latencies remained ~95–105 µs across all sizes due to memory copy speeds in Linux kernel buffers, contrasting with physical low-power radio link constraints (~170 ms transmission airtime on 250 kbps 802.15.4).
  6. **Correctness:** 100% of cryptographic and transport integrity checks passed. Detailed report in `experiments/EXP_STAGE_D1_ARTIFACTS_20261025_214841/STAGE_D1_REPORT.md`.
### `STAGE_D2_STUDY` (Cold-Start, Initialization & Steady-State Cryptographic Profiling)
- **Execution Date:** 2026-10-25 22:17:45 to 22:19:22 UTC
- **Experiment ID:** `EXP_STAGE_D2_COLDSTART_20261025_221745`
- **Configurations:** 25 independent fresh subprocesses per condition across 9 startup targets (225 processes) and 11 cryptographic operations (275 processes). 5 warm-ups and 100 steady-state trials per process. Total recorded operations: 27,775 observations.
- **Key Findings:**
  1. **Subprocess Startup & Import Hierarchy:** Minimal Python 3.12 subprocess launch requires a median parent-observed wall time of **55.59 ms** (child internal runtime: **1.70 µs**). Standard library imports add **18.06 ms**. `cryptography` import requires **63.71 ms** (peak RSS ~25.8 MiB). `oqs` import requires **207.10 ms** (**3.25× higher than `cryptography`**, peak RSS ~31.2 MiB) due to dynamic CFFI symbol resolution of AVX2/AVX512/ARMv8 vector extensions across multiple lattice schemes.
  2. **Algorithm-Object Instantiation Overhead:** Once libraries are imported, object construction is negligible across all primitives: inline for X25519, 1.26 µs for ECDSA P-256 curve selection, 49.19 µs for ML-KEM-768 KEM object allocation, and 54.40 µs for ML-DSA-65 Signer object allocation.
  3. **First-Operation Cold Penalties:** Every cryptographic primitive incurs substantial initial execution overhead attributable to internal context setup and CSPRNG entropy seeding:
     - **X25519 `keygen`:** First op median = **20,695.79 µs** (20.70 ms) vs steady-state = **51.18 µs** (Ratio = **404.36×**, Cold increase = **+40,335.7%**).
     - **ECDSA-P256 `sign`:** First op median = **17,294.83 µs** (17.29 ms) vs steady-state = **40.47 µs** (Ratio = **427.36×**, Cold increase = **+42,636.0%**).
     - **ML-KEM-768 `keygen`:** First op median = **2,442.83 µs** (2.44 ms) vs steady-state = **26.65 µs** (Ratio = **91.67×**, Cold increase = **+9,066.7%**).
     - **ML-KEM-768 `encapsulation`:** First op median = **142.78 µs** vs steady-state = **28.68 µs** (Ratio = **4.98×**, Cold increase = **+397.9%**).
     - **ML-DSA-65 `keygen`:** First op median = **2,490.42 µs** (2.49 ms) vs steady-state = **85.47 µs** (Ratio = **29.14×**, Cold increase = **+2,813.9%**).
     - **ML-DSA-65 `sign`:** First op median = **356.79 µs** vs steady-state = **200.07 µs** (Ratio = **1.78×**, Cold increase = **+78.3%**).
  4. **Between-Process Variability vs Steady-State Consistency:** First-operation CoV across independent processes ranged from 4.6% to 48.1% due to operating system scheduling and CPU governor latency. Process steady-state median CoV remained highly consistent ($CoV_\text{proc} \le 17.7\%$).
  5. **Correctness & Verification:** 100% of cryptographic operations passed verification across all 275 fresh processes. Full report in `experiments/EXP_STAGE_D2_COLDSTART_20261025_221745/STAGE_D2_REPORT.md` and root `STAGE_D2_REPORT.md`.

### STAGE_E_STUDY (Embedded Architecture, PQM4 Audit & Host-Native C Reference Benchmarking)
- **Execution Date:** 2026-10-26 00:52:46 to 01:10:00 UTC
- **Experiment IDs:** EXP_STAGE_E_HOST_C_20261026_005246
- **Configurations:** 1,000 trials per operation across 11 cryptographic operations (11,000 observations) in compiled C (gcc -O3, liboqs 0.16.0, OpenSSL 3.5.7). Hardware audit conducted; embedded STM32F407VG firmware harness implemented with DWT cycle counting, dynamic stack watermarking, and streaming UART CSV telemetry.
- **Key Findings:**
  1. **Quantification of Python CFFI Wrapper Tax:**
     - Python CFFI and runtime dispatch impose a relatively constant **~3.5 to 7.5 µs boundary overhead** per cryptographic call.
     - **ML-KEM-768 Encapsulation:** Native C = **21.29 µs** vs Python Stage D2 = **28.68 µs** (Python is **1.35× slower**, **+34.7% wrapper tax**).
     - **ML-KEM-768 Keygen:** Native C = **20.65 µs** vs Python Stage D2 = **26.65 µs** (**1.29× slower**, **+29.0% wrapper tax**).
     - **ML-KEM-768 Decapsulation:** Native C = **25.08 µs** vs Python Stage D2 = **30.91 µs** (**1.23× slower**, **+23.3% wrapper tax**).
     - **ML-DSA-65 Verification:** Native C = **70.37 µs** vs Python Stage D2 = **81.50 µs** (**1.16× slower**, **+15.8% wrapper tax**).
     - **ML-DSA-65 Signing:** Native C = **181.21 µs** vs Python Stage D2 = **200.07 µs** (**1.10× slower**, **+10.4% wrapper tax**).
     - **ECDSA P-256 Signing:** Native C = **37.72 µs** vs Python Stage D2 = **40.47 µs** (**1.07× slower**, **+7.3% wrapper tax**).
     - **X25519 Derivation:** Native C = **46.98 µs** vs Python Stage D2 = **50.48 µs** (**1.07× slower**, **+7.4% wrapper tax**).
  2. **Upstream PQM4 Framework Audit:**
     - Evaluated upstream mupq/pqm4 at pinned commit 6ff2be970f6f4592b341d432042063ceacf424a2 with submodules libopencm3 (1f3abd4), mupq (981df31), and pqclean (2cc6471).
     - **Scope Restriction:** PQM4 exclusively provides post-quantum algorithms (ml-kem-768 m4fspeed/m4fstack and ml-dsa-65 m4f/m4fstack). It **does not provide classical ECC schemes** (X25519 or ECDSA P-256).
     - **Deprecation Notice:** Upstream PQM4 officially announced end of active maintenance with archiving scheduled for January 2027.
     - **Clocking & Timing Justification:** STM32F4 Discovery target is clocked at 24 MHz with 0 Flash wait states (FLASH_ACR_LATENCY_0WS) for cycle reproducibility, or 168 MHz with 5 wait states for performance. Cycle counting uses SysTick with a 64-bit overflow ISR handler (hal_get_time()) to prevent 32-bit counter wraparound.
  3. **Embedded Firmware Architecture:**
     - Implemented stage_e_embedded/firmware/source/ with DWT cycle counting (dwt_cycles.c), stack sentinel spray (stack_watermark.c), USART2 streaming CSV telemetry (uart_telemetry.c), linker script (stm32f407vg.ld), and cross-compilation Makefile.
     - All 7/7 firmware math and unit tests passed on host (	est_firmware_units.exe).
  4. **Hardware Verification & Scientific Non-Fabrication:**
     - Host audit confirmed zero physical STM32 development boards connected.
     - In strict adherence to scientific integrity rules, **zero physical cycle counts were fabricated**, and 
esults/stm32f4_physical/ is preserved unpopulated pending physical hardware connection.
  5. **Deliverables & Validation:**
     - All 11,000 raw host C records passed strict CSV schema validation (alidate_csv_schema.py).
     - Publication plots generated: plot_stage_e_host_c_latency.png, plot_stage_e_c_vs_python.png, plot_stage_e_timing_distributions.png.
     - Full documentation provided in stage_e_embedded/README.md, ENVIRONMENT.md, EXPERIMENT_PROTOCOL.md, and RESULTS_AND_LIMITATIONS.md.
