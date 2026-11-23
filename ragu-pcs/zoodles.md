# Zoodles

Zoodles is a post-quantum variant of [Tachyon](https://tachyon.z.cash/), designed to be deployed as
a follow-on to it, with [Kishu](../book/src/proof-systems/kishu.md) as its proof system. It is named
after (pasta-free) zucchini noodles.

Apart from using Kishu as the proof system, the changes from Tachyon to Zoodles are pretty
straightforward. They just drop all uses of Pasta outside the Ironwood/Tachyon recovery circuit:

- The value commitments are replaced by a balance check in PCD. The binding signature is dropped; it
  is not needed for either non-malleability or balance.
- Note commitments and nullifiers are derived using BLAKE3.
- Spends are authenticated *either* by proving knowledge of $\mathsf{qsk}$, or via a leanSPHINCS
  signature verified in zk. The latter requires many PCD steps to verify, but the overall
  performance is entirely practical both on a hardware wallet and on the host wallet.
  Multisignatures are also feasible.
- The epoch tachygram set accumulators are replaced by sorted Merkle trees rather than by set
  polynomials in Kishu's PCS (Akita); [The epoch's tachygram set](zoodles-epoch-set.md) compares the
  two, and a bucketed table.
- The PCD step size is reoptimized for Kishu. It ends up committing between a quarter and the same
  step circuit witness size as Ragu, but as bits rather than Pallas field elements.

The rest of this page expands on each of these, as the [PCS frontier
page](pareto-template.html#transaction-prover) prices them.

## What stays from Tachyon

Tachyon's architecture is kept: the same spend, output, merge, and fee circuits for a transaction,
and a note's membership and unspentness attested by a background lineage over the chain's anchors
rather than by a Merkle path in the spend. The published tachygrams are what the merges combine: a
spend's two epoch nullifiers, an output's commitment and its padding, and the fee circuit's change
commitment. The fee circuit fixes the fee last and hashes the change note, the maximum-fee note's
value less the fee, as Tachyon's does. What changes in the tree is the packing: Tachyon gives each
circuit a step of its own, where a Kishu step of $2^{\mathrm{rank}}$ digits holds the fee
circuit, <!--fig:zoodles_fee_digits-->39,557<!--/fig--> digits, and with it as many
spends, <!--fig:zoodles_spend_digits-->50,461<!--/fig--> digits each, and
outputs, <!--fig:zoodles_output_digits-->65,513<!--/fig-->, as fit, each with its merge
of <!--fig:zoodles_merge_digits-->13,666<!--/fig-->: <!--fig:zoodles_actions_per_step_17-->1<!--/fig-->
action at rank 17, <!--fig:zoodles_actions_per_step_19-->6<!--/fig--> at rank 19,
and <!--fig:zoodles_actions_per_step_21-->28<!--/fig--> at rank 21. A transaction of two inputs and
two outputs is <!--fig:zoodles_nodes-->12<!--/fig--> circuits, and at
rank <!--fig:tx_zoodles_preimage_kishu_zk_rank-->19<!--/fig--> they fit
in <!--fig:tx_zoodles_preimage_kishu_zk_steps-->1<!--/fig--> step. A spend authorized by leanSPHINCS
is <!--fig:zoodles_leansphincs_spend_digits-->6.44 million<!--/fig--> digits and takes several steps
by itself.

What changes is the arithmetic inside the nodes. In Tachyon the set polynomials are Pedersen vector
commitments and the bridge hash is a Pedersen hash onto Pallas. In Zoodles the set polynomials are
the proof system's own committed vectors with evaluation claims, so that a root costs one
multiplication in a 256-bit extension of the claim field and an opening one more claim absorbed by
the merge above, and the bridge hash is a BLAKE3 hash of the commitment, computed natively. The
tree's nodes hash <!--fig:zoodles_blake3-->16<!--/fig--> BLAKE3 compressions in all,
with <!--fig:zoodles_roots-->12<!--/fig--> roots and <!--fig:zoodles_openings-->15<!--/fig-->
openings. The curve goes.

## Balance in the headers

Amounts are range-checked to 51 bits and summed in the PCD headers in place of value commitments and
the binding signature: a spend's bind step range-checks its amount, a merge sums its children's
amounts, and the fee step range-checks the slack, the fee, and the change. The binding signature is
not needed for non-malleability either, since every spend's authorization is proved inside the tree
that the headers bind together.

## Spend authorization

Spend authorization is chosen per input, usually the same for all.

The first form is a Sprout-like preimage check: the payment key is the BLAKE3 hash of the
authorizing key, which Tachyon's spend step derives already, and the spend step proves knowledge of
the preimage. It needs no digest of the transaction, since it is proved inside the spend step, which
the tree binds to the rest of the transaction directly and through the PCD headers. Its binding to
the transaction rests on the signature-of-knowledge argument of [Hardware wallets and the recovery
statement](hardware-wallets.md), and that page also prices the preimage statement as the part a
hardware wallet proves on its own.

The second form is a leanSPHINCS signature with BLAKE2s at the pruned
key, <!--fig:leansphincs_sig_bytes-->4,276<!--/fig--> bytes verified
in <!--fig:leansphincs_blake2s_calls-->298<!--/fig--> compressions, over a transaction digest. The
signature is verified in the circuit with the public key as a witness: the zero-knowledge fold hides
the key, so no re-randomized signature is needed. Since the signature is made outside the proof, its
message must bind the transaction's effecting data: each spend's two nullifiers, each output's
commitment, the change commitment, the fee, and the
epoch, <!--fig:zoodles_sighash_bytes-->235<!--/fig--> bytes
or <!--fig:zoodles_sighash_blake3-->4<!--/fig--> compressions. The digest is a PCD header value:
each spend verifies its signature over it, and the fee step recomputes it from the nullifiers and
commitments that its children's headers carry. The signature verification, not the digest, is the
expensive part of this form.

## The lineage

A Zoodles note's lineage runs in the background, as Tachyon's does, and is not part of any
transaction. Once an epoch, <!--fig:zoodles_epoch_blocks-->4,096<!--/fig--> blocks
or <!--fig:zoodles_epoch_days-->3.6<!--/fig--> days at 75-second blocks, a step advances the note
past the epoch's published tachygrams, proving that its nullifier is not among them.

Tachyon does this with set polynomials: the epoch's tachygrams are split into buckets by a
quadratic-residue profile, each bucket a polynomial opened at the nullifier, and the step folds the
bucket's contents. Over Kishu's digits a bucket of <!--fig:zoodles_bucket_coeffs-->8,192<!--/fig-->
tachygrams is <!--fig:zoodles_bucket_digits-->2.10 million<!--/fig--> digits to fold for every note
in every epoch, most of them the builder's work rather than the wallet's. The frontier page prices
the alternative: a sorted Merkle tree over the
epoch's <!--fig:zoodles_epoch_tachygrams-->1,048,576<!--/fig-->
tachygrams, <!--fig:zoodles_epoch_per_block-->256<!--/fig--> a block, in which the exclusion proof
is the nullifier's two neighbours as one leaf with its path
of <!--fig:zoodles_epoch_hashes-->22<!--/fig--> hashes, two 256-bit comparisons, and the epoch range
check: <!--fig:app_zoodles_epoch_kishu-->332,000<!--/fig--> Kishu digits,
and <!--fig:tx_zoodles_epoch_kishu_s-->0.0395<!--/fig--> s a note an epoch at
rank <!--fig:tx_zoodles_epoch_kishu_rank-->19<!--/fig--> on one core, without zero knowledge, since
the lineage never leaves the wallet. On that count the tree is well ahead; the bucket route as
Tachyon folds it, at a capacity chosen for digits, is still to be priced beside it; [The epoch's
tachygram set](zoodles-epoch-set.md) compares the representations.

## Cost

On one core, in Kishu, for two inputs and two outputs: a transaction authorized by preimage
is <!--fig:app_zoodles_preimage_kishu-->313,000<!--/fig--> committed digits and
takes <!--fig:tx_zoodles_preimage_kishu_zk_s-->0.0824<!--/fig--> s with zero knowledge at
rank <!--fig:tx_zoodles_preimage_kishu_zk_rank-->19<!--/fig-->,
or <!--fig:tx_zoodles_preimage_kishu_s-->0.0395<!--/fig--> s without; one authorized by leanSPHINCS
is <!--fig:app_zoodles_leansphincs_kishu-->13.1 million<!--/fig--> digits
and <!--fig:tx_zoodles_leansphincs_kishu_zk_s-->0.488<!--/fig--> s with zero knowledge at
rank <!--fig:tx_zoodles_leansphincs_kishu_zk_rank-->21<!--/fig-->,
in <!--fig:tx_zoodles_leansphincs_kishu_zk_steps-->7<!--/fig--> steps. Tachyon's own four
tachyactions in Kishu with zero knowledge take <!--fig:tx_tachyon4_kishu_zk_s-->0.241<!--/fig--> s,
so Zoodles by preimage is <!--fig:zoodles_preimage_of_tachyon_pct-->34<!--/fig--> percent of them;
on Pedersen-IPA they take <!--fig:tx_tachyon4_pedersen_s-->8.44<!--/fig--> s. At these ranks a step
commits $2^{\mathrm{rank}}$ bits, between a quarter and the whole of Ragu's $2^{13}$ Pallas
coefficients in bits, which is the fifth bullet above. The [frontier
page](pareto-template.html#transaction-prover) gives the same transactions under every scheme it
prices.

## Status

- Whether Zoodles needs Tachyon's PCD header of nine elements, or fits the recovery circuit's six or
  seven, is not settled; the frontier page prices it at nine.
- The lineage is priced by the sorted tree alone; the bucket route is to be priced beside it.
- The bind, lift, and fuse steps that close a lineage segment at a spend are not counted.
- The packed step's interface is not charged: one step circuit carrying several nodes' headers and
  set products, with the fee logic beside the spends and outputs it fuses, is circuit layout that
  Tachyon's one-circuit-per-step design does not have.
- The set polynomials over a 64-bit field need a quartic extension, or four polynomials, for 256-bit
  tachygrams, and an opening is priced as one more claim; a committed online vector per step would
  add a group to the fold.

## Acknowledgements

Zoodles is mostly just the obvious adaptation of Tachyon. Thank you to the [Tachyon
team](https://tachyon.z.cash/team/), Sean Bowe, Tal Derei, Connor O'Hara, Alex Xiong, L Winslow, and
Samuel Akinosho, for their work. The adaptation, its name, and its modelling are Daira-Emma
Hopwood's.
