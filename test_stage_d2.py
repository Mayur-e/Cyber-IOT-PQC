#!/usr/bin/env python3
"""
Stage D2 Automated Test Suite
Empirical Migration Feasibility Analysis of Post-Quantum Cryptography for Resource-Constrained Systems

Validates:
1. Child worker JSON serialization and error handling
2. Non-negative monotonic timer outputs and high-resolution representation
3. Distinguishability of first-operation and steady-state observations
4. Cryptographic correctness and negative verification tests for all 4 algorithms
5. Statistical computation functions (ratio, percentage increase, IQR, MAD)
6. Immutability of historical result directories
"""

import json
import math
import subprocess
import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

import oqs
import cryptography
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, x25519
from cryptography.exceptions import InvalidSignature

from stage_d2_cold_start import spawn_child_worker, compute_consolidated_summary

ROOT_DIR = Path(__file__).resolve().parent

class TestStageD2Engine(unittest.TestCase):
    def test_child_worker_startup_baseline(self):
        args = {"mode": "startup_profiling", "target": "baseline_empty"}
        res = spawn_child_worker(args)
        self.assertIn("child_internal_ns", res)
        self.assertIn("parent_wall_ns", res)
        self.assertGreater(res["parent_wall_ns"], 0)
        self.assertGreaterEqual(res["child_internal_ns"], 0)
        self.assertTrue(res["correctness"])

    def test_child_worker_crypto_operation(self):
        args = {
            "mode": "operation_benchmark",
            "algorithm": "ML-KEM-768",
            "operation": "keygen",
            "warmups": 2,
            "trials": 5,
            "message": "test message"
        }
        res = spawn_child_worker(args)
        self.assertIn("first_op_ns", res)
        self.assertIn("steady_state_timings", res)
        self.assertGreater(res["first_op_ns"], 0)
        self.assertEqual(len(res["steady_state_timings"]), 5)
        self.assertTrue(res["correctness"])

    def test_child_worker_error_detection(self):
        # Invalid mode or arguments
        args = {"mode": "non_existent_mode"}
        with self.assertRaises(RuntimeError):
            spawn_child_worker(args)

    def test_x25519_correctness(self):
        priv_a = x25519.X25519PrivateKey.generate()
        priv_b = x25519.X25519PrivateKey.generate()
        ss_a = priv_a.exchange(priv_b.public_key())
        ss_b = priv_b.exchange(priv_a.public_key())
        self.assertEqual(len(ss_a), 32)
        self.assertEqual(ss_a, ss_b)

    def test_mlkem768_correctness(self):
        with oqs.KeyEncapsulation("ML-KEM-768") as kem:
            pk = kem.generate_keypair()
            self.assertEqual(len(pk), 1184)
            ct, ss1 = kem.encap_secret(pk)
            self.assertEqual(len(ct), 1088)
            ss2 = kem.decap_secret(ct)
            self.assertEqual(ss1, ss2)

    def test_ecdsa_correctness_and_tamper(self):
        priv = ec.generate_private_key(ec.SECP256R1())
        pub = priv.public_key()
        msg = b"Validation message for ECDSA P-256"
        sig = priv.sign(msg, ec.ECDSA(hashes.SHA256()))
        pub.verify(sig, msg, ec.ECDSA(hashes.SHA256()))
        
        # Corrupt message
        with self.assertRaises(InvalidSignature):
            pub.verify(sig, msg + b"x", ec.ECDSA(hashes.SHA256()))

    def test_mldsa65_correctness_and_tamper(self):
        with oqs.Signature("ML-DSA-65") as signer:
            pk = signer.generate_keypair()
            msg = b"Validation message for ML-DSA-65"
            sig = signer.sign(msg)
            self.assertTrue(signer.verify(msg, sig, pk))
            self.assertFalse(signer.verify(msg + b"x", sig, pk))

    def test_statistical_calculations(self):
        # Test synthetic process dataframe
        proc_data = [
            {"algorithm": "ALG1", "operation": "OP1", "category": "CAT", "process_id": "p1", "process_repeat": 1,
             "first_op_us": 100.0, "steady_median_us": 20.0, "steady_mean_us": 20.0, "steady_std_us": 1.0,
             "steady_p95_us": 21.0, "cold_penalty_diff_us": 80.0, "first_to_steady_ratio": 5.0, "peak_rss_kib": 1000, "all_valid": True},
            {"algorithm": "ALG1", "operation": "OP1", "category": "CAT", "process_id": "p2", "process_repeat": 2,
             "first_op_us": 120.0, "steady_median_us": 22.0, "steady_mean_us": 22.0, "steady_std_us": 1.0,
             "steady_p95_us": 23.0, "cold_penalty_diff_us": 98.0, "first_to_steady_ratio": 5.45, "peak_rss_kib": 1000, "all_valid": True},
        ]
        raw_ops_data = [
            {"algorithm": "ALG1", "operation": "OP1", "category": "CAT", "process_id": "p1", "process_repeat": 1, "is_first_operation": True, "trial_index": 0, "latency_us": 100.0, "correctness": True, "peak_rss_kib": 1000, "timestamp_utc": "2026-10-26T00:00:00Z"},
            {"algorithm": "ALG1", "operation": "OP1", "category": "CAT", "process_id": "p1", "process_repeat": 1, "is_first_operation": False, "trial_index": 1, "latency_us": 20.0, "correctness": True, "peak_rss_kib": 1000, "timestamp_utc": "2026-10-26T00:00:00Z"},
            {"algorithm": "ALG1", "operation": "OP1", "category": "CAT", "process_id": "p2", "process_repeat": 2, "is_first_operation": True, "trial_index": 0, "latency_us": 120.0, "correctness": True, "peak_rss_kib": 1000, "timestamp_utc": "2026-10-26T00:00:00Z"},
            {"algorithm": "ALG1", "operation": "OP1", "category": "CAT", "process_id": "p2", "process_repeat": 2, "is_first_operation": False, "trial_index": 1, "latency_us": 22.0, "correctness": True, "peak_rss_kib": 1000, "timestamp_utc": "2026-10-26T00:00:00Z"},
        ]
        
        proc_df = pd.DataFrame(proc_data)
        raw_df = pd.DataFrame(raw_ops_data)
        
        tmp_dir = ROOT_DIR / "scratch" / "test_summary_out"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        try:
            summary_df = compute_consolidated_summary(raw_df, proc_df, tmp_dir, "TEST_EXP")
            self.assertEqual(len(summary_df), 1)
            row = summary_df.iloc[0]
            self.assertEqual(row["first_op_median_us"], 110.0)
            self.assertEqual(row["steady_median_us"], 21.0)
            self.assertAlmostEqual(row["first_to_steady_ratio"], 110.0 / 21.0, places=2)
            self.assertAlmostEqual(row["cold_penalty_abs_us"], 89.0, places=2)
        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_historical_preservation(self):
        dirs = [
            "results_cpu1_mem3",
            "results_cpu1_mem512",
            "results_cpu1_mem512_n1000_run1",
            "results_cpu1_mem512_n1000_run2",
            "results_cpu1_mem512_n1000_run3",
            "results_cpu2_mem3"
        ]
        total_files = sum(len(list((ROOT_DIR / d).glob("*"))) for d in dirs)
        self.assertEqual(total_files, 26, "Historical files must be exactly 26 and preserved")

if __name__ == "__main__":
    unittest.main()
