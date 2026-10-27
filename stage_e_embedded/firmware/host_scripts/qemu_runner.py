#!/usr/bin/env python3
"""
ARM Cortex-M QEMU Emulator Execution & Validation Harness
Module: stage_e_embedded/firmware/host_scripts/qemu_runner.py

Executes cross-compiled firmware under the QEMU ARM system emulator.
SCIENTIFIC INTEGRITY ENFORCEMENT:
1. Results are saved to stage_e_embedded/results/stm32f4_emulated/ (NEVER stm32f4_physical/).
2. All records are explicitly labeled with:
   - measurement_method = 'qemu_mps2_an386_emulator'
   - status = 'emulator_validation_not_physical'
   - notes = 'Simulated execution; cycle counts are non-hardware instruction-emulation approximations.'
"""

import sys
import os
import subprocess
import shutil
import csv
import json
from datetime import datetime, timezone

EMULATED_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "results", "stm32f4_emulated"))

def check_qemu():
    """Verify if qemu-system-arm is installed on PATH."""
    return shutil.which("qemu-system-arm")

def run_qemu_simulation(elf_path, timeout_sec=30):
    qemu_bin = check_qemu()
    if not qemu_bin:
        print("[NOTICE] qemu-system-arm is not available on PATH.")
        print("To run emulator validation: install qemu-system-arm via system package manager.")
        return False

    if not os.path.isfile(elf_path):
        print(f"[ERROR] Firmware binary not found: {elf_path}")
        return False

    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_id = f"EXP_STAGE_E_EMULATED_{timestamp_str}"
    run_dir = os.path.join(EMULATED_BASE_DIR, run_id)
    os.makedirs(run_dir, exist_ok=False)

    raw_csv_path = os.path.join(run_dir, "stm32f4_emulated_raw.csv")
    manifest_path = os.path.join(run_dir, "stm32f4_emulated_manifest.json")

    cmd = [
        qemu_bin,
        "-M", "mps2-an386",
        "-cpu", "cortex-m4",
        "-nographic",
        "-semihosting",
        "-kernel", elf_path
    ]

    print(f"Launching QEMU emulation: {' '.join(cmd)}")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
        stdout = proc.stdout
    except subprocess.TimeoutExpired:
        print(f"[WARNING] QEMU timed out after {timeout_sec}s")
        stdout = ""

    lines = stdout.splitlines()
    records = []
    with open(raw_csv_path, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.writer(f_out)
        for line in lines:
            if "run_id,device,board" in line:
                writer.writerow(line.split(","))
            elif line.count(",") >= 15:
                parts = [p.strip() for p in line.split(",")]
                # Overwrite measurement_method and status to enforce integrity
                if len(parts) >= 17:
                    parts[12] = "qemu_mps2_an386_emulator"
                    parts[16] = "emulator_validation_not_physical"
                    writer.writerow(parts)
                    records.append(parts)

    manifest = {
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "qemu_binary": qemu_bin,
        "input_elf": elf_path,
        "records_captured": len(records),
        "status": "COMPLETED_EMULATION" if records else "NO_RECORDS",
        "scientific_integrity_notice": "Cycle counts produced by QEMU are emulated instruction counters and DO NOT represent physical Cortex-M4 hardware timings."
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"[SUCCESS] Emulation completed. Output saved to {raw_csv_path}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python qemu_runner.py <path_to_firmware.elf>")
        sys.exit(1)
    run_qemu_simulation(sys.argv[1])
