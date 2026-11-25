# The soundness obligations behind Kishu: the statements

Statements drafted 2026-11-14, to be reviewed before any proof is attempted. Sources: the
Booleanity-by-projection draft "Efficient Booleanity Checking via Structured Modular Projections"
of 2026-09-23 (§2 Theorem 1, §4 equation 6, §5 the certificate), and
[`spike/booleanity_spike.py`](spike/booleanity_spike.py) (the limb protocol). The Pasta-claims
Akita variant has a different obligation, which is not Kishu's; it is the subject of
[The soundness obligation behind the Pasta-claims Akita variant](pasta-q64-soundness.md).

## 1. Kishu's obligations

Kishu's claim field is $\mathbb{F}_q$ with $q = 2^{64}-59$, which is Akita's own 64-bit
commitment modulus. There is no decoupling of the commitment modulus from the claim field: the
digits are committed as any small digit vector is, bits where the circuit needs bits and
Akita's own base-8 digits for integer words, and the evaluation claims are
Akita's ordinary claims at the 64-bit profile, over the quadratic extension
$E = \mathbb{F}_q[u]/(u^2-2)$ that the draft's sum-check uses. The Pasta values never reach the
commitment: a value's digits are read as eight 32-bit limbs
$v_j = \langle c_j, s\rangle$, proved as linear claims in the same sum-check, and the verifier
recomposes $V = \sum_j 2^{32j} v_j$ over the integers and reduces modulo $p$.

So Kishu's obligations are: (B1) Akita's knowledge soundness at its 64-bit profile with claims
in $E$, which the paper proves in the classical ROM; (B2) the soundness of the range check,
the Booleanity check on the bit positions and Akita's paired predicate on the dibits and
tribits; and (B4), for the fingerprint route only, the soundness of checking an integer
relation in three instances over random 52-bit primes. (B4) is BitZ's argument, separate from
the range check. The limb route asks nothing more of the proof system. The correctness of its
Pasta arithmetic is a circuit-level matter: each constraint's sides are kept within a range no
larger than $q$. Lemma B3 below only states what the limb reading of a value means. The
PCS frontier page's Kishu paragraph once said that
Kishu carries "the same open soundness obligation" as the Pasta-claims Akita variant, whose
claims are $\mathbb{F}_p$ values over the 64-bit commitment. It was corrected on 2026-11-14
(commit c8aa3302edbb5377e925a85e6552223c53f1934b): that variant's obligation, Theorem A on its
own page, is Kishu's fallback's, not Kishu's.

Which Booleanity check (B2) is about. The frontier's Kishu rows use the conventional weighted
sum-check, the draft's §3 baseline, not its projection. In recursion the projection's verifier
is the merge circuit's work, a committed digit per sampled coefficient at the least. The
projection is therefore ahead only from rank 23 at the draft's geometry. Separately, ranks of
21 and up are too slow for a Zcash transaction, which puts the frontier's Kishu rows at 19
and 20, where the sum-check form wins. (B2) is then the ordinary sum-check's soundness, with
no integer lift. The draft's projection certificate, with its CertifiedJL estimates and its
numerical check, is not on Kishu's path, so formally verifying the projection is not a
blocker for Zcash's use of Kishu (the user's decision, 2026-11-17). The projection form's
statement is kept as Theorem B′ below, for a verifier that runs natively.

## 2. The no-wrap lemma

**Lemma L (no wrap).** Let $F$ be a prime field of size $r$, and let $u, v \in \mathbb{Z}$ with
$\lvert u \rvert, \lvert v \rvert < r/2$. If $u \equiv v \pmod r$ then $u = v$.

This is the same Lemma L as on the Pasta-claims variant's page, repeated so that each page
stands alone; here only Theorem B′ needs it. Theorem 1 of the draft is Lemma L applied to
$u = D_x = \sum_i x_i(x_i-1)$ and $v = 0$, with the bound
$0 \le D_x \le E_x + \sqrt{nE_x} < Q_0 + \sqrt{nQ_0} < q$ from Cauchy–Schwarz.

## 3. Kishu's statements

**Lemma B3 (limbs).** Let $s \in \{0,1\}^n$ with $n \le 2^{31}$, and let $c_j \in \mathbb{Z}^n$
have entries $2^{i - 32j}$ at positions $i \in [32j, 32j+32)$ and zero elsewhere. Then the
integer $v_j = \langle c_j, s \rangle$ satisfies $0 \le v_j < 2^{32}$, so its value in
$\mathbb{F}_q$ is its integer value, $V = \sum_{j} 2^{32j} v_j$ is the integer whose bits are
$s_0, \ldots, s_{254}$, and $V \bmod p$ is the Pasta value those bits encode.

Proof sketch: each $v_j$ is a sum of at most 32 distinct powers of two below $2^{32}$, and
$2^{32} < q$; Lemma L is not even needed, the integer is below $q$ outright. The hypothesis
$n \le 2^{31}$ is only what makes the general linear claims of equation 6 (the projection rows,
entries in $\{-1,0,1\}$) have integer magnitude below $q/2$ as well. The lemma is stated for a
value held in bits. For a value held in tribits the limb is the same linear reading over digits
in $\{-4, \ldots, 3\}$ plus the offset constant, and its range follows from the alphabet. The
statement should be redone for that reading when the proofs are attempted.

**Theorem B (Kishu's claim reduction, sum-check form).** Fix $s \in \mathbb{F}_q^n$
authenticated by an Akita commitment at the 64-bit profile. Suppose the verifier accepts the
sum-check over $E$, with uniform $r \in E^m$ and $\mu \in E^8$ drawn after the commitment, of
$$\sum_a \mathrm{eq}(r, a)\,\widetilde s(a)(\widetilde s(a)-1) + \widetilde s(a)\,\widetilde w(a) = \sum_j \mu_j v_j,
\qquad w = \sum_j \mu_j c_j,$$
with the terminal evaluation $v = \widetilde s(\rho)$ authenticated by the commitment. Then, except
with probability at most $(4m+1)/\lvert E \rvert$ over the verifier's randomness, plus Akita's
knowledge error for the opening: $s \in \{0,1\}^n$, every $v_j$ is the integer limb of Lemma
B3, and $V \bmod p$ is the Pasta value whose bits $s$ carries.

Where each term comes from: $m/\lvert E \rvert$ is the weighted defect
$\sum_a \mathrm{eq}(r, a)\, s_a (s_a - 1)$, a nonzero multilinear polynomial in $r$ when some
$s_a \notin \{0, 1\}$, vanishing at a uniform $r$ (Schwartz–Zippel); $1/\lvert E \rvert$ is the
affine batching of the limb claims by independent $\mu_j$ (if some
$v_j \ne \langle c_j, s \rangle$, the batched equation holds with probability exactly
$1/\lvert E \rvert$ over $\mu$, whatever $r$ is); $3m/\lvert E \rvert$ is the degree-three
sum-check; and the opening's authentication is Akita's. No integer lift is needed, since
$x(x-1) = 0$ in a prime field only at $0$ and $1$.

**Theorem B′ (the projection form; not on Kishu's path).** Fix $s \in \mathbb{F}_q^n$
authenticated by an Akita commitment at the 64-bit profile, before the projection randomness.
Suppose the verifier accepts the protocol of the draft's equation 6 extended by the limb terms
(the spike's steps 6 and 7): the batched quadratic sum-check over $E$ of
$$\sum_a \widetilde s(a)(\widetilde s(a)-1) + \widetilde s(a)\,\widetilde w(a) = \langle \lambda, y\rangle + \sum_j \mu_j v_j,
\qquad w = T^\top \lambda + \sum_j \mu_j c_j,$$
with the terminal evaluation $v = \widetilde s(\rho)$ authenticated by the commitment, and the
integer energy checks on the revealed $y$. Then, except with probability at most
$\varepsilon_{\mathrm{proj}} + (2m+2)/\lvert E \rvert$ over the verifier's randomness, plus
Akita's knowledge error for the opening: $s \in \{0,1\}^n$, $y = Ts$, every $v_j$ is the integer
limb of Lemma B3, and $V \bmod p$ is the Pasta value whose bits $s$ carries.

Where each term comes from: $\varepsilon_{\mathrm{proj}}$ is the draft's equation 1, the
projection's lower-tail certificate (its $2^{-136}$ is conditional on CertifiedJL's estimates
(10) and (11)); $(2m+1)/\lvert E \rvert$ is the quadratic sum-check's algebraic error from the
draft's §4; the extra $1/\lvert E \rvert$ is the affine batching of the limb claims with the
projection claims by independent $\mu_j$, which is the same argument as the draft's for
$\lambda$ (if $y \ne Ts$ or some $v_j \ne \langle c_j, s\rangle$, the batched equation holds
with probability exactly $1/\lvert E\rvert$ over the batching vector); Booleanity is Theorem 1
from $E_x < Q_0$ and the zero defect; and the opening's authentication is Akita's.

Neither Theorem B nor B′ covers:

- the Fiat–Shamir transform, inherited from Akita's ROM proof; the draft's AES-derived cores
  are a computational assumption on top of B′;
- zero knowledge: B′ has none, since the revealed $y$ forgoes it, as the draft says, and B's
  rows take Akita's mask;
- the accumulation: the fold's sum-checks are Akita's, over $E$ at the 64-bit profile,
  unchanged by Kishu.

So Kishu's soundness reduces to Akita's at its native profile plus a standard sum-check
argument. The decoupled commitment modulus of the Pasta-claims variant is not involved, and
neither is the draft's certificate.

## 4. What to do next, once the statements are reviewed

1. Theorem B first, since it is Kishu's. Its proof is the standard one: Schwartz–Zippel on
   the weighted defect, the affine batching, and the sum-check's soundness. Add the sum-check
   form to the spike beside the projection form. Its adversarial cases are the ones the
   statement names: a non-Boolean $s$; a $v_j$ off by a multiple of $q$; and batching with a
   dependent $\mu$. Add an exhaustive check of Lemma B3's bound at small $n$ and small $q$.
2. Not a blocker: the independent recomputation of the draft's certificate at its parameters,
   which is what $\varepsilon_{\mathrm{proj}} = 2^{-136}$ in Theorem B′ rests on beyond
   CertifiedJL's estimates. It is needed only if the projection form is adopted for a native
   verifier.
3. Lean: Lemma B3 first, then Theorem B's reduction in VCVio. Lemma L is needed here only by
   Theorem B′, and the projection certificate only by B′.
