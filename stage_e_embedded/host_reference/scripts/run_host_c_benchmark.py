#!/usr/bin/env python3
"""
Master Runner for Stage E: Host-Native C Cryptographic Reference Benchmark
Empirical Migration Feasibility Analysis of Post-Quantum Cryptography for Resource-Constrained Systems

Executes:
1. Automated compilation and unit testing of native C test suite
2. Native C execution across ML-KEM-768, ML-DSA-65, X25519, and ECDSA P-256
3. Verification of raw CSV outputs (host_native_c_raw.csv)
4. Consolidated summary generation (host_native_c_summary.csv)
5. Comparison against Stage D2 Python API baseline
6. Generation of host reference visualization plots
"""

import argparse
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

STAGE_E_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = STAGE_E_DIR.parent
HOST_REF_DIR = STAGE_E_DIR / "host_reference"
RESULTS_C_DIR = STAGE_E_DIR / "results" / "host_native_c"

def is_in_docker() -> bool:
    return Path("/.dockerenv").exists() or Path("/app/stage_e_embedded").exists()

def execute_cmd(cmd_list, description, cwd=None):
    print(f"\n--- {description} ---")
    res = subprocess.run(cmd_list, capture_output=True, text=True, cwd=cwd)
    if res.stdout:
        print(res.stdout)
    if res.returncode != 0:
        if res.stderr:
            print("STDERR:\n", res.stderr)
        raise RuntimeError(f"Command failed ({description}) with code {res.returncode}")
    return res

def summarize_native_c_data(raw_csv: Path, out_dir: Path, run_id: str, trials: int, warmups: int):
    df = pd.read_csv(raw_csv)
    print(f"\n[Summary] Computing consolidated statistics across {len(df)} raw observations...")

    summary_rows = []
    for (alg, op, impl), g in df.groupby(["algorithm", "operation", "implementation"], sort=False):
        times = g["elapsed_us"]
        med = float(times.median())
        mean = float(times.mean())
        std = float(times.std(ddof=1)) if len(times) > 1 else 0.0
        p90 = float(times.quantile(0.90))
        p95 = float(times.quantile(0.95))
        p99 = float(times.quantile(0.99))
        q25 = float(times.quantile(0.25))
        q75 = float(times.quantile(0.75))
        iqr = q75 - q25
        mad = float((times - med).abs().median())
        min_v = float(times.min())
        max_v = float(times.max())
        cov_pct = (std / mean * 100.0) if mean > 0 else 0.0

        summary_rows.append({
            "run_id": run_id,
            "algorithm": alg,
            "operation": op,
            "implementation": impl,
            "samples_count": len(times),
            "median_us": round(med, 3),
            "mean_us": round(mean, 3),
            "std_us": round(std, 3),
            "cov_pct": round(cov_pct, 2),
            "p90_us": round(p90, 3),
            "p95_us": round(p95, 3),
            "p99_us": round(p99, 3),
            "iqr_us": round(iqr, 3),
            "mad_us": round(mad, 3),
            "min_us": round(min_v, 3),
            "max_us": round(max_v, 3)
        })

    sum_df = pd.DataFrame(summary_rows)
    sum_csv = out_dir / "host_native_c_summary.csv"
    sum_df.to_csv(sum_csv, index=False)
    print(f"[OK] Wrote summary to {sum_csv}")

    # Manifest
    manifest = {
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "platform": "Linux_x86_64_Docker",
        "cpu_model": "AMD Ryzen 7 7435HS",
        "compiler": "GCC 14.2.0 (-O3 -std=c11)",
        "liboqs_version": "0.16.0",
        "openssl_version": "3.5.7",
        "trials_per_operation": trials,
        "warmups_per_operation": warmups,
        "total_operations_recorded": len(df),
        "all_validations_passed": bool(df["valid"].all()),
        "summary": summary_rows
    }
    manifest_path = out_dir / "host_native_c_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[OK] Wrote manifest to {manifest_path}")

    return sum_df

def generate_host_comparison_plots(sum_c_df: pd.DataFrame, out_dir: Path):
    print("\n[Plots] Generating Host-Native C reference plots...")
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    # 1. Native C Latencies
    fig, ax = plt.subplots(figsize=(12, 6))
    labels = [f"{r['algorithm']}\n{r['operation']}" for _, r in sum_c_df.iterrows()]
    x = np.arange(len(labels))
    bars = ax.bar(x, sum_c_df["median_us"], color="#2E7D32", edgecolor="black", width=0.55)
    
    ax.set_ylabel("Execution Latency (µs, Log Scale)", fontweight="bold")
    ax.set_yscale("log")
    ax.set_title("Stage E: Host-Native C Reference Execution Latency (GCC -O3)", fontweight="bold", fontsize=13)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=25, ha="right", fontsize=9)
    ax.grid(True, linestyle="--", alpha=0.5, which="both")

    for bar, val in zip(bars, sum_c_df["median_us"]):
        ax.annotate(f"{val:.1f} µs",
                    xy=(bar.get_x() + bar.get_width() / 2, val),
                    xytext=(0, 4), textcoords="offset points",
                    ha='center', va='bottom', fontsize=8, fontweight="bold")

    plt.tight_layout()
    p1 = out_dir / "plot_native_c_latency.png"
    plt.savefig(p1, dpi=200)
    plt.close()
    print(f"[OK] Generated {p1.name}")

    # 2. Comparison with Stage D2 Python API steady-state
    # Find latest Stage D2 summary
    d2_summaries = list(ROOT_DIR.glob("experiments/EXP_STAGE_D2_COLDSTART_*/d2_summary.csv"))
    if d2_summaries:
        latest_d2 = sorted(d2_summaries)[-1]
        df_d2 = pd.read_csv(latest_d2)

        # Merge matching alg & op
        merged = []
        for _, rc in sum_c_df.iterrows():
            match = df_d2[(df_d2["algorithm"] == rc["algorithm"]) & (df_d2["operation"] == rc["operation"])]
            if not match.empty:
                r_py = match.iloc[0]
                py_med = r_py["steady_median_us"]
                c_med = rc["median_us"]
                ratio = py_med / c_med if c_med > 0 else 1.0
                merged.append({
                    "label": f"{rc['algorithm']}\n{rc['operation']}",
                    "c_us": c_med,
                    "python_us": py_med,
                    "wrapper_overhead_ratio": ratio
                })
        
        if merged:
            m_df = pd.DataFrame(merged)
            fig, ax = plt.subplots(figsize=(13, 6))
            x = np.arange(len(m_df))
            w = 0.35
            
            b1 = ax.bar(x - w/2, m_df["c_us"], w, label="Host-Native C (liboqs / OpenSSL -O3)", color="#2E7D32", edgecolor="black")
            b2 = ax.bar(x + w/2, m_df["python_us"], w, label="Host Python API (Stage D2 Steady-State)", color="#1976D2", edgecolor="black")

            ax.set_ylabel("Median Latency (µs, Log Scale)", fontweight="bold")
            ax.set_yscale("log")
            ax.set_title("Host-Native C vs. Python API Wrapper Overhead", fontweight="bold", fontsize=13)
            ax.set_xticks(x)
            ax.set_xticklabels(m_df["label"], rotation=25, ha="right", fontsize=9)
            ax.legend(loc="upper left")
            ax.grid(True, linestyle="--", alpha=0.5, which="both")

            # Add ratio annotations
            for i, r in m_df.iterrows():
                y_pos = max(r["c_us"], r["python_us"])
                ax.annotate(f"{r['wrapper_overhead_ratio']:.1f}×",
                            xy=(i, y_pos),
                            xytext=(0, 5), textcoords="offset points",
                            ha='center', va='bottom', fontsize=8, fontweight="bold", color="#D32F2F")

            plt.tight_layout()
            p2 = out_dir / "plot_native_c_vs_python.png"
            plt.savefig(p2, dpi=200)
            plt.close()
            print(f"[OK] Generated {p2.name} (Wrapper overhead comparison)")

def run_stage_e_host_c(trials: int = 1000, warmups: int = 10):
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_id = f"EXP_STAGE_E_HOST_C_{timestamp_str}"
    out_dir = RESULTS_C_DIR / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("STAGE E: Host-Native C Cryptographic Reference Benchmark")
    print("=" * 70)
    print(f"Run ID:    {run_id}")
    print(f"Directory: {out_dir}")
    print(f"Trials:    {trials} | Warmups: {warmups}")
    print("=" * 70)

    in_doc = is_in_docker()

    # Step 1: Build & Run Test Suite
    if in_doc:
        cmd_make = ["make", "clean"]
        execute_cmd(cmd_make, "Cleaning Build Artifacts", cwd=str(HOST_REF_DIR))
        cmd_test = ["make", "test"]
        execute_cmd(cmd_test, "Compiling and Running Native C Unit Tests", cwd=str(HOST_REF_DIR))
        cmd_build = ["make", "all"]
        execute_cmd(cmd_build, "Compiling Native C Benchmark Binary", cwd=str(HOST_REF_DIR))
        
        # Step 2: Run Benchmark
        bench_bin = HOST_REF_DIR / "bin" / "benchmark_native"
        cmd_bench = [
            str(bench_bin),
            "--trials", str(trials),
            "--warmups", str(warmups),
            "--out-dir", str(out_dir),
            "--run-id", run_id
        ]
        execute_cmd(cmd_bench, "Executing Native C Benchmark")
    else:
        # Run via Docker
        docker_host_ref = "/app/stage_e_embedded/host_reference"
        docker_out_dir = f"/app/stage_e_embedded/results/host_native_c/{run_id}"

        cmd_docker_build = [
            "docker", "run", "--rm",
            "-v", f"{ROOT_DIR.as_posix()}:/app",
            "-w", docker_host_ref,
            "pqc-bench:1.0",
            "bash", "-c", "make clean && make test && make all"
        ]
        execute_cmd(cmd_docker_build, "Building & Testing in Docker pqc-bench:1.0")

        cmd_docker_run = [
            "docker", "run", "--rm",
            "-v", f"{ROOT_DIR.as_posix()}:/app",
            "pqc-bench:1.0",
            f"{docker_host_ref}/bin/benchmark_native",
            "--trials", str(trials),
            "--warmups", str(warmups),
            "--out-dir", docker_out_dir,
            "--run-id", run_id
        ]
        execute_cmd(cmd_docker_run, "Executing Host-Native C Benchmark in Docker")

    raw_csv = out_dir / "host_native_c_raw.csv"
    if not raw_csv.exists() or raw_csv.stat().st_size == 0:
        raise RuntimeError(f"Raw CSV not found or empty: {raw_csv}")

    # Step 3: Summarize & Plot
    sum_df = summarize_native_c_data(raw_csv, out_dir, run_id, trials, warmups)
    generate_host_comparison_plots(sum_df, out_dir)

    print("\n" + "=" * 70)
    print("STAGE E HOST-NATIVE C BENCHMARK COMPLETE!")
    print(f"Results stored in: {out_dir}")
    print("=" * 70)
    return run_id, out_dir

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage E Host-Native C Benchmark Runner")
    parser.add_argument("--trials", type=int, default=1000, help="Number of steady-state trials per operation")
    parser.add_argument("--warmups", type=int, default=10, help="Number of warmup iterations per operation")
    args = parser.parse_args()

    run_stage_e_host_c(trials=args.trials, warmups=args.warmups)
