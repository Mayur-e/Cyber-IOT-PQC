#!/usr/bin/env python3
"""
STM32F4 UART Serial Capture and Ingestion Harness
Module: stage_e_embedded/firmware/host_scripts/capture_serial.py

Listens to the ST-Link Virtual COM Port, captures streaming CSV telemetry records,
validates schema compliance, and saves verified raw datasets to stage_e_embedded/results/stm32f4_physical/.
"""

import sys
import os
import time
import argparse
import json
import csv
from datetime import datetime, timezone

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None

OUTPUT_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "results", "stm32f4_physical"))

EXPECTED_HEADER = [
    "run_id", "device", "board", "mcu", "algorithm", "operation", "implementation",
    "library_name", "library_version", "compiler", "opt_flags", "clock_hz",
    "measurement_method", "trial", "cycles", "elapsed_us", "status", "valid",
    "warmup", "stack_bytes", "notes"
]

def find_stlink_port():
    """Detect available ST-Link VCP COM ports."""
    if serial is None:
        return None
    ports = serial.tools.list_ports.comports()
    for port, desc, hwid in sorted(ports):
        if "STMicroelectronics" in desc or "ST-Link" in desc or "STM" in desc:
            return port
    # Fallback to first available port if only one exists
    if len(ports) == 1:
        return ports[0].device
    return None

def capture_stream(port_name, baud_rate=115200, timeout_sec=60):
    """Capture serial telemetry stream from connected board."""
    if serial is None:
        print("[ERROR] pyserial is not installed. Install via: pip install pyserial")
        sys.exit(1)

    print(f"Connecting to {port_name} at {baud_rate} baud...")
    ser = serial.Serial(port_name, baud_rate, timeout=2.0)
    time.sleep(0.5)

    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_id = f"EXP_STAGE_E_STM32F4_PHYSICAL_{timestamp_str}"
    run_dir = os.path.join(OUTPUT_BASE_DIR, run_id)
    os.makedirs(run_dir, exist_ok=False)

    raw_csv_path = os.path.join(run_dir, "stm32f4_physical_raw.csv")
    manifest_path = os.path.join(run_dir, "stm32f4_physical_manifest.json")

    records = []
    header_found = False
    start_time = time.time()

    print(f"Listening for telemetry... Run directory: {run_dir}")

    with open(raw_csv_path, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.writer(f_out)

        while (time.time() - start_time) < timeout_sec:
            line = ser.readline().decode("utf-8", errors="replace").strip()
            if not line:
                continue

            print(f"[UART] {line}")

            if "run_id,device,board" in line:
                writer.writerow(EXPECTED_HEADER)
                header_found = True
                continue

            if header_found and line.count(",") >= 15:
                parts = [p.strip() for p in line.split(",")]
                if len(parts) == len(EXPECTED_HEADER):
                    writer.writerow(parts)
                    records.append(parts)

            if "### BENCHMARK COMPLETE ###" in line:
                print("Benchmark completion marker received.")
                break

    ser.close()

    manifest = {
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "port": port_name,
        "baud_rate": baud_rate,
        "records_captured": len(records),
        "raw_csv": os.path.basename(raw_csv_path),
        "status": "COMPLETED" if records else "NO_RECORDS_CAPTURED"
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"[SUCCESS] Captured {len(records)} records saved to {raw_csv_path}")

def main():
    parser = argparse.ArgumentParser(description="Capture STM32F4 PQC Benchmark Telemetry")
    parser.add_argument("--port", type=str, default=None, help="Serial COM port (e.g., COM3, /dev/ttyACM0)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument("--timeout", type=int, default=60, help="Capture timeout in seconds")
    args = parser.parse_args()

    port = args.port or find_stlink_port()
    if not port:
        print("[NOTICE] No STM32 development board detected on host COM ports.")
        print("To run when hardware is connected: python capture_serial.py --port COMx")
        sys.exit(0)

    capture_stream(port, args.baud, args.timeout)

if __name__ == "__main__":
    main()
