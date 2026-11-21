// Throughput of a GF(2^128) multiplication by the carry-less multiply instruction against a
// 64-bit modular multiplication, the model's word multiplication, on one core. The model's
// CLMULS table counts 64-bit carry-less multiplications per binary-field multiplication and
// takes each as one word multiplication; this measures how many word multiplications a
// binary-field multiplication really costs on the machine at hand.
//
// GF(2^128) is taken modulo x^128 + x^7 + x^2 + x + 1 (the GCM polynomial): three carry-less
// multiplications by Karatsuba and three more for the reduction, all through PMULL. The 64-bit
// field is the Goldilocks prime 2^64 - 2^32 + 1 with its usual reduction. Both run eight
// independent chains, so the figures are throughputs, which is what a sum-check prover sees.
//
// Build and run on an Apple Silicon Mac, on mains power, with nothing else running:
//   cc -O3 -mcpu=native -o work/clmul-bench scripts/clmul-bench.c && work/clmul-bench
#include <arm_neon.h>
#include <stdint.h>
#include <stdio.h>
#include <time.h>

// The low lanes of two vectors, multiplied carry-less: PMULL on the registers as they are.
static inline uint64x2_t pmull_lo(uint64x2_t a, uint64x2_t b) {
    return vreinterpretq_u64_p128(vmull_p64(vgetq_lane_p64(vreinterpretq_p64_u64(a), 0),
                                            vgetq_lane_p64(vreinterpretq_p64_u64(b), 0)));
}

static inline uint64x2_t gf128_mul(uint64x2_t a, uint64x2_t b) {
    uint64x2_t lo = pmull_lo(a, b);
    uint64x2_t hi = vreinterpretq_u64_p128(vmull_high_p64(vreinterpretq_p64_u64(a), vreinterpretq_p64_u64(b)));
    // Karatsuba's cross term from a0 ^ a1 and b0 ^ b1, formed in the vector unit.
    uint64x2_t ax = veorq_u64(a, vextq_u64(a, a, 1));
    uint64x2_t bx = veorq_u64(b, vextq_u64(b, b, 1));
    uint64x2_t mid = pmull_lo(ax, bx);
    mid = veorq_u64(mid, veorq_u64(lo, hi));
    // The 256-bit product: lo + mid x^64 + hi x^128.
    uint64x2_t zero = vdupq_n_u64(0);
    lo = veorq_u64(lo, vextq_u64(zero, mid, 1));
    hi = veorq_u64(hi, vextq_u64(mid, zero, 1));
    // hi x^128 = (h1 x^64 + h0) x^128, and x^128 = x^7 + x^2 + x + 1 = 0x87.
    const uint64x2_t c = vdupq_n_u64(0x87);
    uint64x2_t t1 = vreinterpretq_u64_p128(vmull_high_p64(vreinterpretq_p64_u64(hi), vreinterpretq_p64_u64(c)));  // h1 0x87 x^64
    uint64x2_t t2 = pmull_lo(hi, c);  // h0 0x87
    // t1's high half is above x^128 again: fold it once more, it is at most 7 bits.
    uint64x2_t t3 = vreinterpretq_u64_p128(vmull_high_p64(vreinterpretq_p64_u64(t1), vreinterpretq_p64_u64(c)));
    uint64x2_t r = veorq_u64(lo, t2);
    r = veorq_u64(r, vextq_u64(zero, t1, 1));
    return veorq_u64(r, t3);
}

static inline uint64_t gl_mul(uint64_t a, uint64_t b) {
    const uint64_t P = 0xffffffff00000001ULL;
    __uint128_t p = (__uint128_t)a * b;
    uint64_t lo = (uint64_t)p, hi = (uint64_t)(p >> 64);
    uint64_t hi_hi = hi >> 32, hi_lo = hi & 0xffffffffULL;
    // lo - hi_hi, then + hi_lo (2^32 - 1), each with its wrap.
    uint64_t r = lo - hi_hi;
    if (lo < hi_hi) r += P;
    uint64_t t = (hi_lo << 32) - hi_lo;
    uint64_t s = r + t;
    if (s < r) s -= P;
    if (s >= P) s -= P;
    return s;
}

static double now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

#ifndef CHAINS
#define CHAINS 8
#endif

int main(void) {
    const long N = (1L << 30) / CHAINS;
    // GF(2^128): CHAINS independent chains.
    uint64x2_t x[CHAINS], m[CHAINS];
    for (int i = 0; i < CHAINS; i++) {
        x[i] = (uint64x2_t){0x0123456789abcdefULL ^ i, 0xfedcba9876543210ULL + i};
        m[i] = (uint64x2_t){0x1111111122222222ULL * (i + 1), 0x3333333344444444ULL ^ i};
    }
    double t0 = now();
    for (long n = 0; n < N; n++)
#pragma clang loop unroll(full)
        for (int i = 0; i < CHAINS; i++) x[i] = gf128_mul(x[i], m[i]);
    double t1 = now();
    uint64_t sink = 0;
    for (int i = 0; i < CHAINS; i++) sink ^= vgetq_lane_u64(x[i], 0) ^ vgetq_lane_u64(x[i], 1);
    double gf_ns = (t1 - t0) * 1e9 / ((double)CHAINS * N);
    // Goldilocks: eight chains.
    uint64_t y[CHAINS], k[CHAINS];
    for (int i = 0; i < CHAINS; i++) {
        y[i] = 0x0123456789abcdefULL ^ i;
        k[i] = 0x9e3779b97f4a7c15ULL * (i + 1);
    }
    t0 = now();
    for (long n = 0; n < N; n++)
#pragma clang loop unroll(full)
        for (int i = 0; i < CHAINS; i++) y[i] = gl_mul(y[i], k[i]);
    t1 = now();
    for (int i = 0; i < CHAINS; i++) sink ^= y[i];
    double gl_ns = (t1 - t0) * 1e9 / ((double)CHAINS * N);
    printf("GF(2^128) multiplication: %.2f ns, %.2e per second (6 carry-less multiplications each)\n", gf_ns, 1e9 / gf_ns);
    printf("Goldilocks multiplication: %.2f ns, %.2e per second\n", gl_ns, 1e9 / gl_ns);
    printf("word multiplications per GF(2^128) multiplication: %.2f (the model's CLMULS[128] is 4)\n", gf_ns / gl_ns);
    printf("sink %llx\n", (unsigned long long)sink);
    return 0;
}
