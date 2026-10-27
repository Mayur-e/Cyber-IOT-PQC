# Stage D1 Scientific Report: Cryptographic Artifact Size, Serialization, and Transmission Feasibility

**Project Title:** Empirical Migration Feasibility Analysis of Post-Quantum Cryptography for Resource-Constrained Systems  
**Experiment ID:** `EXP_STAGE_D1_ARTIFACTS_20261025_214841`  
**Execution Timestamp:** `2026-10-25 21:49:00 UTC`  
**Target Directory:** [`EXP_STAGE_D1_ARTIFACTS_20261025_214841`](file:///D:/Cyber-security/pqc_first_experiment/experiments/EXP_STAGE_D1_ARTIFACTS_20261025_214841)  
**Evaluation Scope:** Exact serialized byte footprints, message exchange flows (Scenarios K1 & K2), application payload expansion (16B–4096B), link-layer fragmentation (Ethernet 1500B vs 6LoWPAN 128B), and local TCP loopback transfer microbenchmarks.

---

## 1. Executive Summary

Stage D1 provides empirical quantification of the communication overhead incurred when migrating from classical primitives (**X25519**, **ECDSA P-256**) to post-quantum standards (**ML-KEM-768**, **ML-DSA-65**).

A total of **13,000 artifact measurements** across 1000 samples per primitive and **2,000 loopback transfer trials** were executed under Docker containerization (`pqc-bench:1.0`, Python 3.12.15, liboqs 0.16.0, OpenSSL 3.5.7). All tests and validations passed with **100% cryptographic correctness**.

### Key Scientific Findings:
1. **Public Key Expansion:**
   - **ML-KEM-768 public key (1,184 B)** is **37.0× larger** than the raw X25519 public key (32 B), and **26.9× larger** than X25519 SPKI DER (44 B). *(Directly measured)*
   - **ML-DSA-65 public key (1,952 B)** is **30.0× larger** than uncompressed ECDSA P-256 (65 B), and **59.2× larger** than compressed ECDSA P-256 (33 B). *(Directly measured)*
2. **Signature & Ciphertext Expansion:**
   - **ML-DSA-65 signature (3,309 B)** is **46.6× larger** than the mean ECDSA P-256 DER signature (71.0 B, range 69–72 B), and **51.7× larger** than IEEE P1363 raw signature (64 B). *(Directly measured)*
   - **ML-KEM-768 encapsulation ciphertext (1,088 B)** carries vector $u$ and scalar $v$, whereas X25519 produces zero ciphertext (shared secret derived directly via scalar multiplication). *(Directly measured)*
3. **Key-Establishment Message Budgets:**
   - **Scenario K1 (Pre-shared Recipient PK):** Initiator transmits 32 B for X25519 vs. 1,088 B for ML-KEM-768 (**34.0× expansion**). *(Calculated from measured values)*
   - **Scenario K2 (Interactive 2-Way Handshake):** Total exchange is 64 B for X25519 vs. 2,272 B for ML-KEM-768 (**35.5× expansion**). *(Calculated from measured values)*
4. **Fragmentation Crisis on Constrained Links (6LoWPAN / IEEE 802.15.4):**
   - On a nominal 128-byte 6LoWPAN frame with 48B header/security overhead (80B usable payload), a single **ML-DSA-65 signature requires 42 fragments** (generating **2,016 bytes of header overhead**, a **60.9% transmission penalty**). In contrast, an ECDSA P-256 signature fits into **1 single frame** with 0 fragmentation. *(Model-dependent estimate)*
   - An **ML-KEM-768 public key requires 15 fragments**; encapsulation ciphertext requires **14 fragments**.
   - On 1500-byte Ethernet MTU, all individual artifacts fit into 1 frame, except for ML-DSA-65 signatures (3,309 B) and ML-KEM 2-way handshakes (2,272 B), which require 2–3 frames depending on transport overhead. *(Model-dependent estimate)*
5. **Local Transport vs. Physical IoT Realities:**
   - On local TCP loopback (`127.0.0.1`), transmitting 3,309 bytes requires only **99.85 µs** (achieving **31.6 MB/s** throughput).
   - **Critical Distinction:** Loopback transfer times reflect memory copy rates in Linux kernel buffers. On physical low-power radio links (e.g. 250 kbps 802.15.4), transmitting 42 fragments of ML-DSA-65 requires over **170 milliseconds of continuous radio-on airtime** without accounting for CSMA/CA backoff, packet collisions, or retransmissions. *(Model-dependent estimate vs Directly measured loopback)*

---

## 2. Environment & Instrumentation

- **Host Processor:** AMD Ryzen 7 7435HS (8 Cores, 16 Threads, 3.1 GHz Base)
- **Container Environment:** `pqc-bench:1.0` (Debian Linux, kernel 6.6.114.1 WSL2)
- **Software Versions:**
  - Python: `3.12.15`
  - liboqs: `0.16.0`
  - cryptography: `50.0.2`
  - OpenSSL: `OpenSSL 3.5.7 9 Jun 2026`
- **High-Resolution Clock:** Monotonic nanosecond timing via `time.perf_counter_ns()`
- **TCP Socket Options:** `127.0.0.1`, `TCP_NODELAY=1`, 4-byte big-endian framing (`>I`)

---

## 3. Experiment D1-A: Cryptographic Artifact Size Characterization

Measurements compiled from [EXP_STAGE_D1_ARTIFACTS_20261025_214841/artifact_summary.csv](file:///D:/Cyber-security/pqc_first_experiment/experiments/EXP_STAGE_D1_ARTIFACTS_20261025_214841/artifact_summary.csv):

| Algorithm | Category | Artifact Type | Encoding | Representation | Sample Count | Fixed? | Min (B) | Max (B) | Mean (B) | Median (B) | Std (B) |
|---|---|---|---|---|---:|:---:|---:|---:|---:|---:|---:|
| **ECDSA-P256** | Digital Signature | `public_key` | `DER_SPKI` | SubjectPublicKeyInfo DER | 1000 | Yes | 91 | 91 | 91.0 | 91.0 | 0.0 |
| **ECDSA-P256** | Digital Signature | `public_key` | `X962_Compressed` | ANSI X9.62 compressed point 0x02/0x03||X | 1000 | Yes | 33 | 33 | 33.0 | 33.0 | 0.0 |
| **ECDSA-P256** | Digital Signature | `public_key` | `X962_Uncompressed` | ANSI X9.62 uncompressed point 0x04||X||Y | 1000 | Yes | 65 | 65 | 65.0 | 65.0 | 0.0 |
| **ECDSA-P256** | Digital Signature | `signature` | `DER` | ASN.1 DER sequence of (r, s) | 1000 | **No (Var)** | 69 | 72 | 71.018 | 71.0 | 0.713 |
| **ECDSA-P256** | Digital Signature | `signature` | `IEEE_P1363` | Fixed-width raw r || s (32B + 32B) | 1000 | Yes | 64 | 64 | 64.0 | 64.0 | 0.0 |
| **ML-DSA-65** | Digital Signature | `public_key` | `Raw` | FIPS 204 verification key (raw bytes) | 1000 | Yes | 1952 | 1952 | 1952.0 | 1952.0 | 0.0 |
| **ML-DSA-65** | Digital Signature | `signature` | `Raw` | FIPS 204 signature (raw bytes) | 1000 | Yes | 3309 | 3309 | 3309.0 | 3309.0 | 0.0 |
| **ML-KEM-768** | KEM | `ciphertext` | `Raw` | FIPS 203 encapsulation ciphertext (raw bytes) | 1000 | Yes | 1088 | 1088 | 1088.0 | 1088.0 | 0.0 |
| **ML-KEM-768** | KEM | `public_key` | `Raw` | FIPS 203 encapsulation key (raw bytes) | 1000 | Yes | 1184 | 1184 | 1184.0 | 1184.0 | 0.0 |
| **ML-KEM-768** | KEM | `shared_secret` | `Raw` | FIPS 203 shared secret (raw bytes) | 1000 | Yes | 32 | 32 | 32.0 | 32.0 | 0.0 |
| **X25519** | Key Agreement | `public_key` | `DER_SPKI` | SubjectPublicKeyInfo DER | 1000 | Yes | 44 | 44 | 44.0 | 44.0 | 0.0 |
| **X25519** | Key Agreement | `public_key` | `Raw` | Curve25519 point (raw bytes) | 1000 | Yes | 32 | 32 | 32.0 | 32.0 | 0.0 |
| **X25519** | Key Agreement | `shared_secret` | `Raw` | Shared Secret (raw bytes) | 1000 | Yes | 32 | 32 | 32.0 | 32.0 | 0.0 |

### Empirical Distribution of ECDSA P-256 DER Signatures:
- Unlike post-quantum signatures which are fixed at standard block lengths, ASN.1 DER-encoded ECDSA signatures have variable lengths:
  - **70 Bytes:** $1000$ total samples analyzed.
  - Across 1000 samples: Min = **69 B**, Max = **72 B**, Mean = **71.02 B** ($P_{95} = 72$ B, $P_{99} = 72$ B).
  - Variations arise due to ASN.1 INTEGER leading zero-padding when the most significant bit of $r$ or $s$ is 1.

---

## 4. Experiment D1-B: Message-Flow & Transmission Budgets

Compiled from [EXP_STAGE_D1_ARTIFACTS_20261025_214841/message_budget.csv](file:///D:/Cyber-security/pqc_first_experiment/experiments/EXP_STAGE_D1_ARTIFACTS_20261025_214841/message_budget.csv):

### 4.1 Model 1: Direct Artifact Comparison

| Scenario | Category | Classical Description | Classical (B) | PQC Description | PQC (B) | Expansion Ratio |
|---|---|---|---:|---|---:|---:|
| Public Key Comparison | Key Establishment | X25519 Public Key (Raw) | 32.0 | ML-KEM-768 Public Key (Raw) | 1184 | **37.0×** |
| Key Establishment Response Artifact | Key Establishment | X25519 Peer Public Key (Raw) | 32.0 | ML-KEM-768 Encapsulation Ciphertext (Raw) | 1088 | **34.0×** |
| Digital Signature Comparison (DER) | Digital Signature | ECDSA P-256 Signature (DER) | 71.0 | ML-DSA-65 Signature (Raw) | 3309 | **46.59×** |
| Digital Signature Comparison (IEEE P1363) | Digital Signature | ECDSA P-256 Signature (IEEE P1363 Raw r||s) | 64.0 | ML-DSA-65 Signature (Raw) | 3309 | **51.7×** |
| Signature Verification Key Comparison | Digital Signature | ECDSA P-256 Public Key (Uncompressed X9.62) | 65.0 | ML-DSA-65 Public Key (Raw) | 1952 | **30.03×** |

### 4.2 Model 2: Key-Establishment Message Exchanges

| Scenario | Classical Flow | Classical Total (B) | PQC Flow | PQC Total (B) | Expansion Ratio |
|---|---|---:|---|---:|---:|
| **Scenario K1: Pre-shared Recipient Public Key** | Initiator sends ephemeral X25519 PK | 32.0 | Initiator sends ML-KEM-768 Ciphertext | 1088 | **34.0×** |
| **Scenario K2: 2-Way Handshake (PK + Reply)** | X25519 PK (32B) + X25519 PK (32B) | 64.0 | ML-KEM-768 PK (1184B) + ML-KEM-768 CT (1088B) | 2272 | **35.5×** |

### 4.3 Model 3: Signed Message Transmission (Pre-Shared PK vs Included PK)

| Payload Size | Classical (Pre-Shared PK) | PQC (Pre-Shared PK) | Expansion | Classical (PK Included) | PQC (PK Included) | Expansion |
|---:|---:|---:|---:|---:|---:|---:|
| **16 B** | 87 B | 3325 B | **38.21×** | 152 B | 5277 B | **34.71×** |
| **32 B** | 103 B | 3341 B | **32.43×** | 168 B | 5293 B | **31.5×** |
| **64 B** | 135 B | 3373 B | **24.98×** | 200 B | 5325 B | **26.62×** |
| **128 B** | 199 B | 3437 B | **17.27×** | 264 B | 5389 B | **20.41×** |
| **256 B** | 327 B | 3565 B | **10.9×** | 392 B | 5517 B | **14.07×** |
| **512 B** | 583 B | 3821 B | **6.55×** | 648 B | 5773 B | **8.91×** |
| **1024 B** | 1095 B | 4333 B | **3.96×** | 1160 B | 6285 B | **5.42×** |
| **4096 B** | 4167 B | 7405 B | **1.78×** | 4232 B | 9357 B | **2.21×** |

**Key Insight:** For small telemetry messages typical of IoT sensors (e.g. 16–32 bytes), ML-DSA-65 introduces an astonishing **10,000% to 20,000% overhead** above payload size, transmitting 3.3 KB of signature for 16 bytes of telemetry data.

---

## 5. Experiment D1-C: MTU and Link-Layer Fragmentation Modeling

Compiled from [EXP_STAGE_D1_ARTIFACTS_20261025_214841/fragmentation_analysis.csv](file:///D:/Cyber-security/pqc_first_experiment/experiments/EXP_STAGE_D1_ARTIFACTS_20261025_214841/fragmentation_analysis.csv):

| Artifact / Message Flow | Size (B) | Ethernet IPv6/UDP (1500B / 1452B Usable) | 6LoWPAN Basic (128B / 103B Usable) | 6LoWPAN Secure Mesh (128B / 80B Usable) | 6LoWPAN Total Tx Bytes (Secure) |
|---|---:|:---:|:---:|:---:|---:|
| `X25519 Public Key (Raw)` | 32 | 1 frame (OK) | 1 frame | 1 frame | **80 B** (+150.0%) |
| `X25519 2-Way Handshake (2x PK)` | 64 | 1 frame (OK) | 1 frame | 1 frame | **112 B** (+75.0%) |
| `ML-KEM-768 Public Key (Raw)` | 1184 | 1 frame (OK) | **12 frags** | **15 frags** | **1904 B** (+60.8%) |
| `ML-KEM-768 Ciphertext (Raw)` | 1088 | 1 frame (OK) | **11 frags** | **14 frags** | **1760 B** (+61.8%) |
| `ML-KEM-768 2-Way Handshake (PK + CT)` | 2272 | 2 frag | **23 frags** | **29 frags** | **3664 B** (+61.3%) |
| `ECDSA-P256 Signature (DER Mean)` | 71 | 1 frame (OK) | 1 frame | 1 frame | **119 B** (+67.6%) |
| `ECDSA-P256 Signed Msg (128B payload + DER sig)` | 199 | 1 frame (OK) | **2 frags** | **3 frags** | **343 B** (+72.4%) |
| `ML-DSA-65 Signature (Raw)` | 3309 | 3 frag | **33 frags** | **42 frags** | **5325 B** (+60.9%) |
| `ML-DSA-65 Signed Msg (128B payload + sig)` | 3437 | 3 frag | **34 frags** | **43 frags** | **5501 B** (+60.1%) |
| `ML-DSA-65 Self-Contained Msg (128B + PK + sig)` | 5389 | 4 frag | **53 frags** | **68 frags** | **8653 B** (+60.6%) |

---

## 6. Experiment D1-D: Local TCP Loopback Microbenchmark

Measurements compiled from [EXP_STAGE_D1_ARTIFACTS_20261025_214841/transport_summary.csv](file:///D:/Cyber-security/pqc_first_experiment/experiments/EXP_STAGE_D1_ARTIFACTS_20261025_214841/transport_summary.csv) (100 trials per condition):

| Condition Label | Category | Payload (B) | Median Latency (µs) | Mean Latency (µs) | P95 Latency (µs) | Median RTT (µs) | Median Throughput (MB/s) | Verified? |
|---|---|---:|---:|---:|---:|---:|---:|:---:|
| `X25519_PK` | Artifact_Key | 32 | 103.72 | 118.56 | 166.75 | 190.62 | **0.3** | OK |
| `ECDSA_PK_Uncompressed` | Artifact_Key | 65 | 103.58 | 110.26 | 157.79 | 192.60 | **0.6** | OK |
| `ECDSA_Sig_DER` | Artifact_Sig | 71 | 96.63 | 105.22 | 142.31 | 187.02 | **0.7** | OK |
| `MLKEM_PK` | Artifact_Key | 1184 | 99.83 | 105.45 | 154.35 | 189.92 | **11.3** | OK |
| `MLKEM_CT` | Artifact_CT | 1088 | 105.77 | 121.24 | 190.11 | 201.19 | **9.8** | OK |
| `MLDSA_PK` | Artifact_Key | 1952 | 99.69 | 108.56 | 161.00 | 188.16 | **18.7** | OK |
| `MLDSA_Sig` | Artifact_Sig | 3309 | 99.85 | 105.91 | 136.94 | 186.01 | **31.6** | OK |
| `Scenario_K1_X25519` | Scenario_KEM | 32 | 101.09 | 113.67 | 182.43 | 191.91 | **0.3** | OK |
| `Scenario_K1_MLKEM` | Scenario_KEM | 1088 | 102.38 | 118.17 | 146.46 | 191.03 | **10.1** | OK |
| `Scenario_K2_X25519_2Way` | Scenario_KEM | 64 | 97.86 | 104.17 | 156.47 | 186.85 | **0.6** | OK |
| `Scenario_K2_MLKEM_2Way` | Scenario_KEM | 2272 | 99.69 | 106.73 | 139.84 | 182.05 | **21.7** | OK |
| `Payload_16B` | Payload_Sweep | 16 | 101.72 | 110.70 | 144.24 | 186.16 | **0.1** | OK |
| `Payload_32B` | Payload_Sweep | 32 | 100.69 | 115.09 | 170.78 | 192.40 | **0.3** | OK |
| `Payload_64B` | Payload_Sweep | 64 | 99.57 | 105.07 | 139.71 | 184.20 | **0.6** | OK |
| `Payload_128B` | Payload_Sweep | 128 | 95.97 | 108.92 | 158.85 | 182.59 | **1.3** | OK |
| `Payload_256B` | Payload_Sweep | 256 | 98.58 | 107.72 | 164.92 | 188.96 | **2.5** | OK |
| `Payload_512B` | Payload_Sweep | 512 | 94.90 | 103.46 | 139.43 | 178.86 | **5.1** | OK |
| `Payload_1024B` | Payload_Sweep | 1024 | 100.63 | 109.97 | 155.13 | 189.63 | **9.7** | OK |
| `Payload_2048B` | Payload_Sweep | 2048 | 101.71 | 106.64 | 155.20 | 191.09 | **19.2** | OK |
| `Payload_4096B` | Payload_Sweep | 4096 | 98.03 | 107.05 | 148.06 | 188.65 | **39.8** | OK |

---

## 7. Publication-Quality Visualizations

The following 7 scientific figures have been generated and archived in [EXP_STAGE_D1_ARTIFACTS_20261025_214841/](file:///D:/Cyber-security/pqc_first_experiment/experiments/EXP_STAGE_D1_ARTIFACTS_20261025_214841):

1. **Figure 1:** Public-key and signature size comparison across classical and post-quantum algorithms (Log Scale).  
   Link: [plot1_pubkey_and_signature_size_comparison.png](file:///D:/Cyber-security/pqc_first_experiment/experiments/EXP_STAGE_D1_ARTIFACTS_20261025_214841/plot1_pubkey_and_signature_size_comparison.png)
2. **Figure 2:** Key establishment transmitted artifacts (ML-KEM-768 PK & CT vs X25519 PK).  
   Link: [plot2_mlkem_pk_and_ct_comparison.png](file:///D:/Cyber-security/pqc_first_experiment/experiments/EXP_STAGE_D1_ARTIFACTS_20261025_214841/plot2_mlkem_pk_and_ct_comparison.png)
3. **Figure 3:** Signed message total bytes and relative cryptographic overhead (%) versus application payload size.  
   Link: [plot3_message_overhead_vs_payload_size.png](file:///D:/Cyber-security/pqc_first_experiment/experiments/EXP_STAGE_D1_ARTIFACTS_20261025_214841/plot3_message_overhead_vs_payload_size.png)
4. **Figure 4:** Modeled link-layer packet fragmentation count: Ethernet MTU (1500B) vs. 6LoWPAN (128B).  
   Link: [plot4_fragmentation_counts_ethernet_and_6lowpan.png](file:///D:/Cyber-security/pqc_first_experiment/experiments/EXP_STAGE_D1_ARTIFACTS_20261025_214841/plot4_fragmentation_counts_ethernet_and_6lowpan.png)
5. **Figure 5:** Measured local TCP loopback transfer latency across parametric payload sizes with cryptographic artifact overlays.  
   Link: [plot5_measured_loopback_latency_vs_payload.png](file:///D:/Cyber-security/pqc_first_experiment/experiments/EXP_STAGE_D1_ARTIFACTS_20261025_214841/plot5_measured_loopback_latency_vs_payload.png)
6. **Figure 6:** Measured effective TCP loopback throughput (MB/s) versus payload size.  
   Link: [plot6_loopback_throughput_vs_payload.png](file:///D:/Cyber-security/pqc_first_experiment/experiments/EXP_STAGE_D1_ARTIFACTS_20261025_214841/plot6_loopback_throughput_vs_payload.png)
7. **Figure 7:** Frequency distribution of variable ECDSA P-256 DER signature lengths ($N=1000$ samples).  
   Link: [plot7_ecdsa_der_signature_length_distribution.png](file:///D:/Cyber-security/pqc_first_experiment/experiments/EXP_STAGE_D1_ARTIFACTS_20261025_214841/plot7_ecdsa_der_signature_length_distribution.png)

---

## 8. Epistemological Categorization & Scientific Limitations

To prevent over-generalization, each conclusion is strictly classified:

| Finding | Classification | Evidentiary Basis | Threat to Validity / Boundary Condition |
|---|---|---|---|
| **Serialized Artifact Sizes** | **Directly measured** | Exact byte lengths recorded across 1000 samples from liboqs and Python cryptography. | Standardized representations; negligible threat to validity. |
| **ECDSA DER Variance** | **Directly measured** | Min 69B, Max 72B observed across 1000 runs. | Characteristic of ASN.1 integer encoding; raw P1363 avoids variance. |
| **Message Exchange Totals** | **Calculated from measured values** | Computed from verified artifact combinations for Scenarios K1 and K2. | Excludes TLS record headers, TCP/IP headers, and certificate chains. |
| **Link Fragmentation Counts** | **Model-dependent estimate** | Mathematical ceiling division under standard 802.15.4 / 6LoWPAN header overhead assumptions. | Does not model real radio link quality, packet retransmissions, or variable 6LoWPAN compression state. |
| **Local Transfer Latency** | **Directly measured** | Loopback TCP socket transfers timed via `perf_counter_ns()`. | **NOT representative of physical IoT networks.** Measures kernel IPC buffer copy speed on an AMD Ryzen processor. |
| **Physical IoT Feasibility** | **Model-dependent estimate** | Derived mathematical extrapolation from link baud rates and fragmentation counts. | Physical verification requires hardware radio testbeds (e.g. Nordic nRF52840, ESP32). |

---

## 9. Recommendations for Stage D2 (Cold-Start & Initialization Overhead)

1. **Cold-Start Isolation:** Separate shared library loading (`liboqs.so`, `libcrypto.so`) and CFFI binding initialization from steady-state cryptographic loops.
2. **Key Generation vs. Operational Latency:** Profile memory allocation spikes during lattice polynomial sampling in first-call invocation.
3. **Protocol-Level Handshakes:** Transition from isolated artifact benchmarks to simulated TLS 1.3 handshake state machines evaluating hybrid `X25519MLKEM768`.
