/* Rounded-Gaussian sampling rate on one core, for the zero-knowledge mask.
 *
 * Draws N coordinates of a rounded continuous Gaussian of width sigma as the user's masking
 * fold would: ChaCha20 (RFC 8439) randomness, two uniforms of 53 bits per Box-Muller pair,
 * Sheppard's correction sigma' = sigma - 1/(24 sigma) (Jeudy, ePrint 2026/2583), the scaling,
 * the tail check |x| <= 14 sigma, and rounding to the nearest integer. A coordinate whose
 * distance from a half-integer is within the double computation's error bound is counted as
 * undecided; the fold would refine those few in higher precision, which costs nothing
 * measurable at one coordinate in about 2^25.
 *
 * Build and run (one core, the machine idle, a laptop on mains):
 *   clang -O3 -o work/sampler-bench scripts/sampler-bench.c -lm
 *   work/sampler-bench [log2 N] [repetitions] [log2 sigma] [aes]
 * Defaults: N = 2^22 (the fold's), 8 repetitions, sigma = 2^22.9 (the page's), ChaCha20; a
 * fourth argument "aes" draws the randomness from AES-128-CTR through CommonCrypto instead,
 * which on Apple silicon runs on the AES instructions (macOS only). Prints the nanoseconds a
 * coordinate for the whole path and for the randomness alone.
 */
#ifdef __APPLE__
#include <CommonCrypto/CommonCryptor.h>
#endif
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define ROTL(a, b) (((a) << (b)) | ((a) >> (32 - (b))))
#define QR(a, b, c, d) \
    a += b; d ^= a; d = ROTL(d, 16); c += d; b ^= c; b = ROTL(b, 12); \
    a += b; d ^= a; d = ROTL(d, 8);  c += d; b ^= c; b = ROTL(b, 7);

static void chacha20_block(const uint32_t in[16], uint32_t out[16]) {
    uint32_t x[16];
    memcpy(x, in, sizeof x);
    for (int i = 0; i < 10; i++) {
        QR(x[0], x[4], x[8], x[12]) QR(x[1], x[5], x[9], x[13])
        QR(x[2], x[6], x[10], x[14]) QR(x[3], x[7], x[11], x[15])
        QR(x[0], x[5], x[10], x[15]) QR(x[1], x[6], x[11], x[12])
        QR(x[2], x[7], x[8], x[13]) QR(x[3], x[4], x[9], x[14])
    }
    for (int i = 0; i < 16; i++) out[i] = x[i] + in[i];
}

typedef struct {
    uint32_t state[16];
    uint64_t words[8];
    int next;
    int aes;  /* 1: AES-128-CTR through CommonCrypto in place of ChaCha20 */
#ifdef __APPLE__
    CCCryptorRef cryptor;
    uint64_t aes_words[4096];
    int aes_next;
#endif
} rng_t;

static void rng_init(rng_t *r, uint64_t seed) {
    static const uint32_t sigma[4] = {0x61707865, 0x3320646e, 0x79622d32, 0x6b206574};
    memcpy(r->state, sigma, sizeof sigma);
    for (int i = 4; i < 12; i++) r->state[i] = (uint32_t)(seed * 0x9e3779b97f4a7c15ULL >> (i * 5));
    r->state[12] = 0;
    r->state[13] = r->state[14] = r->state[15] = 0;
    r->next = 8;
    r->aes = 0;
#ifdef __APPLE__
    uint8_t key[16], iv[16] = {0};
    for (int i = 0; i < 16; i++) key[i] = (uint8_t)(seed >> (i * 4));
    if (CCCryptorCreateWithMode(kCCEncrypt, kCCModeCTR, kCCAlgorithmAES, ccNoPadding, iv, key, 16,
                                NULL, 0, 0, kCCModeOptionCTR_BE, &r->cryptor) != kCCSuccess)
        r->cryptor = NULL;
    r->aes_next = 4096;
#endif
}

static inline uint64_t rng_u64(rng_t *r) {
#ifdef __APPLE__
    if (r->aes) {
        if (r->aes_next == 4096) {
            static const uint64_t zeros[4096];
            size_t moved;
            CCCryptorUpdate(r->cryptor, zeros, sizeof zeros, r->aes_words, sizeof r->aes_words, &moved);
            r->aes_next = 0;
        }
        return r->aes_words[r->aes_next++];
    }
#endif
    if (r->next == 8) {
        uint32_t out[16];
        chacha20_block(r->state, out);
        r->state[12]++;
        memcpy(r->words, out, sizeof r->words);
        r->next = 0;
    }
    return r->words[r->next++];
}

static double now_s(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (double)t.tv_sec + 1e-9 * (double)t.tv_nsec;
}

int main(int argc, char **argv) {
    int log_n = argc > 1 ? atoi(argv[1]) : 22;
    int reps = argc > 2 ? atoi(argv[2]) : 8;
    double log_sigma = argc > 3 ? atof(argv[3]) : 22.9;
    uint64_t n = 1ULL << log_n;
    double sigma = pow(2.0, log_sigma);
    double sigma_c = sigma - 1.0 / (24.0 * sigma);  /* Sheppard's correction */
    double tail = 14.0 * sigma;
    double eps = ldexp(1.0, -50);  /* relative error bound of the double path, generous */
    const double two_pi = 6.283185307179586;
    const double scale53 = ldexp(1.0, -53);

    rng_t rng;
    rng_init(&rng, 0x5eed);
#ifdef __APPLE__
    rng.aes = argc > 4 && strcmp(argv[4], "aes") == 0 && rng.cryptor != NULL;
#endif
    int64_t checksum = 0;
    uint64_t undecided = 0, rejected = 0;

    /* Randomness alone: the u64 draws a coordinate needs (one, since a pair uses two). */
    double t0 = now_s();
    uint64_t acc = 0;
    for (uint64_t i = 0; i < n * (uint64_t)reps; i++) acc ^= rng_u64(&rng);
    double t_rng = now_s() - t0;

    /* The whole path. */
    double t_total = 0;
    for (int rep = 0; rep < reps; rep++) {
        double t1 = now_s();
        for (uint64_t i = 0; i < n; i += 2) {
            uint64_t a = rng_u64(&rng), b = rng_u64(&rng);
            double u1 = (double)((a >> 11) + 1) * scale53;  /* in (0, 1] */
            double u2 = (double)(b >> 11) * scale53;        /* in [0, 1) */
            double r = sqrt(-2.0 * log(u1));
            double z0 = r * cos(two_pi * u2), z1 = r * sin(two_pi * u2);
            double x[2] = {sigma_c * z0, sigma_c * z1};
            for (int k = 0; k < 2; k++) {
                double v = x[k];
                if (fabs(v) > tail) { rejected++; continue; }
                double y = rint(v);
                double f = fabs(v - floor(v) - 0.5);  /* distance from the half-integer */
                if (f < fabs(v) * eps) undecided++;
                checksum += (int64_t)y;
            }
        }
        t_total += now_s() - t1;
    }
    double per = 1e9 * t_total / ((double)n * reps);
    double per_rng = 1e9 * t_rng / ((double)n * reps);
    printf("N = 2^%d, %d repetitions, sigma = 2^%.1f\n", log_n, reps, log_sigma);
    printf("randomness alone: %.2f ns a coordinate (one %s word each)\n", per_rng, rng.aes ? "AES-128-CTR" : "ChaCha20");
    printf("whole path:       %.2f ns a coordinate\n", per);
    printf("undecided %llu of %llu (2^%.1f), rejected %llu, checksum %lld, acc %llx\n",
           (unsigned long long)undecided, (unsigned long long)(n * reps),
           undecided ? log2((double)undecided / ((double)n * reps)) : -INFINITY,
           (unsigned long long)rejected, (long long)checksum, (unsigned long long)acc);
    return 0;
}
