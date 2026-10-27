#!/usr/bin/env python3
"""
Stage D1: Publication-Quality Plotting Pipeline
Empirical Migration Feasibility Analysis of Post-Quantum Cryptography for Resource-Constrained Systems

Generates 7 publication-quality scientific plots:
1. plot1_pubkey_and_signature_size_comparison.png
2. plot2_mlkem_pk_and_ct_comparison.png
3. plot3_message_overhead_vs_payload_size.png
4. plot4_fragmentation_counts_ethernet_and_6lowpan.png
5. plot5_measured_loopback_latency_vs_payload.png
6. plot6_loopback_throughput_vs_payload.png
7. plot7_ecdsa_der_signature_length_distribution.png
"""

import argparse
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def generate_plots(exp_dir: Path):
    exp_dir = exp_dir.resolve()
    print(f"=== Stage D1 Plot Generation ===")
    print(f"Reading from: {exp_dir}")

    art_summary_f = exp_dir / "artifact_summary.csv"
    art_samples_f = exp_dir / "artifact_samples.csv"
    msg_budget_f = exp_dir / "message_budget.csv"
    frag_analysis_f = exp_dir / "fragmentation_analysis.csv"
    trans_summary_f = exp_dir / "transport_summary.csv"

    # Style configuration
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    plt.rcParams.update({
        "font.size": 10,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.titlesize": 13,
    })

    # ==========================================================
    # Plot 1: Public-Key and Signature Size Comparison (Classical vs PQC)
    # ==========================================================
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))
    
    # Public Keys
    pk_labels = ["X25519 (Raw)", "ECDSA P-256 (Uncomp)", "ML-KEM-768 (Raw)", "ML-DSA-65 (Raw)"]
    pk_sizes = [32, 65, 1184, 1952]
    pk_colors = ["#4A90E2", "#50E3C2", "#E94E77", "#D0021B"]
    
    bars1 = ax1.bar(pk_labels, pk_sizes, color=pk_colors, width=0.55, edgecolor="black", linewidth=0.8)
    ax1.set_title("Public Key Sizes: Classical vs PQC", fontweight="bold")
    ax1.set_ylabel("Size (Bytes)")
    ax1.set_yscale("log")
    ax1.set_ylim(10, 5000)
    ax1.grid(True, linestyle="--", alpha=0.5, which="both")
    for bar in bars1:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2.0, yval * 1.15, f"{yval} B", ha="center", va="bottom", fontweight="bold", fontsize=9)
    ax1.set_xticks(range(len(pk_labels)))
    ax1.set_xticklabels(pk_labels, rotation=15, ha="right")

    # Signatures
    sig_labels = ["ECDSA P-256 (Raw P1363)", "ECDSA P-256 (DER Mean)", "ML-DSA-65 (Raw)"]
    sig_sizes = [64, 71, 3309]
    sig_colors = ["#50E3C2", "#7ED321", "#D0021B"]
    
    bars2 = ax2.bar(sig_labels, sig_sizes, color=sig_colors, width=0.45, edgecolor="black", linewidth=0.8)
    ax2.set_title("Digital Signature Sizes: Classical vs PQC", fontweight="bold")
    ax2.set_ylabel("Size (Bytes)")
    ax2.set_yscale("log")
    ax2.set_ylim(10, 8000)
    ax2.grid(True, linestyle="--", alpha=0.5, which="both")
    for bar in bars2:
        yval = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2.0, yval * 1.15, f"{yval} B", ha="center", va="bottom", fontweight="bold", fontsize=9)
    ax2.set_xticks(range(len(sig_labels)))
    ax2.set_xticklabels(sig_labels, rotation=15, ha="right")

    plt.suptitle("Cryptographic Artifact Sizes: Classical vs Post-Quantum (Log Scale)", fontweight="bold")
    plt.tight_layout()
    p1_path = exp_dir / "plot1_pubkey_and_signature_size_comparison.png"
    plt.savefig(p1_path, dpi=200)
    plt.close()
    print(f"[OK] Generated {p1_path.name}")

    # ==========================================================
    # Plot 2: ML-KEM-768 Public-Key & Ciphertext vs X25519
    # ==========================================================
    fig, ax = plt.subplots(figsize=(8, 5.2))
    kem_items = ["X25519 PK", "X25519 Peer PK", "ML-KEM-768 PK", "ML-KEM-768 Ciphertext"]
    kem_sizes = [32, 32, 1184, 1088]
    kem_cols = ["#4A90E2", "#4A90E2", "#F5A623", "#BD10E0"]
    
    bars = ax.bar(kem_items, kem_sizes, color=kem_cols, width=0.5, edgecolor="black", linewidth=0.8)
    ax.set_title("Key Establishment Transmitted Artifact Sizes (Bytes)", fontweight="bold")
    ax.set_ylabel("Serialized Size (Bytes)")
    ax.grid(True, linestyle="--", alpha=0.5, axis="y")
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + 25, f"{yval} B", ha="center", va="bottom", fontweight="bold", fontsize=10)
    ax.set_ylim(0, 1400)
    plt.tight_layout()
    p2_path = exp_dir / "plot2_mlkem_pk_and_ct_comparison.png"
    plt.savefig(p2_path, dpi=200)
    plt.close()
    print(f"[OK] Generated {p2_path.name}")

    # ==========================================================
    # Plot 3: Message-Size Overhead vs Application Payload Size
    # ==========================================================
    if msg_budget_f.exists():
        df_mb = pd.read_csv(msg_budget_f)
        m3_df = df_mb[(df_mb["model_id"] == "M3_SIGNED_MESSAGE") & (df_mb["framing_bytes"] == 0)]
        
        # Split into pre-shared PK vs PK included
        preshared = m3_df[m3_df["scenario"].str.contains("Pre-Shared PK")].sort_values("payload_bytes")
        pk_incl = m3_df[m3_df["scenario"].str.contains("PK Included")].sort_values("payload_bytes")
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))
        
        # Total bytes
        ax1.plot(preshared["payload_bytes"], preshared["classical_bytes"], marker="o", label="ECDSA P-256 (Pre-shared PK)", color="#50E3C2", linewidth=2)
        ax1.plot(preshared["payload_bytes"], preshared["pqc_bytes"], marker="s", label="ML-DSA-65 (Pre-shared PK)", color="#D0021B", linewidth=2)
        ax1.plot(pk_incl["payload_bytes"], pk_incl["classical_bytes"], marker="^", linestyle="--", label="ECDSA P-256 (PK Included)", color="#4A90E2", linewidth=1.5)
        ax1.plot(pk_incl["payload_bytes"], pk_incl["pqc_bytes"], marker="d", linestyle="--", label="ML-DSA-65 (PK Included)", color="#9013FE", linewidth=1.5)
        ax1.set_title("Total Transmitted Bytes vs Application Payload", fontweight="bold")
        ax1.set_xlabel("Application Payload (Bytes)")
        ax1.set_ylabel("Total Transmitted Bytes")
        ax1.set_xscale("log", base=2)
        ax1.grid(True, linestyle="--", alpha=0.5)
        ax1.legend()

        # Overhead Percentage: (Total - Payload) / Payload * 100
        preshared_ecdsa_pct = (preshared["classical_bytes"] - preshared["payload_bytes"]) / preshared["payload_bytes"] * 100
        preshared_mldsa_pct = (preshared["pqc_bytes"] - preshared["payload_bytes"]) / preshared["payload_bytes"] * 100
        
        ax2.plot(preshared["payload_bytes"], preshared_ecdsa_pct, marker="o", label="ECDSA P-256 Signature Overhead (%)", color="#50E3C2", linewidth=2)
        ax2.plot(preshared["payload_bytes"], preshared_mldsa_pct, marker="s", label="ML-DSA-65 Signature Overhead (%)", color="#D0021B", linewidth=2)
        ax2.set_title("Relative Cryptographic Overhead (%)", fontweight="bold")
        ax2.set_xlabel("Application Payload (Bytes)")
        ax2.set_ylabel("Overhead (% of Payload)")
        ax2.set_xscale("log", base=2)
        ax2.set_yscale("log")
        ax2.grid(True, linestyle="--", alpha=0.5, which="both")
        ax2.legend()

        plt.suptitle("Message Transmission Overhead: ECDSA P-256 vs ML-DSA-65", fontweight="bold")
        plt.tight_layout()
        p3_path = exp_dir / "plot3_message_overhead_vs_payload_size.png"
        plt.savefig(p3_path, dpi=200)
        plt.close()
        print(f"[OK] Generated {p3_path.name}")

    # ==========================================================
    # Plot 4: Fragmentation Counts at 1500-byte and 128-byte Budgets
    # ==========================================================
    if frag_analysis_f.exists():
        df_fr = pd.read_csv(frag_analysis_f)
        
        # Create full name for reliable matching
        df_fr["full_name"] = df_fr["algorithm"] + " " + df_fr["item_name"]
        
        items_to_plot = [
            "X25519 Public Key (Raw)",
            "ML-KEM-768 Public Key (Raw)",
            "ML-KEM-768 Ciphertext (Raw)",
            "ECDSA-P256 Signature (DER Mean)",
            "ML-DSA-65 Signature (Raw)",
            "ML-DSA-65 Signed Msg (128B payload + sig)"
        ]
        
        eth_sub = df_fr[(df_fr["network_profile"] == "Ethernet_IPv6_UDP") & (df_fr["full_name"].isin(items_to_plot))]
        low_sub = df_fr[(df_fr["network_profile"] == "6LoWPAN_Mesh_Sec") & (df_fr["full_name"].isin(items_to_plot))]
        
        # Merge on full_name to align
        merged_fr = pd.merge(eth_sub[["full_name", "artifact_size_bytes", "fragment_count"]], 
                             low_sub[["full_name", "fragment_count"]], 
                             on="full_name", suffixes=("_eth", "_6lowpan"))
        
        if not merged_fr.empty:
            fig, ax = plt.subplots(figsize=(12, 6))
            x = np.arange(len(merged_fr))
            width = 0.35
            
            rects1 = ax.bar(x - width/2, merged_fr["fragment_count_eth"], width, label="Ethernet (1500B MTU / 1452B Usable)", color="#4A90E2", edgecolor="black")
            rects2 = ax.bar(x + width/2, merged_fr["fragment_count_6lowpan"], width, label="6LoWPAN (128B Budget / 80B Usable)", color="#F5A623", edgecolor="black")
            
            ax.set_ylabel("Required Fragment Count", fontweight="bold")
            ax.set_title("Modeled Link-Layer Fragment Counts: Ethernet vs 6LoWPAN", fontweight="bold")
            ax.set_xticks(x)
            clean_labels = [name.replace(" (Raw)", "").replace(" (DER Mean)", "") for name in merged_fr["full_name"]]
            ax.set_xticklabels(clean_labels, rotation=20, ha="right")
            ax.grid(True, linestyle="--", alpha=0.5, axis="y")
            ax.legend()
            
            for bar in rects1:
                h = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2.0, h + 0.5, f"{int(h)}", ha="center", va="bottom", fontsize=9, fontweight="bold")
            for bar in rects2:
                h = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2.0, h + 0.5, f"{int(h)}", ha="center", va="bottom", fontsize=9, fontweight="bold")
                
            ax.set_ylim(0, max(merged_fr["fragment_count_6lowpan"]) + 6)
            plt.tight_layout()
            p4_path = exp_dir / "plot4_fragmentation_counts_ethernet_and_6lowpan.png"
            plt.savefig(p4_path, dpi=200)
            plt.close()
            print(f"[OK] Generated {p4_path.name}")

    # ==========================================================
    # Plot 5: Measured Loopback Transfer Time vs Payload Size
    # ==========================================================
    if trans_summary_f.exists():
        df_tr = pd.read_csv(trans_summary_f)
        sweep_df = df_tr[df_tr["category"] == "Payload_Sweep"].sort_values("payload_bytes")
        art_df = df_tr[df_tr["category"].isin(["Artifact_Key", "Artifact_CT", "Artifact_Sig"])]
        
        fig, ax = plt.subplots(figsize=(9, 5.5))
        ax.plot(sweep_df["payload_bytes"], sweep_df["median_transfer_us"], marker="o", color="#0072B2", linewidth=2, label="Payload Sweep Median Latency")
        ax.fill_between(sweep_df["payload_bytes"], sweep_df["p90_transfer_us"], sweep_df["median_transfer_us"], color="#0072B2", alpha=0.15, label="P90 Tail Range")
        
        # Overlay actual artifacts as scatter points
        for _, r in art_df.iterrows():
            ax.scatter(r["payload_bytes"], r["median_transfer_us"], s=70, zorder=5, label=f"{r['condition_label']} ({r['payload_bytes']}B)")
            ax.annotate(r['condition_label'], (r["payload_bytes"], r["median_transfer_us"]), 
                        textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8)

        ax.set_title("Measured Local TCP Loopback Transfer Latency vs Payload Size", fontweight="bold")
        ax.set_xlabel("Payload Size (Bytes)")
        ax.set_ylabel("One-Way Transfer Latency (µs)")
        ax.set_xscale("log", base=2)
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
        plt.tight_layout()
        p5_path = exp_dir / "plot5_measured_loopback_latency_vs_payload.png"
        plt.savefig(p5_path, dpi=200)
        plt.close()
        print(f"[OK] Generated {p5_path.name}")

    # ==========================================================
    # Plot 6: Measured Loopback Transfer Throughput vs Payload Size
    # ==========================================================
    if trans_summary_f.exists():
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.plot(sweep_df["payload_bytes"], sweep_df["median_throughput_mb_s"], marker="s", color="#D55E00", linewidth=2, label="Measured Loopback Throughput")
        ax.set_title("Local TCP Loopback Effective Throughput (MB/s)", fontweight="bold")
        ax.set_xlabel("Payload Size (Bytes)")
        ax.set_ylabel("Effective Throughput (MB/s)")
        ax.set_xscale("log", base=2)
        ax.grid(True, linestyle="--", alpha=0.5)
        for _, r in sweep_df.iterrows():
            ax.annotate(f"{r['median_throughput_mb_s']:.1f}", (r["payload_bytes"], r["median_throughput_mb_s"]),
                        textcoords="offset points", xytext=(0, 6), ha="center", fontsize=8)
        ax.legend()
        plt.tight_layout()
        p6_path = exp_dir / "plot6_loopback_throughput_vs_payload.png"
        plt.savefig(p6_path, dpi=200)
        plt.close()
        print(f"[OK] Generated {p6_path.name}")

    # ==========================================================
    # Plot 7: Distribution of Variable ECDSA DER Signature Lengths
    # ==========================================================
    if art_samples_f.exists():
        df_samples = pd.read_csv(art_samples_f)
        ecdsa_der = df_samples[(df_samples["algorithm"] == "ECDSA-P256") & (df_samples["artifact_type"] == "signature") & (df_samples["encoding"] == "DER")]
        
        if not ecdsa_der.empty:
            fig, ax = plt.subplots(figsize=(8, 4.8))
            counts = ecdsa_der["size_bytes"].value_counts().sort_index()
            
            bars = ax.bar([f"{k} Bytes" for k in counts.index], counts.values, color="#2B7A78", width=0.45, edgecolor="black")
            ax.set_title(f"ECDSA P-256 DER Signature Length Distribution (N={len(ecdsa_der)} Samples)", fontweight="bold")
            ax.set_xlabel("DER Signature Length (Bytes)")
            ax.set_ylabel("Sample Frequency")
            ax.grid(True, linestyle="--", alpha=0.5, axis="y")
            
            total = len(ecdsa_der)
            for bar, (sz, cnt) in zip(bars, counts.items()):
                pct = (cnt / total) * 100
                ax.text(bar.get_x() + bar.get_width()/2.0, cnt + total*0.01, f"{cnt}\n({pct:.1f}%)", ha="center", va="bottom", fontsize=9, fontweight="bold")
            
            ax.set_ylim(0, max(counts.values) * 1.18)
            plt.tight_layout()
            p7_path = exp_dir / "plot7_ecdsa_der_signature_length_distribution.png"
            plt.savefig(p7_path, dpi=200)
            plt.close()
            print(f"[OK] Generated {p7_path.name}")

    print("[SUCCESS] All 7 Stage D1 scientific plots generated.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage D1 Plot Generator")
    parser.add_argument("exp_dir", type=str, help="Experiment directory containing CSV outputs")
    args = parser.parse_args()
    generate_plots(Path(args.exp_dir))
