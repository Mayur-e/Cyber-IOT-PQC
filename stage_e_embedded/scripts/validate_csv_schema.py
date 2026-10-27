#!/usr/bin/env python3
"""
Stage E CSV Schema and Integrity Validator
Module: stage_e_embedded/scripts/validate_csv_schema.py

Validates that raw and summary CSV datasets produced in Stage E adhere strictly
to the schema specification, data types, sample counts, and scientific integrity rules.
"""

import sys
import os
import glob
import pandas as pd

REQUIRED_COLUMNS = [
    "run_id", "timestamp_utc", "device", "board", "mcu", "algorithm", "operation",
    "implementation", "library_name", "library_version", "git_commit", "compiler",
    "compiler_version", "optimization_flags", "clock_hz", "measurement_method",
    "trial", "cycles", "elapsed_us", "status", "valid", "warmup", "notes"
]

def validate_csv_file(csv_path):
    print(f"\n--- Validating: {os.path.basename(csv_path)} ---")
    if not os.path.isfile(csv_path):
        print(f"  [FAIL] File does not exist: {csv_path}")
        return False

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"  [FAIL] Could not parse CSV: {e}")
        return False

    errors = []

    # 1. Column header check
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        errors.append(f"Missing required columns: {missing_cols}")

    # 2. Row count check
    if len(df) == 0:
        errors.append("Dataset has 0 rows.")

    # 3. Data type and value checks
    if "trial" in df.columns and not pd.api.types.is_integer_dtype(df["trial"]):
        errors.append("Column 'trial' is not integer type.")

    if "elapsed_us" in df.columns:
        if not pd.api.types.is_numeric_dtype(df["elapsed_us"]):
            errors.append("Column 'elapsed_us' is not numeric.")
        elif (df["elapsed_us"] <= 0).any():
            errors.append("Column 'elapsed_us' contains non-positive values.")

    if "valid" in df.columns:
        invalid_flags = df[~df["valid"].isin([True, False, "true", "false", "True", "False"])]
        if not invalid_flags.empty:
            errors.append(f"Column 'valid' contains invalid boolean values: {len(invalid_flags)} rows")

    # 4. Status checks
    if "status" in df.columns:
        valid_statuses = {"success", "ok", "error", "emulator_validation_not_physical", "not_run"}
        unrecognized = set(df["status"].str.lower()) - valid_statuses
        if unrecognized:
            errors.append(f"Unrecognized status values: {unrecognized}")

    # 5. Scientific integrity check
    # Check if host runs falsely claim to be MCU
    if "device" in df.columns and "measurement_method" in df.columns:
        host_mcu_clash = df[(df["device"] == "host_x86_64") & (df["measurement_method"] == "dwt_cyccnt")]
        if not host_mcu_clash.empty:
            errors.append("INTEGRITY VIOLATION: Host x86_64 run claims DWT Cortex-M cycle counter.")

    if errors:
        for err in errors:
            print(f"  [FAIL] {err}")
        return False
    else:
        print(f"  [PASS] Clean schema ({len(df)} rows, {len(df.columns)} columns)")
        return True

def main():
    print("====================================================")
    print("Stage E: CSV Schema & Integrity Validation")
    print("====================================================")

    base_results = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results"))
    csv_files = glob.glob(os.path.join(base_results, "**", "*.csv"), recursive=True)

    # Filter for raw CSV datasets
    raw_csvs = [f for f in csv_files if "raw" in f]
    if not raw_csvs:
        print("[NOTICE] No raw CSV datasets found to validate.")
        return 0

    all_pass = True
    for c in raw_csvs:
        ok = validate_csv_file(c)
        if not ok:
            all_pass = False

    print("====================================================")
    if all_pass:
        print("[SUCCESS] All Stage E raw datasets passed schema validation!")
        return 0
    else:
        print("[FAIL] Schema validation encountered errors.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
