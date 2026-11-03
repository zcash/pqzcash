"""Search for primes a little above 2^64 with a cheap reduction and an NTT-friendly structure.

Candidates are p = 2^n + c or 2^n - c with 64 <= n <= 68 and c a signed sum of at most
`--weight` distinct powers of two below 2^`--max-c-bits`, so that the fold 2^n = -c (mod p)
costs a few shifts and adds, as Goldilocks's 2^64 = 2^32 - 1 does. An element then needs
n bits for p = 2^n - c and n + 1 bits for p = 2^n + c, whose elements reach past 2^n: a 64-bit
word plus that many flag bits less 64 (the `flags` column is the bit length less 64).

Each prime is reported with its 2-adicity s (the power of two dividing p - 1): Akita's ring
Z_q[X]/(X^64 + 1) needs q = 1 mod 128, s >= 7, and a hash-based NTT domain of 2^k elements
needs s >= k. Also reported: the smallest odd exponent coprime to p - 1, for a Poseidon
S-box, and whether the prime has the Goldilocks shape 2^n - 2^m + 1, whose 2-adicity is m.

Run: python prime-search.py [--min-adicity 7] [--weight 3] [--max-c-bits 48]
"""
import argparse
import itertools
import math

MR_BASES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)  # deterministic below 3.3e24


def is_prime(n):
    if n < 2:
        return False
    for q in MR_BASES:
        if n % q == 0:
            return n == q
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for a in MR_BASES:
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def two_adicity(m):
    return (m & -m).bit_length() - 1


def poseidon_alpha(p):
    a = 3
    while math.gcd(a, p - 1) != 1:
        a += 2
    return a


def signed_sums(weight, max_bits):
    """Positive values that are sums of at most `weight` distinct signed powers of two, with
    the expression that produced them, keyed by value; a value keeps its lightest expression."""
    out = {}
    exps = range(max_bits)
    for w in range(1, weight + 1):
        for es in itertools.combinations(exps, w):
            for signs in itertools.product((1, -1), repeat=w):
                if signs[-1] != 1:  # the top term must be positive for the sum to be positive
                    continue
                c = sum(s << e for s, e in zip(signs, es))
                if c <= 0:
                    continue
                expr = " ".join(f"{'+' if s > 0 else '-'} 2^{e}" for s, e in reversed(list(zip(signs, es))))
                if c not in out or len(expr) < len(out[c]):
                    out[c] = expr.lstrip("+ ")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--min-n", type=int, default=64)
    ap.add_argument("--max-n", type=int, default=68)
    ap.add_argument("--weight", type=int, default=3, help="largest signed-binary weight of c")
    ap.add_argument("--max-c-bits", type=int, default=48, help="c below 2^this")
    ap.add_argument("--min-adicity", type=int, default=7, help="smallest 2-adicity of p - 1 to report")
    args = ap.parse_args()

    cs = signed_sums(args.weight, args.max_c_bits)
    found = []
    for n in range(args.min_n, args.max_n + 1):
        for c, expr in cs.items():
            for sign, sym in ((1, "+"), (-1, "-")):
                p = (1 << n) + sign * c
                if p <= (1 << 64) or p >= (1 << args.max_n):
                    continue
                s = two_adicity(p - 1)
                if s < args.min_adicity:
                    continue
                if not is_prime(p):
                    continue
                weight = expr.count("2^")
                # p = 2^n - 2^m + 1 (Goldilocks's shape) or 2^n + 2^m + 1: p - 1 = 2^m (2^(n-m) -+ 1)
                shape = weight == 2 and expr.endswith(("- 2^0", "+ 2^0")) and (
                    (sym == "-" and expr.endswith("- 2^0")) or (sym == "+" and expr.endswith("+ 2^0")))
                found.append((s, n, sym, c, expr, p, poseidon_alpha(p), weight, shape))
    found.sort(key=lambda t: (-t[0], t[1], t[7], t[3]))

    def show(rows, title):
        print(f"\n{title}: {len(rows)}")
        print(f"{'2-adicity':>9}  {'bits':>4}  {'flags':>5}  {'weight':>6}  {'α':>5}  form")
        for s, n, sym, _, expr, p, alpha, weight, shape in rows:
            print(f"{s:9d}  {p.bit_length():4d}  {p.bit_length() - 64:5d}  {weight:6d}  {alpha:5d}  2^{n} {sym} ({expr})"
                  f"{'  2^n -+ 2^m + 1 shape' if shape else ''}")

    print(f"{len(found)} primes 2^n +/- c, {args.min_n} <= n <= {args.max_n}, weight(c) <= {args.weight}, "
          f"c < 2^{args.max_c_bits}, 2-adicity >= {args.min_adicity}")
    show([t for t in found if t[7] <= 2], "weight 1 or 2: the cheapest folds")
    show([t for t in found if t[5].bit_length() == 65][:12], "65 bits (one flag bit), best 2-adicity first")
    show(found[:12], "all forms, best 2-adicity first")
    g = (1 << 64) - (1 << 32) + 1
    print(f"\nreference: Goldilocks 2^64 - 2^32 + 1: 2-adicity {two_adicity(g - 1)}, α {poseidon_alpha(g)}")


if __name__ == "__main__":
    main()
