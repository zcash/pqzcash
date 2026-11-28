# Recovery from Ironwood

ZIP 2005 makes Ironwood-pool notes quantum-recoverable in the sense of [this section's
definition](spend-authorization.md#quantum-recovery) [\[ZIP-2005\]](#ref-zip2005). Each note's keys
commit to a quantum key $\mathsf{qk} = \mathsf{H^{qk}}(\mathsf{qsk})$, the quantum spending key
$\mathsf{qsk}$ derived from the spending key and in no viewing key. A Recovery Statement, to be
introduced in a later upgrade, spends such a note without discrete logarithms. The statement needs
two authorizations of a recovery spend. One is a RedDSA signature under the randomized key, which
FROST makes $t$-of-$n$. The other is $\mathsf{SoK^{qsk}}$: a signature of knowledge of
$\mathsf{qsk}$ on the transaction's SigHash, with $\mathsf{H^{qk}}(\mathsf{qsk}) = \mathsf{qk}$,
which is the [hash preimage](auth-preimage.md) method made as a signature. With
$\mathsf{use\_qsk} = \mathsf{true}$ the rest of the statement is proved from viewing-key material,
the path a hardware wallet is meant to optimize. The other path,
$\mathsf{use\_qsk} = \mathsf{false}$, has the statement prove the key derivations from the spending
key itself. The recovery circuit the frontier page prices takes either value, as ZIP 2005's
statement does, the two paths' derivations multiplexed over the same three BLAKE2b compressions;
this section's hardware-wallet analysis follows the $\mathsf{use\_qsk} = \mathsf{true}$ path. In a
Zoodles transaction the recovery spends also reveal their total, for the [pool
accounting](zoodles.md#pool-accounting) that the Zoodles page sets out.

With FROST, ZIP 2005 has the participants agree privately on the value $\mathsf{sk}$ from which
$\mathsf{nk}$, $\mathsf{qsk}$, and $\mathsf{qk}$ are derived, while $\mathsf{ak}$ is the output of
the distributed key generation. Every wallet then holds the same $\mathsf{qsk}$. So against an
adversary who breaks discrete logarithms the recovery spend's unforgeability is that of
$\mathsf{SoK^{qsk}}$ as a signature scheme with key $\mathsf{qk}$, 1-of-$n$, while a pre-quantum
adversary corrupting up to $t - 1$ wallets is bounded by re-randomized FROST; [Hardware
wallets](hardware-wallets.md) sets out that model. The frontier page prices the recovery circuit as
an application: in Kishu with zero knowledge it
takes <!--fig:tx_recovery_kishu_zk_s-->0.119<!--/fig--> s on one core in a step
of <!--fig:tx_recovery_kishu_zk_rank-->$1.875 \times 2^{21}$<!--/fig--> digits.

## The signature method as an arm of the Recovery Statement

What a [leanSPHINCS](auth-leansphincs.md) route asks of ZIP 2005 is less than it first seems. Its
$\mathsf{qk} = \mathsf{H^{qk}}(\mathsf{qsk})$ hashes the secret, and a hash-based signature needs
$\mathsf{qk}$ to commit to the signature's public key instead. Deriving that key from the seed
inside the Recovery Statement would cost the top layer's key generation, out of the question. But
the derivation is domain-separated. A signature route would define its own derivation of
$\mathsf{qk}$ from the public key under another context, and the Recovery Statement, which is not
yet specified, would accept it as one more arm of its tagged union beside the preimage proof and
$\mathsf{SoK^{sk}}$. The arms cannot satisfy each other's rule, since that would be a collision
across two domain-separated hashes. So nothing has to be decided before the scheme is known. The one
consequence is that a key derived before the signature route exists is a preimage-route key. A
wallet that wants the signature route later needs a new key, which means new addresses and moved
funds.

## A static cap for the Merkle path

The Ironwood note commitment tree is frozen once the pool's pre-quantum protocol is turned off. A
deployment can leave time between that and turning the Recovery Statement on, for nodes and wallets
to compute the static tree. The nodes at a chosen depth are then a fixed public table, the cap, and
the circuit need not hash the levels above it. It selects the cap's entry by the top bits of the
note's position, as a [Sinsemilla chunk](kishu-arithmetization.md#the-recovery-circuit) selects a
generator, and compares it with the node that the lower levels hash to. The position's bits stay
private. The circuit is written generically: the cap enters only as the coefficients of the
selection's constraints, filled in when the tree is frozen. The idea came from a discussion between
Daira-Emma Hopwood and Jack Grigg at Zcon3, where it was suggested for Sprout.

In Kishu the index bits are split into two halves. The subset products within a half are committed,
and each product across the halves is a term of a constraint. A node is compared
as <!--fig:recovery_cap_limbs-->4<!--/fig--> limbs of 64 bits, a constraint each. The comparison is
in $\mathbb{F}_q$, so it is sound when every limb of the cap is at
least <!--fig:recovery_cap_limb_margin-->59<!--/fig--> and below $q$. A limb falls outside that
range with negligible probability. If one does, the tree, which ZIP 2005 has rehashed in any case,
is rehashed under another BLAKE3 personalization.

The frozen tree is rehashed, so it need be no deeper than its commitments fill. The rehash keys each
node's hash by the node's position in the tree, which costs nothing with BLAKE3 and leaves an
attacker no choice among many targets; the tree's hash still has to be collision-resistant. It is
taken to have <!--fig:recovery_tree_height-->27<!--/fig--> levels at the freeze. Each
arithmetization's rows on the frontier page take the cap at the depth that costs them least. For
Kishu <!--claim:recovery_cap_saves:1dc118-->that is <!--fig:recovery_cap_levels-->14<!--/fig-->
levels<!--/claim-->: <!--fig:recovery_cap_entries-->16,384<!--/fig--> nodes,
or <!--fig:recovery_cap_kb-->524 kbytes<!--/fig-->, for each node and wallet to hold, and a
selection of <!--fig:recovery_cap_terms-->64,516<!--/fig--> terms. The path is then the leaf's hash
and the levels below the cap, <!--fig:recovery_cap_path_hashes-->14<!--/fig--> compressions. With
zero knowledge the cap saves <!--fig:recovery_cap_path_pct-->43<!--/fig-->% of what a path hashed
all the way would cost, which is <!--fig:recovery_cap_tx_pct-->1.5<!--/fig-->% of the recovery
transaction. Over Pasta, where a selection is the subset products of the index bits, the best cap
is <!--fig:recovery_cap_levels_pasta_poseidon-->9<!--/fig--> levels under a Poseidon path
and <!--fig:recovery_cap_levels_pasta_blake3-->14<!--/fig--> under a BLAKE3 one.

## References

- <a id="ref-zip2005"></a>[ZIP-2005] Daira-Emma Hopwood, Jack Grigg. ZIP 2005: Ironwood Quantum
  Recoverability. <https://zips.z.cash/zip-2005>
