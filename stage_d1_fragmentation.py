#!/usr/bin/env python3
"""
Stage D1-C: MTU and Link-Layer Fragmentation Modeling
Empirical Migration Feasibility Analysis of Post-Quantum Cryptography for Resource-Constrained Systems

Evaluates the packet fragmentation characteristics of classical and PQC artifacts across:
1. Nominal 1500-byte Ethernet IP MTU
2. Nominal 128-byte IEEE 802.15.4 / 6LoWPAN Link-Layer Frame Budget

Implements:
- Mode A: Raw Artifact Planning (usable payload = configured budget)
- Mode B: Header-Aware Modeled Payload (usable payload = budget - overhead)

Outputs:
- fragmentation_analysis.csv
- fragmentation_assumptions.json
"""

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

def calculate_fragments(artifact_bytes: int, configured_budget: int, modeled_overhead: int):
    """
    Computes fragment count and last fragment size using ceiling division.
    Handles boundary conditions rigorously:
    - 0 bytes: 0 fragments, last fragment 0
    - Exact multiple of usable payload: last fragment equals usable payload
    - 1 byte over usable payload: creates new fragment of 1 byte
    """
    usable_payload = configured_budget - modeled_overhead
    if usable_payload <= 0:
        raise ValueError(f"Overhead ({modeled_overhead}B) >= Budget ({configured_budget}B)")
    if artifact_bytes <= 0:
        return 0, 0, usable_payload, 0
    
    fragment_count = math.ceil(artifact_bytes / usable_payload)
    last_fragment_bytes = artifact_bytes - ((fragment_count - 1) * usable_payload)
    total_transmitted_bytes = (fragment_count * modeled_overhead) + artifact_bytes
    return fragment_count, last_fragment_bytes, usable_payload, total_transmitted_bytes

def analyze_fragmentation(artifact_summary_csv: Path, output_dir: Path, experiment_id: str):
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Standard artifacts to evaluate
    artifacts = [
        ("X25519", "Public Key (Raw)", 32, "Key Establishment"),
        ("X25519", "Public Key (SPKI DER)", 44, "Key Establishment"),
        ("X25519", "2-Way Handshake (2x PK)", 64, "Key Establishment Flow"),
        ("ML-KEM-768", "Public Key (Raw)", 1184, "Key Establishment"),
        ("ML-KEM-768", "Ciphertext (Raw)", 1088, "Key Establishment"),
        ("ML-KEM-768", "2-Way Handshake (PK + CT)", 2272, "Key Establishment Flow"),
        ("ECDSA-P256", "Public Key (Uncompressed X9.62)", 65, "Digital Signature"),
        ("ECDSA-P256", "Public Key (Compressed X9.62)", 33, "Digital Signature"),
        ("ECDSA-P256", "Signature (DER Mean)", 71, "Digital Signature"),
        ("ECDSA-P256", "Signature (IEEE P1363 Raw)", 64, "Digital Signature"),
        ("ECDSA-P256", "Signed Msg (128B payload + DER sig)", 199, "Signed Message"),
        ("ECDSA-P256", "Signed Msg (1024B payload + DER sig)", 1095, "Signed Message"),
        ("ML-DSA-65", "Public Key (Raw)", 1952, "Digital Signature"),
        ("ML-DSA-65", "Signature (Raw)", 3309, "Digital Signature"),
        ("ML-DSA-65", "Signed Msg (128B payload + sig)", 3437, "Signed Message"),
        ("ML-DSA-65", "Signed Msg (1024B payload + sig)", 4333, "Signed Message"),
        ("ML-DSA-65", "Self-Contained Msg (128B + PK + sig)", 5389, "Signed Message"),
    ]

    # Budgets and Scenarios
    # Ethernet MTU 1500B
    # 6LoWPAN / 802.15.4 128B frame
    network_profiles = [
        # (Profile Name, Network Tech, Budget, Overhead, Mode, Description)
        ("Ethernet_Raw", "Ethernet IP", 1500, 0, "Mode_A_Raw", "1500B IP MTU unadjusted raw payload planning"),
        ("Ethernet_IPv4_UDP", "Ethernet IP", 1500, 28, "Mode_B_HeaderAware", "1500B MTU minus IPv4 (20B) + UDP (8B) headers"),
        ("Ethernet_IPv6_UDP", "Ethernet IP", 1500, 48, "Mode_B_HeaderAware", "1500B MTU minus IPv6 (40B) + UDP (8B) headers"),
        ("Ethernet_IPv4_TCP", "Ethernet IP", 1500, 40, "Mode_B_HeaderAware", "1500B MTU minus IPv4 (20B) + TCP (20B) headers"),
        ("6LoWPAN_Raw", "6LoWPAN/802.15.4", 128, 0, "Mode_A_Raw", "128B IEEE 802.15.4 raw physical frame budget"),
        ("6LoWPAN_MAC_Basic", "6LoWPAN/802.15.4", 128, 25, "Mode_B_HeaderAware", "128B frame minus 802.15.4 MAC header + FCS (25B) -> 103B usable"),
        ("6LoWPAN_Mesh_Sec", "6LoWPAN/802.15.4", 128, 48, "Mode_B_HeaderAware", "128B frame minus MAC (25B), security MIC (14B), 6LoWPAN frag (9B) -> 80B usable"),
        ("6LoWPAN_Conservative", "6LoWPAN/802.15.4", 128, 64, "Mode_B_HeaderAware", "Conservative 64-byte payload per frame for constrained mesh"),
    ]

    records = []
    for alg, item_name, size_b, category in artifacts:
        for prof_name, net_tech, budget, overhead, mode, desc in network_profiles:
            frag_cnt, last_frag, usable_payload, total_tx = calculate_fragments(size_b, budget, overhead)
            expansion_factor = round(total_tx / size_b, 3) if size_b > 0 else 1.0
            is_fragmented = (frag_cnt > 1)
            
            records.append({
                "algorithm": alg,
                "item_name": item_name,
                "category": category,
                "artifact_size_bytes": size_b,
                "network_profile": prof_name,
                "network_technology": net_tech,
                "mode": mode,
                "configured_budget_bytes": budget,
                "modeled_overhead_bytes": overhead,
                "usable_payload_bytes": usable_payload,
                "fragment_count": frag_cnt,
                "last_fragment_bytes": last_frag,
                "total_transmitted_bytes": total_tx,
                "expansion_factor": expansion_factor,
                "is_fragmented": is_fragmented,
                "profile_description": desc
            })

    frag_df = pd.DataFrame(records)
    csv_path = output_dir / "fragmentation_analysis.csv"
    frag_df.to_csv(csv_path, index=False)
    print(f"[OK] Wrote {len(records)} fragmentation analysis records to {csv_path}")

    assumptions = {
        "experiment_id": experiment_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "notes": [
            "1500 bytes is a standard Ethernet IP MTU; total Ethernet frame size is 1518 bytes (excluding VLAN/preamble).",
            "128 bytes is the maximum Physical Layer Service Data Unit (PSDU) for IEEE 802.15.4-2006.",
            "6LoWPAN adaptation layer provides header compression (RFC 6282) and fragmentation (RFC 4944).",
            "Mode A evaluates mathematical division of raw artifact bytes against nominal link capacity.",
            "Mode B models header consumption at MAC, adaptation, and transport layers, reporting real fragment counts.",
            "Calculations are deterministic protocol models and do not represent physical radio sniff captures."
        ],
        "profiles": {p[0]: {"technology": p[1], "budget": p[2], "overhead": p[3], "description": p[5]} for p in network_profiles}
    }
    json_path = output_dir / "fragmentation_assumptions.json"
    json_path.write_text(json.dumps(assumptions, indent=2), encoding="utf-8")
    print(f"[OK] Wrote fragmentation assumptions to {json_path}")

    return frag_df

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage D1-C Fragmentation Analysis")
    parser.add_argument("--artifact-summary", type=str, default="stage_d1_output/artifact_summary.csv")
    parser.add_argument("--output-dir", type=str, default="stage_d1_output")
    parser.add_argument("--experiment-id", type=str, default="")
    args = parser.parse_args()

    exp_id = args.experiment_id or f"EXP_STAGE_D1_FRAG_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    analyze_fragmentation(Path(args.artifact_summary), Path(args.output_dir), exp_id)
