#!/usr/bin/env python3
"""
Stage D1-E: Automated Test Suite
Empirical Migration Feasibility Analysis of Post-Quantum Cryptography for Resource-Constrained Systems

Validates:
1. Standardized fixed-size artifact lengths
2. Variable ECDSA DER signature length boundaries
3. Cryptographic correctness, shared secret equality, and altered message rejection
4. Fragmentation arithmetic and boundary conditions (zero-length, exact multiples, +1 overflow)
5. Message-budget calculation consistency
6. Local TCP socket framing, loopback payload byte equality, and partial-read robustness
"""

import math
import socket
import struct
import sys
import threading
import time
import unittest

import oqs
import cryptography
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, x25519
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.exceptions import InvalidSignature

from stage_d1_fragmentation import calculate_fragments
from stage_d1_transport import recv_exact

class TestStageD1CryptoArtifacts(unittest.TestCase):
    def test_x25519_sizes_and_correctness(self):
        priv_a = x25519.X25519PrivateKey.generate()
        pub_a = priv_a.public_key()
        raw_pub = pub_a.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        spki_pub = pub_a.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        
        self.assertEqual(len(raw_pub), 32, "X25519 raw public key must be exactly 32 bytes")
        self.assertEqual(len(spki_pub), 44, "X25519 SPKI DER public key must be exactly 44 bytes")

        priv_b = x25519.X25519PrivateKey.generate()
        ss_a = priv_a.exchange(priv_b.public_key())
        ss_b = priv_b.exchange(pub_a)
        self.assertEqual(len(ss_a), 32, "X25519 shared secret must be 32 bytes")
        self.assertEqual(ss_a, ss_b, "X25519 mutual key agreement shared secrets must match")

    def test_mlkem768_sizes_and_correctness(self):
        with oqs.KeyEncapsulation("ML-KEM-768") as kem:
            pk = kem.generate_keypair()
            self.assertEqual(len(pk), 1184, "ML-KEM-768 public key must be exactly 1184 bytes")
            
            ct, ss_srv = kem.encap_secret(pk)
            self.assertEqual(len(ct), 1088, "ML-KEM-768 ciphertext must be exactly 1088 bytes")
            self.assertEqual(len(ss_srv), 32, "ML-KEM-768 shared secret must be exactly 32 bytes")
            
            ss_cli = kem.decap_secret(ct)
            self.assertEqual(ss_srv, ss_cli, "ML-KEM-768 client and server shared secrets must match")

    def test_ecdsa_p256_sizes_and_signatures(self):
        priv = ec.generate_private_key(ec.SECP256R1())
        pub = priv.public_key()
        
        pk_uncompressed = pub.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
        pk_compressed = pub.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.CompressedPoint)
        pk_spki = pub.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        
        self.assertEqual(len(pk_uncompressed), 65, "ECDSA P-256 uncompressed point must be 65 bytes")
        self.assertEqual(len(pk_compressed), 33, "ECDSA P-256 compressed point must be 33 bytes")
        self.assertEqual(len(pk_spki), 91, "ECDSA P-256 SPKI DER must be 91 bytes")

        msg = b"Validation message for ECDSA P-256 signature verification"
        sig_der = priv.sign(msg, ec.ECDSA(hashes.SHA256()))
        self.assertTrue(69 <= len(sig_der) <= 73, f"ECDSA DER signature length {len(sig_der)} outside expected range [69, 73]")
        
        # Valid signature verification
        pub.verify(sig_der, msg, ec.ECDSA(hashes.SHA256()))
        
        # Corrupted message rejection
        corrupted = msg[:-1] + (b"\x00" if msg[-1:] != b"\x00" else b"\x01")
        with self.assertRaises(InvalidSignature):
            pub.verify(sig_der, corrupted, ec.ECDSA(hashes.SHA256()))

        # Raw IEEE P1363 decoding
        r, s = decode_dss_signature(sig_der)
        sig_p1363 = r.to_bytes(32, "big") + s.to_bytes(32, "big")
        self.assertEqual(len(sig_p1363), 64, "ECDSA P-256 IEEE P1363 signature must be 64 bytes")

    def test_mldsa65_sizes_and_signatures(self):
        with oqs.Signature("ML-DSA-65") as signer:
            pk = signer.generate_keypair()
            self.assertEqual(len(pk), 1952, "ML-DSA-65 public key must be exactly 1952 bytes")
            
            msg = b"Validation message for ML-DSA-65 signature verification"
            sig = signer.sign(msg)
            self.assertEqual(len(sig), 3309, "ML-DSA-65 signature must be exactly 3309 bytes")
            
            # Positive verification
            self.assertTrue(signer.verify(msg, sig, pk), "ML-DSA-65 signature must verify on valid message")
            
            # Negative verification
            corrupted = msg[:-1] + (b"\x00" if msg[-1:] != b"\x00" else b"\x01")
            self.assertFalse(signer.verify(corrupted, sig, pk), "ML-DSA-65 signature must reject corrupted message")

class TestStageD1Fragmentation(unittest.TestCase):
    def test_zero_bytes(self):
        cnt, last, usable, total = calculate_fragments(0, 1500, 0)
        self.assertEqual(cnt, 0)
        self.assertEqual(last, 0)
        self.assertEqual(total, 0)

    def test_under_budget(self):
        # 100 bytes in 1500-byte budget
        cnt, last, usable, total = calculate_fragments(100, 1500, 48)
        self.assertEqual(cnt, 1)
        self.assertEqual(usable, 1452)
        self.assertEqual(last, 100)
        self.assertEqual(total, 148) # 100 + 48

    def test_exact_multiple(self):
        # 1452 bytes in 1500-byte budget with 48B overhead
        cnt, last, usable, total = calculate_fragments(1452, 1500, 48)
        self.assertEqual(cnt, 1)
        self.assertEqual(last, 1452)
        self.assertEqual(total, 1500)

        # 2904 bytes in 1500-byte budget with 48B overhead -> 2 fragments of 1452
        cnt, last, usable, total = calculate_fragments(2904, 1500, 48)
        self.assertEqual(cnt, 2)
        self.assertEqual(last, 1452)
        self.assertEqual(total, 3000)

    def test_boundary_overflow(self):
        # 1453 bytes in 1500-byte budget with 48B overhead -> 2 fragments: 1452 and 1
        cnt, last, usable, total = calculate_fragments(1453, 1500, 48)
        self.assertEqual(cnt, 2)
        self.assertEqual(last, 1)
        self.assertEqual(total, 1453 + 2 * 48)

    def test_6lowpan_mlkem_pk(self):
        # ML-KEM PK (1184B) over 6LoWPAN 128B budget with 48B overhead -> usable 80B
        # ceil(1184 / 80) = 15 fragments
        # 14 * 80 = 1120; last fragment = 1184 - 1120 = 64B
        cnt, last, usable, total = calculate_fragments(1184, 128, 48)
        self.assertEqual(usable, 80)
        self.assertEqual(cnt, 15)
        self.assertEqual(last, 64)
        self.assertEqual(total, 1184 + 15 * 48)

    def test_invalid_overhead(self):
        with self.assertRaises(ValueError):
            calculate_fragments(100, 128, 128)

class TestStageD1Transport(unittest.TestCase):
    def test_loopback_exact_read_and_byte_equality(self):
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.bind(("127.0.0.1", 0))
        server_sock.listen(1)
        port = server_sock.getsockname()[1]
        
        test_payload = b"Research byte stream payload." * 50 # 1450 bytes
        frame = struct.pack(">I", len(test_payload)) + test_payload
        
        received_data = []

        def srv_worker():
            conn, _ = server_sock.accept()
            prefix = recv_exact(conn, 4)
            length = struct.unpack(">I", prefix)[0]
            body = recv_exact(conn, length)
            received_data.append(body)
            conn.sendall(b"\x06")
            conn.close()
            server_sock.close()

        t = threading.Thread(target=srv_worker, daemon=True)
        t.start()

        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_sock.connect(("127.0.0.1", port))
        
        # Test sending in multiple small chunks to ensure recv_exact is robust against partial reads
        half = len(frame) // 2
        client_sock.sendall(frame[:half])
        time.sleep(0.01)
        client_sock.sendall(frame[half:])
        
        ack = recv_exact(client_sock, 1)
        client_sock.close()
        t.join(timeout=2.0)

        self.assertEqual(ack, b"\x06")
        self.assertEqual(len(received_data), 1)
        self.assertEqual(received_data[0], test_payload, "Received payload must match transmitted payload bit-for-bit")

if __name__ == "__main__":
    unittest.main()
