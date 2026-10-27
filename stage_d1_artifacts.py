#!/usr/bin/env python3
"""
Stage D1-A: Cryptographic Artifact Size Characterization
Empirical Migration Feasibility Analysis of Post-Quantum Cryptography for Resource-Constrained Systems

Measures the exact serialized byte representation of:
- X25519: Public Key (Raw 32B, SPKI DER 44B), Shared Secret (32B)
- ML-KEM-768: Public Key (Raw 1184B), Ciphertext (Raw 1088B), Shared Secret (32B)
- ECDSA P-256: Public Key (Uncompressed X9.62 65B, Compressed X9.62 33B, SPKI DER 91B),
               Signature (DER variable ~70-72B, IEEE P1363 Raw 64B)
- ML-DSA-65: Public Key (Raw 1952B), Signature (Raw 3309B)

Outputs:
- artifact_samples.csv
- artifact_summary.csv
- artifact_manifest.json
"""

import argparse
import csv
import json
import os
import platform
import ssl
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import oqs
import cryptography
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, x25519
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature, encode_dss_signature
from cryptography.exceptions import InvalidSignature

TEST_MESSAGE = b"PQC migration feasibility benchmark - Stage D1 artifact size characterization."

def measure_artifacts(sample_count: int, output_dir: Path, experiment_id: str):
    output_dir.mkdir(parents=True, exist_ok=True)
    samples = []
    
    print(f"=== Stage D1-A: Artifact Size Characterization ===")
    print(f"Experiment ID: {experiment_id}")
    print(f"Samples per artifact: {sample_count}")
    print(f"Target directory: {output_dir}")
    print("-" * 50)
    
    # 1. X25519 Artifacts
    print("[1/4] Measuring X25519 artifacts...")
    for s_idx in range(1, sample_count + 1):
        priv_a = x25519.X25519PrivateKey.generate()
        pub_a = priv_a.public_key()
        raw_pub = pub_a.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        spki_pub = pub_a.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        
        # Peer for shared secret derivation
        priv_b = x25519.X25519PrivateKey.generate()
        ss_a = priv_a.exchange(priv_b.public_key())
        ss_b = priv_b.exchange(pub_a)
        is_valid = (ss_a == ss_b and len(ss_a) == 32)
        
        now_ts = datetime.now(timezone.utc).isoformat()
        samples.append({
            "experiment_id": experiment_id,
            "sample_id": s_idx,
            "algorithm": "X25519",
            "category": "Key Agreement",
            "artifact_type": "public_key",
            "encoding": "Raw",
            "representation": "Curve25519 point (raw bytes)",
            "size_bytes": len(raw_pub),
            "valid": is_valid,
            "timestamp_utc": now_ts,
        })
        samples.append({
            "experiment_id": experiment_id,
            "sample_id": s_idx,
            "algorithm": "X25519",
            "category": "Key Agreement",
            "artifact_type": "public_key",
            "encoding": "DER_SPKI",
            "representation": "SubjectPublicKeyInfo DER",
            "size_bytes": len(spki_pub),
            "valid": is_valid,
            "timestamp_utc": now_ts,
        })
        samples.append({
            "experiment_id": experiment_id,
            "sample_id": s_idx,
            "algorithm": "X25519",
            "category": "Key Agreement",
            "artifact_type": "shared_secret",
            "encoding": "Raw",
            "representation": "Shared Secret (raw bytes)",
            "size_bytes": len(ss_a),
            "valid": is_valid,
            "timestamp_utc": now_ts,
        })

    # 2. ML-KEM-768 Artifacts
    print("[2/4] Measuring ML-KEM-768 artifacts...")
    with oqs.KeyEncapsulation("ML-KEM-768") as kem:
        for s_idx in range(1, sample_count + 1):
            pk = kem.generate_keypair()
            ct, ss_srv = kem.encap_secret(pk)
            ss_cli = kem.decap_secret(ct)
            is_valid = (ss_srv == ss_cli and len(ss_srv) == 32)
            
            now_ts = datetime.now(timezone.utc).isoformat()
            samples.append({
                "experiment_id": experiment_id,
                "sample_id": s_idx,
                "algorithm": "ML-KEM-768",
                "category": "KEM",
                "artifact_type": "public_key",
                "encoding": "Raw",
                "representation": "FIPS 203 encapsulation key (raw bytes)",
                "size_bytes": len(pk),
                "valid": is_valid,
                "timestamp_utc": now_ts,
            })
            samples.append({
                "experiment_id": experiment_id,
                "sample_id": s_idx,
                "algorithm": "ML-KEM-768",
                "category": "KEM",
                "artifact_type": "ciphertext",
                "encoding": "Raw",
                "representation": "FIPS 203 encapsulation ciphertext (raw bytes)",
                "size_bytes": len(ct),
                "valid": is_valid,
                "timestamp_utc": now_ts,
            })
            samples.append({
                "experiment_id": experiment_id,
                "sample_id": s_idx,
                "algorithm": "ML-KEM-768",
                "category": "KEM",
                "artifact_type": "shared_secret",
                "encoding": "Raw",
                "representation": "FIPS 203 shared secret (raw bytes)",
                "size_bytes": len(ss_srv),
                "valid": is_valid,
                "timestamp_utc": now_ts,
            })

    # 3. ECDSA P-256 Artifacts
    print("[3/4] Measuring ECDSA P-256 artifacts...")
    for s_idx in range(1, sample_count + 1):
        priv_ec = ec.generate_private_key(ec.SECP256R1())
        pub_ec = priv_ec.public_key()
        
        # Public key formats
        pk_uncompressed = pub_ec.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
        pk_compressed = pub_ec.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.CompressedPoint)
        pk_spki = pub_ec.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        
        # Signature: DER and IEEE P1363 (Raw r || s)
        sig_der = priv_ec.sign(TEST_MESSAGE, ec.ECDSA(hashes.SHA256()))
        r, s = decode_dss_signature(sig_der)
        sig_p1363 = r.to_bytes(32, "big") + s.to_bytes(32, "big")
        
        # Verification
        try:
            pub_ec.verify(sig_der, TEST_MESSAGE, ec.ECDSA(hashes.SHA256()))
            ver_ok = True
        except InvalidSignature:
            ver_ok = False
            
        now_ts = datetime.now(timezone.utc).isoformat()
        samples.append({
            "experiment_id": experiment_id,
            "sample_id": s_idx,
            "algorithm": "ECDSA-P256",
            "category": "Digital Signature",
            "artifact_type": "public_key",
            "encoding": "X962_Uncompressed",
            "representation": "ANSI X9.62 uncompressed point 0x04||X||Y",
            "size_bytes": len(pk_uncompressed),
            "valid": ver_ok,
            "timestamp_utc": now_ts,
        })
        samples.append({
            "experiment_id": experiment_id,
            "sample_id": s_idx,
            "algorithm": "ECDSA-P256",
            "category": "Digital Signature",
            "artifact_type": "public_key",
            "encoding": "X962_Compressed",
            "representation": "ANSI X9.62 compressed point 0x02/0x03||X",
            "size_bytes": len(pk_compressed),
            "valid": ver_ok,
            "timestamp_utc": now_ts,
        })
        samples.append({
            "experiment_id": experiment_id,
            "sample_id": s_idx,
            "algorithm": "ECDSA-P256",
            "category": "Digital Signature",
            "artifact_type": "public_key",
            "encoding": "DER_SPKI",
            "representation": "SubjectPublicKeyInfo DER",
            "size_bytes": len(pk_spki),
            "valid": ver_ok,
            "timestamp_utc": now_ts,
        })
        samples.append({
            "experiment_id": experiment_id,
            "sample_id": s_idx,
            "algorithm": "ECDSA-P256",
            "category": "Digital Signature",
            "artifact_type": "signature",
            "encoding": "DER",
            "representation": "ASN.1 DER sequence of (r, s)",
            "size_bytes": len(sig_der),
            "valid": ver_ok,
            "timestamp_utc": now_ts,
        })
        samples.append({
            "experiment_id": experiment_id,
            "sample_id": s_idx,
            "algorithm": "ECDSA-P256",
            "category": "Digital Signature",
            "artifact_type": "signature",
            "encoding": "IEEE_P1363",
            "representation": "Fixed-width raw r || s (32B + 32B)",
            "size_bytes": len(sig_p1363),
            "valid": ver_ok,
            "timestamp_utc": now_ts,
        })

    # 4. ML-DSA-65 Artifacts
    print("[4/4] Measuring ML-DSA-65 artifacts...")
    with oqs.Signature("ML-DSA-65") as signer:
        for s_idx in range(1, sample_count + 1):
            pk_dsa = signer.generate_keypair()
            sig_dsa = signer.sign(TEST_MESSAGE)
            ver_ok = signer.verify(TEST_MESSAGE, sig_dsa, pk_dsa)
            
            now_ts = datetime.now(timezone.utc).isoformat()
            samples.append({
                "experiment_id": experiment_id,
                "sample_id": s_idx,
                "algorithm": "ML-DSA-65",
                "category": "Digital Signature",
                "artifact_type": "public_key",
                "encoding": "Raw",
                "representation": "FIPS 204 verification key (raw bytes)",
                "size_bytes": len(pk_dsa),
                "valid": ver_ok,
                "timestamp_utc": now_ts,
            })
            samples.append({
                "experiment_id": experiment_id,
                "sample_id": s_idx,
                "algorithm": "ML-DSA-65",
                "category": "Digital Signature",
                "artifact_type": "signature",
                "encoding": "Raw",
                "representation": "FIPS 204 signature (raw bytes)",
                "size_bytes": len(sig_dsa),
                "valid": ver_ok,
                "timestamp_utc": now_ts,
            })

    # Save raw samples CSV
    samples_path = output_dir / "artifact_samples.csv"
    with samples_path.open("w", newline="", encoding="utf-8") as f:
        fieldnames = list(samples[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(samples)
    print(f"\n[OK] Wrote {len(samples)} raw measurement samples to {samples_path}")

    # Compute statistical summary
    import pandas as pd
    df = pd.DataFrame(samples)
    
    summary_rows = []
    for (alg, cat, art_type, enc, rep), g in df.groupby(["algorithm", "category", "artifact_type", "encoding", "representation"]):
        sizes = g["size_bytes"]
        is_fixed = (sizes.nunique() == 1)
        summary_rows.append({
            "algorithm": alg,
            "category": cat,
            "artifact_type": art_type,
            "encoding": enc,
            "representation": rep,
            "sample_count": len(sizes),
            "is_fixed_size": is_fixed,
            "min_bytes": int(sizes.min()),
            "max_bytes": int(sizes.max()),
            "mean_bytes": round(float(sizes.mean()), 3),
            "median_bytes": round(float(sizes.median()), 3),
            "std_bytes": round(float(sizes.std(ddof=1)), 3) if len(sizes) > 1 else 0.0,
            "p90_bytes": round(float(sizes.quantile(0.90)), 3),
            "p95_bytes": round(float(sizes.quantile(0.95)), 3),
            "p99_bytes": round(float(sizes.quantile(0.99)), 3),
            "all_valid": bool(g["valid"].all()),
        })
        
    summary_df = pd.DataFrame(summary_rows)
    summary_path = output_dir / "artifact_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    print(f"[OK] Wrote artifact summary to {summary_path}")

    # Generate Manifest
    manifest = {
        "experiment_id": experiment_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "sample_count": sample_count,
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "liboqs_version": oqs.oqs_version(),
        "cryptography_version": cryptography.__version__,
        "openssl_version": ssl.OPENSSL_VERSION,
        "total_samples_recorded": len(samples),
        "all_validations_passed": bool(df["valid"].all()),
        "summary": summary_rows,
    }
    manifest_path = output_dir / "artifact_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[OK] Wrote artifact manifest to {manifest_path}")

    return summary_df

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage D1-A Artifact Size Characterization")
    parser.add_argument("--samples", type=int, default=1000, help="Samples per artifact (default: 1000)")
    parser.add_argument("--output-dir", type=str, default="stage_d1_output", help="Output directory")
    parser.add_argument("--experiment-id", type=str, default="", help="Experiment ID")
    args = parser.parse_args()

    exp_id = args.experiment_id or f"EXP_STAGE_D1_ARTIFACTS_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    measure_artifacts(args.samples, Path(args.output_dir), exp_id)
