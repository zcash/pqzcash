# Zoodles

Zoodles is a post-quantum shielded protocol based on [Tachyon](https://tachyon.z.cash/), with its
own shielded pool. It uses a new lattice-based proof system,
[Kishu](../book/src/proof-systems/kishu.md). It is designed to be deployed as a follow-on to
Tachyon. Zoodles is named after (pasta-free) zucchini noodles.

Apart from using Kishu as the proof system, the changes from Tachyon to Zoodles are pretty
straightforward. They just drop all uses of Pasta outside the Ironwood/Tachyon recovery circuit:

- The value commitments are replaced by a balance check in PCD. The binding signature is dropped; it
  is not needed for either non-malleability or balance.
- Note commitments and nullifiers are derived using BLAKE3.
- [Spends are authenticated](spend-authorization.md) *either* by proving knowledge of
  $\mathsf{qsk}$, or via a leanSPHINCS signature verified in zk. The latter requires many PCD steps
  to verify, but the overall performance is entirely practical both on a hardware wallet and on the
  host wallet. Multisignatures are also feasible.
- The [epoch tachygram set accumulators](zoodles-epoch-set.md) are replaced by sorted Merkle trees
  rather than by set polynomials in Kishu's PCS (Akita). That page compares the two, and a bucketed
  table.
- The PCD step size is reoptimized for Kishu. It ends up committing between a quarter and the same
  step circuit witness size as Ragu, but as bits rather than Pallas field elements.

The rest of this page expands on each of these, as the [PCS frontier
page](pareto-template.html#transaction-prover) prices them.

## What stays from Tachyon

Tachyon's architecture is kept: the same spend, output, merge, and fee circuits for a transaction,
and the same background lineage. A note's membership and unspentness are attested by that lineage
over the chain's anchors rather than by a Merkle path in the spend. The published tachygrams are
what the merges combine: a spend's two epoch nullifiers, an output's commitment and its padding, and
the fee circuit's change commitment. The fee circuit fixes the fee last and hashes the change note,
the maximum-fee note's value less the fee, as Tachyon's does.

What changes in the tree is the packing: Tachyon gives each circuit a step of its own, whereas a
Kishu step of $2^{\mathrm{rank}}$ digits holds the fee
circuit, <!--fig:zoodles_fee_digits-->39,557<!--/fig--> digits, and with it as many spends and
outputs as fit. A spend uses <!--fig:zoodles_spend_digits-->50,461<!--/fig--> digits and an
output <!--fig:zoodles_output_digits-->65,513<!--/fig--> digits, each with its merge
of <!--fig:zoodles_merge_digits-->13,666<!--/fig--> digits.
Therefore, <!--fig:zoodles_actions_per_step_17-->1<!--/fig--> action, a spend or an output, fits at
rank 17, <!--fig:zoodles_actions_per_step_19-->6<!--/fig--> at rank 19,
and <!--fig:zoodles_actions_per_step_21-->28<!--/fig--> at rank 21. A transaction of two inputs and
two outputs is four actions, and at rank <!--fig:tx_zoodles_preimage_kishu_zk_rank-->19<!--/fig-->
it fits in <!--fig:tx_zoodles_preimage_kishu_zk_steps-->1<!--/fig--> step. Tachyon's tree proves the
same transaction in <!--fig:zoodles_nodes-->12<!--/fig--> steps, two for each spend or output, three
merges, and the fee, and then rerandomizes. A spend authorized by leanSPHINCS with BLAKE3
is <!--fig:zoodles_leansphincs_blake3_spend_digits-->4.58 million<!--/fig--> digits and takes
several steps by itself.

The arithmetic inside the nodes also changes. In Tachyon the set polynomials are Pedersen vector
commitments and the bridge hash is a Pedersen hash onto Pallas. In Zoodles the set polynomials are
the proof system's own committed vectors with evaluation claims. A root then costs one
multiplication in a 256-bit extension of the claim field, and an opening one more claim, absorbed by
the merge above. The bridge hash is a BLAKE3 hash of the commitment, computed natively. The tree's
nodes hash <!--fig:zoodles_blake3-->16<!--/fig--> BLAKE3 compressions in all,
with <!--fig:zoodles_roots-->12<!--/fig--> roots and <!--fig:zoodles_openings-->15<!--/fig-->
openings. The curve goes.

## Balance in the headers

Amounts are range-checked to $[0, \mathsf{MAX\_MONEY}]$ and summed in the PCD headers in place of
value commitments and the binding signature. A spend's bind step range-checks its amount, a merge
sums its children's amounts, and the fee step range-checks the slack, the fee, and the change. The
binding signature is not needed for non-malleability either, since every spend's authorization is
proved inside the tree that the headers bind together.

## Pool accounting

A Zoodles bundle (e.g. in a ZIP 248 transaction [ZIP-248](#ref-zip248)) can spend from three pools:
its own, Ironwood's through the Recovery Statement of [Recovery from
Ironwood](recovery-ironwood.md), and Tachyon's through the recovery spend of [Recovery from
Tachyon](recovery-tachyon.md). Consensus tracks each pool's balance, and ZIP 209
[ZIP-209](#ref-zip209) rejects a transaction that would take any pool's balance out of range. So the
Zoodles bundle reveals the total it spends from Ironwood, the total it spends from Tachyon, and its
Zoodles balance, the net value leaving the Zoodles pool, which is negative when value enters it.

The headers carry the sums: a recovery spend's step adds its amount to its pool's sum and a native
spend's to the Zoodles sum, a merge adds its children's sums, and the fee step publishes the two
recovery totals and the Zoodles balance. A transaction with no recovery inputs publishes two zero
totals. The recovery totals are public, as a turnstile's flows are.

Unlike earlier turnstile crossings, where each pool's bundle carried its own proof and the
transparent value pool bridged them, the whole transaction is one Kishu proof; the recovery spends
are steps of its tree. This is necessary because both Halo 2 and Ragu proofs will have to be
disabled before Q-day.

## Spend authorization

Spend authorization is chosen per input, usually the same for all. The [Spend
authorization](spend-authorization.md) section motivates the two methods and has a page on each: the
[hash preimage](auth-preimage.md), the check $\mathsf{qk} = \mathsf{H^{qk}}(\mathsf{qsk})$ of ZIP
2005 [ZIP-2005](#ref-zip2005) with $\mathsf{qk}$ committed in the note's payment key, proved inside
the spend step, which derives it anyway; and a [leanSPHINCS](auth-leansphincs.md) signature over a
digest of the transaction, verified inside the proof with the public key as a witness. The section
also covers recovery from Ironwood and from Tachyon, and hardware wallets.

## Binding a note to its action

Tachyon binds a note to its action through the randomized key: the randomizer $\alpha =
\mathsf{PRF}(\mathsf{cm} \| \theta)$ ties $\mathsf{rk}$, which the action publishes and the
signature verifies under, to the note's commitment inside the proof. Tachyon's book notes that with
$\mathsf{rk}$ gone the binding has to be re-established as a constraint of the proof statement. In
Zoodles it is. Every value an action publishes is derived in the step that opens the note. A spend's
step opens $\mathsf{cm}$ to the payment key, the value, $\psi$, and $\mathsf{rcm}$, derives the
nullifiers from $\mathsf{nk}$ and $\psi$, and takes the amount from the value. An output's step
hashes the commitment it publishes from the note it creates. The lineage's attestation of
$\mathsf{cm}$ reaches the spend step as a PCD header, which the step checks against the commitment
it opens. The proof tree then carries the published values to the root in its headers. So a preimage
proof inside a spend step is bound to the whole transaction by the tree, and a signature by [the
digest](auth-leansphincs.md#the-message) of those values. No randomizer is needed.

## The lineage

A Zoodles note's lineage runs in the background, as Tachyon's does, and is not part of any
transaction. Once an epoch, <!--fig:zoodles_epoch_blocks-->4,096<!--/fig--> blocks
or <!--fig:zoodles_epoch_days-->1.2<!--/fig--> days at 25-second blocks, a step advances the note
past the epoch's published tachygrams, proving that its nullifier is not among them.

Tachyon does this with set polynomials. The epoch's tachygrams are split into buckets by a
quadratic-residue profile, each bucket a polynomial opened at the nullifier, and the step folds the
bucket's contents. Over Kishu's digits a bucket of <!--fig:zoodles_bucket_coeffs-->8,192<!--/fig-->
tachygrams is <!--fig:zoodles_bucket_digits-->2.10 million<!--/fig--> digits to fold for every note
in every epoch, most of them the builder's work rather than the wallet's. The frontier page prices
the alternative: a sorted Merkle tree over the
epoch's <!--fig:zoodles_epoch_tachygrams-->1,048,576<!--/fig-->
tachygrams, <!--fig:zoodles_epoch_per_block-->256<!--/fig--> a block. The exclusion proof is the
nullifier's two neighbours as one leaf with its path of <!--fig:zoodles_epoch_hashes-->22<!--/fig-->
hashes, two 256-bit comparisons, and the epoch range
check: <!--fig:app_zoodles_epoch_kishu-->332,000<!--/fig--> Kishu digits. That
takes <!--fig:tx_zoodles_epoch_kishu_s-->0.0395<!--/fig--> s a note an epoch at
rank <!--fig:tx_zoodles_epoch_kishu_rank-->19<!--/fig--> on one core, without zero knowledge, since
the lineage never leaves the wallet. On that count the tree is well ahead. The bucket route as
Tachyon folds it, at a capacity chosen for digits, is still to be priced beside it, and [The epoch's
tachygram set](zoodles-epoch-set.md) compares the representations.

## Cost

On one core, in Kishu, for two inputs and two outputs: a transaction authorized by preimage
is <!--fig:app_zoodles_preimage_kishu-->313,000<!--/fig--> committed digits and
takes <!--fig:tx_zoodles_preimage_kishu_zk_s-->0.0824<!--/fig--> s with zero knowledge at
rank <!--fig:tx_zoodles_preimage_kishu_zk_rank-->19<!--/fig-->,
or <!--fig:tx_zoodles_preimage_kishu_s-->0.0395<!--/fig--> s without. One authorized by leanSPHINCS
with BLAKE3 is <!--fig:app_zoodles_leansphincs_blake3_kishu-->9.42 million<!--/fig--> digits
and <!--fig:tx_zoodles_leansphincs_blake3_kishu_zk_s-->0.363<!--/fig--> s with zero knowledge at
rank <!--fig:tx_zoodles_leansphincs_blake3_kishu_zk_rank-->21<!--/fig-->,
in <!--fig:tx_zoodles_leansphincs_blake3_kishu_zk_steps-->5<!--/fig--> steps; the frontier page has
the BLAKE2s and Keccak variants. Tachyon's own four tachyactions in Kishu with zero knowledge
take <!--fig:tx_tachyon4_kishu_zk_s-->0.241<!--/fig--> s, so Zoodles by preimage
is <!--fig:zoodles_preimage_of_tachyon_pct-->34<!--/fig--> percent of them; on Pedersen-IPA they
take <!--fig:tx_tachyon4_pedersen_s-->8.44<!--/fig--> s. At these ranks a step commits
$2^{\mathrm{rank}}$ bits, between a quarter and the whole of Ragu's $2^{13}$ Pallas coefficients in
bits, which is the fifth bullet above. The [frontier page](pareto-template.html#transaction-prover)
gives the same transactions under every scheme it prices.

## Status

- Whether Zoodles needs Tachyon's PCD header of nine elements, or fits the recovery circuit's six or
  seven, is not settled; the frontier page prices it at nine. The pool sums of [Pool
  accounting](#pool-accounting) are part of the count.
- The lineage is priced by the sorted tree alone; the bucket route is to be priced beside it.
- The bind, lift, and fuse steps that close a lineage segment at a spend are not counted.
- The packed step's interface is not charged. One step circuit carrying several nodes' headers and
  set products, with the fee logic beside the spends and outputs it fuses, is circuit layout that
  Tachyon's one-circuit-per-step design does not have.
- The set polynomials over a 64-bit field need a quartic extension, or four polynomials, for 256-bit
  tachygrams, and an opening is priced as one more claim. A committed online vector per step would
  add a group to the fold.

## Acknowledgements

Zoodles is mostly just the obvious adaptation of Tachyon. Thank you to the [Tachyon
team](https://tachyon.z.cash/team/), Sean Bowe, Tal Derei, Connor O'Hara, Alex Xiong, L Winslow, and
Samuel Akinosho, for their work. The adaptation, its name, and its modelling are Daira-Emma
Hopwood's.

## References

- <a id="ref-zip209"></a>[ZIP-209] Sean Bowe. ZIP 209: Prohibit Out-of-Range Chain Value Pool
  Balances. <https://zips.z.cash/zip-0209>
- <a id="ref-zip248"></a>[ZIP-248] Jack Grigg, Kris Nuttycombe, Daira-Emma Hopwood, Schell Scivally.
  ZIP 248: Extensible Transaction Format. Draft. <https://zips.z.cash/zip-0248>
- <a id="ref-zip2005"></a>[ZIP-2005] Daira-Emma Hopwood, Jack Grigg. ZIP 2005: Ironwood Quantum
  Recoverability. <https://zips.z.cash/zip-2005>
