# PQC Benchmark Experiment: Empirical Migration Feasibility Analysis

This research repository conducts controlled empirical evaluations comparing post-quantum cryptography standards against classical algorithms for resource-constrained systems:
- **Key Establishment:** ML-KEM-768 (NIST FIPS 203) vs. X25519 (RFC 7748)
- **Digital Signatures:** ML-DSA-65 (NIST FIPS 204) vs. ECDSA P-256 (NIST FIPS 186-5)

It records per-operation elapsed time through Python APIs, artifact sizes, software versions, direct resource consumption (peak process RSS, cgroup v2 memory and CPU throttling), execution order randomization, and positive/negative correctness checks.

---

## Requirements
- Windows 10/11
- Docker Desktop configured in Linux container mode (WSL2 backend)
- Internet connection for initial image build (if not already cached)

---

## 1. Environment & Image Build

If the image `pqc-bench:1.0` is already built, it does **not** need to be rebuilt.
To build from scratch:
```powershell
docker build -t pqc-bench:1.0 .
```

---

## 2. Running an Experiment

All new experiments must be recorded in unique timestamped directories under `experiments/` to preserve historical data immutability:

```powershell
$EXP_DIR = "experiments\EXP_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Force $EXP_DIR | Out-Null

docker run --rm --cpus="1" --memory="512m" `
  -e RESULTS_DIR="/app/$EXP_DIR" `
  -e N_RUNS=1000 `
  -e WARMUPS=20 `
  -e ORDER_POLICY=rotate `
  -e ORDER_SEED=42 `
  -v "${PWD}\benchmark.py:/app/benchmark.py:ro" `
  -v "${PWD}\${EXP_DIR}:/app/${EXP_DIR}" `
  pqc-bench:1.0
```

### Configurable Environment Variables
- `RESULTS_DIR`: Target directory inside the container for outputs (default: `results`).
- `N_RUNS`: Number of timed trials per operation (default: `100`).
- `WARMUPS`: Number of unrecorded warm-up iterations executed prior to timing (default: `5`).
- `ORDER_POLICY`: Algorithm execution order policy:
  - `fixed`: deterministic default (`X25519 -> ML-KEM-768 -> ECDSA-P256 -> ML-DSA-65`)
  - `rotate`: cyclic permutation based on `ORDER_SEED`
  - `random`: pseudo-random permutation based on `ORDER_SEED`
- `ORDER_SEED`: Integer seed used for order rotation or randomization (default: `42`).
- `EXPERIMENT_ID`: User-defined identifier (default: `EXP_YYYYMMDD_HHMMSS`).
- `RUN_ID`: Unique run identifier (default: auto-generated UUID).

---

## 3. Generating Statistical Summaries & Plots

To generate latency and size charts from an experiment directory:
```powershell
python plot_results.py $EXP_DIR
```
Or inside Docker:
```powershell
docker run --rm -v "${PWD}:/app" pqc-bench:1.0 python plot_results.py $EXP_DIR
```

---

## 4. Stage D1: Cryptographic Artifact Size & Transmission Feasibility

To run the automated Stage D1 unit test suite:
```powershell
docker run --rm -v "${PWD}:/app" pqc-bench:1.0 python test_stage_d1.py
```

To run the full Stage D1 benchmark (characterization, message budgets, MTU fragmentation, loopback transport benchmark, plot generation, and report compilation):
```powershell
python run_stage_d1.py
```
For a rapid smoke validation:
```powershell
python run_stage_d1.py --smoke
```

---

## 5. Stage D2: Cold-Start vs. Steady-State Cryptographic Profiling

To run the automated Stage D2 unit test suite:
```powershell
docker run --rm -v "${PWD}:/app" pqc-bench:1.0 python test_stage_d2.py
```

To run the full Stage D2 benchmark (subprocess startup profiling, library import hierarchy, object construction, first-operation cold penalties vs steady-state across 25 independent processes per condition, plot generation, and report compilation):
```powershell
python run_stage_d2.py
```

For a rapid smoke validation:
```powershell
python run_stage_d2.py --smoke
```

To regenerate plots and scientific report from an existing experiment directory without rerunning measurements:
```powershell
python run_stage_d2.py --report-only experiments/EXP_STAGE_D2_COLDSTART_<TIMESTAMP>
```

---

## 6. Stage E: Embedded ARM Cortex-M4 & Host-Native C Benchmarking

Stage E transitions the research from high-level Python APIs to low-level native execution and embedded microcontroller environments:
- **Host-Native C Reference Suite (`stage_e_embedded/host_reference/`):** High-resolution monotonic timing of compiled C implementations (`gcc -O3`, `liboqs` 0.16.0, OpenSSL 3.5.7), isolating a **~3.5 to 7.5 µs Python CFFI wrapper tax** (+34.7% overhead on ML-KEM encapsulation).
- **ARM Cortex-M4 Firmware Harness (`stage_e_embedded/firmware/source/`):** Complete embedded C harness for STM32F407VG featuring DWT cycle counting with barrier instructions (`__DSB()`, `__ISB()`), dynamic stack watermarking (`0x5A5A5A5A` canary spray), USART2 streaming CSV telemetry, and standalone linker script (`stm32f407vg.ld`).
- **Upstream PQM4 Framework Audit (`stage_e_embedded/pqm4/`):** Pinned commit `6ff2be970f6f4592b341d432042063ceacf424a2`, evaluated 24 MHz 0-wait-state clocking vs 168 MHz performance, SysTick 64-bit overflow ISR timing, and documented PQM4's lack of classical ECC schemes and planned archiving in January 2027.
- **Hardware Status & Scientific Non-Fabrication:** Automated host audit confirmed zero physical STM32 development boards connected. Adhering to scientific integrity rules, zero physical cycle counts were fabricated, and `stage_e_embedded/results/stm32f4_physical/` remains unpopulated pending physical hardware connection.

For complete execution instructions, reproduction steps, and analysis scripts, refer to:
- [`stage_e_embedded/README.md`](file:///d:/Cyber-security/pqc_first_experiment/stage_e_embedded/README.md)
- [`stage_e_embedded/docs/RESULTS_AND_LIMITATIONS.md`](file:///d:/Cyber-security/pqc_first_experiment/stage_e_embedded/docs/RESULTS_AND_LIMITATIONS.md)

---

## 7. Experiment Outputs

Each experiment directory contains:
- `benchmark_raw.csv`: Raw trial-by-trial observations including monotonic nanoseconds (`elapsed_ns`), microseconds (`time_us`), trial index, execution order, artifact sizes, and correctness status.
- `benchmark_summary.csv`: Aggregated statistics including sample counts, median, mean, standard deviation, min, max, P90, P95, P99, Interquartile Range (IQR), Median Absolute Deviation (MAD), and artifact sizes.
- `run_manifest.json`: Complete machine-readable metadata capture: Python compiler, OS, architecture, package versions (liboqs, cryptography, OpenSSL), cgroup configurations, CPU throttling stats, and correctness validation records.
- `resource_usage.json`: Detailed snapshots of cold-start and post-benchmark peak process RSS, cgroup memory current, and CFS throttling counters.
- `kem_timing.png` & `signature_timing.png`: Category-isolated timing bar plots.
- `public_key_sizes.png` & `ciphertext_signature_sizes.png`: Artifact size comparisons.

---

## 8. Research Documentation

- `RESEARCH_STATUS.md`: Current project status, completed milestones, open questions, and anomaly findings.
- `EXPERIMENT_PROTOCOL.md`: Comprehensive experimental protocol, timing boundaries, correctness checks, and data preservation standards.
- `EXPERIMENT_LOG.md`: Chronological log of all historical and new experiment executions.
- `analyze_repeats.py`: Cross-run repetition analysis with corrected 100-trial block grouping and observation counts.
- `stage_e_embedded/`: Dedicated Stage E workspace for host-native C and embedded ARM Cortex-M4 benchmarking.

---

## 9. Scientific & Cryptographic Accuracy Notes
- **Key Establishment:** ML-KEM-768 is a Key Encapsulation Mechanism (NIST FIPS 203) establishing a 32-byte shared secret; it does not directly encrypt arbitrary plaintext messages. X25519 is an Elliptic-Curve Diffie-Hellman key agreement mechanism (RFC 7748).
- **Digital Signatures:** ML-DSA-65 is a lattice-based digital signature algorithm (NIST FIPS 204). ECDSA P-256 is an elliptic-curve digital signature algorithm (NIST FIPS 186-5).
- **Timing Scope:** Python API measurements reflect *Python API-level elapsed time* via `time.perf_counter_ns()`, including library binding wrappers and C-extension overhead. Native C measurements in Stage E isolate the underlying cryptographic execution.
- **Hardware Limitations:** Docker container quotas (`--cpus`, `--memory`) set OS resource limits inside a WSL2 virtual machine on the host; they do not emulate physical microcontroller architectures (e.g., ARM Cortex-M, RISC-V). Bare-metal evaluation requires verified physical boards or explicitly tagged emulator validation.
