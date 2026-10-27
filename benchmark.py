import csv
import json
import os
import platform
import random
import resource
import ssl
import statistics
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import oqs
import cryptography
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, x25519
from cryptography.exceptions import InvalidSignature

# Configuration from environment with robust defaults
OUT = Path(os.environ.get("RESULTS_DIR", "results"))
OUT.mkdir(parents=True, exist_ok=True)
N = int(os.environ.get("N_RUNS", "100"))
WARMUPS = int(os.environ.get("WARMUPS", "5"))
ORDER_POLICY = os.environ.get("ORDER_POLICY", "fixed").lower()
ORDER_SEED = int(os.environ.get("ORDER_SEED", "42"))
EXPERIMENT_ID = os.environ.get(
    "EXPERIMENT_ID", f"EXP_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
)
RUN_ID = os.environ.get(
    "RUN_ID", f"RUN_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
)

MESSAGE = b"PQC migration feasibility benchmark - fixed 128-byte research message." * 2

ALGORITHM_SPECS = {
    "ML-KEM-768": {
        "standard": "NIST FIPS 203",
        "type": "Key Encapsulation Mechanism (KEM)",
        "claimed_security": "Category 3 (~128-bit post-quantum security)",
        "parameter_set": "ml-kem-768 (Kyber-768 equivalent)",
    },
    "ML-DSA-65": {
        "standard": "NIST FIPS 204",
        "type": "Digital Signature Scheme",
        "claimed_security": "Category 3 (~128-bit post-quantum security)",
        "parameter_set": "ml-dsa-65 (Dilithium3 equivalent)",
    },
    "X25519": {
        "standard": "RFC 7748",
        "type": "Elliptic-Curve Diffie-Hellman Key Agreement",
        "claimed_security": "128-bit classical security (broken by cryptanalytically relevant quantum computer)",
        "parameter_set": "Curve25519",
    },
    "ECDSA-P256": {
        "standard": "NIST FIPS 186-5 / ANSI X9.62",
        "type": "Elliptic-Curve Digital Signature Scheme",
        "claimed_security": "128-bit classical security (broken by cryptanalytically relevant quantum computer)",
        "parameter_set": "secp256r1 curve, SHA-256 digest",
    },
}

def read_cgroup_file(path_str):
    p = Path(path_str)
    if p.exists():
        try:
            return p.read_text(encoding="utf-8").strip()
        except Exception:
            return None
    return None

def parse_cgroup_kv(text):
    if not text:
        return {}
    res = {}
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2:
            try:
                res[parts[0]] = int(parts[1])
            except ValueError:
                res[parts[0]] = parts[1]
    return res

def get_resource_metrics():
    metrics = {
        "ru_maxrss_bytes": None,
        "cgroup_memory_current_bytes": None,
        "cgroup_memory_max_bytes": None,
        "cgroup_memory_events": {},
        "cgroup_cpu_max": None,
        "cgroup_cpu_stat": {},
        "system_load_average": None,
        "direct_cpu_frequency_khz": "UNAVAILABLE (inaccessible inside unprivileged virtualization container)",
    }
    try:
        if hasattr(os, "getloadavg"):
            l1, l5, l15 = os.getloadavg()
            metrics["system_load_average"] = {
                "load_1min": round(l1, 4),
                "load_5min": round(l5, 4),
                "load_15min": round(l15, 4),
            }
    except Exception as e:
        metrics["system_load_average_error"] = str(e)
    try:
        rusage = resource.getrusage(resource.RUSAGE_SELF)
        # On Linux, ru_maxrss is in KiB. Convert to bytes.
        metrics["ru_maxrss_bytes"] = int(rusage.ru_maxrss * 1024)
    except Exception as e:
        metrics["ru_maxrss_error"] = str(e)

    mem_curr = read_cgroup_file("/sys/fs/cgroup/memory.current")
    if mem_curr is not None:
        try:
            metrics["cgroup_memory_current_bytes"] = int(mem_curr)
        except ValueError:
            metrics["cgroup_memory_current_bytes"] = mem_curr

    mem_max = read_cgroup_file("/sys/fs/cgroup/memory.max")
    if mem_max is not None:
        try:
            metrics["cgroup_memory_max_bytes"] = int(mem_max)
        except ValueError:
            metrics["cgroup_memory_max_bytes"] = mem_max

    mem_events = read_cgroup_file("/sys/fs/cgroup/memory.events")
    if mem_events is not None:
        metrics["cgroup_memory_events"] = parse_cgroup_kv(mem_events)

    cpu_max = read_cgroup_file("/sys/fs/cgroup/cpu.max")
    if cpu_max is not None:
        metrics["cgroup_cpu_max"] = cpu_max

    cpu_stat = read_cgroup_file("/sys/fs/cgroup/cpu.stat")
    if cpu_stat is not None:
        metrics["cgroup_cpu_stat"] = parse_cgroup_kv(cpu_stat)

    return metrics

def compute_stats(values):
    if not values:
        return {}
    s = sorted(values)
    n = len(s)
    mean = statistics.mean(s)
    median = statistics.median(s)
    stdev = statistics.stdev(s) if n > 1 else 0.0
    min_v = s[0]
    max_v = s[-1]

    def quantile(p):
        idx = (n - 1) * p
        lower = int(idx)
        upper = lower + 1
        weight = idx - lower
        if upper < n:
            return s[lower] * (1 - weight) + s[upper] * weight
        return s[lower]

    p25 = quantile(0.25)
    p75 = quantile(0.75)
    iqr = p75 - p25
    p90 = quantile(0.90)
    p95 = quantile(0.95)
    p99 = quantile(0.99)
    mad = statistics.median([abs(x - median) for x in s])

    return {
        "count": n,
        "median": round(median, 4),
        "mean": round(mean, 4),
        "std": round(stdev, 4),
        "min": round(min_v, 4),
        "max": round(max_v, 4),
        "p90": round(p90, 4),
        "p95": round(p95, 4),
        "p99": round(p99, 4),
        "iqr": round(iqr, 4),
        "mad": round(mad, 4),
    }

rows = []
correctness_records = []

def timed_operation(fn):
    """
    High-resolution timing boundary using time.perf_counter_ns().
    Returns (elapsed_ns, return_value).
    """
    start_ns = time.perf_counter_ns()
    res = fn()
    end_ns = time.perf_counter_ns()
    return (end_ns - start_ns), res

def record(algorithm, category, operation, trial, elapsed_ns,
           public_key_bytes=0, artifact_bytes=0, message_bytes=len(MESSAGE),
           correct=True, iteration_order=None):
    elapsed_us = elapsed_ns / 1000.0
    rows.append({
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "liboqs_version": oqs.oqs_version(),
        "algorithm": algorithm,
        "category": category,
        "operation": operation,
        "trial": trial,
        "elapsed_ns": int(elapsed_ns),
        "time_us": round(elapsed_us, 4),
        "public_key_bytes": int(public_key_bytes),
        "ciphertext_or_signature_bytes": int(artifact_bytes),
        "message_bytes": int(message_bytes),
        "correctness_check": bool(correct),
        "iteration_order": iteration_order or "",
    })

def run_x25519(order_idx):
    alg = "X25519"
    cat = "KEM/key agreement"

    # Warm-up phase
    for _ in range(WARMUPS):
        p1 = x25519.X25519PrivateKey.generate()
        p2 = x25519.X25519PrivateKey.generate()
        s1 = p1.exchange(p2.public_key())
        s2 = p2.exchange(p1.public_key())
        assert s1 == s2 and len(s1) == 32

    for i in range(1, N + 1):
        # 1. Timed Key Generation
        elapsed_ns, priv = timed_operation(x25519.X25519PrivateKey.generate)
        pub_bytes = priv.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        record(alg, cat, "keygen", i, elapsed_ns, len(pub_bytes), 0,
               correct=True, iteration_order=f"{order_idx}")

        # 2. Peer generation (outside timing)
        peer = x25519.X25519PrivateKey.generate()
        peer_pub = peer.public_key()

        # 3. Timed Shared Secret Derivation
        elapsed_ns, secret = timed_operation(lambda: priv.exchange(peer_pub))

        # 4. Correctness verification (outside timing)
        peer_secret = peer.exchange(priv.public_key())
        is_correct = (secret == peer_secret and len(secret) == 32)
        if not is_correct:
            correctness_records.append({"algorithm": alg, "trial": i, "error": "Shared secret mismatch"})
            raise RuntimeError(f"X25519 shared secret mismatch on trial {i}")

        record(alg, cat, "shared_secret_derivation", i, elapsed_ns, len(pub_bytes), 0,
               correct=is_correct, iteration_order=f"{order_idx}")

def run_mlkem(order_idx):
    alg = "ML-KEM-768"
    cat = "KEM/key establishment"

    with oqs.KeyEncapsulation(alg) as kem:
        details = kem.details
        pk_len = int(details.get("length_public_key", 0))
        ct_len = int(details.get("length_ciphertext", 0))

        # Warm-up phase
        for _ in range(WARMUPS):
            pk = kem.generate_keypair()
            ct, ss_srv = kem.encap_secret(pk)
            ss_cli = kem.decap_secret(ct)
            assert ss_srv == ss_cli

        for i in range(1, N + 1):
            # 1. Timed Key Generation
            elapsed_ns, pk = timed_operation(kem.generate_keypair)
            record(alg, cat, "keygen", i, elapsed_ns, len(pk) or pk_len, 0,
                   correct=True, iteration_order=f"{order_idx}")

            # 2. Timed Encapsulation
            elapsed_ns, encap_res = timed_operation(lambda: kem.encap_secret(pk))
            ct, ss_server = encap_res
            record(alg, cat, "encapsulation", i, elapsed_ns, len(pk) or pk_len, len(ct),
                   correct=True, iteration_order=f"{order_idx}")

            # 3. Timed Decapsulation
            elapsed_ns, ss_client = timed_operation(lambda: kem.decap_secret(ct))

            # 4. Correctness verification (outside timing)
            is_correct = (ss_server == ss_client)
            if not is_correct:
                correctness_records.append({"algorithm": alg, "trial": i, "error": "ML-KEM shared secret mismatch"})
                raise RuntimeError(f"ML-KEM shared secret mismatch on trial {i}")

            record(alg, cat, "decapsulation", i, elapsed_ns, len(pk) or pk_len, len(ct),
                   correct=is_correct, iteration_order=f"{order_idx}")

def run_ecdsa(order_idx):
    alg = "ECDSA-P256"
    cat = "Digital signature"

    # Warm-up phase
    for _ in range(WARMUPS):
        k = ec.generate_private_key(ec.SECP256R1())
        sig = k.sign(MESSAGE, ec.ECDSA(hashes.SHA256()))
        k.public_key().verify(sig, MESSAGE, ec.ECDSA(hashes.SHA256()))

    for i in range(1, N + 1):
        # 1. Timed Key Generation
        elapsed_ns, priv = timed_operation(lambda: ec.generate_private_key(ec.SECP256R1()))
        pub = priv.public_key()
        pub_bytes = pub.public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint
        )
        record(alg, cat, "keygen", i, elapsed_ns, len(pub_bytes), 0,
               correct=True, iteration_order=f"{order_idx}")

        # 2. Timed Sign
        elapsed_ns, signature = timed_operation(
            lambda: priv.sign(MESSAGE, ec.ECDSA(hashes.SHA256()))
        )
        record(alg, cat, "sign", i, elapsed_ns, len(pub_bytes), len(signature),
               correct=True, iteration_order=f"{order_idx}")

        # 3. Timed Verify (Positive)
        def verify_fn():
            try:
                pub.verify(signature, MESSAGE, ec.ECDSA(hashes.SHA256()))
                return True
            except InvalidSignature:
                return False

        elapsed_ns, ok = timed_operation(verify_fn)

        # 4. Negative verification test (outside timing)
        corrupted_message = MESSAGE[:-1] + (b"\x00" if MESSAGE[-1:] != b"\x00" else b"\x01")
        negative_ok = False
        try:
            pub.verify(signature, corrupted_message, ec.ECDSA(hashes.SHA256()))
        except InvalidSignature:
            negative_ok = True

        is_correct = bool(ok and negative_ok)
        if not is_correct:
            correctness_records.append({"algorithm": alg, "trial": i, "error": "ECDSA verification failure"})
            raise RuntimeError(f"ECDSA verification failed on trial {i}")

        record(alg, cat, "verify", i, elapsed_ns, len(pub_bytes), len(signature),
               correct=is_correct, iteration_order=f"{order_idx}")

def run_mldsa(order_idx):
    alg = "ML-DSA-65"
    cat = "Digital signature"

    with oqs.Signature(alg) as signer:
        details = signer.details
        pk_len = int(details.get("length_public_key", 0))
        sig_len = int(details.get("length_signature", 0))

        # Warm-up phase
        for _ in range(WARMUPS):
            pk = signer.generate_keypair()
            sig = signer.sign(MESSAGE)
            assert signer.verify(MESSAGE, sig, pk)

        for i in range(1, N + 1):
            # 1. Timed Key Generation
            elapsed_ns, pk = timed_operation(signer.generate_keypair)
            record(alg, cat, "keygen", i, elapsed_ns, len(pk) or pk_len, 0,
                   correct=True, iteration_order=f"{order_idx}")

            # 2. Timed Sign
            elapsed_ns, signature = timed_operation(lambda: signer.sign(MESSAGE))
            record(alg, cat, "sign", i, elapsed_ns, len(pk) or pk_len, len(signature) or sig_len,
                   correct=True, iteration_order=f"{order_idx}")

            # 3. Timed Verify
            elapsed_ns, ok = timed_operation(lambda: signer.verify(MESSAGE, signature, pk))

            # 4. Negative verification test (outside timing)
            corrupted_message = MESSAGE[:-1] + (b"\x00" if MESSAGE[-1:] != b"\x00" else b"\x01")
            negative_ok = not signer.verify(corrupted_message, signature, pk)

            is_correct = bool(ok and negative_ok)
            if not is_correct:
                correctness_records.append({"algorithm": alg, "trial": i, "error": "ML-DSA verification failure"})
                raise RuntimeError(f"ML-DSA verification failed on trial {i}")

            record(alg, cat, "verify", i, elapsed_ns, len(pk) or pk_len, len(signature) or sig_len,
                   correct=is_correct, iteration_order=f"{order_idx}")

def determine_execution_order():
    algorithms = ["X25519", "ML-KEM-768", "ECDSA-P256", "ML-DSA-65"]
    if ORDER_POLICY == "rotate":
        shift = ORDER_SEED % len(algorithms)
        return algorithms[shift:] + algorithms[:shift]
    elif ORDER_POLICY == "random":
        r = random.Random(ORDER_SEED)
        shuffled = list(algorithms)
        r.shuffle(shuffled)
        return shuffled
    else:
        # Default fixed order
        return algorithms

def main():
    bench_start_utc = datetime.now(timezone.utc).isoformat()
    wall_start = time.perf_counter()
    initial_resources = get_resource_metrics()

    exec_order = determine_execution_order()
    runner_map = {
        "X25519": run_x25519,
        "ML-KEM-768": run_mlkem,
        "ECDSA-P256": run_ecdsa,
        "ML-DSA-65": run_mldsa,
    }

    print(f"=== PQC Feasibility Benchmark Harness ===")
    print(f"Experiment ID:   {EXPERIMENT_ID}")
    print(f"Run ID:          {RUN_ID}")
    print(f"liboqs version:  {oqs.oqs_version()} (python: {oqs.oqs_python_version()})")
    print(f"cryptography:    {cryptography.__version__}")
    print(f"OpenSSL:         {ssl.OPENSSL_VERSION}")
    print(f"Trials/Op:       {N} | Warmups: {WARMUPS}")
    print(f"Order policy:    {ORDER_POLICY} (seed={ORDER_SEED})")
    print(f"Execution order: {' -> '.join(exec_order)}")
    print(f"Output directory:{OUT.resolve()}")
    print("-" * 45)

    for idx, alg_name in enumerate(exec_order, 1):
        print(f"[{idx}/{len(exec_order)}] Executing {alg_name}...")
        runner_map[alg_name](idx)

    bench_end_utc = datetime.now(timezone.utc).isoformat()
    wall_duration_s = time.perf_counter() - wall_start
    final_resources = get_resource_metrics()

    # 1. Write benchmark_raw.csv
    raw_path = OUT / "benchmark_raw.csv"
    fields = list(rows[0].keys())
    with raw_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n[OK] Saved {len(rows)} raw measurement rows to {raw_path}")

    # 2. Compute and write benchmark_summary.csv
    grouped_rows = {}
    for r in rows:
        key = (r["algorithm"], r["category"], r["operation"])
        grouped_rows.setdefault(key, []).append(r)

    summary_rows = []
    print("\nStatistical Summary (microseconds):")
    header_str = f"{'Algorithm':12} {'Operation':25} {'Samples':>7} {'Median':>9} {'Mean':>9} {'Std':>9} {'IQR':>9} {'MAD':>9} {'P95':>9}"
    print(header_str)
    print("-" * len(header_str))

    for (alg, cat, op), r_list in sorted(grouped_rows.items()):
        times_us = [x["time_us"] for x in r_list]
        stats = compute_stats(times_us)
        pk_bytes = r_list[0]["public_key_bytes"]
        art_bytes = r_list[0]["ciphertext_or_signature_bytes"]

        summary_rows.append({
            "algorithm": alg,
            "category": cat,
            "operation": op,
            "samples": stats["count"],
            "median_us": stats["median"],
            "mean_us": stats["mean"],
            "std_us": stats["std"],
            "min_us": stats["min"],
            "max_us": stats["max"],
            "p90_us": stats["p90"],
            "p95_us": stats["p95"],
            "p99_us": stats["p99"],
            "iqr_us": stats["iqr"],
            "mad_us": stats["mad"],
            "public_key_bytes": pk_bytes,
            "artifact_bytes": art_bytes,
        })
        print(f"{alg:12} {op:25} {stats['count']:7d} {stats['median']:9.3f} {stats['mean']:9.3f} {stats['std']:9.3f} {stats['iqr']:9.3f} {stats['mad']:9.3f} {stats['p95']:9.3f}")

    sum_path = OUT / "benchmark_summary.csv"
    with sum_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)
    print(f"[OK] Saved statistical summary to {sum_path}")

    # 3. Create run_manifest.json
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": RUN_ID,
        "start_utc": bench_start_utc,
        "end_utc": bench_end_utc,
        "wall_duration_seconds": round(wall_duration_s, 4),
        "environment": {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "python_compiler": platform.python_compiler(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
        },
        "software_versions": {
            "liboqs": oqs.oqs_version(),
            "liboqs_python": oqs.oqs_python_version(),
            "cryptography": cryptography.__version__,
            "openssl": ssl.OPENSSL_VERSION,
        },
        "configuration": {
            "trials_per_operation": N,
            "warmups_per_operation": WARMUPS,
            "order_policy": ORDER_POLICY,
            "order_seed": ORDER_SEED,
            "execution_order": exec_order,
            "message_length_bytes": len(MESSAGE),
            "algorithm_specifications": ALGORITHM_SPECS,
        },
        "resource_monitoring": {
            "initial_snapshot": initial_resources,
            "final_snapshot": final_resources,
            "peak_process_rss_bytes": final_resources["ru_maxrss_bytes"],
            "peak_process_rss_kib": round(final_resources["ru_maxrss_bytes"] / 1024, 2) if final_resources["ru_maxrss_bytes"] else None,
            "container_memory_current_bytes": final_resources["cgroup_memory_current_bytes"],
            "container_memory_max_bytes": final_resources["cgroup_memory_max_bytes"],
            "container_cpu_max": final_resources["cgroup_cpu_max"],
            "container_cpu_throttling": {
                "nr_periods": final_resources["cgroup_cpu_stat"].get("nr_periods", 0) - initial_resources["cgroup_cpu_stat"].get("nr_periods", 0),
                "nr_throttled": final_resources["cgroup_cpu_stat"].get("nr_throttled", 0) - initial_resources["cgroup_cpu_stat"].get("nr_throttled", 0),
                "throttled_usec": final_resources["cgroup_cpu_stat"].get("throttled_usec", 0) - initial_resources["cgroup_cpu_stat"].get("throttled_usec", 0),
            },
        },
        "correctness": {
            "all_passed": len(correctness_records) == 0 and all(r["correctness_check"] for r in rows),
            "total_checks": len(rows),
            "failures": correctness_records,
        },
        "output_files": {
            "raw_csv": str(raw_path.name),
            "summary_csv": str(sum_path.name),
            "manifest_json": "run_manifest.json",
        }
    }

    manifest_path = OUT / "run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[OK] Saved run manifest to {manifest_path}")

    # Also save standalone resource_usage.json
    res_path = OUT / "resource_usage.json"
    res_path.write_text(json.dumps(manifest["resource_monitoring"], indent=2), encoding="utf-8")
    print(f"[OK] Saved resource monitoring to {res_path}")

    if not manifest["correctness"]["all_passed"]:
        raise RuntimeError("Correctness checks failed during execution!")

if __name__ == "__main__":
    main()
