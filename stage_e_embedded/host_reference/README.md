# Stage E: Host-Native C Cryptographic Reference Benchmark

**Project Title:** Empirical Migration Feasibility Analysis of Post-Quantum Cryptography for Resource-Constrained Systems  
**Module:** `stage_e_embedded/host_reference`  

---

## 1. Overview & Purpose

This module provides a standalone, high-performance C reference implementation measuring the execution latency of post-quantum and classical cryptographic algorithms directly at the native library interface level:
- **ML-KEM-768** (NIST FIPS 203) via `liboqs` 0.16.0 C API (`OQS_KEM_*`)
- **ML-DSA-65** (NIST FIPS 204) via `liboqs` 0.16.0 C API (`OQS_SIG_*`)
- **X25519** (RFC 7748) via OpenSSL 3.5.7 EVP C API (`EVP_PKEY_*`, `EVP_PKEY_derive`)
- **ECDSA P-256** (NIST FIPS 186-5) via OpenSSL 3.5.7 EVP C API (`EVP_DigestSign`, `EVP_DigestVerify`)

By compiling with `gcc -O3 -std=c11` and linking directly against native shared objects, this benchmark isolates pure algorithmic efficiency and memory management from Python interpreter overhead, dynamic typing, and CFFI wrapper latency.

---

## 2. Directory Structure

```
host_reference/
├── README.md               # This documentation
├── Makefile                # GCC build automation (clean, test, all)
├── include/
│   ├── benchmark_native.h  # Monotonic timing primitives & benchmark declarations
│   └── stats.h             # Distribution statistics calculation header
├── src/
│   ├── benchmark_native.c  # Benchmark runner emitting raw CSV rows
│   └── stats.c             # Statistical computations (median, IQR, MAD, P90, P95, P99)
├── tests/
│   └── test_native.c       # Automated unit & cryptographic invariant verification
└── scripts/
    └── run_host_c_benchmark.py # Orchestrator, data summarizer, and plot generator
```

---

## 3. Build & Test Instructions

### Inside Docker Container (`pqc-bench:1.0`):
```bash
cd /app/stage_e_embedded/host_reference
make clean
make test   # Compiles and runs 6/6 unit & invariant tests
make all    # Compiles bin/benchmark_native and bin/test_native
```

### Full Benchmark Execution & Analysis:
```bash
python /app/stage_e_embedded/host_reference/scripts/run_host_c_benchmark.py --trials 1000 --warmups 10
```

### From Windows Host (via Docker):
```powershell
docker run --rm -v "${PWD}:/app" -w /app pqc-bench:1.0 python stage_e_embedded/host_reference/scripts/run_host_c_benchmark.py --trials 1000 --warmups 10
```

---

## 4. Output Artifacts

Benchmark runs generate outputs in `stage_e_embedded/results/host_native_c/EXP_STAGE_E_HOST_C_<TIMESTAMP>/`:
1. `host_native_c_raw.csv`: Raw trial-by-trial measurements adhering to the project schema.
2. `host_native_c_summary.csv`: Aggregated distribution metrics across all tested operations.
3. `host_native_c_manifest.json`: Machine-readable environmental metadata and execution parameters.
4. `plot_native_c_latency.png`: Log-scale execution latency comparison across all 11 conditions.
5. `plot_native_c_vs_python.png`: Comparative analysis quantifying Python CFFI wrapper overhead against Stage D2 steady-state data.
