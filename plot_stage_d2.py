#!/usr/bin/env python3
"""
Stage D2 Scientific Plotting Pipeline
Empirical Migration Feasibility Analysis of Post-Quantum Cryptography for Resource-Constrained Systems

Generates 6 publication-quality scientific figures:
1. plot1_first_vs_steady_latency.png (First-Operation vs Steady-State Median Latency)
2. plot2_first_to_steady_ratio.png (Cold-Start Slowdown Factor / Latency Ratio)
3. plot3_startup_and_import_breakdown.png (Subprocess Startup, Import, and Construction Overhead)
4. plot4_steady_state_distribution_boxplots.png (Steady-State Operation Latency Distributions)
5. plot5_between_process_variability.png (Process-to-Process CoV % Comparison)
6. plot6_first_vs_steady_scatter.png (First-Call vs Steady-State Process Correlation)
"""

import argparse
import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def generate_plots(exp_dir: Path):
    exp_dir = exp_dir.resolve()
    print(f"=== Stage D2 Plot Generation ===")
    print(f"Reading from: {exp_dir}")

    summary_f = exp_dir / "d2_summary.csv"
    raw_ops_f = exp_dir / "d2_raw_operations.csv"
    proc_summary_f = exp_dir / "d2_process_summary.csv"
    raw_startup_f = exp_dir / "d2_raw_startup.csv"

    # Style configuration
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    plt.rcParams.update({
        "font.size": 10,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "figure.titlesize": 13,
    })

    # ==========================================================
    # Plot 1: First-Operation vs. Steady-State Median Latency
    # ==========================================================
    if summary_f.exists():
        df_sum = pd.read_csv(summary_f)
        fig, ax = plt.subplots(figsize=(14, 6.5))
        
        # Labels: Alg + Op
        labels = [f"{r['algorithm']}\n{r['operation']}" for _, r in df_sum.iterrows()]
        x = np.arange(len(labels))
        width = 0.35
        
        rects1 = ax.bar(x - width/2, df_sum["first_op_median_us"], width, label="First-Operation (Cold)", color="#D0021B", edgecolor="black")
        rects2 = ax.bar(x + width/2, df_sum["steady_median_us"], width, label="Steady-State Median", color="#4A90E2", edgecolor="black")
        
        ax.set_ylabel("Operation Latency (µs, Log Scale)", fontweight="bold")
        ax.set_yscale("log")
        ax.set_title("First-Operation (Cold) vs. Steady-State Median Latency Across Cryptographic Operations", fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=25, ha="right")
        ax.grid(True, linestyle="--", alpha=0.5, which="both")
        ax.legend()
        
        for bar in rects1:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2.0, h * 1.15, f"{h:.0f}", ha="center", va="bottom", fontsize=8, rotation=90)
        for bar in rects2:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2.0, h * 1.15, f"{h:.1f}", ha="center", va="bottom", fontsize=8, rotation=90)
            
        ax.set_ylim(1, max(df_sum["first_op_median_us"]) * 5)
        plt.tight_layout()
        p1_path = exp_dir / "plot1_first_vs_steady_latency.png"
        plt.savefig(p1_path, dpi=200)
        plt.close()
        print(f"[OK] Generated {p1_path.name}")

    # ==========================================================
    # Plot 2: First-to-Steady Latency Ratio (Cold Slowdown Factor)
    # ==========================================================
    if summary_f.exists():
        fig, ax = plt.subplots(figsize=(12, 5.5))
        colors = ["#F5A623" if r["first_to_steady_ratio"] > 100 else "#4A90E2" for _, r in df_sum.iterrows()]
        
        bars = ax.bar(labels, df_sum["first_to_steady_ratio"], color=colors, width=0.5, edgecolor="black")
        ax.set_ylabel("First-to-Steady Latency Ratio", fontweight="bold")
        ax.set_title("Cold-Start Penalty: First-Operation Latency / Steady-State Median", fontweight="bold")
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=25, ha="right")
        ax.grid(True, linestyle="--", alpha=0.5, axis="y")
        
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2.0, h + max(df_sum["first_to_steady_ratio"])*0.02, f"{h:.1f}×", ha="center", va="bottom", fontweight="bold", fontsize=9)
            
        ax.set_ylim(0, max(df_sum["first_to_steady_ratio"]) * 1.15)
        plt.tight_layout()
        p2_path = exp_dir / "plot2_first_to_steady_ratio.png"
        plt.savefig(p2_path, dpi=200)
        plt.close()
        print(f"[OK] Generated {p2_path.name}")

    # ==========================================================
    # Plot 3: Fresh-Process Startup and Import-Duration Breakdown
    # ==========================================================
    if raw_startup_f.exists():
        df_start = pd.read_csv(raw_startup_f)
        grp = df_start.groupby("target_condition", as_index=False).agg(
            child_internal_ms=("child_internal_us", lambda x: x.median() / 1000.0),
            import_stdlib_ms=("import_stdlib_us", lambda x: x.median() / 1000.0),
            import_target_ms=("import_target_us", lambda x: x.median() / 1000.0),
            object_init_ms=("object_init_us", lambda x: x.median() / 1000.0),
            first_op_ms=("first_op_us", lambda x: x.median() / 1000.0),
            launch_gap_ms=("launch_gap_us", lambda x: x.median() / 1000.0),
            parent_wall_ms=("parent_wall_us", lambda x: x.median() / 1000.0)
        )
        
        # Order by total duration
        grp = grp.sort_values("parent_wall_ms")
        
        fig, ax = plt.subplots(figsize=(13, 6))
        cond_labels = grp["target_condition"].tolist()
        y_pos = np.arange(len(cond_labels))
        
        # Horizontal stacked bar
        b_launch = ax.barh(y_pos, grp["launch_gap_ms"], label="Subprocess Launch Gap (OS/Pipe)", color="#9E9E9E")
        b_std = ax.barh(y_pos, grp["import_stdlib_ms"], left=grp["launch_gap_ms"], label="Stdlib Import", color="#FFC107")
        left_val = grp["launch_gap_ms"] + grp["import_stdlib_ms"]
        b_imp = ax.barh(y_pos, grp["import_target_ms"], left=left_val, label="Target Package Import", color="#03A9F4")
        left_val = left_val + grp["import_target_ms"]
        b_obj = ax.barh(y_pos, grp["object_init_ms"], left=left_val, label="Object Construction", color="#8BC34A")
        left_val = left_val + grp["object_init_ms"]
        b_op = ax.barh(y_pos, grp["first_op_ms"], left=left_val, label="First Operation", color="#E91E63")
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(cond_labels)
        ax.set_xlabel("Elapsed Time (Milliseconds)", fontweight="bold")
        ax.set_title("Subprocess Initialization & Import Cost Breakdown (Median per Condition)", fontweight="bold")
        ax.grid(True, linestyle="--", alpha=0.5, axis="x")
        ax.legend(loc="lower right")
        
        for idx, total_ms in enumerate(grp["parent_wall_ms"]):
            ax.text(total_ms + 2, idx, f"{total_ms:.1f} ms", va="center", fontsize=9, fontweight="bold")
            
        ax.set_xlim(0, max(grp["parent_wall_ms"]) * 1.12)
        plt.tight_layout()
        p3_path = exp_dir / "plot3_startup_and_import_breakdown.png"
        plt.savefig(p3_path, dpi=200)
        plt.close()
        print(f"[OK] Generated {p3_path.name}")

    # ==========================================================
    # Plot 4: Steady-State Distribution Boxplots
    # ==========================================================
    if raw_ops_f.exists():
        df_raw = pd.read_csv(raw_ops_f)
        steady_df = df_raw[~df_raw["is_first_operation"]]
        
        fig, ax = plt.subplots(figsize=(14, 6.5))
        ops_groups = []
        box_labels = []
        for (alg, op), g in steady_df.groupby(["algorithm", "operation"], sort=False):
            ops_groups.append(g["latency_us"].values)
            box_labels.append(f"{alg}\n{op}")
            
        try:
            ax.boxplot(ops_groups, tick_labels=box_labels, showmeans=True, patch_artist=True,
                       boxprops=dict(facecolor="#E1F5FE", color="#0288D1"),
                       medianprops=dict(color="#D0021B", linewidth=1.5),
                       meanprops=dict(marker="o", markeredgecolor="black", markerfacecolor="#4CAF50"))
        except TypeError:
            ax.boxplot(ops_groups, labels=box_labels, showmeans=True, patch_artist=True,
                       boxprops=dict(facecolor="#E1F5FE", color="#0288D1"),
                       medianprops=dict(color="#D0021B", linewidth=1.5),
                       meanprops=dict(marker="o", markeredgecolor="black", markerfacecolor="#4CAF50"))
                   
        ax.set_yscale("log")
        ax.set_ylabel("Steady-State Latency (µs, Log Scale)", fontweight="bold")
        ax.set_title("Steady-State Latency Distributions Across Cryptographic Operations (Boxplots)", fontweight="bold")
        ax.set_xticklabels(box_labels, rotation=25, ha="right")
        ax.grid(True, linestyle="--", alpha=0.5, which="both")
        
        plt.tight_layout()
        p4_path = exp_dir / "plot4_steady_state_distribution_boxplots.png"
        plt.savefig(p4_path, dpi=200)
        plt.close()
        print(f"[OK] Generated {p4_path.name}")

    # ==========================================================
    # Plot 5: Between-Process Variability (CoV % Comparison)
    # ==========================================================
    if summary_f.exists():
        fig, ax = plt.subplots(figsize=(13, 5.5))
        x = np.arange(len(labels))
        width = 0.35
        
        ax.bar(x - width/2, df_sum["first_op_cov_pct"], width, label="First-Operation CoV (%) across Processes", color="#E91E63", edgecolor="black")
        ax.bar(x + width/2, df_sum["proc_steady_cov_pct"], width, label="Steady-State Process Median CoV (%)", color="#009688", edgecolor="black")
        
        ax.set_ylabel("Coefficient of Variation (CoV %)", fontweight="bold")
        ax.set_title("Between-Process Variability: First-Operation vs. Steady-State Median", fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=25, ha="right")
        ax.grid(True, linestyle="--", alpha=0.5, axis="y")
        ax.legend()
        
        plt.tight_layout()
        p5_path = exp_dir / "plot5_between_process_variability.png"
        plt.savefig(p5_path, dpi=200)
        plt.close()
        print(f"[OK] Generated {p5_path.name}")

    # ==========================================================
    # Plot 6: Per-Process First-Operation vs Steady-State Scatter
    # ==========================================================
    if proc_summary_f.exists():
        df_proc = pd.read_csv(proc_summary_f)
        fig, ax = plt.subplots(figsize=(10, 6.5))
        
        # Color by algorithm
        color_map = {
            "X25519": "#4A90E2",
            "ECDSA-P256": "#50E3C2",
            "ML-KEM-768": "#E94E77",
            "ML-DSA-65": "#9013FE"
        }
        
        for alg, g in df_proc.groupby("algorithm"):
            ax.scatter(g["steady_median_us"], g["first_op_us"], 
                       label=alg, color=color_map.get(alg, "gray"), s=45, alpha=0.75, edgecolors="black", linewidth=0.5)
                       
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("Process Steady-State Median Latency (µs, Log Scale)", fontweight="bold")
        ax.set_ylabel("Process First-Operation Latency (µs, Log Scale)", fontweight="bold")
        ax.set_title("Process Correlation: First-Operation vs Steady-State Latency", fontweight="bold")
        
        # Dynamic limits to prevent clipping
        min_x = max(10, df_proc["steady_median_us"].min() * 0.7)
        max_x = df_proc["steady_median_us"].max() * 1.4
        min_y = max(10, df_proc["first_op_us"].min() * 0.7)
        max_y = df_proc["first_op_us"].max() * 1.4
        ax.set_xlim(min_x, max_x)
        ax.set_ylim(min_y, max_y)
        
        # Diagonal equality line y = x
        parity_min = min(min_x, min_y)
        parity_max = max(max_x, max_y)
        ax.plot([parity_min, parity_max], [parity_min, parity_max], linestyle="--", color="black", alpha=0.6, label="Line of Parity (y = x)")
        ax.grid(True, linestyle="--", alpha=0.5, which="both")
        ax.legend()
        
        plt.tight_layout()
        p6_path = exp_dir / "plot6_first_vs_steady_scatter.png"
        plt.savefig(p6_path, dpi=200)
        plt.close()
        print(f"[OK] Generated {p6_path.name}")

    print("[SUCCESS] All 6 Stage D2 scientific plots generated.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage D2 Plot Generator")
    parser.add_argument("pos_exp_dir", nargs="?", default=None, help="Experiment directory containing CSV outputs")
    parser.add_argument("--exp-dir", dest="named_exp_dir", type=str, default=None, help="Experiment directory containing CSV outputs")
    args = parser.parse_args()
    target_dir = args.named_exp_dir or args.pos_exp_dir
    if not target_dir:
        parser.error("Must provide an experiment directory via positional argument or --exp-dir")
    generate_plots(Path(target_dir))
