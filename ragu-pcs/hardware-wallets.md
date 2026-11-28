# Hardware wallets

A hardware wallet can use either authorization method of [this section](spend-authorization.md) on
its own: the [hash preimage](auth-preimage.md) as a Kishu leaf of the transaction's proof, or a
[leanSPHINCS](auth-leansphincs.md) signature that the host verifies in its transaction. This page
asks what the wallet has to compute and transfer for each, and what a channel allows. It was written
for ZIP 2005's Recovery Statement [\[ZIP-2005\]](#ref-zip2005), whose Option A keeps $\mathsf{qsk}$
on a hardware wallet and has the networked host prove the rest ([Recovery from
Ironwood](recovery-ironwood.md)). It takes the device split from an analysis of FROST members
recovering from a seed phrase. The costs are the same for a native Zoodles spend. The figures come
from [the PCS frontier page](pareto-template.html), which prices the wallet's part as applications
of its transaction measure.

## The device split

The model to reason in makes the hardware wallets the only honest parties and treats every networked
device as the adversary. A wallet holds the spending key $\mathsf{sk}$, or with FROST its signing
share and the common $\mathsf{sk}$, and so $\mathsf{qsk}$. It exports $\mathsf{nk}$ and
$\mathsf{qk}$ and nothing else that is derived from the secret. $\mathsf{ak}$ is derived from
$\mathsf{sk}$ and exported by a single-signer wallet; with FROST it is the output of the distributed
key generation. $\mathsf{rivk\_ext}$ and the incoming and outgoing viewing keys follow from those,
so the host can scan, build transactions and produce the main Recovery proof, whose witness is
viewing-key material plus the note and its path. ZIP 2005's other path,
$\mathsf{use\_qsk} = \mathsf{false}$, has the Recovery Statement prove the key derivations from
$\mathsf{sk}$ itself. The priced circuit takes either value; this page follows the
$\mathsf{use\_qsk} = \mathsf{true}$ path, the one whose costs a hardware wallet is meant to
optimize.

The wallet signs FROST shares and makes $\mathsf{SoK^{qsk}}$, each after verifying the transaction
and asking the user, and the user's confirmation is the adversary's choice of message. Two adversary
classes share one win condition: a consensus-valid recovery spend on an unapproved SigHash.

- A pre-quantum adversary corrupts up to $t - 1$ wallets. It is bounded by the unforgeability of
  re-randomized FROST.
- A discrete-log-breaking adversary is given every host's state and every network message, but no
  wallet. It is bounded by the unforgeability of $\mathsf{SoK^{qsk}}$ as a signature scheme with key
  $\mathsf{qk}$. That bound is 1-of-$n$, since every wallet holds the same $\mathsf{qsk}$.

Option A is the statement that the second class learns nothing from a wallet but its interface's
outputs.

## What the wallet can prove

Two shapes are priced. The wallet can prove the preimage statement as a leaf of the transaction's
own proof system, [Kishu on the frontier page](pareto-template.html#kishu): one BLAKE3
compression, <!--fig:app_qk_bits-->11,344<!--/fig--> committed digits, with the linking commitment
of ZIP 2005's hardware-wallet section left out for now. Or the wallet can sign with leanSPHINCS and
leave the verification to the host, which proves the verifier inside its own transaction with the
signature and the public key as witnesses, so the spends stay unlinkable.

### A Kishu leaf

The handoff is the whole question. The host folds the wallet's leaf into the transaction's
accumulator, and split accumulation needs the witness of whatever it folds. So the wallet hands over
a masked witness: the response $z = y + cs$ of the [zero-knowledge
note](zk-fiat-shamir-with-aborts.md) (the zk note), a Gaussian mask $y$ added to the leaf's digits
$s$ under a challenge $c$. Rejection sampling makes the accepted $z$ independent of the secret. The
mask covers the leaf's $2^{\text{step rank}}$ digits alone, since the wallet hands over no
accumulator of its own. The transaction measure charges the user's handoff the host's merge that
folds the leaf, and a small merge of the handoff's own: the challenge derivation, the commitment
identity, and the claim fold. The decomposition and the range and norm proofs are deferred to the
host (the zk note's [§5.8](zk-fiat-shamir-with-aborts.md#58-the-users-online-cost)). For a
one-compression leaf the host's merge is most of the cost. <!--claim:qk_merge_and_fold:44a4b2-->The
measure's <!--fig:tx_qk_kishu_zk_s-->0.0336<!--/fig--> s in a step
of <!--fig:tx_qk_kishu_zk_rank-->$1.75 \times 2^{20}$<!--/fig--> digits
is <!--fig:tx_qk_kishu_zk_merges_pct-->99<!--/fig--> percent merge
and <!--fig:tx_qk_kishu_zk_fold_pct-->8<!--/fig--> percent fold, and the circuit itself is a few
percent.<!--/claim-->

The wallet need not prove that fold. The zk note's
[§4.2](zk-fiat-shamir-with-aborts.md#42-what-the-proof-needs) lists the handoff merge's witness as
simulatable: the hiding commitment, the mask's commitment, the challenge, the claims and the
obligation transcripts. So the host can derive the challenge, prove the fold's merge and the
obligations (the zk note's [§5.8](zk-fiat-shamir-with-aborts.md#58-the-users-online-cost) deferral),
and verify the leaf's sum-checks in its own merge. The wallet keeps what touches the secret. It
commits to the leaf under the matrix that binds the masked response $z$, whose coordinates are
larger than the leaf's digits. It appends uniformly random bits to the leaf's bits. The commitment
hides the leaf only if there are enough of them: <!--fig:hiding_padding_bits-->4,800<!--/fig--> bits
at the 147-bit floor, for a computational argument that is given below. It proves its constraint and
Booleanity sum-checks under Libra-style masking polynomials, since the host sees their
transcripts: <!--fig:qk_sumcheck_mask_elements-->112<!--/fig--> committed elements of
$\mathbb{F}_q$. <!--claim:device_element_widths:773881-->Each is committed in the widest digits that
keep the vector's matrix at the padding sweep's rows, judged by the vector's exact $\ell_2$
norm: <!--fig:qk_device_element_digits-->33<!--/fig--> balanced dibits at the 147-bit floor,
and <!--fig:qk_device_element_digits_128-->22<!--/fig--> tribits at 128.<!--/claim--> It samples and
commits the mask in idle time, and computes the response with the rejection test.

The padding is computational rather than the zk note's [leftover-hash
one](zk-fiat-shamir-with-aborts.md#42-what-the-proof-needs). $A\rho$ for $\rho$
of <!--fig:hiding_padding_bits-->4,800<!--/fig--> uniform bits at the 147-bit floor, the page's
default, or <!--fig:hiding_padding_bits_128-->4,400<!--/fig--> at 128, is pseudorandom if
knapsack-LWE is hard at the commitment's rows. By the Micciancio–Mol duality that is LWE of the
padding's bits less the rows, with the rows as samples and binary secret and error at the 64-bit
modulus (the zk note's [§5.10](zk-fiat-shamir-with-aborts.md#510-a-computational-hiding-padding)
gives the argument). <!--claim:hiding_padding_secure:9dc0b4-->The lattice estimator puts the
cheapest attack on the padding at the matrix's <!--fig:qk_device_matrix_rows-->1,024<!--/fig--> rows
at <!--fig:hiding_padding_attack_bits-->149<!--/fig-->
and <!--fig:hiding_padding_attack_bits_128-->128<!--/fig--> quantum bits at the two floors'
paddings, under the page's cost model, a dual hybrid attack on the binary secret. The primal attacks
are a hundred bits dearer, so a primal estimate alone would overstate the margin. The padding is the
least on the sweep's grid, 50 bits where the floors are crossed, that reaches the floor, so the
hedge of the 147-bit floor applies to it too. At the zk note's 1,385 rows 5,000 bits
give <!--fig:hiding_padding_attack_bits_1385-->140<!--/fig--> bits, and at 2,048 rows they would
fall short of the 128-bit floor. The frontier page's [165-bit level](pareto-template.html#level-3)
is in that case: the wallet's matrix there has <!--fig:hiding_padding_rows_level3-->2,048<!--/fig-->
rows at every digit width, so its padding comes from a sweep at those rows. It
is <!--fig:hiding_padding_bytes_level3-->768<!--/fig--> bytes, <!--fig:hiding_padding_bits_level3-->6,144<!--/fig--> bits,
where the cheapest attack is at <!--fig:hiding_padding_attack_bits_level3-->165.9<!--/fig--> quantum
bits. The least whole number of bytes that reaches the level
is <!--fig:hiding_padding_least_bytes_level3-->767<!--/fig-->, and 768 is taken as the rounder
figure.<!--/claim--> The statistical padding would
be <!--fig:hiding_padding_statistical_kbits-->66<!--/fig--> thousand
bits, <!--fig:hiding_padding_statistical_over_statement-->5.8<!--/fig--> times the statement.

The paddings at the three floors: the wallet's matrix's rows, the padding, the work of the cheapest
attack on it under the quantum cost model, and the handoff that results, the wallet's masked
response:

| Floor | Matrix rows | Padding | Cheapest attack | Handoff |
|---|---|---|---|---|
| 128 bits | <!--fig:hiding_padding_table_rows_128-->1,024<!--/fig--> | <!--fig:hiding_padding_table_padding_128-->4,400 bits<br>(550 bytes)<!--/fig--> | <!--fig:hiding_padding_table_attack_128-->$2^{128.3}$<!--/fig--> | <!--fig:hiding_padding_table_handoff_128-->50.1 kbytes<!--/fig--> |
| 147 bits, the default | <!--fig:hiding_padding_table_rows_147-->1,024<!--/fig--> | <!--fig:hiding_padding_table_padding_147-->4,800 bits<br>(600 bytes)<!--/fig--> | <!--fig:hiding_padding_table_attack_147-->$2^{148.9}$<!--/fig--> | <!--fig:hiding_padding_table_handoff_147-->54.6 kbytes<!--/fig--> |
| 165 bits | <!--fig:hiding_padding_table_rows_165-->2,048<!--/fig--> | <!--fig:hiding_padding_table_padding_165-->6,144 bits<br>(768 bytes)<!--/fig--> | <!--fig:hiding_padding_table_attack_165-->$2^{165.9}$<!--/fig--> | <!--fig:hiding_padding_table_handoff_165-->54.9 kbytes<!--/fig--> |

So the wallet
commits <!--fig:qk_device_digits-->19,840<!--/fig--> digits. <!--claim:qk_device_share_small:35dfe3-->That
is <!--fig:qk_device_online_ms-->0.224<!--/fig--> ms of online work on one M4
core, <!--fig:qk_device_share_pct-->9<!--/fig--> percent of the handoff fold that the measure
charges the user,<!--/claim--> with <!--fig:qk_device_idle_ms-->0.280<!--/fig--> ms in idle time,
and a response of <!--fig:qk_device_z_kbytes-->55 kbytes<!--/fig-->
at <!--fig:qk_device_z_bits-->22<!--/fig--> bits a coordinate. The device rates are assumptions,
scaled from the hash rates that [\[Wam26\]](#ref-wam26)'s hardware-wallet benchmark measured on a
Ledger Nano S+: <!--fig:device_mcu_rate-->10 million<!--/fig--> word multiplications a second for an
MCU-class device and <!--fig:device_se_rate-->3 million<!--/fig--> for a secure element. At those
rates the computation takes <!--fig:qk_device_mcu_s-->0.067<!--/fig-->
and <!--fig:qk_device_secure_element_s-->0.22<!--/fig--> s. The transfer of $z$ at that device's
measured <!--fig:device_link_kbytes_s-->21<!--/fig--> kbytes a second over USB
takes <!--fig:qk_device_link_s-->2.6<!--/fig--> s,
or <!--fig:qk_device_link_pipelined_s-->0.94<!--/fig--> s with a pipelined transport. No merge
circuit and no accumulator sit on the device, and the witness
is <!--fig:qk_device_witness_kbytes-->2.9 kbytes<!--/fig--> packed at its digits' widths. So a Kishu
signature of knowledge is within reach of a high-end hardware wallet on a USB link, and the transfer
is the larger part of it.

#### Over an animated QR code

An airgapped wallet of the Keystone kind exchanges data by animated QR codes, fountain-coded
fragments read by a phone camera from the wallet's screen. Keystone's firmware sends fragments
of <!--fig:qr_fragment_bytes-->200<!--/fig--> bytes at <!--fig:qr_frames_per_s-->5<!--/fig--> frames
a second, <!--fig:qr_kbytes_per_s-->1<!--/fig--> kbyte a second. So the response
takes <!--fig:qk_qr_current_s-->55<!--/fig--> s with no frame missed, and the fountain code's
redundancy after missed frames can double or treble that. Denser codes would cut it: a fragment
of <!--fig:qr_dense_fragment_bytes-->800<!--/fig--> bytes at the same rate
gives <!--fig:qk_qr_dense_s-->14<!--/fig--> s, and the format's ceiling, a version-40 symbol holding
about <!--fig:qr_max_fragment_bytes-->2,100<!--/fig--> bytes of
fragment, <!--fig:qk_qr_max_s-->5.2<!--/fig--> s. Whether a camera reads the denser codes reliably
depends on the screen, the light, and the camera, and gets worse toward the ceiling. So the transfer
is slow at today's settings and within reach with denser codes on some devices. The device's memory
is the other constraint: it holds the mask, about <!--fig:qk_device_z_kbytes-->55 kbytes<!--/fig-->,
over which the response is written in place, beside the witness.

The response cannot be made much
smaller, and the reason is not an encoding choice. <!--claim:qk_qr_channel_too_big:94cc38-->The
accepted $z$ is a Gaussian of width $\sigma$ on every coordinate of the leaf, about
$\log_2(\sigma\sqrt{2\pi e})$ bits of information each. It is secret-dependent, so it cannot be
regenerated from a seed as the mask can. With no padding and no masking elements the leaf's
own <!--fig:app_qk_bits-->11,344<!--/fig--> coordinates still
make <!--fig:qk_z_floor_kbytes-->30 kbytes<!--/fig-->. A succinct Kishu proof of the leaf in place
of the response would be about <!--fig:qk_succinct_proof_kbytes-->72 kbytes<!--/fig-->, whatever the
step rank from <!--fig:qk_min_rank-->14<!--/fig--> up, since nearly all of it is the opening's fixed
parts, the compression levels and the terminal.<!--/claim--> A narrower mask saves two or three bits
a coordinate at the price of idle-time attempts, and a lighter challenge set a fraction of a bit.
The transfer cannot be avoided by moving the fold elsewhere: split accumulation needs the host to
hold a witness of the wallet's accumulator, and that witness is $z$. A wallet on today's QR settings
is better served by the signature of the [next section](#a-hash-based-signature).

### A hash-based signature

leanSPHINCS fits the QR channel: a signature
of <!--fig:leansphincs_sig_bytes-->4,276<!--/fig--> bytes with the pruned
key, <!--fig:leansphincs_layered_sig_bytes-->6,332<!--/fig--> with the layered forest key,
or <!--fig:leansphincs_ethereum_bytes-->7,740<!--/fig--> with Ethereum's provisional set
[\[EIP-8288\]](#ref-eip8288) [\[Lit26\]](#ref-lit26) is a few seconds of scanning. Its signing is
hashing alone, measured on a Nano S+ by [\[Wam26\]](#ref-wam26)'s benchmark. The pruned
key's <!--fig:leansphincs_grind-->16,384<!--/fig--> grinding digests per signature
take <!--fig:leansphincs_grind_keccak_s-->2.8<!--/fig--> s with Keccak on that device
and <!--fig:leansphincs_grind_blake2s_s-->0.50<!--/fig--> s with BLAKE2s; BLAKE3, with seven rounds
to BLAKE2s's ten, was not in the benchmark and should be no slower. The grind is the wallet's: it is
keyed, and the key cannot leave the wallet without revealing which leaves it kept. A full tree can
take the host's help instead. The wallet produces the leaf hashes at key generation, the host builds
and stores the tree and supplies the authentication paths, and signing then has no grind.

How much of the tree the signer keeps is a choice. <!--claim:leansphincs_pruning_table:da04e8-->The
kept subtree's height sets the trade between the key's proved lifetime, its generation, and the
grind.<!--/claim--> For a tree of height <!--fig:leansphincs_tree_height-->26<!--/fig-->, with the
lifetimes proved at <!--fig:leansphincs_security_bits-->127<!--/fig--> bits and the times on a Nano
S+ with BLAKE2s:

| Kept subtree's height | Signatures proved safe | Key generation | Grinding cost per signature |
|---|---|---|---|
| 12, as priced here | <!--fig:leansphincs_b12_lifetime-->126,900<!--/fig--> | <!--fig:leansphincs_b12_keygen-->991,260 compressions<br>(30 s)<!--/fig--> | <!--fig:leansphincs_b12_grind-->16,384 compressions<br>(0.50 s)<!--/fig--> |
| 14 | <!--fig:leansphincs_b14_lifetime-->480,100<!--/fig--> | <!--fig:leansphincs_b14_keygen-->3.96 million compressions<br>(2.0 minutes)<!--/fig--> | <!--fig:leansphincs_b14_grind-->4,096 compressions<br>(0.13 s)<!--/fig--> |
| 20 | <!--fig:leansphincs_b20_lifetime-->26.0 million<!--/fig--> | <!--fig:leansphincs_b20_keygen-->254 million compressions<br>(2.2 hours)<!--/fig--> | <!--fig:leansphincs_b20_grind-->64 compressions<br>(0.0020 s)<!--/fig--> |
| 26, the full tree | <!--fig:leansphincs_b26_lifetime-->1.38 billion<!--/fig--> | <!--fig:leansphincs_b26_keygen-->16.2 billion compressions<br>(5.8 days)<!--/fig--> | <!--fig:leansphincs_b26_grind-->none<!--/fig--> |

The signature is the same size, <!--fig:leansphincs_sig_bytes-->4,276<!--/fig--> bytes, in every
row: the verifier cannot tell a pruned key from a full one.

leanSPHINCS is stateless and deterministic, which matters when every member's wallet holds the same
seed: a stateful scheme's index would be reused across wallets, and the deterministic randomizer
makes the members' signatures identical. The verifier's cost in the host's transaction is on the
[leanSPHINCS](auth-leansphincs.md) page.

## References

- <a id="ref-eip8288"></a>[EIP-8288] Vitalik Buterin, Thomas Coratger. EIP-8288: in-mempool
  signature and proof aggregation. Draft, 2026. <https://eips.ethereum.org/EIPS/eip-8288>
- <a id="ref-lit26"></a>[Lit26] Ivan Litteri. Dependency frames for leanSPHINCS signatures. Draft
  EIP-8504, 2026. <https://github.com/ethereum/EIPs/pull/12672>
- <a id="ref-wam26"></a>[Wam26] Tom Wambsgans. leanSPHINCS: a hash-based stateless signature scheme
  for post-quantum Ethereum, with security proofs in Lean 4. 2026. <https://sphincs.art/>; the
  hardware-wallet benchmark at <https://github.com/TomWambsgans/hardware-wallet-benchmark>
- <a id="ref-zip2005"></a>[ZIP-2005] Daira-Emma Hopwood, Jack Grigg. ZIP 2005: Ironwood Quantum
  Recoverability. <https://zips.z.cash/zip-2005>
