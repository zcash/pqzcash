# The soundness obligation behind the Pasta-claims Akita variant: the statement

Statement drafted 2026-11-14, to be reviewed before any proof is attempted. Sources:
[§6.3 of the Akita proof sizes at a Pasta modulus](pasta-proof-size.md#63-decoupling-the-commitment-modulus-from-the-claim-field)
page (the decoupled commitment modulus), and LaBinius (ePrint 2026/2103). Kishu's obligations
are different ones, the subject of [The soundness obligations behind Kishu](kishu-soundness.md).

## 1. The design and its obligation

**Akita with Pasta claims over the 64-bit commitment (`pasta_q64`).** The claim field is
Pallas's field $\mathbb{F}_p$. The witness is the balanced base-8 digit vector of the
$\mathbb{F}_p$ coefficients, 85 digits each, committed under Akita's Ajtai matrix over
$R_{q_c} = \mathbb{Z}_{q_c}[X]/(X^{64}+1)$ with $q_c = 2^{64}-59$. The sum-checks, the partials
and the claim values are $\mathbb{F}_p$ values. The ring relations modulo $q_c$ are checked
over $\mathbb{F}_p$ with explicit quotient witnesses: $Az - \sum_i c_i t_i = q_c k$ over the
integers, $k$ carried as digits. This is the decoupling of
[§6.3](pasta-proof-size.md#63-decoupling-the-commitment-modulus-from-the-claim-field), a
protocol change whose knowledge-soundness proof has to be redone with the no-wrap step.

Kishu does not use this decoupling: its claim field is the commitment modulus itself, so its
obligations are Akita's own at the 64-bit profile, a Booleanity check, and a limb lemma, stated
on its own page. Theorem A below is the obligation of Kishu's fallback, the variant that keeps
its claims in $\mathbb{F}_p$, not of Kishu.

## 2. The no-wrap lemma

**Lemma L (no wrap).** Let $F$ be a prime field of size $r$, and let $u, v \in \mathbb{Z}$ with
$\lvert u \rvert, \lvert v \rvert < r/2$. If $u \equiv v \pmod r$ then $u = v$.

This is the same Lemma L as on the Kishu page, repeated so that each page stands alone. §6.3's
"an $\mathbb{F}_p$ identity among integers of size $2^{86}$ cannot wrap" is Lemma L with
$r = p \approx 2^{254}$.

## 3. The statement

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
  $N \cdot \lVert z \rVert_\infty = 2^{49}$, 17 base-8 digits, where
  [§6.3](pasta-proof-size.md#63-decoupling-the-commitment-modulus-from-the-claim-field) says
  "eleven base-8 digits per relation coordinate" with "$\lvert k \rvert$ around $2^{31}$". The
  count depends on where in the tree the relation is checked: a fresh witness has digits at
  most 4, an accumulated one entries near the norm bound. The proof must fix the quotient's
  width per level, and the page's digit count for $k$ may be low.
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

## 4. A cost consequence

In this design the fold's norm and range sum-checks run over $\mathbb{F}_p$, since every
sum-check message is an $\mathbb{F}_p$ value
([§6.3](pasta-proof-size.md#63-decoupling-the-commitment-modulus-from-the-claim-field)). A
linear-time sum-check prover pays about one full claim-field multiplication per digit per pass
after the first fold: 32 word multiplications in $\mathbb{F}_p$, against 2 at the 64-bit
commitment modulus. The page's accumulation prover prices the sum-checks at the claim field's
rate, since the same commit of 2026-11-14. Before it the `pasta_q64` rows were charged the
commitment modulus's rate, so their accumulation term was low by a factor of three to four.
Kishu is unaffected: its sum-checks are over $E$ at 64 bits, which is what the draft measured.

## 5. What to do next, once the statement is reviewed

1. Theorem A's protocol written in full with the quotient widths and the range-check form
   settled per level, then its proof adapted from LaBinius.
2. Lean: Lemma L, then Theorem A's reduction, once the protocol is written.
