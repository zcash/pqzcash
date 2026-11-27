# Kishu's arithmetization

Kishu is a proof-carrying-data scheme in Ragu's shape. An application is a tree of nodes. Each node
is a circuit that takes the public headers of its input nodes, checks whatever the application
needs, and publishes a header of its own. The scheme attests that every node in the tree was
satisfied, so that a verifier checks one proof for the whole tree. What differs from Ragu is what a
node's circuit is written over. This page describes a node's circuit as its writer sees it, then the
pieces Kishu is built from, the costs the [frontier page](pareto-template.html#kishu) prices it by,
and the differences from Ragu's arithmetization. Every figure is the model's ([Regenerating the
Study's Numbers](REGENERATING.md)).

## Kishu as a Proof-Carrying-Data scheme

A node's circuit has:

- a witness, the values its prover knows;
- a header, the values the node publishes, which the scheme carries to the node above; and
- the headers of its input nodes, which the scheme attests.

The circuit's writer states constraints over these three, and the scheme guarantees that a proof of
the node exists only if the constraints hold and the input nodes were proved. A transaction is
formed from a tree of nodes, as in Tachyon: a node for each spend and each output, nodes that
combine them, and a node that fixes the fee, with the root's proof the transaction's. (For
efficiency we distinguish nodes in the PCD graph from steps of the accumulation scheme, discussed
below: a step is what the prover commits at once, and several nodes can share one.)

## The arithmetization

Let $q$ be a fixed prime; $q = 2^{64} - 59$ for the modelled parameters. Write
$\innerprod{\mathbf{x}}{\mathbf{y}} = \mathbf{x}^{\mathsf{T}} \mathbf{y}$ for the inner product of
two column vectors over the field $\mathbb{F}_q$. A matrix in $\mathbb{F}_q^{r \times c}$ has $r$
rows and $c$ columns, so that premultiplying by it takes a column vector in $\mathbb{F}_q^c$ to one
in $\mathbb{F}_q^r$.

Consider a Kishu circuit over $\mathbb{F}_q$ with $m$ constraints. The public inputs, padded to
length $m$ with zeros, form the instance vector $\mathbf{v} \in \mathbb{F}_q^m$. A witness is a
vector of $N$ small integers, $\mathbf{w} \in \mathbb{Z}^N$, read as elements of $\mathbb{F}_q$. The
circuit fixes each position's alphabet: a bit, in $\{0, 1\}$; a dibit, in $\{-2, -1, 0, 1\}$; or a
tribit, in $\{-4, \ldots, 3\}$, Akita's own balanced base-8 digit. The entries are called digits.

The circuit is defined by, for each constraint index $j$,

- fixed (typically sparse) coefficient matrices
  $\mathbf{A}_j, \mathbf{B}_j \in \mathbb{F}_q^{t_j \times N}$, where $t_j \geq 0$; and
- a fixed coefficient row vector $\mathbf{c}_j \in \mathbb{F}_q^{1 \times N}$.

The constraint at index $j$ requires this equality in $\mathbb{F}_q$:

$$\innerprod{\mathbf{A}_j \mathbf{w}}{\mathbf{B}_j \mathbf{w}} + \mathbf{c}_j \mathbf{w} = \mathbf{v}_j.$$

In words: each row of $\mathbf{A}_j$ and the matching row of $\mathbf{B}_j$ give two linear
combinations of the digits in $\mathbb{F}_q$, which are multiplied. These products are added up over
the $t_j$ rows, together with one more linear combination of the digits given by $\mathbf{c}_j$. The
total must equal the constraint's entry of $\mathbf{v}$. So a constraint is a polynomial of degree
at most two in the digits, with no constant term, set equal to zero or to a public input. Leaving
out the constant term loses no generality: if one public input is the constant 1 and one witness bit
is constrained to equal it, a constant term in any constraint is a multiple of that bit.

That every entry of $\mathbf{w}$ lies in its alphabet is enforced for the whole witness at once by a
range check, not by a constraint per digit. For the bit positions it is the Booleanity check.

### Relation to R1CS

This is a generalization of R1CS over $\mathbb{F}_q$ with several products allowed in one
constraint. The digits' range constraints are implicit.

### Relation to CCS

CCS [\[STW23\]](#ref-stw23) writes a whole constraint system as one vector equation over
$\mathbf{z} = (\mathbf{w}, 1, \mathbf{x})$, the witness, the constant 1, and the public inputs:

$$\sum_i c_i \cdot \bigcirc_{j \in S_i} \mathbf{M}_j \mathbf{z} = \mathbf{0}.$$

The $\mathbf{M}_j$ are fixed matrices, each $S_i$ is a multiset of their indices of size at most the
degree $d$, $\bigcirc$ is the Hadamard (entrywise) product between vectors, and the $c_i$ are
constants.

Read row by row at degree two, that is the form above. Each $S_i$ then names one or two matrices.
For a pair, their rows at a constraint, the first scaled by $c_i$, are a row of $\mathbf{A}_j$ and
the matching row of $\mathbf{B}_j$. The single matrices, scaled, sum to $\mathbf{c}_j$. A $t_j$ that
varies with $j$ is the same as padding $\mathbf{A}_j$ and $\mathbf{B}_j$ with zero rows up to a
fixed number.

CCS puts the constant 1 and the public inputs inside $\mathbf{z}$, where they can enter the
products. Here the witness is small digits and the public inputs stand on the right-hand side. A
constant or an input that a product needs is first copied into witness digits by a linear
constraint. CCS allows degrees above two; here the degree is two.

### Relation to Universal Constraint Systems

Universal Constraint Systems [\[AGK+26\]](#ref-agk26) are the constraint systems of Zinc+, over
polynomial rings in general. Over the integers they are the constraint systems of Zinc
[\[GWHD25\]](#ref-gwhd25): CCS on a witness of bounded integers, with lifted moduli. The relations
are proved by projecting them to a random prime field for the PIOP, so that one constraint system
serves any moduli. That is what makes them universal. BitZ [\[BGK+26\]](#ref-bgk26) proves integer
polynomial constraints the same way.

Kishu keeps the shape of the constraints and the small integers as witness, but evaluates the
constraints in $\mathbb{F}_q$ itself. Its fingerprint route is Zinc's method, the relations checked
in instances over random primes; its limb route is not, holding the relations over the integers by
keeping the left-hand side of each constraint within a range no larger than $q$.

### Relation to Ragu

Ragu's arithmetization is the constraint system of Bootle et al. [\[BCC+16\]](#ref-bcc16), over the
Pallas base field and with a fourth wire added to each gate. A circuit of $n$ gates has four wires a
gate, each gate enforcing $\mathbf{a}_i \mathbf{b}_i = \mathbf{c}_i$ and
$\mathbf{c}_i \mathbf{d}_i = 0$, and $4n$ linear constraints, each a fixed linear combination of all
the wires equal to an instance value ([Ragu's arithmetization
chapter](https://tachyon.z.cash/ragu/protocol/construction/arithmetization.html)).

Kishu's wires are digits of one to three bits rather than field elements, so a boolean value needs
no gate. Constraints are over the 64-bit $\mathbb{F}_q$, not a Pallas-sized field. Its constraints
are not gates of a fixed shape with a fixed number of linear constraints, but quadratic constraints
with any number of products each, as above. In both Ragu and Kishu, the public inputs enter as
instance values.

## Writing circuits

The writer pays per digit of witness, per product, and a little per nonzero coefficient — less for a
small one, such as the powers of two that assemble a word from its digits. A sum-check could take
higher degrees at a cost per degree, but the model charges degree two. Fusing Keccak's steps into
cubic constraints was found not to pay; a term of higher degree costs an intermediate witness value
instead.

A digit's width is the writer's choice, position by position. A value that is a factor of a product
needs the width the product needs: a bit, in the hashes. A value that enters constraints only
through linear combinations is written in tribits. That is any integer word: a limb, a quotient, a
carry, an amount, or an element of $\mathbb{F}_q$. A dibit or a bit takes the remainder if the width
is not a multiple of three. The commitment, the fold, and the mask cost the same per digit at any of
these widths. The range check costs one product a bit, two a dibit, and four a tribit, by Akita's
paired predicate. So a tribit holds three bits for a little over a third of their cost.

A word of $\ell < 64$ bits is a linear combination of its digits plus a constant, which costs
nothing to form. The constant offsets the balanced digits. Bit vectors of any fixed length can be
represented directly, as can elements of $\mathbb{F}_q$ (non-canonically,
in <!--fig:q64_digits-->22<!--/fig--> digits). A range check is free: a value held in digits of
$\ell$ bits in all is below $2^\ell$ by construction.

Since a word is a linear combination in certified digits, a relation holds over the integers
whenever it holds in $\mathbb{F}_q$, provided that its two sides, as integers, both lie in a range
no larger than $q$, so that they cannot differ by a multiple of $q$. That is how integer arithmetic
is written. Adding a value in $[0, u]$ to one in $[0, v]$ is safe whenever $u + v < q$, for example.
A 32-bit addition is $a + b = s + 2^{32} c$ with the sum and the carry committed, and a comparison
is a subtraction's carry. A multiplication of two words costs one product term; a constant costs by
its nonzeros.

Arithmetic in a prime field other than $\mathbb{F}_q$, such as Pasta's base field, is a relation
with a committed quotient. Each multiplication carries a quotient and carries, which Kishu commits
as tribits. An R1CS emulation of the same arithmetic pays mostly for the boolean constraints on the
bits of those values, which Kishu's digits do not need, so in Kishu's arithmetization it is
expensive but not prohibitively so.

Bit operations are a term each: XOR is $z = x + y - 2xy$ and AND is $z = xy$; rotations and shifts
are wiring and cost nothing. A result needs committing only where it is a factor of a later product.
A result used linearly, as an addend or as a hash's output, stays an expression inside the
constraint that uses it. In a chain of XORs every other word is committed, each certified against
both XORs' inputs at once at two terms a bit. A third XOR in a chain would need degree three.
Bitwise operations keep bits. A dibit XOR is degree two only with a committed quotient digit, which
is pinned only by committing the reduced result. Tribits have no degree-two XOR at all. So a BLAKE3
compression is <!--fig:blake3_bits-->11,344<!--/fig--> bits of witness
and <!--fig:blake3_piop_terms-->11,120<!--/fig--> terms, a multiplication in $\mathbb{F}_q$ is one
term over 64-bit operands, and a Pasta multiplication
is <!--fig:mult_fingerprint_digits-->170<!--/fig-->
or <!--fig:mult_limbs_digits-->374<!--/fig--> digits by one of two routes. The circuits that suit
Kishu are the hash-heavy ones.

A step is one committed witness of a chosen length in digits, with one evaluation claim, since the
constraints are a sum-check over the whole table. The frontier page's rows are at lengths
from <!--fig:bits_q64_min_step-->$1.5 \times 2^{20}$<!--/fig-->
to <!--fig:kishu_max_step-->$1.875 \times 2^{25}$<!--/fig--> digits. A transaction's first step
holds the application alone. In each later step the merge's digits take the first part, and the
application's nodes fill the rest, as many as fit, as the [Zoodles](zoodles.md) page's packing
shows. Zero knowledge asks nothing of the circuit's writer: the scheme hides the witness, and no
randomizer or blinding wire is needed. Not available: lookup arguments, which the study does not
model.

## What Kishu is made of

Kishu is an arithmetization in [BitZ](pareto-template.html#bitz)'s style over
[Akita](pareto-template.html#akita)'s commitment scheme.

Akita is a lattice-based polynomial commitment scheme, secure under the Module-SIS assumption: it
commits to a vector of small integers, its digits, by an Ajtai hash over a ring with a 64-bit
modulus (its own digits are balanced base-8 digits, a few bits each), and it accumulates many such
commitments into one by folding, so that a proof-carrying-data scheme can defer the expensive
opening to the end.

BitZ is a hash-based commitment scheme whose witnesses are bit-decomposed: it commits the bits and
proves an evaluation claim over any ring by lifting it to the integers.

Kishu takes BitZ's view of the witness as small integers and the constraint style of Zinc+'s
universal constraint systems. It commits the witness with Akita: bits where the circuit needs bits
as factors, and Akita's own base-8 digits for integer words. So the committed vector is the witness
itself, the range check certifies it, and Akita's accumulation replaces BitZ's hashing-heavy proofs.
A digit is therefore the unit in which this study counts a circuit's size. The two arithmetizations
are not the same. BitZ states integer relations and proves them by projecting to random prime
fields. Kishu evaluates its constraints in $\mathbb{F}_q$, Akita's commitment modulus. It reaches
the integers either by keeping each constraint's sides within a range no larger than $q$, the limb
route, or by random-prime instances as BitZ does, the fingerprint route.

The piece that such a combination needs is a range check over the lattice's own prime field, to
certify that every digit lies in its alphabet. For the wider digits that is Akita's own paired
predicate, a sum-check of degree $b/2$ for an alphabet of $b$ values. For the bits it is a
Booleanity check, and an internal research draft of September 2026, provisional and unreviewed,
supplies one. The committed table's bits are certified by one unweighted quadratic identity plus an
integer norm bound, which a structured random projection supplies by revealing 160 coordinates. So
BitZ's exponent-lift GKR, <!--fig:bitz_gkr_share_pct-->80<!--/fig-->% of its prover, is not needed.
The draft measures the reduction alone, single-threaded at $2^{27}$ bits over $2^{64} - 59$. The
projection prover takes <!--fig:bool_projection_prover_ms-->113<!--/fig--> ms
against <!--fig:bool_sumcheck_prover_ms-->438<!--/fig--> ms for the optimized conventional
Booleanity sum-check, with verifiers of <!--fig:bool_projection_verify_ms-->0.85<!--/fig-->
and <!--fig:bool_sumcheck_verify_ms-->0.023<!--/fig--> ms and payloads
of <!--fig:bool_projection_kb-->2.6 kbytes<!--/fig-->
and <!--fig:bool_sumcheck_kb-->1.7 kbytes<!--/fig-->. Neither includes the commitment opening or
hiding. The projection form reveals coordinates of the committed table, so the rows that use it have
no zero knowledge; the zero-knowledge rows use the sum-check form. The draft's certificates are
conditional and not yet formalized; [Kishu's Soundness Obligations](kishu-soundness.md) states what
has to be proved.

Beneath the step interface, Kishu accumulates as Ragu does: each step's proof is folded into an
accumulator rather than verified, and a step's circuit is accompanied by a circuit that verifies the
fold of its input proofs' accumulators, the merge, written in the same arithmetization. The sections
below price the arithmetization's units, the merge, and the application circuits in them.

## Digits and constraints

Kishu commits its digits over Akita's 64-bit modulus, plus the range check. For a bit that is the
Booleanity check at <!--fig:bool_projection_per_bit-->2.5<!--/fig-->
or <!--fig:bool_sumcheck_per_bit-->9.8<!--/fig--> word multiplications. A dibit or a tribit costs
one or three products more at the same rate, charged with the application's constraints. A step
commits $2^{\mathrm{rank}}$ digits. Its constraints are charged as well as its digits: the
constraint PIOP, a sum-check over the committed table, costs
about <!--fig:constraint_term_mults-->9.8<!--/fig--> word multiplications per product term of a
constraint, the measured rate of the Booleanity sum-check. A nonzero coefficient of a linear
combination costs <!--fig:nonzero_small_mults-->2<!--/fig--> for a small constant
or <!--fig:nonzero_field_mults-->4<!--/fig--> for a field constant, the combinations being over word
entries. This is charged for the application's constraints and the merge's alike, and the PIOP's
transcript is absorbed and its verifier run in the merge above.

Its claims live in the 64-bit field itself, Akita's commitment modulus, and the verifier recomposes
each Pasta value from 32-bit limbs proved as linear claims in the same sum-check. So Kishu does not
use the decoupled commitment, and its soundness rests on Akita's own at the 64-bit profile and on
the draft's Booleanity certificate. Its opening proof and decider are priced on the Goldilocks
variant's plan and measurement, the same profile, at Kishu's digit count.

## Pasta multiplication by two routes

Akita's claims are in one fixed field, so a Pasta multiplication $a \cdot b = k \cdot p + r$ over
committed digits cannot be checked modulo that field alone: the prover could choose $r$. Kishu's
rows therefore come in two routes, each a row. By the limb route the relation is checked coefficient
by coefficient over 29-bit limbs, which are linear in the digits and cost nothing to commit. That
is <!--fig:mult_coefficients-->17<!--/fig--> constraints of up to nine product terms each, bounded
below half the modulus so that they hold over the integers, with a committed carry
of <!--fig:mult_carry_bits-->34<!--/fig--> bits each. A multiplication is
then <!--fig:mult_limbs_digits-->374<!--/fig--> digits and <!--fig:mult_limbs_terms-->98<!--/fig-->
product terms. By the fingerprint route the relation is one constraint in each
of <!--fig:fingerprint_instances-->3<!--/fig--> PIOP instances over random 52-bit primes, as BitZ
checks it, at <!--fig:mult_fingerprint_digits-->170<!--/fig--> digits. The price is per step that
has multiplications, so a step of hashes alone pays nothing and the routes tie on the path
applications. Each instance's evaluation claim becomes about $\sqrt{2^{\mathrm{rank}}}$ integer
column sums by BitZ's tensor split, each exact as one claim in the 64-bit field and committed as a
word
of <!--fig:column_sum_bits-->61<!--/fig--> bits, <!--fig:column_sum_digits-->21<!--/fig--> digits.
That is <!--fig:fingerprint_step_digits_21-->91,287<!--/fig--> digits a step at rank 21, with three
more transcripts for the merge above. So the recovery circuit
is <!--fig:app_recovery_kishu_limbs-->6.1 million<!--/fig--> digits by the limb route
and <!--fig:app_recovery_kishu_fingerprint-->3.2 million<!--/fig--> by the fingerprint route. Its
constraint PIOPs take <!--fig:piop_recovery_kishu_limbs_s-->0.0135<!--/fig-->
and <!--fig:piop_recovery_kishu_fingerprint_s-->0.00556<!--/fig--> s on one core. The range checks
of its tribits take <!--fig:range_recovery_kishu_limbs_s-->0.0509<!--/fig-->
and <!--fig:range_recovery_kishu_fingerprint_s-->0.0244<!--/fig--> s more, beyond the one product a
digit that every digit pays.

## The merge

Kishu's merge is Akita's, costed in digits. A committed bit is one digit, so a BLAKE3 compression of
the transcript is <!--fig:blake3_chained_bits-->11,216<!--/fig--> digits and the images' reductions
one per bit. The BLAKE3 accounting is its seven rounds of eight G functions. Every word of a G
function is used once as a factor, in an XOR, and once linearly, in an addition, and only a factor
needs committing:

- each 32-bit addition is one relation $a + b = s + 2^{32} c$ over word entries, with the 32 sum
  bits and the carry committed, two bits of carry where there are three addends;
- of each chain of two XORs in a G function, the first's word is left uncommitted: its bits are the
  expressions $x + y - 2xy$ inside the addition that takes the word, 32 terms there;
- the second's word is committed, each bit certified against both XORs' inputs at two terms;
- rotations are free, being wiring; and
- the finalisation XORs two state words into each of the eight output words, and what is committed
  depends on what consumes them.

Where the output is the next compression's chaining value, within one message, four of its words are
that compression's factors in its first round and are committed at one term a bit. The other four
enter its first additions as expressions. That
is <!--fig:blake3_chained_bits-->11,216<!--/fig--> digits a compression.

Where the output is data, all eight words are committed at one term a bit. A Merkle node's output
and a hash call's are message words of the next compression, addends in each of its seven rounds,
and a transcript's last output is a challenge. That
is <!--fig:blake3_data_more_digits-->128<!--/fig--> digits
more, <!--fig:blake3_bits-->11,344<!--/fig-->. <!--claim:blake3_output_same_constraints:80a8b3-->Either
way a compression is <!--fig:blake3_piop_terms-->11,120<!--/fig--> constraints,<!--/claim-->
with <!--fig:blake3_piop_nonzeros-->37,760<!--/fig--> nonzeros where the output is data.

BLAKE3 splits a message into chunks of <!--fig:blake3_chunk_bytes-->1,024<!--/fig--> bytes, each a
chain of compressions over its 64-byte blocks, and joins the chunks' outputs by a binary tree of
parent compressions, one fewer than the chunks. Over a whole transcript the parents would
be <!--fig:blake3_parent_overhead_pct-->6.25<!--/fig-->% more compressions, and that would compound,
since the merge absorbs each step circuit's claim and a dearer merge needs more circuits.

So the transcript is a Merkle–Damgård chain at the application level. Each link is a keyed BLAKE3
call on one 64-byte block of the transcript, whose key is the previous call's output. Every call is
BLAKE3 as specified, in its keyed mode, on a single block, so it is one compression, and the
transcript takes exactly one compression a block. The key is the compression's chaining value, so
each output but the last is consumed as one, and the last is data.

BLAKE2b has the same G function at 64 bits, each addition in two halves since a 64-bit sum can wrap
modulo $q$. Its finalisation differs: it XORs the old chaining word in with the two state words, a
chain of two XORs. So all eight output words are committed, each bit certified at two terms. That
gives BLAKE2b <!--fig:blake2b_bits_kishu-->38,528<!--/fig--> digits
and <!--fig:blake2b_piop_terms-->38,272<!--/fig--> constraints.

Under BLAKE3 every transcript
element the prover supplies is first checked to be below the modulus, since a 64-bit decomposition
is canonical only there, about <!--fig:range_check_digits-->22<!--/fig--> digits a word.

The merge's arithmetic is over the 64-bit field and its quadratic extension, which is the PIOP's own
field. As in BitZ, the constraint PIOP runs over the ring itself, and only the final linear claim is
proved on the bits. So a multiplication there is one constraint, with no bit decomposition and no
quotient. But every wire is committed as tribits: <!--fig:q64_digits-->22<!--/fig--> digits for a
field element and <!--fig:e_mult_digits-->44<!--/fig--> for a product in the extension. So the
sum-check's arithmetic is <!--fig:sumcheck_gates-->400<!--/fig--> such products, each circuit's
claim <!--fig:claim_gates-->4<!--/fig--> and the Booleanity sum-check's verifier
about <!--fig:bool_sumcheck_merge_mults-->3,000<!--/fig-->; the projection verifier
scans <!--fig:bool_projection_scan-->3.1 million<!--/fig--> sampled coefficients, a digit each. The
transcript's elements and each circuit's claim are elements of the
extension, <!--fig:kishu_claim_bytes-->16<!--/fig--> bytes, and the Booleanity sum-check's own
transcript is absorbed with them.

Under the Poseidon option the transcript is hashed by Poseidon over the 64-bit field at width 12 and
rate 8 with the $x^3$ S-box: <!--fig:q64_poseidon_mults-->276<!--/fig--> multiplications a
permutation at <!--fig:q64_digits-->22<!--/fig--> digits
each. <!--claim:poseidon_fewer_digits_than_blake3:82eb62-->That
is <!--fig:poseidon_of_blake3_digits_pct-->54<!--/fig-->% of BLAKE3's committed digits per absorbed
byte, fewer because Poseidon's wires are tribits where BLAKE3's are bits.<!--/claim--> A permutation
is <!--fig:q64_poseidon_mults-->276<!--/fig--> constraints
with <!--fig:poseidon_q64_piop_nonzeros-->13,800<!--/fig--> nonzeros of field constants, where a
BLAKE3 compression is <!--fig:blake3_piop_terms-->11,120<!--/fig-->
with <!--fig:blake3_piop_nonzeros-->37,760<!--/fig--> of small ones, and these are charged at the
rates above. <!--claim:hash_within_quarter:de8249-->Per 64 bytes absorbed, commitments and
constraints together, BLAKE3 costs <!--fig:blake3_64b_mults-->430,000<!--/fig--> word
multiplications and Poseidon <!--fig:poseidon_64b_mults-->350,000<!--/fig-->,
within <!--fig:hash_64b_within_pct-->21<!--/fig-->% of each other, which many modelling choices
could sway either way.<!--/claim--> So both hashes are kept as variants of Kishu on the frontier
page, each a family of its own in the list and the plot. The BLAKE3 rows appear under either hash
option and the Poseidon rows under the arithmetic-hash option, and the frontier decides between
them.

## The recovery circuit

The Ironwood recovery circuit itself is hash-heavy: its expensive parts are seven BLAKE2b-512
compressions (the cost section of [\[ZIP-2005\]](#ref-zip2005); beside two Sinsemilla commitments,
two full-width Pallas scalar multiplications, a Merkle path, and a BLAKE3 compression in the
quantum-key signature). In Kishu a bit-oriented hash is one bit per wire against many Pasta gates
per round in the others, and the integer arithmetic simulates $\mathbb{F}_p$ without a bit
decomposition per operation, with range checks free. A Sinsemilla chunk selects one of 1,024
generators by ten bits, each coordinate a fixed linear form in the subset products of the bits. Only
a product that is a factor of another is committed:
the <!--fig:sinsemilla_committed_products-->52<!--/fig--> subsets within each half of the bits.
The <!--fig:sinsemilla_cross_products-->961<!--/fig--> subsets spanning both halves are terms of the
two coordinate constraints. So a chunk is <!--fig:sinsemilla_chunk_digits-->222<!--/fig--> digits
with its coordinates. Costed component by component in this arithmetization, with a committed bit at
one digit and a multiplication at <!--fig:mult_limbs_digits-->374<!--/fig--> digits by the limb
route or <!--fig:mult_fingerprint_digits-->170<!--/fig--> by the fingerprint route, the recovery
circuit is <!--fig:app_recovery_kishu_limbs-->6.1 million<!--/fig-->
or <!--fig:app_recovery_kishu_fingerprint-->3.2 million<!--/fig--> digits. In Pasta arithmetic it
is <!--fig:app_recovery_pasta_poseidon-->570,000<!--/fig--> gates. The frontier page's transaction
measure uses those counts together with the constraint PIOP's work.

## A rough cost model

The unit costs above, gathered. A digit is one committed bit, dibit, or tribit. A term is one
product term of a constraint, or one product of the range check beyond the first. The word
multiplications are native 64-bit ones on the prover.

| What | Digits | Terms | Prover work |
|---|---|---|---|
| a committed digit | 1 | 0, 1, or 3 for a bit, a dibit, or a tribit | <!--fig:kishu_digit_mults-->11.0<!--/fig--> word multiplications to commit, <!--fig:kishu_digit_mults_masked-->14.0<!--/fig--> under zero knowledge |
| a Pasta value, as tribits | <!--fig:value_digits-->85<!--/fig--> | | <!--fig:kishu_value_commit_mults-->935<!--/fig--> word multiplications to commit |
| a constraint term | | 1 | <!--fig:constraint_term_mults-->9.8<!--/fig--> word multiplications; a nonzero <!--fig:nonzero_small_mults-->2<!--/fig--> or <!--fig:nonzero_field_mults-->4<!--/fig--> |
| an XOR of two 32-bit words, committed | 32 | 32, or 64 when the next XOR's word is left uncommitted | |
| an XOR of two 32-bit words, uncommitted | 0 | 32, inside the constraint that consumes it | |
| a 32-bit addition | 33, or 34 with three addends | 1 | |
| a field element of $\mathbb{F}_q$; a product in $E$ | <!--fig:q64_digits-->22<!--/fig-->; <!--fig:e_mult_digits-->44<!--/fig--> | 1 | |
| a BLAKE3 compression | <!--fig:blake3_bits-->11,344<!--/fig--> | <!--fig:blake3_piop_terms-->11,120<!--/fig--> | |
| a Poseidon permutation over $\mathbb{F}_q$ | <!--fig:q64_poseidon_mults-->276<!--/fig--> × <!--fig:q64_digits-->22<!--/fig--> | <!--fig:q64_poseidon_mults-->276<!--/fig--> | |
| a Pasta multiplication | <!--fig:mult_fingerprint_digits-->170<!--/fig--> by fingerprint, <!--fig:mult_limbs_digits-->374<!--/fig--> by limbs | 3 or <!--fig:mult_limbs_terms-->98<!--/fig--> | the fingerprint route's column sums per step besides |
| a step | its length, chosen | | its digits' commitment and its constraints' PIOP |
| the merge of one step | <!--fig:kishu21_blake3_digits-->1.2 million<!--/fig--> in a step of $2^{21}$ digits | | as a step's |

A transaction's prover work is then its steps' commitments and PIOPs, a merge for each step, the
fold's sum-checks over the accumulator, and the final opening. The frontier page's axes
[Accumulation prover](pareto-template.html#accumulation-prover), [Prover commitment
work](pareto-template.html#prover-work), and [Transaction
prover](pareto-template.html#transaction-prover) say how each is counted, and its [Step
rank](pareto-template.html#step-rank) section how the step size is chosen. Zero knowledge adds the
masked accumulation matrix's rate to every digit and the masking fold once per transaction, as [Zero
Knowledge for a Lattice Accumulation Step](zk-fiat-shamir-with-aborts.md) describes.

## Differences from Ragu

[Relation to Ragu](#relation-to-ragu) above gives the differences in the arithmetization itself.
Beyond it, Ragu commits a step's trace as one structured polynomial of degree below $4n$, by
Pedersen, and checks the gates and constraints together by one revdot identity at random points,
sound by Schwartz–Zippel in the field. A step of rank $r$ commits $2^r$ coefficients, so
$2^{r-2}$ gates: at rank 13, Ragu's production rank, 2,048 gates, which every one of Tachyon's
circuits fits. Kishu differs in these ways:

- **A value's digits cost less than a coefficient.** Ragu's gate costs about one Pallas
  multiplication of Pedersen work per wire, about <!--fig:pedersen_per_coeff_13-->5,600<!--/fig-->
  word multiplications a coefficient at rank 13. Kishu's digit
  costs <!--fig:kishu_digit_mults-->11.0<!--/fig--> to commit, so a Pasta
  value's <!--fig:value_digits-->85<!--/fig--> tribits
  cost <!--fig:kishu_value_commit_mults-->935<!--/fig-->, well under one coefficient.
- **Constraints are a sum-check, not a gate identity.** Ragu's constraints are the fixed gate shape
  and linear combinations, checked by one polynomial identity over the field. Kishu's are a
  sum-check PIOP over the committed table, as in BitZ and Zinc+'s universal constraint systems, with
  integer relations projected to the 64-bit field or to random primes. A constraint is charged by
  its product terms and nonzeros rather than by gates.
- **Hashes are cheap and Pasta arithmetic is dear.** In Ragu a Poseidon permutation over Pallas is
  about 192 gates and a Pasta multiplication one gate, while a bit-oriented hash would cost a gate
  per bit operation. In Kishu a BLAKE3 compression
  is <!--fig:blake3_bits-->11,344<!--/fig--> digits, one per bit, and a Pasta
  multiplication <!--fig:mult_fingerprint_digits-->170<!--/fig-->
  or <!--fig:mult_limbs_digits-->374<!--/fig--> digits by relation, since the field is not Pasta's.
  That is why the recovery circuit
  is <!--fig:app_recovery_kishu_fingerprint-->3.2 million<!--/fig--> digits
  against <!--fig:app_recovery_pasta_poseidon-->570,000<!--/fig--> Pasta gates, and why Zoodles,
  with no Pasta arithmetic, suits it. Kishu is not specialized to Pasta at all. Given that, it does
  well on Pasta in prover time, as the frontier page's transaction measure shows, and it would do as
  well on any large-field arithmetic.
- **The claim field is small.** Ragu's claims are Pallas elements; Kishu's are elements of the
  64-bit field's quadratic extension, <!--fig:kishu_claim_bytes-->16<!--/fig--> bytes, so a Pasta
  value is proved through limbs or a fingerprint.
- **The step is larger and its size is a knob.** Ragu's step is fixed at $2^{13}$ coefficients;
  Kishu's is $2^{\mathrm{rank}}$ digits over a range of ranks, and one Kishu step holds several of
  Tachyon's circuits, as the [Zoodles](zoodles.md) page's packing shows.
- **The merge verifies a lattice fold.** Ragu's merge circuits verify Pedersen-IPA accumulation with
  Poseidon transcripts over Pallas ([the frontier page's circuit
  budget](pareto-template.html#circuit-budget)); Kishu's verify Akita's fold, its sum-checks and
  images, with a BLAKE3 or Poseidon transcript in digits, as above.
- **Zero knowledge by masking.** Ragu rerandomizes its proofs in two steps of their own; Kishu's
  accumulation is made zero-knowledge by a masking fold with rejection sampling, paid once per
  transaction, as the [zero-knowledge note](zk-fiat-shamir-with-aborts.md) describes.

## References

- <a id="ref-agk26"></a>[AGK+26] Alexander Abdugafarov, Albert Garreta, Amit Kumar, Michał Osadnik,
  Psi Vesely, Ilia Vlasov, Kai Zhe Zheng. Zinc+: SNARKs for polynomial rings.
  2026. <https://eprint.iacr.org/2026/855>
- <a id="ref-bcc16"></a>[BCC+16] Jonathan Bootle, Andrea Cerulli, Pyrros Chaidos, Jens Groth,
  Christophe Petit. Efficient Zero-Knowledge Arguments for Arithmetic Circuits in the Discrete Log
  Setting. EUROCRYPT 2016. <https://eprint.iacr.org/2016/263>
- <a id="ref-bgk26"></a>[BGK+26] Remco Bloemen, Albert Garreta, Marcin Kostrzewa, Shreyas Londhe,
  Lev Soukhanov, John Wu. BitZ: proofs and commitments in arbitrary rings through binary fields.
  2026. <https://eprint.iacr.org/2026/2141>
- <a id="ref-gwhd25"></a>[GWHD25] Albert Garreta, Hendrik Waldner, Katerina Hristova, Luca Dall'Ava.
  Zinc: Succinct Arguments with Small Arithmetization Overheads from IOPs of Proximity to the
  Integers. 2025. <https://eprint.iacr.org/2025/316>
- <a id="ref-stw23"></a>[STW23] Srinath Setty, Justin Thaler, Riad Wahby. Customizable Constraint
  Systems for Succinct Arguments. 2023. <https://eprint.iacr.org/2023/552>
- <a id="ref-zip2005"></a>[ZIP-2005] Daira-Emma Hopwood, Jack Grigg. ZIP 2005: Ironwood Quantum
  Recoverability. <https://zips.z.cash/zip-2005>
