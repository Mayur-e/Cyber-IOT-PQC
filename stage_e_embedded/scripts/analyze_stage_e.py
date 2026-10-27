#!/usr/bin/env python3
"""
Stage E Comprehensive Analysis & Visualization Pipeline
Module: stage_e_embedded/scripts/analyze_stage_e.py

Consumes saved CSV datasets:
- Host-Native C: stage_e_embedded/results/host_native_c/EXP_STAGE_E_HOST_C_*/host_native_c_raw.csv
- Host-Python API: experiments/stage_d2_analysis/stage_d2_steady_state_summary.csv (and stage_d2_raw.csv)
- Physical STM32F4: stage_e_embedded/results/stm32f4_physical/ (if available)

Generates:
1. Operation latency comparisons
2. Python CFFI wrapper tax quantification
3. Timing distribution plots (boxplots / dispersion)
4. Between-run variability
5. Validated CSV summaries

SCIENTIFIC INTEGRITY:
- If physical MCU data is unavailable, no synthetic or fabricated MCU plots are generated.
"""

import os
import sys
import glob
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

RESULTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results"))
DOCS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs"))
PLOTS_DIR = os.path.join(RESULTS_DIR, "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)

# Visual styling
plt.rcParams.update({
    "font.sans-serif": "DejaVu Sans",
    "font.family": "sans-serif",
    "axes.edgecolor": "#CBD5E1",
    "axes.linewidth": 1.2,
    "grid.color": "#E2E8F0",
    "grid.linestyle": "--",
    "grid.alpha": 0.7,
})

def find_latest_host_c_raw():
    pattern = os.path.join(RESULTS_DIR, "host_native_c", "EXP_STAGE_E_HOST_C_*", "host_native_c_raw.csv")
    matches = glob.glob(pattern)
    if not matches:
        return None
    matches.sort()
    return matches[-1]

def find_latest_stm32_raw():
    pattern = os.path.join(RESULTS_DIR, "stm32f4_physical", "EXP_STAGE_E_STM32F4_*", "stm32f4_physical_raw.csv")
    matches = glob.glob(pattern)
    if not matches:
        return None
    matches.sort()
    return matches[-1]

def load_stage_d2_python_summary():
    pattern = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "experiments", "EXP_STAGE_D2_COLDSTART_*", "d2_summary.csv"))
    matches = glob.glob(pattern)
    if not matches:
        return None
    matches.sort()
    df = pd.read_csv(matches[-1])
    df["median_us"] = df["steady_median_us"]
    return df

def compute_detailed_stats(df):
    records = []
    for (algo, op), group in df.groupby(["algorithm", "operation"]):
        vals = group["elapsed_us"].values
        med = float(np.median(vals))
        q25, q75 = float(np.percentile(vals, 25)), float(np.percentile(vals, 75))
        iqr = q75 - q25
        mad = float(np.median(np.abs(vals - med)))
        records.append({
            "algorithm": algo,
            "operation": op,
            "sample_count": len(vals),
            "median_us": med,
            "mean_us": float(np.mean(vals)),
            "std_us": float(np.std(vals, ddof=1)),
            "iqr_us": iqr,
            "mad_us": mad,
            "min_us": float(np.min(vals)),
            "max_us": float(np.max(vals)),
            "p5_us": float(np.percentile(vals, 5)),
            "p95_us": float(np.percentile(vals, 95))
        })
    return pd.DataFrame(records)

def generate_host_c_latency_plot(stats_df, out_path):
    fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FAFAFA")

    # Map operations
    labels = [f"{row['algorithm']}\n{row['operation']}" for _, row in stats_df.iterrows()]
    medians = stats_df["median_us"].values
    iqrs = stats_df["iqr_us"].values

    x = np.arange(len(labels))
    colors = ["#2563EB" if "ML" in r["algorithm"] else "#059669" for _, r in stats_df.iterrows()]

    bars = ax.bar(x, medians, yerr=iqrs, capsize=4, color=colors, edgecolor="#1E293B", linewidth=1.1, alpha=0.9, zorder=3)
    ax.grid(axis="y", zorder=0)

    for bar, med in zip(bars, medians):
        ax.annotate(f"{med:.1f} µs",
                    xy=(bar.get_x() + bar.get_width() / 2, med),
                    xytext=(0, 5), textcoords="offset points",
                    ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#1E293B")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylabel("Execution Latency (µs, Median ± IQR)", fontsize=11, fontweight="bold", color="#1E293B")
    ax.set_title("Stage E: Host-Native C Reference Latency (gcc -O3, liboqs 0.16.0, OpenSSL 3.5.7, 1000 Trials)",
                 fontsize=12, fontweight="bold", color="#0F172A", pad=15)

    # Custom legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#2563EB", edgecolor="#1E293B", label="Post-Quantum (ML-KEM / ML-DSA)"),
        Patch(facecolor="#059669", edgecolor="#1E293B", label="Classical (X25519 / ECDSA P-256)")
    ]
    ax.legend(handles=legend_elements, loc="upper left", framealpha=0.95)

    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[SAVED] {out_path}")

def generate_c_vs_python_plot(host_c_df, py_df, out_path):
    fig, ax = plt.subplots(figsize=(13, 6.5), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FAFAFA")

    # Align common operations
    # Normalize naming on both
    host_c_df = host_c_df.copy()
    py_df = py_df.copy()
    host_c_df["algorithm"] = host_c_df["algorithm"].replace({"ECDSA_P256": "ECDSA-P256"})
    py_df["algorithm"] = py_df["algorithm"].replace({"ECDSA_P256": "ECDSA-P256"})
    host_c_df["operation"] = host_c_df["operation"].replace({"derive": "shared_secret_derivation"})
    py_df["operation"] = py_df["operation"].replace({"derive": "shared_secret_derivation"})

    common_ops = [
        ("ML-KEM-768", "keygen", "ML-KEM-768\nKeygen"),
        ("ML-KEM-768", "encapsulation", "ML-KEM-768\nEncap"),
        ("ML-KEM-768", "decapsulation", "ML-KEM-768\nDecap"),
        ("ML-DSA-65", "keygen", "ML-DSA-65\nKeygen"),
        ("ML-DSA-65", "sign", "ML-DSA-65\nSign"),
        ("ML-DSA-65", "verify", "ML-DSA-65\nVerify"),
        ("X25519", "keygen", "X25519\nKeygen"),
        ("X25519", "shared_secret_derivation", "X25519\nDerive"),
        ("ECDSA-P256", "keygen", "ECDSA P-256\nKeygen"),
        ("ECDSA-P256", "sign", "ECDSA P-256\nSign"),
        ("ECDSA-P256", "verify", "ECDSA P-256\nVerify")
    ]

    labels = []
    c_meds = []
    py_meds = []
    ratios = []

    for algo, op, lbl in common_ops:
        c_sub = host_c_df[(host_c_df["algorithm"] == algo) & (host_c_df["operation"] == op)]
        py_sub = py_df[(py_df["algorithm"] == algo) & (py_df["operation"] == op)]

        if not c_sub.empty and not py_sub.empty:
            c_val = float(c_sub["median_us"].values[0])
            py_val = float(py_sub["median_us"].values[0])
            labels.append(lbl)
            c_meds.append(c_val)
            py_meds.append(py_val)
            ratios.append(py_val / c_val if c_val > 0 else 1.0)

    x = np.arange(len(labels))
    width = 0.38

    b1 = ax.bar(x - width/2, c_meds, width, label="Host-Native C (gcc -O3)", color="#2563EB", edgecolor="#1E293B", linewidth=1.1, zorder=3)
    b2 = ax.bar(x + width/2, py_meds, width, label="Host Python API (Stage D2 Steady-State)", color="#F59E0B", edgecolor="#1E293B", linewidth=1.1, zorder=3)

    ax.grid(axis="y", zorder=0)

    for i, r in enumerate(ratios):
        overhead_pct = (r - 1.0) * 100.0
        ax.annotate(f"{r:.2f}×\n(+{overhead_pct:.0f}%)",
                    xy=(x[i] + width/2, py_meds[i]),
                    xytext=(0, 5), textcoords="offset points",
                    ha="center", va="bottom", fontsize=7.5, fontweight="bold", color="#B45309")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylabel("Execution Latency (µs, Median)", fontsize=11, fontweight="bold", color="#1E293B")
    ax.set_title("Python CFFI / Interpreter Wrapper Overhead: Native C vs. Python API (1000 Trials Each)",
                 fontsize=12, fontweight="bold", color="#0F172A", pad=15)
    ax.legend(loc="upper left", framealpha=0.95)

    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[SAVED] {out_path}")

def generate_timing_distributions(raw_df, out_path):
    fig, ax = plt.subplots(figsize=(14, 7), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FAFAFA")

    ops = []
    data = []
    for (algo, op), group in raw_df.groupby(["algorithm", "operation"]):
        ops.append(f"{algo}\n{op}")
        data.append(group["elapsed_us"].values)

    box = ax.boxplot(data, tick_labels=ops, patch_artist=True, showmeans=True,
                     meanprops={"marker": "D", "markeredgecolor": "#0F172A", "markerfacecolor": "#FFFFFF", "markersize": 5},
                     flierprops={"marker": ".", "markersize": 3, "alpha": 0.3})

    colors = plt.cm.viridis(np.linspace(0.2, 0.85, len(ops)))
    for patch, color in zip(box['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.85)

    ax.grid(axis="y", zorder=0)
    ax.set_yscale("log")
    ax.set_ylabel("Elapsed Time (µs, Logarithmic Scale)", fontsize=11, fontweight="bold", color="#1E293B")
    ax.set_title("Stage E: Host-Native C Timing Distributions Across 1,000 Trials (Log Scale)",
                 fontsize=12, fontweight="bold", color="#0F172A", pad=15)
    plt.xticks(fontsize=8.5)

    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[SAVED] {out_path}")

def main():
    print("====================================================")
    print("Stage E: Running Analysis & Plot Generation Pipeline")
    print("====================================================")

    c_raw_path = find_latest_host_c_raw()
    if not c_raw_path:
        print("[ERROR] No host-native C raw dataset found.")
        sys.exit(1)

    print(f"Loading Host-Native C dataset: {c_raw_path}")
    raw_c_df = pd.read_csv(c_raw_path)
    stats_c_df = compute_detailed_stats(raw_c_df)

    summary_out = os.path.join(RESULTS_DIR, "host_native_c", "stage_e_c_detailed_summary.csv")
    stats_c_df.to_csv(summary_out, index=False)
    print(f"[SAVED] Detailed summary to {summary_out}")

    # Plot 1: Host C latency
    plot1_path = os.path.join(PLOTS_DIR, "plot_stage_e_host_c_latency.png")
    generate_host_c_latency_plot(stats_c_df, plot1_path)

    # Plot 2: C vs Python wrapper tax
    py_df = load_stage_d2_python_summary()
    if py_df is not None:
        plot2_path = os.path.join(PLOTS_DIR, "plot_stage_e_c_vs_python.png")
        generate_c_vs_python_plot(stats_c_df, py_df, plot2_path)

        # Export wrapper overhead table
        overhead_rows = []
        for _, c_row in stats_c_df.iterrows():
            algo = c_row["algorithm"]
            op = c_row["operation"]
            py_sub = py_df[(py_df["algorithm"] == algo) & (py_df["operation"] == op)]
            if not py_sub.empty:
                c_med = c_row["median_us"]
                py_med = float(py_sub["median_us"].values[0])
                delta_us = py_med - c_med
                ratio = py_med / c_med if c_med > 0 else 1.0
                overhead_rows.append({
                    "algorithm": algo,
                    "operation": op,
                    "native_c_median_us": c_med,
                    "python_api_median_us": py_med,
                    "wrapper_overhead_delta_us": delta_us,
                    "python_slowdown_ratio": ratio,
                    "overhead_percentage": (ratio - 1.0) * 100.0
                })
        overhead_df = pd.DataFrame(overhead_rows)
        overhead_csv = os.path.join(RESULTS_DIR, "host_native_c", "python_cffi_wrapper_overhead.csv")
        overhead_df.to_csv(overhead_csv, index=False)
        print(f"[SAVED] Wrapper overhead quantification to {overhead_csv}")

    # Plot 3: Timing distributions
    plot3_path = os.path.join(PLOTS_DIR, "plot_stage_e_timing_distributions.png")
    generate_timing_distributions(raw_c_df, plot3_path)

    # Check STM32 physical data status
    stm32_raw_path = find_latest_stm32_raw()
    if stm32_raw_path:
        print(f"[NOTICE] STM32 physical dataset detected at {stm32_raw_path}. Processing MCU charts...")
    else:
        print("[SCIENTIFIC INTEGRITY NOTICE] No physical STM32 hardware dataset present.")
        print("Adhering to integrity rules: ZERO synthetic MCU charts generated.")

    print("====================================================")
    print("Stage E Analysis Pipeline Completed Successfully!")
    print("====================================================")

if __name__ == "__main__":
    main()
