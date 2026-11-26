# Recovery from Tachyon

Tachyon is designed to be quantum-private today and quantum-sound after an upgrade
[\[Tac26\]](#ref-tac26). Zoodles is that upgrade, defined here.

Tachyon's owner field is a Poseidon commitment over Pallas,
$\mathsf{pk} = \mathsf{Com}(\mathsf{ak}, \mathsf{nk})$, to the spend validating key and the
nullifier deriving key. Its note commitment
$\mathsf{cm} = \mathsf{Com}(\mathsf{pk}, v, \psi; \mathsf{rcm})$ is a Poseidon commitment, with no
constraint needed on how $\mathsf{rcm}$ is derived, and its nullifiers are hash outputs. So a
quantum computer learns nothing from the chain, and the commitment and nullifier parts of [this
section's definition](spend-authorization.md#quantum-recovery) hold by design. The only curve points
on chain are the value commitments and the randomized keys, and re-randomization keeps those private
too. What a quantum computer can do is forge: take the discrete log of a randomized key and
authorize a spend, or break the discrete-log polynomial commitments of the proof system. Tachyon's
book sketches a full upgrade, a post-quantum signature proved in zero knowledge in place of
re-randomization and a lattice folding scheme in place of Pedersen, and leaves it there.

## What the key structure lacks

Recovery before or across that upgrade is the question for Zoodles, and there Tachyon's key
structure has a gap that Ironwood's does not. The witness for Tachyon's quantum recoverability is
the opening of $\mathsf{pk}$, the pair $(\mathsf{ak}, \mathsf{nk})$. Tachyon has no viewing keys as
such, but $\mathsf{nk}$ plays the part of one: a host that scans for a hardware wallet holds it to
derive the nullifiers, and holding it must not authorize a spend. And $\mathsf{ak}$ is the public
output of a FROST group's key generation. So once discrete logarithms fall, the recovery witness is
in the wrong hands in both settings: a single-signer hardware wallet's host holds $\mathsf{nk}$ and
$\mathsf{ak}$, so it could spend; and a FROST group has no secret that only its members hold, since
$\mathsf{ask}$ is shared and never reconstructed and $\mathsf{ak}$ is known to every participant.
ZIP 2005 avoids both by committing to a separate $\mathsf{qk} = \mathsf{H^{qk}}(\mathsf{qsk})$ whose
secret is in no viewing key, and by having a FROST group derive $\mathsf{qsk}$ from a privately
agreed value [\[ZIP-2005\]](#ref-zip2005). Tachyon has no counterpart, a regression from Ironwood
for single-signer hardware wallets and FROST groups alike.

## The suggested change

The fix is small. The proof-authorizing key becomes $(\mathsf{ak}, \mathsf{nk}, \mathsf{qk})$ with
$\mathsf{qk} = \mathsf{H^{qk}}(\mathsf{qsk})$, ZIP 2005's BLAKE3 derivation, and the owner field
$\mathsf{pk} = \mathsf{Com}(\mathsf{ak}, \mathsf{nk}, \mathsf{qk})$ stays one hash commitment:
Tachyon's sponge absorbs four field elements a permutation and $\mathsf{pk}$ takes three, so
$\mathsf{qk}$ fits as the fourth, entered as one Pallas element by reduction modulo $p$, since a
256-bit hash output is not one. The ordinary spend circuit is unchanged, since it opens
$\mathsf{pk}$ as before with $\mathsf{qk}$ as one more field. The recovery statement proves
knowledge of $\mathsf{qsk}$ and $\mathsf{nk}$ rather than of $\mathsf{ak}$ and $\mathsf{nk}$, and a
FROST group derives $\mathsf{qsk}$ from its privately agreed value as ZIP 2005 prescribes, with
$\mathsf{ak}$ still the distributed key generation's output. The cost is one more field in the
commitment and, in the recovery proof, one BLAKE3
compression, <!--fig:app_qk_bits-->11,344<!--/fig--> Kishu digits, which the recovery circuit
application already charges for $\mathsf{H^{qk}}$, and the reduction's range check of 256 bits.

## The migration transaction

A Tachyon note moves to Zoodles by a recovery spend and a Zoodles output. The transaction reveals
the total it spends from the Tachyon pool, for the [pool accounting](zoodles.md#pool-accounting)
that the Zoodles page sets out. The spend proves knowledge of $\mathsf{qsk}$ against $\mathsf{qk}$
in $\mathsf{pk}$, the Poseidon openings of $\mathsf{pk}$ and $\mathsf{cm}$ over Pallas, the
membership of $\mathsf{cm}$ in a hash-based tree over Tachyon's published commitments, and the
nullifier's derivation and its absence from Tachyon's published nullifiers. It cannot rely on
Tachyon's set polynomials, which are Pedersen commitments, once discrete log is gone, so the tree is
the structure for Tachyon's notes as it is for Zoodles' own epochs. The shape is ZIP 2005's Recovery
Statement over Tachyon's note format, with Poseidon where Orchard has Sinsemilla. The [frontier
page](pareto-template.html#transaction-prover) prices the migration as an application, in Zoodles'
proof tree with a recovery node for each input. With Kishu the recovery spend
is <!--fig:app_tachyon_recovery_kishu-->1.3 million<!--/fig--> digits, by limbs, of a
transaction's <!--fig:app_tachyon_zoodles1_kishu-->1.4 million<!--/fig-->. Recovering one note
takes <!--fig:tx_tachyon_zoodles1_kishu_zk_s-->0.113<!--/fig--> s of prover on one core with zero
knowledge, and four notes in one
transaction <!--fig:tx_tachyon_zoodles4_kishu_zk_s-->0.226<!--/fig--> s. The spend derives and
excludes one epoch's nullifier. A note's nullifiers for the other epochs it has lived through need a
lineage of their own, as Zoodles' notes have, which is not priced.

Tachyon's own circuits are priced there too in each post-quantum proof system. They are not what
such a system would prove, but they compare it with Ragu on the same application.

## References

- <a id="ref-tac26"></a>[Tac26] The Tachyon project. The Tachyon book, chapter "Revisit": the
  payment key and quantum safety.
  2026. <https://tachyon.z.cash/book/revisit.html#payment-key>, <https://tachyon.z.cash/book/revisit.html#pq>
- <a id="ref-zip2005"></a>[ZIP-2005] Daira-Emma Hopwood, Jack Grigg. ZIP 2005: Ironwood Quantum
  Recoverability. <https://zips.z.cash/zip-2005>
