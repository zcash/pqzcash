# Zero knowledge for a lattice accumulation step: Fiat–Shamir with aborts

Ragu hides a user's witness from the aggregator by folding the user's proof with a random partner before handing it over. If Ragu's Pedersen commitments are replaced by Akita's Module-SIS commitments (ePrint 2026/1983), that fold needs Lyubashevsky's rejection sampling, also called Fiat–Shamir with aborts. This note gives the setting (§1), the technique (§2), the resulting protocol for the user's fold (§3), why it is zero knowledge and what remains to be proved (§4), what it costs (§5), proof hygiene (§6), and open points (§7). The audience is cryptographic engineers who know commitment schemes and Fiat–Shamir but not necessarily lattices, so lattice terms are defined at first use. Written 2026-10-13, after a discussion with Tal Derei and Quang Dao at the Cambridge PQC workshop.

## 1. The setting and the problem

### 1.1 What the aggregator sees, and what Ragu's fold does

In split accumulation (Ragu's scheme, following BCLMS20), an accumulator is an instance (a commitment and an evaluation claim) and a witness (the committed vector). The accumulation prover needs the witnesses of everything it folds, and in Tachyon the aggregator is that prover. So the user has to hand over an accumulator whose witness does not depend on the user's secrets, and the intended mechanism is one fold by the user with a random partner.

Ragu's fold is the PCS aggregation of its book. Take claims $(\bar C_i, x_i, y_i)$ on polynomials $p_i$ with blinding factors $\gamma_i$. The prover commits to $f = \sum_i \alpha^i q_i$ with $q_i = (p_i - y_i)/(X - x_i)$ and sends the evaluations $p_i(u)$ at a fresh point $u$. The folded witness is $p = f + \sum_i \beta^i p_i$ with blinding $\gamma = \gamma_f + \sum_i \beta^i \gamma_i$. A Pedersen commitment $\sum_j p_j G_j + \gamma H$ commits to any vector in $\mathbb{F}^n$, so $p$ is an opening of the folded commitment $\bar F + \sum_i \beta^i \bar C_i$ whatever the $p_i$ are.

Now let one folded claim be on a uniformly random polynomial $r$ with a trivially true claim. Then $r$ enters $p$ through $\beta^k r$ and its own quotient $\alpha^k q_r$. The map $r \mapsto \beta^k r + \alpha^k q_r$ is a linear bijection of $\mathbb{F}^n$: if it vanished, $r(X)\,(\beta^k (X - x_r) + \alpha^k)$ would equal the constant $\alpha^k r(x_r)$, which forces $r = 0$. Two qualifications. The aggregator also holds the folded instance, which forces $p(u) = v$, so $p$ is uniform on that affine hyperplane rather than on all of $\mathbb{F}^n$; that is the most any handoff can hide. And $\beta$ is derived after the evaluations $p_i(u)$, which include $r(u)$, so the argument conditions on the transcript. Given $r(u) = \rho$, the partner is uniform on the hyperplane $r(u) = \rho$ and the challenges are fixed, and the bijection carries that hyperplane onto $p(u) = v$. Everything else the aggregator sees about $r$ is a perfectly hiding commitment. This is a statement about the witness vector alone; §4.3 states what has to hold for the whole handoff.

The random partner does not exist yet. In the Ragu checkout at hand (commit 526b0e3ecdc1c39d03df315316ac075854769352, 2026-10-04), the rerandomization step folds the proof with a cached seeded trivial proof, which is deterministic, with an empty witness. Its comments say that the folded accumulator is then a deterministic function of the input proof, the cached proof, and the public challenges. They say that hiding it needs a fold-level randomizer claim, and that this is future work. They also note that the uncompressed output embeds the input proof's commitments and stage polynomials in the clear as child data. The book's NARK and PCD chapters say the same. A deterministic rerandomization cannot be zero knowledge: a guess at the witness is confirmed by recomputing the output.

### 1.2 Lattice commitments and short openings

An Ajtai commitment is $\mathrm{Com}(w) = A w \bmod q$, where $A$ is a public matrix over the ring $R_q = \mathbb{Z}_q[X]/(X^d+1)$ and $w \in R_q^m$ is the committed vector. Here $q$ is the field prime, for Ragu the Pasta prime, and $d$ is the ring dimension. A vector in $R_q^m$ is also an integer vector with $N = md$ coordinates once each coefficient is lifted to $(-q/2, q/2]$; $\|w\|_2$ and $\|w\|_\infty$ are the norms of that integer vector.

The map $w \mapsto Aw$ is linear, so a preimage of arbitrary size is found by linear algebra. Binding applies only to short openings. Module-SIS says it is hard to find a nonzero $z$ with $Az = 0$ and $\|z\|_2 \le \beta$, for the bound $\beta$ that the parameters are chosen for. Two distinct openings of norm at most $\beta/2$ would give such a $z$. So an opening is by definition a short vector, and a long preimage is not an opening of anything.

Akita commits to a polynomial over $\mathbb{F}_q$ by writing each coefficient in balanced base 8, digits in $\{-4, \ldots, 3\}$, which is 85 digits per coefficient at 255 bits. The digit vector $w$ is short, the polynomial is $p = Gw \bmod q$ for the public recomposition matrix $G$, and $p \mapsto \mathrm{digits}(p)$ is not linear.

### 1.3 Why the uniformity argument does not transfer

Fold the user's digit vector $s$ with a random vector $y$ under a challenge $c$: $z = y + cs$ in the ring. Then $Az = Ay + c \cdot As$, so the verifier checks the folded commitment from the two inputs. Because $z$ must be a short opening, $y$ and $c$ must be short too. But a short $y$ cannot pad $cs$. In one dimension, a uniform $y$ on $[-\gamma, \gamma]$ gives $z = y + v$ uniform on $[-\gamma + v, \gamma + v]$, and a $z$ near either end reveals $v$. A Gaussian $y$ of width $\sigma$ gives a Gaussian shifted by $v$, distinguishable from an unshifted one with advantage about $|v|/\sigma$ per coordinate, over millions of coordinates. The handed-over witness depends on $s$, and rejection sampling is the standard remedy.

## 2. Rejection sampling

### 2.1 Discrete Gaussians

$D^N_\sigma$ is the discrete Gaussian on $\mathbb{Z}^N$ of width $\sigma$ centred at $0$, with probability proportional to $\exp(-\|x\|_2^2 / 2\sigma^2)$; $D^N_{v,\sigma}$ is the same centred at $v$, and $y \leftarrow D^N_\sigma$ gives $y + v \sim D^N_{v,\sigma}$. Two tail facts (Lyubashevsky 2012, Lemma 4.4): a coordinate of $z \leftarrow D^N_\sigma$ exceeds $t\sigma$ with probability at most $2e^{-t^2/2}$, below $2^{-140}$ at $t = 14$; and $\|z\|_2 \le 2\sigma\sqrt{N}$ except with probability below $e^{-0.8N}$.

### 2.2 The theorem

Theorem 4.6 of Lyubashevsky, "Lattice Signatures Without Trapdoors" (EUROCRYPT 2012, ePrint 2011/537). Let $V \subseteq \mathbb{Z}^N$ contain vectors of norm at most $T$, let $h$ be any distribution on $V$, and let $\sigma = \alpha T$.

- Procedure $\mathcal{A}$ (the real prover): sample $v \leftarrow h$ and $z \leftarrow D^N_{v,\sigma}$; output $(z, v)$ with probability $\min\!\left(1, \dfrac{D^N_\sigma(z)}{M \cdot D^N_{v,\sigma}(z)}\right)$, else nothing.
- Procedure $\mathcal{F}$ (the ideal): sample $v \leftarrow h$ and $z \leftarrow D^N_\sigma$; output $(z, v)$ with probability $1/M$, else nothing.

With $M = e^{12/\alpha + 1/(2\alpha^2)}$, the outputs of $\mathcal{A}$ and $\mathcal{F}$ are within statistical distance $2^{-100}/M$, and $\mathcal{A}$ outputs something with probability at least $(1 - 2^{-100})/M$. In words: the prover samples $z$ around the secret-dependent centre $v$ and keeps it with a probability chosen so that kept samples are distributed as if drawn around $0$; the dependence on $v$ is paid in aborts, not leakage. With $\alpha = 12$, $M = e^{1 + 1/288} \approx 2.73$ expected attempts. The acceptance probability is computable from $z$ and $v$:

$$
\Pr[\text{accept}] \;=\; \min\!\left(1,\; \frac{1}{M} \exp\!\left(\frac{\|v\|_2^2 - 2\langle z, v\rangle}{2\sigma^2}\right)\right).
$$

In a signature $v = cs$ and $z = y + cs$, which is the shape of the fold in §1.3.

### 2.3 Variants

- Uniform masks (Lyubashevsky 2009; Dilithium): $y$ uniform in the box $\|y\|_\infty \le \gamma$, accept iff $\|z\|_\infty \le \gamma - T_\infty$ with $T_\infty \ge \|cs\|_\infty$; the accepted $z$ is uniform in the smaller box. Acceptance is about $\exp(-N T_\infty/\gamma)$, so a constant rate needs $\gamma \approx N T_\infty$. Competitive at signature sizes; at $N$ in the millions the Gaussian gives a smaller $z$ by several bits (§5.1), so this note uses Gaussians.
- Bimodal Gaussians (BLISS, Ducas–Durmus–Lepoint–Lyubashevsky 2013): $z = y \pm cs$ with a hidden sign brings $\alpha$ from 12 to about 1. The sign stays hidden in BLISS because the public key satisfies $As = q \bmod 2q$, so both signs verify. In the fold the verifier checks $Az = Ay + c \cdot As$ and would need the sign, which makes the trick a symmetric challenge set and does not gain anything. Not applicable without a sign-hiding commitment structure.

### 2.4 The cost in norm

After acceptance $z \sim D^N_\sigma$ with $\sigma = \alpha \|cs\|_2$, so $\|z\|_2 \approx \alpha\sqrt{N}\,\|cs\|_2$. The $\sqrt{N}$ is the price of the technique: every coordinate is masked at a width covering the norm of the whole vector. At $N \approx 2^{10}$, as in a signature, that is 5 bits; at $N \approx 2^{22}$ it is 11.

## 3. The protocol: a zero-knowledge user fold

### 3.1 Notation

- $A \in R_q^{n \times m}$: the commitment matrix, shared by every commitment in the accumulation chain.
- $s \in R_q^m$: the concatenation of the user's secret committed vectors as digit vectors. Several staged commitments concatenate, and $C_s = As$ is their sum, since Ajtai commitments add.
- $(x_i, v_i)_i$: the NARK's evaluation claims, that the polynomial recomposed from $s$ evaluates to $v_i$ at $x_i$. Several commitments each carry their own claim list and are handled alike.
- $\mathcal{C} \subset R_q$: the challenge set, of small elements with invertible pairwise differences, of size at least $2^{128}$ times the extraction slack (§5.4).
- $H$: the transcript hash, modeled as a random oracle; in the merge circuit it must be arithmetization-friendly.
- $b = 8$: the digit base; $J$: digits needed for a coordinate of $z$; $N = md$.

### 3.2 Steps

1. Mask. Sample $y \leftarrow D^N_\sigma$ and commit $C_y = Ay$ directly, not through digits (§4.2). For each claim point $x_i$ compute $u_i$, the evaluation at $x_i$ of the polynomial recomposed from $y$, so that $(C_y, x_i, u_i)$ is a valid claim. This is the random partner: a random claim, not a proof of a random instance (§4.3).
2. Challenge. $c = H(\text{instance}, C_s, (x_i, v_i)_i, C_y, (u_i)_i)$, mapped into $\mathcal{C}$.
3. Response. $z = y + cs$ in the ring, as integer vectors.
4. Rejection test. With $v = cs$, accept with the probability of §2.2; on rejection return to step 1 with a fresh $y$, hence a fresh $C_y$ and a fresh $c$. Also return to step 1 in the rare case that a coordinate of $z$ exceeds $14\sigma$, so that $J$ is fixed.
5. Decomposition. Write $z = \sum_{j<J} b^j z_j$ with each $z_j \in \{-4, \ldots, 3\}^N$, and commit $C_{z_j} = A z_j$.
6. Claim fold. For each $i$ the folded claim is $(C_z, x_i, u_i + c \cdot v_i)$ with $C_z = \sum_j b^j C_{z_j}$, the addition in Akita's packing. Akita arranges its folds so that evaluation commutes with multiplication by a subring challenge, and the same arrangement is assumed here. Claims stay at their own points: moving them to a common point first, as LatticeFold-style folds do, would run a sum-check over the unmasked $s$ and need its own masking. The claim count does not grow, and the aggregator's later folds reduce the claims to a common point on masked data.
7. Obligations. Prove that each $z_j$ has digits in the alphabet and that $\|z\|_2$ is at most its certified bound, as Akita certifies its folded responses, by sum-checks absorbed into the transcript. The $\ell_2$ bound matters for soundness (§5.2).

### 3.3 What the verifier checks and what the aggregator receives

The merge circuit that verifies the fold checks:

- the challenge derivation;
- the commitment identity $\sum_j b^j C_{z_j} = C_y + c \cdot C_s$, which is ring-linear in the commitment vectors and holds because $z = y + cs$ and $z = \sum_j b^j z_j$ both hold over the integers;
- the claim fold, which is field arithmetic;
- the sum-check transcripts of step 7, whose final evaluation claims join the accumulator.

Absorbing $C_y$ and the $C_{z_j}$ is where the commitment rank enters the circuit cost; the compressed-commitment deferral discussed separately makes that cost rank-insensitive and does not change anything here.

The aggregator receives the output accumulator, instance $(C_{z_j})_j$ with the folded claims and the obligations' final claims and witness $(z_j)_j$, together with the merge NARK that verifies the fold, instance and witness. The merge NARK's witness is the merge circuit's trace: transcript values, commitments, and verifier arithmetic on them.

## 4. Why it is zero knowledge

### 4.1 The simulator

Given the public instance and the output, the simulator:

1. samples $c \leftarrow \mathcal{C}$ and $z \leftarrow D^N_\sigma$, conditioned on every coordinate being at most $14\sigma$;
2. decomposes $z$ into $(z_j)_j$ and commits them;
3. sets $C_y := Az - c \cdot C_s$ and $u_i := z(x_i) - c \cdot v_i$;
4. programs the random oracle so that $H(\ldots, C_y, (u_i)_i) = c$;
5. runs the honest prover for the obligations of step 7 on $z$, which it knows.

### 4.2 What the proof needs

- The rejection-sampling theorem: the real accepted $z$ is within $2^{-100}/M$ of $D^N_\sigma$ and independent of $s$ and $c$.
- The mask commitment is a function of $z$ and $c$. Because $y$ is committed as one vector, the real $C_y = Ay$ equals $Az - c \cdot C_s$ exactly, so the simulator can compute it. This is the Schnorr simulator's $R = g^z y^{-c}$: the first message must be a function of the response and the challenge alone. Committing to the digits $y_j$ of $y$ instead would also be sound, but a distinguisher who knows $s$ computes $y = z - cs$, its digits, and $A \cdot \mathrm{digit}_j(y)$, and a simulator cannot. The price of the direct commitment is that $y$, with coordinates up to $14\sigma$, must itself be a short opening, which §5.2 needs anyway.
- Programming succeeds. By the regularity lemma for discrete Gaussians (Gentry–Peikert–Vaikuntanathan 2008), $Ay \bmod q$ is statistically close to uniform on $R_q^n$ when $\sigma$ exceeds the smoothing parameter of $\{y : Ay = 0\}$. That holds with enormous margin at $N$ and $\sigma$ in the millions. So the real $C_y$ has high min-entropy and the adversary has not queried $H$ at it except with negligible probability.
- Everything else published is a function of $z$, $c$, and public values: the $C_{z_j}$, the $u_i = z(x_i) - c \cdot v_i$, the folded claims, and the obligation transcripts, which are proofs about $z$. None needs masking of its own.
- $C_s$ must be hiding. An Ajtai commitment is deterministic, and $A \cdot \mathrm{digits}(\text{trace})$ of a trace driven by a few hundred secret bits is not statistically hiding. Appending uniformly random digits $\rho$ to the committed vector fixes this by the leftover hash lemma when $H_\infty(\rho) \ge nd \log_2 q + 2\lambda$. At the parameters of §5.3 that is about 86K bits, about 29K base-8 digits or the digits of about 340 random field elements. The padding folds and range-checks like everything else.
- Revealed evaluations must not leak. Ragu's NARK is deliberately not zero knowledge: it sends the witness vectors unmasked, and its trace polynomial has a hiding commitment but does not have any random coefficients. The vectors go into the accumulator, which the randomizer pads; the evaluations $a(xz)$, $b(x)$, $s(x,y)$ in the NARK and $p_i(u)$ in the fold are linear functionals of the trace and do not. The standard fix is one random coefficient in the trace polynomial per evaluation revealed over its lifetime.
- The merge NARK's witness, handed to the aggregator, contains $C_s$ (hiding by the previous item), $C_y$, $c$, the claims, and the obligation transcripts, all simulatable, so it does not carry any further information.

### 4.3 The "one fold suffices" statement, and what the random partner has to be

The statement to prove, in either setting: after the user's single fold with a random partner, the joint distribution of everything the aggregator receives is simulatable from the public statement of the action and the output instance alone. What the aggregator receives is the output accumulator's instance and witness and the merge NARK's instance and witness. Neither setting has a proof yet. In the DL setting the witness side is the uniformity argument of §1.1, and the message side is the quotient commitment, hidden by $\gamma_f$, and the evaluations at $u$, hidden by blinding coefficients. In the lattice setting the witness side is rejection sampling and the message side is the list of §4.2. That list is longer because the commitment does not have any blinding factor and the fold's messages include a decomposition and sum-check transcripts, but each item reduces to a function of the masked $z$.

One part of the statement is decided by what the partner is. A proof of a random instance of the circuit has as its polynomial the trace of that instance, a deterministic function of a few free inputs, not a uniform vector, and then $p + \beta r$ is not uniform. For a circuit that computes the powers of its one input, $p = (x, x^2, x^3, \ldots)$ and $r = (y, y^2, y^3, \ldots)$ give $w_j = x^j + \beta y^j$. That is $n$ equations in the two unknowns $x$ and $y$, which determine $x$ for $n \ge 3$; more random instances add unknowns but add equations faster. The partner must be a uniformly random vector with a trivially true claim, folded as an extra claim rather than as a proof. The lattice setting has the same requirement in another form: the rejection-sampling theorem needs a fresh Gaussian $y$, and a random trace is not one.

## 5. Costs

### 5.1 Norm growth

With $\sigma = \alpha\|cs\|_2$ and $\alpha = 48$: $\|z\|_2 \approx 48\sqrt{N}\,\|cs\|_2$, and $\|z\|_\infty \le 14\sigma = 672\,\|cs\|_2$ fixes the digit count $J$. The uniform-box variant would give $\|z\|_\infty \approx N\,\|cs\|_\infty$, about 4 bits worse in $\ell_2$ at $N = 2^{22}$.

### 5.2 The Module-SIS bound

The extractor rewinds to a second challenge $c'$ and obtains short responses $z^*, z'^*$ with $A(z^* - z'^*) = (c - c') C_s$. This is a relaxed opening of $C_s$: $(c - c')^{-1}(z^* - z'^*)$ opens it, but only its multiple by $c - c'$ is known to be short. Binding for relaxed openings is the cross-multiplication argument of Attema–Lyubashevsky–Seiler 2020, which Akita uses in its lemma on binding from weak openings. Two relaxed openings with challenge differences $\delta_1, \delta_2$ give a kernel vector of norm at most $\|\delta_2\|_1 \|\delta_1 \bar s_1\|_2 + \|\delta_1\|_1 \|\delta_2 \bar s_2\|_2$. So the bound of $A$ must be at least

$$
\beta \;\gtrsim\; 2 \cdot \|c - c'\|_1 \cdot 2\,\|z^*\|_2 ,
$$

with $\|z^*\|_2$ the certified Euclidean bound on responses. That is why step 7 certifies the $\ell_2$ norm and not only the digit range: a digit range alone gives $\|z\|_\infty \sqrt{N} = 14\sigma\sqrt{N}$ rather than $2\sigma\sqrt{N}$, which costs 3 bits of $\beta$.

The bound is a property of $A$, and $A$ is shared by every commitment that the decider opens through this chain, because binding transfers only through the matrix under which the fold identity is checked. So the mask raises $\beta$ for the whole system. That system is the accumulation: every accumulator is committed under this matrix. Akita's internal fold levels and its terminal commit the final accumulator's ordinary witness under their own matrices, whose bounds the mask does not change, so the opening proof is nearly unaffected; only this matrix's larger images, carried as auxiliary digits at the first level, grow. A smaller matrix for later folds does not help: their checks would cover only a prefix of the rows, and the extracted openings would satisfy only that prefix. Two independent matrices joined by proven switches are the other shape; §5.9 works it through and finds the switch's verifier cost to be the obstacle.

The rank follows from the usual estimate: lattice reduction with root Hermite factor $\delta$ finds a kernel vector of norm about $2^{2\sqrt{nd \log_2 q \cdot \log_2 \delta}}$, so hardness at $\beta$ needs

$$
nd \log_2 q \;\ge\; \frac{(\log_2 \beta)^2}{4 \log_2 \delta}.
$$

At the 128-bit quantum ADPS16 target the block size is 484 and $\log_2 \delta \approx 0.0050$. The commitment's size in bits depends on $\beta$ and not on $q$, and doubling $\log_2 \beta$ quadruples the rank; §5.5 confirms both with Akita's estimator.

### 5.3 A worked example

Assumptions are listed so that each can be replaced. The parameters are the page's: weight-20 challenges in the accumulation matrix's ring dimension and $\alpha = 48$, which §5.6 compares with the alternatives. The two rank rows come from Akita's SIS estimator at the Pasta modulus (§5.5); the rows above them are this note's assumptions.

| quantity | assumption or derivation | value |
|---|---|---|
| secret committed vectors | three vectors of $2^{14}$ coefficients over Pasta | $3 \cdot 2^{14}$ coefficients |
| digits $N$ | 85 digits per coefficient | $\approx 2^{22}$ |
| $\|s\|_2$ | digits at most 4 | $\le 2^{13}$ |
| challenge set | ring dimension $d = 512$, ternary, weight 20 | $\binom{512}{20} 2^{20} \approx 2^{138}$ elements |
| $\|cs\|_2$ | $\le \|c\|_1 \|s\|_2$ | $\le 2^{<!--fig:note_log_cs-->17.3<!--/fig-->}$ |
| $\sigma$ | $48\,\|cs\|_2$ | $\approx 2^{<!--fig:note_log_sigma-->22.9<!--/fig-->}$ |
| $\|z\|_2$ | $2\sigma\sqrt{N}$ certified | $\approx 2^{<!--fig:note_log_z2-->34.9<!--/fig-->}$ |
| $\|z\|_\infty$ | $14\sigma$ | $\approx 2^{<!--fig:note_log_zinf-->26.7<!--/fig-->}$ |
| digits per coordinate $J$ | balanced base 8 | 9 |
| masked $\beta$ | $2 \cdot 40 \cdot 2 \cdot \|z\|_2$ | $\approx 2^{<!--fig:note_log_beta-->42.2<!--/fig-->}$ |
| masked rank $nd$ | Akita's estimator, 128 quantum bits | <!--fig:note_masked_rows-->349<!--/fig--> field elements, <!--fig:note_masked_kb-->11.2<!--/fig--> kbytes |
| unmasked $\beta$ | responses of norm about $2^{19}$ | $\approx 2^{27}$ |
| unmasked rank $nd$ | Akita's estimator, 128 quantum bits | 143 field elements, <!--fig:note_unmasked_kb-->4.6<!--/fig--> kbytes |
| hiding padding $\rho$ | $nd \log_2 q + 256$ bits of uniform digits | $\approx$ <!--fig:note_padding_kdigits-->30<!--/fig-->K digits |

So the mask costs about <!--fig:note_rank_factor-->2.45<!--/fig--> times the commitment rank, 9 times the witness length handed to the aggregator, and about <!--fig:mask_attempts-->1.3<!--/fig--> attempts per fold.

### 5.4 Other costs

- Witness size. The aggregator receives $JN$ digits instead of $N$: about $2^{25.2}$ digits, 14 Mbytes at three bits each, against about 1.5 Mbytes unmasked. The information content is $N$ coordinates of <!--fig:note_zinf_bits-->27<!--/fig--> bits, about <!--fig:note_z_mb-->14 Mbytes<!--/fig-->, so the slices are at the limit. The length is paid in that transfer and in the aggregator's first fold on this accumulator, whose range checks cover the nine slices and which folds them back to $N$ digits with its other inputs. The folds above are at the ordinary length; what every fold pays is the rank of §5.2.
- Prover time per attempt: one commitment $Ay$ of a vector with 23-bit entries, plus Gaussian sampling of $N$ coordinates. The commitment is $(\mathit{rows}/d) \cdot (N/d)$ ring products. At the masked <!--fig:note_masked_rows-->349<!--/fig--> rows over Pasta, $N = 2^{22}$ and $d = 512$, the mask's $N/d = 2^{13}$ NTTs of size 512 are about $2^{<!--fig:note_ntt_log2-->24.2<!--/fig-->}$ butterfly multiplications and the pointwise products $\mathit{rows} \cdot N/d$ about $2^{<!--fig:note_pointwise_log2-->21.4<!--/fig-->}$, so about $2^{<!--fig:note_mults_log2-->24.4<!--/fig-->}$ multiplications, or $2^{26}$ operations with the additions and reductions. At 32 word multiplications per Pasta multiplication that is about $2^{<!--fig:note_word_mults_log2-->29.4<!--/fig-->}$ word multiplications, <!--fig:zk_note_commit_s-->0.232<!--/fig--> s at $3 \cdot 10^9$ per second on one core. At a 64-bit commitment modulus the rows are four times as many and each multiplication two words, about a fifth of that. The sampling, $2^{22}$ coordinates at $\sigma \approx 2^{<!--fig:note_log_sigma-->22.9<!--/fig-->}$ as a rounded continuous Gaussian at about <!--fig:mask_sample_ns-->20<!--/fig--> nanoseconds each (the sampling point below), is <!--fig:zk_note_sampling_s-->0.0839<!--/fig--> s, about a third of the commitment (<!--fig:zk_note_sampling_over_commit-->0.36<!--/fig--> times). So an attempt is <!--fig:zk_note_attempt_s-->0.316<!--/fig--> s, and a fold <!--fig:zk_note_fold_s-->0.405<!--/fig--> s at the expected $M \approx$ <!--fig:mask_attempts-->1.3<!--/fig--> attempts of $\alpha = 48$. Against that, a fold is <!--fig:zk_note_fold_alpha12_s-->0.854<!--/fig--> s at the <!--fig:mask_attempts_alpha12-->2.7<!--/fig--> attempts of $\alpha = 12$ and <!--fig:zk_note_fold_alpha6_s-->2.33<!--/fig--> s at the <!--fig:mask_attempts_alpha6-->7.5<!--/fig--> of $\alpha = 6$ (§5.6), or <!--fig:zk_note_fold_karney_s-->1.91<!--/fig--> s with Karney's exact sampler at <!--fig:mask_karney_sample_ns-->300<!--/fig--> nanoseconds. <!--claim:mask_fold_small_fraction:b1798f-->An ordinary user proof of two to four dozen rank-13 steps over Pasta is <!--fig:zk_note_proof24_s-->23.9<!--/fig--> to <!--fig:zk_note_proof48_s-->47.8<!--/fig--> s of prover at the page's rates, so the fold is under three percent of it, and on a phone a few seconds; §5.8 moves the attempts and the obligations off the device's critical path.<!--/claim--> The merge circuit sees only the accepted attempt.
- Challenge set. $d = 512$ is the accumulation matrix's ring dimension in Akita's catalog at this geometry, so weight-20 ternary challenges there cost nothing and give $2^{138}$ choices. In dimension 128 weight 32 is needed for $2^{130}$, and in dimension 64 ternary challenges give only about $2^{101}$. Wider coefficients at fixed positions are cheaper to apply in a circuit, since the positions are constants, at the price of a larger $\|c\|_1$.
- Gaussian sampling must be within statistical distance about $2^{-\lambda}$ of $D^N_\sigma$ for the theorem to apply as stated, and at $\sigma \approx 2^{23}$ double precision alone is not enough. The sampler assumed here is a rounded continuous Gaussian with Sheppard's correction, $\sigma' = \sigma - 1/(24\sigma)$. Jeudy (ePrint 2026/2583, Theorem 3.1) shows that it is the discrete Gaussian of width $\sigma$ at any centre to within a Rényi divergence of order $a$ of $1 + 73aN/(33{,}177{,}600\,\sigma^8)$. That is below $2^{-<!--fig:mask_rounded_divergence_log2-->179<!--/fig-->}$ over the $N$ coordinates here, so the proof replaces the real mask by the ideal discrete one at no loss. Hülsing, Lange and Smeets' Box–Muller sampler (PKC 2018, ePrint 2017/1025) takes <!--fig:hls18_sample_ns_min-->7.7<!--/fig--> to <!--fig:hls18_sample_ns_max-->13<!--/fig--> nanoseconds a coordinate measured, without and with its randomness, and the <!--fig:mask_sample_ns-->20<!--/fig--> here adds the boundary check and the scaling. What double precision cannot do is round exactly. A coordinate's error is its size times $2^{-53}$, which leaves about $2^{-<!--fig:mask_double_undecided_log2-->25<!--/fig-->}$ of the coordinates undecided between two integers, one coordinate in $2^{<!--fig:mask_double_undecided_fold_log2-->3<!--/fig-->}$ folds. That fraction is also the PKC 2018 paper's worst-case bound on the divergence the error would leave, far from $2^{-\lambda}$. Refining those coordinates in higher precision makes the rounding exact. Karney's exact method is the alternative, at about <!--fig:mask_karney_sample_ns-->300<!--/fig--> nanoseconds a coordinate (Du, Fan and Wei, arXiv 2008.03855, measured his RandomLib sampler at <!--fig:karney_ns_min-->290<!--/fig--> to <!--fig:karney_ns_max-->470<!--/fig-->).
- Where refinements change these figures. The rank rests on the single shared matrix of §5.2; a design that checked the masked fold under a matrix of its own would confine the rank to the zero-knowledge layer, but the switch between matrices has to be proved, and §5.9 finds that proof to cost a linear-size verifier or an in-circuit opening. The digit count $J$ follows from the base, from $\alpha = 48$ and from $\|c\|_1$; a Pasta profile of Akita with another base, a smaller $\alpha$ at the price of more rejections, or sparser challenges changes it, and Akita's $\ell_\infty$ certification may price the unmasked parts more favourably (§5.5). The witness size is the example's, three vectors of $2^{14}$ coefficients, so the 14 Mbytes is four times larger at $2^{16}$.

### 5.5 Checking the ranks with Akita's estimator

The rank rows of §5.3 come from Akita's own SIS estimator, the component of its planner that sizes every matrix: repository `LayerZero-Labs/akita` at commit 60b82bc30f4f8f1130ccd71fe10b0b9bed909ab9 (2026-10-09, Apache-2.0 or MIT), crate `akita-sis-estimator`, Euclidean path, configuration `akita_euclidean_table` (ADPS16 quantum Core-SVP, 128-bit floor). The driver `pasta_rank.rs` beside this note, added as an example to a scratch clone, takes the Pallas base-field prime, $2^{22}$ columns, and a Euclidean collision bound, and binary-searches the least number of scalar rows reaching 128 bits. One adjustment: the estimator reports infinity when the BKZ block it needs exceeds the lattice dimension it chose, which at tiny row counts hides a trivial attack in a larger sublattice. The driver therefore takes the cheapest attack over the estimator's own dimension and a ladder of explicit ones.

| $\log_2$ of collision bound | rows at Pasta | rows at $q_{64}$ | rows at $q_{128}$ | commitment bits |
|---|---|---|---|---|
| 20 | 79 | 312 | 156 | 20.0K |
| 24 | 113 | 448 | 224 | 28.7K |
| 27 | 143 | 567 | 284 | 36.3K |
| 32 | 201 | 797 | 399 | 51.1K |
| 36 | 254 | 1008 | 504 | 64.5K |
| 41.6 | 340 | 1346 | 673 | 86.3K |
| 42.2 | 349 | 1385 | 693 | 88.6K |
| 42.6 | 356 | 1412 | 706 | 90.4K |
| 43.2 | 366 | 1452 | 726 | 92.9K |
| 44 | 380 | 1506 | 753 | 96.5K |
| 48 | 452 | 1792 | 896 | 114.8K |

Every row sits at BKZ block size 484 to 486, and the commitment bits agree across the three moduli to within half a percent, which is §5.2 made concrete; the two §5.3 rows are in the ratio 2.44, against 2.45 by the rule. Cross-checks:

- The pinned Python lattice-estimator in Akita's `third_party` submodule, run under Sage with `sage-sis-check.py` beside this note, gives the same Pasta figures. At $2^{27}$, 143 rows give 128.26 bits with block 484 in dimension 2690, and 142 rows give 126.94. At $2^{41.6}$, 340 rows give 128.53 with block 485 in dimension 4151, and 339 rows give 128.00. The Rust estimator ports the same formula, so this checks the port and the driver, not the cost model.
- A shipped schedule, `artifacts/schedules/fp128_dense.aks` row 0, has a Euclidean terminal instance with collision bound $2^{22}$, ring dimension 64, rank 3, width 256, so 192 rows. The same path says 189 rows are needed at $q_{128}$, and 192 is the least multiple of 64 above it: the driver reproduces the planner's choice on an instance the planner chose.
- The catalog security report covers 115 schedule rows across the three moduli and passes its own check; every weakest instance is a coefficient-$\ell_\infty$ instance at the 128.26-bit floor. For the root inner matrix of `fp128_onehot_recursive`, ring dimension 512, rank 1, width 131072, $\ell_\infty$ bound 835380, the $\ell_\infty$ estimator reports at least 128.26 bits at dimensions 512 and 384 and 84.0 bits at 256. So 512 is the least power of two that meets the floor.
- The six compression maps of the paper's Table 5, rank one with $\ell_\infty$ bound one, pass the 128-bit floor under the proven-pruned profile; the paper states at least 147 bits for them.

This checks that the §5.3 ranks are what Akita's estimator gives for the stated Euclidean bounds at a 254-bit modulus, and that its behaviour there is continuous with the paper's moduli. It does not check the collision bounds themselves, which rest on this note's assumptions about the witness, the challenge set, and the extraction slack. Nor does it check the $\ell_\infty$ route, which Akita prefers for digit-bounded witnesses and which may price the unmasked parts more favourably. Proof sizes at a Pasta modulus are the subject of `pasta-proof-size.md` beside this note.

### 5.6 Cutting the masked bound

The bound of §5.2 is $2 \cdot \|c - c'\|_1 \cdot 2 \cdot \|z\|_2$ with $\|z\|_2 \approx 2\sigma\sqrt{N}$ and $\sigma = \alpha \|c\|_1 \|s\|_2$, and the rank grows as the square of its logarithm. Two of its inputs are choices. A narrower Gaussian, smaller $\alpha$, costs rejection attempts, about $\exp(12/\alpha + 1/(2\alpha^2))$ of them. A challenge set of smaller $\ell_1$ norm needs a larger ring dimension to keep $2^{128}$ challenges; the accumulation matrix's ring dimension in Akita's catalog is 512 at the $2^{14}$ geometry and 1024 above it, so the weight-20 ternary challenges in dimension 512 that §5.3 assumes are available without any change; weight 32 in dimension 128 is the alternative at a smaller ring. Each bit off the bound takes about five percent off the rank, and the masked coordinate width $14\sigma$ sets the digits $J$ per coordinate, so the accumulator handed to the aggregator shrinks only when a whole digit goes. At $N = 2^{22}$:

| α | ‖c‖₁ and the challenge set | attempts | log₂ β | rank factor | coordinate bits | J | masked accumulator |
|---|---|---|---|---|---|---|---|
| 96 | 20 (d = 512, weight 20, $2^{138}$ challenges) | 1.1 | 43.2 | 2.56 | 27.7 | 10 | 15.7 Mbytes |
| 48 (§5.3) | 20 (d = 512, weight 20, $2^{138}$ challenges) | 1.3 | 42.2 | 2.45 | 26.7 | 9 | 14.2 Mbytes |
| 24 | 20 (d = 512, weight 20, $2^{138}$ challenges) | 1.7 | 41.2 | 2.33 | 25.7 | 9 | 14.2 Mbytes |
| 12 | 20 (d = 512, weight 20, $2^{138}$ challenges) | 2.7 | 40.2 | 2.22 | 24.7 | 9 | 14.2 Mbytes |
| 6 | 20 (d = 512, weight 20, $2^{138}$ challenges) | 7.5 | 39.2 | 2.11 | 23.7 | 8 | 12.6 Mbytes |
| 4 | 20 (d = 512, weight 20, $2^{138}$ challenges) | 20.7 | 38.6 | 2.05 | 23.1 | 8 | 12.6 Mbytes |
| 12 | 32 (d = 128, weight 32, $2^{132}$ challenges) | 2.7 | 41.6 | 2.37 | 25.4 | 9 | 14.2 Mbytes |
| 6 | 32 (d = 128, weight 32, $2^{132}$ challenges) | 7.5 | 40.6 | 2.26 | 24.4 | 9 | 14.2 Mbytes |
| 12 | 16 (d = 1024, weight 16, $2^{132}$ challenges) | 2.7 | 39.6 | 2.15 | 24.4 | 9 | 14.2 Mbytes |
| 6 | 16 (d = 1024, weight 16, $2^{132}$ challenges) | 7.5 | 38.6 | 2.04 | 23.4 | 8 | 12.6 Mbytes |

The page's choice, and §5.3's, is $\alpha = 48$ with the weight-20 challenges. A narrower mask saves rank. $\alpha = 12$ takes the factor from 2.45 to 2.22 for <!--fig:mask_attempts_alpha12-->2.7<!--/fig--> attempts instead of <!--fig:mask_attempts-->1.3<!--/fig-->; $\alpha = 6$ brings 2.11 and a masked accumulator of 12.6 Mbytes for <!--fig:mask_attempts_alpha6-->7.5<!--/fig--> attempts at about <!--fig:zk_note_attempt_alpha6_s-->0.31<!--/fig--> s each; and $\alpha = 4$ buys little more for three times the attempts. A wider one saves attempts, which cannot fall below one while the rank keeps growing, and from $\alpha = 59$ the coordinates take a tenth slice. The page's transaction measure prices the user's whole chain, and in it each attempt commits the whole mask. It finds its least between 64 and 130 across its applications at this sampler, with 48 within three percent of it (its zero-knowledge section). It does not price the rows term on the public merges or the aggregator's range checks over an extra slice, which both favour the narrower mask, so 48 is where it stops. These figures move the prover's commitment work and the zero-knowledge layer's accumulator, not the final proof, which §5.2 leaves nearly unchanged. The $\sqrt{N}$ in $\|z\|_2$ is the larger term, and §5.7 considers masking in blocks to reduce it.

### 5.7 Masking in blocks

The $\sqrt{N}$ in $\|z\|_2$ is the price of masking the whole vector at one width (§2.4). Masking block by block, $z_b = y_b + c_b s_b$ over $B$ blocks of $N_b = N/B$ digits, replaces $\sqrt{N}$ by $\sqrt{N_b}$: at $B = 256$ that is four bits off the bound, a rank factor of 2.00 instead of 2.45 with §5.3's parameters, or 1.70 instead of 2.11 at $\alpha = 6$, and 23-bit coordinates, eight digits, an accumulator of 12.6 Mbytes. The difficulty is making the rejection test independent per block. A rejected block resamples its mask, which changes the mask's commitment and so the challenge; with one challenge for every block, one rejection restarts them all, and the acceptance probability $M^{-B}$ vanishes. Two ways around it:

- Per-block challenges. A challenge $c_b$ per block, derived from $C_{y_b}$, lets each block retry alone. But the fold identity $A z_b = A y_b + c_b A s_b$ needs the block's own inner image $A s_b$, and the accumulator's commitment binds only the outer commitment of the concatenated images, $\sum_b B_b t_b$ (Akita §4.5). With distinct $c_b$ the verifier cannot form $\sum_b c_b B_b t_b$ from the one outer commitment. So the accumulator would carry $B$ commitments per committed vector instead of one: compressed, 128 bytes each, 32 kbytes per vector at $B = 256$, six vectors per step, and the merge absorbs them all, about 12,000 atoms against 180. The claims split the same way, into per-block partials, $B$ per claim point, which Akita's terminal already uses. At $B = 16$ the saving is two bits and one digit, and the cost 16 commitments per vector and about 700 more atoms in the zero-knowledge layer's merge. Not attractive.
- One challenge, candidate masks. Keep one $c$, but sample $k$ candidate masks per block before the challenge, bind all of them, derive $c$, and take for each block the first candidate that passes the rejection test against $c s_b$, publishing the index. The index leaks nothing: the theorem of §2.2 makes the accepted output and the acceptance probability independent of the secret, so the index is geometric with parameter $1/M$ whatever $s$ is. The probability that some block exhausts its $k$ candidates is about $B (1 - 1/M)^k$; at $B = 256$ and $M = 1.3$, $k =$ <!--fig:note_blocks_k-->9<!--/fig--> leaves $2^{-10}$. The cost is $k$ times the mask sampling and the binding of $kB$ candidate masks before the challenge. Akita's compression maps are linear, so the binding can be a Merkle tree over the candidates' compressed images, with the $B$ chosen leaves opened in the merge circuit and summed: 256 paths of about 14 hashes, a million gates, plus 256 images of 128 bytes absorbed, about a thousand atoms, in the zero-knowledge layer's merge only. A single lattice commitment to all candidates with the selection proven as a linear relation would be cheaper and is a further design. The masks' commitments are the same $Ay$ as before, so the extraction argument and the bound are unchanged apart from $\sqrt{N_b}$.

The second route is the one worth pursuing, if the candidate binding can be made cheap; it is open. Either way these figures move the prover's commitment work and the zero-knowledge layer's accumulator and merge, not the final proof.

### 5.8 The user's online cost

<!--claim:mask_fold_phone_seconds:a8efc2-->The fold of §3 runs once per transaction on the user's device: the <!--fig:zk_note_fold_s-->0.405<!--/fig--> s of §5.4 on a fast core, a few seconds on a phone, which is still worth moving off the critical path.<!--/claim--> Two changes move nearly all of it.

- Precomputed candidate masks. The masks depend on neither the witness nor the transaction, so the device samples a batch of $k$ masks $y_1, \ldots, y_k$ and commits to them, $C_{y,i} = A y_i$, in idle time. At transaction time the batch is bound into the transcript, the challenge $c$ is derived, and the first candidate that passes the rejection test against $cs$ is used, with its index published: the second route of §5.7, across attempts rather than blocks. The index leaks nothing, since the acceptance probability does not depend on the secret. The batch is discarded after use: a rejected candidate's rejection is correlated with the secret, and reusing it would fall outside the theorem. A batch of $k$ fails with probability $(1 - 1/M)^k$, one percent at <!--fig:note_batch_alpha48-->4<!--/fig--> candidates for $\alpha = 48$, <!--fig:note_batch_alpha12-->11<!--/fig--> for $\alpha = 12$ and <!--fig:note_batch_alpha6-->33<!--/fig--> for $\alpha = 6$; on failure the device samples online. Extraction rewinds until two transcripts use the same index, $k + 1$ transcripts in the worst case instead of two, which costs about $\log_2 k$ bits of tightness. The merge circuit absorbs the $k$ compressed commitments, four atoms each, and derives $c$ from them.
- Deferred obligations. The decomposition of $z$ into slices, their commitments, and the range and norm proofs of step 7 need not be the user's. The aggregator's first fold decomposes its inputs anyway, and it holds $z$. So the user hands over $z$ itself, with $C_z = C_y + c \cdot C_s$ computed homomorphically, and the aggregator commits the slices and proves the obligations in its own fold, whose merge circuit checks them as §3.3 describes. The user's merge circuit checks only the challenge derivation, the commitment identity and the claim fold. Cross-transaction aggregation is not trusted for privacy, and this changes nothing for it: the aggregator received the slices before, which together are $z$, and it receives $z$ now, which rejection sampling makes independent of $s$; the obligations it now proves are about $z$, which it holds, and they guard the decider against a malformed $z$ rather than the transaction against the aggregator, so it checks $z$'s norm on receipt and refuses a bad one. This is the deferral of open point 7, and it takes nine commitments of $N$ digits and the sum-checks off the device.

What remains online is $z = y + cs$: a ring product by a sparse ternary challenge, 32 additions per coordinate, and one vector addition, about $2^{27}$ additions, a tenth of a second on a phone core; the evaluations $u_i$ of the chosen mask at the claim points; and the transfer of $z$, about <!--fig:note_z_mb-->14 Mbytes<!--/fig--> at <!--fig:note_zinf_bits-->27<!--/fig--> bits per coordinate, 13 Mbytes at $\alpha = 12$ and 12 Mbytes with §5.7's blocks. The transfer is the cost that does not move, since the information content of $z$ is set by the mask's width.

### 5.9 Two matrices: confining the rank to the zero-knowledge layer, and where that stalls

§5.2 charges the masked bound to every step, because every accumulator is committed under the one matrix $A$ whose bound the mask raises, and a smaller matrix for the later folds does not help when it is a prefix of the rows. The other shape is two independent matrices joined by proven equalities, which this section works through to the point where it stalls.

**The design.** Let $A$ be the accumulation matrix at the ordinary bound, 143 rows over Pasta in §5.3, and $A'$ a second matrix sized for the masked bound, <!--fig:note_masked_rows-->349<!--/fig--> rows. The user's own chain runs under $A$, and so do the aggregator's merges. Only the handoff touches $A'$. At the handoff the user commits the last accumulator's witness $s$ again under $A'$, $C'_s = A' s$, and proves that $C_s$ and $C'_s$ open to the same short $s$. The masking fold of §3 then runs under $A'$. The user hands over $z$ decomposed into its slices, each committed under $A$ and proved equal to its $A'$ commitment the same way, and the aggregator's first fold takes the slices as ordinary inputs. The extractor would run in three pieces: the public chain's, under $A$ at the ordinary bound; the masking fold's, by the rewinding of §5.2, under $A'$ at the masked bound; and the user's chain's, under $A$ again; the two switches tie the pieces together. That is not the prefix construction §5.2 rules out, since nothing requires the $A$ identities to cover the $A'$ rows. If it went through, $A'$ would be used twice per transaction and nowhere else: one more wide commitment, about a third of the masking fold of §5.4, and the rows term of every step would return to the ordinary rank.

**The switch must be proved.** It is not enough that the user computes $C'_s$ honestly. The claims $(x_i, v_i)$ folded at the handoff do not bind $s$. A dishonest user can choose a short $s' \ne s$ with $s'(x_i) = v_i$ at the few claim points, which is a system of a few equations in $N$ unknowns, commit $s'$ under $A'$, and hand over a masked $s'$ whose claims pass at the decider. Only the commitment binds the witness, so the switch has to prove that the vector $C'_s$ binds is the vector $C_s$ binds.

**Where it stalls.** Accumulation never recomputes a commitment: binding transfers through fold identities that are linear in the commitments, and that is what a change of matrix forfeits, since no linear map takes $As$ to $A's$. The direct proof of $A' s = C'_s$ for a committed $s$ is a sum-check: the verifier draws $r$, and the prover shows $\langle A'^{\mathsf T} r, s \rangle = \langle r, C'_s \rangle$. That reduces to an evaluation of $s$'s multilinear extension, which the accumulator carries as a claim, together with an evaluation of the multilinear extension of $A'^{\mathsf T} r$ at the sum-check's point, which the verifier must compute itself. For a pseudo-random $A'$ that evaluation is a dense sum over $N$ entries, so the merge circuit that verifies the switch does $\Theta(N)$ work, about as much as committing the witness again. Stacking the matrices instead, so that one commitment carries both blocks and the chain checks only the $A$ block, is the prefix construction of §5.2: a cheating prover fills the unchecked block freely. So the switch costs either a linear-size verifier or a matrix with structure that makes $A'^{\mathsf T} r$'s multilinear extension succinct, and Akita's matrices, expanded from seeds, have no such structure.

**The form that would work, and what it costs.** An opening at the boundary: fold the user's witness down through Akita's own levels to a terminal response short enough that the verifier recomputes its commitment, as the decider does, and have the aggregator's first merge circuit verify that opening. This seals the handoff the way recursion does (the page's zero-knowledge paragraph), and it is a decider's verification inside a step circuit, once per transaction. Its transcript alone is an opening proof of about 85 kbytes to absorb: some $2 \cdot 10^7$ gates with a conventional hash at 14,900 gates per 64 bytes, or about $2 \cdot 10^5$ with Poseidon at 72 gates per atom, before the sum-check arithmetic. What it would save is the rows term on the transaction's steps and merges, a factor of 1.7 to 1.9 on their commitments. For a $2^{17}$-gate transaction over Goldilocks at rank 13 on the page that is about a quarter of a second, against a masking fold of under half a second. So with a conventional hash the opening costs several times what it saves per transaction, and with Poseidon the two are close. System-wide the picture is different, since the rows term is also what every public merge pays, and that is the whole zero-knowledge cost in the page's merge-prover measure.

So the rank stays with the shared matrix for now. The two-matrix design is worth returning to if either a succinct switch exists for a structured $A'$, or an in-circuit opening becomes cheap, which the hash policy of the page decides; open point 10.

## 6. Proof hygiene

- The original Fiat–Shamir-with-aborts analyses had gaps in the treatment of aborted iterations, fixed in 2023 by Devevey–Fallahpour–Passelègue–Stehlé and by Barbosa et al. (both CRYPTO 2023). A proof for the fold should follow a corrected treatment. Two practical consequences: cap the number of attempts, accepting a negligible completeness error, and never publish anything from an aborted attempt.
- The QROM treatment of Fiat–Shamir with aborts for signatures is Kiltz–Lyubashevsky–Schaffner (EUROCRYPT 2018), the natural starting point here, and separate from Akita's own QROM proof, which covers the opening protocol.
- The number of aborts is not in the transcript but is visible to anyone timing the user's device. Minor for a wallet, but to be noted.
- The relaxed openings of §5.2 are a soundness matter, not a zero-knowledge one: whatever NARK runs on top of the lattice accumulation must be sound with respect to relaxed openings of its commitments. That is a property of the whole lattice-Ragu design and out of scope here.

## 7. Open points

1. Add the fold-level randomizer to Ragu's rerandomization step, which its code lists as future work: a uniformly random polynomial with a trivially true claim, folded as an extra claim (§4.3).
2. Add a random coefficient to the trace polynomial per evaluation revealed over its lifetime (§4.2).
3. Stop the handed-over object from carrying the child's commitments and stage polynomials in the clear (§1.1).
4. Write the one-fold statement of §4.3 as a theorem and prove it, DL version first, since its proof is shorter and fixes the statement. The DL proof relies on the partner's own quotient being folded in, which is what makes the map of §1.1 a bijection.
5. Decide the challenge set and get $\|c\|_1$ and the extraction slack from Akita's planner, then redo §5.3 with real numbers.
6. Check that the commutation of evaluation with the challenge in step 6 holds for the packing Ragu would use, or choose the packing so that it does.
7. Settle how the obligations of step 7 are verified, in the user's merge circuit or deferred with Akita's fused range and norm checks, and what each costs in gates; §5.8 argues for the deferral.
8. Decide whether the hiding padding $\rho$ goes into every staged commitment or only into the published ones.
9. Look for a sign-hiding structure that would make the bimodal variant applicable, saving about 3.6 bits of $\beta$ and one digit of $J$.
10. Revisit the two-matrix design of §5.9 if a succinct proof of a change of commitment matrix appears, for instance from a structured matrix, or if an in-circuit Akita opening becomes cheap enough to seal the handoff.

## References

- V. Lyubashevsky. Fiat–Shamir with Aborts: Applications to Lattice and Factoring-Based Signatures. ASIACRYPT 2009. <https://doi.org/10.1007/978-3-642-10366-7_35>
- V. Lyubashevsky. Lattice Signatures Without Trapdoors. EUROCRYPT 2012. <https://eprint.iacr.org/2011/537>, <https://doi.org/10.1007/978-3-642-29011-4_43>. Theorem 4.6 and Lemma 4.4.
- L. Ducas, A. Durmus, T. Lepoint, V. Lyubashevsky. Lattice Signatures and Bimodal Gaussians. CRYPTO 2013. <https://eprint.iacr.org/2013/383>
- C. Gentry, C. Peikert, V. Vaikuntanathan. Trapdoors for Hard Lattices and New Cryptographic Constructions. STOC 2008. <https://eprint.iacr.org/2007/432>. The regularity lemma for discrete Gaussians.
- T. Attema, V. Lyubashevsky, G. Seiler. Practical Product Proofs for Lattice Commitments. CRYPTO 2020. <https://eprint.iacr.org/2020/517>. Relaxed openings and the cross-multiplication binding argument.
- E. Kiltz, V. Lyubashevsky, C. Schaffner. A Concrete Treatment of Fiat-Shamir Signatures in the Quantum Random-Oracle Model. EUROCRYPT 2018. <https://eprint.iacr.org/2017/916>
- J. Devevey, P. Fallahpour, A. Passelègue, D. Stehlé. A Detailed Analysis of Fiat-Shamir with Aborts. CRYPTO 2023. <https://eprint.iacr.org/2023/245>
- M. Barbosa et al. Fixing and Mechanizing the Security Proof of Fiat-Shamir with Aborts and Dilithium. CRYPTO 2023. <https://eprint.iacr.org/2023/246>
- NIST FIPS 204, Module-Lattice-Based Digital Signature Standard (ML-DSA). <https://doi.org/10.6028/NIST.FIPS.204>. The uniform-mask variant in deployment.
- D. Boneh, B. Chen. LatticeFold: A Lattice-based Folding Scheme and its Applications to Succinct Proof Systems. <https://eprint.iacr.org/2024/257>. Decomposition and range checks in a folding verifier.
- Q. Dao et al. Akita: A High-Performance Lattice-Based Polynomial Commitment Scheme. <https://eprint.iacr.org/2026/1983>
- B. Bünz, A. Chiesa, W. Lin, P. Mishra, N. Spooner. Proof-Carrying Data without Succinct Arguments. CRYPTO 2021 (BCLMS). <https://eprint.iacr.org/2020/1618>. Split accumulation, and zero-knowledge accumulation by folding with a random instance.
