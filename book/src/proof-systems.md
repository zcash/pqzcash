# Proof Systems

The zero-knowledge proofs deployed in Zcash's shielded protocols are not post-quantum.
Sapling's Groth16 proofs rest on pairings, and the Orchard protocol's Halo 2 proofs rest on
the discrete logarithm problem in the Pasta curves. A quantum adversary could forge either,
and so could break the soundness of the shielded pools.

[Ragu](https://github.com/tachyon-zcash/ragu) is a proof-carrying-data scheme built for
Tachyon: each step proves a small circuit, and the steps' proofs are folded into an
accumulator rather than verified in full. Its polynomial commitment scheme is Pedersen
commitments opened by an inner-product argument, the same family as Halo 2's, and that is
where its pre-quantum assumption lives. It is also what sets the size of its proofs and the
cost of its prover and of its recursion. The chapters in this section ask what replacing
that commitment scheme with a post-quantum one would cost, for the lattice-based and
hash-based schemes that could do it.
