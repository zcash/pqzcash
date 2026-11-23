# The epoch's tachygram set: tree, buckets, and polynomials

Zoodles' lineage asks two things of an epoch's set of tachygrams: that a note's commitment is in the
set of the epoch that created it, and that its nullifier is in none of the sets since. Tachyon
answers both from one structure, and that is worth keeping: a second structure for one of the two
checks is more state for the builder and a second proof for the wallet. The builder makes the
structure once an epoch from tachygrams that are public, so inserting into it is never proved in a
circuit; what the wallet proves is one membership and, epoch by epoch, one exclusion. This page
compares the representations that could serve, with the sorted Merkle tree that the [frontier
page](pareto-template.html#transaction-prover) prices as the one to beat. The [Zoodles](zoodles.md)
page gives the lineage's place in the protocol.

## The sorted tree

The builder sorts the epoch's <!--fig:zoodles_epoch_tachygrams-->1,048,576<!--/fig--> tachygrams and
hashes consecutive pairs into the leaves of a Merkle tree. Membership is a leaf and its path.
Exclusion is the leaf whose two neighbours straddle the nullifier, its path, and two 256-bit
comparisons: <!--fig:tree_hashes_20-->21<!--/fig--> hashes. The representation is exact. A
non-member is always provably absent, so no honest note can be frozen, and nothing an attacker
publishes changes that.

## Set polynomials

Tachyon's structure is a polynomial whose roots are the tachygrams, split into buckets by a
quadratic-residue profile, each bucket a committed polynomial opened at the nullifier. A root is a
field element, so the field must hold a 256-bit tachygram: Pallas itself in Tachyon, and over
Kishu's 64-bit modulus a quartic extension, in which a root costs nine base multiplications. The
wallet folds the bucket's contents every
epoch, <!--fig:zoodles_bucket_digits-->2.10 million<!--/fig--> digits
for <!--fig:zoodles_bucket_coeffs-->8,192<!--/fig--> tachygrams, against the
tree's <!--fig:app_zoodles_epoch_kishu-->332,000<!--/fig-->.

The extension could be avoided by shortening the tachygrams, to 128 bits say, so that the
polynomials live in Kishu's claim field. Secrecy does not protect a compression: a tachygram is
public in the mempool before it is final, and an attacker who sees it there can grind a colliding
image into an output or a nullifier of their own and have it mined first, a roadblock. Against one
target that costs $2^{128}$ classically and a Grover search of depth $2^{64}$, which the usual depth
limits put out of reach, so a compression to 128 bits survives the roadblock on that reading. It
does not survive the multi-target version of the membership check: an attacker who wants a note
whose compressed commitment lands on any of the $N$ commitments ever created, $2^{30}$ or more over
the chain's life, pays $2^{128}/N$, below $2^{100}$, and the search needs no race. So a compressed
set can serve exclusion, whose targets are only the nullifiers in flight, but not membership, and
the two checks part company: the simplification is lost. A product over a committed multiset at
challenges drawn after the commitment, $\prod_i (\zeta - t_{\mathrm{lo},i} - \beta\,
t_{\mathrm{hi},i})$, binds the halves by the challenge rather than by a compression and has no
target to grind, but it needs the tachygrams committed rather than the polynomial's coefficients,
which is not Tachyon's technique either.

## A bucketed table

The non-membership accumulator proposed for Zcash in 2019
([zcash/zcash#4062](https://github.com/zcash/zcash/issues/4062)) is a hash table: a tachygram goes
to one of $2^B$ buckets by its $B$-bit prefix, a bucket holds up to $K$ suffixes of $N - B$ bits,
and the buckets are the leaves of a tree of depth $B$. A note whose nullifier finds its bucket full
is treated as spent, so the table is an approximate set: an exact collision or a full bucket is a
false positive that destroys an honest note. The issue left the choice of $B$ and $K$ for later.

Take $m$ tachygrams as uniform $N$-bit strings. The exact collisions have probability about $m^2 /
2^{N+1}$, negligible at $N = 256$. A bucket's load is binomial with mean $\mu = m / 2^B$, Poisson at
these sizes, and by a union bound over the buckets the probability that any bucket overflows is at
most $2^B \cdot \Pr[\mathrm{Poisson}(\mu) \ge K + 1]$. This is the maximum load of balls thrown into
bins in its heavily loaded case, $m \gg 2^B$, where the typical maximum is $\mu + \sqrt{2\mu \ln
2^B}$ [[RS98](#ref-rs98), [BCSV06](#ref-bcsv06)]; a bound of $2^{-64}$ on losing any note sits far
out in the tail, and that is what sets $K$. The least $K$ with the bound below $2^{-64}$ and
$2^{-128}$, and the exclusion proof's hashes at the first, the $B$ path hashes plus the bucket's $K
(N - B)$ bits at 512 a compression:

| tachygrams | prefix bits $B$ | mean load $\mu$ | $K$ at $2^{-64}$ | $K$ at $2^{-128}$ | proof hashes, table | sorted tree |
|---|---|---|---|---|---|---|
| $2^{20}$ | 16 | 16 | <!--fig:bucket_k64_20_16-->72<!--/fig--> | <!--fig:bucket_k128_20_16-->98<!--/fig--> | <!--fig:bucket_hashes_20_16-->50<!--/fig--> | <!--fig:tree_hashes_20-->21<!--/fig--> |
| $2^{20}$ | 18 | 4 | <!--fig:bucket_k64_20_18-->39<!--/fig--> | <!--fig:bucket_k128_20_18-->56<!--/fig--> | <!--fig:bucket_hashes_20_18-->37<!--/fig--> | <!--fig:tree_hashes_20-->21<!--/fig--> |
| $2^{20}$ | 20 | 1 | <!--fig:bucket_k64_20_20-->24<!--/fig--> | <!--fig:bucket_k128_20_20-->37<!--/fig--> | <!--fig:bucket_hashes_20_20-->32<!--/fig--> | <!--fig:tree_hashes_20-->21<!--/fig--> |
| $2^{34}$ | 32 | 4 | <!--fig:bucket_k64_34_32-->43<!--/fig--> | <!--fig:bucket_k128_34_32-->60<!--/fig--> | <!--fig:bucket_hashes_34_32-->51<!--/fig--> | <!--fig:tree_hashes_34-->35<!--/fig--> |
| $2^{34}$ | 34 | 1 | <!--fig:bucket_k64_34_34-->27<!--/fig--> | <!--fig:bucket_k128_34_34-->40<!--/fig--> | <!--fig:bucket_hashes_34_34-->46<!--/fig--> | <!--fig:tree_hashes_34-->35<!--/fig--> |

Even <!--claim:bucket_table_dearer:8b56f1-->at one expected tachygram a bucket the capacity has to
be <!--fig:bucket_k64_20_20-->24<!--/fig--> for the bound to hold, the bucket alone is a dozen
compressions, and in every row the table's proof is at least ten hashes more than the
tree's.<!--/claim-->

The issue's second idea is to make the bucket's contents approximate too. Storing a $T$-bit tag of
each suffix adds a within-bucket collision term of about $m \mu / 2^{T+1}$, so $T \approx \log_2 m +
\log_2 \mu + \lambda$: <!--fig:bucket_tag_bits_20_16-->87<!--/fig--> bits at $2^{20}$ tachygrams,
$\mu = $ <!--fig:bucket_mu_20_16-->16<!--/fig--> and $2^{-64}$, which brings that row's proof
to <!--fig:bucket_tag_hashes_20_16-->29<!--/fig--> hashes, still above the tree's. Placing each
tachygram in the emptier of two buckets [[ABKU99](#ref-abku99)] brings the maximum load down to $\mu
+ O(\log \log 2^B)$, but an exclusion proof must then show absence from both buckets, two paths, and
gives back the saving. Bloom and cuckoo filters [[Blo70](#ref-blo70), [FAKM14](#ref-fakm14)] make
the same trade in another shape; their false positives are frozen notes rather than forged ones, so
they are admissible in principle, and larger than the tree at these sizes.

The table has an adversary the tree has not. Filling a bucket is finding $K$ less its load
tachygrams with one prefix, and grinding a prefix is free at these $B$, so a roadblock attacker who
sees a nullifier in the mempool needs that many spends of their own mined before it. With $K$ in the
dozens that is dozens of fees and a block's time, a real cost, but one the tree does not ask the
design to rely on.

## What the table was for

The table's merit is authenticated insertion: "assert absent, then insert" in a circuit, for an
accumulator updated one nullifier at a time, which is the setting the issue was written for.
Merklized balanced trees do the same at about $1.44 \log_2 m$ hashes an insertion
[[RMCI17](#ref-rmci17)]. In Zoodles nothing is inserted in a circuit: the builder makes each epoch's
structure from public tachygrams, so the sorted tree's exactness and its shorter proof come free,
and it serves membership and exclusion alike. That is why the frontier page prices the lineage by
the tree. The analysis above is recorded so that the alternative need not be re-derived.

## References

- <a id="ref-rs98"></a>[RS98] Martina Raab, Angelika Steger. "Balls into Bins": A Simple and Tight
  Analysis. RANDOM 1998. <https://doi.org/10.1007/3-540-49543-6_13>
- <a id="ref-bcsv06"></a>[BCSV06] Petra Berenbrink, Artur Czumaj, Angelika Steger, Berthold Vöcking.
  Balanced Allocations: The Heavily Loaded Case. SIAM Journal on Computing 35(6), 2006.
  <https://doi.org/10.1137/S009753970444435X>
- <a id="ref-abku99"></a>[ABKU99] Yossi Azar, Andrei Z. Broder, Anna R. Karlin, Eli Upfal. Balanced
  Allocations. SIAM Journal on Computing 29(1), 1999. <https://doi.org/10.1137/S0097539795288490>
- <a id="ref-blo70"></a>[Blo70] Burton H. Bloom. Space/Time Trade-offs in Hash Coding with Allowable
  Errors. Communications of the ACM 13(7), 1970. <https://doi.org/10.1145/362686.362692>
- <a id="ref-fakm14"></a>[FAKM14] Bin Fan, David G. Andersen, Michael Kaminsky, Michael D.
  Mitzenmacher. Cuckoo Filter: Practically Better Than Bloom. CoNEXT 2014.
  <https://doi.org/10.1145/2674005.2674994>
- <a id="ref-rmci17"></a>[RMCI17] Leonid Reyzin, Dmitry Meshkov, Alexander Chepurnoy, Sasha Ivanov.
  Improving Authenticated Dynamic Dictionaries, with Applications to Cryptocurrencies. Financial
  Cryptography 2017. <https://eprint.iacr.org/2016/994>
- <a id="ref-mu17"></a>[MU17] Michael Mitzenmacher, Eli Upfal. Probability and Computing:
  Randomization and Probabilistic Techniques in Algorithms and Data Analysis, second edition.
  Cambridge University Press, 2017. The Poisson approximation to balls into bins.
