#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <oqs/oqs.h>
#include <openssl/evp.h>
#include <openssl/crypto.h>

int main(void) {
    OQS_init();
    printf("Testing liboqs ML-KEM-768...\n");
    OQS_KEM *kem = OQS_KEM_new(OQS_KEM_alg_ml_kem_768);
    if (!kem) { printf("Error: KEM init failed\n"); return 1; }
    
    uint8_t *pk = malloc(kem->length_public_key);
    uint8_t *sk = malloc(kem->length_secret_key);
    uint8_t *ct = malloc(kem->length_ciphertext);
    uint8_t *ss_enc = malloc(kem->length_shared_secret);
    uint8_t *ss_dec = malloc(kem->length_shared_secret);
    
    if (OQS_KEM_keypair(kem, pk, sk) != OQS_SUCCESS) { printf("KEM keypair failed\n"); return 1; }
    if (OQS_KEM_encaps(kem, ct, ss_enc, pk) != OQS_SUCCESS) { printf("KEM encap failed\n"); return 1; }
    if (OQS_KEM_decaps(kem, ss_dec, ct, sk) != OQS_SUCCESS) { printf("KEM decap failed\n"); return 1; }
    if (memcmp(ss_enc, ss_dec, kem->length_shared_secret) != 0) { printf("KEM SS mismatch!\n"); return 1; }
    printf("ML-KEM-768 OK! PK=%zu, CT=%zu, SS=%zu\n", kem->length_public_key, kem->length_ciphertext, kem->length_shared_secret);
    
    free(pk); free(sk); free(ct); free(ss_enc); free(ss_dec);
    OQS_KEM_free(kem);
    
    printf("Testing liboqs ML-DSA-65...\n");
    OQS_SIG *sig = OQS_SIG_new(OQS_SIG_alg_ml_dsa_65);
    if (!sig) { printf("Error: SIG init failed\n"); return 1; }
    
    uint8_t *spk = malloc(sig->length_public_key);
    uint8_t *ssk = malloc(sig->length_secret_key);
    uint8_t *sm = malloc(sig->length_signature);
    size_t sig_len = 0;
    const uint8_t msg[] = "Test message for ML-DSA-65 verification.";
    
    if (OQS_SIG_keypair(sig, spk, ssk) != OQS_SUCCESS) { printf("SIG keypair failed\n"); return 1; }
    if (OQS_SIG_sign(sig, sm, &sig_len, msg, sizeof(msg), ssk) != OQS_SUCCESS) { printf("SIG sign failed\n"); return 1; }
    if (OQS_SIG_verify(sig, msg, sizeof(msg), sm, sig_len, spk) != OQS_SUCCESS) { printf("SIG verify failed\n"); return 1; }
    printf("ML-DSA-65 OK! PK=%zu, Sig=%zu\n", sig->length_public_key, sig_len);
    
    free(spk); free(ssk); free(sm);
    OQS_SIG_free(sig);
    
    printf("Testing OpenSSL X25519...\n");
    EVP_PKEY *pka = EVP_PKEY_Q_keygen(NULL, NULL, "X25519");
    EVP_PKEY *pkb = EVP_PKEY_Q_keygen(NULL, NULL, "X25519");
    if (!pka || !pkb) { printf("X25519 keygen failed\n"); return 1; }
    
    EVP_PKEY_CTX *ctx_a = EVP_PKEY_CTX_new(pka, NULL);
    EVP_PKEY_derive_init(ctx_a);
    EVP_PKEY_derive_set_peer(ctx_a, pkb);
    size_t ssa_len = 0;
    EVP_PKEY_derive(ctx_a, NULL, &ssa_len);
    uint8_t *ssa = malloc(ssa_len);
    EVP_PKEY_derive(ctx_a, ssa, &ssa_len);
    
    EVP_PKEY_CTX *ctx_b = EVP_PKEY_CTX_new(pkb, NULL);
    EVP_PKEY_derive_init(ctx_b);
    EVP_PKEY_derive_set_peer(ctx_b, pka);
    size_t ssb_len = 0;
    EVP_PKEY_derive(ctx_b, NULL, &ssb_len);
    uint8_t *ssb = malloc(ssb_len);
    EVP_PKEY_derive(ctx_b, ssb, &ssb_len);
    
    if (ssa_len != 32 || ssb_len != 32 || memcmp(ssa, ssb, 32) != 0) { printf("X25519 SS mismatch\n"); return 1; }
    printf("X25519 OK! SS=%zu\n", ssa_len);
    
    free(ssa); free(ssb);
    EVP_PKEY_CTX_free(ctx_a); EVP_PKEY_CTX_free(ctx_b);
    EVP_PKEY_free(pka); EVP_PKEY_free(pkb);
    
    printf("Testing OpenSSL ECDSA P-256...\n");
    EVP_PKEY *eckey = EVP_PKEY_Q_keygen(NULL, NULL, "EC", "P-256");
    if (!eckey) { printf("ECDSA keygen failed\n"); return 1; }
    
    EVP_MD_CTX *mctx = EVP_MD_CTX_new();
    EVP_DigestSignInit(mctx, NULL, EVP_sha256(), NULL, eckey);
    size_t esig_len = 0;
    EVP_DigestSign(mctx, NULL, &esig_len, msg, sizeof(msg));
    uint8_t *esig = malloc(esig_len);
    EVP_DigestSign(mctx, esig, &esig_len, msg, sizeof(msg));
    EVP_MD_CTX_free(mctx);
    
    mctx = EVP_MD_CTX_new();
    EVP_DigestVerifyInit(mctx, NULL, EVP_sha256(), NULL, eckey);
    int vres = EVP_DigestVerify(mctx, esig, esig_len, msg, sizeof(msg));
    EVP_MD_CTX_free(mctx);
    if (vres != 1) { printf("ECDSA verify failed\n"); return 1; }
    printf("ECDSA P-256 OK! Sig len=%zu\n", esig_len);
    
    free(esig);
    EVP_PKEY_free(eckey);
    OQS_destroy();
    printf("ALL NATIVE C API CHECKS PASSED!\n");
    return 0;
}
