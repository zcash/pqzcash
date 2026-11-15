# The soundness obligations behind Kishu and the Pasta-claims Akita variant: the statements

Statements drafted 2026-11-14, to be reviewed before any proof is attempted. Sources:
pasta-proof-size.md §6.3 (the decoupled commitment modulus); the Booleanity-by-projection draft
"Efficient Booleanity Checking via Structured Modular Projections" of 2026-09-23 (§2 Theorem 1,
§4 equation 6, §5 the certificate); and spike/booleanity_spike.py (the limb protocol).

## 1. Two designs, two different obligations

Writing the two protocols out shows two different obligations. The PCS frontier page's Kishu
paragraph once said that Kishu carries "the same open soundness obligation" as the Pasta-claims
Akita variant. It was corrected on 2026-11-14 (commit
c8aa3302edbb5377e925a85e6552223c53f1934b), and says that Kishu does not use the decoupled
commitment.

**Design A: Akita with Pasta claims over the 64-bit commitment (`pasta_q64`).** The claim
field is Pallas's field $\mathbb{F}_p$. The witness is the balanced base-8 digit vector of the
$\mathbb{F}_p$ coefficients, 85 digits each, committed under Akita's Ajtai matrix over
$R_{q_c} = \mathbb{Z}_{q_c}[X]/(X^{64}+1)$ with $q_c = 2^{64}-59$. The sum-checks, the partials
and the claim values are $\mathbb{F}_p$ values. The ring relations modulo $q_c$ are checked
over $\mathbb{F}_p$ with explicit quotient witnesses: $Az - \sum_i c_i t_i = q_c k$ over the
integers, $k$ carried as digits. This is the decoupling of §6.3, a protocol change whose
knowledge-soundness proof has to be redone with the no-wrap step.

**Design B: Kishu.** The claim field is $\mathbb{F}_q$ with $q = 2^{64}-59$, which is Akita's
own 64-bit commitment modulus. There is no decoupling: the bits are committed one per digit as
any small digit vector is, and the evaluation claims are Akita's ordinary claims at the 64-bit
profile, over the quadratic extension $E = \mathbb{F}_q[u]/(u^2-2)$ that the draft's sum-check
uses. The Pasta values never reach the commitment: the first 255 bits of a value are read as
eight 32-bit limbs $v_j = \langle c_j, s\rangle$, proved as linear claims in the same sum-check,
and the verifier recomposes $V = \sum_j 2^{32j} v_j$ over the integers and reduces modulo $p$.

So Kishu's obligations are: (B1) Akita's knowledge soundness at its 64-bit profile with claims
in $E$, which the paper proves in the classical ROM; (B2) the draft's Booleanity certificate;
(B3) an elementary limb lemma. Design A's obligation, Theorem A in §4, is Kishu's fallback's,
not Kishu's.

## 2. The shared lemma

**Lemma L (no wrap).** Let $F$ be a prime field of size $r$, and let $u, v \in \mathbb{Z}$ with
$\lvert u \rvert, \lvert v \rvert < r/2$. If $u \equiv v \pmod r$ then $u = v$.

Theorem 1 of the draft is Lemma L applied to $u = D_x = \sum_i x_i(x_i-1)$ and $v = 0$, with
the bound $0 \le D_x \le E_x + \sqrt{nE_x} < Q_0 + \sqrt{nQ_0} < q$ from Cauchy–Schwarz. §6.3's
"an $\mathbb{F}_p$ identity among integers of size $2^{86}$ cannot wrap" is Lemma L with
$r = p \approx 2^{254}$.

## 3. Kishu's statements

**Lemma B3 (limbs).** Let $s \in \{0,1\}^n$ with $n \le 2^{31}$, and let $c_j \in \mathbb{Z}^n$
have entries $2^{i - 32j}$ at positions $i \in [32j, 32j+32)$ and zero elsewhere. Then the
integer $v_j = \langle c_j, s \rangle$ satisfies $0 \le v_j < 2^{32}$, so its value in
$\mathbb{F}_q$ is its integer value, $V = \sum_{j} 2^{32j} v_j$ is the integer whose bits are
$s_0, \ldots, s_{254}$, and $V \bmod p$ is the Pasta value those bits encode.

Proof sketch: each $v_j$ is a sum of at most 32 distinct powers of two below $2^{32}$, and
$2^{32} < q$; Lemma L is not even needed, the integer is below $q$ outright. The hypothesis
$n \le 2^{31}$ is only what makes the general linear claims of equation 6 (the projection rows,
entries in $\{-1,0,1\}$) have integer magnitude below $q/2$ as well.

**Theorem B (Kishu's claim reduction).** Fix $s \in \mathbb{F}_q^n$ authenticated by an Akita
commitment at the 64-bit profile, before the projection randomness. Suppose the verifier
accepts the protocol of the draft's equation 6 extended by the limb terms (the spike's steps 6
and 7): the batched quadratic sum-check over $E$ of
$$\sum_a \tilde s(a)(\tilde s(a)-1) + \tilde s(a)\,\tilde w(a) = \langle \lambda, y\rangle + \sum_j \mu_j v_j,
\qquad w = T^\top \lambda + \sum_j \mu_j c_j,$$
with the terminal evaluation $v = \tilde s(\rho)$ authenticated by the commitment, and the
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

What is NOT in Theorem B: the Fiat–Shamir transform (inherited from Akita's ROM proof; the
draft's AES-derived cores are a computational assumption on top), zero knowledge (none; the
revealed $y$ forgoes it, as the draft says), and the accumulation (the fold's sum-checks are
Akita's, over $E$ at the 64-bit profile, unchanged by Kishu).

So Kishu's soundness reduces to Akita's at its native profile plus the draft's certificate.
The decoupling of §6.3 is not involved.

## 4. Design A's statement

**Theorem A (knowledge soundness of the decoupled Akita), to be stated precisely once the
protocol is written.** The protocol is Akita's at the fp128-style profile, with these changes:
the claim field is $\mathbb{F}_p$; every relation the verifier checks is an $\mathbb{F}_p$
identity; the ring relations $Az = \sum_i c_i t_i$ modulo $q_c$ are replaced by
$Az - \sum_i c_i t_i = q_c k$ with $k$ a committed digit witness; the digit range and norm
checks are $\mathbb{F}_p$ identities on the digits. The claim is: if Module-SIS over $R_{q_c}$
holds at the accumulated bound $\beta$, Akita's extractor yields, from any accepting prover, a
digit vector $w$ with $\lVert w \rVert_2 \le \beta$ such that the committed polynomial's
coefficients are $\sum_k 8^k w_{j,k} \bmod p$ and the claimed evaluation holds in
$\mathbb{F}_p$, with Akita's knowledge error and no new probabilistic term.

The new step is deterministic: every $\mathbb{F}_p$-checked identity must have both sides of
integer magnitude below $p/2$ for Lemma L to lift it, and the lifted ring relation must then
hold modulo $q_c$. The magnitudes to pin:

- The ring relation: $\lvert (Az)_i \rvert \le N \cdot q_c \cdot \lVert z \rVert_\infty$ for
  $N$ digit columns, so with $N = 2^{22}$ and the accumulated $\lVert z \rVert_\infty \le 2^{27}$
  that is $2^{113} < p/2 \approx 2^{253}$: fine. But the quotient $k$ is then up to
  $N \cdot \lVert z \rVert_\infty = 2^{49}$, 17 base-8 digits, where §6.3 says "eleven base-8
  digits per relation coordinate" with "$\lvert k \rvert$ around $2^{31}$". The count depends on
  where in the tree the relation is checked: a fresh witness has digits at most 4, an
  accumulated one entries near the norm bound. The proof must fix the quotient's width per
  level, and the page's digit count for $k$ may be low.
- The digit range identity, e.g. $\prod_{a=-4}^{3}(w_i - a) = 0$ summed with random weights:
  magnitude at most $N \cdot (\lVert w \rVert_\infty + 4)^8 \le 2^{22} \cdot 2^{248}$, which is
  NOT below $p/2$ for accumulated witnesses at $2^{27}$. The range check for accumulated
  witnesses must therefore be the norm check (an $\ell_2$ sum of squares, magnitude
  $N \cdot 2^{54} = 2^{76}$, fine), or the range identity must be applied only to fresh digits.
  This is the kind of detail that decides whether the design is sound as described.
- The evaluation claim needs no lift: it is an $\mathbb{F}_p$ statement about the
  $\mathbb{F}_p$ reductions of the recomposed digits.

LaBinius (ePrint 2026/2103) proves the analogous decoupling with extraction over the number
field, avoiding reduction modulo the commitment modulus; its claim field is binary. Its
argument is the one to adapt, and the two bullets above are where the adaptation is not
mechanical.

## 5. A cost consequence

In design A the fold's norm and range sum-checks run over $\mathbb{F}_p$, since every
sum-check message is an $\mathbb{F}_p$ value (§6.3). A linear-time sum-check prover pays about
one full claim-field multiplication per digit per pass after the first fold: 32 word
multiplications in $\mathbb{F}_p$, against 2 at the 64-bit commitment modulus. The page's
accumulation prover prices the sum-checks at the claim field's rate, since the same commit of
2026-11-14. Before it the `pasta_q64` rows were charged the commitment modulus's rate, so
their accumulation term was low by a factor of three to four. Kishu is unaffected: its
sum-checks are over $E$ at 64 bits, which is what the draft measured.

## 6. What to do next, once the statements are reviewed

1. Theorem B first, since it is Kishu's: write the proof, which is short given the draft's
   §4 argument, and extend the spike with the adversarial cases the statement names (a
   non-Boolean $s$ with wrapped limbs; a $v_j$ off by a multiple of $q$; batching with a
   dependent $\mu$) and an exhaustive check of Lemma B3's bound at small $n$ and small $q$.
2. The independent recomputation of the draft's certificate at its parameters, which is what
   $\varepsilon_{\mathrm{proj}} = 2^{-136}$ rests on beyond CertifiedJL's estimates.
3. Theorem A's protocol written in full with the quotient widths and the range-check form
   settled per level, then its proof adapted from LaBinius.
4. Lean: Lemma L and Lemma B3 first, then Theorem B's reduction in VCVio, with the projection
   certificate imported from CertifiedJL when it lands.
