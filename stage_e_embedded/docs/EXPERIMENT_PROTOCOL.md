# Stage E Experimental Protocol: Embedded & Host-Native C Cryptographic Profiling

**Project Title:** Empirical Migration Feasibility Analysis of Post-Quantum Cryptography for Resource-Constrained Systems  
**Milestone:** Stage E — ARM Cortex-M4 Benchmarking & Host-Native C Reference  

---

## 1. Scientific Objectives

Stage E bridges the gap between high-level Python API profiling (Stages A–D2) and direct hardware execution:
1. **Host-Native C Reference:** Quantify pure algorithmic latency and memory footprint in compiled C, isolating cryptographic efficiency from Python interpreter overhead, dynamic typing, and CFFI wrapper penalties.
2. **Embedded Target Architecture:** Profile post-quantum and classical algorithms on resource-constrained 32-bit ARM Cortex-M4 architecture using CPU cycle counting (ARM DWT cycle counter) and SRAM stack usage tracking.
3. **Cross-Tier Separation:** Strictly prevent conflation between host container timings, compiled C host execution, emulated Cortex-M4 execution, and physical embedded microcontroller measurements.

---

## 2. Measurement Categories & Epistemological Boundaries

To preserve strict scientific reproducibility, all Stage E results belong to one of four mutually exclusive categories:

| Category | Execution Environment | Timing Primitive | Artifact Directory | Valid Claims |
|---|---|---|---|---|
| **CAT-1: Host Python API** | Docker WSL2 (`python3.12`) | `time.perf_counter_ns()` | `results/host_python_api/` | High-level application/service latency |
| **CAT-2: Host Native C** | Docker WSL2 native ELF (`gcc -O3`) | `clock_gettime(CLOCK_MONOTONIC_RAW)` | `results/host_native_c/` | Host baseline algorithmic efficiency without Python runtime overhead |
| **CAT-3: Physical Cortex-M4** | STM32F4 Hardware (Bare-Metal) | ARM DWT Cycle Counter (`DWT->CYCCNT`) | `results/stm32f4_physical/` | Physical embedded hardware feasibility, cycle counts, stack watermark |
| **CAT-4: Emulated Cortex-M4** | QEMU ARM Cortex-M Emulator | Virtual CPU clock / cycle counter | `results/stm32f4_emulated/` | Instruction trace and build validation only (Never physical hardware claims) |

---

## 3. Cryptographic Primitives & Evaluation Boundaries

### 3.1 Key Establishment
- **ML-KEM-768 (NIST FIPS 203):**
  - `keygen`: FIPS 203 keypair generation (`OQS_KEM_keypair`). Returns 1,184-byte public key and 2,400-byte secret key.
  - `encapsulation`: Encapsulation of 32-byte shared secret into 1,088-byte ciphertext (`OQS_KEM_encaps`).
  - `decapsulation`: Decapsulation of 1,088-byte ciphertext into 32-byte shared secret (`OQS_KEM_decaps`).
  - Correctness invariant: Decapsulated shared secret must match encapsulated shared secret byte-for-byte (`memcmp` == 0).
- **X25519 (RFC 7748):**
  - `keygen`: Ephemeral keypair creation (`EVP_PKEY_Q_keygen(NULL, NULL, "X25519")`).
  - `shared_secret_derivation`: Diffie-Hellman scalar multiplication (`EVP_PKEY_derive`).
  - Correctness invariant: Peer derived secrets must match byte-for-byte (32 bytes).

### 3.2 Digital Signatures
- **ML-DSA-65 (NIST FIPS 204):**
  - `keygen`: FIPS 204 verification keypair generation (`OQS_SIG_keypair`). Returns 1,952-byte public key and 4,032-byte secret key.
  - `sign`: Signature generation over fixed 64-byte payload (`OQS_SIG_sign`). Returns 3,309-byte signature.
  - `verify`: Verification of 3,309-byte signature against 1,952-byte public key (`OQS_SIG_verify`).
  - Correctness invariant: Valid signature returns success; single-byte mutated message returns failure.
- **ECDSA P-256 (NIST FIPS 186-5):**
  - `keygen`: SECP256R1 keypair creation (`EVP_PKEY_Q_keygen(NULL, NULL, "EC", "P-256")`).
  - `sign`: Deterministic ECDSA signature with SHA-256 over fixed 64-byte payload (`EVP_DigestSign`). Returns ASN.1 DER signature (~70–72 B).
  - `verify`: Verification against public key (`EVP_DigestVerify`).
  - Correctness invariant: Valid signature returns 1; mutated message returns 0.

---

## 4. Host-Native C Timing Methodology

1. **High-Resolution Clock:** Monotonic elapsed time measured via `clock_gettime(CLOCK_MONOTONIC_RAW, &ts)`.
2. **Boundary Isolation:** 
   - No `printf()`, file I/O, or heap allocation (`malloc`/`free`) inside the timed block.
   - Buffers pre-allocated and memory locked where possible.
   - For verification, valid signatures and public keys are prepared prior to starting the timer.
   - For decapsulation, valid ciphertext is prepared prior to starting the timer.
3. **Warm-Up and Repetitions:**
   - 10 unrecorded warm-up iterations executed per operation.
   - 1,000 recorded steady-state trials per operation.
   - First-operation cold invocation recorded separately in a dedicated run.

---

## 5. Embedded Cortex-M4 Timing Methodology (When Hardware Available)

1. **Cycle Counter:** ARM Cortex-M4 DWT (Data Watchpoint and Trace) cycle counter:
   ```c
   CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
   DWT->CYCCNT = 0;
   DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
   ```
2. **Timer Overflows:** 32-bit `DWT->CYCCNT` wraps every $2^{32} / 168\text{ MHz} \approx 25.5\text{ seconds}$. Operations exceeding counter capacity must use overflow interrupt handlers.
3. **Elapsed Time Derivation:**
   $$t_{\mu s} = \frac{C}{f_\text{Hz}} \times 10^6$$
   Clock frequency $f_\text{Hz}$ must be empirically validated via timer capture rather than assumed.
4. **Memory Measurement:**
   - Flash code footprint: `arm-none-eabi-size -B` (.text + .rodata).
   - Static RAM: .data + .bss.
   - Dynamic Stack Usage: Stack painting pattern (`0x5A5A5A5A`) and high-watermark inspection.

---

## 6. Raw Data Schema (CSV)

Each raw observation adheres to this standardized schema:
```csv
run_id,timestamp_utc,device,board,mcu,algorithm,operation,implementation,library_name,library_version,git_commit,compiler,compiler_version,optimization_flags,clock_hz,measurement_method,trial,cycles,elapsed_us,status,valid,warmup,notes
```

Field rules:
- `device`: `host_x86_64`, `stm32f4_physical`, or `stm32f4_qemu`.
- `board`: `host_workstation`, `stm32f4_discovery`, or `mps2_an386`.
- `mcu`: `AMD_Ryzen_7_7435HS`, `STM32F407VG`, or `Cortex-M4_QEMU`.
- `cycles`: Integer cycle count for MCU; `0` or `not_applicable` for host OS.
- `elapsed_us`: Microseconds elapsed, formatted to 3 decimal places.
- `status`: `OK`, `ERROR`, `UNSUPPORTED`, `NOT_RUN`.
- `valid`: Boolean `true`/`false` indicating cryptographic round-trip verification status.
