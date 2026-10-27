#!/usr/bin/env python3
"""
Stage D1-D: Local TCP Loopback Transmission Microbenchmark
Empirical Migration Feasibility Analysis of Post-Quantum Cryptography for Resource-Constrained Systems

Measures actual socket transmission performance over local loopback (127.0.0.1) for:
1. Exact cryptographic artifact payload sizes (X25519 PK, ML-KEM PK/CT, ECDSA PK/Sig, ML-DSA PK/Sig)
2. Scenario K1 and K2 key establishment message sizes
3. Parametric application payload sweep (16B to 4096B)

Distinguishes:
- Connection establishment latency (isolated from data transfer)
- Transfer latency (send start to receiver complete)
- Round-trip delivery latency (send start to confirmation ACK)
- Effective throughput (MB/s)

Outputs:
- transport_raw.csv
- transport_summary.csv
- transport_manifest.json
"""

import argparse
import csv
import json
import os
import platform
import socket
import struct
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

def recv_exact(sock: socket.socket, num_bytes: int) -> bytes:
    """Reads exactly num_bytes from socket, looping until complete or connection closes."""
    buf = bytearray()
    while len(buf) < num_bytes:
        chunk = sock.recv(min(num_bytes - len(buf), 65536))
        if not chunk:
            raise ConnectionError(f"Socket closed unexpectedly after {len(buf)}/{num_bytes} bytes")
        buf.extend(chunk)
    return bytes(buf)

class LoopbackBenchmarkServer:
    def __init__(self, host="127.0.0.1", port=0):
        self.host = host
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.server_sock.bind((self.host, port))
        self.server_sock.listen(1)
        self.port = self.server_sock.getsockname()[1]
        self.client_conn = None
        self.running = True
        self.last_recv_ts = 0
        self.last_payload = b""
        self.last_valid = False

    def accept_client(self):
        self.server_sock.settimeout(5.0)
        conn, addr = self.server_sock.accept()
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        conn.settimeout(5.0)
        self.client_conn = conn

    def serve_requests(self, expected_count: int, expected_payload: bytes):
        """Receives expected_count frames, verifies integrity against expected_payload, and ACKs."""
        for _ in range(expected_count):
            # 1. Read 4-byte big-endian length prefix
            prefix = recv_exact(self.client_conn, 4)
            length = struct.unpack(">I", prefix)[0]
            
            # 2. Read exact payload
            payload = recv_exact(self.client_conn, length)
            recv_complete_ts = time.perf_counter_ns()
            
            # 3. Verify integrity
            is_valid = (payload == expected_payload)
            self.last_valid = is_valid
            self.last_recv_ts = recv_complete_ts
            
            # 4. Send 1-byte ACK back to sender
            self.client_conn.sendall(b"\x06")

    def close(self):
        self.running = False
        if self.client_conn:
            try:
                self.client_conn.close()
            except Exception:
                pass
        try:
            self.server_sock.close()
        except Exception:
            pass

def run_transport_benchmark(trials: int, warmups: int, output_dir: Path, experiment_id: str):
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"=== Stage D1-D: Local Transmission Microbenchmark ===")
    print(f"Experiment ID: {experiment_id}")
    print(f"Trials per condition: {trials} (Warmups: {warmups})")
    print(f"Transport: Local TCP Loopback (127.0.0.1, TCP_NODELAY)")
    print("-" * 55)

    # Test Conditions: (Label, Category, Size Bytes, Description)
    test_conditions = [
        # Cryptographic Artifacts
        ("X25519_PK", "Artifact_Key", 32, "X25519 Public Key (32B)"),
        ("ECDSA_PK_Uncompressed", "Artifact_Key", 65, "ECDSA P-256 Public Key Uncompressed (65B)"),
        ("ECDSA_Sig_DER", "Artifact_Sig", 71, "ECDSA P-256 DER Signature (~71B)"),
        ("MLKEM_PK", "Artifact_Key", 1184, "ML-KEM-768 Public Key (1184B)"),
        ("MLKEM_CT", "Artifact_CT", 1088, "ML-KEM-768 Encapsulation Ciphertext (1088B)"),
        ("MLDSA_PK", "Artifact_Key", 1952, "ML-DSA-65 Public Key (1952B)"),
        ("MLDSA_Sig", "Artifact_Sig", 3309, "ML-DSA-65 Signature (3309B)"),
        
        # Message Scenarios
        ("Scenario_K1_X25519", "Scenario_KEM", 32, "K1 Initiator sends X25519 PK (32B)"),
        ("Scenario_K1_MLKEM", "Scenario_KEM", 1088, "K1 Initiator sends ML-KEM CT (1088B)"),
        ("Scenario_K2_X25519_2Way", "Scenario_KEM", 64, "K2 2-Way X25519 Handshake Total (64B)"),
        ("Scenario_K2_MLKEM_2Way", "Scenario_KEM", 2272, "K2 2-Way ML-KEM Handshake Total (2272B)"),
        
        # Parametric Payload Sweep
        ("Payload_16B", "Payload_Sweep", 16, "16-byte application payload"),
        ("Payload_32B", "Payload_Sweep", 32, "32-byte application payload"),
        ("Payload_64B", "Payload_Sweep", 64, "64-byte application payload"),
        ("Payload_128B", "Payload_Sweep", 128, "128-byte application payload"),
        ("Payload_256B", "Payload_Sweep", 256, "256-byte application payload"),
        ("Payload_512B", "Payload_Sweep", 512, "512-byte application payload"),
        ("Payload_1024B", "Payload_Sweep", 1024, "1024-byte application payload"),
        ("Payload_2048B", "Payload_Sweep", 2048, "2048-byte application payload"),
        ("Payload_4096B", "Payload_Sweep", 4096, "4096-byte application payload"),
    ]

    raw_records = []
    connection_setup_records = []

    # Start loopback server
    server = LoopbackBenchmarkServer()
    server_thread = threading.Thread(target=server.accept_client, daemon=True)
    server_thread.start()

    # Client socket
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    
    # 1. Measure Connection Setup Latency
    conn_t0 = time.perf_counter_ns()
    client_sock.connect(("127.0.0.1", server.port))
    conn_t1 = time.perf_counter_ns()
    server_thread.join(timeout=2.0)
    
    conn_setup_ns = conn_t1 - conn_t0
    conn_setup_us = round(conn_setup_ns / 1000.0, 3)
    print(f"[TCP] Established loopback connection on port {server.port} in {conn_setup_us:.2f} µs")
    
    connection_setup_records.append({
        "connect_duration_ns": conn_setup_ns,
        "connect_duration_us": conn_setup_us,
        "port": server.port
    })

    # Execute conditions
    for cond_idx, (label, category, size_bytes, desc) in enumerate(test_conditions, 1):
        # Deterministic pseudo-random payload of requested size
        payload = bytes([(i * 37 + 13) % 256 for i in range(size_bytes)])
        frame = struct.pack(">I", size_bytes) + payload

        # Server thread target for this condition
        total_runs = warmups + trials
        srv_worker = threading.Thread(
            target=server.serve_requests,
            args=(total_runs, payload),
            daemon=True
        )
        srv_worker.start()

        # Warm-ups
        for _ in range(warmups):
            client_sock.sendall(frame)
            ack = recv_exact(client_sock, 1)
            assert ack == b"\x06"

        # Recorded trials
        for t_idx in range(1, trials + 1):
            t_send_start = time.perf_counter_ns()
            client_sock.sendall(frame)
            
            # Wait for ACK from server
            ack = recv_exact(client_sock, 1)
            t_ack_end = time.perf_counter_ns()
            
            # Retrieve receiver timestamp from server
            t_recv_end = server.last_recv_ts
            is_valid = server.last_valid
            
            # Metrics
            one_way_ns = max(t_recv_end - t_send_start, 1)
            rtt_ns = max(t_ack_end - t_send_start, 1)
            one_way_us = round(one_way_ns / 1000.0, 3)
            rtt_us = round(rtt_ns / 1000.0, 3)
            
            # Throughput in MB/s based on payload bytes / one-way transfer time
            throughput_mb_s = round((size_bytes / (one_way_ns / 1e9)) / (1024 * 1024), 2)
            
            raw_records.append({
                "experiment_id": experiment_id,
                "trial": t_idx,
                "condition_label": label,
                "category": category,
                "payload_bytes": size_bytes,
                "total_frame_bytes": len(frame),
                "one_way_transfer_ns": one_way_ns,
                "one_way_transfer_us": one_way_us,
                "rtt_delivery_ns": rtt_ns,
                "rtt_delivery_us": rtt_us,
                "throughput_mb_s": throughput_mb_s,
                "payload_valid": is_valid,
                "timestamp_utc": datetime.now(timezone.utc).isoformat()
            })

        srv_worker.join(timeout=3.0)
        print(f"[{cond_idx:02d}/{len(test_conditions):02d}] {label:<24} ({size_bytes:>4} B): "
              f"Median = {pd.DataFrame(raw_records[-trials:])['one_way_transfer_us'].median():>6.2f} µs | "
              f"Throughput = {pd.DataFrame(raw_records[-trials:])['throughput_mb_s'].median():>8.2f} MB/s")

    # Clean shutdown
    client_sock.close()
    server.close()

    # 1. Write raw observations
    raw_df = pd.DataFrame(raw_records)
    raw_csv = output_dir / "transport_raw.csv"
    raw_df.to_csv(raw_csv, index=False)
    print(f"\n[OK] Wrote {len(raw_records)} raw transport measurement rows to {raw_csv}")

    # 2. Compute Summary Statistics
    summary_rows = []
    for (label, cat, p_bytes), g in raw_df.groupby(["condition_label", "category", "payload_bytes"], sort=False):
        lat = g["one_way_transfer_us"]
        rtt = g["rtt_delivery_us"]
        tp = g["throughput_mb_s"]
        
        summary_rows.append({
            "condition_label": label,
            "category": cat,
            "payload_bytes": p_bytes,
            "sample_count": len(g),
            "median_transfer_us": round(float(lat.median()), 3),
            "mean_transfer_us": round(float(lat.mean()), 3),
            "std_transfer_us": round(float(lat.std(ddof=1)), 3),
            "p90_transfer_us": round(float(lat.quantile(0.90)), 3),
            "p95_transfer_us": round(float(lat.quantile(0.95)), 3),
            "p99_transfer_us": round(float(lat.quantile(0.99)), 3),
            "median_rtt_us": round(float(rtt.median()), 3),
            "p95_rtt_us": round(float(rtt.quantile(0.95)), 3),
            "median_throughput_mb_s": round(float(tp.median()), 2),
            "mean_throughput_mb_s": round(float(tp.mean()), 2),
            "all_payloads_verified": bool(g["payload_valid"].all())
        })

    summary_df = pd.DataFrame(summary_rows)
    summary_csv = output_dir / "transport_summary.csv"
    summary_df.to_csv(summary_csv, index=False)
    print(f"[OK] Wrote transport summary to {summary_csv}")

    # 3. Write Transport Manifest
    manifest = {
        "experiment_id": experiment_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "transport_type": "TCP Loopback (127.0.0.1)",
        "socket_options": ["TCP_NODELAY=1", "SO_RCVTIMEO=5s", "SO_SNDTIMEO=5s"],
        "framing": "4-byte big-endian unsigned integer length prefix",
        "connection_setup": connection_setup_records[0],
        "trials_per_condition": trials,
        "warmups_per_condition": warmups,
        "total_trials_recorded": len(raw_records),
        "all_payloads_valid": bool(raw_df["payload_valid"].all()),
        "summary": summary_rows,
        "scientific_caveats": [
            "Local loopback tests measure Linux kernel network buffer copies and TCP stack overhead.",
            "Loopback tests DO NOT measure physical Ethernet, Wi-Fi, radio (802.15.4), or constrained WAN transmission latency.",
            "Transfer latency on physical IoT links will be dominated by packet serialization rate (baud rate / bitrate) and radio PHY headers."
        ]
    }
    manifest_json = output_dir / "transport_manifest.json"
    manifest_json.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[OK] Wrote transport manifest to {manifest_json}")

    return summary_df

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage D1-D Transport Benchmark")
    parser.add_argument("--trials", type=int, default=100, help="Trials per condition (default: 100)")
    parser.add_argument("--warmups", type=int, default=10, help="Warmup iterations (default: 10)")
    parser.add_argument("--output-dir", type=str, default="stage_d1_output")
    parser.add_argument("--experiment-id", type=str, default="")
    args = parser.parse_args()

    exp_id = args.experiment_id or f"EXP_STAGE_D1_TRANS_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    run_transport_benchmark(args.trials, args.warmups, Path(args.output_dir), exp_id)
