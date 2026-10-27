# Stage E Environmental Audit & Toolchain Baseline

**Project Title:** Empirical Migration Feasibility Analysis of Post-Quantum Cryptography for Resource-Constrained Systems  
**Milestone:** Stage E — Embedded & Host-Native C Benchmarking  
**Audit Date:** 2026-10-26  

---

## 1. Host System Specifications

- **Processor:** AMD Ryzen 7 7435HS (8 physical cores, 16 logical threads, 3.10 GHz base clock, up to 4.50 GHz boost)
- **Host Operating System:** Windows 11 Home (64-bit)
- **Host Compilers & Build Tools:**
  - `gcc.exe`: MinGW GCC available (`C:\MinGW\bin\gcc.exe`, `D:\mingw64\bin\gcc.exe`)
  - `cmake.exe`: CMake 3.x available (`C:\Program Files\CMake\bin\cmake.exe`)
  - `git.exe`: Git for Windows 2.x (`D:\Git\cmd\git.exe`)
  - `python.exe`: Python 3.11.9 (`C:\Users\Mayuresh\AppData\Local\Programs\Python\Python311\python.exe`)
  - `arm-none-eabi-gcc`: Not present on Windows host PATH
  - `qemu-system-arm`: Not present on Windows host PATH
  - `openocd` / `st-flash`: Not present on Windows host PATH

---

## 2. Containerized Benchmark Environment

- **Container Engine:** Docker Desktop 29.5.2
- **Virtualization Backend:** WSL2 (Linux kernel 6.6.114.1-microsoft-standard-WSL2, cgroups v2 enabled)
- **Base Image:** `pqc-bench:1.0` (Debian GNU/Linux 12 / sid base)
- **Compilers & Interpreters:**
  - GCC: `gcc (Debian 14.2.0-19) 14.2.0` (`/usr/bin/gcc`)
  - GNU Make: `GNU Make 4.4.1` (`/usr/bin/make`)
  - CMake: `cmake version 3.31.5` (`/usr/bin/cmake`)
  - Python: `Python 3.12.15` (`/usr/local/bin/python3`)
- **Native Cryptographic Libraries (Host Reference):**
  - **`liboqs` 0.16.0:**
    - Headers: `/root/_oqs/include/oqs/` (`oqs.h`, `kem.h`, `sig.h`, `rand.h`, `common.h`)
    - Shared Library: `/root/_oqs/lib/liboqs.so` (version 0.16.0)
    - Available algorithms verified: `ML-KEM-768` (FIPS 203), `ML-DSA-65` (FIPS 204)
  - **OpenSSL `libcrypto` 3.5.7:**
    - Headers: `/usr/include/openssl/` (`evp.h`, `ec.h`, `crypto.h`)
    - Shared Library: `/usr/lib/x86_64-linux-gnu/libcrypto.so.3`
    - Available algorithms verified: `X25519` (RFC 7748), `ECDSA P-256` (FIPS 186-5)

---

## 3. Physical Hardware & Serial Interconnect Status

- **Host USB / PnP Enumeration:** Checked via `Win32_PnPEntity`. No ST-Link, J-Link, or STM32 hardware devices are currently enumerated on host USB.
- **Active COM / Serial Ports:** `[System.IO.Ports.SerialPort]::GetPortNames()` reports 0 active COM ports.
- **Hardware Availability Assumption:** Explicitly **NONE ASSUMED**. Hardware status is tracked as unverified/pending user confirmation. Physical MCU measurements will NOT be reported unless physical hardware is connected, programmed, and monitored.

---

## 4. Upstream Embedded Framework (PQM4)

- **Repository URL:** `https://github.com/mupq/pqm4.git`
- **Pinned Commit Hash:** `6ff2be970f6f4592b341d432042063ceacf424a2` (verified active upstream)
- **Primary Embedded Target Architecture:** ARM Cortex-M4 (`stm32f4discovery` / STM32F407VG)
- **Emulated Target Options in PQM4:** ARM Cortex-M4 on `mps2-an386` (QEMU target)
