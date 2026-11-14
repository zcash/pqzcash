"""A toy of the draft frontend "BitZ over Akita": Booleanity by projection, and Pasta claims.

Follows "Efficient Booleanity Checking via Structured Modular Projections" (internal draft,
2026-09-23): a bit source s in F_q^n, q = 2^64 - 59, is certified Boolean by

  1. a structured random projection T (g independent tensor chains of balanced-ternary cores,
     section 5.1), whose revealed output y = T s has small centered integer energy, which bounds
     the integer energy E_x of the source (equation 1);
  2. the field identity sum_a s(a)(s(a) - 1) = 0, which with the bound lifts to the integers
     (Theorem 1), so every entry is 0 or 1;
  3. one quadratic sum-check (equation 6) that proves the revealed y is T s and the defect is
     zero together, under one batching vector lambda, ending in one evaluation s~(rho) that the
     polynomial commitment opens.

On top of that, the decoupled-modulus bridge of pasta-proof-size.md section 6.3 for the study's
"Pasta claims": a Pasta field element is 255 committed bits, and a linear claim <c, s> with
Pasta coefficients is proved as 32-bit limbs <c_j, s>, each an integer below q (no wrap, given
Booleanity and n <= 2^31), batched into the same sum-check; the verifier recomposes the limbs
over the integers and reduces modulo p.

The commitment is mocked: an oracle holds s and answers the one evaluation query. Akita's
opening proof, Fiat-Shamir, hiding and the certified projection parameters are what the real
system adds. Verifier randomness comes from a seeded RNG, standing in for AES counter mode.

Run: python booleanity_spike.py [seed]
"""
import math
import random
import sys

# ---- the fields -------------------------------------------------------------------------------
Q = 2**64 - 59                     # the draft's modulus; 2 is a non-residue (q = 5 mod 8)
P = 0x40000000000000000000000000000000224698fc094cf91b992d30ed00000001  # Pallas base field


def ctr(x):
    """The centered representative in [-(q-1)/2, (q-1)/2]."""
    x %= Q
    return x - Q if x > (Q - 1) // 2 else x


class E:
    """F_q[u]/(u^2 - 2), the challenge field; elements are (a, b) = a + b u."""
    __slots__ = ("a", "b")

    def __init__(self, a, b=0):
        self.a, self.b = a % Q, b % Q

    def __add__(self, o):
        o = lift(o)
        return E(self.a + o.a, self.b + o.b)

    def __sub__(self, o):
        o = lift(o)
        return E(self.a - o.a, self.b - o.b)

    def __mul__(self, o):
        o = lift(o)
        return E(self.a * o.a + 2 * self.b * o.b, self.a * o.b + self.b * o.a)

    __radd__, __rmul__ = __add__, __mul__

    def __rsub__(self, o):
        return lift(o) - self

    def __eq__(self, o):
        o = lift(o)
        return self.a == o.a and self.b == o.b

    def inv(self):
        # (a + bu)^-1 = (a - bu) / (a^2 - 2 b^2)
        n = pow((self.a * self.a - 2 * self.b * self.b) % Q, Q - 2, Q)
        return E(self.a * n, -self.b * n)

    def __repr__(self):
        return f"E({self.a}, {self.b})"


def lift(x):
    return x if isinstance(x, E) else E(x)


ZERO, ONE = E(0), E(1)


def rand_E(rng):
    return E(rng.randrange(Q), rng.randrange(Q))


# ---- multilinear extensions --------------------------------------------------------------------
def fold(table, r):
    """One sum-check fold: bind the lowest address bit to r. table has even length."""
    half = len(table) // 2
    return [table[2 * i] + (table[2 * i + 1] - table[2 * i]) * r for i in range(half)]


def mle_eval(table, point):
    """s~(point) for point in E^m, binding the lowest address bit first (as the sum-check does)."""
    t = [lift(x) for x in table]
    for r in point:
        t = fold(t, r)
    assert len(t) == 1
    return t[0]


# ---- the projection: grouped tensor chains (section 5.1) ---------------------------------------
class Chain:
    """One chain: cores A_i in {-1,0,1}^(c_i x c_{i-1} x d_i), entries with probabilities 1/4, 1/2, 1/4.

    The address of source index a is (a_1, ..., a_L) with a = a_1 + d_1 (a_2 + d_2 (...)), so that
    a_1 is the LOW address block, which the sum-check binds first.
    """

    def __init__(self, rng, d, c):
        assert len(d) == len(c)
        self.d, self.c = d, [1] + list(c)
        self.cores = []
        for i in range(len(d)):
            ci, cprev, di = self.c[i + 1], self.c[i], d[i]
            self.cores.append([[[rng.choice((-1, 0, 0, 1)) for _ in range(di)] for _ in range(cprev)]
                               for _ in range(ci)])

    def apply(self, s):
        """y = T s in F_q, by the recurrence F_i(u, a_{i+1..}) = sum_{v, a_i} A_i(u, v, a_i) F_{i-1}(v, a_i, a_{i+1..})."""
        n = len(s)
        f = [[x % Q for x in s]]            # F_0 with one channel: f[v][address]
        rest = n
        for i, core in enumerate(self.cores):
            di, ci, cprev = self.d[i], self.c[i + 1], self.c[i]
            rest //= di
            nxt = []
            for u in range(ci):
                row = []
                for addr in range(rest):      # the remaining address tuple (a_{i+1}, ...)
                    acc = 0
                    for v in range(cprev):
                        prev = f[v]
                        base = addr * di
                        A = core[u][v]
                        for ai in range(di):
                            coef = A[ai]
                            if coef:
                                acc += prev[base + ai] if coef > 0 else -prev[base + ai]
                    row.append(acc % Q)
                nxt.append(row)
            f = nxt
        assert rest == 1
        return [f[u][0] for u in range(self.c[-1])]

    def transpose_apply(self, lam):
        """T^T lambda as an n-table in E: contract lambda back through the cores, expanding addresses.

        beta_L = lambda; beta_{i-1}(v, a_i, a_{i+1..}) = sum_u beta_i(u, a_{i+1..}) A_i(u, v, a_i).
        """
        beta = {(): list(lam)}   # suffix address tuple -> channel vector
        for i in reversed(range(len(self.cores))):
            core, di, ci, cprev = self.cores[i], self.d[i], self.c[i + 1], self.c[i]
            nxt = {}
            for suffix, vec in beta.items():
                for ai in range(di):
                    out = []
                    for v in range(cprev):
                        acc = ZERO
                        for u in range(ci):
                            coef = core[u][v][ai]
                            if coef:
                                acc = acc + vec[u] if coef > 0 else acc - vec[u]
                        out.append(acc)
                    nxt[(ai,) + suffix] = out
            beta = nxt
        n = math.prod(self.d)
        table = [None] * n
        for addr_tuple, vec in beta.items():
            a = 0
            for ai, di in zip(reversed(addr_tuple), reversed(self.d)):
                a = a * di + ai
            table[a] = vec[0]
        return table

    def eval_transpose(self, lam, rho):
        """w_lambda~(rho) for w_lambda = T^T lambda, by the verifier's backward contraction
        (section 4.1): at core i, C_i(u, a_i) = sum_v beta_i(v) A_i(v, u, a_i), then fold the
        address block a_i at the challenges that bound it. Costs sum_i c_i c_{i-1} d_i field
        operations instead of n.
        """
        bits_of = [int(math.log2(di)) for di in self.d]
        assert all(1 << b == di for b, di in zip(bits_of, self.d))
        offsets = [sum(bits_of[:i]) for i in range(len(self.d))]
        beta = list(lam)
        for i in reversed(range(len(self.cores))):
            core, di, ci, cprev = self.cores[i], self.d[i], self.c[i + 1], self.c[i]
            block = rho[offsets[i]:offsets[i] + bits_of[i]]
            nxt = []
            for v in range(cprev):
                col = []
                for ai in range(di):
                    acc = ZERO
                    for u in range(ci):
                        coef = core[u][v][ai]
                        if coef:
                            acc = acc + beta[u] if coef > 0 else acc - beta[u]
                    col.append(acc)
                nxt.append(mle_eval(col, block))
            beta = nxt
        assert len(beta) == 1
        return beta[0]


def energy(values):
    return sum(ctr(v) ** 2 for v in values)


# ---- the certificate inequalities (sections 2 and 5.1), as numbers --------------------------------
K_CJL, T_CJL = 681 / 1250, 25123 / 10000


def lower_tail(c_list, rho, steps=600, lo=-40.0, hi=12.0):
    """Pr[prod_i Z_{c_i} < rho] for Z_c = (b_c - X)^+, X ~ Exp(t), b_c = -c log K / t, by a
    discretized convolution of the densities of log Z_c on a grid, with the point mass at
    Z_c = 0 (X >= b_c) kept separately. This is the single-chain comparison law of equation 13;
    its g-th power bounds the projection error for a source of energy at least Q."""
    dz = (hi - lo) / (steps - 1)
    grid = [lo + k * dz for k in range(steps)]            # log z
    total_zero, dens = 0.0, [0.0] * steps
    for i, c in enumerate(c_list):
        b = -c * math.log(K_CJL) / T_CJL
        p_zero = math.exp(-T_CJL * b)                     # Pr[X >= b] = K^c
        # the mass of log Z in each cell, for Z = b - X in (0, b): f_Z(z) = t e^{-t(b - z)}
        f = [T_CJL * math.exp(-T_CJL * (b - math.exp(l))) * math.exp(l) * dz if math.exp(l) < b else 0.0
             for l in grid]
        total_zero = total_zero + p_zero - total_zero * p_zero
        dens = f if i == 0 else _logconv(dens, f, lo, dz)
    cut = math.log(rho) if rho > 0 else -math.inf
    mass_below = sum(m for l, m in zip(grid, dens) if l < cut)
    return min(1.0, total_zero + mass_below)


def _logconv(f, g, lo, dz):
    """Convolution of two mass vectors on the same log grid (the product of the variables),
    mapped back onto that grid: cell i + j of the product holds log z = 2 lo + (i + j) dz."""
    steps = len(f)
    out = [0.0] * steps
    shift = round(lo / dz)                                # 2 lo + k dz = lo + (k + shift) dz
    for i, fi in enumerate(f):
        if fi == 0.0:
            continue
        for j, gj in enumerate(g):
            k = i + j + shift
            if 0 <= k < steps:
                out[k] += fi * gj
    return out


# ---- the protocol -------------------------------------------------------------------------------
class Oracle:
    """Stands in for the polynomial commitment: answers one evaluation of s~ over E."""

    def __init__(self, s):
        self._s = list(s)
        self.queries = 0

    def open(self, rho):
        self.queries += 1
        return mle_eval(self._s, rho)


def prover_sumcheck(s, w, rng_verifier, m):
    """The quadratic sum-check of sum_a s(a)(s(a) - 1) + s(a) w(a) (equation 6). Returns the
    transcript: per round the three evaluations g_j(0), g_j(1), g_j(2), and the challenges."""
    S = [lift(x) for x in s]
    W = list(w)
    rounds, challenges = [], []
    for _ in range(m):
        half = len(S) // 2
        g0 = g1 = g2 = ZERO
        for i in range(half):
            s0, s1 = S[2 * i], S[2 * i + 1]
            w0, w1 = W[2 * i], W[2 * i + 1]
            g0 = g0 + s0 * (s0 - ONE + w0)
            g1 = g1 + s1 * (s1 - ONE + w1)
            s2, w2 = s1 + s1 - s0, w1 + w1 - w0           # the linear extensions at X = 2
            g2 = g2 + s2 * (s2 - ONE + w2)
        rounds.append((g0, g1, g2))
        r = rand_E(rng_verifier)
        challenges.append(r)
        S, W = fold(S, r), fold(W, r)
    return rounds, challenges


def eval_quadratic(g0, g1, g2, x):
    """The degree-2 polynomial through (0, g0), (1, g1), (2, g2), at x (Lagrange)."""
    inv2 = E(2).inv()
    l0 = (x - ONE) * (x - E(2)) * inv2
    l1 = ZERO - x * (x - E(2))
    l2 = x * (x - ONE) * inv2
    return g0 * l0 + g1 * l1 + g2 * l2


def verify_sumcheck(rounds, challenges, claim):
    for (g0, g1, g2), r in zip(rounds, challenges):
        if not (g0 + g1 == claim):
            return None
        claim = eval_quadratic(g0, g1, g2, r)
    return claim


def run(seed=1, n_log=12, d=(256, 4, 4), c=(8, 8, 6), g=4, limb_bits=32, cheat=None, verbose=True):
    rng = random.Random(seed)             # the prover's and the setup's randomness
    vrng = random.Random(seed + 10**6)    # the verifier's: the projection cores, lambda, rho
    n = 1 << n_log
    assert math.prod(d) == n

    # 1. The source: 255 bits of a Pasta element, then random bits (honest), or a cheat.
    value = rng.randrange(P)
    bits = [(value >> i) & 1 for i in range(255)] + [rng.randrange(2) for _ in range(n - 255)]
    s = list(bits)
    if cheat == "defect":
        # Two large entries whose defects cancel modulo q: x2^2 - x2 + D1 = 0 has a root for
        # about half of the x1; the source then passes the field identity but is not Boolean.
        while True:
            x1 = rng.randrange(2, Q - 1)
            D1 = (x1 * (x1 - 1)) % Q
            disc = (1 - 4 * D1) % Q
            root = pow(disc, (Q + 1) // 4, Q) if Q % 4 == 3 else sqrt_mod(disc)
            if root is not None and (root * root) % Q == disc:
                x2 = ((1 + root) * pow(2, Q - 2, Q)) % Q
                break
        s[300], s[301] = x1, x2
        assert sum(x * (x - 1) for x in s) % Q == 0
    oracle = Oracle(s)

    # 2. The verifier samples the projection; the prover reveals y = T s.
    chains = [Chain(vrng, d, c) for _ in range(g)]
    y = [ch.apply(s) for ch in chains]
    if cheat == "y":
        y[0][0] = (y[0][0] + 1) % Q

    # 3. The energy check against the integer bound C, from the honest moment bound (14) at p = 1.
    e_hon = n                                   # every entry a bit: E_x <= n
    growth = math.prod(ci / 2 for ci in c)
    C = math.ceil(2**40 * g * e_hon * growth)   # Markov with p = 1; the draft uses higher moments
    energies = [energy(yc) for yc in y]
    energy_ok = all(e <= C for e in energies)

    # 4. Theorem 1's condition and the bound the projection must certify.
    #    Q0 is the energy threshold above which the projection rejects (eq. 1 and 13).
    Q0_max = int((math.sqrt(4 * Q + n) - math.sqrt(n)) ** 2 / 4)   # largest Q0 with Q0 + sqrt(n Q0) < q
    rho = (C + 1) / Q0_max                                           # eq. 13 at Q = Q0_max
    eps_single = lower_tail(list(c), rho)
    eps_proj = eps_single ** g

    # 5. The Pasta claim: the first 255 bits as 32-bit limbs, each an integer inner product.
    limbs = []
    for j in range(math.ceil(255 / limb_bits)):
        cj = [0] * n
        for i in range(j * limb_bits, min(255, (j + 1) * limb_bits)):
            cj[i] = 1 << (i - j * limb_bits)
        limbs.append(cj)
    v_limbs = [sum(cj[i] * s[i] for i in range(n)) % Q for cj in limbs]   # integers below 2^32
    if cheat == "claim":
        v_limbs[0] = (v_limbs[0] + 1) % Q

    # 6. The batching vector lambda over the revealed coordinates and the limb claims, and the
    #    public weight table w = T^T lambda + sum_j mu_j c_j (materialized here; the verifier
    #    evaluates it at rho by contraction).
    lam = [[rand_E(vrng) for _ in range(c[-1])] for _ in range(g)]
    mu = [rand_E(vrng) for _ in limbs]
    w = [ZERO] * n
    for ch, lc in zip(chains, lam):
        for i, x in enumerate(ch.transpose_apply(lc)):
            w[i] = w[i] + x
    for cj, mj in zip(limbs, mu):
        for i in range(n):
            if cj[i]:
                w[i] = w[i] + mj * cj[i]
    claim = ZERO
    for yc, lc in zip(y, lam):
        for yi, li in zip(yc, lc):
            claim = claim + li * yi
    for vj, mj in zip(v_limbs, mu):
        claim = claim + mj * vj

    # 7. The sum-check and the final opening.
    rounds, rho_pt = prover_sumcheck(s, w, vrng, n_log)
    final = verify_sumcheck(rounds, rho_pt, claim)
    v = oracle.open(rho_pt)
    w_at_rho = ZERO
    for ch, lc in zip(chains, lam):
        w_at_rho = w_at_rho + ch.eval_transpose(lc, rho_pt)
    for cj, mj in zip(limbs, mu):
        w_at_rho = w_at_rho + mj * mle_eval(cj, rho_pt)
    assert w_at_rho == mle_eval(w, rho_pt), "the contraction disagrees with the materialized table"
    sumcheck_ok = final is not None and final == v * (v - ONE + w_at_rho)

    # 8. Recompose the limbs over the integers and reduce modulo p.
    V = sum(vj << (j * limb_bits) for j, vj in enumerate(v_limbs))
    claim_ok = V % P == value

    accepted = energy_ok and sumcheck_ok
    if verbose:
        print(f"n = 2^{n_log}, chains g = {g}, cores d = {d}, c = {c}: {g * c[-1]} revealed coordinates")
        print(f"  honest energy bound n = {n}; verifier bound C = 2^{math.log2(C):.1f}; "
              f"chain energies 2^{[round(math.log2(max(e, 1)), 1) for e in energies]}")
        print(f"  Theorem 1 admits Q0 up to 2^{math.log2(Q0_max):.2f} (q = 2^64 - 59, n = 2^{n_log})")
        print(f"  comparison-law error for E_x >= Q0: single chain {eps_single:.3g}, all chains {eps_proj:.3g}"
              f"  (the draft's 4 x (43,43,43,43,40) at n = 2^27 reaches 2^-136)")
        print(f"  sum-check: {n_log} rounds x 3 E elements, 1 opening; verifier contraction over "
              f"{sum(ci * cp * di for ci, cp, di in zip(chains[0].c[1:], chains[0].c[:-1], d)) * g} coefficients")
        print(f"  energy check {'ok' if energy_ok else 'FAIL'}; sum-check {'ok' if sumcheck_ok else 'FAIL'}; "
              f"Pasta claim recomposed {'ok' if claim_ok else 'FAIL'}; cheat = {cheat}")
    return accepted, claim_ok


def sqrt_mod(a):
    """Tonelli-Shanks for q = 5 mod 8 is not needed: q = 2^64 - 59 = 5 mod 8, use Atkin's formula."""
    a %= Q
    if a == 0:
        return 0
    if pow(a, (Q - 1) // 2, Q) != 1:
        return None
    # Atkin, for q = 5 mod 8
    v = pow(2 * a, (Q - 5) // 8, Q)
    i = (2 * a * v * v) % Q
    r = (a * v * (i - 1)) % Q
    return r


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    print("honest prover:")
    ok, claim_ok = run(seed)
    assert ok and claim_ok
    print("\ncheating source that passes the field identity (two large cancelling entries):")
    ok, _ = run(seed, cheat="defect")
    assert not ok
    print("\nprover lies about a revealed projection coordinate:")
    ok, _ = run(seed, cheat="y")
    assert not ok
    print("\nprover lies about a Pasta limb:")
    ok, _ = run(seed, cheat="claim")
    assert not ok
    print("\nall four behaved as expected")
