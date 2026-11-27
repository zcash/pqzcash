# Hash preimage

The simplest authorization method is Sprout's: the note's payment key is a hash of the authorizing
key, and the spender proves knowledge of the preimage. The preimage and its image are a quantum
spending key and a quantum key as ZIP 2005 defines them [\[ZIP-2005\]](#ref-zip2005),
$\mathsf{qk} = \mathsf{H^{qk}}(\mathsf{qsk})$ by the ZIP's BLAKE3 derivation.[^personalization] Each
protocol has keys of its own; what they share is the derivation, so the same check serves:

- a native Zoodles spend, where $\mathsf{qk}$ is the owner component of the note's payment key;
- the recovery of an Ironwood note on the $\mathsf{use\_qsk} = \mathsf{true}$ path, where it is the
  arm $\mathsf{SoK^{qsk}}$ of the Recovery Statement; and
- the recovery of a Tachyon note, [once its proof-authorizing key carries
  $\mathsf{qk}$](recovery-tachyon.md#what-the-key-structure-lacks).

In Zoodles the spend step opens the payment key to $(\mathsf{nk}, \mathsf{qk})$ and derives
$\mathsf{qk}$ from $\mathsf{qsk}$, two BLAKE3 compressions, the second being the check. On its own
the statement is one BLAKE3 compression, <!--fig:app_qk_bits-->11,344<!--/fig--> committed digits in
Kishu, which the frontier page prices as the device statement `qk`, with the linking commitment of
ZIP 2005's hardware-wallet section left out for now. [Hardware wallets](hardware-wallets.md) gives
what it costs a wallet to prove by itself.

Inside a transaction's own proof the check needs nothing more: the spend step that proves it is
bound to the rest of the transaction by the proof tree, directly and through the PCD headers, so no
digest of the transaction is involved. Made outside that proof, as a wallet's leaf handed to the
host or as ZIP 2005's $\mathsf{SoK^{qsk}}$ on the transaction's SigHash, the proof is a signature,
and the rest of this page is about what that requires.

## The signature of knowledge

A proof of knowledge of a preimage of $\mathsf{qk}$ is not enough. It would verify under any
transaction, so it could be replayed; the statement has to be signed. The reason goes deeper than
replay. The reduction that proves $\mathsf{SoK^{qsk}}$ unforgeable, as a signature scheme with key
$\mathsf{qk}$, has to answer signing queries without $\mathsf{qsk}$. So it simulates them, and it
must then extract a preimage from a forger who has seen simulated proofs. That is simulation
extractability, which plain knowledge soundness does not give. A signature of knowledge is by
definition a simulation-extractable proof with the message as its label [\[CL06\]](#ref-cl06).

### The folklore technique, and where it is proved

The technique is to bind the message into the Fiat–Shamir transcript from the start. The instance
and the message go into the hash before the first challenge, and the chain of challenges binds
everything after. Classically this is proved. For sigma protocols it is [\[FKMV12\]](#ref-fkmv12).
For multi-round sum-check protocols it is recent. [\[DG23\]](#ref-dg23) shows Spartan and
Bulletproofs simulation-extractable with no change. [\[FFKRZ23\]](#ref-ffkrz23) and
[\[KPT23\]](#ref-kpt23) prove it for Fiat–Shamir of a polynomial IOP with a binding commitment in
general, under the conditions one expects: the instance hashed first, and a unique-response or
state-restoration property of the protocol. The Frozen Heart vulnerabilities of 2022
[\[TOB22\]](#ref-tob22), forgeries against implementations that left the instance out of the hash,
are what omitting it costs. The technique is free.

What is missing is the quantum random-oracle model, which Zoodles and the Recovery Protocol need.
Fiat–Shamir of sigma protocols is settled there, by [\[DFMS19\]](#ref-dfms19) and
[\[LZ19\]](#ref-lz19). Knowledge soundness of Fiat–Shamir on an IOP is settled with polynomial loss,
by [\[CMS19\]](#ref-cms19). But the multi-round measure-and-reprogram bound [\[DFM20\]](#ref-dfm20)
loses a factor exponential in the number of rounds, which for thirty sum-check rounds says nothing.
And the simulation-extractability proofs above rewind, which the quantum setting does not allow. We
know of no simulation-extractability result for a sum-check-based succinct argument in the quantum
random-oracle model with usable bounds. In the trust-boundary style of the Ironwood formalization,
the signature-of-knowledge property would have to be a named hypothesis.

### A route that is available: the non-injectivity of the hash

A classical argument avoids simulation extractability altogether, and it fits this statement
unusually well. $\mathsf{H^{qk}}$ maps 256 bits to 256 bits, so a uniformly random $\mathsf{qsk}$
has a second preimage with probability about
$1 - 1/e$, <!--fig:sok_second_preimage_pct-->63<!--/fig--> percent. The reduction to the collision
resistance of $\mathsf{H^{qk}}$ picks $\mathsf{qsk}$ itself, answers every signing query with the
real prover, and extracts a preimage from the forgery. A zero-knowledge proof is witness
indistinguishable [\[FS90\]](#ref-fs90). So when a second preimage exists, the forger's view is the
same whichever preimage the reduction holds, and the extracted one differs from the reduction's with
probability about a half. Then the reduction holds a
collision. <!--claim:sok_loss_small:10a6c1-->The loss is a factor of
about <!--fig:sok_loss_factor-->3.2<!--/fig-->.<!--/claim--> This is the two-witness form that
[\[KW03\]](#ref-kw03) used for tight signature reductions, with the hash's own non-injectivity
standing in for the second key, so the circuit does not change. It needs zero knowledge and
knowledge soundness with auxiliary input, the honest signatures on other messages being that input.
Both are available in the quantum random-oracle model for the proof systems in play, and the message
is still bound into the instance before the first challenge. Nothing in the protocol changes; only
the proof does. This is the proof to write for the Kishu route. The [hash-based
signature](auth-leansphincs.md) route does not raise the question. leanSPHINCS is a signature scheme
with its own strong unforgeability proof, 127 classical bits in the random-oracle model
[\[Wam26\]](#ref-wam26), and the message enters its digest with the randomizer.

[^personalization]: The derivation's personalization string, "Zcash ZIP 2005 qk-derivation v1",
names the ZIP and not Ironwood, on purpose. Any domain separation between the protocols need only
affect how $\mathsf{qsk}$ is obtained, not the derivation of $\mathsf{qk}$ from it.

## References

- <a id="ref-cl06"></a>[CL06] Melissa Chase, Anna Lysyanskaya. On signatures of knowledge. CRYPTO
  2006. <https://eprint.iacr.org/2006/184>
- <a id="ref-cms19"></a>[CMS19] Alessandro Chiesa, Peter Manohar, Nicholas Spooner. Succinct
  arguments in the quantum random oracle model. TCC 2019. <https://eprint.iacr.org/2019/834>
- <a id="ref-dfm20"></a>[DFM20] Jelle Don, Serge Fehr, Christian Majenz. The measure-and-reprogram
  technique 2.0: multi-round Fiat–Shamir and more. CRYPTO 2020. <https://eprint.iacr.org/2020/282>
- <a id="ref-dfms19"></a>[DFMS19] Jelle Don, Serge Fehr, Christian Majenz, Christian Schaffner.
  Security of the Fiat–Shamir transformation in the quantum random-oracle model. CRYPTO
  2019. <https://eprint.iacr.org/2019/190>
- <a id="ref-dg23"></a>[DG23] Quang Dao, Paul Grubbs. Spartan and Bulletproofs are
  simulation-extractable (for free!). EUROCRYPT 2023. <https://eprint.iacr.org/2023/494>
- <a id="ref-ffkrz23"></a>[FFKRZ23] Antonio Faonio, Dario Fiore, Markulf Kohlweiss, Luigi Russo,
  Michał Zając. From polynomial IOP and commitments to non-malleable zkSNARKs. TCC 2023.
- <a id="ref-fkmv12"></a>[FKMV12] Sebastian Faust, Markulf Kohlweiss, Giorgia Azzurra Marson,
  Daniele Venturi. On the non-malleability of the Fiat–Shamir transform. INDOCRYPT 2012.
- <a id="ref-fs90"></a>[FS90] Uriel Feige, Adi Shamir. Witness indistinguishable and witness hiding
  protocols. STOC 1990.
- <a id="ref-kpt23"></a>[KPT23] Markulf Kohlweiss, Mahak Pancholi, Akira Takahashi. How to compile
  polynomial IOP into simulation-extractable SNARKs: a modular approach. TCC 2023.
- <a id="ref-kw03"></a>[KW03] Jonathan Katz, Nan Wang. Efficiency improvements for signature schemes
  with tight security reductions. CCS 2003.
- <a id="ref-lz19"></a>[LZ19] Qipeng Liu, Mark Zhandry. Revisiting post-quantum Fiat–Shamir. CRYPTO
  2019.
- <a id="ref-tob22"></a>[TOB22] Trail of Bits. Coordinated disclosure of vulnerabilities affecting
  Girault, Bulletproofs, and PlonK ("Frozen Heart").
  2022. <https://blog.trailofbits.com/2022/04/13/the-frozen-heart-vulnerability-in-bulletproofs/>
- <a id="ref-wam26"></a>[Wam26] Tom Wambsgans. leanSPHINCS: a hash-based stateless signature scheme
  for post-quantum Ethereum, with security proofs in Lean 4. 2026. <https://sphincs.art/>
- <a id="ref-zip2005"></a>[ZIP-2005] Daira-Emma Hopwood, Jack Grigg. ZIP 2005: Ironwood Quantum
  Recoverability. <https://zips.z.cash/zip-2005>
