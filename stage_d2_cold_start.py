#!/usr/bin/env python3
"""
Stage D2: Cryptographic Cold-Start, Initialization, and Steady-State Profiling Engine
Empirical Migration Feasibility Analysis of Post-Quantum Cryptography for Resource-Constrained Systems

Implements:
- Experiment D2-A: Process Startup, Import Overhead, and Object Construction Profiling
- Experiment D2-B: First-Operation Latency vs. Steady-State Operation in Fresh Processes

Outputs:
- d2_raw_startup.csv
- d2_raw_operations.csv
- d2_process_summary.csv
- d2_summary.csv
- d2_manifest.json
"""

import argparse
import csv
import json
import math
import os
import platform
import resource
import ssl
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

TEST_MESSAGE = b"PQC migration feasibility benchmark - Stage D2 cold-start profiling fixed 64-byte message."

# ==============================================================================
# Helper Child Process Workers
# ==============================================================================

CHILD_WORKER_SCRIPT = """
import sys
import time
import json
import resource

# Read arguments from stdin
args = json.loads(sys.stdin.read())
mode = args["mode"]

def get_peak_rss_kib():
    try:
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except Exception:
        return 0

if mode == "startup_profiling":
    target = args["target"]
    t0 = time.perf_counter_ns()
    
    # Baseline timing
    t_std = t0
    t_import = t0
    t_obj = t0
    t_op = t0
    
    if target == "baseline_empty":
        t1 = time.perf_counter_ns()
        print(json.dumps({
            "target": target,
            "child_internal_ns": t1 - t0,
            "import_stdlib_ns": 0,
            "import_target_ns": 0,
            "object_init_ns": 0,
            "first_op_ns": 0,
            "peak_rss_kib": get_peak_rss_kib(),
            "correctness": True
        }))
        sys.exit(0)

    # Import standard library
    import math, os, statistics
    t_std = time.perf_counter_ns()
    
    if target == "baseline_stdlib":
        t1 = time.perf_counter_ns()
        print(json.dumps({
            "target": target,
            "child_internal_ns": t1 - t0,
            "import_stdlib_ns": t_std - t0,
            "import_target_ns": 0,
            "object_init_ns": 0,
            "first_op_ns": 0,
            "peak_rss_kib": get_peak_rss_kib(),
            "correctness": True
        }))
        sys.exit(0)
        
    if target == "import_cryptography":
        t_c0 = time.perf_counter_ns()
        import cryptography
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec, x25519
        t_import = time.perf_counter_ns()
        t1 = time.perf_counter_ns()
        print(json.dumps({
            "target": target,
            "child_internal_ns": t1 - t0,
            "import_stdlib_ns": t_std - t0,
            "import_target_ns": t_import - t_c0,
            "object_init_ns": 0,
            "first_op_ns": 0,
            "peak_rss_kib": get_peak_rss_kib(),
            "correctness": True
        }))
        sys.exit(0)

    if target == "import_oqs":
        t_o0 = time.perf_counter_ns()
        import oqs
        t_import = time.perf_counter_ns()
        t1 = time.perf_counter_ns()
        print(json.dumps({
            "target": target,
            "child_internal_ns": t1 - t0,
            "import_stdlib_ns": t_std - t0,
            "import_target_ns": t_import - t_o0,
            "object_init_ns": 0,
            "first_op_ns": 0,
            "peak_rss_kib": get_peak_rss_kib(),
            "correctness": True
        }))
        sys.exit(0)

    if target == "import_both":
        t_b0 = time.perf_counter_ns()
        import cryptography
        from cryptography.hazmat.primitives.asymmetric import ec, x25519
        import oqs
        t_import = time.perf_counter_ns()
        t1 = time.perf_counter_ns()
        print(json.dumps({
            "target": target,
            "child_internal_ns": t1 - t0,
            "import_stdlib_ns": t_std - t0,
            "import_target_ns": t_import - t_b0,
            "object_init_ns": 0,
            "first_op_ns": 0,
            "peak_rss_kib": get_peak_rss_kib(),
            "correctness": True
        }))
        sys.exit(0)

    if target == "init_x25519":
        t_c0 = time.perf_counter_ns()
        from cryptography.hazmat.primitives.asymmetric import x25519
        t_import = time.perf_counter_ns()
        # Object creation + keygen
        t_op0 = time.perf_counter_ns()
        k = x25519.X25519PrivateKey.generate()
        t_op1 = time.perf_counter_ns()
        t1 = time.perf_counter_ns()
        print(json.dumps({
            "target": target,
            "child_internal_ns": t1 - t0,
            "import_stdlib_ns": t_std - t0,
            "import_target_ns": t_import - t_c0,
            "object_init_ns": 0,
            "first_op_ns": t_op1 - t_op0,
            "peak_rss_kib": get_peak_rss_kib(),
            "correctness": bool(len(k.public_key().public_bytes_raw()) == 32)
        }))
        sys.exit(0)

    if target == "init_ecdsa":
        t_c0 = time.perf_counter_ns()
        from cryptography.hazmat.primitives.asymmetric import ec
        t_import = time.perf_counter_ns()
        # Curve parameter load
        t_obj0 = time.perf_counter_ns()
        curve = ec.SECP256R1()
        t_obj1 = time.perf_counter_ns()
        # First key generation
        t_op0 = time.perf_counter_ns()
        k = ec.generate_private_key(curve)
        t_op1 = time.perf_counter_ns()
        t1 = time.perf_counter_ns()
        print(json.dumps({
            "target": target,
            "child_internal_ns": t1 - t0,
            "import_stdlib_ns": t_std - t0,
            "import_target_ns": t_import - t_c0,
            "object_init_ns": t_obj1 - t_obj0,
            "first_op_ns": t_op1 - t_op0,
            "peak_rss_kib": get_peak_rss_kib(),
            "correctness": bool(k.key_size == 256)
        }))
        sys.exit(0)

    if target == "init_mlkem":
        t_o0 = time.perf_counter_ns()
        import oqs
        t_import = time.perf_counter_ns()
        # Algorithm object construction
        t_obj0 = time.perf_counter_ns()
        kem = oqs.KeyEncapsulation("ML-KEM-768")
        t_obj1 = time.perf_counter_ns()
        # First key generation
        t_op0 = time.perf_counter_ns()
        pk = kem.generate_keypair()
        t_op1 = time.perf_counter_ns()
        t1 = time.perf_counter_ns()
        print(json.dumps({
            "target": target,
            "child_internal_ns": t1 - t0,
            "import_stdlib_ns": t_std - t0,
            "import_target_ns": t_import - t_o0,
            "object_init_ns": t_obj1 - t_obj0,
            "first_op_ns": t_op1 - t_op0,
            "peak_rss_kib": get_peak_rss_kib(),
            "correctness": bool(len(pk) == 1184)
        }))
        sys.exit(0)

    if target == "init_mldsa":
        t_o0 = time.perf_counter_ns()
        import oqs
        t_import = time.perf_counter_ns()
        # Algorithm object construction
        t_obj0 = time.perf_counter_ns()
        signer = oqs.Signature("ML-DSA-65")
        t_obj1 = time.perf_counter_ns()
        # First key generation
        t_op0 = time.perf_counter_ns()
        pk = signer.generate_keypair()
        t_op1 = time.perf_counter_ns()
        t1 = time.perf_counter_ns()
        print(json.dumps({
            "target": target,
            "child_internal_ns": t1 - t0,
            "import_stdlib_ns": t_std - t0,
            "import_target_ns": t_import - t_o0,
            "object_init_ns": t_obj1 - t_obj0,
            "first_op_ns": t_op1 - t_op0,
            "peak_rss_kib": get_peak_rss_kib(),
            "correctness": bool(len(pk) == 1952)
        }))
        sys.exit(0)

elif mode == "operation_benchmark":
    algorithm = args["algorithm"]
    operation = args["operation"]
    warmups = args["warmups"]
    trials = args["trials"]
    message = args["message"].encode("utf-8")
    
    first_op_ns = 0
    steady_state_timings = []
    correctness_ok = True

    if algorithm == "X25519":
        from cryptography.hazmat.primitives.asymmetric import x25519
        if operation == "keygen":
            t0 = time.perf_counter_ns()
            k = x25519.X25519PrivateKey.generate()
            first_op_ns = time.perf_counter_ns() - t0
            correctness_ok = correctness_ok and (len(k.public_key().public_bytes_raw()) == 32)
            
            for _ in range(warmups):
                _ = x25519.X25519PrivateKey.generate()
                
            for _ in range(trials):
                t0 = time.perf_counter_ns()
                _ = x25519.X25519PrivateKey.generate()
                steady_state_timings.append(time.perf_counter_ns() - t0)

        elif operation == "shared_secret_derivation":
            # Prepare keys outside timed region
            priv_a = x25519.X25519PrivateKey.generate()
            priv_b = x25519.X25519PrivateKey.generate()
            pub_b = priv_b.public_key()
            
            t0 = time.perf_counter_ns()
            ss1 = priv_a.exchange(pub_b)
            first_op_ns = time.perf_counter_ns() - t0
            ss2 = priv_b.exchange(priv_a.public_key())
            correctness_ok = correctness_ok and (ss1 == ss2 and len(ss1) == 32)
            
            for _ in range(warmups):
                _ = priv_a.exchange(pub_b)
                
            for _ in range(trials):
                t0 = time.perf_counter_ns()
                _ = priv_a.exchange(pub_b)
                steady_state_timings.append(time.perf_counter_ns() - t0)

    elif algorithm == "ML-KEM-768":
        import oqs
        with oqs.KeyEncapsulation("ML-KEM-768") as kem:
            if operation == "keygen":
                t0 = time.perf_counter_ns()
                pk = kem.generate_keypair()
                first_op_ns = time.perf_counter_ns() - t0
                correctness_ok = correctness_ok and (len(pk) == 1184)
                
                for _ in range(warmups):
                    _ = kem.generate_keypair()
                    
                for _ in range(trials):
                    t0 = time.perf_counter_ns()
                    _ = kem.generate_keypair()
                    steady_state_timings.append(time.perf_counter_ns() - t0)

            elif operation == "encapsulation":
                pk = kem.generate_keypair()
                t0 = time.perf_counter_ns()
                ct, ss = kem.encap_secret(pk)
                first_op_ns = time.perf_counter_ns() - t0
                correctness_ok = correctness_ok and (len(ct) == 1088 and len(ss) == 32)
                
                for _ in range(warmups):
                    _ = kem.encap_secret(pk)
                    
                for _ in range(trials):
                    t0 = time.perf_counter_ns()
                    _ = kem.encap_secret(pk)
                    steady_state_timings.append(time.perf_counter_ns() - t0)

            elif operation == "decapsulation":
                pk = kem.generate_keypair()
                ct, ss_srv = kem.encap_secret(pk)
                t0 = time.perf_counter_ns()
                ss_cli = kem.decap_secret(ct)
                first_op_ns = time.perf_counter_ns() - t0
                correctness_ok = correctness_ok and (ss_srv == ss_cli)
                
                for _ in range(warmups):
                    _ = kem.decap_secret(ct)
                    
                for _ in range(trials):
                    t0 = time.perf_counter_ns()
                    _ = kem.decap_secret(ct)
                    steady_state_timings.append(time.perf_counter_ns() - t0)

    elif algorithm == "ECDSA-P256":
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import hashes
        curve = ec.SECP256R1()
        
        if operation == "keygen":
            t0 = time.perf_counter_ns()
            priv = ec.generate_private_key(curve)
            first_op_ns = time.perf_counter_ns() - t0
            correctness_ok = correctness_ok and (priv.key_size == 256)
            
            for _ in range(warmups):
                _ = ec.generate_private_key(curve)
                
            for _ in range(trials):
                t0 = time.perf_counter_ns()
                _ = ec.generate_private_key(curve)
                steady_state_timings.append(time.perf_counter_ns() - t0)

        elif operation == "sign":
            priv = ec.generate_private_key(curve)
            t0 = time.perf_counter_ns()
            sig = priv.sign(message, ec.ECDSA(hashes.SHA256()))
            first_op_ns = time.perf_counter_ns() - t0
            correctness_ok = correctness_ok and (69 <= len(sig) <= 73)
            
            for _ in range(warmups):
                _ = priv.sign(message, ec.ECDSA(hashes.SHA256()))
                
            for _ in range(trials):
                t0 = time.perf_counter_ns()
                _ = priv.sign(message, ec.ECDSA(hashes.SHA256()))
                steady_state_timings.append(time.perf_counter_ns() - t0)

        elif operation == "verify":
            priv = ec.generate_private_key(curve)
            pub = priv.public_key()
            sig = priv.sign(message, ec.ECDSA(hashes.SHA256()))
            
            t0 = time.perf_counter_ns()
            pub.verify(sig, message, ec.ECDSA(hashes.SHA256()))
            first_op_ns = time.perf_counter_ns() - t0
            
            for _ in range(warmups):
                pub.verify(sig, message, ec.ECDSA(hashes.SHA256()))
                
            for _ in range(trials):
                t0 = time.perf_counter_ns()
                pub.verify(sig, message, ec.ECDSA(hashes.SHA256()))
                steady_state_timings.append(time.perf_counter_ns() - t0)

    elif algorithm == "ML-DSA-65":
        import oqs
        with oqs.Signature("ML-DSA-65") as signer:
            if operation == "keygen":
                t0 = time.perf_counter_ns()
                pk = signer.generate_keypair()
                first_op_ns = time.perf_counter_ns() - t0
                correctness_ok = correctness_ok and (len(pk) == 1952)
                
                for _ in range(warmups):
                    _ = signer.generate_keypair()
                    
                for _ in range(trials):
                    t0 = time.perf_counter_ns()
                    _ = signer.generate_keypair()
                    steady_state_timings.append(time.perf_counter_ns() - t0)

            elif operation == "sign":
                pk = signer.generate_keypair()
                t0 = time.perf_counter_ns()
                sig = signer.sign(message)
                first_op_ns = time.perf_counter_ns() - t0
                correctness_ok = correctness_ok and (len(sig) == 3309)
                
                for _ in range(warmups):
                    _ = signer.sign(message)
                    
                for _ in range(trials):
                    t0 = time.perf_counter_ns()
                    _ = signer.sign(message)
                    steady_state_timings.append(time.perf_counter_ns() - t0)

            elif operation == "verify":
                pk = signer.generate_keypair()
                sig = signer.sign(message)
                
                t0 = time.perf_counter_ns()
                v_ok = signer.verify(message, sig, pk)
                first_op_ns = time.perf_counter_ns() - t0
                correctness_ok = correctness_ok and v_ok
                
                for _ in range(warmups):
                    _ = signer.verify(message, sig, pk)
                    
                for _ in range(trials):
                    t0 = time.perf_counter_ns()
                    _ = signer.verify(message, sig, pk)
                    steady_state_timings.append(time.perf_counter_ns() - t0)

    print(json.dumps({
        "algorithm": algorithm,
        "operation": operation,
        "first_op_ns": first_op_ns,
        "steady_state_timings": steady_state_timings,
        "correctness": correctness_ok,
        "peak_rss_kib": get_peak_rss_kib()
    }))
    sys.exit(0)
else:
    sys.stderr.write(f"Unknown mode: {mode}\\n")
    sys.exit(1)
"""

def spawn_child_worker(args_dict: dict) -> dict:
    """Spawns a fresh child Python process and returns parent wall time and child JSON output."""
    t_parent_0 = time.perf_counter_ns()
    proc = subprocess.run(
        [sys.executable, "-c", CHILD_WORKER_SCRIPT],
        input=json.dumps(args_dict),
        capture_output=True,
        text=True
    )
    t_parent_1 = time.perf_counter_ns()
    parent_wall_ns = t_parent_1 - t_parent_0

    if proc.returncode != 0:
        raise RuntimeError(f"Child process failed (code {proc.returncode}): {proc.stderr}")

    try:
        # Filter out any non-JSON lines (such as liboqs faulthandler notice)
        stdout_lines = proc.stdout.strip().splitlines()
        json_line = None
        for line in reversed(stdout_lines):
            if line.startswith("{") and line.endswith("}"):
                json_line = line
                break
        if not json_line:
            raise ValueError(f"No JSON object found in child stdout: {proc.stdout}")
        child_res = json.loads(json_line)
    except Exception as e:
        raise ValueError(f"Failed to parse child JSON output: {e}\nRaw stdout: {proc.stdout}")

    child_res["parent_wall_ns"] = parent_wall_ns
    return child_res

# ==============================================================================
# Experiment D2-A: Startup & Import Profiling
# ==============================================================================

def run_experiment_d2a(num_processes: int, output_dir: Path, experiment_id: str):
    print("\n" + "=" * 65)
    print("EXPERIMENT D2-A: Process Startup & Import Profiling")
    print(f"Independent fresh processes per condition: {num_processes}")
    print("=" * 65)

    targets = [
        ("baseline_empty", "Minimal empty process (no extra imports)"),
        ("baseline_stdlib", "Standard library imports only (math, os, statistics)"),
        ("import_cryptography", "cryptography package + EC/X25519 primitives"),
        ("import_oqs", "oqs (liboqs CFFI binding & shared library loading)"),
        ("import_both", "Both cryptography and oqs imported concurrently"),
        ("init_x25519", "X25519 import + keypair generation"),
        ("init_ecdsa", "ECDSA import + curve initialization + keygen"),
        ("init_mlkem", "ML-KEM-768 import + KEM object alloc + keygen"),
        ("init_mldsa", "ML-DSA-65 import + Signer object alloc + keygen"),
    ]

    raw_records = []
    
    for t_idx, (target_name, desc) in enumerate(targets, 1):
        print(f"[{t_idx}/{len(targets)}] Profiling: {target_name:<20} ({desc})")
        for p_idx in range(1, num_processes + 1):
            args = {"mode": "startup_profiling", "target": target_name}
            res = spawn_child_worker(args)
            
            p_wall_us = round(res["parent_wall_ns"] / 1000.0, 3)
            c_int_us = round(res["child_internal_ns"] / 1000.0, 3)
            std_us = round(res["import_stdlib_ns"] / 1000.0, 3)
            imp_us = round(res["import_target_ns"] / 1000.0, 3)
            obj_us = round(res["object_init_ns"] / 1000.0, 3)
            op_us = round(res["first_op_ns"] / 1000.0, 3)
            launch_gap_us = max(p_wall_us - c_int_us, 0.0)

            raw_records.append({
                "experiment_id": experiment_id,
                "target_condition": target_name,
                "process_repeat": p_idx,
                "parent_wall_us": p_wall_us,
                "child_internal_us": c_int_us,
                "launch_gap_us": launch_gap_us,
                "import_stdlib_us": std_us,
                "import_target_us": imp_us,
                "object_init_us": obj_us,
                "first_op_us": op_us,
                "peak_rss_kib": res.get("peak_rss_kib", 0),
                "correctness": res.get("correctness", True),
                "timestamp_utc": datetime.now(timezone.utc).isoformat()
            })

    raw_df = pd.DataFrame(raw_records)
    csv_path = output_dir / "d2_raw_startup.csv"
    raw_df.to_csv(csv_path, index=False)
    print(f"[OK] Wrote {len(raw_records)} startup profiling rows to {csv_path}")
    return raw_df

# ==============================================================================
# Experiment D2-B: First Operation vs. Steady-State Profiling
# ==============================================================================

def run_experiment_d2b(num_processes: int, warmups: int, trials: int, output_dir: Path, experiment_id: str):
    print("\n" + "=" * 65)
    print("EXPERIMENT D2-B: First-Operation vs. Steady-State Profiling")
    print(f"Independent fresh processes per condition: {num_processes}")
    print(f"Warm-ups per process: {warmups} | Steady-state trials per process: {trials}")
    print("=" * 65)

    operations_matrix = [
        # (Algorithm, Operation, Category)
        ("X25519", "keygen", "Key Agreement"),
        ("X25519", "shared_secret_derivation", "Key Agreement"),
        ("ML-KEM-768", "keygen", "KEM"),
        ("ML-KEM-768", "encapsulation", "KEM"),
        ("ML-KEM-768", "decapsulation", "KEM"),
        ("ECDSA-P256", "keygen", "Digital Signature"),
        ("ECDSA-P256", "sign", "Digital Signature"),
        ("ECDSA-P256", "verify", "Digital Signature"),
        ("ML-DSA-65", "keygen", "Digital Signature"),
        ("ML-DSA-65", "sign", "Digital Signature"),
        ("ML-DSA-65", "verify", "Digital Signature"),
    ]

    raw_operations_records = []
    process_summary_records = []

    for op_idx, (alg, op, cat) in enumerate(operations_matrix, 1):
        print(f"[{op_idx:02d}/{len(operations_matrix):02d}] Profiling {alg} - {op} across {num_processes} fresh processes...")
        
        for p_idx in range(1, num_processes + 1):
            process_id = f"proc_{alg}_{op}_{p_idx:02d}"
            args = {
                "mode": "operation_benchmark",
                "algorithm": alg,
                "operation": op,
                "warmups": warmups,
                "trials": trials,
                "message": TEST_MESSAGE.decode("utf-8")
            }
            
            res = spawn_child_worker(args)
            first_op_us = round(res["first_op_ns"] / 1000.0, 3)
            steady_timings_us = [round(t / 1000.0, 3) for t in res["steady_state_timings"]]
            
            # Record first operation row
            raw_operations_records.append({
                "experiment_id": experiment_id,
                "algorithm": alg,
                "operation": op,
                "category": cat,
                "process_id": process_id,
                "process_repeat": p_idx,
                "is_first_operation": True,
                "trial_index": 0,
                "latency_us": first_op_us,
                "correctness": res["correctness"],
                "peak_rss_kib": res["peak_rss_kib"],
                "timestamp_utc": datetime.now(timezone.utc).isoformat()
            })
            
            # Record steady-state rows
            for t_idx, t_us in enumerate(steady_timings_us, 1):
                raw_operations_records.append({
                    "experiment_id": experiment_id,
                    "algorithm": alg,
                    "operation": op,
                    "category": cat,
                    "process_id": process_id,
                    "process_repeat": p_idx,
                    "is_first_operation": False,
                    "trial_index": t_idx,
                    "latency_us": t_us,
                    "correctness": res["correctness"],
                    "peak_rss_kib": res["peak_rss_kib"],
                    "timestamp_utc": datetime.now(timezone.utc).isoformat()
                })
                
            # Process-level summary
            st_arr = np.array(steady_timings_us)
            p_steady_med = float(np.median(st_arr))
            ratio = round(first_op_us / p_steady_med, 2) if p_steady_med > 0 else 1.0
            diff = round(first_op_us - p_steady_med, 3)
            
            process_summary_records.append({
                "experiment_id": experiment_id,
                "algorithm": alg,
                "operation": op,
                "category": cat,
                "process_id": process_id,
                "process_repeat": p_idx,
                "first_op_us": first_op_us,
                "steady_median_us": p_steady_med,
                "steady_mean_us": round(float(np.mean(st_arr)), 3),
                "steady_std_us": round(float(np.std(st_arr, ddof=1)), 3),
                "steady_p95_us": round(float(np.percentile(st_arr, 95)), 3),
                "cold_penalty_diff_us": diff,
                "first_to_steady_ratio": ratio,
                "peak_rss_kib": res["peak_rss_kib"],
                "all_valid": res["correctness"]
            })

    # Save raw operations CSV
    raw_ops_df = pd.DataFrame(raw_operations_records)
    raw_ops_path = output_dir / "d2_raw_operations.csv"
    raw_ops_df.to_csv(raw_ops_path, index=False)
    print(f"\n[OK] Wrote {len(raw_operations_records)} raw operation observations to {raw_ops_path}")

    # Save process-level summary CSV
    proc_df = pd.DataFrame(process_summary_records)
    proc_path = output_dir / "d2_process_summary.csv"
    proc_df.to_csv(proc_path, index=False)
    print(f"[OK] Wrote {len(process_summary_records)} process-level summaries to {proc_path}")

    return raw_ops_df, proc_df

# ==============================================================================
# Consolidated Statistical Summary & Manifest
# ==============================================================================

def compute_consolidated_summary(raw_ops_df: pd.DataFrame, proc_df: pd.DataFrame, output_dir: Path, experiment_id: str):
    def calc_iqr(x):
        return x.quantile(0.75) - x.quantile(0.25)

    def calc_mad(x):
        return (x - x.median()).abs().median()

    summary_rows = []

    for (alg, op, cat), g_proc in proc_df.groupby(["algorithm", "operation", "category"], sort=False):
        # Subset all steady-state observations across all processes for this operation
        g_all_steady = raw_ops_df[(raw_ops_df["algorithm"] == alg) & 
                                  (raw_ops_df["operation"] == op) & 
                                  (~raw_ops_df["is_first_operation"])]["latency_us"]
        
        first_ops = g_proc["first_op_us"]
        proc_medians = g_proc["steady_median_us"]

        # First operation stats (between independent processes)
        first_med = float(first_ops.median())
        first_mean = float(first_ops.mean())
        first_std = float(first_ops.std(ddof=1)) if len(first_ops) > 1 else 0.0
        first_cov_pct = round((first_std / first_mean * 100), 2) if first_mean > 0 else 0.0

        # Steady-state stats (pooling all steady-state observations)
        steady_med = float(g_all_steady.median())
        steady_mean = float(g_all_steady.mean())
        steady_std = float(g_all_steady.std(ddof=1)) if len(g_all_steady) > 1 else 0.0
        steady_p90 = float(g_all_steady.quantile(0.90))
        steady_p95 = float(g_all_steady.quantile(0.95))
        steady_p99 = float(g_all_steady.quantile(0.99))
        steady_iqr = float(calc_iqr(g_all_steady))
        steady_mad = float(calc_mad(g_all_steady))

        # Between-process steady median CoV%
        proc_med_std = float(proc_medians.std(ddof=1)) if len(proc_medians) > 1 else 0.0
        proc_med_mean = float(proc_medians.mean())
        proc_steady_cov_pct = round((proc_med_std / proc_med_mean * 100), 2) if proc_med_mean > 0 else 0.0

        # Ratios and Differences
        abs_diff_us = round(first_med - steady_med, 3)
        ratio = round(first_med / steady_med, 2) if steady_med > 0 else 1.0
        pct_increase = round(((first_med - steady_med) / steady_med * 100), 2) if steady_med > 0 else 0.0

        summary_rows.append({
            "algorithm": alg,
            "operation": op,
            "category": cat,
            "processes_count": len(g_proc),
            "steady_samples_total": len(g_all_steady),
            "first_op_median_us": round(first_med, 3),
            "first_op_mean_us": round(first_mean, 3),
            "first_op_std_us": round(first_std, 3),
            "first_op_cov_pct": first_cov_pct,
            "first_op_min_us": round(float(first_ops.min()), 3),
            "first_op_max_us": round(float(first_ops.max()), 3),
            "steady_median_us": round(steady_med, 3),
            "steady_mean_us": round(steady_mean, 3),
            "steady_std_us": round(steady_std, 3),
            "steady_p90_us": round(steady_p90, 3),
            "steady_p95_us": round(steady_p95, 3),
            "steady_p99_us": round(steady_p99, 3),
            "steady_iqr_us": round(steady_iqr, 3),
            "steady_mad_us": round(steady_mad, 3),
            "proc_steady_cov_pct": proc_steady_cov_pct,
            "cold_penalty_abs_us": abs_diff_us,
            "first_to_steady_ratio": ratio,
            "cold_increase_pct": pct_increase
        })

    summary_df = pd.DataFrame(summary_rows)
    summary_path = output_dir / "d2_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    print(f"[OK] Wrote consolidated summary to {summary_path}")

    # Build manifest
    manifest = {
        "experiment_id": experiment_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "openssl_version": ssl.OPENSSL_VERSION,
        "independent_processes_per_condition": len(proc_df["process_repeat"].unique()),
        "total_processes_spawned": len(proc_df),
        "total_operations_recorded": len(raw_ops_df),
        "all_validations_passed": bool(proc_df["all_valid"].all()),
        "summary": summary_rows,
        "definitions": {
            "first_to_steady_ratio": "median(first_operation latency) / median(steady_state latency)",
            "cold_increase_pct": "100 * (median(first) - median(steady)) / median(steady)",
            "first_op_cov_pct": "100 * std(first_operation) / mean(first_operation) across independent processes",
            "proc_steady_cov_pct": "100 * std(process_medians) / mean(process_medians) across independent processes"
        }
    }
    manifest_path = output_dir / "d2_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[OK] Wrote experiment manifest to {manifest_path}")

    return summary_df

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage D2 Cold-Start Profiler")
    parser.add_argument("--processes", type=int, default=25, help="Fresh processes per condition")
    parser.add_argument("--warmups", type=int, default=5, help="Warmup operations per process")
    parser.add_argument("--trials", type=int, default=100, help="Steady-state operations per process")
    parser.add_argument("--output-dir", type=str, default="stage_d2_output")
    parser.add_argument("--experiment-id", type=str, default="")
    args = parser.parse_args()

    out_p = Path(args.output_dir)
    out_p.mkdir(parents=True, exist_ok=True)
    exp_id = args.experiment_id or f"EXP_STAGE_D2_COLDSTART_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    # Run D2-A
    run_experiment_d2a(args.processes, out_p, exp_id)
    # Run D2-B
    raw_ops, proc_summary = run_experiment_d2b(args.processes, args.warmups, args.trials, out_p, exp_id)
    # Summarize
    compute_consolidated_summary(raw_ops, proc_summary, out_p, exp_id)
