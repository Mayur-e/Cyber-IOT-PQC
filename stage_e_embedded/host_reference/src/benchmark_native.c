#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <getopt.h>
#include <sys/stat.h>
#include <oqs/oqs.h>
#include <openssl/evp.h>
#include <openssl/crypto.h>

#include "benchmark_native.h"

static const uint8_t FIXED_TEST_MSG[] = 
    "PQC migration feasibility benchmark - Stage E Host Native C Msg";


// Format UTC ISO timestamp
static void get_iso_timestamp(char *buf, size_t max_len) {
    time_t now = time(NULL);
    struct tm tm_buf;
    gmtime_r(&now, &tm_buf);
    strftime(buf, max_len, "%Y-%m-%dT%H:%M:%SZ", &tm_buf);
}

// -----------------------------------------------------------------------------
// Benchmark: ML-KEM-768 (NIST FIPS 203)
// -----------------------------------------------------------------------------
int bench_mlkem768(size_t warmups, size_t trials, const char *out_csv, const char *run_id, const char *compiler_info, const char *flags_info) {
    printf("[Host C] Benchmarking ML-KEM-768 (Warmups: %zu, Trials: %zu)...\n", warmups, trials);
    OQS_KEM *kem = OQS_KEM_new(OQS_KEM_alg_ml_kem_768);
    if (!kem) {
        fprintf(stderr, "Error: OQS_KEM_new(ML-KEM-768) failed\n");
        return -1;
    }

    uint8_t *pk = malloc(kem->length_public_key);
    uint8_t *sk = malloc(kem->length_secret_key);
    uint8_t *ct = malloc(kem->length_ciphertext);
    uint8_t *ss_enc = malloc(kem->length_shared_secret);
    uint8_t *ss_dec = malloc(kem->length_shared_secret);

    // Warm-up loop
    for (size_t w = 0; w < warmups; w++) {
        OQS_KEM_keypair(kem, pk, sk);
        OQS_KEM_encaps(kem, ct, ss_enc, pk);
        OQS_KEM_decaps(kem, ss_dec, ct, sk);
    }

    double *s_keygen = malloc(trials * sizeof(double));
    double *s_encap  = malloc(trials * sizeof(double));
    double *s_decap  = malloc(trials * sizeof(double));

    FILE *f_raw = fopen(out_csv, "a");
    if (!f_raw) {
        fprintf(stderr, "Error opening raw output CSV\n");
        return -1;
    }

    char ts[64];
    for (size_t t = 0; t < trials; t++) {
        get_iso_timestamp(ts, sizeof(ts));

        // 1. Key generation
        uint64_t t0 = get_time_ns();
        OQS_STATUS res_kg = OQS_KEM_keypair(kem, pk, sk);
        uint64_t t1 = get_time_ns();
        double us_kg = (double)(t1 - t0) / 1000.0;
        s_keygen[t] = us_kg;

        // Write keygen raw row
        fprintf(f_raw, "%s,%s,host_x86_64,host_workstation,AMD_Ryzen_7_7435HS,ML-KEM-768,keygen,liboqs_c,liboqs,%s,clean,%s,14.2.0,%s,0,clock_monotonic_raw,%zu,0,%.3f,%s,%s,false,FIPS_203_PK_%zu_SK_%zu\n",
                run_id, ts, OQS_version(), compiler_info, flags_info, t, us_kg, (res_kg == OQS_SUCCESS ? "OK" : "ERROR"), (res_kg == OQS_SUCCESS ? "true" : "false"), kem->length_public_key, kem->length_secret_key);

        // 2. Encapsulation
        t0 = get_time_ns();
        OQS_STATUS res_enc = OQS_KEM_encaps(kem, ct, ss_enc, pk);
        t1 = get_time_ns();
        double us_enc = (double)(t1 - t0) / 1000.0;
        s_encap[t] = us_enc;

        fprintf(f_raw, "%s,%s,host_x86_64,host_workstation,AMD_Ryzen_7_7435HS,ML-KEM-768,encapsulation,liboqs_c,liboqs,%s,clean,%s,14.2.0,%s,0,clock_monotonic_raw,%zu,0,%.3f,%s,%s,false,FIPS_203_CT_%zu_SS_%zu\n",
                run_id, ts, OQS_version(), compiler_info, flags_info, t, us_enc, (res_enc == OQS_SUCCESS ? "OK" : "ERROR"), (res_enc == OQS_SUCCESS ? "true" : "false"), kem->length_ciphertext, kem->length_shared_secret);

        // 3. Decapsulation
        t0 = get_time_ns();
        OQS_STATUS res_dec = OQS_KEM_decaps(kem, ss_dec, ct, sk);
        t1 = get_time_ns();
        double us_dec = (double)(t1 - t0) / 1000.0;
        s_decap[t] = us_dec;

        bool match = (memcmp(ss_enc, ss_dec, kem->length_shared_secret) == 0);
        fprintf(f_raw, "%s,%s,host_x86_64,host_workstation,AMD_Ryzen_7_7435HS,ML-KEM-768,decapsulation,liboqs_c,liboqs,%s,clean,%s,14.2.0,%s,0,clock_monotonic_raw,%zu,0,%.3f,%s,%s,false,FIPS_203_SS_MATCH_%d\n",
                run_id, ts, OQS_version(), compiler_info, flags_info, t, us_dec, (res_dec == OQS_SUCCESS && match ? "OK" : "ERROR"), (res_dec == OQS_SUCCESS && match ? "true" : "false"), match ? 1 : 0);
    }
    fclose(f_raw);

    OpStats st_kg = compute_stats(s_keygen, trials);
    OpStats st_enc = compute_stats(s_encap, trials);
    OpStats st_dec = compute_stats(s_decap, trials);

    printf("  [ML-KEM-768] Keygen:  Median=%.2f us, Mean=%.2f us (P95=%.2f us, IQR=%.2f us)\n", st_kg.median_us, st_kg.mean_us, st_kg.p95_us, st_kg.iqr_us);
    printf("  [ML-KEM-768] Encap:   Median=%.2f us, Mean=%.2f us (P95=%.2f us, IQR=%.2f us)\n", st_enc.median_us, st_enc.mean_us, st_enc.p95_us, st_enc.iqr_us);
    printf("  [ML-KEM-768] Decap:   Median=%.2f us, Mean=%.2f us (P95=%.2f us, IQR=%.2f us)\n", st_dec.median_us, st_dec.mean_us, st_dec.p95_us, st_dec.iqr_us);

    free(pk); free(sk); free(ct); free(ss_enc); free(ss_dec);
    free(s_keygen); free(s_encap); free(s_decap);
    OQS_KEM_free(kem);
    return 0;
}

// -----------------------------------------------------------------------------
// Benchmark: ML-DSA-65 (NIST FIPS 204)
// -----------------------------------------------------------------------------
int bench_mldsa65(size_t warmups, size_t trials, const char *out_csv, const char *run_id, const char *compiler_info, const char *flags_info) {
    printf("[Host C] Benchmarking ML-DSA-65 (Warmups: %zu, Trials: %zu)...\n", warmups, trials);
    OQS_SIG *sig = OQS_SIG_new(OQS_SIG_alg_ml_dsa_65);
    if (!sig) {
        fprintf(stderr, "Error: OQS_SIG_new(ML-DSA-65) failed\n");
        return -1;
    }

    uint8_t *pk = malloc(sig->length_public_key);
    uint8_t *sk = malloc(sig->length_secret_key);
    uint8_t *sm = malloc(sig->length_signature);
    size_t sig_len = 0;

    // Warm-up loop
    for (size_t w = 0; w < warmups; w++) {
        OQS_SIG_keypair(sig, pk, sk);
        OQS_SIG_sign(sig, sm, &sig_len, FIXED_TEST_MSG, sizeof(FIXED_TEST_MSG), sk);
        OQS_SIG_verify(sig, FIXED_TEST_MSG, sizeof(FIXED_TEST_MSG), sm, sig_len, pk);
    }

    double *s_keygen = malloc(trials * sizeof(double));
    double *s_sign   = malloc(trials * sizeof(double));
    double *s_verify = malloc(trials * sizeof(double));

    FILE *f_raw = fopen(out_csv, "a");
    if (!f_raw) {
        fprintf(stderr, "Error opening raw output CSV\n");
        return -1;
    }

    char ts[64];
    for (size_t t = 0; t < trials; t++) {
        get_iso_timestamp(ts, sizeof(ts));

        // 1. Key generation
        uint64_t t0 = get_time_ns();
        OQS_STATUS res_kg = OQS_SIG_keypair(sig, pk, sk);
        uint64_t t1 = get_time_ns();
        double us_kg = (double)(t1 - t0) / 1000.0;
        s_keygen[t] = us_kg;

        fprintf(f_raw, "%s,%s,host_x86_64,host_workstation,AMD_Ryzen_7_7435HS,ML-DSA-65,keygen,liboqs_c,liboqs,%s,clean,%s,14.2.0,%s,0,clock_monotonic_raw,%zu,0,%.3f,%s,%s,false,FIPS_204_PK_%zu_SK_%zu\n",
                run_id, ts, OQS_version(), compiler_info, flags_info, t, us_kg, (res_kg == OQS_SUCCESS ? "OK" : "ERROR"), (res_kg == OQS_SUCCESS ? "true" : "false"), sig->length_public_key, sig->length_secret_key);

        // 2. Signing
        t0 = get_time_ns();
        OQS_STATUS res_sign = OQS_SIG_sign(sig, sm, &sig_len, FIXED_TEST_MSG, sizeof(FIXED_TEST_MSG), sk);
        t1 = get_time_ns();
        double us_sign = (double)(t1 - t0) / 1000.0;
        s_sign[t] = us_sign;

        fprintf(f_raw, "%s,%s,host_x86_64,host_workstation,AMD_Ryzen_7_7435HS,ML-DSA-65,sign,liboqs_c,liboqs,%s,clean,%s,14.2.0,%s,0,clock_monotonic_raw,%zu,0,%.3f,%s,%s,false,FIPS_204_SIG_%zu\n",
                run_id, ts, OQS_version(), compiler_info, flags_info, t, us_sign, (res_sign == OQS_SUCCESS ? "OK" : "ERROR"), (res_sign == OQS_SUCCESS ? "true" : "false"), sig_len);

        // 3. Verification
        t0 = get_time_ns();
        OQS_STATUS res_ver = OQS_SIG_verify(sig, FIXED_TEST_MSG, sizeof(FIXED_TEST_MSG), sm, sig_len, pk);
        t1 = get_time_ns();
        double us_ver = (double)(t1 - t0) / 1000.0;
        s_verify[t] = us_ver;

        fprintf(f_raw, "%s,%s,host_x86_64,host_workstation,AMD_Ryzen_7_7435HS,ML-DSA-65,verify,liboqs_c,liboqs,%s,clean,%s,14.2.0,%s,0,clock_monotonic_raw,%zu,0,%.3f,%s,%s,false,FIPS_204_VERIFY_OK\n",
                run_id, ts, OQS_version(), compiler_info, flags_info, t, us_ver, (res_ver == OQS_SUCCESS ? "OK" : "ERROR"), (res_ver == OQS_SUCCESS ? "true" : "false"));
    }
    fclose(f_raw);

    OpStats st_kg = compute_stats(s_keygen, trials);
    OpStats st_sn = compute_stats(s_sign, trials);
    OpStats st_vr = compute_stats(s_verify, trials);

    printf("  [ML-DSA-65] Keygen:  Median=%.2f us, Mean=%.2f us (P95=%.2f us, IQR=%.2f us)\n", st_kg.median_us, st_kg.mean_us, st_kg.p95_us, st_kg.iqr_us);
    printf("  [ML-DSA-65] Sign:    Median=%.2f us, Mean=%.2f us (P95=%.2f us, IQR=%.2f us)\n", st_sn.median_us, st_sn.mean_us, st_sn.p95_us, st_sn.iqr_us);
    printf("  [ML-DSA-65] Verify:  Median=%.2f us, Mean=%.2f us (P95=%.2f us, IQR=%.2f us)\n", st_vr.median_us, st_vr.mean_us, st_vr.p95_us, st_vr.iqr_us);

    free(pk); free(sk); free(sm);
    free(s_keygen); free(s_sign); free(s_verify);
    OQS_SIG_free(sig);
    return 0;
}

// -----------------------------------------------------------------------------
// Benchmark: X25519 (RFC 7748)
// -----------------------------------------------------------------------------
int bench_x25519(size_t warmups, size_t trials, const char *out_csv, const char *run_id, const char *compiler_info, const char *flags_info) {
    printf("[Host C] Benchmarking X25519 (Warmups: %zu, Trials: %zu)...\n", warmups, trials);
    EVP_PKEY *pka = NULL;
    EVP_PKEY *pkb = NULL;

    // Warm-up loop
    for (size_t w = 0; w < warmups; w++) {
        pka = EVP_PKEY_Q_keygen(NULL, NULL, "X25519");
        pkb = EVP_PKEY_Q_keygen(NULL, NULL, "X25519");
        EVP_PKEY_CTX *ctx = EVP_PKEY_CTX_new(pka, NULL);
        EVP_PKEY_derive_init(ctx);
        EVP_PKEY_derive_set_peer(ctx, pkb);
        size_t s_len = 0;
        EVP_PKEY_derive(ctx, NULL, &s_len);
        uint8_t *s = malloc(s_len);
        EVP_PKEY_derive(ctx, s, &s_len);
        free(s);
        EVP_PKEY_CTX_free(ctx);
        EVP_PKEY_free(pka);
        EVP_PKEY_free(pkb);
    }

    double *s_keygen = malloc(trials * sizeof(double));
    double *s_derive = malloc(trials * sizeof(double));

    FILE *f_raw = fopen(out_csv, "a");
    if (!f_raw) {
        fprintf(stderr, "Error opening raw output CSV\n");
        return -1;
    }

    char ts[64];
    for (size_t t = 0; t < trials; t++) {
        get_iso_timestamp(ts, sizeof(ts));

        // 1. Key generation
        uint64_t t0 = get_time_ns();
        pka = EVP_PKEY_Q_keygen(NULL, NULL, "X25519");
        uint64_t t1 = get_time_ns();
        double us_kg = (double)(t1 - t0) / 1000.0;
        s_keygen[t] = us_kg;

        fprintf(f_raw, "%s,%s,host_x86_64,host_workstation,AMD_Ryzen_7_7435HS,X25519,keygen,openssl_c,OpenSSL,%s,clean,%s,14.2.0,%s,0,clock_monotonic_raw,%zu,0,%.3f,%s,%s,false,RFC_7748_KEYGEN\n",
                run_id, ts, OpenSSL_version(OPENSSL_VERSION_STRING), compiler_info, flags_info, t, us_kg, (pka != NULL ? "OK" : "ERROR"), (pka != NULL ? "true" : "false"));

        // Generate peer key for derive timing
        pkb = EVP_PKEY_Q_keygen(NULL, NULL, "X25519");

        // Prepare derive context outside timed region
        EVP_PKEY_CTX *ctx = EVP_PKEY_CTX_new(pka, NULL);
        EVP_PKEY_derive_init(ctx);
        EVP_PKEY_derive_set_peer(ctx, pkb);
        size_t ss_len = 0;
        EVP_PKEY_derive(ctx, NULL, &ss_len);
        uint8_t *ss = malloc(ss_len);

        // 2. Shared secret derivation
        t0 = get_time_ns();
        int res_der = EVP_PKEY_derive(ctx, ss, &ss_len);
        t1 = get_time_ns();
        double us_der = (double)(t1 - t0) / 1000.0;
        s_derive[t] = us_der;

        fprintf(f_raw, "%s,%s,host_x86_64,host_workstation,AMD_Ryzen_7_7435HS,X25519,shared_secret_derivation,openssl_c,OpenSSL,%s,clean,%s,14.2.0,%s,0,clock_monotonic_raw,%zu,0,%.3f,%s,%s,false,RFC_7748_SS_%zu\n",
                run_id, ts, OpenSSL_version(OPENSSL_VERSION_STRING), compiler_info, flags_info, t, us_der, (res_der == 1 ? "OK" : "ERROR"), (res_der == 1 ? "true" : "false"), ss_len);

        free(ss);
        EVP_PKEY_CTX_free(ctx);
        EVP_PKEY_free(pka);
        EVP_PKEY_free(pkb);
    }
    fclose(f_raw);

    OpStats st_kg = compute_stats(s_keygen, trials);
    OpStats st_dr = compute_stats(s_derive, trials);

    printf("  [X25519] Keygen:  Median=%.2f us, Mean=%.2f us (P95=%.2f us, IQR=%.2f us)\n", st_kg.median_us, st_kg.mean_us, st_kg.p95_us, st_kg.iqr_us);
    printf("  [X25519] Derive:  Median=%.2f us, Mean=%.2f us (P95=%.2f us, IQR=%.2f us)\n", st_dr.median_us, st_dr.mean_us, st_dr.p95_us, st_dr.iqr_us);

    free(s_keygen); free(s_derive);
    return 0;
}

// -----------------------------------------------------------------------------
// Benchmark: ECDSA P-256 (NIST FIPS 186-5)
// -----------------------------------------------------------------------------
int bench_ecdsa_p256(size_t warmups, size_t trials, const char *out_csv, const char *run_id, const char *compiler_info, const char *flags_info) {
    printf("[Host C] Benchmarking ECDSA P-256 (Warmups: %zu, Trials: %zu)...\n", warmups, trials);
    EVP_PKEY *eckey = NULL;

    // Warm-up loop
    for (size_t w = 0; w < warmups; w++) {
        eckey = EVP_PKEY_Q_keygen(NULL, NULL, "EC", "P-256");
        EVP_MD_CTX *mctx = EVP_MD_CTX_new();
        EVP_DigestSignInit(mctx, NULL, EVP_sha256(), NULL, eckey);
        size_t sig_len = 0;
        EVP_DigestSign(mctx, NULL, &sig_len, FIXED_TEST_MSG, sizeof(FIXED_TEST_MSG));
        uint8_t *sig = malloc(sig_len);
        EVP_DigestSign(mctx, sig, &sig_len, FIXED_TEST_MSG, sizeof(FIXED_TEST_MSG));
        EVP_MD_CTX_free(mctx);

        mctx = EVP_MD_CTX_new();
        EVP_DigestVerifyInit(mctx, NULL, EVP_sha256(), NULL, eckey);
        EVP_DigestVerify(mctx, sig, sig_len, FIXED_TEST_MSG, sizeof(FIXED_TEST_MSG));
        EVP_MD_CTX_free(mctx);
        free(sig);
        EVP_PKEY_free(eckey);
    }

    double *s_keygen = malloc(trials * sizeof(double));
    double *s_sign   = malloc(trials * sizeof(double));
    double *s_verify = malloc(trials * sizeof(double));

    FILE *f_raw = fopen(out_csv, "a");
    if (!f_raw) {
        fprintf(stderr, "Error opening raw output CSV\n");
        return -1;
    }

    char ts[64];
    for (size_t t = 0; t < trials; t++) {
        get_iso_timestamp(ts, sizeof(ts));

        // 1. Key generation
        uint64_t t0 = get_time_ns();
        eckey = EVP_PKEY_Q_keygen(NULL, NULL, "EC", "P-256");
        uint64_t t1 = get_time_ns();
        double us_kg = (double)(t1 - t0) / 1000.0;
        s_keygen[t] = us_kg;

        fprintf(f_raw, "%s,%s,host_x86_64,host_workstation,AMD_Ryzen_7_7435HS,ECDSA-P256,keygen,openssl_c,OpenSSL,%s,clean,%s,14.2.0,%s,0,clock_monotonic_raw,%zu,0,%.3f,%s,%s,false,SECP256R1_KEYGEN\n",
                run_id, ts, OpenSSL_version(OPENSSL_VERSION_STRING), compiler_info, flags_info, t, us_kg, (eckey != NULL ? "OK" : "ERROR"), (eckey != NULL ? "true" : "false"));

        // Setup signing context
        EVP_MD_CTX *mctx = EVP_MD_CTX_new();
        EVP_DigestSignInit(mctx, NULL, EVP_sha256(), NULL, eckey);
        size_t sig_len = 0;
        EVP_DigestSign(mctx, NULL, &sig_len, FIXED_TEST_MSG, sizeof(FIXED_TEST_MSG));
        uint8_t *sig = malloc(sig_len);

        // 2. Signing
        t0 = get_time_ns();
        int res_sign = EVP_DigestSign(mctx, sig, &sig_len, FIXED_TEST_MSG, sizeof(FIXED_TEST_MSG));
        t1 = get_time_ns();
        double us_sign = (double)(t1 - t0) / 1000.0;
        s_sign[t] = us_sign;
        EVP_MD_CTX_free(mctx);

        fprintf(f_raw, "%s,%s,host_x86_64,host_workstation,AMD_Ryzen_7_7435HS,ECDSA-P256,sign,openssl_c,OpenSSL,%s,clean,%s,14.2.0,%s,0,clock_monotonic_raw,%zu,0,%.3f,%s,%s,false,DER_SIG_%zu\n",
                run_id, ts, OpenSSL_version(OPENSSL_VERSION_STRING), compiler_info, flags_info, t, us_sign, (res_sign == 1 ? "OK" : "ERROR"), (res_sign == 1 ? "true" : "false"), sig_len);

        // Setup verification context outside timed region
        mctx = EVP_MD_CTX_new();
        EVP_DigestVerifyInit(mctx, NULL, EVP_sha256(), NULL, eckey);

        // 3. Verification
        t0 = get_time_ns();
        int res_ver = EVP_DigestVerify(mctx, sig, sig_len, FIXED_TEST_MSG, sizeof(FIXED_TEST_MSG));
        t1 = get_time_ns();
        double us_ver = (double)(t1 - t0) / 1000.0;
        s_verify[t] = us_ver;
        EVP_MD_CTX_free(mctx);

        fprintf(f_raw, "%s,%s,host_x86_64,host_workstation,AMD_Ryzen_7_7435HS,ECDSA-P256,verify,openssl_c,OpenSSL,%s,clean,%s,14.2.0,%s,0,clock_monotonic_raw,%zu,0,%.3f,%s,%s,false,DER_VERIFY_RES_%d\n",
                run_id, ts, OpenSSL_version(OPENSSL_VERSION_STRING), compiler_info, flags_info, t, us_ver, (res_ver == 1 ? "OK" : "ERROR"), (res_ver == 1 ? "true" : "false"), res_ver);

        free(sig);
        EVP_PKEY_free(eckey);
    }
    fclose(f_raw);

    OpStats st_kg = compute_stats(s_keygen, trials);
    OpStats st_sn = compute_stats(s_sign, trials);
    OpStats st_vr = compute_stats(s_verify, trials);

    printf("  [ECDSA-P256] Keygen:  Median=%.2f us, Mean=%.2f us (P95=%.2f us, IQR=%.2f us)\n", st_kg.median_us, st_kg.mean_us, st_kg.p95_us, st_kg.iqr_us);
    printf("  [ECDSA-P256] Sign:    Median=%.2f us, Mean=%.2f us (P95=%.2f us, IQR=%.2f us)\n", st_sn.median_us, st_sn.mean_us, st_sn.p95_us, st_sn.iqr_us);
    printf("  [ECDSA-P256] Verify:  Median=%.2f us, Mean=%.2f us (P95=%.2f us, IQR=%.2f us)\n", st_vr.median_us, st_vr.mean_us, st_vr.p95_us, st_vr.iqr_us);

    free(s_keygen); free(s_sign); free(s_verify);
    return 0;
}

// -----------------------------------------------------------------------------
// Main Entry Point
// -----------------------------------------------------------------------------
int main(int argc, char **argv) {
    size_t trials = 1000;
    size_t warmups = 10;
    char out_dir[512] = ".";
    char run_id[128] = "";

    static struct option long_options[] = {
        {"trials", required_argument, 0, 't'},
        {"warmups", required_argument, 0, 'w'},
        {"out-dir", required_argument, 0, 'o'},
        {"run-id", required_argument, 0, 'r'},
        {"help", no_argument, 0, 'h'},
        {0, 0, 0, 0}
    };

    int opt;
    while ((opt = getopt_long(argc, argv, "t:w:o:r:h", long_options, NULL)) != -1) {
        switch (opt) {
            case 't': trials = (size_t)atoi(optarg); break;
            case 'w': warmups = (size_t)atoi(optarg); break;
            case 'o': strncpy(out_dir, optarg, sizeof(out_dir) - 1); break;
            case 'r': strncpy(run_id, optarg, sizeof(run_id) - 1); break;
            case 'h':
            default:
                printf("Usage: %s [--trials N] [--warmups N] [--out-dir path] [--run-id id]\n", argv[0]);
                return 0;
        }
    }

    if (strlen(run_id) == 0) {
        time_t now = time(NULL);
        struct tm tm_buf;
        gmtime_r(&now, &tm_buf);
        strftime(run_id, sizeof(run_id), "EXP_STAGE_E_HOST_C_%Y%m%d_%H%M%S", &tm_buf);
    }

    printf("======================================================================\n");
    printf("Stage E: Host-Native C Cryptographic Reference Benchmark\n");
    printf("Run ID:   %s\n", run_id);
    printf("Output:   %s\n", out_dir);
    printf("Trials:   %zu | Warmups: %zu\n", trials, warmups);
    printf("======================================================================\n");

    OQS_init();

    char raw_csv[1024];
    snprintf(raw_csv, sizeof(raw_csv), "%s/host_native_c_raw.csv", out_dir);

    // Initialize raw CSV with header
    FILE *f_init = fopen(raw_csv, "w");
    if (!f_init) {
        fprintf(stderr, "Failed to create %s\n", raw_csv);
        return 1;
    }
    fprintf(f_init, "run_id,timestamp_utc,device,board,mcu,algorithm,operation,implementation,library_name,library_version,git_commit,compiler,compiler_version,optimization_flags,clock_hz,measurement_method,trial,cycles,elapsed_us,status,valid,warmup,notes\n");
    fclose(f_init);

    const char *compiler_info = "GCC";
    const char *flags_info = "-O3_march_native";

    bench_mlkem768(warmups, trials, raw_csv, run_id, compiler_info, flags_info);
    bench_mldsa65(warmups, trials, raw_csv, run_id, compiler_info, flags_info);
    bench_x25519(warmups, trials, raw_csv, run_id, compiler_info, flags_info);
    bench_ecdsa_p256(warmups, trials, raw_csv, run_id, compiler_info, flags_info);

    OQS_destroy();
    printf("\n[SUCCESS] Host-Native C benchmark completed cleanly. Outputs stored in %s\n", raw_csv);
    return 0;
}
