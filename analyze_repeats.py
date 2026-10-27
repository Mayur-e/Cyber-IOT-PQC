import pandas as pd

folders = {
    "Run 1": "results_cpu1_mem512_n1000_run1/benchmark_raw.csv",
    "Run 2": "results_cpu1_mem512_n1000_run2/benchmark_raw.csv",
    "Run 3": "results_cpu1_mem512_n1000_run3/benchmark_raw.csv",
}

frames = []
for run, path in folders.items():
    df = pd.read_csv(path)
    df["run"] = run
    frames.append(df)

data = pd.concat(frames, ignore_index=True)

print("\n=== Per-run timing summary (microseconds) ===")
summary = data.groupby(
    ["algorithm", "operation", "run"]
)["time_us"].agg(
    median="median",
    mean="mean",
    std="std",
    p90=lambda x: x.quantile(0.90),
    samples="count",
).round(3)

print(summary.to_string())

print("\n=== ML-KEM timing by trial block ===")
kem = data[
    (data["algorithm"] == "ML-KEM-768")
].copy()

if "trial" in kem.columns:
    # Fix off-by-one indexing: trials are 1-indexed (1 to 1000).
    # Group into exact 100-trial blocks: 1-100, 101-200, ..., 901-1000.
    block_num = (kem["trial"] - 1) // 100 + 1
    kem["block"] = block_num.apply(lambda b: f"{(b - 1) * 100 + 1:04d}-{b * 100:04d}")
    block_summary = kem.groupby(
        ["operation", "run", "block"]
    )["time_us"].agg(
        median="median",
        count="count"
    ).round(3)
    print(block_summary.to_string())
else:
    print("No trial column found; inspect CSV columns:")
    print(data.columns.tolist())
