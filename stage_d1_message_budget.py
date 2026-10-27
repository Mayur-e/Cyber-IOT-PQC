#!/usr/bin/env python3
"""
Stage D1-B: Message-Flow and Transmission Budget Evaluation
Empirical Migration Feasibility Analysis of Post-Quantum Cryptography for Resource-Constrained Systems

Models transmission byte totals under explicitly documented protocol scenarios:
- Model 1: Direct Cryptographic Artifact Comparison
- Model 2: Key-Establishment Exchange (Scenario K1: pre-shared recipient PK, Scenario K2: full 2-way handshake)
- Model 3: Signed Message Transmission across variable application payloads [16B to 4096B]

Outputs:
- message_budget.csv
- message_budget_assumptions.json
"""

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

def compute_message_budgets(artifact_summary_csv: Path, output_dir: Path, experiment_id: str):
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load measured artifact sizes if summary exists, else fallback to standard lengths
    measured_sizes = {
        "x25519_pk_raw": 32,
        "x25519_pk_spki": 44,
        "x25519_ss": 32,
        "mlkem_pk": 1184,
        "mlkem_ct": 1088,
        "mlkem_ss": 32,
        "ecdsa_pk_uncompressed": 65,
        "ecdsa_pk_compressed": 33,
        "ecdsa_pk_spki": 91,
        "ecdsa_sig_der_mean": 71.0,
        "ecdsa_sig_p1363": 64,
        "mldsa_pk": 1952,
        "mldsa_sig": 3309,
    }
    
    if artifact_summary_csv.exists():
        df_art = pd.read_csv(artifact_summary_csv)
        for _, row in df_art.iterrows():
            alg = row["algorithm"]
            art = row["artifact_type"]
            enc = row["encoding"]
            mean_b = row["mean_bytes"]
            if alg == "X25519" and art == "public_key" and enc == "Raw":
                measured_sizes["x25519_pk_raw"] = int(mean_b)
            elif alg == "X25519" and art == "public_key" and enc == "DER_SPKI":
                measured_sizes["x25519_pk_spki"] = int(mean_b)
            elif alg == "ML-KEM-768" and art == "public_key":
                measured_sizes["mlkem_pk"] = int(mean_b)
            elif alg == "ML-KEM-768" and art == "ciphertext":
                measured_sizes["mlkem_ct"] = int(mean_b)
            elif alg == "ECDSA-P256" and art == "public_key" and enc == "X962_Uncompressed":
                measured_sizes["ecdsa_pk_uncompressed"] = int(mean_b)
            elif alg == "ECDSA-P256" and art == "public_key" and enc == "X962_Compressed":
                measured_sizes["ecdsa_pk_compressed"] = int(mean_b)
            elif alg == "ECDSA-P256" and art == "signature" and enc == "DER":
                measured_sizes["ecdsa_sig_der_mean"] = float(mean_b)
            elif alg == "ECDSA-P256" and art == "signature" and enc == "IEEE_P1363":
                measured_sizes["ecdsa_sig_p1363"] = int(mean_b)
            elif alg == "ML-DSA-65" and art == "public_key":
                measured_sizes["mldsa_pk"] = int(mean_b)
            elif alg == "ML-DSA-65" and art == "signature":
                measured_sizes["mldsa_sig"] = int(mean_b)

    records = []

    # ==========================================================
    # Model 1: Artifact-Only Comparisons
    # ==========================================================
    # 1.1 Public Key (Key Establishment)
    records.append({
        "model_id": "M1_ARTIFACT_ONLY",
        "scenario": "Public Key Comparison",
        "category": "Key Establishment",
        "classical_description": "X25519 Public Key (Raw)",
        "classical_bytes": measured_sizes["x25519_pk_raw"],
        "pqc_description": "ML-KEM-768 Public Key (Raw)",
        "pqc_bytes": measured_sizes["mlkem_pk"],
        "expansion_ratio": round(measured_sizes["mlkem_pk"] / measured_sizes["x25519_pk_raw"], 2),
        "payload_bytes": 0,
        "framing_bytes": 0,
        "notes": "Direct artifact size comparison. ML-KEM PK contains matrix A seed and polynomial vector t."
    })
    
    # 1.2 Ciphertext vs Transmitted Artifact (Key Establishment)
    records.append({
        "model_id": "M1_ARTIFACT_ONLY",
        "scenario": "Key Establishment Response Artifact",
        "category": "Key Establishment",
        "classical_description": "X25519 Peer Public Key (Raw)",
        "classical_bytes": measured_sizes["x25519_pk_raw"],
        "pqc_description": "ML-KEM-768 Encapsulation Ciphertext (Raw)",
        "pqc_bytes": measured_sizes["mlkem_ct"],
        "expansion_ratio": round(measured_sizes["mlkem_ct"] / measured_sizes["x25519_pk_raw"], 2),
        "payload_bytes": 0,
        "framing_bytes": 0,
        "notes": "X25519 transmits peer public key; ML-KEM transmits encapsulation ciphertext (vector u + scalar v)."
    })

    # 1.3 Signature Comparison (DER)
    records.append({
        "model_id": "M1_ARTIFACT_ONLY",
        "scenario": "Digital Signature Comparison (DER)",
        "category": "Digital Signature",
        "classical_description": "ECDSA P-256 Signature (DER)",
        "classical_bytes": round(measured_sizes["ecdsa_sig_der_mean"], 1),
        "pqc_description": "ML-DSA-65 Signature (Raw)",
        "pqc_bytes": measured_sizes["mldsa_sig"],
        "expansion_ratio": round(measured_sizes["mldsa_sig"] / measured_sizes["ecdsa_sig_der_mean"], 2),
        "payload_bytes": 0,
        "framing_bytes": 0,
        "notes": "ECDSA DER signature length varies (70-72B); ML-DSA-65 signature is fixed at 3309B."
    })

    # 1.4 Signature Comparison (Raw IEEE P1363)
    records.append({
        "model_id": "M1_ARTIFACT_ONLY",
        "scenario": "Digital Signature Comparison (IEEE P1363)",
        "category": "Digital Signature",
        "classical_description": "ECDSA P-256 Signature (IEEE P1363 Raw r||s)",
        "classical_bytes": measured_sizes["ecdsa_sig_p1363"],
        "pqc_description": "ML-DSA-65 Signature (Raw)",
        "pqc_bytes": measured_sizes["mldsa_sig"],
        "expansion_ratio": round(measured_sizes["mldsa_sig"] / measured_sizes["ecdsa_sig_p1363"], 2),
        "payload_bytes": 0,
        "framing_bytes": 0,
        "notes": "Fixed-width 64-byte raw representation for ECDSA vs fixed 3309-byte ML-DSA-65."
    })

    # 1.5 Verification Public Key Comparison
    records.append({
        "model_id": "M1_ARTIFACT_ONLY",
        "scenario": "Signature Verification Key Comparison",
        "category": "Digital Signature",
        "classical_description": "ECDSA P-256 Public Key (Uncompressed X9.62)",
        "classical_bytes": measured_sizes["ecdsa_pk_uncompressed"],
        "pqc_description": "ML-DSA-65 Public Key (Raw)",
        "pqc_bytes": measured_sizes["mldsa_pk"],
        "expansion_ratio": round(measured_sizes["mldsa_pk"] / measured_sizes["ecdsa_pk_uncompressed"], 2),
        "payload_bytes": 0,
        "framing_bytes": 0,
        "notes": "65 bytes uncompressed EC point vs 1952 bytes ML-DSA verification key (rho + t1)."
    })

    # ==========================================================
    # Model 2: Key-Establishment Message Exchanges
    # ==========================================================
    # Scenario K1: Recipient PK already known/cached by initiator
    # Classical: Initiator sends X25519 PK (32B). Peer computes shared secret. Total = 32B.
    # PQC: Initiator encapsulates against recipient PK, sends Ciphertext (1088B). Recipient decapsulates. Total = 1088B.
    # Note: Recipient PK distribution is assumed pre-provisioned (32B vs 1184B).
    records.append({
        "model_id": "M2_KEY_EXCHANGE",
        "scenario": "Scenario K1: Pre-shared Recipient Public Key",
        "category": "Key Establishment",
        "classical_description": "Initiator sends ephemeral X25519 PK",
        "classical_bytes": measured_sizes["x25519_pk_raw"],
        "pqc_description": "Initiator sends ML-KEM-768 Ciphertext",
        "pqc_bytes": measured_sizes["mlkem_ct"],
        "expansion_ratio": round(measured_sizes["mlkem_ct"] / measured_sizes["x25519_pk_raw"], 2),
        "payload_bytes": 0,
        "framing_bytes": 0,
        "notes": "One-way key transmission when recipient public key is pre-authenticated or pre-shared."
    })

    # Scenario K2: Public-Key Delivery Included (Interactive 2-Way Handshake)
    # Classical: Party A sends X25519 PK (32B) -> Party B sends X25519 PK (32B). Total = 64B.
    # PQC: Party A sends ML-KEM PK (1184B) -> Party B sends ML-KEM CT (1088B). Total = 2272B.
    records.append({
        "model_id": "M2_KEY_EXCHANGE",
        "scenario": "Scenario K2: 2-Way Handshake (PK + Reply)",
        "category": "Key Establishment",
        "classical_description": "X25519 PK (32B) + X25519 PK (32B)",
        "classical_bytes": measured_sizes["x25519_pk_raw"] * 2,
        "pqc_description": "ML-KEM-768 PK (1184B) + ML-KEM-768 CT (1088B)",
        "pqc_bytes": measured_sizes["mlkem_pk"] + measured_sizes["mlkem_ct"],
        "expansion_ratio": round((measured_sizes["mlkem_pk"] + measured_sizes["mlkem_ct"]) / (measured_sizes["x25519_pk_raw"] * 2), 2),
        "payload_bytes": 0,
        "framing_bytes": 0,
        "notes": "Full ephemeral-ephemeral two-way handshake. Excludes protocol/TLS framing and certificate overhead."
    })

    # ==========================================================
    # Model 3: Signed Message Transmission Overhead
    # ==========================================================
    payload_sizes = [16, 32, 64, 128, 256, 512, 1024, 4096]
    framing_configs = [
        ("Raw", 0, "No framing header"),
        ("Prefix4B", 4, "4-byte length prefix"),
        ("Header8B", 8, "8-byte application protocol header (type, flags, length)")
    ]

    for p_size in payload_sizes:
        for f_name, f_bytes, f_desc in framing_configs:
            # 3A: Pre-shared / Cached Public Key (Message = Payload + Signature + Framing)
            ecdsa_der_total = p_size + measured_sizes["ecdsa_sig_der_mean"] + f_bytes
            mldsa_total = p_size + measured_sizes["mldsa_sig"] + f_bytes
            records.append({
                "model_id": "M3_SIGNED_MESSAGE",
                "scenario": f"Signed Message (Pre-Shared PK, Framing: {f_name})",
                "category": "Digital Signature",
                "classical_description": f"Payload ({p_size}B) + ECDSA-DER (~{measured_sizes['ecdsa_sig_der_mean']:.0f}B) + Framing ({f_bytes}B)",
                "classical_bytes": round(ecdsa_der_total, 1),
                "pqc_description": f"Payload ({p_size}B) + ML-DSA-65 ({measured_sizes['mldsa_sig']}B) + Framing ({f_bytes}B)",
                "pqc_bytes": round(mldsa_total, 1),
                "expansion_ratio": round(mldsa_total / ecdsa_der_total, 2),
                "payload_bytes": p_size,
                "framing_bytes": f_bytes,
                "notes": f"Public key is cached at verifier. Overhead: ECDSA={((ecdsa_der_total-p_size)/p_size*100):.1f}%, ML-DSA={((mldsa_total-p_size)/p_size*100):.1f}%."
            })

            # 3B: Self-Contained Signed Message (Public Key Included in Message)
            # Classical: Payload + ECDSA Uncompressed PK (65B) + ECDSA DER Sig (~71B) + Framing
            # PQC: Payload + ML-DSA PK (1952B) + ML-DSA Sig (3309B) + Framing
            ecdsa_pk_sig_total = p_size + measured_sizes["ecdsa_pk_uncompressed"] + measured_sizes["ecdsa_sig_der_mean"] + f_bytes
            mldsa_pk_sig_total = p_size + measured_sizes["mldsa_pk"] + measured_sizes["mldsa_sig"] + f_bytes
            records.append({
                "model_id": "M3_SIGNED_MESSAGE",
                "scenario": f"Self-Contained Signed Message (PK Included, Framing: {f_name})",
                "category": "Digital Signature",
                "classical_description": f"Payload ({p_size}B) + ECDSA PK (65B) + Sig (~{measured_sizes['ecdsa_sig_der_mean']:.0f}B) + Framing ({f_bytes}B)",
                "classical_bytes": round(ecdsa_pk_sig_total, 1),
                "pqc_description": f"Payload ({p_size}B) + ML-DSA PK ({measured_sizes['mldsa_pk']}B) + Sig ({measured_sizes['mldsa_sig']}B) + Framing ({f_bytes}B)",
                "pqc_bytes": round(mldsa_pk_sig_total, 1),
                "expansion_ratio": round(mldsa_pk_sig_total / ecdsa_pk_sig_total, 2),
                "payload_bytes": p_size,
                "framing_bytes": f_bytes,
                "notes": f"Public key transmitted with signature. Overhead: ECDSA={((ecdsa_pk_sig_total-p_size)/p_size*100):.1f}%, ML-DSA={((mldsa_pk_sig_total-p_size)/p_size*100):.1f}%."
            })

    budget_df = pd.DataFrame(records)
    budget_csv = output_dir / "message_budget.csv"
    budget_df.to_csv(budget_csv, index=False)
    print(f"[OK] Wrote {len(records)} message budget records to {budget_csv}")

    # Write Assumptions Document
    assumptions = {
        "experiment_id": experiment_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "measured_sizes_used": measured_sizes,
        "models": {
            "M1_ARTIFACT_ONLY": "Direct comparison of cryptographic serialized outputs without framing or protocol headers.",
            "M2_KEY_EXCHANGE": {
                "Scenario_K1": "Initiator already possesses recipient's verified public key. Initiator transmits ephemeral key/ciphertext.",
                "Scenario_K2": "Full two-way ephemeral key exchange. Excludes certificate chain and TLS record headers."
            },
            "M3_SIGNED_MESSAGE": {
                "Option_A": "Public key cached at receiver (only payload, signature, and optional framing transmitted).",
                "Option_B": "Public key transmitted alongside signature (self-contained signed object, e.g. JWT or detached signature envelope).",
                "Framing_Variants": ["Raw (0B)", "Length-prefix (4B)", "Header (8B)"]
            }
        },
        "critical_distinctions": [
            "X25519 produces a 32-byte public key; ML-KEM-768 produces a 1184-byte public key and 1088-byte ciphertext.",
            "X25519 shared secret is computed mutually via scalar multiplication, not transmitted as ciphertext.",
            "ECDSA DER signature length is mathematically variable (69-73 bytes); ML-DSA-65 signature is strictly fixed (3309 bytes).",
            "Models represent application-layer serialization and do not substitute for full TLS/TCP/IP packetization."
        ]
    }
    assumptions_json = output_dir / "message_budget_assumptions.json"
    assumptions_json.write_text(json.dumps(assumptions, indent=2), encoding="utf-8")
    print(f"[OK] Wrote message budget assumptions to {assumptions_json}")

    return budget_df

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage D1-B Message Budget Modeling")
    parser.add_argument("--artifact-summary", type=str, default="stage_d1_output/artifact_summary.csv")
    parser.add_argument("--output-dir", type=str, default="stage_d1_output")
    parser.add_argument("--experiment-id", type=str, default="")
    args = parser.parse_args()

    exp_id = args.experiment_id or f"EXP_STAGE_D1_BUDGET_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    compute_message_budgets(Path(args.artifact_summary), Path(args.output_dir), exp_id)
