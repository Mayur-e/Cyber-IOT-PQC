import os
import glob
import json
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

root_dir = Path("d:/Cyber-security/pqc_first_experiment").resolve()
experiments_dir = root_dir / "experiments"

# Find all Stage C experiment directories
stage_c_dirs = sorted([d for d in experiments_dir.glob("EXP_STAGE_C_*") if d.is_dir() and "VALIDATION" not in d.name])
print(f"Found {len(stage_c_dirs)} Stage C run directories:")
for d in stage_c_dirs:
    print(f"  {d.name}")

if len(stage_c_dirs) < 15:
    print(f"Waiting: Expected 15 runs, found {len(stage_c_dirs)}...")
    sys.exit(0)

output_dir = experiments_dir / "stage_c_analysis"
output_dir.mkdir(parents=True, exist_ok=True)

frames = []
manifests = {}
resources = {}

for d in stage_c_dirs:
    raw_csv = d / "benchmark_raw.csv"
    manifest_f = d / "run_manifest.json"
    res_f = d / "resource_usage.json"
    
    df = pd.read_csv(raw_csv)
    manifest = json.loads(manifest_f.read_text(encoding="utf-8"))
    res = json.loads(res_f.read_text(encoding="utf-8"))
    
    # Parse tag: EXP_STAGE_C_<tag>_<timestamp>
    # tag format: CPU05_MEM512_R1, CPU10_MEM512_R2, CPU10_MEM256_R1, etc.
    parts = d.name.split("_")
    cpu_str = parts[3] # CPU05, CPU10, CPU20
    mem_str = parts[4] # MEM512, MEM256, MEM1024
    rep_str = parts[5] # R1, R2, R3
    
    cpu_val = float(cpu_str.replace("CPU", "").replace("05", "0.5").replace("10", "1.0").replace("20", "2.0"))
    mem_val = int(mem_str.replace("MEM", ""))
    repeat_val = int(rep_str.replace("R", ""))
    
    df["exp_id"] = d.name
    df["cpu_quota"] = cpu_val
    df["mem_limit_mib"] = mem_val
    df["repeat"] = repeat_val
    df["config_label"] = f"{cpu_val} CPU / {mem_val} MiB"
    
    frames.append(df)
    manifests[d.name] = manifest
    resources[d.name] = res

all_c_df = pd.concat(frames, ignore_index=True)
print(f"\nLoaded {len(all_c_df)} total observations across {len(stage_c_dirs)} Stage C runs.")

# 1. Summary Statistics per Run
def calc_iqr(x):
    return x.quantile(0.75) - x.quantile(0.25)

def calc_mad(x):
    return (x - x.median()).abs().median()

per_run_summary = all_c_df.groupby(
    ["cpu_quota", "mem_limit_mib", "repeat", "config_label", "exp_id", "algorithm", "category", "operation"],
    as_index=False
).agg(
    samples=("time_us", "count"),
    median_us=("time_us", "median"),
    mean_us=("time_us", "mean"),
    std_us=("time_us", "std"),
    min_us=("time_us", "min"),
    max_us=("time_us", "max"),
    p90_us=("time_us", lambda x: x.quantile(0.90)),
    p95_us=("time_us", lambda x: x.quantile(0.95)),
    p99_us=("time_us", lambda x: x.quantile(0.99)),
    iqr_us=("time_us", calc_iqr),
    mad_us=("time_us", calc_mad)
)
per_run_summary.to_csv(output_dir / "stage_c_per_run_summary.csv", index=False)

# 2. Configuration-Level Summary (aggregating the 3 independent runs)
config_summary = per_run_summary.groupby(
    ["cpu_quota", "mem_limit_mib", "config_label", "algorithm", "operation"],
    as_index=False
).agg(
    runs=("median_us", "count"),
    median_of_medians=("median_us", "median"),
    mean_of_medians=("median_us", "mean"),
    std_of_medians=("median_us", "std"),
    min_median=("median_us", "min"),
    max_median=("median_us", "max"),
    mean_p95=("p95_us", "mean"),
    mean_p99=("p99_us", "mean"),
    mean_iqr=("iqr_us", "mean"),
    mean_mad=("mad_us", "mean"),
)
config_summary["cov_pct"] = (config_summary["std_of_medians"] / config_summary["mean_of_medians"] * 100).round(2)
config_summary.to_csv(output_dir / "stage_c_config_summary.csv", index=False)

# 3. Telemetry Consolidation
telemetry_rows = []
for exp_name, manifest in manifests.items():
    res = manifest["resource_monitoring"]
    parts = exp_name.split("_")
    cpu_val = float(parts[3].replace("CPU", "").replace("05", "0.5").replace("10", "1.0").replace("20", "2.0"))
    mem_val = int(parts[4].replace("MEM", ""))
    rep_val = int(parts[5].replace("R", ""))
    
    throttled = res.get("container_cpu_throttling", {})
    throttled_ms = round(throttled.get("throttled_usec", 0) / 1000.0, 2)
    nr_throttled = throttled.get("nr_throttled", 0)
    nr_periods = throttled.get("nr_periods", 0)
    
    events = res.get("final_snapshot", {}).get("cgroup_memory_events", {})
    
    telemetry_rows.append({
        "exp_id": exp_name,
        "cpu_quota": cpu_val,
        "mem_limit_mib": mem_val,
        "repeat": rep_val,
        "wall_duration_s": manifest.get("wall_duration_seconds"),
        "peak_rss_mib": round(res.get("peak_process_rss_kib", 0) / 1024, 2),
        "container_mem_mib": round(res.get("container_memory_current_bytes", 0) / (1024*1024), 2),
        "configured_mem_mib": round(res.get("container_memory_max_bytes", 0) / (1024*1024), 2),
        "throttled_ms": throttled_ms,
        "nr_throttled": nr_throttled,
        "nr_periods": nr_periods,
        "oom_count": events.get("oom", 0),
        "oom_kill_count": events.get("oom_kill", 0),
        "correctness_all_passed": manifest["correctness"]["all_passed"]
    })

telemetry_df = pd.DataFrame(telemetry_rows)
telemetry_df.to_csv(output_dir / "stage_c_telemetry_summary.csv", index=False)

# Telemetry grouped by configuration
telem_grouped = telemetry_df.groupby(["cpu_quota", "mem_limit_mib"]).agg(
    mean_wall_s=("wall_duration_s", "mean"),
    mean_rss_mib=("peak_rss_mib", "mean"),
    std_rss_mib=("peak_rss_mib", "std"),
    mean_container_mem_mib=("container_mem_mib", "mean"),
    mean_throttled_ms=("throttled_ms", "mean"),
    mean_nr_throttled=("nr_throttled", "mean"),
    total_oom=("oom_count", "sum"),
    total_oom_kill=("oom_kill_count", "sum"),
    all_passed=("correctness_all_passed", "all")
).round(3)
telem_grouped.to_csv(output_dir / "stage_c_telemetry_by_config.csv")

print("\n=== Stage C Telemetry Grouped by Configuration ===")
print(telem_grouped.to_string())

# 4. Sensitivity Computations: Relative Delta to Reference (1.0 CPU / 512 MiB)
ref = config_summary[(config_summary["cpu_quota"] == 1.0) & (config_summary["mem_limit_mib"] == 512)][["algorithm", "operation", "median_of_medians", "mean_p95"]]
ref = ref.rename(columns={"median_of_medians": "ref_median_us", "mean_p95": "ref_p95_us"})

sensitivity_df = pd.merge(config_summary, ref, on=["algorithm", "operation"])
sensitivity_df["median_change_pct"] = ((sensitivity_df["median_of_medians"] - sensitivity_df["ref_median_us"]) / sensitivity_df["ref_median_us"] * 100).round(2)
sensitivity_df["p95_change_pct"] = ((sensitivity_df["mean_p95"] - sensitivity_df["ref_p95_us"]) / sensitivity_df["ref_p95_us"] * 100).round(2)
sensitivity_df.to_csv(output_dir / "stage_c_sensitivity_relative_to_ref.csv", index=False)

print("\n=== CPU Quota Effect on Medians (relative to 1.0 CPU / 512 MiB) ===")
cpu_comp = sensitivity_df[sensitivity_df["mem_limit_mib"] == 512][["cpu_quota", "algorithm", "operation", "median_of_medians", "median_change_pct", "cov_pct"]]
print(cpu_comp.pivot(index=["algorithm", "operation"], columns="cpu_quota", values=["median_of_medians", "median_change_pct"]).round(2).to_string())

print("\n=== Memory Limit Effect on Medians (relative to 1.0 CPU / 512 MiB) ===")
mem_comp = sensitivity_df[sensitivity_df["cpu_quota"] == 1.0][["mem_limit_mib", "algorithm", "operation", "median_of_medians", "median_change_pct", "cov_pct"]]
print(mem_comp.pivot(index=["algorithm", "operation"], columns="mem_limit_mib", values=["median_of_medians", "median_change_pct"]).round(2).to_string())

# 5. Generate 6 Specialized Scientific Plots
# Plot 1: CPU quota vs operation latency
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
axes = axes.flatten()
cpu_subset = config_summary[config_summary["mem_limit_mib"] == 512]
cpu_vals = [0.5, 1.0, 2.0]

for ax, (alg, ops) in zip(axes, [
    ("ML-KEM-768", ["keygen", "encapsulation", "decapsulation"]),
    ("X25519", ["keygen", "shared_secret_derivation"]),
    ("ECDSA-P256", ["keygen", "sign", "verify"]),
    ("ML-DSA-65", ["keygen", "sign", "verify"])
]):
    sub = cpu_subset[cpu_subset["algorithm"] == alg]
    for op in ops:
        op_sub = sub[sub["operation"] == op].sort_values("cpu_quota")
        ax.plot(op_sub["cpu_quota"], op_sub["median_of_medians"], marker="o", linewidth=1.8, label=op)
    ax.set_title(f"{alg} Latency vs CPU Quota (Mem=512M)", fontsize=11, fontweight="bold")
    ax.set_xlabel("CPU Quota (cores)")
    ax.set_ylabel("Median Latency (µs)")
    ax.set_xticks(cpu_vals)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()
plt.tight_layout()
plt.savefig(output_dir / "plot1_cpu_quota_vs_latency.png", dpi=180)
plt.close()

# Plot 2: CPU quota vs throttling
plt.figure(figsize=(8, 5))
cpu_telem = telemetry_df[telemetry_df["mem_limit_mib"] == 512].groupby("cpu_quota").agg(
    mean_throttled_ms=("throttled_ms", "mean"),
    mean_nr_throttled=("nr_throttled", "mean")
).reset_index()
plt.bar([str(c) + " CPU" for c in cpu_telem["cpu_quota"]], cpu_telem["mean_throttled_ms"], color="crimson", alpha=0.8, width=0.5)
plt.title("CFS CPU Throttling Duration vs CPU Quota (Mem=512M)", fontsize=12, fontweight="bold")
plt.xlabel("Configured CPU Quota")
plt.ylabel("Throttled CPU Time (milliseconds)")
plt.grid(True, linestyle="--", alpha=0.4, axis="y")
for i, v in enumerate(cpu_telem["mean_throttled_ms"]):
    plt.text(i, v + 0.5, f"{v:.1f} ms\n({cpu_telem['mean_nr_throttled'][i]:.0f} periods)", ha="center", fontsize=9)
plt.tight_layout()
plt.savefig(output_dir / "plot2_cpu_quota_vs_throttling.png", dpi=180)
plt.close()

# Plot 3: Memory limit vs measured RSS and container memory
plt.figure(figsize=(9, 5.5))
mem_telem = telemetry_df[telemetry_df["cpu_quota"] == 1.0].groupby("mem_limit_mib").agg(
    rss=("peak_rss_mib", "mean"),
    container=("container_mem_mib", "mean")
).reset_index()

x = np.arange(len(mem_telem))
width = 0.35
plt.bar(x - width/2, mem_telem["rss"], width, label="Peak Process RSS (MiB)", color="royalblue")
plt.bar(x + width/2, mem_telem["container"], width, label="Container Memory Current (MiB)", color="seagreen")
plt.title("Measured Memory Consumption vs Configured Memory Limit (CPU=1.0)", fontsize=12, fontweight="bold")
plt.xlabel("Configured Memory Limit (MiB)")
plt.ylabel("Memory (MiB)")
plt.xticks(x, [f"{m} MiB" for m in mem_telem["mem_limit_mib"]])
plt.grid(True, linestyle="--", alpha=0.4, axis="y")
plt.legend()
for i in x:
    plt.text(i - width/2, mem_telem["rss"][i] + 1, f"{mem_telem['rss'][i]:.1f}", ha="center", fontsize=9)
    plt.text(i + width/2, mem_telem["container"][i] + 1, f"{mem_telem['container'][i]:.1f}", ha="center", fontsize=9)
plt.tight_layout()
plt.savefig(output_dir / "plot3_memory_limit_vs_measured_memory.png", dpi=180)
plt.close()

# Plot 4: Memory limit vs operation latency
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
axes = axes.flatten()
mem_subset = config_summary[config_summary["cpu_quota"] == 1.0]
mem_vals = [256, 512, 1024]

for ax, (alg, ops) in zip(axes, [
    ("ML-KEM-768", ["keygen", "encapsulation", "decapsulation"]),
    ("X25519", ["keygen", "shared_secret_derivation"]),
    ("ECDSA-P256", ["keygen", "sign", "verify"]),
    ("ML-DSA-65", ["keygen", "sign", "verify"])
]):
    sub = mem_subset[mem_subset["algorithm"] == alg]
    for op in ops:
        op_sub = sub[sub["operation"] == op].sort_values("mem_limit_mib")
        ax.plot(op_sub["mem_limit_mib"], op_sub["median_of_medians"], marker="s", linewidth=1.8, label=op)
    ax.set_title(f"{alg} Latency vs Memory Limit (CPU=1.0)", fontsize=11, fontweight="bold")
    ax.set_xlabel("Memory Limit (MiB)")
    ax.set_ylabel("Median Latency (µs)")
    ax.set_xticks(mem_vals)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()
plt.tight_layout()
plt.savefig(output_dir / "plot4_memory_limit_vs_latency.png", dpi=180)
plt.close()

# Plot 5: P95 and P99 tail latency changes across configurations
plt.figure(figsize=(13, 6))
# Compare P95 for ML-DSA sign, ECDSA verify, ML-KEM encap, X25519 keygen across all 5 configs
selected_ops = [
    ("ML-DSA-65", "sign"),
    ("ECDSA-P256", "verify"),
    ("X25519", "keygen"),
    ("ML-KEM-768", "encapsulation")
]
configs = ["0.5 CPU / 512 MiB", "1.0 CPU / 512 MiB", "2.0 CPU / 512 MiB", "1.0 CPU / 256 MiB", "1.0 CPU / 1024 MiB"]
x = np.arange(len(configs))
width = 0.2

for i, (alg, op) in enumerate(selected_ops):
    vals = []
    for cfg in configs:
        cpu_v = float(cfg.split()[0])
        mem_v = int(cfg.split()[3])
        row = config_summary[(config_summary["cpu_quota"] == cpu_v) & (config_summary["mem_limit_mib"] == mem_v) & (config_summary["algorithm"] == alg) & (config_summary["operation"] == op)]
        vals.append(row["mean_p95"].values[0] if not row.empty else 0)
    plt.bar(x + i*width - 1.5*width, vals, width, label=f"{alg} {op}")

plt.title("Tail Latency (P95) Across Resource Configurations", fontsize=12, fontweight="bold")
plt.ylabel("P95 Latency (µs)")
plt.xticks(x, configs, rotation=10)
plt.grid(True, linestyle="--", alpha=0.4, axis="y")
plt.legend()
plt.tight_layout()
plt.savefig(output_dir / "plot5_tail_latency_p95_comparison.png", dpi=180)
plt.close()

# Plot 6: Run-to-Run Variability (Coefficient of Variation %) across configurations
plt.figure(figsize=(11, 5.5))
cov_pivot = config_summary.pivot(index=["algorithm", "operation"], columns="config_label", values="cov_pct")
cov_pivot.plot(kind="bar", figsize=(14, 6), width=0.8)
plt.title("Run-to-Run Coefficient of Variation (%) Across Configurations", fontsize=12, fontweight="bold")
plt.ylabel("CoV (%) between 3 Independent Repeats")
plt.xlabel("Algorithm / Operation")
plt.xticks(rotation=45, ha="right")
plt.grid(True, linestyle="--", alpha=0.4, axis="y")
plt.legend(title="Configuration")
plt.tight_layout()
plt.savefig(output_dir / "plot6_run_to_run_variability_cov.png", dpi=180)
plt.close()

print(f"\nAll 6 Stage C scientific plots generated in {output_dir}:")
for p in sorted(output_dir.glob("plot*.png")):
    print(f" - {p.name}")
