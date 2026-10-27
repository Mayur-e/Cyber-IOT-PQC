#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <math.h>
#include <oqs/oqs.h>
#include <openssl/evp.h>
#include <openssl/crypto.h>

#include "benchmark_native.h"

static void test_monotonic_timer(void) {
    printf("[TEST] Verifying high-resolution monotonic timer...\n");
    uint64_t t0 = get_time_ns();
    struct timespec req = {0, 1000000}; // 1 ms sleep
    nanosleep(&req, NULL);
    uint64_t t1 = get_time_ns();
    assert(t1 > t0);
    double elapsed_us = (double)(t1 - t0) / 1000.0;
    assert(elapsed_us >= 500.0); // At least 0.5 ms
    printf("  [PASS] Timer monotonic: elapsed = %.2f us\n", elapsed_us);
}

static void test_mlkem768_invariants(void) {
    printf("[TEST] Verifying ML-KEM-768 correctness & security invariants...\n");
    OQS_KEM *kem = OQS_KEM_new(OQS_KEM_alg_ml_kem_768);
    assert(kem != NULL);
    assert(kem->length_public_key == 1184);
    assert(kem->length_secret_key == 2400);
    assert(kem->length_ciphertext == 1088);
    assert(kem->length_shared_secret == 32);

    uint8_t pk[1184], sk[2400], ct[1088], ss_enc[32], ss_dec[32];
    assert(OQS_KEM_keypair(kem, pk, sk) == OQS_SUCCESS);
    assert(OQS_KEM_encaps(kem, ct, ss_enc, pk) == OQS_SUCCESS);
    assert(OQS_KEM_decaps(kem, ss_dec, ct, sk) == OQS_SUCCESS);
    assert(memcmp(ss_enc, ss_dec, 32) == 0);

    // Tamper ciphertext: decapsulation should produce mismatched secret (implicit rejection)
    ct[0] ^= 0xFF;
    uint8_t ss_tampered[32];
    assert(OQS_KEM_decaps(kem, ss_tampered, ct, sk) == OQS_SUCCESS);
    assert(memcmp(ss_enc, ss_tampered, 32) != 0);

    OQS_KEM_free(kem);
    printf("  [PASS] ML-KEM-768 round-trip match and implicit rejection verified.\n");
}

static void test_mldsa65_invariants(void) {
    printf("[TEST] Verifying ML-DSA-65 correctness & negative verification...\n");
    OQS_SIG *sig = OQS_SIG_new(OQS_SIG_alg_ml_dsa_65);
    assert(sig != NULL);
    assert(sig->length_public_key == 1952);
    assert(sig->length_secret_key == 4032);
    assert(sig->length_signature == 3309);

    uint8_t pk[1952], sk[4032], sm[3309];
    size_t sig_len = 0;
    const uint8_t msg[] = "Cryptographic test payload for ML-DSA-65.";

    assert(OQS_SIG_keypair(sig, pk, sk) == OQS_SUCCESS);
    assert(OQS_SIG_sign(sig, sm, &sig_len, msg, sizeof(msg), sk) == OQS_SUCCESS);
    assert(sig_len == 3309);

    // Valid verification
    assert(OQS_SIG_verify(sig, msg, sizeof(msg), sm, sig_len, pk) == OQS_SUCCESS);

    // Corrupted message should fail
    uint8_t bad_msg[sizeof(msg)];
    memcpy(bad_msg, msg, sizeof(msg));
    bad_msg[0] ^= 0x01;
    assert(OQS_SIG_verify(sig, bad_msg, sizeof(msg), sm, sig_len, pk) != OQS_SUCCESS);

    // Corrupted signature should fail
    sm[10] ^= 0x55;
    assert(OQS_SIG_verify(sig, msg, sizeof(msg), sm, sig_len, pk) != OQS_SUCCESS);

    OQS_SIG_free(sig);
    printf("  [PASS] ML-DSA-65 positive verification and tamper rejection verified.\n");
}

static void test_x25519_invariants(void) {
    printf("[TEST] Verifying X25519 mutual key agreement...\n");
    EVP_PKEY *pka = EVP_PKEY_Q_keygen(NULL, NULL, "X25519");
    EVP_PKEY *pkb = EVP_PKEY_Q_keygen(NULL, NULL, "X25519");
    assert(pka != NULL && pkb != NULL);

    EVP_PKEY_CTX *ctx_a = EVP_PKEY_CTX_new(pka, NULL);
    EVP_PKEY_derive_init(ctx_a);
    EVP_PKEY_derive_set_peer(ctx_a, pkb);
    size_t ssa_len = 0;
    assert(EVP_PKEY_derive(ctx_a, NULL, &ssa_len) == 1);
    assert(ssa_len == 32);
    uint8_t ssa[32];
    assert(EVP_PKEY_derive(ctx_a, ssa, &ssa_len) == 1);

    EVP_PKEY_CTX *ctx_b = EVP_PKEY_CTX_new(pkb, NULL);
    EVP_PKEY_derive_init(ctx_b);
    EVP_PKEY_derive_set_peer(ctx_b, pka);
    size_t ssb_len = 0;
    assert(EVP_PKEY_derive(ctx_b, NULL, &ssb_len) == 1);
    assert(ssb_len == 32);
    uint8_t ssb[32];
    assert(EVP_PKEY_derive(ctx_b, ssb, &ssb_len) == 1);

    assert(memcmp(ssa, ssb, 32) == 0);

    EVP_PKEY_CTX_free(ctx_a);
    EVP_PKEY_CTX_free(ctx_b);
    EVP_PKEY_free(pka);
    EVP_PKEY_free(pkb);
    printf("  [PASS] X25519 bilateral shared secret equivalence verified.\n");
}

static void test_ecdsa_invariants(void) {
    printf("[TEST] Verifying ECDSA P-256 signing and negative verification...\n");
    EVP_PKEY *eckey = EVP_PKEY_Q_keygen(NULL, NULL, "EC", "P-256");
    assert(eckey != NULL);

    const uint8_t msg[] = "Cryptographic test payload for ECDSA P-256.";
    EVP_MD_CTX *mctx = EVP_MD_CTX_new();
    assert(EVP_DigestSignInit(mctx, NULL, EVP_sha256(), NULL, eckey) == 1);
    size_t sig_len = 0;
    assert(EVP_DigestSign(mctx, NULL, &sig_len, msg, sizeof(msg)) == 1);
    assert(sig_len >= 68 && sig_len <= 74); // ASN.1 DER bounds

    uint8_t *sig = malloc(sig_len);
    assert(EVP_DigestSign(mctx, sig, &sig_len, msg, sizeof(msg)) == 1);
    EVP_MD_CTX_free(mctx);

    // Verify valid signature
    mctx = EVP_MD_CTX_new();
    assert(EVP_DigestVerifyInit(mctx, NULL, EVP_sha256(), NULL, eckey) == 1);
    assert(EVP_DigestVerify(mctx, sig, sig_len, msg, sizeof(msg)) == 1);
    EVP_MD_CTX_free(mctx);

    // Corrupted message should fail
    uint8_t bad_msg[sizeof(msg)];
    memcpy(bad_msg, msg, sizeof(msg));
    bad_msg[0] ^= 0x80;
    mctx = EVP_MD_CTX_new();
    assert(EVP_DigestVerifyInit(mctx, NULL, EVP_sha256(), NULL, eckey) == 1);
    assert(EVP_DigestVerify(mctx, sig, sig_len, bad_msg, sizeof(msg)) != 1);
    EVP_MD_CTX_free(mctx);

    free(sig);
    EVP_PKEY_free(eckey);
    printf("  [PASS] ECDSA P-256 signature verification & tamper rejection verified.\n");
}

static void test_statistical_math(void) {
    printf("[TEST] Verifying statistical computation engine...\n");
    double samples[] = {10.0, 20.0, 30.0, 40.0, 50.0};
    OpStats st = compute_stats(samples, 5);
    assert(st.count == 5);
    assert(fabs(st.median_us - 30.0) < 1e-6);
    assert(fabs(st.mean_us - 30.0) < 1e-6);
    assert(fabs(st.min_us - 10.0) < 1e-6);
    assert(fabs(st.iqr_us - 20.0) < 1e-6); // Q3(40) - Q1(20) = 20
    assert(fabs(st.mad_us - 10.0) < 1e-6); // deviations: 0, 10, 10, 20, 20 -> median is 10
    printf("  [PASS] Statistical routines match reference mathematics.\n");
}

int main(void) {
    printf("======================================================================\n");
    printf("Stage E: Host-Native C Automated Test Suite\n");
    printf("======================================================================\n");

    OQS_init();
    test_monotonic_timer();
    test_mlkem768_invariants();
    test_mldsa65_invariants();
    test_x25519_invariants();
    test_ecdsa_invariants();
    test_statistical_math();
    OQS_destroy();

    printf("\n[SUCCESS] ALL STAGE E NATIVE C UNIT & INVARIANT TESTS PASSED (6/6)!\n");
    return 0;
}
