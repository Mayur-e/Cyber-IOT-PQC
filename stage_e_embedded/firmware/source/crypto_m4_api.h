#ifndef CRYPTO_M4_API_H
#define CRYPTO_M4_API_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ML-KEM-768 parameters (NIST FIPS 203) */
#define MLKEM768_PUBLICKEYBYTES   1184
#define MLKEM768_SECRETKEYBYTES   2400
#define MLKEM768_CIPHERTEXTBYTES  1088
#define MLKEM768_SSBYTES          32

/* ML-DSA-65 parameters (NIST FIPS 204) */
#define MLDSA65_PUBLICKEYBYTES    1952
#define MLDSA65_SECRETKEYBYTES    4032
#define MLDSA65_SIGBYTES          3309

/* X25519 parameters (RFC 7748) */
#define X25519_KEYBYTES           32
#define X25519_SSBYTES            32

/* ECDSA P-256 parameters (NIST FIPS 186-5) */
#define ECDSA_P256_PUBLICKEYBYTES 64
#define ECDSA_P256_SECRETKEYBYTES 32
#define ECDSA_P256_SIGBYTES       64

/* Return status codes */
#define CRYPTO_SUCCESS            0
#define CRYPTO_ERROR_KEYGEN      -1
#define CRYPTO_ERROR_ENC         -2
#define CRYPTO_ERROR_DEC         -3
#define CRYPTO_ERROR_SIGN        -4
#define CRYPTO_ERROR_VERIFY      -5
#define CRYPTO_ERROR_MEMCMP      -6

#ifdef __cplusplus
}
#endif

#endif /* CRYPTO_M4_API_H */
