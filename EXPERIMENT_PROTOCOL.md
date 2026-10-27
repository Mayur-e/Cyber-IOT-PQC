# Experiment Protocol: Empirical PQC Migration Feasibility Benchmark

## 1. Scope & Objective

This experimental protocol defines the scientific methodology, execution procedure, measurement boundaries, and reproducibility standards for benchmarking Post-Quantum Cryptography (PQC) primitives against classical counterparts under resource-constrained container environments.

The protocol evaluates:
1. **Key Establishment:** ML-KEM-768 (NIST FIPS 203) vs. X25519 (RFC 7748).
2. **Digital Signatures:** ML-DSA-65 (NIST FIPS 204) vs. ECDSA P-256 (NIST FIPS 186-5).

---

## 2. Cryptographic Specifications & Boundaries

### 2.1 Cryptographic Primitives
- **ML-KEM-768:** Standardized in NIST FIPS 203. Module-Lattice-based Key Encapsulation Mechanism. Security Category 3 (aiming to match or exceed AES-192 against classical and quantum attacks). Establishes a 32-byte symmetric shared secret. Does **not** directly encrypt application payloads.
- **ML-DSA-65:** Standardized in NIST FIPS 204. Module-Lattice-based Digital Signature Algorithm. Security Category 3.
- **X25519:** Elliptic-curve Diffie-Hellman key agreement over Curve25519 (RFC 7748). ~128-bit classical security. Vulnerable to polynomial-time discrete logarithm attacks on a cryptanalytically relevant quantum computer (Shor's algorithm).
- **ECDSA P-256:** Elliptic-curve digital signature algorithm over the NIST secp256r1 curve with SHA-256 (FIPS 186-5). ~128-bit classical security. Vulnerable to Shor's algorithm.

### 2.2 Timing Isolation & Instrumentation Boundaries
All timing measurements are performed using the monotonic high-resolution clock `time.perf_counter_ns()`.

To prevent measurement contamination:
- **X25519:**
  - *Keygen:* Measures only `x25519.X25519PrivateKey.generate()`. Public key raw byte serialization is executed outside the timed window.
  - *Derivation:* Peer private key generation and peer public key derivation are completed prior to timing. Only the scalar multiplication `priv.exchange(peer.public_key())` is timed.
- **ML-KEM-768:**
  - *Keygen:* Measures `kem.generate_keypair()`.
  - *Encapsulation:* Measures `kem.encap_secret(pk)`.
  - *Decapsulation:* Measures `kem.decap_secret(ct)`.
- **ECDSA P-256:**
  - *Keygen:* Measures `ec.generate_private_key(ec.SECP256R1())`. Public key export is outside the timing window.
  - *Sign:* Measures `priv.sign(MESSAGE, ec.ECDSA(hashes.SHA256()))`. Message initialization is static and outside timing.
  - *Verify:* Measures `pub.verify(signature, MESSAGE, ec.ECDSA(hashes.SHA256()))`.
- **ML-DSA-65:**
  - *Keygen:* Measures `signer.generate_keypair()`.
  - *Sign:* Measures `signer.sign(MESSAGE)`.
  - *Verify:* Measures `signer.verify(MESSAGE, signature, pk)`.

**Excluded from timing:** All CSV logging, memory inspection, file I/O, string formatting, correctness checks, and negative verification tests.

---

## 3. Correctness Verification Protocol

Correctness checks are executed for every trial outside the timing boundaries:
1. **ML-KEM-768:** Verifies that the client decapsulated shared secret exactly equals the server encapsulated shared secret (`ss_server == ss_client`).
2. **X25519:** Verifies mutual key agreement equality: party A's exchange with B's public key equals party B's exchange with A's public key (`priv.exchange(peer_pub) == peer.exchange(priv_pub)`), and confirms length is 32 bytes.
3. **ECDSA P-256:**
   - *Positive test:* Valid signature verifies successfully on `MESSAGE`.
   - *Negative test:* 1 bit/byte of `MESSAGE` is corrupted; verifies that `InvalidSignature` exception is raised.
4. **ML-DSA-65:**
   - *Positive test:* Valid signature verifies successfully on `MESSAGE`.
   - *Negative test:* 1 bit/byte of `MESSAGE` is corrupted; verifies that `signer.verify` returns `False`.

Any correctness failure halts execution or records a non-zero failure count in `run_manifest.json`.

---

## 4. Execution Order & Confounding Control

To detect and isolate host CPU dynamic frequency scaling (boost/P-state ramp-up), thermal throttling, and CFS quota boundary artifacts:
- The harness supports execution order policies configured via `ORDER_POLICY`:
  - `fixed`: deterministic sequence (`X25519 -> ML-KEM-768 -> ECDSA-P256 -> ML-DSA-65`).
  - `rotate`: cyclic permutation based on integer `ORDER_SEED`.
  - `random`: pseudo-random permutation generated via `random.Random(ORDER_SEED)`.
- The exact order and seed are recorded in `run_manifest.json` and in every row of `benchmark_raw.csv`.

---

## 5. Resource Telemetry Protocol

Direct telemetry is collected at process start (cold-start baseline) and immediately upon benchmark completion (post-execution state):
1. **Process Peak RSS:** Recorded via `resource.getrusage(resource.RUSAGE_SELF).ru_maxrss` (converted from KiB to bytes).
2. **Container Memory Usage:** Queried from `/sys/fs/cgroup/memory.current` (bytes).
3. **Container Memory Limit:** Queried from `/sys/fs/cgroup/memory.max` (bytes).
4. **Cgroup Memory Events:** Queried from `/sys/fs/cgroup/memory.events` (`oom`, `oom_kill`).
5. **CFS CPU Quota & Period:** Queried from `/sys/fs/cgroup/cpu.max`.
6. **CFS CPU Throttling:** Queried from `/sys/fs/cgroup/cpu.stat` (`nr_periods`, `nr_throttled`, `throttled_usec`).

---

## 6. Statistical Summaries

Per-operation metrics are compiled into `benchmark_summary.csv`:
- `samples`: sample count $N$
- `median_us`: 50th percentile (robust central tendency)
- `mean_us`: arithmetic mean
- `std_us`: sample standard deviation ($N-1$ degrees of freedom)
- `min_us`, `max_us`: range boundaries
- `p90_us`, `p95_us`, `p99_us`: tail latencies (computed with linear interpolation)
- `iqr_us`: Interquartile Range ($Q_3 - Q_1$)
- `mad_us`: Median Absolute Deviation ($\text{median}(|x_i - \tilde{x}|)$)

For repeated-run comparisons across multiple processes, run-level variation must be reported rather than pooling all trials as independent observations.

---

## 7. Data Preservation & Directory Standards

1. Historical data folders (`results_*`) are immutable and read-only.
2. New experiments must be stored in isolated directories:
   `experiments/EXP_YYYYMMDD_HHMMSS/`
3. Every experiment directory must contain:
   - `benchmark_raw.csv`: raw observations with monotonic nanoseconds, microseconds, and trial indices.
   - `benchmark_summary.csv`: aggregated statistical distribution metrics.
   - `run_manifest.json`: machine-readable environmental and configuration metadata.
   - `resource_usage.json`: isolated cgroup and process memory telemetry.

---

## 8. Stage D1 Protocol: Artifact Size, Serialization, and Transmission Feasibility

### 8.1 Measurement Scope
- **Actual Serialized Bytes:** Measures raw wire representations (not in-memory Python object wrappers or `sys.getsizeof`).
- **Key Establishment:**
  - X25519: Public key in raw 32-byte representation and SubjectPublicKeyInfo (SPKI) DER. Shared secret (32B).
  - ML-KEM-768: FIPS 203 public key (1,184B), encapsulation ciphertext (1,088B), and decapsulated shared secret (32B).
- **Digital Signatures:**
  - ECDSA P-256: Uncompressed point (65B), compressed point (33B), SubjectPublicKeyInfo (91B). Signatures measured in ASN.1 DER (variable 69–73B) and raw IEEE P1363 ($r||s$, 64B).
  - ML-DSA-65: FIPS 204 public key (1,952B) and signature (3,309B).

### 8.2 Protocol Flow & Message-Budget Modeling
- **Scenario K1 (Pre-shared Recipient Public Key):** Initiator sends ephemeral artifact (X25519 PK [32B] vs. ML-KEM ciphertext [1,088B]).
- **Scenario K2 (Interactive 2-Way Handshake):** Evaluates total bidirectional exchange (64B for X25519 vs. 2,272B for ML-KEM).
- **Signed Messages:** Evaluated across payload sizes from 16B to 4,096B with pre-shared and inline public key distribution options.

### 8.3 Fragmentation & Link-Layer Modeling
- Evaluates nominal 1500-byte Ethernet IP MTU and nominal 128-byte IEEE 802.15.4 / 6LoWPAN budgets.
- Implements Mode A (raw artifact planning) and Mode B (header-aware payload ceiling division).

### 8.4 Local Transport Microbenchmark
- Uses local TCP loopback (`127.0.0.1`, `TCP_NODELAY=1`).
- Requires strict 4-byte big-endian framing (`>I`) with looping `recv()` until exact length is consumed.
- Validates 100% byte-for-byte payload integrity.
---

## 9. Stage D2 Protocol: Cold-Start, Initialization, and Steady-State Cryptographic Profiling

### 9.1 Experimental Boundaries & Initialization Hierarchy
- **Process-Cold:** Freshly spawned operating system subprocess running Python 3.12 without prior state.
- **Import-Cold:** Isolated measurement of `import cryptography` and `import oqs` dynamic shared object loading via CFFI/dlopen.
- **Object-Cold:** First instantiation of cryptographic algorithm objects (`oqs.KeyEncapsulation`, `oqs.Signature`, `ec.generate_private_key`, `x25519.X25519PrivateKey`).
- **Operation-Cold:** The very first cryptographic operation executed after algorithm object instantiation.
- **Steady-State:** Repeated operations in the same process after a deterministic warm-up sequence ($N \ge 5$).

### 9.2 Operation Controls & Timing Isolation
- **Boundary Precision:** High-resolution monotonic timing using `time.perf_counter_ns()`.
- **Pre-computed Inputs:** Keys, test messages (fixed 64-byte payload), ciphertexts, and signatures for verification are generated outside the timed region.
- **Child-Parent Separation:** Parent-observed wall duration is recorded separately from child-internal timings to isolate OS fork/exec and pipe communication costs from internal Python and cryptographic execution.

### 9.3 Statistical Metrics & Mathematical Formulations
- **First-to-Steady Ratio:** $\text{Ratio} = \frac{\text{Median}(\text{First-Operation Latency})}{\text{Median}(\text{Steady-State Latency})}$
- **Cold Penalty Percentage:** $\text{Increase (\%)} = 100 \times \frac{\text{Median}(\text{First}) - \text{Median}(\text{Steady})}{\text{Median}(\text{Steady})}$
- **Between-Process Variability ($CoV_\text{proc}$):** $CoV_\text{proc} (\%) = 100 \times \frac{\sigma(\text{first-op})}{\mu(\text{first-op})}$
- **Tail Latencies:** $P_{90}, P_{95}, P_{99}$, IQR, and MAD calculated across all pooled steady-state observations.

### 9.4 Directory & Manifest Standards
- Directory: `experiments/EXP_STAGE_D2_COLDSTART_<UTC_TIMESTAMP>/`
- Output files: `d2_raw_startup.csv`, `d2_raw_operations.csv`, `d2_process_summary.csv`, `d2_summary.csv`, `d2_manifest.json`, `STAGE_D2_REPORT.md`, and 6 publication-quality figures (`plot1` through `plot6`).
