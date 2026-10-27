#include <stdio.h>
#include <oqs/oqs.h>
#include <openssl/evp.h>
#include <openssl/crypto.h>

int main(void) {
    OQS_init();
    printf("liboqs version: %s\n", OQS_version());
    printf("ML-KEM-768 enabled: %d\n", OQS_KEM_alg_is_enabled(OQS_KEM_alg_ml_kem_768));
    printf("ML-DSA-65 enabled: %d\n", OQS_SIG_alg_is_enabled(OQS_SIG_alg_ml_dsa_65));
    printf("OpenSSL version: %s\n", OpenSSL_version(OPENSSL_VERSION_STRING));
    OQS_destroy();
    return 0;
}
