from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

import os
import sys

results_dir = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("RESULTS_DIR", "results"))
source = results_dir / "benchmark_raw.csv"
if not source.exists():
    raise SystemExit("Missing results/benchmark_raw.csv. Run benchmark.py first.")

df = pd.read_csv(source)

def calc_iqr(x):
    return x.quantile(0.75) - x.quantile(0.25)

def calc_mad(x):
    return (x - x.median()).abs().median()

summary = (
    df.groupby(["algorithm", "category", "operation"], as_index=False)
      .agg(samples=("time_us", "count"),
           median_us=("time_us", "median"),
           mean_us=("time_us", "mean"),
           std_us=("time_us", "std"),
           min_us=("time_us", "min"),
           max_us=("time_us", "max"),
           p90_us=("time_us", lambda x: x.quantile(0.90)),
           p95_us=("time_us", lambda x: x.quantile(0.95)),
           p99_us=("time_us", lambda x: x.quantile(0.99)),
           iqr_us=("time_us", calc_iqr),
           mad_us=("time_us", calc_mad),
           public_key_bytes=("public_key_bytes", "median"),
           artifact_bytes=("ciphertext_or_signature_bytes", "median"))
)
summary.to_csv(results_dir / "benchmark_summary.csv", index=False)

# Separate timing charts by operation family so unrelated operations are not
# compared on a misleading common scale.
for category, filename, title in [
    ("KEM/key agreement", "kem_timing.png", "Key establishment operation timings"),
    ("Digital signature", "signature_timing.png", "Digital signature operation timings"),
]:
    subset = summary[summary["category"] == category].copy()
    if subset.empty:
        continue
    subset["label"] = subset["algorithm"] + "\n" + subset["operation"]
    plt.figure(figsize=(11, 6))
    plt.bar(subset["label"], subset["median_us"])
    plt.ylabel("Median time (microseconds)")
    plt.title(title)
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(results_dir / filename, dpi=180)
    plt.close()

# Compare public-key and ciphertext/signature sizes, preserving categories.
size_df = (
    df.groupby(["algorithm", "category"], as_index=False)
      .agg(public_key_bytes=("public_key_bytes", "max"),
           artifact_bytes=("ciphertext_or_signature_bytes", "max"))
)
for column, filename, title in [
    ("public_key_bytes", "public_key_sizes.png", "Public key sizes"),
    ("artifact_bytes", "ciphertext_signature_sizes.png",
     "KEM ciphertext / digital signature sizes"),
]:
    plot_df = size_df[size_df[column] > 0]
    if plot_df.empty:
        continue
    plt.figure(figsize=(9, 5))
    plt.bar(plot_df["algorithm"], plot_df[column])
    plt.ylabel("Bytes")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(results_dir / filename, dpi=180)
    plt.close()

print("Created:")
for p in sorted(results_dir.glob("*.png")):
    print(" -", p)
print(" -", results_dir / "benchmark_summary.csv")
print("\nSummary:")
print(summary.to_string(index=False))
